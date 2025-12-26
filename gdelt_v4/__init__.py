"""
GDELT Momentum Engine v4.4
==========================
A modular, scalable Python framework for geopolitical intelligence analysis.

This package provides:
- Unified BigQuery connector with retry logic and caching
- Flexible query builder supporting Boolean logic, entities, and source trust
- Multi-mode momentum engine (Basic, Sentiment-Weighted, Entity-Level)
- Standardized data models with consistent field naming
- Service facade for clean dashboard integration
- v4.4: Multidimensional analysis (Bivariate Crisis Map, Conflict Hubs)

Author: Philip Hendrik Littau
Version: 4.4.0
License: MIT
"""

__version__ = "4.4.0"
__author__ = "Philip Hendrik Littau"

# Configuration
from gdelt_v4.config.settings import (
    GDELTConfig,
    BigQueryConfig,
    CacheConfig,
    LogConfig,
    get_config,
    set_config,
)

# Connectors
from gdelt_v4.connectors.base import BaseGDELTConnector
from gdelt_v4.connectors.unified import UnifiedConnector

# Query Building
from gdelt_v4.query.builder import UnifiedQueryBuilder
from gdelt_v4.query.parser import BooleanParser, parse_boolean_query

# Engines
from gdelt_v4.engines.momentum import UnifiedMomentumEngine, MomentumMode

# Models
from gdelt_v4.models.experiment import BaseExperiment, ExperimentConfig, AnalysisMode
from gdelt_v4.models.result import UnifiedResult, TimeSeriesData, GeoData, EntityData

# Mapping
from gdelt_v4.mapping.country_codes import CountryCodeMapper, FIPS_TO_ISO3

# Services
from gdelt_v4.services.gdelt_service import GDELTService, quick_analyze

# Public API
__all__ = [
    # Version
    "__version__",
    "__author__",
    # Config
    "GDELTConfig",
    "BigQueryConfig",
    "CacheConfig",
    "LogConfig",
    "get_config",
    "set_config",
    # Connectors
    "BaseGDELTConnector",
    "UnifiedConnector",
    # Query
    "UnifiedQueryBuilder",
    "BooleanParser",
    "parse_boolean_query",
    # Engines
    "UnifiedMomentumEngine",
    "MomentumMode",
    # Models
    "BaseExperiment",
    "ExperimentConfig",
    "AnalysisMode",
    "UnifiedResult",
    "TimeSeriesData",
    "GeoData",
    "EntityData",
    # Mapping
    "CountryCodeMapper",
    "FIPS_TO_ISO3",
    # Services
    "GDELTService",
    "quick_analyze",
]

