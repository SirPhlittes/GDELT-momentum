"""
GDELT v4.0 Unified Connector
=============================
Single-entry BigQuery connector that replaces all 5 previous implementations.

Provides unified access to GDELT GKG data with:
- Standard query execution
- Entity extraction support
- Source trust filtering
- Geographic data extraction
- Query caching

Author: Philip Hendrik Littau
Version: 4.0.0
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from functools import lru_cache

import pandas as pd
from google.cloud.bigquery import QueryJobConfig

from gdelt_v4.connectors.base import BaseGDELTConnector, QueryError
from gdelt_v4.config.settings import GDELTConfig, get_config
from gdelt_v4.utils.logging import get_logger


logger = get_logger(__name__)


class QueryCache:
    """
    Simple in-memory query cache with TTL support.
    
    Thread-safe implementation using a dictionary with expiration tracking.
    """
    
    def __init__(self, max_size: int = 100, ttl: int = 300):
        self._cache: Dict[str, tuple[pd.DataFrame, float]] = {}
        self.max_size = max_size
        self.ttl = ttl
    
    def _make_key(self, sql: str) -> str:
        """Generate a cache key from SQL."""
        return hashlib.md5(sql.encode()).hexdigest()
    
    def get(self, sql: str) -> Optional[pd.DataFrame]:
        """Get cached result if available and not expired."""
        key = self._make_key(sql)
        if key in self._cache:
            df, timestamp = self._cache[key]
            if (datetime.now().timestamp() - timestamp) < self.ttl:
                logger.debug(f"Cache hit for query (key={key[:8]}...)")
                return df.copy()
            else:
                # Expired
                del self._cache[key]
        return None
    
    def set(self, sql: str, df: pd.DataFrame) -> None:
        """Cache a query result."""
        key = self._make_key(sql)
        
        # Evict oldest entries if cache is full
        while len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
        
        self._cache[key] = (df.copy(), datetime.now().timestamp())
        logger.debug(f"Cached query result (key={key[:8]}..., rows={len(df)})")
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        logger.debug("Query cache cleared")
    
    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
        }


class UnifiedConnector(BaseGDELTConnector):
    """
    Unified BigQuery connector for GDELT v4.0.
    
    This connector replaces:
    - BigQueryConnector (gdeltquery.py)
    - GDELTConnector (gdelt_engine.py)
    - GDELTEntityConnector (gdelt_entity_engine.py)
    - SourceTrustConnector (source_trust.py)
    - MapIntelligenceConnector (map_intelligence.py)
    
    Features:
    - Unified query execution with caching
    - Automatic partition filtering
    - Entity extraction helpers
    - Source trust domain classification
    - Geographic aggregation
    
    Example:
        >>> from gdelt_v4.connectors import UnifiedConnector
        >>> from gdelt_v4.config import GDELTConfig
        >>> 
        >>> config = GDELTConfig.from_env()
        >>> connector = UnifiedConnector(config)
        >>> 
        >>> df = connector.execute_query("SELECT * FROM ...")
        >>> print(connector.get_metrics())
    """
    
    def __init__(self, config: Optional[GDELTConfig] = None):
        """
        Initialize the unified connector.
        
        Args:
            config: Optional GDELTConfig instance.
        """
        super().__init__(config)
        
        # Initialize query cache if enabled
        cache_config = self.config.cache
        if cache_config.enabled:
            self._cache = QueryCache(
                max_size=cache_config.max_size,
                ttl=cache_config.ttl,
            )
        else:
            self._cache = None
    
    def execute_query(
        self,
        sql: str,
        use_cache: bool = True,
        timeout: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Execute a SQL query and return results.
        
        Args:
            sql: The SQL query to execute.
            use_cache: Whether to use query caching.
            timeout: Optional query timeout in seconds.
            
        Returns:
            Query results as a pandas DataFrame.
            
        Raises:
            QueryError: If the query fails.
        """
        # Check cache first
        if use_cache and self._cache:
            cached = self._cache.get(sql)
            if cached is not None:
                return cached
        
        # Execute query
        df = self._execute_sql(sql, timeout=timeout)
        
        # Cache result
        if use_cache and self._cache and not df.empty:
            self._cache.set(sql, df)
        
        return df
    
    def execute_queries(
        self,
        queries: Dict[str, str],
        use_cache: bool = True,
    ) -> Dict[str, pd.DataFrame]:
        """
        Execute multiple queries and return results.
        
        Args:
            queries: Dictionary mapping labels to SQL queries.
            use_cache: Whether to use query caching.
            
        Returns:
            Dictionary mapping labels to result DataFrames.
        """
        results = {}
        for label, sql in queries.items():
            logger.info(f"Executing query for '{label}'...")
            try:
                results[label] = self.execute_query(sql, use_cache=use_cache)
            except QueryError as e:
                logger.error(f"Query failed for '{label}': {e}")
                results[label] = pd.DataFrame()
        
        return results
    
    def fetch_time_series(
        self,
        conditions: str,
        start_date: datetime,
        end_date: datetime,
        sample_percent: Optional[int] = None,
        include_sentiment: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch daily aggregated time series data.
        
        Args:
            conditions: SQL WHERE conditions.
            start_date: Start of date range.
            end_date: End of date range.
            sample_percent: Optional sampling percentage.
            include_sentiment: Whether to include sentiment data.
            
        Returns:
            DataFrame with columns: record_date, mention_count, sentiment_score
        """
        table = self.config.bigquery.full_table_id
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        sample_clause = f"AND RAND() < {sample_percent / 100.0}" if sample_percent else ""
        
        sentiment_cols = ""
        if include_sentiment:
            sentiment_cols = """
                AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS sentiment_score,
                AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(1)] AS FLOAT64)) AS positive_score,
                AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(2)] AS FLOAT64)) AS negative_score,
            """
        
        sql = f"""
        SELECT
            DATE(_PARTITIONTIME) AS record_date,
            COUNT(*) AS mention_count,
            {sentiment_cols}
        FROM `{table}`
        WHERE
            _PARTITIONTIME >= TIMESTAMP('{start_str}')
            AND _PARTITIONTIME < TIMESTAMP(DATE_ADD('{end_str}', INTERVAL 1 DAY))
            AND ({conditions})
            {sample_clause}
        GROUP BY record_date
        ORDER BY record_date
        """
        
        return self.execute_query(sql)
    
    def fetch_geo_data(
        self,
        conditions: str,
        start_date: datetime,
        end_date: datetime,
        sample_percent: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Fetch geographic aggregation data.
        
        Args:
            conditions: SQL WHERE conditions.
            start_date: Start of date range.
            end_date: End of date range.
            sample_percent: Optional sampling percentage.
            
        Returns:
            DataFrame with columns: iso3, mention_count, sentiment_score, latitude, longitude
        """
        table = self.config.bigquery.full_table_id
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        sample_clause = f"AND RAND() < {sample_percent / 100.0}" if sample_percent else ""
        
        sql = f"""
        SELECT
            SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(2)] AS country_code,
            COUNT(*) AS mention_count,
            AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS sentiment_score,
            AVG(SAFE_CAST(SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(5)] AS FLOAT64)) AS latitude,
            AVG(SAFE_CAST(SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(6)] AS FLOAT64)) AS longitude
        FROM `{table}`
        WHERE
            _PARTITIONTIME >= TIMESTAMP('{start_str}')
            AND _PARTITIONTIME < TIMESTAMP(DATE_ADD('{end_str}', INTERVAL 1 DAY))
            AND ({conditions})
            AND V2Locations IS NOT NULL
            AND V2Locations != ''
            {sample_clause}
        GROUP BY country_code
        HAVING country_code IS NOT NULL AND country_code != ''
        ORDER BY mention_count DESC
        """
        
        return self.execute_query(sql)
    
    def fetch_entities(
        self,
        conditions: str,
        start_date: datetime,
        end_date: datetime,
        sample_percent: Optional[int] = None,
        top_n: int = 10,
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch entity data (persons and organizations).
        
        Args:
            conditions: SQL WHERE conditions.
            start_date: Start of date range.
            end_date: End of date range.
            sample_percent: Optional sampling percentage.
            top_n: Number of top entities to return.
            
        Returns:
            Dictionary with 'persons' and 'organizations' DataFrames.
        """
        table = self.config.bigquery.full_table_id
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        sample_clause = f"AND RAND() < {sample_percent / 100.0}" if sample_percent else ""
        
        # Persons query
        persons_sql = f"""
        WITH person_mentions AS (
            SELECT
                TRIM(person) AS entity_name,
                COUNT(*) AS mention_count,
                AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS avg_sentiment
            FROM `{table}`,
            UNNEST(SPLIT(V2Persons, ';')) AS person
            WHERE
                _PARTITIONTIME >= TIMESTAMP('{start_str}')
                AND _PARTITIONTIME < TIMESTAMP(DATE_ADD('{end_str}', INTERVAL 1 DAY))
                AND ({conditions})
                AND V2Persons IS NOT NULL
                {sample_clause}
            GROUP BY entity_name
            HAVING LENGTH(entity_name) > 2
        )
        SELECT * FROM person_mentions
        ORDER BY mention_count DESC
        LIMIT {top_n}
        """
        
        # Organizations query
        orgs_sql = f"""
        WITH org_mentions AS (
            SELECT
                TRIM(org) AS entity_name,
                COUNT(*) AS mention_count,
                AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS avg_sentiment
            FROM `{table}`,
            UNNEST(SPLIT(V2Organizations, ';')) AS org
            WHERE
                _PARTITIONTIME >= TIMESTAMP('{start_str}')
                AND _PARTITIONTIME < TIMESTAMP(DATE_ADD('{end_str}', INTERVAL 1 DAY))
                AND ({conditions})
                AND V2Organizations IS NOT NULL
                {sample_clause}
            GROUP BY entity_name
            HAVING LENGTH(entity_name) > 2
        )
        SELECT * FROM org_mentions
        ORDER BY mention_count DESC
        LIMIT {top_n}
        """
        
        return {
            "persons": self.execute_query(persons_sql),
            "organizations": self.execute_query(orgs_sql),
        }
    
    def fetch_source_trust(
        self,
        conditions: str,
        start_date: datetime,
        end_date: datetime,
        sample_percent: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Fetch source domain data with tier classification.
        
        Args:
            conditions: SQL WHERE conditions.
            start_date: Start of date range.
            end_date: End of date range.
            sample_percent: Optional sampling percentage.
            
        Returns:
            DataFrame with domain, tier, and mention data.
        """
        table = self.config.bigquery.full_table_id
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        sample_clause = f"AND RAND() < {sample_percent / 100.0}" if sample_percent else ""
        
        # Build tier classification CASE statement
        tier1_list = ", ".join(f"'{d}'" for d in self.config.source_trust.tier1_domains)
        tier3_list = ", ".join(f"'{d}'" for d in self.config.source_trust.tier3_domains)
        
        sql = f"""
        SELECT
            NET.REG_DOMAIN(DocumentIdentifier) AS domain,
            CASE
                WHEN NET.REG_DOMAIN(DocumentIdentifier) IN ({tier1_list}) THEN 1
                WHEN NET.REG_DOMAIN(DocumentIdentifier) IN ({tier3_list}) THEN 3
                ELSE 2
            END AS tier,
            COUNT(*) AS mention_count,
            AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS sentiment_score
        FROM `{table}`
        WHERE
            _PARTITIONTIME >= TIMESTAMP('{start_str}')
            AND _PARTITIONTIME < TIMESTAMP(DATE_ADD('{end_str}', INTERVAL 1 DAY))
            AND ({conditions})
            AND DocumentIdentifier IS NOT NULL
            {sample_clause}
        GROUP BY domain, tier
        HAVING domain IS NOT NULL
        ORDER BY mention_count DESC
        """
        
        return self.execute_query(sql)
    
    def clear_cache(self) -> None:
        """Clear the query cache."""
        if self._cache:
            self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self._cache:
            return self._cache.stats()
        return {"enabled": False}

