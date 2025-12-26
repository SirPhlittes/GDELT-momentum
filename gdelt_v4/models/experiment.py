"""
GDELT v4.0 Experiment Models
=============================
Unified experiment and configuration dataclasses.

Replaces:
- Experiment (gdeltquery.py)
- QueryExperiment (gdelt_engine.py)
- EntityExperiment (gdelt_entity_engine.py)
- SourceTrustExperiment (source_trust.py)

Author: Philip Hendrik Littau
Version: 4.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

from gdelt_v4.utils.validators import (
    validate_date_range,
    validate_sample_percent,
    validate_experiment_label,
    validate_boolean_expression,
)


class AnalysisMode(Enum):
    """Available analysis modes."""
    BASIC = "basic"              # Time series + geo only
    ENTITIES = "entities"        # Include entity extraction
    SOURCE_TRUST = "source_trust"  # Include source credibility
    FULL = "full"                # All features


@dataclass
class BaseExperiment:
    """
    Unified experiment configuration for GDELT queries.
    
    This replaces all previous experiment dataclasses with a single,
    flexible configuration that supports all analysis modes.
    
    Attributes:
        label: Human-readable experiment identifier.
        boolean_string: Query expression with Boolean operators.
        start_date: Start of date range (inclusive).
        end_date: End of date range (inclusive).
        search_fields: GDELT fields to search.
        sample_percent: Optional sampling percentage (1-100).
        mode: Analysis mode (basic, entities, source_trust, full).
        color: Optional color for visualization.
        entity_filter: Optional list of entities to filter by.
        metadata: Additional custom metadata.
    
    Example:
        >>> from datetime import datetime, timedelta
        >>> experiment = BaseExperiment(
        ...     label="China Trade Policy",
        ...     boolean_string="(CHINA OR BEIJING) AND (TRADE OR TARIFF)",
        ...     start_date=datetime.now() - timedelta(days=7),
        ...     end_date=datetime.now() - timedelta(days=1),
        ...     sample_percent=10,
        ...     mode=AnalysisMode.ENTITIES,
        ... )
    """
    label: str
    boolean_string: str
    start_date: datetime
    end_date: datetime
    search_fields: List[str] = field(default_factory=lambda: ["V2Themes", "AllNames", "V2Organizations"])
    sample_percent: Optional[int] = None
    mode: AnalysisMode = AnalysisMode.BASIC
    color: Optional[str] = None
    entity_filter: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate experiment parameters."""
        self.label = validate_experiment_label(self.label)
        self.boolean_string = validate_boolean_expression(self.boolean_string)
        self.start_date, self.end_date = validate_date_range(self.start_date, self.end_date)
        self.sample_percent = validate_sample_percent(self.sample_percent)
        
        # Convert mode from string if necessary
        if isinstance(self.mode, str):
            self.mode = AnalysisMode(self.mode)
    
    @classmethod
    def create(
        cls,
        label: str,
        boolean_string: str,
        days: int = 7,
        sample_percent: Optional[int] = 10,
        mode: str = "basic",
        **kwargs
    ) -> "BaseExperiment":
        """
        Factory method for creating experiments with sensible defaults.
        
        Args:
            label: Experiment label.
            boolean_string: Query expression.
            days: Number of days to analyze (default: 7).
            sample_percent: Sampling percentage (default: 10).
            mode: Analysis mode (default: "basic").
            **kwargs: Additional experiment parameters.
            
        Returns:
            Configured BaseExperiment instance.
        """
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=days)
        
        return cls(
            label=label,
            boolean_string=boolean_string,
            start_date=start_date,
            end_date=end_date,
            sample_percent=sample_percent,
            mode=AnalysisMode(mode),
            **kwargs
        )
    
    def with_mode(self, mode: AnalysisMode) -> "BaseExperiment":
        """
        Create a copy with a different analysis mode.
        
        Args:
            mode: The new analysis mode.
            
        Returns:
            New BaseExperiment instance with updated mode.
        """
        return BaseExperiment(
            label=self.label,
            boolean_string=self.boolean_string,
            start_date=self.start_date,
            end_date=self.end_date,
            search_fields=self.search_fields.copy(),
            sample_percent=self.sample_percent,
            mode=mode,
            color=self.color,
            entity_filter=self.entity_filter.copy() if self.entity_filter else None,
            metadata=self.metadata.copy(),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "label": self.label,
            "boolean_string": self.boolean_string,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "search_fields": self.search_fields,
            "sample_percent": self.sample_percent,
            "mode": self.mode.value,
            "color": self.color,
            "entity_filter": self.entity_filter,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseExperiment":
        """Create from dictionary representation."""
        return cls(
            label=data["label"],
            boolean_string=data["boolean_string"],
            start_date=datetime.fromisoformat(data["start_date"]),
            end_date=datetime.fromisoformat(data["end_date"]),
            search_fields=data.get("search_fields", ["V2Themes"]),
            sample_percent=data.get("sample_percent"),
            mode=AnalysisMode(data.get("mode", "basic")),
            color=data.get("color"),
            entity_filter=data.get("entity_filter"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ExperimentConfig:
    """
    Configuration for running multiple experiments.
    
    Attributes:
        experiments: List of experiments to run.
        parallel: Whether to run experiments in parallel.
        cache_results: Whether to cache query results.
        include_geo: Include geographic aggregation.
        include_entities: Include entity extraction.
        include_source_trust: Include source credibility analysis.
        top_n_entities: Number of top entities to extract.
    """
    experiments: List[BaseExperiment]
    parallel: bool = False
    cache_results: bool = True
    include_geo: bool = True
    include_entities: bool = False
    include_source_trust: bool = False
    top_n_entities: int = 10
    
    def __post_init__(self):
        """Validate configuration."""
        if not self.experiments:
            raise ValueError("At least one experiment must be provided")
        
        # Ensure all experiments have unique labels
        labels = [exp.label for exp in self.experiments]
        if len(labels) != len(set(labels)):
            raise ValueError("All experiment labels must be unique")
    
    @property
    def date_range(self) -> tuple[datetime, datetime]:
        """Get the overall date range across all experiments."""
        min_date = min(exp.start_date for exp in self.experiments)
        max_date = max(exp.end_date for exp in self.experiments)
        return min_date, max_date
    
    @property
    def labels(self) -> List[str]:
        """Get list of experiment labels."""
        return [exp.label for exp in self.experiments]

