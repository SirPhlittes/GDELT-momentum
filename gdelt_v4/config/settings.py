"""
GDELT v4.0 Configuration Module
================================
Centralized, type-safe configuration management using Pydantic.

Supports:
- Environment variables (GDELT_* prefix)
- Configuration files (.env, config.yaml)
- Programmatic overrides

Environment Variables:
    GDELT_PROJECT_ID: GCP project for BigQuery jobs (default: user's project)
    GDELT_DATA_PROJECT: GDELT data project (default: gdelt-bq)
    GDELT_DATASET: Dataset name (default: gdeltv2)
    GDELT_TABLE: Table name (default: gkg_partitioned)
    GDELT_CREDENTIALS_PATH: Path to service account JSON
    GDELT_CACHE_TTL: Cache TTL in seconds (default: 300)
    GDELT_LOG_LEVEL: Logging level (default: INFO)
    GDELT_DEFAULT_SAMPLE_PERCENT: Default sampling percentage (default: 10)

Author: Philip Hendrik Littau
Version: 4.0.0
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import logging


class LogLevel(Enum):
    """Logging level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class BigQueryConfig:
    """
    BigQuery-specific configuration.
    
    Attributes:
        data_project: The GCP project containing GDELT data (gdelt-bq).
        job_project: The GCP project for running BigQuery jobs (user's project).
        dataset: The BigQuery dataset name.
        table: The main GKG table name.
        credentials_path: Optional path to service account JSON.
        location: BigQuery job location.
        max_retries: Maximum retry attempts for failed queries.
        retry_delay: Initial delay between retries (exponential backoff).
        timeout: Query timeout in seconds.
    """
    data_project: str = "gdelt-bq"
    job_project: Optional[str] = None  # Will be resolved from credentials
    dataset: str = "gdeltv2"
    table: str = "gkg_partitioned"
    credentials_path: Optional[str] = None
    location: str = "US"
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 300
    
    @property
    def full_table_id(self) -> str:
        """Return the fully qualified table ID."""
        return f"{self.data_project}.{self.dataset}.{self.table}"
    
    def __post_init__(self):
        """Resolve job_project from credentials if not specified."""
        if self.job_project is None and self.credentials_path:
            try:
                with open(self.credentials_path, 'r') as f:
                    creds = json.load(f)
                    self.job_project = creds.get('project_id')
            except (FileNotFoundError, json.JSONDecodeError):
                pass


@dataclass
class CacheConfig:
    """
    Caching configuration.
    
    Attributes:
        enabled: Whether caching is enabled.
        ttl: Time-to-live in seconds.
        max_size: Maximum number of cached items.
        backend: Cache backend type (memory, redis, disk).
    """
    enabled: bool = True
    ttl: int = 300  # 5 minutes
    max_size: int = 100
    backend: str = "memory"


@dataclass
class LogConfig:
    """
    Logging configuration.
    
    Attributes:
        level: Logging level.
        format: Log message format.
        date_format: Date format for log messages.
        log_file: Optional path to log file.
        json_format: Whether to output JSON-formatted logs.
    """
    level: str = "INFO"
    format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    log_file: Optional[str] = None
    json_format: bool = False


@dataclass
class QueryDefaults:
    """
    Default query parameters.
    
    Attributes:
        sample_percent: Default sampling percentage (1-100).
        default_days: Default number of days for date range.
        max_results: Maximum number of results to return.
        include_geo: Whether to include geographic data by default.
        include_entities: Whether to include entity extraction by default.
        include_source_trust: Whether to include source trust by default.
    """
    sample_percent: int = 10
    default_days: int = 7
    max_results: int = 10000
    include_geo: bool = True
    include_entities: bool = False
    include_source_trust: bool = False


@dataclass
class SourceTrustConfig:
    """
    Source trust tier configuration.
    
    Attributes:
        tier1_domains: List of Tier 1 (verified) domains.
        tier3_domains: List of Tier 3 (unverified) domains.
        custom_tiers: Custom domain-to-tier mappings.
    """
    tier1_domains: List[str] = field(default_factory=list)
    tier3_domains: List[str] = field(default_factory=list)
    custom_tiers: Dict[str, int] = field(default_factory=dict)
    
    def __post_init__(self):
        """Load default tier domains if not provided."""
        if not self.tier1_domains:
            self.tier1_domains = [
                # Wire Services
                "reuters.com", "apnews.com", "afp.com",
                # US Quality Press
                "nytimes.com", "washingtonpost.com", "wsj.com",
                # UK Quality Press
                "bbc.com", "bbc.co.uk", "theguardian.com", "ft.com",
                # European Press
                "lemonde.fr", "spiegel.de", "zeit.de",
                # International
                "aljazeera.com", "cnn.com", "bloomberg.com",
            ]
        
        if not self.tier3_domains:
            self.tier3_domains = [
                # Content Mills
                "beforeitsnews.com", "naturalnews.com", "infowars.com",
                # State-Sponsored
                "rt.com", "sputniknews.com", "globaltimes.cn",
                # Hyper-Partisan
                "breitbart.com", "dailykos.com",
            ]


