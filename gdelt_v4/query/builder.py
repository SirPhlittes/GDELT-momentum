"""
GDELT v4.0 Unified Query Builder
=================================
Consolidates all SQL generation into a single, modular system.

Replaces:
- DynamicSQLBuilder (gdelt_engine.py)
- BooleanQueryParser + EntitySQLBuilder (gdelt_entity_engine.py)
- DynamicSQLGenerator (map_intelligence.py)
- SourceTrustSQLBuilder (source_trust.py)

Author: Philip Hendrik Littau
Version: 4.0.0
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any

from gdelt_v4.config.settings import GDELTConfig, get_config
from gdelt_v4.query.parser import BooleanParser, ParsedQuery
from gdelt_v4.query.templates import SQLTemplates, QueryType
from gdelt_v4.models.experiment import BaseExperiment
from gdelt_v4.utils.logging import get_logger
from gdelt_v4.utils.validators import validate_date_range


logger = get_logger(__name__)


class UnifiedQueryBuilder:
    """
    Unified SQL query builder for all GDELT query types.
    
    This builder:
    - Parses Boolean expressions correctly (fixed AND logic)
    - Supports multiple query types (time series, geo, entities, source trust)
    - Enforces partition filtering for cost optimization
    - Generates optimized SQL using templates
    
    Example:
        >>> from gdelt_v4.query import UnifiedQueryBuilder
        >>> from gdelt_v4.models import BaseExperiment
        >>> from datetime import datetime, timedelta
        >>> 
        >>> builder = UnifiedQueryBuilder()
        >>> experiment = BaseExperiment(
        ...     label="China Trade",
        ...     boolean_string="(CHINA OR BEIJING) AND TRADE",
        ...     start_date=datetime.now() - timedelta(days=7),
        ...     end_date=datetime.now() - timedelta(days=1),
        ... )
        >>> 
        >>> sql = builder.build_time_series_query(experiment)
        >>> print(sql)
    """
    
    def __init__(self, config: Optional[GDELTConfig] = None):
        """
        Initialize the query builder.
        
        Args:
            config: Optional GDELTConfig instance.
        """
        self.config = config or get_config()
        self.parser = BooleanParser()
        self._default_fields = ["V2Themes", "AllNames", "V2Organizations"]
    
    def _get_table(self) -> str:
        """Get the fully qualified table ID."""
        return self.config.bigquery.full_table_id
    
    def _parse_and_build_conditions(
        self,
        boolean_string: str,
        fields: Optional[List[str]] = None,
    ) -> str:
        """
        Parse a Boolean string and build SQL conditions.
        
        Args:
            boolean_string: The Boolean expression.
            fields: GDELT fields to search.
            
        Returns:
            SQL WHERE conditions string.
        """
        fields = fields or self._default_fields
        parsed = self.parser.parse(boolean_string)
        return self.parser.to_sql_conditions(parsed, fields)
    
    def build_time_series_query(
        self,
        experiment: BaseExperiment,
        include_sentiment: bool = True,
    ) -> str:
        """
        Build a time series aggregation query.
        
        Args:
            experiment: The experiment configuration.
            include_sentiment: Whether to include sentiment columns.
            
        Returns:
            SQL query string.
        """
        conditions = self._parse_and_build_conditions(
            experiment.boolean_string,
            experiment.search_fields,
        )
        
        template = SQLTemplates.TIME_SERIES_WITH_EXPERIMENT if experiment.label else SQLTemplates.TIME_SERIES_BASIC
        
        return SQLTemplates.format_template(
            template,
            table=self._get_table(),
            start_date=experiment.start_date.strftime("%Y-%m-%d"),
            end_date=experiment.end_date.strftime("%Y-%m-%d"),
            conditions=conditions,
            sample_percent=experiment.sample_percent,
            experiment_label=experiment.label,
        )
    
    def build_geo_query(
        self,
        experiment: BaseExperiment,
        include_momentum: bool = False,
    ) -> str:
        """
        Build a geographic aggregation query.
        
        Args:
            experiment: The experiment configuration.
            include_momentum: Whether to include momentum calculation.
            
        Returns:
            SQL query string.
        """
        conditions = self._parse_and_build_conditions(
            experiment.boolean_string,
            experiment.search_fields,
        )
        
        template = SQLTemplates.GEO_MOMENTUM if include_momentum else SQLTemplates.GEO_AGGREGATE_COUNTRY
        
        return SQLTemplates.format_template(
            template,
            table=self._get_table(),
            start_date=experiment.start_date.strftime("%Y-%m-%d"),
            end_date=experiment.end_date.strftime("%Y-%m-%d"),
            conditions=conditions,
            sample_percent=experiment.sample_percent,
        )
    
    def build_temporal_geo_query(
        self,
        experiment: BaseExperiment,
    ) -> str:
        """
        Build a temporal geographic query with daily record_date.
        
        v4.3.1: This query includes record_date for Chronos replay functionality.
        The data is grouped by date AND country, enabling temporal slicing.
        
        Args:
            experiment: The experiment configuration.
            
        Returns:
            SQL query string with record_date column.
        """
        conditions = self._parse_and_build_conditions(
            experiment.boolean_string,
            experiment.search_fields,
        )
        
        return SQLTemplates.format_template(
            SQLTemplates.GEO_TEMPORAL_DAILY,
            table=self._get_table(),
            start_date=experiment.start_date.strftime("%Y-%m-%d"),
            end_date=experiment.end_date.strftime("%Y-%m-%d"),
            conditions=conditions,
            sample_percent=experiment.sample_percent,
        )
    
    def build_entity_query(
        self,
        experiment: BaseExperiment,
        entity_type: str = "both",
        top_n: int = 10,
    ) -> Dict[str, str]:
        """
        Build entity extraction queries.
        
        Args:
            experiment: The experiment configuration.
            entity_type: "persons", "organizations", or "both".
            top_n: Number of top entities to return.
            
        Returns:
            Dictionary of query type to SQL string.
        """
        conditions = self._parse_and_build_conditions(
            experiment.boolean_string,
            experiment.search_fields,
        )
        
        queries = {}
        
        if entity_type in ("persons", "both"):
            queries["persons"] = SQLTemplates.format_template(
                SQLTemplates.ENTITY_PERSONS,
                table=self._get_table(),
                start_date=experiment.start_date.strftime("%Y-%m-%d"),
                end_date=experiment.end_date.strftime("%Y-%m-%d"),
                conditions=conditions,
                sample_percent=experiment.sample_percent,
                top_n=top_n,
            )
        
        if entity_type in ("organizations", "both"):
            queries["organizations"] = SQLTemplates.format_template(
                SQLTemplates.ENTITY_ORGANIZATIONS,
                table=self._get_table(),
                start_date=experiment.start_date.strftime("%Y-%m-%d"),
                end_date=experiment.end_date.strftime("%Y-%m-%d"),
                conditions=conditions,
                sample_percent=experiment.sample_percent,
                top_n=top_n,
            )
        
        return queries
    
    def build_source_trust_query(
        self,
        experiment: BaseExperiment,
        daily: bool = False,
    ) -> str:
        """
        Build a source trust aggregation query.
        
        Args:
            experiment: The experiment configuration.
            daily: Whether to aggregate by day.
            
        Returns:
            SQL query string.
        """
        conditions = self._parse_and_build_conditions(
            experiment.boolean_string,
            experiment.search_fields,
        )
        
        # Build tier domain lists
        tier1_list = ", ".join(f"'{d}'" for d in self.config.source_trust.tier1_domains)
        tier3_list = ", ".join(f"'{d}'" for d in self.config.source_trust.tier3_domains)
        
        template = SQLTemplates.SOURCE_TRUST_DAILY if daily else SQLTemplates.SOURCE_TRUST_AGGREGATE
        
        return SQLTemplates.format_template(
            template,
            table=self._get_table(),
            start_date=experiment.start_date.strftime("%Y-%m-%d"),
            end_date=experiment.end_date.strftime("%Y-%m-%d"),
            conditions=conditions,
            sample_percent=experiment.sample_percent,
            tier1_domains=tier1_list,
            tier3_domains=tier3_list,
        )
    
    def build_conflict_query(
        self,
        experiment: BaseExperiment,
    ) -> str:
        """
        Build a conflict/protest events query.
        
        Args:
            experiment: The experiment configuration.
            
        Returns:
            SQL query string.
        """
        conditions = self._parse_and_build_conditions(
            experiment.boolean_string,
            experiment.search_fields,
        )
        
        return SQLTemplates.format_template(
            SQLTemplates.CONFLICT_EVENTS,
            table=self._get_table(),
            start_date=experiment.start_date.strftime("%Y-%m-%d"),
            end_date=experiment.end_date.strftime("%Y-%m-%d"),
            conditions=conditions,
            sample_percent=experiment.sample_percent,
        )
    
    def build_multi_experiment_query(
        self,
        experiments: List[BaseExperiment],
        start_date: datetime,
        end_date: datetime,
        sample_percent: Optional[int] = None,
    ) -> str:
        """
        Build a single query for multiple experiments.
        
        Uses CASE statements to label each matching row with its experiment.
        More efficient than running separate queries.
        
        Args:
            experiments: List of experiment configurations.
            start_date: Overall start date.
            end_date: Overall end date.
            sample_percent: Optional sampling percentage.
            
        Returns:
            SQL query string.
        """
        experiment_cases = []
        all_conditions = []
        
        for exp in experiments:
            conditions = self._parse_and_build_conditions(
                exp.boolean_string,
                exp.search_fields,
            )
            experiment_cases.append(f"WHEN {conditions} THEN '{exp.label}'")
            all_conditions.append(f"({conditions})")
        
        return SQLTemplates.format_template(
            SQLTemplates.MULTI_EXPERIMENT,
            table=self._get_table(),
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            conditions="TRUE",  # Not used, combined_conditions is
            sample_percent=sample_percent,
            experiment_cases="\n            ".join(experiment_cases),
            combined_conditions=" OR ".join(all_conditions),
        )
    
    def build_layer_query(
        self,
        experiment: BaseExperiment,
        layer_type: str,
    ) -> str:
        """
        Build a layer-specific query for map visualization.
        
        Args:
            experiment: The experiment configuration.
            layer_type: One of "momentum", "sentiment", "conflict", "entity".
            
        Returns:
            SQL query string.
        """
        if layer_type == "momentum":
            return self.build_geo_query(experiment, include_momentum=True)
        elif layer_type == "sentiment":
            return self.build_geo_query(experiment, include_momentum=False)
        elif layer_type == "conflict":
            return self.build_conflict_query(experiment)
        elif layer_type == "entity":
            conditions = self._parse_and_build_conditions(
                experiment.boolean_string,
                experiment.search_fields,
            )
            return SQLTemplates.format_template(
                SQLTemplates.ENTITY_BY_COUNTRY,
                table=self._get_table(),
                start_date=experiment.start_date.strftime("%Y-%m-%d"),
                end_date=experiment.end_date.strftime("%Y-%m-%d"),
                conditions=conditions,
                sample_percent=experiment.sample_percent,
            )
        else:
            raise ValueError(f"Unknown layer type: {layer_type}")
    
    def estimate_cost(
        self,
        experiment: BaseExperiment,
        query_type: str = "time_series",
    ) -> Dict[str, Any]:
        """
        Estimate the cost of a query without executing it.
        
        Args:
            experiment: The experiment configuration.
            query_type: Type of query to estimate.
            
        Returns:
            Dictionary with cost estimation.
        """
        # Build the query
        if query_type == "time_series":
            sql = self.build_time_series_query(experiment)
        elif query_type == "geo":
            sql = self.build_geo_query(experiment)
        elif query_type == "entity":
            sql = list(self.build_entity_query(experiment).values())[0]
        else:
            sql = self.build_time_series_query(experiment)
        
        # This would need a connector to do a dry run
        # For now, return a placeholder
        return {
            "query_type": query_type,
            "sample_percent": experiment.sample_percent,
            "note": "Use UnifiedConnector.dry_run(sql) for actual estimation",
        }

