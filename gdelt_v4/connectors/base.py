"""
GDELT v4.0 Base Connector
==========================
Abstract base class for all BigQuery connectors with robust error handling,
retry logic, and standardized logging.

Author: Philip Hendrik Littau
Version: 4.0.0
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
from functools import wraps

import pandas as pd
from google.cloud import bigquery
from google.cloud.bigquery import Client, QueryJobConfig
from google.api_core import exceptions as google_exceptions

from gdelt_v4.config.settings import GDELTConfig, get_config
from gdelt_v4.utils.logging import get_logger


logger = get_logger(__name__)


class BigQueryError(Exception):
    """Base exception for BigQuery-related errors."""
    pass


class QueryError(BigQueryError):
    """Raised when a query fails."""
    
    def __init__(self, message: str, sql: Optional[str] = None, job_id: Optional[str] = None):
        super().__init__(message)
        self.sql = sql
        self.job_id = job_id


class ConnectionError(BigQueryError):
    """Raised when connection to BigQuery fails."""
    pass


class PermissionError(BigQueryError):
    """Raised when permission is denied."""
    pass


class RetryableError(BigQueryError):
    """Raised for errors that can be retried."""
    pass


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (
        google_exceptions.ServiceUnavailable,
        google_exceptions.TooManyRequests,
        google_exceptions.InternalServerError,
        RetryableError,
    ),
):
    """
    Decorator for retry logic with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial delay between retries in seconds.
        backoff_factor: Multiplier for delay after each retry.
        retryable_exceptions: Tuple of exception types to retry.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed. Last error: {e}"
                        )
                except Exception as e:
                    # Non-retryable exception
                    raise
            
            # If we've exhausted retries, raise the last exception
            raise last_exception
        
        return wrapper
    return decorator


