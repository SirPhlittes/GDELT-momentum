"""
GDELT v4.3 Temporal Engine (CHRONOS)
=====================================
High-performance temporal slicing and frame retrieval for Command Center.

Features:
- High-speed timestamp indexing
- Frame retrieval with lookback window
- Global replay state management
- Temporal fading calculations

Author: Philip Hendrik Littau
Version: 4.3.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Generator, Tuple
import pandas as pd
import numpy as np
from bisect import bisect_left, bisect_right

from gdelt_v4.utils.logging import get_logger


logger = get_logger(__name__)


# =============================================================================
# TEMPORAL SLICE DATA CLASS
# =============================================================================

@dataclass
class TemporalSlice:
    """
    A single time slice of GDELT data.
    
    Attributes:
        timestamp: The date/time of this slice
        time_series: Time series metrics for this slice
        geo_data: Geographic data for this slice
        entities: Entity data (persons/organizations)
        momentum_zscore: Calculated Z-score for this point
        sentiment_avg: Average sentiment for this slice
        mention_count: Total mentions in this slice
        top_headlines: Sample headlines from this period
    """
    timestamp: datetime
    time_series: pd.DataFrame = field(default_factory=pd.DataFrame)
    geo_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    entities: Dict[str, pd.DataFrame] = field(default_factory=dict)
    momentum_zscore: float = 0.0
    sentiment_avg: float = 0.0
    mention_count: int = 0
    top_headlines: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert slice to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "momentum_zscore": self.momentum_zscore,
            "sentiment_avg": self.sentiment_avg,
            "mention_count": self.mention_count,
            "geo_count": len(self.geo_data),
            "headlines_count": len(self.top_headlines),
        }


@dataclass
class TemporalFrame:
    """
    A frame for rendering containing events within a lookback window.
    
    Used for high-speed temporal visualization with fading effects.
    """
    timestamp: datetime
    current_events: pd.DataFrame  # Events at current timestamp
    lookback_events: pd.DataFrame  # Events within lookback window (with age)
    momentum_zscore: float = 0.0
    sentiment_avg: float = 0.0
    mention_count: int = 0
    
    @property
    def all_events(self) -> pd.DataFrame:
        """Get all events (current + lookback) combined."""
        if self.current_events.empty and self.lookback_events.empty:
            return pd.DataFrame()
        elif self.current_events.empty:
            return self.lookback_events
        elif self.lookback_events.empty:
            return self.current_events
        else:
            return pd.concat([self.current_events, self.lookback_events], ignore_index=True)


@dataclass
class TemporalResult:
    """
    Complete temporal analysis result with daily slices and high-speed index.
    
    Attributes:
        slices: Dictionary mapping date strings to TemporalSlice objects
        date_range: Tuple of (start_date, end_date)
        total_days: Number of days in the result
        aggregated: Aggregated metrics across all slices
        _index: High-speed timestamp index for frame retrieval
    """
    slices: Dict[str, TemporalSlice] = field(default_factory=dict)
    date_range: tuple = field(default_factory=lambda: (None, None))
    total_days: int = 0
    aggregated: Dict[str, Any] = field(default_factory=dict)
    _geo_index: pd.DataFrame = field(default_factory=pd.DataFrame)
    _sorted_timestamps: List[datetime] = field(default_factory=list)
    
    def get_slice(self, date: str) -> Optional[TemporalSlice]:
        """Get slice for a specific date."""
        return self.slices.get(date)
    
    def get_dates(self) -> List[str]:
        """Get sorted list of available dates."""
        return sorted(self.slices.keys())
    
    def get_momentum_series(self) -> pd.DataFrame:
        """Get momentum time series across all slices."""
        data = []
        for date_str in sorted(self.slices.keys()):
            slice_data = self.slices[date_str]
            data.append({
                "date": date_str,
                "momentum_zscore": slice_data.momentum_zscore,
                "sentiment_avg": slice_data.sentiment_avg,
                "mention_count": slice_data.mention_count,
            })
        return pd.DataFrame(data)


# =============================================================================
# REPLAY STATE MANAGER (Global)
# =============================================================================

@dataclass
class ReplayState:
    """
    Global state manager for temporal replay in Command Center.
    
    This state is shared between GAIA and CHRONOS components
    and should be stored in st.session_state.
    
    Attributes:
        is_playing: Whether replay is currently active
        current_index: Current frame index
        current_timestamp: Current timestamp being displayed
        speed: Replay speed multiplier (1.0 = 1 day per 0.5s)
        loop: Whether to loop at end
        lookback_hours: Hours to look back for fading effect
        decay_window: Decay window in hours for opacity calculation
    """
    is_playing: bool = False
    current_index: int = 0
    current_timestamp: Optional[datetime] = None
    speed: float = 1.0
    loop: bool = True
    total_frames: int = 0
    lookback_hours: int = 72  # 3 days
    decay_window: int = 72    # 3 days decay
    
    def play(self) -> None:
        """Start replay."""
        self.is_playing = True
    
    def pause(self) -> None:
        """Pause replay."""
        self.is_playing = False
    
    def toggle(self) -> None:
        """Toggle play/pause."""
        self.is_playing = not self.is_playing
    
    def reset(self) -> None:
        """Reset to beginning."""
        self.current_index = 0
        self.is_playing = False
        self.current_timestamp = None
    
    def next_frame(self) -> int:
        """
        Advance to next frame.
        
        Returns:
            New frame index
        """
        if self.current_index < self.total_frames - 1:
            self.current_index += 1
        elif self.loop:
            self.current_index = 0
        else:
            self.is_playing = False
        return self.current_index
    
    def set_frame(self, index: int) -> None:
        """Set specific frame index."""
        self.current_index = max(0, min(index, self.total_frames - 1))
    
    def get_progress(self) -> float:
        """Get replay progress (0-1)."""
        if self.total_frames == 0:
            return 0
        return self.current_index / max(1, self.total_frames - 1)
    
    def calculate_opacity(self, event_time: datetime, current_time: datetime) -> float:
        """
        Calculate opacity for an event based on age.
        
        Formula: Opacity(E) = max(0, 1 - (t_current - t_event) / decay_window)
        
        Args:
            event_time: Timestamp of the event
            current_time: Current display timestamp
            
        Returns:
            Opacity value between 0 and 1
        """
        if event_time >= current_time:
            return 1.0
        
        age_hours = (current_time - event_time).total_seconds() / 3600
        opacity = max(0.0, 1.0 - (age_hours / self.decay_window))
        return opacity


# =============================================================================
# TEMPORAL ENGINE
# =============================================================================

class TemporalEngine:
    """
    High-performance temporal analysis engine for Command Center.
    
    Handles:
    - Slicing UnifiedResult into daily segments
    - High-speed frame retrieval with lookback window
    - Dynamic momentum calculation per slice
    - Temporal fading calculations
    
    Example:
        >>> engine = TemporalEngine(window=7, lookback_hours=72)
        >>> temporal_result = engine.slice_result(unified_result)
        >>> frame = engine.get_frame(temporal_result, current_timestamp)
    """
    
    def __init__(
        self,
        window: int = 7,
        min_data_points: int = 3,
        lookback_hours: int = 72,
    ):
        """
        Initialize the temporal engine.
        
        Args:
            window: Rolling window size for momentum calculation
            min_data_points: Minimum data points required for valid slice
            lookback_hours: Hours to look back for fading (default 72 = 3 days)
        """
        self.window = window
        self.min_data_points = min_data_points
        self.lookback_hours = lookback_hours
    
    def slice_result(
        self,
        time_series_df: pd.DataFrame,
        geo_df: pd.DataFrame,
        date_col: str = "record_date",
    ) -> TemporalResult:
        """
        Slice data into daily temporal segments with high-speed indexing.
        
        Args:
            time_series_df: Time series DataFrame
            geo_df: Geographic DataFrame
            date_col: Date column name
            
        Returns:
            TemporalResult with daily slices and indexed geo data
        """
        result = TemporalResult()
        
        if time_series_df.empty:
            logger.warning("Empty time series data for temporal slicing")
            return result
        
        # Ensure date column is datetime
        ts_df = time_series_df.copy()
        if date_col in ts_df.columns:
            ts_df[date_col] = pd.to_datetime(ts_df[date_col])
        else:
            logger.error(f"Date column '{date_col}' not found")
            return result
        
        # Get date range
        min_date = ts_df[date_col].min()
        max_date = ts_df[date_col].max()
        result.date_range = (min_date, max_date)
        result.total_days = (max_date - min_date).days + 1
        
        # Calculate rolling statistics for momentum
        ts_df = ts_df.sort_values(date_col)
        if "mention_count" in ts_df.columns:
            ts_df["rolling_mean"] = ts_df["mention_count"].rolling(
                window=self.window, min_periods=1
            ).mean()
            ts_df["rolling_std"] = ts_df["mention_count"].rolling(
                window=self.window, min_periods=1
            ).std().fillna(1)
        
        # Build high-speed geo index
        # v4.3.1: More robust handling when record_date is missing
        has_temporal_geo = not geo_df.empty and date_col in geo_df.columns
        
        if has_temporal_geo:
            geo_indexed = geo_df.copy()
            geo_indexed[date_col] = pd.to_datetime(geo_indexed[date_col])
            geo_indexed = geo_indexed.sort_values(date_col)
            result._geo_index = geo_indexed
            result._sorted_timestamps = sorted(geo_indexed[date_col].unique())
            logger.info(f"Built geo index with {len(result._sorted_timestamps)} temporal points")
        elif not geo_df.empty:
            # v4.3.1: Geo data exists but no record_date - use as static fallback
            logger.warning(
                f"Geo data has no '{date_col}' column. Available columns: {list(geo_df.columns)}. "
                "Chronos temporal replay will use static geo data."
            )
            # Store static geo data for fallback
            result._geo_index = geo_df.copy()
            result._sorted_timestamps = []
        else:
            logger.warning("No geo data available for temporal indexing")
        
        # Create slices for each unique date
        for date in ts_df[date_col].unique():
            date_str = pd.Timestamp(date).strftime("%Y-%m-%d")
            
            # Filter data for this date
            day_ts = ts_df[ts_df[date_col] == date]
            day_geo = pd.DataFrame()
            
            if has_temporal_geo:
                geo_df_copy = geo_df.copy()
                geo_df_copy[date_col] = pd.to_datetime(geo_df_copy[date_col])
                day_geo = geo_df_copy[geo_df_copy[date_col] == date]
            elif not geo_df.empty:
                # v4.3.1: Use static geo data for all slices
                day_geo = geo_df.copy()
            
            # Calculate slice metrics
            mention_count = int(day_ts["mention_count"].sum()) if "mention_count" in day_ts.columns else 0
            sentiment_avg = float(day_ts["sentiment_score"].mean()) if "sentiment_score" in day_ts.columns else 0.0
            
            # Calculate momentum Z-score for this slice
            momentum_zscore = 0.0
            if "mention_count" in day_ts.columns and not day_ts.empty:
                row = day_ts.iloc[-1]
                if "rolling_mean" in row and "rolling_std" in row:
                    mean = row.get("rolling_mean", mention_count)
                    std = row.get("rolling_std", 1)
                    if std > 0:
                        momentum_zscore = (mention_count - mean) / std
            
            # Create slice
            slice_obj = TemporalSlice(
                timestamp=pd.Timestamp(date).to_pydatetime(),
                time_series=day_ts,
                geo_data=day_geo,
                momentum_zscore=float(momentum_zscore),
                sentiment_avg=float(sentiment_avg),
                mention_count=mention_count,
            )
            
            result.slices[date_str] = slice_obj
        
        # Calculate aggregated metrics
        result.aggregated = self._calculate_aggregated(result)
        
        logger.info(f"Created {len(result.slices)} temporal slices with high-speed index")
        
        return result
    
    def get_frame(
        self,
        result: TemporalResult,
        timestamp: datetime,
        lookback_hours: Optional[int] = None,
    ) -> TemporalFrame:
        """
        High-speed frame retrieval for a specific timestamp.
        
        v4.3.1: Now handles static geo data fallback when record_date is missing.
        
        Retrieves all events at the given timestamp plus events
        within the lookback window, with age metadata for fading.
        
        Args:
            result: TemporalResult with indexed data
            timestamp: Target timestamp
            lookback_hours: Override default lookback (hours)
            
        Returns:
            TemporalFrame with current and lookback events
        """
        lookback = lookback_hours or self.lookback_hours
        lookback_start = timestamp - timedelta(hours=lookback)
        
        # Initialize empty frame
        frame = TemporalFrame(
            timestamp=timestamp,
            current_events=pd.DataFrame(),
            lookback_events=pd.DataFrame(),
        )
        
        if result._geo_index.empty:
            return frame
        
        geo_df = result._geo_index
        date_col = "record_date"
        
        # v4.3.1: Check if we have temporal data or static fallback
        has_temporal_data = date_col in geo_df.columns and len(result._sorted_timestamps) > 0
        
        if has_temporal_data:
            # Fast timestamp filtering using sorted index
            # Current day events
            current_day_start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            current_day_end = current_day_start + timedelta(days=1)
            
            current_mask = (geo_df[date_col] >= current_day_start) & (geo_df[date_col] < current_day_end)
            current_events = geo_df[current_mask].copy()
            
            if not current_events.empty:
                current_events["_age_hours"] = 0
                current_events["_opacity"] = 1.0
                frame.current_events = current_events
            
            # Lookback events (excluding current day)
            lookback_mask = (geo_df[date_col] >= lookback_start) & (geo_df[date_col] < current_day_start)
            lookback_events = geo_df[lookback_mask].copy()
            
            if not lookback_events.empty:
                # Calculate age and opacity for each event
                lookback_events["_age_hours"] = lookback_events[date_col].apply(
                    lambda t: (timestamp - t).total_seconds() / 3600
                )
                lookback_events["_opacity"] = lookback_events["_age_hours"].apply(
                    lambda age: max(0.0, 1.0 - (age / lookback))
                )
                frame.lookback_events = lookback_events
        else:
            # v4.3.1: Static fallback - use all geo data for current frame
            current_events = geo_df.copy()
            current_events["_age_hours"] = 0
            current_events["_opacity"] = 1.0
            frame.current_events = current_events
            logger.debug("Using static geo data fallback for frame (no record_date)")
        
        # Get metrics from slice if available
        date_str = timestamp.strftime("%Y-%m-%d")
        if date_str in result.slices:
            slice_data = result.slices[date_str]
            frame.momentum_zscore = slice_data.momentum_zscore
            frame.sentiment_avg = slice_data.sentiment_avg
            frame.mention_count = slice_data.mention_count
        
        return frame
    
    def _calculate_aggregated(self, result: TemporalResult) -> Dict[str, Any]:
        """Calculate aggregated metrics across all slices."""
        if not result.slices:
            return {}
        
        total_mentions = sum(s.mention_count for s in result.slices.values())
        avg_sentiment = np.mean([s.sentiment_avg for s in result.slices.values()])
        max_momentum = max(s.momentum_zscore for s in result.slices.values())
        min_momentum = min(s.momentum_zscore for s in result.slices.values())
        
        return {
            "total_mentions": total_mentions,
            "avg_sentiment": avg_sentiment,
            "max_momentum": max_momentum,
            "min_momentum": min_momentum,
            "momentum_range": max_momentum - min_momentum,
        }
    
    def get_replay_frames(
        self,
        result: TemporalResult,
        fps: int = 2,
    ) -> Generator[TemporalSlice, None, None]:
        """
        Generate frames for replay animation.
        
        Args:
            result: TemporalResult to replay
            fps: Frames per second (slices per second)
            
        Yields:
            TemporalSlice objects in chronological order
        """
        dates = sorted(result.slices.keys())
        for date_str in dates:
            yield result.slices[date_str]


# =============================================================================
# NEWS TICKER GENERATOR
# =============================================================================

class NewsTicker:
    """
    Generate scrolling news ticker data from GDELT results.
    
    Creates formatted ticker items with:
    - Timestamp
    - Country/Region
    - Key entities
    - Sentiment indicator
    """
    
    @staticmethod
    def generate_ticker_items(
        frame: TemporalFrame,
        max_items: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Generate ticker items from a temporal frame.
        
        Args:
            frame: TemporalFrame to process
            max_items: Maximum ticker items to generate
            
        Returns:
            List of ticker item dictionaries
        """
        items = []
        
        # Get events from frame
        events_df = frame.all_events
        
        if events_df.empty:
            return items
        
        # Sort by recency and mentions
        if "mention_count" in events_df.columns:
            events_df = events_df.nlargest(max_items, "mention_count")
        else:
            events_df = events_df.head(max_items)
        
        for _, row in events_df.iterrows():
            sentiment = row.get("sentiment_score", 0)
            sentiment_icon = "▲" if sentiment > 0 else "▼" if sentiment < 0 else "●"
            opacity = row.get("_opacity", 1.0)
            
            location = row.get("country_name", row.get("iso3", "Unknown"))
            mentions = int(row.get("mention_count", 0))
            
            items.append({
                "timestamp": frame.timestamp.strftime("%H:%M"),
                "location": location,
                "mentions": mentions,
                "sentiment": sentiment,
                "sentiment_icon": sentiment_icon,
                "opacity": opacity,
                "formatted": f"[{frame.timestamp.strftime('%H:%M')}] {location}: {mentions} {sentiment_icon}",
            })
        
        return items[:max_items]
    
    @staticmethod
    def format_ticker_line(items: List[Dict[str, Any]], separator: str = " │ ") -> str:
        """
        Format ticker items into a single scrolling line.
        
        Args:
            items: List of ticker item dictionaries
            separator: Separator between items
            
        Returns:
            Formatted ticker string
        """
        formatted_items = [item["formatted"] for item in items]
        return separator.join(formatted_items)
    
    @staticmethod
    def generate_from_slice(
        slice_data: TemporalSlice,
        max_items: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Generate ticker items from a TemporalSlice (backward compat).
        
        Args:
            slice_data: TemporalSlice to process
            max_items: Maximum ticker items to generate
            
        Returns:
            List of ticker item dictionaries
        """
        items = []
        
        if slice_data.geo_data.empty:
            return items
        
        geo_df = slice_data.geo_data
        if "mention_count" in geo_df.columns:
            geo_df = geo_df.nlargest(max_items, "mention_count")
        else:
            geo_df = geo_df.head(max_items)
        
        for _, row in geo_df.iterrows():
            sentiment = row.get("sentiment_score", 0)
            sentiment_icon = "▲" if sentiment > 0 else "▼" if sentiment < 0 else "●"
            
            items.append({
                "timestamp": slice_data.timestamp.strftime("%H:%M"),
                "location": row.get("country_name", row.get("iso3", "Unknown")),
                "mentions": int(row.get("mention_count", 0)),
                "sentiment": sentiment,
                "sentiment_icon": sentiment_icon,
                "opacity": 1.0,
                "formatted": f"[{slice_data.timestamp.strftime('%H:%M')}] {row.get('country_name', 'Unknown')}: {int(row.get('mention_count', 0))} {sentiment_icon}",
            })
        
        return items[:max_items]


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_temporal_result(
    time_series_df: pd.DataFrame,
    geo_df: pd.DataFrame,
    window: int = 7,
    lookback_hours: int = 72,
) -> TemporalResult:
    """
    Convenience function to create a TemporalResult.
    
    Args:
        time_series_df: Time series DataFrame
        geo_df: Geographic DataFrame
        window: Rolling window for momentum calculation
        lookback_hours: Lookback window for fading
        
    Returns:
        TemporalResult with sliced data and index
    """
    engine = TemporalEngine(window=window, lookback_hours=lookback_hours)
    return engine.slice_result(time_series_df, geo_df)


def get_global_replay_state() -> ReplayState:
    """
    Get or create global replay state.
    
    Should be called after importing streamlit:
        import streamlit as st
        state = get_global_replay_state()
    
    Returns:
        ReplayState from session_state
    """
    try:
        import streamlit as st
        if "replay_state" not in st.session_state:
            st.session_state.replay_state = ReplayState()
        return st.session_state.replay_state
    except ImportError:
        return ReplayState()
