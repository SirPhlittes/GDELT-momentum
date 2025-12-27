"""
GDELT v4.0 Result Models
=========================
Unified result dataclasses with standardized field naming.

Field naming conventions:
- iso3: ISO-3 country code (not country_code or fips)
- mention_count: Volume of mentions (not volume or daily_volume)
- sentiment_score: Average sentiment (not avg_tone or sentiment)
- momentum_zscore: Z-score momentum (not momentum or z_score)
- record_date: Date of record (not date or day)

Author: Philip Hendrik Littau
Version: 4.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any

import pandas as pd


@dataclass
class TimeSeriesData:
    """
    Time series data with standardized columns.
    
    Required columns:
    - record_date: datetime
    - experiment_label: str
    - mention_count: int
    - sentiment_score: float
    
    Optional columns:
    - momentum_zscore: float
    - positive_score: float
    - negative_score: float
    """
    df: pd.DataFrame
    
    def __post_init__(self):
        """Validate and standardize column names."""
        self._standardize_columns()
    
    def _standardize_columns(self):
        """Rename columns to standard names, avoiding duplicates."""
        column_map = {
            "date": "record_date",
            "day": "record_date",
            "volume": "mention_count",
            "daily_volume": "mention_count",
            "mentions": "mention_count",
            "sentiment": "sentiment_score",
            "avg_tone": "sentiment_score",
            "tone": "sentiment_score",
            "momentum": "momentum_zscore",
            "z_score": "momentum_zscore",
            "zscore": "momentum_zscore",
            "label": "experiment_label",
        }
        
        # Only rename if target column doesn't already exist
        filtered_map = {
            old: new for old, new in column_map.items()
            if old in self.df.columns and new not in self.df.columns
        }
        
        # Drop source columns if target already exists
        cols_to_drop = [
            old for old, new in column_map.items()
            if old in self.df.columns and new in self.df.columns and old != new
        ]
        if cols_to_drop:
            self.df = self.df.drop(columns=cols_to_drop)
        
        self.df = self.df.rename(columns=filtered_map)
    
    @property
    def experiments(self) -> List[str]:
        """Get list of unique experiment labels."""
        if "experiment_label" in self.df.columns:
            return self.df["experiment_label"].unique().tolist()
        return []
    
    def filter_by_experiment(self, label: str) -> pd.DataFrame:
        """Get data for a specific experiment."""
        if "experiment_label" in self.df.columns:
            return self.df[self.df["experiment_label"] == label]
        return self.df
    
    def to_long_format(self) -> pd.DataFrame:
        """Return data in long format for Plotly."""
        return self.df.copy()


@dataclass
class GeoData:
    """
    Geographic aggregation data with standardized columns.
    
    Required columns:
    - iso3: str (ISO-3 country code)
    - mention_count: int
    
    Optional columns:
    - sentiment_score: float
    - momentum_zscore: float
    - latitude: float
    - longitude: float
    - experiment_label: str
    """
    df: pd.DataFrame
    
    def __post_init__(self):
        """Validate and standardize column names."""
        self._standardize_columns()
    
    def _standardize_columns(self):
        """Rename columns to standard names, avoiding duplicates."""
        column_map = {
            "country_code": "iso3",
            "fips": "iso3",
            "country": "iso3",
            "geo_country_code": "iso3",
            "volume": "mention_count",
            "total_volume": "mention_count",
            "mentions": "mention_count",
            "sentiment": "sentiment_score",
            "avg_sentiment": "sentiment_score",
            "avg_tone": "sentiment_score",
            "momentum": "momentum_zscore",
            "z_score": "momentum_zscore",
            "lat": "latitude",
            "lon": "longitude",
            "lng": "longitude",
        }
        
        # Only rename if target column doesn't already exist
        filtered_map = {
            old: new for old, new in column_map.items()
            if old in self.df.columns and new not in self.df.columns
        }
        
        # Drop source columns if target already exists
        cols_to_drop = [
            old for old, new in column_map.items()
            if old in self.df.columns and new in self.df.columns and old != new
        ]
        if cols_to_drop:
            self.df = self.df.drop(columns=cols_to_drop)
        
        self.df = self.df.rename(columns=filtered_map)
    
    def filter_by_country(self, iso3: str) -> pd.DataFrame:
        """Get data for a specific country."""
        if "iso3" in self.df.columns:
            return self.df[self.df["iso3"] == iso3.upper()]
        return pd.DataFrame()
    
    def top_countries(self, n: int = 10) -> pd.DataFrame:
        """Get top N countries by mention count."""
        if "mention_count" in self.df.columns:
            return self.df.nlargest(n, "mention_count")
        return self.df.head(n)


@dataclass
class EntityData:
    """
    Entity (person/organization) data with standardized columns.
    
    Required columns:
    - entity_name: str
    - entity_type: str ("person" or "organization")
    - mention_count: int
    
    Optional columns:
    - sentiment_score: float
    - share_of_voice: float
    - momentum_zscore: float
    - experiment_label: str
    """
    persons: pd.DataFrame
    organizations: pd.DataFrame
    
    def __post_init__(self):
        """Add entity_type column to each DataFrame."""
        if not self.persons.empty:
            self.persons = self.persons.copy()
            self.persons["entity_type"] = "person"
            self._standardize_df(self.persons)
        
        if not self.organizations.empty:
            self.organizations = self.organizations.copy()
            self.organizations["entity_type"] = "organization"
            self._standardize_df(self.organizations)
    
    def _standardize_df(self, df: pd.DataFrame):
        """Standardize column names."""
        column_map = {
            "name": "entity_name",
            "person": "entity_name",
            "organization": "entity_name",
            "org": "entity_name",
            "volume": "mention_count",
            "mentions": "mention_count",
            "count": "mention_count",
            "sentiment": "sentiment_score",
            "avg_sentiment": "sentiment_score",
            "sov": "share_of_voice",
            "momentum": "momentum_zscore",
        }
        df.rename(columns=column_map, inplace=True)
    
    @property
    def combined(self) -> pd.DataFrame:
        """Get combined DataFrame of all entities."""
        return pd.concat([self.persons, self.organizations], ignore_index=True)
    
    def top_persons(self, n: int = 5) -> pd.DataFrame:
        """Get top N persons by mention count."""
        if "mention_count" in self.persons.columns:
            return self.persons.nlargest(n, "mention_count")
        return self.persons.head(n)
    
    def top_organizations(self, n: int = 5) -> pd.DataFrame:
        """Get top N organizations by mention count."""
        if "mention_count" in self.organizations.columns:
            return self.organizations.nlargest(n, "mention_count")
        return self.organizations.head(n)


@dataclass
class SourceTrustData:
    """
    Source trust/credibility data.
    
    Required columns:
    - domain: str
    - tier: int (1, 2, or 3)
    - mention_count: int
    
    Optional columns:
    - sentiment_score: float
    - experiment_label: str
    """
    df: pd.DataFrame
    
    def by_tier(self, tier: int) -> pd.DataFrame:
        """Get data for a specific tier."""
        if "tier" in self.df.columns:
            return self.df[self.df["tier"] == tier]
        return pd.DataFrame()
    
    @property
    def tier_summary(self) -> Dict[int, int]:
        """Get total mentions by tier."""
        if "tier" in self.df.columns and "mention_count" in self.df.columns:
            return self.df.groupby("tier")["mention_count"].sum().to_dict()
        return {}


@dataclass
class IntegrityMetrics:
    """
    Source integrity metrics.
    
    Attributes:
        integrity_ratio: Tier1 momentum / Tier3 momentum
        tier1_percentage: Percentage of mentions from Tier 1
        tier3_percentage: Percentage of mentions from Tier 3
        risk_score: Overall risk score (0-1)
        status: Integrity status ("organic", "mixed", "artificial", "propaganda_risk")
    """
    integrity_ratio: float
    tier1_percentage: float
    tier3_percentage: float
    risk_score: float
    status: str
    
    @classmethod
    def calculate(cls, tier_data: Dict[int, int]) -> "IntegrityMetrics":
        """
        Calculate integrity metrics from tier data.
        
        Args:
            tier_data: Dictionary mapping tier (1, 2, 3) to mention count.
            
        Returns:
            IntegrityMetrics instance.
        """
        total = sum(tier_data.values()) or 1
        tier1 = tier_data.get(1, 0)
        tier3 = tier_data.get(3, 0)
        
        tier1_pct = tier1 / total * 100
        tier3_pct = tier3 / total * 100
        
        # Integrity ratio (avoid division by zero)
        ir = tier1 / tier3 if tier3 > 0 else 10.0
        
        # Risk score: higher when tier3 > tier1
        risk = min(1.0, tier3_pct / 100 * (1 / max(ir, 0.1)))
        
        # Status determination
        if ir > 2.0:
            status = "organic"
        elif ir > 0.5:
            status = "mixed"
        elif ir > 0.1:
            status = "artificial"
        else:
            status = "propaganda_risk"
        
        return cls(
            integrity_ratio=round(ir, 3),
            tier1_percentage=round(tier1_pct, 2),
            tier3_percentage=round(tier3_pct, 2),
            risk_score=round(risk, 3),
            status=status,
        )


@dataclass
class UnifiedResult:
    """
    Unified result container for all GDELT analysis output.
    
    Consolidates:
    - Time series data
    - Geographic aggregation
    - Entity extraction
    - Source trust analysis
    - Momentum calculations
    - v4.4: Conflict/protest event data
    
    All DataFrames use standardized column names.
    
    Attributes:
        time_series: Daily aggregated time series.
        geo_data: Geographic country-level aggregation.
        entities: Entity extraction results (optional).
        source_trust: Source credibility data (optional).
        integrity: Integrity metrics (optional).
        experiments: List of experiment configurations.
        metadata: Additional result metadata.
        _conflict_data: v4.4 Conflict events for Conflict Hubs layer.
    """
    time_series: TimeSeriesData
    geo_data: GeoData
    entities: Optional[EntityData] = None
    source_trust: Optional[SourceTrustData] = None
    integrity: Optional[IntegrityMetrics] = None
    experiments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # v4.4: Conflict data for Conflict Hubs layer
    _conflict_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    @property
    def has_entities(self) -> bool:
        """Check if entity data is available."""
        return self.entities is not None
    
    @property
    def has_source_trust(self) -> bool:
        """Check if source trust data is available."""
        return self.source_trust is not None
    
    @property
    def has_conflict_data(self) -> bool:
        """v4.4: Check if conflict data is available."""
        return self._conflict_data is not None and not self._conflict_data.empty
    
    @property
    def conflict_data(self) -> pd.DataFrame:
        """v4.4: Get conflict/protest event data."""
        return self._conflict_data if self._conflict_data is not None else pd.DataFrame()
    
    def summary(self) -> Dict[str, Any]:
        """
        Get a summary of the results.
        
        Returns:
            Dictionary with summary statistics.
        """
        summary = {
            "total_records": len(self.time_series.df),
            "date_range": {
                "start": str(self.time_series.df["record_date"].min()) if "record_date" in self.time_series.df.columns else None,
                "end": str(self.time_series.df["record_date"].max()) if "record_date" in self.time_series.df.columns else None,
            },
            "countries": len(self.geo_data.df),
            "experiments": self.time_series.experiments,
        }
        
        if self.has_entities:
            summary["top_persons"] = len(self.entities.persons)
            summary["top_organizations"] = len(self.entities.organizations)
        
        if self.has_source_trust:
            summary["source_domains"] = len(self.source_trust.df)
            summary["tier_breakdown"] = self.source_trust.tier_summary
        
        if self.integrity:
            summary["integrity_status"] = self.integrity.status
            summary["risk_score"] = self.integrity.risk_score
        
        return summary