class BaseGDELTConnector(ABC):
    """
    Abstract base class for GDELT BigQuery connectors.
    
    Provides:
    - Standardized BigQuery client initialization
    - Retry logic with exponential backoff
    - Error classification and handling
    - Query logging and metrics
    - Dry-run cost estimation
    
    Subclasses must implement:
    - execute_query(): Execute a SQL query and return results
    
    Attributes:
        config: The GDELT configuration instance.
        client: The BigQuery client instance.
        _query_count: Number of queries executed.
        _total_bytes_billed: Total bytes billed across queries.
    
    Example:
        >>> class MyConnector(BaseGDELTConnector):
        ...     def execute_query(self, sql: str) -> pd.DataFrame:
        ...         return self._execute_sql(sql)
        ...
        >>> connector = MyConnector()
        >>> df = connector.execute_query("SELECT * FROM ...")
    """
    
    def __init__(self, config: Optional[GDELTConfig] = None):
        """
        Initialize the connector.
        
        Args:
            config: Optional GDELTConfig instance. Uses global config if not provided.
        """
        self.config = config or get_config()
        self.client = self._init_client()
        self._query_count = 0
        self._total_bytes_billed = 0
        
        logger.info(
            f"Initialized {self.__class__.__name__} "
            f"(project={self.config.bigquery.job_project or 'default'}, "
            f"table={self.config.bigquery.full_table_id})"
        )
    
    def _init_client(self) -> Client:
        """
        Initialize the BigQuery client.
        
        Returns:
            Configured BigQuery Client instance.
            
        Raises:
            ConnectionError: If client initialization fails.
        """
        try:
            bq_config = self.config.bigquery
            
            if bq_config.credentials_path:
                # Use service account credentials
                import json
                with open(bq_config.credentials_path, 'r') as f:
                    creds_data = json.load(f)
                
                # Use the user's project for jobs, not gdelt-bq
                project_id = bq_config.job_project or creds_data.get('project_id')
                
                client = Client.from_service_account_json(
                    bq_config.credentials_path,
                    project=project_id,
                    location=bq_config.location,
                )
                logger.debug(f"Using service account credentials for project: {project_id}")
            else:
                # Use application default credentials
                client = Client(
                    project=bq_config.job_project,
                    location=bq_config.location,
                )
                logger.debug("Using application default credentials")
            
            return client
            
        except FileNotFoundError as e:
            raise ConnectionError(f"Credentials file not found: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to initialize BigQuery client: {e}")
    
    @abstractmethod
    def execute_query(self, sql: str, **kwargs) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a DataFrame.
        
        Args:
            sql: The SQL query to execute.
            **kwargs: Additional arguments for query execution.
            
        Returns:
            Query results as a pandas DataFrame.
        """
        pass
    
    @with_retry(max_retries=3, initial_delay=1.0)
    def _execute_sql(
        self,
        sql: str,
        job_config: Optional[QueryJobConfig] = None,
        timeout: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Execute a SQL query with retry logic.
        
        Args:
            sql: The SQL query to execute.
            job_config: Optional QueryJobConfig for the query.
            timeout: Query timeout in seconds.
            
        Returns:
            Query results as a pandas DataFrame.
            
        Raises:
            QueryError: If the query fails after retries.
            PermissionError: If permission is denied.
        """
        timeout = timeout or self.config.bigquery.timeout
        
        try:
            logger.debug(f"Executing query (timeout={timeout}s)...")
            
            job = self.client.query(sql, job_config=job_config)
            result = job.result(timeout=timeout)
            
            # Convert to DataFrame without BigQuery Storage API
            # (avoids readsessions.create permission issues)
            df = result.to_dataframe(create_bqstorage_client=False)
            
            # Update metrics
            self._query_count += 1
            if job.total_bytes_billed:
                self._total_bytes_billed += job.total_bytes_billed
            
            logger.info(
                f"Query completed: {len(df)} rows, "
                f"{self._format_bytes(job.total_bytes_billed or 0)} billed"
            )
            
            return df
            
        except google_exceptions.Forbidden as e:
            raise PermissionError(f"Permission denied: {e}")
        except google_exceptions.BadRequest as e:
            raise QueryError(f"Invalid query: {e}", sql=sql)
        except google_exceptions.NotFound as e:
            raise QueryError(f"Table or dataset not found: {e}", sql=sql)
        except TimeoutError as e:
            raise RetryableError(f"Query timed out after {timeout}s")
        except Exception as e:
            raise QueryError(f"Query execution failed: {e}", sql=sql)
    
    def dry_run(self, sql: str) -> Dict[str, Any]:
        """
        Perform a dry run to estimate query cost.
        
        Args:
            sql: The SQL query to estimate.
            
        Returns:
            Dictionary with cost estimation details:
            - total_bytes_processed: Bytes that would be scanned
            - estimated_cost_usd: Estimated cost in USD
            - estimated_gb: Data size in GB
        """
        job_config = QueryJobConfig(dry_run=True, use_query_cache=False)
        
        try:
            job = self.client.query(sql, job_config=job_config)
            
            bytes_processed = job.total_bytes_processed or 0
            gb_processed = bytes_processed / (1024 ** 3)
            # BigQuery on-demand pricing: $5/TB = $0.005/GB
            estimated_cost = gb_processed * 0.005
            
            return {
                "total_bytes_processed": bytes_processed,
                "estimated_gb": round(gb_processed, 3),
                "estimated_cost_usd": round(estimated_cost, 4),
                "formatted_bytes": self._format_bytes(bytes_processed),
            }
            
        except Exception as e:
            logger.warning(f"Dry run failed: {e}")
            return {
                "error": str(e),
                "total_bytes_processed": 0,
                "estimated_cost_usd": 0,
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get query execution metrics.
        
        Returns:
            Dictionary with execution metrics:
            - query_count: Number of queries executed
            - total_bytes_billed: Total bytes billed
            - total_cost_usd: Estimated total cost in USD
        """
        gb_billed = self._total_bytes_billed / (1024 ** 3)
        total_cost = gb_billed * 0.005
        
        return {
            "query_count": self._query_count,
            "total_bytes_billed": self._total_bytes_billed,
            "total_gb_billed": round(gb_billed, 3),
            "estimated_total_cost_usd": round(total_cost, 4),
        }
    
    def reset_metrics(self) -> None:
        """Reset query execution metrics."""
        self._query_count = 0
        self._total_bytes_billed = 0
    
    @staticmethod
    def _format_bytes(num_bytes: int) -> str:
        """Format bytes into human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(num_bytes) < 1024.0:
                return f"{num_bytes:.2f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.2f} PB"
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - log metrics."""
        metrics = self.get_metrics()
        logger.info(
            f"Session complete: {metrics['query_count']} queries, "
            f"{metrics['total_gb_billed']:.3f} GB billed, "
            f"${metrics['estimated_total_cost_usd']:.4f} estimated"
        )
        return False

