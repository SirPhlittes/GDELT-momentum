"""
GDELT v4.0 Unified Momentum Engine
===================================
Multi-mode momentum calculation engine.

Replaces:
- MomentumEngine (gdeltquery.py)
- MomentumEngine (gdelt_engine.py)
- EntityMomentumEngine (gdelt_entity_engine.py)
- IntegrityCalculator (source_trust.py)

Modes:
- BASIC: Standard rolling Z-score
- SENTIMENT_WEIGHTED: Z-score weighted by sentiment intensity
- ENTITY_LEVEL: Share of Voice and entity Z-scores
- TIER_SPECIFIC: Momentum by source tier

Author: Philip Hendrik Littau
Version: 4.0.0
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Dict, Any, List

import numpy as np
import pandas as pd

from gdelt_v4.utils.logging import get_logger
from gdelt_v4.models.result import (
    TimeSeriesData,
    GeoData,
    EntityData,
    IntegrityMetrics,
)


logger = get_logger(__name__)


class MomentumMode(Enum):
    """Available momentum calculation modes."""
    BASIC = "basic"                    # Standard Z-score
    SENTIMENT_WEIGHTED = "sentiment"   # Sentiment-weighted Z-score
    ENTITY_LEVEL = "entity"            # Entity share of voice
    TIER_SPECIFIC = "tier"             # By source tier


class UnifiedMomentumEngine:
    """
    Unified momentum calculation engine for GDELT v4.0.
    
    Supports multiple calculation modes:
    
    1. BASIC: Standard rolling Z-score
       Z = (x - μ) / σ
       where x = current volume, μ = rolling mean, σ = rolling std
    
    2. SENTIMENT_WEIGHTED: Z-score weighted by sentiment intensity
       Z_weighted = Z * (1 + |sentiment| / 10)
    
    3. ENTITY_LEVEL: Share of Voice for entities
       SoV = entity_mentions / total_mentions * 100
    
    4. TIER_SPECIFIC: Momentum by source credibility tier
       IR = Momentum_Tier1 / Momentum_Tier3
    
    Example:
        >>> engine = UnifiedMomentumEngine(window=7, mode=MomentumMode.BASIC)
        >>> df = engine.calculate(time_series_df)
        >>> print(df[['record_date', 'momentum_zscore']].head())
    """
    
    def __init__(
        self,
        window: int = 7,
        min_periods: int = 3,
        mode: MomentumMode = MomentumMode.BASIC,
        zscore_threshold: float = 2.0,
    ):
        """
        Initialize the momentum engine.
        
        Args:
            window: Rolling window size in days.
            min_periods: Minimum periods for valid calculation.
            mode: Calculation mode.
            zscore_threshold: Threshold for significant momentum.
        """
        self.window = window
        self.min_periods = min_periods
        self.mode = mode
        self.zscore_threshold = zscore_threshold
        
        logger.info(f"Initialized MomentumEngine (mode={mode.value}, window={window})")
    
    def calculate(
        self,
        df: pd.DataFrame,
        value_column: str = "mention_count",
        date_column: str = "record_date",
        group_column: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Calculate momentum for a time series.
        
        Args:
            df: Input DataFrame with time series data.
            value_column: Column containing the metric to calculate momentum for.
            date_column: Column containing dates.
            group_column: Optional column to group by (e.g., experiment_label).
            
        Returns:
            DataFrame with added momentum columns.
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # Ensure proper sorting
        if date_column in df.columns:
            df = df.sort_values(date_column)
        
        if group_column and group_column in df.columns:
            # Calculate momentum per group
            result = df.groupby(group_column, group_keys=False).apply(
                lambda g: self._calculate_single(g, value_column)
            )
            return result.reset_index(drop=True)
        else:
            return self._calculate_single(df, value_column)
    
    def _calculate_single(
        self,
        df: pd.DataFrame,
        value_column: str,
    ) -> pd.DataFrame:
        """Calculate momentum for a single time series."""
        if value_column not in df.columns:
            logger.warning(f"Value column '{value_column}' not found")
            return df
        
        df = df.copy()
        values = df[value_column].fillna(0).astype(float)
        
        # Calculate rolling statistics
        rolling = values.rolling(window=self.window, min_periods=self.min_periods)
        rolling_mean = rolling.mean()
        rolling_std = rolling.std()
        
        # Basic Z-score
        zscore = (values - rolling_mean) / rolling_std.replace(0, np.nan)
        zscore = zscore.fillna(0)
        
        # Apply mode-specific adjustments
        if self.mode == MomentumMode.SENTIMENT_WEIGHTED:
            zscore = self._apply_sentiment_weight(df, zscore)
        
        df["momentum_zscore"] = zscore.round(3)
        df["rolling_mean"] = rolling_mean.round(2)
        df["rolling_std"] = rolling_std.round(2)
        
        # Add momentum classification
        df["momentum_status"] = df["momentum_zscore"].apply(self._classify_momentum)
        
        # Calculate percent change
        df["pct_change"] = values.pct_change().fillna(0).round(4)
        
        return df
    
    def _apply_sentiment_weight(
        self,
        df: pd.DataFrame,
        zscore: pd.Series,
    ) -> pd.Series:
        """Apply sentiment weighting to Z-score."""
        if "sentiment_score" not in df.columns:
            return zscore
        
        sentiment = df["sentiment_score"].fillna(0).abs()
        # Weight: 1 + |sentiment| / 10 (sentiment typically -10 to +10)
        weight = 1 + sentiment / 10
        return zscore * weight
    
    def _classify_momentum(self, zscore: float) -> str:
        """Classify momentum based on Z-score."""
        if zscore >= self.zscore_threshold:
            return "SURGE"
        elif zscore >= 1.0:
            return "RISING"
        elif zscore <= -self.zscore_threshold:
            return "CRASH"
        elif zscore <= -1.0:
            return "FALLING"
        else:
            return "STABLE"
    
    def calculate_geo_momentum(
        self,
        geo_df: pd.DataFrame,
        time_series_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Calculate momentum for geographic data.
        
        If time_series_df is provided, calculates true rolling momentum.
        Otherwise, uses cross-sectional Z-scores.
        
        Args:
            geo_df: Geographic aggregation data.
            time_series_df: Optional time series data for rolling calculation.
            
        Returns:
            DataFrame with momentum scores per country.
        """
        if geo_df.empty:
            return geo_df
        
        geo_df = geo_df.copy()
        
        if "mention_count" in geo_df.columns:
            values = geo_df["mention_count"].fillna(0).astype(float)
            
            # Cross-sectional Z-score
            mean_vol = values.mean()
            std_vol = values.std()
            
            if std_vol > 0:
                geo_df["momentum_zscore"] = ((values - mean_vol) / std_vol).round(3)
            else:
                geo_df["momentum_zscore"] = 0.0
            
            geo_df["momentum_status"] = geo_df["momentum_zscore"].apply(
                self._classify_momentum
            )
        
        return geo_df
    
    def calculate_entity_momentum(
        self,
        entity_data: EntityData,
        baseline_df: Optional[pd.DataFrame] = None,
    ) -> EntityData:
        """
        Calculate Share of Voice and momentum for entities.
        
        Args:
            entity_data: Entity extraction results.
            baseline_df: Optional baseline data for comparison.
            
        Returns:
            EntityData with momentum scores.
        """
        # Calculate SoV for persons
        persons = entity_data.persons.copy()
        if not persons.empty and "mention_count" in persons.columns:
            total = persons["mention_count"].sum()
            persons["share_of_voice"] = (
                persons["mention_count"] / total * 100
            ).round(2)
            persons = self._add_entity_zscore(persons)
        
        # Calculate SoV for organizations
        orgs = entity_data.organizations.copy()
        if not orgs.empty and "mention_count" in orgs.columns:
            total = orgs["mention_count"].sum()
            orgs["share_of_voice"] = (
                orgs["mention_count"] / total * 100
            ).round(2)
            orgs = self._add_entity_zscore(orgs)
        
        return EntityData(persons=persons, organizations=orgs)
    
    def _add_entity_zscore(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Z-score to entity DataFrame."""
        if "mention_count" in df.columns:
            values = df["mention_count"].astype(float)
            mean_val = values.mean()
            std_val = values.std()
            
            if std_val > 0:
                df["momentum_zscore"] = ((values - mean_val) / std_val).round(3)
            else:
                df["momentum_zscore"] = 0.0
        
        return df
    
    def calculate_tier_momentum(
        self,
        tier_df: pd.DataFrame,
    ) -> Dict[int, float]:
        """
        Calculate momentum by source tier.
        
        Args:
            tier_df: DataFrame with tier and mention_count columns.
            
        Returns:
            Dictionary mapping tier to momentum Z-score.
        """
        if tier_df.empty or "tier" not in tier_df.columns:
            return {}
        
        tier_momentum = {}
        
        for tier in [1, 2, 3]:
            tier_data = tier_df[tier_df["tier"] == tier]
            if not tier_data.empty and "mention_count" in tier_data.columns:
                values = tier_data["mention_count"].astype(float)
                if len(values) >= self.min_periods:
                    zscore = (values.iloc[-1] - values.mean()) / (values.std() or 1)
                    tier_momentum[tier] = round(zscore, 3)
                else:
                    tier_momentum[tier] = 0.0
            else:
                tier_momentum[tier] = 0.0
        
        return tier_momentum
    
    def calculate_integrity_ratio(
        self,
        tier_counts: Dict[int, int],
        tier_momentum: Optional[Dict[int, float]] = None,
    ) -> IntegrityMetrics:
        """
        Calculate Integrity Ratio and risk metrics.
        
        IR = Tier1_momentum / Tier3_momentum
        
        Args:
            tier_counts: Dictionary mapping tier to mention count.
            tier_momentum: Optional dictionary of tier Z-scores.
            
        Returns:
            IntegrityMetrics instance.
        """
        return IntegrityMetrics.calculate(tier_counts)
    
    def detect_anomalies(
        self,
        df: pd.DataFrame,
        zscore_column: str = "momentum_zscore",
        threshold: Optional[float] = None,
    ) -> pd.DataFrame:
        """
        Detect anomalous data points.
        
        Args:
            df: DataFrame with momentum scores.
            zscore_column: Column containing Z-scores.
            threshold: Z-score threshold for anomaly detection.
            
        Returns:
            DataFrame of anomalous rows.
        """
        threshold = threshold or self.zscore_threshold
        
        if zscore_column not in df.columns:
            return pd.DataFrame()
        
        anomalies = df[df[zscore_column].abs() >= threshold].copy()
        anomalies["anomaly_type"] = anomalies[zscore_column].apply(
            lambda z: "POSITIVE" if z > 0 else "NEGATIVE"
        )
        
        return anomalies.sort_values(zscore_column, key=abs, ascending=False)
    
    def detect_new_entrants(
        self,
        current_entities: pd.DataFrame,
        baseline_entities: pd.DataFrame,
        name_column: str = "entity_name",
    ) -> pd.DataFrame:
        """
        Detect entities that appeared in current period but not in baseline.
        
        Args:
            current_entities: Current period entity data.
            baseline_entities: Baseline period entity data.
            name_column: Column containing entity names.
            
        Returns:
            DataFrame of new entrant entities.
        """
        if current_entities.empty or name_column not in current_entities.columns:
            return pd.DataFrame()
        
        current_names = set(current_entities[name_column].unique())
        
        if baseline_entities.empty or name_column not in baseline_entities.columns:
            baseline_names = set()
        else:
            baseline_names = set(baseline_entities[name_column].unique())
        
        new_names = current_names - baseline_names
        
        if not new_names:
            return pd.DataFrame()
        
        new_entrants = current_entities[
            current_entities[name_column].isin(new_names)
        ].copy()
        new_entrants["is_new_entrant"] = True
        
        return new_entrants.sort_values("mention_count", ascending=False)
    
    def get_summary_stats(
        self,
        df: pd.DataFrame,
        value_column: str = "mention_count",
    ) -> Dict[str, Any]:
        """
        Get summary statistics for a time series.
        
        Args:
            df: Input DataFrame.
            value_column: Column to summarize.
            
        Returns:
            Dictionary of summary statistics.
        """
        if df.empty or value_column not in df.columns:
            return {}
        
        values = df[value_column].fillna(0)
        
        stats = {
            "count": len(values),
            "sum": int(values.sum()),
            "mean": round(values.mean(), 2),
            "std": round(values.std(), 2),
            "min": int(values.min()),
            "max": int(values.max()),
            "median": round(values.median(), 2),
        }
        
        if "momentum_zscore" in df.columns:
            zscores = df["momentum_zscore"]
            stats["max_momentum"] = round(zscores.max(), 3)
            stats["min_momentum"] = round(zscores.min(), 3)
            stats["anomaly_count"] = int((zscores.abs() >= self.zscore_threshold).sum())
        
        return stats