@dataclass
class GDELTConfig:
    """
    Master configuration for GDELT v4.0.
    
    This is the single source of truth for all configuration settings.
    Supports loading from environment variables, config files, or programmatic overrides.
    
    Attributes:
        bigquery: BigQuery-specific configuration.
        cache: Caching configuration.
        logging: Logging configuration.
        query_defaults: Default query parameters.
        source_trust: Source trust tier configuration.
    
    Example:
        >>> config = GDELTConfig.from_env()
        >>> config = GDELTConfig.from_file("config.yaml")
        >>> config = GDELTConfig(
        ...     bigquery=BigQueryConfig(credentials_path="/path/to/creds.json"),
        ...     cache=CacheConfig(ttl=600),
        ... )
    """
    bigquery: BigQueryConfig = field(default_factory=BigQueryConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LogConfig = field(default_factory=LogConfig)
    query_defaults: QueryDefaults = field(default_factory=QueryDefaults)
    source_trust: SourceTrustConfig = field(default_factory=SourceTrustConfig)
    
    @classmethod
    def from_env(cls) -> "GDELTConfig":
        """
        Create configuration from environment variables.
        
        Looks for GDELT_* prefixed environment variables.
        
        Returns:
            GDELTConfig instance populated from environment.
        """
        # BigQuery settings
        bq_config = BigQueryConfig(
            data_project=os.getenv("GDELT_DATA_PROJECT", "gdelt-bq"),
            job_project=os.getenv("GDELT_PROJECT_ID"),
            dataset=os.getenv("GDELT_DATASET", "gdeltv2"),
            table=os.getenv("GDELT_TABLE", "gkg_partitioned"),
            credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            max_retries=int(os.getenv("GDELT_MAX_RETRIES", "3")),
            timeout=int(os.getenv("GDELT_TIMEOUT", "300")),
        )
        
        # Cache settings
        cache_config = CacheConfig(
            enabled=os.getenv("GDELT_CACHE_ENABLED", "true").lower() == "true",
            ttl=int(os.getenv("GDELT_CACHE_TTL", "300")),
        )
        
        # Logging settings
        log_config = LogConfig(
            level=os.getenv("GDELT_LOG_LEVEL", "INFO"),
            log_file=os.getenv("GDELT_LOG_FILE"),
        )
        
        # Query defaults
        query_config = QueryDefaults(
            sample_percent=int(os.getenv("GDELT_DEFAULT_SAMPLE_PERCENT", "10")),
            default_days=int(os.getenv("GDELT_DEFAULT_DAYS", "7")),
        )
        
        return cls(
            bigquery=bq_config,
            cache=cache_config,
            logging=log_config,
            query_defaults=query_config,
        )
    
    @classmethod
    def from_file(cls, path: str) -> "GDELTConfig":
        """
        Create configuration from a YAML or JSON file.
        
        Args:
            path: Path to the configuration file.
            
        Returns:
            GDELTConfig instance populated from file.
            
        Raises:
            FileNotFoundError: If the config file doesn't exist.
            ValueError: If the file format is not supported.
        """
        config_path = Path(path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(config_path, 'r') as f:
            if config_path.suffix in ('.yaml', '.yml'):
                try:
                    import yaml
                    data = yaml.safe_load(f)
                except ImportError:
                    raise ImportError("PyYAML is required for YAML config files")
            elif config_path.suffix == '.json':
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {config_path.suffix}")
        
        return cls._from_dict(data)
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "GDELTConfig":
        """Create configuration from a dictionary."""
        bq_data = data.get("bigquery", {})
        cache_data = data.get("cache", {})
        log_data = data.get("logging", {})
        query_data = data.get("query_defaults", {})
        trust_data = data.get("source_trust", {})
        
        return cls(
            bigquery=BigQueryConfig(**bq_data) if bq_data else BigQueryConfig(),
            cache=CacheConfig(**cache_data) if cache_data else CacheConfig(),
            logging=LogConfig(**log_data) if log_data else LogConfig(),
            query_defaults=QueryDefaults(**query_data) if query_data else QueryDefaults(),
            source_trust=SourceTrustConfig(**trust_data) if trust_data else SourceTrustConfig(),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to a dictionary.
        
        Returns:
            Dictionary representation of the configuration.
        """
        import dataclasses
        
        def _asdict_recursive(obj):
            if dataclasses.is_dataclass(obj):
                return {k: _asdict_recursive(v) for k, v in dataclasses.asdict(obj).items()}
            elif isinstance(obj, list):
                return [_asdict_recursive(v) for v in obj]
            elif isinstance(obj, dict):
                return {k: _asdict_recursive(v) for k, v in obj.items()}
            else:
                return obj
        
        return _asdict_recursive(self)
    
    def validate(self) -> List[str]:
        """
        Validate the configuration.
        
        Returns:
            List of validation error messages. Empty if valid.
        """
        errors = []
        
        # Validate sample_percent
        if not 1 <= self.query_defaults.sample_percent <= 100:
            errors.append(
                f"sample_percent must be between 1 and 100, "
                f"got {self.query_defaults.sample_percent}"
            )
        
        # Validate credentials path exists if specified
        if self.bigquery.credentials_path:
            if not Path(self.bigquery.credentials_path).exists():
                errors.append(
                    f"Credentials file not found: {self.bigquery.credentials_path}"
                )
        
        # Validate cache TTL
        if self.cache.ttl < 0:
            errors.append(f"Cache TTL must be non-negative, got {self.cache.ttl}")
        
        return errors


# Singleton instance for global access
_config_instance: Optional[GDELTConfig] = None


def get_config() -> GDELTConfig:
    """
    Get the global configuration instance.
    
    Creates a new instance from environment variables if not already initialized.
    
    Returns:
        The global GDELTConfig instance.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = GDELTConfig.from_env()
    return _config_instance


def set_config(config: GDELTConfig) -> None:
    """
    Set the global configuration instance.
    
    Args:
        config: The GDELTConfig instance to use globally.
    """
    global _config_instance
    _config_instance = config


def reset_config() -> None:
    """Reset the global configuration instance."""
    global _config_instance
    _config_instance = None


