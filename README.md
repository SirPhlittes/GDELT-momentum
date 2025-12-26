# GDELT Momentum Engine v4.0

🌐 **A modular, scalable Python framework for geopolitical intelligence analysis using GDELT's Global Knowledge Graph (GKG)**

[![Version](https://img.shields.io/badge/version-4.0.0-blue.svg)](https://github.com/yourusername/gdelt-momentum-engine)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

---

## 🚀 What's New in v4.0

**Complete architectural refactoring** from monolithic scripts to a modular, production-ready framework:

- ✅ **Unified BigQuery Connector** - Single entry point replacing 5 redundant implementations
- ✅ **Fixed Boolean Query Parser** - Correct AND/OR/NOT logic with multi-conditional SQL
- ✅ **Multi-Mode Momentum Engine** - Basic, Sentiment-Weighted, Entity-Level, Tier-Specific
- ✅ **Standardized Data Models** - Consistent field naming (`iso3`, `mention_count`, `sentiment_score`)
- ✅ **Service Facade Pattern** - Clean API for dashboards and applications
- ✅ **Centralized Configuration** - Environment variables and config file support
- ✅ **Unified Dashboard** - Multi-tab Streamlit app (Intelligence, Entities, Integrity, Map)
- ✅ **Country Code Mapping** - FIPS→ISO-3 conversion for Plotly compatibility
- ✅ **Retry Logic & Caching** - Robust error handling with exponential backoff
- ✅ **Type Safety** - Full type hints and Google-style docstrings

---

## 📋 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [API Reference](#-api-reference)
- [Configuration](#-configuration)
- [Examples](#-examples)
- [Cost Optimization](#-cost-optimization)
- [License](#-license)

---

## ✨ Features

### Core Capabilities

- **🔍 Boolean Query Builder**: Complex queries with AND, OR, NOT operators
- **📊 Momentum Calculation**: Z-Score normalized momentum for trend detection
- **🌍 Geographic Analysis**: Country-level aggregation with ISO-3 mapping
- **👤 Entity Extraction**: Person and organization extraction with Share of Voice
- **🛡️ Source Trust Analysis**: 3-Tier credibility classification (Verified/General/Unverified)
- **📈 Time Series Analysis**: Daily aggregation with sentiment weighting
- **🗺️ Interactive Maps**: Layer-based visualization (Momentum, Sentiment, Conflict, Entity)

### Technical Features

- **Modular Architecture**: Separated concerns (connectors, engines, models, services)
- **Cost Optimized**: `_PARTITIONTIME` filtering and query sampling
- **Caching**: In-memory query result caching with TTL
- **Error Handling**: Retry logic with exponential backoff
- **Type Safety**: Full type hints and validation
- **Performance**: Optimized SQL templates and batch queries

---

## 📦 Installation

### Prerequisites

- Python 3.8+
- Google Cloud Project with BigQuery access
- GDELT data access (public `gdelt-bq` project)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Required Packages

```
google-cloud-bigquery>=3.11.0
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.18.0
streamlit>=1.28.0
db-dtypes>=1.2.0
```

---

## 🔐 Authentication

Set up Google Cloud credentials:

### Option 1: Service Account (Recommended)

```bash
# Windows
set GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# Linux/Mac
export GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

### Option 2: Application Default Credentials

```bash
gcloud auth application-default login
```

**Required Permissions:**
- `BigQuery Job User` (to run queries)
- `BigQuery Data Viewer` (to read GDELT data)

---

## 🚀 Quick Start

### Basic Analysis

```python
from gdelt_v4 import GDELTService, BaseExperiment

# Initialize service
service = GDELTService()

# Create experiment
experiment = BaseExperiment.create(
    label="China Trade",
    boolean_string="(CHINA OR BEIJING) AND (TRADE OR TARIFF)",
    days=7,
    sample_percent=10,
)

# Run analysis
result = service.analyze(experiment, include_geo=True)

# View results
print(result.summary())
print(result.time_series.df.head())
print(result.geo_data.df.head())
```

### Quick Analysis Function

```python
from gdelt_v4 import quick_analyze

# One-liner analysis
result = quick_analyze(
    label="AI News",
    boolean_string="ARTIFICIAL_INTELLIGENCE OR MACHINE_LEARNING",
    days=7,
    sample_percent=10,
)

print(result.summary())
```

### Entity Extraction

```python
from gdelt_v4 import GDELTService, BaseExperiment, AnalysisMode

service = GDELTService()

experiment = BaseExperiment.create(
    label="Energy Companies",
    boolean_string="ENERGY AND (SHELL OR EXXON OR BP)",
    days=7,
    mode=AnalysisMode.ENTITIES,  # Enable entity extraction
)

result = service.analyze(experiment, include_entities=True)

# View top entities
print(result.entities.top_persons(5))
print(result.entities.top_organizations(5))
```

### Source Trust Analysis

```python
experiment = BaseExperiment.create(
    label="Climate Summit",
    boolean_string="CLIMATE AND (SUMMIT OR COP)",
    days=7,
    mode=AnalysisMode.SOURCE_TRUST,
)

result = service.analyze(experiment, include_source_trust=True)

# View integrity metrics
print(result.integrity)
print(result.source_trust.tier_summary)
```

### Run Dashboard

```bash
streamlit run gdelt_v4/app/unified_dashboard.py
```

Open http://localhost:8501 in your browser.

---

## 🏗️ Architecture

### Directory Structure

```
gdelt_v4/
├── config/           # Configuration management
│   └── settings.py   # GDELTConfig (Pydantic-based)
├── connectors/       # BigQuery connectors
│   ├── base.py       # BaseGDELTConnector (abstract)
│   └── unified.py    # UnifiedConnector (single entry point)
├── query/            # Query building
│   ├── builder.py    # UnifiedQueryBuilder
│   ├── parser.py     # BooleanParser (fixed AND logic)
│   └── templates.py  # SQL templates
├── engines/          # Momentum calculation
│   └── momentum.py   # UnifiedMomentumEngine (4 modes)
├── models/           # Data models
│   ├── experiment.py # BaseExperiment, ExperimentConfig
│   └── result.py     # UnifiedResult, TimeSeriesData, etc.
├── mapping/          # Geographic utilities
│   └── country_codes.py  # FIPS→ISO-3 conversion
├── services/         # Service layer
│   └── gdelt_service.py  # GDELTService facade
├── utils/            # Utilities
│   ├── logging.py    # Centralized logging
│   └── validators.py # Input validation
└── app/              # Streamlit dashboard
    └── unified_dashboard.py
```

### Component Overview

| Component | Purpose | Replaces |
|-----------|---------|----------|
| `UnifiedConnector` | Single BigQuery client | 5 previous connectors |
| `UnifiedQueryBuilder` | SQL generation | 3 previous builders |
| `BooleanParser` | Query parsing | 3 previous parsers |
| `UnifiedMomentumEngine` | Momentum calculation | 3 previous engines |
| `GDELTService` | Service facade | Direct BigQuery access |
| `BaseExperiment` | Experiment config | 4 previous experiment classes |
| `UnifiedResult` | Standardized output | Inconsistent result formats |

---

## 📚 API Reference

### GDELTService

Main service facade for all GDELT operations.

```python
from gdelt_v4 import GDELTService

service = GDELTService(config=None, momentum_window=7, momentum_mode=MomentumMode.BASIC)

# Analyze single experiment
result = service.analyze(
    experiment: BaseExperiment,
    include_geo: bool = True,
    include_entities: bool = False,
    include_source_trust: bool = False,
    calculate_momentum: bool = True,
) -> UnifiedResult

# Analyze multiple experiments
results = service.analyze_batch(
    experiments: List[BaseExperiment],
    include_geo: bool = True,
    include_entities: bool = False,
    include_source_trust: bool = False,
) -> Dict[str, UnifiedResult]

# Fetch layer data for maps
df = service.fetch_layer_data(
    experiment: BaseExperiment,
    layer_type: str,  # "momentum", "sentiment", "conflict", "entity"
) -> pd.DataFrame

# Estimate query cost
cost = service.estimate_cost(experiment, query_type="time_series") -> Dict[str, Any]

# Get service metrics
metrics = service.get_metrics() -> Dict[str, Any]
```

### BaseExperiment

Unified experiment configuration.

```python
from gdelt_v4 import BaseExperiment, AnalysisMode

experiment = BaseExperiment(
    label: str,
    boolean_string: str,
    start_date: datetime,
    end_date: datetime,
    search_fields: List[str] = ["V2Themes", "AllNames", "V2Organizations"],
    sample_percent: Optional[int] = None,
    mode: AnalysisMode = AnalysisMode.BASIC,
    color: Optional[str] = None,
    entity_filter: Optional[List[str]] = None,
    metadata: Dict[str, Any] = {},
)

# Factory method
experiment = BaseExperiment.create(
    label="My Query",
    boolean_string="CHINA AND TRADE",
    days=7,
    sample_percent=10,
    mode="entities",
)
```

### UnifiedResult

Standardized result container.

```python
result = UnifiedResult(
    time_series: TimeSeriesData,
    geo_data: GeoData,
    entities: Optional[EntityData] = None,
    source_trust: Optional[SourceTrustData] = None,
    integrity: Optional[IntegrityMetrics] = None,
    experiments: List[Dict[str, Any]] = [],
    metadata: Dict[str, Any] = {},
)

# Access data
result.time_series.df          # Time series DataFrame
result.geo_data.df              # Geographic DataFrame
result.entities.persons         # Person entities DataFrame
result.entities.organizations    # Organization entities DataFrame
result.source_trust.df          # Source trust DataFrame
result.integrity                # IntegrityMetrics object

# Get summary
summary = result.summary()      # Dict with summary statistics
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# BigQuery settings
GDELT_PROJECT_ID=your-project-id          # Your GCP project for jobs
GDELT_DATA_PROJECT=gdelt-bq               # GDELT data project (default)
GDELT_DATASET=gdeltv2                     # Dataset name (default)
GDELT_TABLE=gkg_partitioned                # Table name (default)
GOOGLE_APPLICATION_CREDENTIALS=path/to/creds.json

# Performance
GDELT_CACHE_ENABLED=true                   # Enable query caching
GDELT_CACHE_TTL=300                       # Cache TTL in seconds
GDELT_DEFAULT_SAMPLE_PERCENT=10           # Default sampling percentage

# Logging
GDELT_LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR
GDELT_LOG_FILE=gdelt.log                  # Optional log file
```

### Programmatic Configuration

```python
from gdelt_v4 import GDELTConfig, BigQueryConfig, CacheConfig

config = GDELTConfig(
    bigquery=BigQueryConfig(
        data_project="gdelt-bq",
        job_project="your-project-id",
        credentials_path="path/to/creds.json",
        max_retries=3,
    ),
    cache=CacheConfig(
        enabled=True,
        ttl=300,
        max_size=100,
    ),
    query_defaults=QueryDefaults(
        sample_percent=10,
        default_days=7,
    ),
)

# Use global config
from gdelt_v4 import set_config
set_config(config)
```

---

## 📊 Examples

### Multi-Experiment Comparison

```python
from gdelt_v4 import GDELTService, BaseExperiment, ExperimentConfig

service = GDELTService()

experiments = [
    BaseExperiment.create("China Trade", "(CHINA OR BEIJING) AND TRADE", days=7),
    BaseExperiment.create("Russia Energy", "(RUSSIA OR MOSCOW) AND ENERGY", days=7),
    BaseExperiment.create("US Tech", "(USA OR AMERICA) AND TECHNOLOGY", days=7),
]

config = ExperimentConfig(experiments=experiments)
result = service.analyze_combined(config)

# Compare experiments
for label in result.time_series.experiments:
    exp_data = result.time_series.filter_by_experiment(label)
    print(f"{label}: {exp_data['mention_count'].sum()} mentions")
```

### Map Layer Visualization

```python
# Fetch momentum layer
momentum_df = service.fetch_layer_data(experiment, layer_type="momentum")

# Fetch sentiment layer
sentiment_df = service.fetch_layer_data(experiment, layer_type="sentiment")

# Fetch conflict layer
conflict_df = service.fetch_layer_data(experiment, layer_type="conflict")

# Fetch entity layer
entity_df = service.fetch_layer_data(experiment, layer_type="entity")
```

### Cost Estimation

```python
# Estimate before running
cost = service.estimate_cost(experiment, query_type="time_series")
print(f"Estimated cost: ${cost['estimated_cost_usd']:.4f}")
print(f"Data to scan: {cost['estimated_gb']:.3f} GB")

# Or use connector directly
from gdelt_v4 import UnifiedConnector
connector = UnifiedConnector()
cost = connector.dry_run(sql_query)
```

---

## 💰 Cost Optimization

### Best Practices

1. **Use Partition Filtering**: Always specify date ranges
2. **Enable Sampling**: Use `sample_percent=10` for exploration
3. **Cache Results**: Enable caching for repeated queries
4. **Batch Queries**: Use `analyze_combined()` for multiple experiments
5. **Estimate First**: Use `estimate_cost()` before large queries

### Cost Estimation

```python
# Dry run before execution
cost = service.estimate_cost(experiment)
if cost['estimated_cost_usd'] > 1.0:
    print("⚠️ High cost query! Consider sampling.")
```

### Query Metrics

```python
# Get session metrics
metrics = service.get_metrics()
print(f"Queries executed: {metrics['connector']['query_count']}")
print(f"Total cost: ${metrics['connector']['estimated_total_cost_usd']:.4f}")
```

---

## 📈 Momentum Formula

The momentum metric uses Z-Score normalization:

$$Z = \frac{x - \mu}{\sigma}$$

Where:
- **x** = Current value (volume, sentiment, etc.)
- **μ** = Rolling mean over window period
- **σ** = Rolling standard deviation

### Momentum Modes

1. **BASIC**: Standard Z-score
2. **SENTIMENT_WEIGHTED**: Z-score weighted by sentiment intensity
3. **ENTITY_LEVEL**: Share of Voice for entities
4. **TIER_SPECIFIC**: Momentum by source credibility tier

### Momentum Classification

| Z-Score | Status | Description |
|---------|--------|-------------|
| ≥ 2.0 | SURGE | Significant positive deviation |
| 1.0 - 2.0 | RISING | Moderate positive trend |
| -1.0 - 1.0 | STABLE | Normal variation |
| -2.0 - -1.0 | FALLING | Moderate negative trend |
| ≤ -2.0 | CRASH | Significant negative deviation |

---

## 🗺️ Standardized Field Names

v4.0 uses consistent field naming across all outputs:

| Standard Name | Old Names (deprecated) | Description |
|---------------|------------------------|-------------|
| `iso3` | `country_code`, `fips`, `geo_country_code` | ISO-3 country code |
| `mention_count` | `volume`, `daily_volume`, `mentions` | Number of mentions |
| `sentiment_score` | `avg_tone`, `sentiment`, `tone` | Average sentiment (-10 to +10) |
| `momentum_zscore` | `momentum`, `z_score`, `zscore` | Z-score momentum |
| `record_date` | `date`, `day` | Record date |
| `experiment_label` | `label` | Experiment identifier |

---

## 🛠️ Development

### Project Structure

The v4.0 codebase is organized into clear modules:

- **config/**: Configuration management
- **connectors/**: BigQuery integration
- **query/**: SQL generation and parsing
- **engines/**: Momentum calculation
- **models/**: Data models and schemas
- **mapping/**: Geographic utilities
- **services/**: Service facade layer
- **utils/**: Shared utilities
- **app/**: Streamlit dashboard

### Adding New Features

1. **New Query Type**: Add template to `query/templates.py`
2. **New Momentum Mode**: Extend `engines/momentum.py`
3. **New Data Model**: Add to `models/result.py`
4. **New Dashboard Tab**: Extend `app/unified_dashboard.py`

---

## 📝 License

MIT License - see LICENSE file for details

---

## 👤 Author

**Philip Hendrik Littau**

---

## 🙏 Acknowledgments

- GDELT Project for providing the Global Knowledge Graph
- Google BigQuery for scalable data processing
- Streamlit and Plotly for visualization capabilities

---

## 📞 Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Version**: 4.0.0  
**Last Updated**: December 2025
