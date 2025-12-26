"""
GDELT v4.4 SQL Templates
=========================
Centralized SQL template definitions for GDELT queries.

v4.4 "Multidimensional" Update:
- GEO_AGGREGATE_COUNTRY: Now includes record_date for temporal sync
- CONFLICT_EVENTS_TEMPORAL: Daily conflict data with record_date
- All geo templates support temporal slicing and Layer Selector

Templates use Python format strings with named placeholders for:
- table: Fully qualified table ID
- start_date: Start of date range
- end_date: End of date range
- conditions: WHERE clause conditions
- sample_clause: Optional sampling filter

Author: Philip Hendrik Littau
Version: 4.4.0
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional


class QueryType(Enum):
    """Types of GDELT queries."""
    TIME_SERIES = "time_series"
    GEO_AGGREGATE = "geo_aggregate"
    GEO_TEMPORAL = "geo_temporal"  # v4.3.1: Daily geo data for Chronos
    ENTITY_PERSONS = "entity_persons"
    ENTITY_ORGANIZATIONS = "entity_organizations"
    SOURCE_TRUST = "source_trust"
    MOMENTUM_DAILY = "momentum_daily"
    CONFLICT_EVENTS = "conflict_events"
    LAYER_SENTIMENT = "layer_sentiment"
    LAYER_ENTITY_MAP = "layer_entity_map"


class SQLTemplates:
    """
    Repository of SQL templates for GDELT queries.
    
    All templates enforce _PARTITIONTIME filtering for cost optimization.
    """
    
    # Base partition filter (required for all queries)
    PARTITION_FILTER = """
        _PARTITIONTIME >= TIMESTAMP('{start_date}')
        AND _PARTITIONTIME < TIMESTAMP(DATE_ADD('{end_date}', INTERVAL 1 DAY))
    """
    
    # =========================================================================
    # TIME SERIES TEMPLATES
    # =========================================================================
    
    TIME_SERIES_BASIC = """
    SELECT
        DATE(_PARTITIONTIME) AS record_date,
        COUNT(*) AS mention_count,
        AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS sentiment_score,
        AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(1)] AS FLOAT64)) AS positive_score,
        AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(2)] AS FLOAT64)) AS negative_score
    FROM `{table}`
    WHERE
        {partition_filter}
        AND ({conditions})
        {sample_clause}
    GROUP BY record_date
    ORDER BY record_date
    """
    
    TIME_SERIES_WITH_EXPERIMENT = """
    SELECT
        DATE(_PARTITIONTIME) AS record_date,
        '{experiment_label}' AS experiment_label,
        COUNT(*) AS mention_count,
        AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS sentiment_score
    FROM `{table}`
    WHERE
        {partition_filter}
        AND ({conditions})
        {sample_clause}
    GROUP BY record_date
    ORDER BY record_date
    """
    
    # =========================================================================
    # GEOGRAPHIC TEMPLATES
    # =========================================================================
    
    # v4.4: GEO_AGGREGATE_COUNTRY now includes record_date for temporal sync
    GEO_AGGREGATE_COUNTRY = """
    SELECT
        DATE(_PARTITIONTIME) AS record_date,
        SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(2)] AS country_code,
        COUNT(*) AS mention_count,
        AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS sentiment_score,
        SAFE_CAST(AVG(SAFE_CAST(SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(5)] AS FLOAT64)) AS FLOAT64) AS latitude,
        SAFE_CAST(AVG(SAFE_CAST(SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(6)] AS FLOAT64)) AS FLOAT64) AS longitude
    FROM `{table}`
    WHERE
        {partition_filter}
        AND ({conditions})
        AND V2Locations IS NOT NULL
        AND V2Locations != ''
        {sample_clause}
    GROUP BY record_date, country_code
    HAVING country_code IS NOT NULL AND country_code != ''
    ORDER BY record_date, mention_count DESC
    """
    
    # v4.3.1: Temporal geo data with record_date for Chronos replay
    GEO_TEMPORAL_DAILY = """
    SELECT
        DATE(_PARTITIONTIME) AS record_date,
        SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(2)] AS country_code,
        COUNT(*) AS mention_count,
        AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS sentiment_score,
        AVG(SAFE_CAST(SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(5)] AS FLOAT64)) AS latitude,
        AVG(SAFE_CAST(SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(6)] AS FLOAT64)) AS longitude
    FROM `{table}`
    WHERE
        {partition_filter}
        AND ({conditions})
        AND V2Locations IS NOT NULL
        AND V2Locations != ''
        {sample_clause}
    GROUP BY record_date, country_code
    HAVING country_code IS NOT NULL AND country_code != ''
    ORDER BY record_date, mention_count DESC
    """
    
    GEO_MOMENTUM = """
    WITH daily_country AS (
        SELECT
            DATE(_PARTITIONTIME) AS record_date,
            SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(2)] AS country_code,
            COUNT(*) AS daily_volume,
            AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS avg_sentiment
        FROM `{table}`
        WHERE
            {partition_filter}
            AND ({conditions})
            AND V2Locations IS NOT NULL
            {sample_clause}
        GROUP BY record_date, country_code
        HAVING country_code IS NOT NULL AND country_code != ''
    ),
    country_stats AS (
        SELECT
            country_code,
            SUM(daily_volume) AS total_volume,
            AVG(daily_volume) AS mean_volume,
            STDDEV(daily_volume) AS std_volume,
            AVG(avg_sentiment) AS avg_sentiment,
            COUNT(DISTINCT record_date) AS active_days
        FROM daily_country
        GROUP BY country_code
    )
    SELECT
        country_code,
        total_volume AS mention_count,
        ROUND(avg_sentiment, 3) AS sentiment_score,
        ROUND(
            CASE 
                WHEN std_volume > 0 
                THEN (total_volume / active_days - mean_volume) / std_volume
                ELSE 0
            END, 3
        ) AS momentum_zscore,
        active_days
    FROM country_stats
    WHERE total_volume > 0
    ORDER BY momentum_zscore DESC
    """
    
    # =========================================================================
    # ENTITY TEMPLATES
    # =========================================================================
    
    ENTITY_PERSONS = """
    WITH person_mentions AS (
        SELECT
            TRIM(person) AS entity_name,
            COUNT(*) AS mention_count,
            AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS avg_sentiment
        FROM `{table}`,
        UNNEST(SPLIT(V2Persons, ';')) AS person
        WHERE
            {partition_filter}
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
    
    ENTITY_ORGANIZATIONS = """
    WITH org_mentions AS (
        SELECT
            TRIM(org) AS entity_name,
            COUNT(*) AS mention_count,
            AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS avg_sentiment
        FROM `{table}`,
        UNNEST(SPLIT(V2Organizations, ';')) AS org
        WHERE
            {partition_filter}
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
    
    ENTITY_BY_COUNTRY = """
    WITH entity_data AS (
        SELECT
            SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(2)] AS country_code,
            TRIM(SPLIT(V2Organizations, ';')[SAFE_OFFSET(0)]) AS top_org,
            TRIM(SPLIT(V2Persons, ';')[SAFE_OFFSET(0)]) AS top_person
        FROM `{table}`
        WHERE
            {partition_filter}
            AND ({conditions})
            {sample_clause}
    )
    SELECT
        country_code,
        COUNT(*) AS mention_count,
        APPROX_TOP_COUNT(top_org, 3) AS top_organizations,
        APPROX_TOP_COUNT(top_person, 3) AS top_persons
    FROM entity_data
    WHERE country_code IS NOT NULL AND country_code != ''
    GROUP BY country_code
    ORDER BY mention_count DESC
    """
    
    # =========================================================================
    # SOURCE TRUST TEMPLATES
    # =========================================================================
    
    SOURCE_TRUST_AGGREGATE = """
    SELECT
        NET.REG_DOMAIN(DocumentIdentifier) AS domain,
        CASE
            WHEN NET.REG_DOMAIN(DocumentIdentifier) IN ({tier1_domains}) THEN 1
            WHEN NET.REG_DOMAIN(DocumentIdentifier) IN ({tier3_domains}) THEN 3
            ELSE 2
        END AS tier,
        COUNT(*) AS mention_count,
        AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS sentiment_score
    FROM `{table}`
    WHERE
        {partition_filter}
        AND ({conditions})
        AND DocumentIdentifier IS NOT NULL
        {sample_clause}
    GROUP BY domain, tier
    HAVING domain IS NOT NULL
    ORDER BY mention_count DESC
    """
    
    SOURCE_TRUST_DAILY = """
    SELECT
        DATE(_PARTITIONTIME) AS record_date,
        CASE
            WHEN NET.REG_DOMAIN(DocumentIdentifier) IN ({tier1_domains}) THEN 1
            WHEN NET.REG_DOMAIN(DocumentIdentifier) IN ({tier3_domains}) THEN 3
            ELSE 2
        END AS tier,
        COUNT(*) AS mention_count
    FROM `{table}`
    WHERE
        {partition_filter}
        AND ({conditions})
        AND DocumentIdentifier IS NOT NULL
        {sample_clause}
    GROUP BY record_date, tier
    ORDER BY record_date, tier
    """
    
    # =========================================================================
    # CONFLICT/PROTEST TEMPLATES
    # =========================================================================
    
    # v4.4: CONFLICT_EVENTS with record_date for Layer Selector temporal sync
    CONFLICT_EVENTS = """
    SELECT
        DATE(_PARTITIONTIME) AS record_date,
        SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(2)] AS country_code,
        SAFE_CAST(AVG(SAFE_CAST(SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(5)] AS FLOAT64)) AS FLOAT64) AS latitude,
        SAFE_CAST(AVG(SAFE_CAST(SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(6)] AS FLOAT64)) AS FLOAT64) AS longitude,
        COUNT(*) AS total_events,
        SUM(CASE WHEN REGEXP_CONTAINS(V2Themes, r'(?i)(PROTEST|DEMONSTRATION|RIOT|STRIKE)') THEN 1 ELSE 0 END) AS protest_count,
        SUM(CASE WHEN REGEXP_CONTAINS(V2Themes, r'(?i)(CONFLICT|WAR|VIOLENCE|ATTACK)') THEN 1 ELSE 0 END) AS conflict_count,
        AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS sentiment_score
    FROM `{table}`
    WHERE
        {partition_filter}
        AND ({conditions})
        AND REGEXP_CONTAINS(V2Themes, r'(?i)(PROTEST|DEMONSTRATION|RIOT|STRIKE|CONFLICT|WAR|VIOLENCE|ATTACK)')
        {sample_clause}
    GROUP BY record_date, country_code
    HAVING country_code IS NOT NULL AND country_code != ''
    ORDER BY record_date, total_events DESC
    """
    
    # Aggregated conflict without temporal dimension (for summary views)
    CONFLICT_EVENTS_AGGREGATE = """
    SELECT
        SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(2)] AS country_code,
        SAFE_CAST(AVG(SAFE_CAST(SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(5)] AS FLOAT64)) AS FLOAT64) AS latitude,
        SAFE_CAST(AVG(SAFE_CAST(SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(6)] AS FLOAT64)) AS FLOAT64) AS longitude,
        COUNT(*) AS total_events,
        SUM(CASE WHEN REGEXP_CONTAINS(V2Themes, r'(?i)(PROTEST|DEMONSTRATION|RIOT|STRIKE)') THEN 1 ELSE 0 END) AS protest_count,
        SUM(CASE WHEN REGEXP_CONTAINS(V2Themes, r'(?i)(CONFLICT|WAR|VIOLENCE|ATTACK)') THEN 1 ELSE 0 END) AS conflict_count,
        AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS sentiment_score
    FROM `{table}`
    WHERE
        {partition_filter}
        AND ({conditions})
        AND REGEXP_CONTAINS(V2Themes, r'(?i)(PROTEST|DEMONSTRATION|RIOT|STRIKE|CONFLICT|WAR|VIOLENCE|ATTACK)')
        {sample_clause}
    GROUP BY country_code
    HAVING country_code IS NOT NULL AND country_code != ''
    ORDER BY total_events DESC
    """
    
    # =========================================================================
    # MULTI-EXPERIMENT TEMPLATE
    # =========================================================================
    
    MULTI_EXPERIMENT = """
    SELECT
        DATE(_PARTITIONTIME) AS record_date,
        CASE
            {experiment_cases}
            ELSE NULL
        END AS experiment_label,
        SPLIT(SPLIT(V2Locations, ';')[SAFE_OFFSET(0)], '#')[SAFE_OFFSET(2)] AS country_code,
        COUNT(*) AS mention_count,
        AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS sentiment_score
    FROM `{table}`
    WHERE
        {partition_filter}
        AND ({combined_conditions})
        {sample_clause}
    GROUP BY record_date, experiment_label, country_code
    HAVING experiment_label IS NOT NULL
    ORDER BY record_date, experiment_label
    """
    
    @classmethod
    def get_template(cls, query_type: QueryType) -> str:
        """
        Get a SQL template by type.
        
        Args:
            query_type: The type of query template.
            
        Returns:
            The SQL template string.
        """
        templates = {
            QueryType.TIME_SERIES: cls.TIME_SERIES_BASIC,
            QueryType.GEO_AGGREGATE: cls.GEO_AGGREGATE_COUNTRY,
            QueryType.GEO_TEMPORAL: cls.GEO_TEMPORAL_DAILY,  # v4.3.1
            QueryType.ENTITY_PERSONS: cls.ENTITY_PERSONS,
            QueryType.ENTITY_ORGANIZATIONS: cls.ENTITY_ORGANIZATIONS,
            QueryType.SOURCE_TRUST: cls.SOURCE_TRUST_AGGREGATE,
            QueryType.MOMENTUM_DAILY: cls.GEO_MOMENTUM,
            QueryType.CONFLICT_EVENTS: cls.CONFLICT_EVENTS,
            QueryType.LAYER_SENTIMENT: cls.GEO_AGGREGATE_COUNTRY,
            QueryType.LAYER_ENTITY_MAP: cls.ENTITY_BY_COUNTRY,
        }
        return templates.get(query_type, cls.TIME_SERIES_BASIC)
    
    @classmethod
    def format_template(
        cls,
        template: str,
        table: str,
        start_date: str,
        end_date: str,
        conditions: str,
        sample_percent: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Format a SQL template with the provided parameters.
        
        Args:
            template: The SQL template string.
            table: Fully qualified table ID.
            start_date: Start date string (YYYY-MM-DD).
            end_date: End date string (YYYY-MM-DD).
            conditions: WHERE clause conditions.
            sample_percent: Optional sampling percentage.
            **kwargs: Additional template parameters.
            
        Returns:
            Formatted SQL query string.
        """
        partition_filter = cls.PARTITION_FILTER.format(
            start_date=start_date,
            end_date=end_date
        )
        
        sample_clause = ""
        if sample_percent and 1 <= sample_percent < 100:
            sample_clause = f"AND RAND() < {sample_percent / 100.0}"
        
        return template.format(
            table=table,
            partition_filter=partition_filter,
            start_date=start_date,
            end_date=end_date,
            conditions=conditions,
            sample_clause=sample_clause,
            **kwargs
        )

