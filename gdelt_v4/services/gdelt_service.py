"""
GDELT v4.0 Service Facade
==========================
Central orchestration layer for all GDELT operations.

The GDELTService is the ONLY entry point for dashboards and applications.
It coordinates:
- Query building
- BigQuery execution
- Momentum calculation
- Result standardization
- Caching

Dashboards should NEVER interact directly with BigQuery.

Author: Philip Hendrik Littau
Version: 4.0.0
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

import pandas as pd

from gdelt_v4.config.settings import GDELTConfig, get_config
from gdelt_v4.connectors.unified import UnifiedConnector
from gdelt_v4.query.builder import UnifiedQueryBuilder
from gdelt_v4.engines.momentum import UnifiedMomentumEngine, MomentumMode
from gdelt_v4.models.experiment import BaseExperiment, ExperimentConfig, AnalysisMode
from gdelt_v4.models.result import (
    UnifiedResult,
    TimeSeriesData,
    GeoData,
    EntityData,
    SourceTrustData,
    IntegrityMetrics,
)
from gdelt_v4.mapping.country_codes import CountryCodeMapper, get_mapper
from gdelt_v4.utils.logging import get_logger, setup_logging


logger = get_logger(__name__)


class GDELTService:
    """
    Unified service facade for GDELT v4.0.
    
    This service:
    - Provides a single entry point for all GDELT operations
    - Orchestrates query building, execution, and processing
    - Handles caching and error recovery
    - Ensures consistent result formatting
    - Abstracts away BigQuery complexity from dashboards
    
    Usage:
        >>> from gdelt_v4.services import GDELTService
        >>> from gdelt_v4.models import BaseExperiment
        >>> 
        >>> service = GDELTService()
        >>> experiment = BaseExperiment.create(
        ...     label="China Trade",
        ...     boolean_string="CHINA AND TRADE",
        ...     days=7,
        ... )
        >>> result = service.analyze(experiment)
        >>> print(result.summary())
    
    Attributes:
        config: Global configuration.
        connector: Unified BigQuery connector.
        query_builder: Unified query builder.
        momentum_engine: Momentum calculation engine.
        country_mapper: Country code converter.
    """
    
    def __init__(
        self,
        config: Optional[GDELTConfig] = None,
        momentum_window: int = 7,
        momentum_mode: MomentumMode = MomentumMode.BASIC,
    ):
        """
        Initialize the GDELT service.
        
        Args:
            config: Optional configuration. Uses global config if not provided.
            momentum_window: Rolling window for momentum calculation.
            momentum_mode: Default momentum calculation mode.
        """
        self.config = config or get_config()
        
        # Setup logging
        setup_logging(level=self.config.logging.level)
        
        # Initialize components
        self.connector = UnifiedConnector(self.config)
        self.query_builder = UnifiedQueryBuilder(self.config)
        self.momentum_engine = UnifiedMomentumEngine(
            window=momentum_window,
            mode=momentum_mode,
        )
        self.country_mapper = get_mapper()
        
        logger.info("GDELTService initialized")
    
    def analyze(
        self,
        experiment: BaseExperiment,
        include_geo: bool = True,
        include_entities: bool = False,
        include_source_trust: bool = False,
        calculate_momentum: bool = True,
    ) -> UnifiedResult:
        """
        Perform comprehensive analysis for a single experiment.
        
        Args:
            experiment: The experiment configuration.
            include_geo: Include geographic aggregation.
            include_entities: Include entity extraction.
            include_source_trust: Include source credibility analysis.
            calculate_momentum: Calculate momentum scores.
            
        Returns:
            UnifiedResult with all requested data.
        """
        logger.info(f"Starting analysis for experiment: {experiment.label}")
        
        # Override based on experiment mode
        if experiment.mode == AnalysisMode.ENTITIES:
            include_entities = True
        elif experiment.mode == AnalysisMode.SOURCE_TRUST:
            include_source_trust = True
        elif experiment.mode == AnalysisMode.FULL:
            include_entities = True
            include_source_trust = True
        
        # Fetch time series
        time_series_df = self._fetch_time_series(experiment)
        
        # Fetch geo data (both aggregated and temporal for Chronos)
        geo_df = pd.DataFrame()
        temporal_geo_df = pd.DataFrame()
        if include_geo:
            geo_df = self._fetch_geo_data(experiment)
            # v4.3.1: Also fetch temporal geo data for Chronos replay
            temporal_geo_df = self._fetch_temporal_geo_data(experiment)
        
        # Fetch entities
        entity_data = None
        if include_entities:
            entity_data = self._fetch_entities(experiment)
        
        # Fetch source trust
        source_trust_data = None
        integrity = None
        if include_source_trust:
            source_trust_data, integrity = self._fetch_source_trust(experiment)
        
        # Calculate momentum
        if calculate_momentum and not time_series_df.empty:
            time_series_df = self.momentum_engine.calculate(
                time_series_df,
                value_column="mention_count",
                date_column="record_date",
            )
        
        if calculate_momentum and not geo_df.empty:
            geo_df = self.momentum_engine.calculate_geo_momentum(geo_df)
        
        if calculate_momentum and entity_data:
            entity_data = self.momentum_engine.calculate_entity_momentum(entity_data)
        
        # Convert country codes
        if not geo_df.empty:
            geo_df = self.country_mapper.convert_dataframe(
                geo_df, "country_code", "iso3", add_name=True
            )
        
        # v4.4 FIX: Process temporal_geo_df through the SAME pipeline as geo_df
        # This was a critical disconnect in v4.3.1
        if not temporal_geo_df.empty:
            # 1. Convert country codes to ISO3 (critical for centroid fallback)
            temporal_geo_df = self.country_mapper.convert_dataframe(
                temporal_geo_df, "country_code", "iso3", add_name=True
            )
            
            # 2. Calculate momentum Z-score per country (critical for Bivariate Matrix)
            if calculate_momentum:
                temporal_geo_df = self._calculate_temporal_geo_momentum(temporal_geo_df)
        
        # v4.4: Fetch conflict data for Conflict Hubs layer
        conflict_df = pd.DataFrame()
        if include_geo:
            conflict_df = self._fetch_conflict_data(experiment)
            if not conflict_df.empty:
                conflict_df = self.country_mapper.convert_dataframe(
                    conflict_df, "country_code", "iso3", add_name=True
                )
        
        # Build result
        # v4.3.1: Use temporal_geo_df as primary geo data for Chronos support
        # If temporal data is available, prefer it; otherwise fallback to aggregated
        primary_geo_df = temporal_geo_df if not temporal_geo_df.empty else geo_df
        
        result = UnifiedResult(
            time_series=TimeSeriesData(time_series_df),
            geo_data=GeoData(primary_geo_df),
            entities=entity_data,
            source_trust=source_trust_data,
            integrity=integrity,
            experiments=[experiment.to_dict()],
            metadata={
                "analyzed_at": datetime.now().isoformat(),
                "experiment_label": experiment.label,
                "include_geo": include_geo,
                "include_entities": include_entities,
                "include_source_trust": include_source_trust,
                "has_temporal_geo": not temporal_geo_df.empty,
                # v4.4: Conflict data for Conflict Hubs layer
                "has_conflict_data": not conflict_df.empty,
            },
        )
        
        # v4.4: Attach conflict data to result for Layer Selector access
        result._conflict_data = conflict_df
        
        logger.info(f"Analysis complete: {result.summary()}")
        
        return result
    
    def analyze_batch(
        self,
        experiments: List[BaseExperiment],
        include_geo: bool = True,
        include_entities: bool = False,
        include_source_trust: bool = False,
    ) -> Dict[str, UnifiedResult]:
        """
        Analyze multiple experiments.
        
        Args:
            experiments: List of experiment configurations.
            include_geo: Include geographic aggregation.
            include_entities: Include entity extraction.
            include_source_trust: Include source credibility analysis.
            
        Returns:
            Dictionary mapping experiment labels to results.
        """
        results = {}
        
        for experiment in experiments:
            try:
                results[experiment.label] = self.analyze(
                    experiment,
                    include_geo=include_geo,
                    include_entities=include_entities,
                    include_source_trust=include_source_trust,
                )
            except Exception as e:
                logger.error(f"Analysis failed for {experiment.label}: {e}")
                results[experiment.label] = self._empty_result(experiment)
        
        return results
    
    def analyze_combined(
        self,
        config: ExperimentConfig,
    ) -> UnifiedResult:
        """
        Analyze multiple experiments with combined output.
        
        Uses a single query with CASE statements for efficiency.
        
        Args:
            config: Configuration with multiple experiments.
            
        Returns:
            UnifiedResult with combined data.
        """
        logger.info(f"Starting combined analysis for {len(config.experiments)} experiments")
        
        start_date, end_date = config.date_range
        sample_percent = config.experiments[0].sample_percent if config.experiments else None
        
        # Build multi-experiment query
        sql = self.query_builder.build_multi_experiment_query(
            config.experiments,
            start_date,
            end_date,
            sample_percent,
        )
        
        # Execute
        combined_df = self.connector.execute_query(sql)
        
        # Separate time series and geo
        time_series_df = combined_df.groupby(
            ["record_date", "experiment_label"],
            as_index=False
        ).agg({
            "mention_count": "sum",
            "sentiment_score": "mean",
        })
        
        geo_df = combined_df.groupby(
            ["country_code", "experiment_label"],
            as_index=False
        ).agg({
            "mention_count": "sum",
            "sentiment_score": "mean",
        })
        
        # Calculate momentum per experiment
        time_series_df = self.momentum_engine.calculate(
            time_series_df,
            group_column="experiment_label",
        )
        
        # Convert country codes
        geo_df = self.country_mapper.convert_dataframe(
            geo_df, "country_code", "iso3", add_name=True
        )
        
        return UnifiedResult(
            time_series=TimeSeriesData(time_series_df),
            geo_data=GeoData(geo_df),
            experiments=[exp.to_dict() for exp in config.experiments],
            metadata={
                "analyzed_at": datetime.now().isoformat(),
                "experiment_count": len(config.experiments),
                "combined": True,
            },
        )
    
    def fetch_layer_data(
        self,
        experiment: BaseExperiment,
        layer_type: str,
    ) -> pd.DataFrame:
        """
        Fetch data for a specific map layer.
        
        Args:
            experiment: The experiment configuration.
            layer_type: One of "momentum", "sentiment", "conflict", "entity".
            
        Returns:
            DataFrame with layer-specific data.
        """
        logger.info(f"Fetching {layer_type} layer data")
        
        sql = self.query_builder.build_layer_query(experiment, layer_type)
        df = self.connector.execute_query(sql)
        
        # Convert country codes
        if "country_code" in df.columns:
            df = self.country_mapper.convert_dataframe(
                df, "country_code", "iso3", add_name=True
            )
        
        return df
    
    def estimate_cost(
        self,
        experiment: BaseExperiment,
        query_type: str = "time_series",
    ) -> Dict[str, Any]:
        """
        Estimate query cost without execution.
        
        Args:
            experiment: The experiment configuration.
            query_type: Type of query to estimate.
            
        Returns:
            Cost estimation dictionary.
        """
        if query_type == "time_series":
            sql = self.query_builder.build_time_series_query(experiment)
        elif query_type == "geo":
            sql = self.query_builder.build_geo_query(experiment)
        else:
            sql = self.query_builder.build_time_series_query(experiment)
        
        return self.connector.dry_run(sql)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics including query counts and costs."""
        connector_metrics = self.connector.get_metrics()
        cache_stats = self.connector.get_cache_stats()
        
        return {
            "connector": connector_metrics,
            "cache": cache_stats,
        }
    
    def clear_cache(self) -> None:
        """Clear the query cache."""
        self.connector.clear_cache()
        logger.info("Query cache cleared")
    
    def _fetch_time_series(self, experiment: BaseExperiment) -> pd.DataFrame:
        """Fetch time series data for an experiment."""
        sql = self.query_builder.build_time_series_query(experiment)
        df = self.connector.execute_query(sql)
        
        if not df.empty and "experiment_label" not in df.columns:
            df["experiment_label"] = experiment.label
        
        return df
    
    def _fetch_geo_data(self, experiment: BaseExperiment) -> pd.DataFrame:
        """Fetch geographic data for an experiment."""
        sql = self.query_builder.build_geo_query(experiment)
        df = self.connector.execute_query(sql)
        
        if not df.empty:
            df["experiment_label"] = experiment.label
        
        return df
    
    def _fetch_temporal_geo_data(self, experiment: BaseExperiment) -> pd.DataFrame:
        """
        Fetch temporal geographic data with daily record_date.
        
        v4.3.1: This enables Chronos replay by providing per-day geo data.
        
        Args:
            experiment: The experiment configuration.
            
        Returns:
            DataFrame with record_date, country_code, lat, lon, etc.
        """
        sql = self.query_builder.build_temporal_geo_query(experiment)
        df = self.connector.execute_query(sql)
        
        if not df.empty:
            df["experiment_label"] = experiment.label
            
            # Ensure record_date is datetime
            if "record_date" in df.columns:
                df["record_date"] = pd.to_datetime(df["record_date"])
        
        return df
    
    def _calculate_temporal_geo_momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate momentum Z-score for temporal geo data.
        
        v4.4: This enables the Bivariate Crisis Matrix by adding momentum_zscore
        to each country's daily geo data.
        
        Args:
            df: DataFrame with record_date, country_code, mention_count
            
        Returns:
            DataFrame with momentum_zscore column added per country
        """
        if df.empty or "mention_count" not in df.columns:
            return df
        
        result = df.copy()
        
        # Calculate momentum per country based on their mention_count variance
        if "iso3" in result.columns:
            group_col = "iso3"
        elif "country_code" in result.columns:
            group_col = "country_code"
        else:
            # No grouping possible, calculate global momentum
            mean_val = result["mention_count"].mean()
            std_val = result["mention_count"].std()
            if std_val > 0:
                result["momentum_zscore"] = (result["mention_count"] - mean_val) / std_val
            else:
                result["momentum_zscore"] = 0.0
            return result
        
        # Calculate per-country momentum
        country_stats = result.groupby(group_col)["mention_count"].agg(["mean", "std"]).reset_index()
        country_stats.columns = [group_col, "_mean", "_std"]
        
        result = result.merge(country_stats, on=group_col, how="left")
        
        # Z-score: (value - mean) / std
        result["momentum_zscore"] = result.apply(
            lambda row: (row["mention_count"] - row["_mean"]) / row["_std"] 
            if row["_std"] > 0 else 0.0,
            axis=1
        )
        
        # Clean up temporary columns
        result = result.drop(columns=["_mean", "_std"], errors="ignore")
        
        logger.debug(f"Calculated momentum for {len(result)} temporal geo records")
        
        return result
    
    def _fetch_conflict_data(self, experiment: BaseExperiment) -> pd.DataFrame:
        """
        Fetch conflict/protest event data for Conflict Hubs layer.
        
        v4.4: Executes the CONFLICT_EVENTS SQL template to retrieve
        protest_count and conflict_count per country per day.
        
        Args:
            experiment: The experiment configuration.
            
        Returns:
            DataFrame with record_date, country_code, protest_count, 
            conflict_count, total_events, lat, lon
        """
        try:
            sql = self.query_builder.build_conflict_query(experiment)
            df = self.connector.execute_query(sql)
            
            if not df.empty:
                df["experiment_label"] = experiment.label
                
                # Ensure record_date is datetime
                if "record_date" in df.columns:
                    df["record_date"] = pd.to_datetime(df["record_date"])
                
                # Ensure numeric columns
                for col in ["protest_count", "conflict_count", "total_events"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                
                logger.info(f"Fetched {len(df)} conflict events for {experiment.label}")
            else:
                logger.info(f"No conflict events found for {experiment.label}")
            
            return df
            
        except Exception as e:
            logger.warning(f"Conflict data fetch failed: {e}")
            return pd.DataFrame()
    
    def _fetch_entities(self, experiment: BaseExperiment) -> EntityData:
        """Fetch entity data for an experiment."""
        queries = self.query_builder.build_entity_query(experiment, top_n=10)
        
        persons_df = pd.DataFrame()
        orgs_df = pd.DataFrame()
        
        if "persons" in queries:
            persons_df = self.connector.execute_query(queries["persons"])
            if not persons_df.empty:
                persons_df["experiment_label"] = experiment.label
        
        if "organizations" in queries:
            orgs_df = self.connector.execute_query(queries["organizations"])
            if not orgs_df.empty:
                orgs_df["experiment_label"] = experiment.label
        
        return EntityData(persons=persons_df, organizations=orgs_df)
    
    def _fetch_source_trust(
        self,
        experiment: BaseExperiment,
    ) -> tuple[SourceTrustData, IntegrityMetrics]:
        """Fetch source trust data and calculate integrity."""
        sql = self.query_builder.build_source_trust_query(experiment)
        df = self.connector.execute_query(sql)
        
        if not df.empty:
            df["experiment_label"] = experiment.label
        
        source_data = SourceTrustData(df)
        integrity = IntegrityMetrics.calculate(source_data.tier_summary)
        
        return source_data, integrity
    
    def _empty_result(self, experiment: BaseExperiment) -> UnifiedResult:
        """Create an empty result for failed analysis."""
        return UnifiedResult(
            time_series=TimeSeriesData(pd.DataFrame()),
            geo_data=GeoData(pd.DataFrame()),
            experiments=[experiment.to_dict()],
            metadata={
                "error": True,
                "experiment_label": experiment.label,
            },
        )


# Convenience function for quick analysis
def quick_analyze(
    label: str,
    boolean_string: str,
    days: int = 7,
    sample_percent: int = 10,
    **kwargs
) -> UnifiedResult:
    """
    Quick analysis function for simple use cases.
    
    Args:
        label: Experiment label.
        boolean_string: Query expression.
        days: Number of days to analyze.
        sample_percent: Sampling percentage.
        **kwargs: Additional experiment parameters.
        
    Returns:
        UnifiedResult with analysis output.
    
    Example:
        >>> result = quick_analyze("AI News", "ARTIFICIAL_INTELLIGENCE", days=7)
        >>> print(result.summary())
    """
    experiment = BaseExperiment.create(
        label=label,
        boolean_string=boolean_string,
        days=days,
        sample_percent=sample_percent,
        **kwargs
    )
    
    service = GDELTService()
    return service.analyze(experiment)

