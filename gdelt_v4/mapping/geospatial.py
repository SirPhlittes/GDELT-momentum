"""
GDELT v4.3 Geospatial Module (GAIA)
====================================
3D tactical globe visualization with temporal fading.

Features:
- 3D globe with satellite basemap
- Temporal fading engine (events fade based on age)
- Dynamic opacity calculation
- Command Center integration

Author: Philip Hendrik Littau
Version: 4.3.0
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

try:
    import pydeck as pdk
    PYDECK_AVAILABLE = True
except ImportError:
    PYDECK_AVAILABLE = False


# =============================================================================
# GAIA COLOR PALETTE (Deep Obsidian)
# =============================================================================

GAIA_PALETTE = {
    # Backgrounds
    "background": "#050505",
    "surface": "#0A0A0A",
    "elevated": "#111111",
    
    # Primary colors
    "slate_blue": "#5A7D9A",
    "muted_sage": "#7D9A7D",
    
    # Accent colors
    "accent_warm": "#D4A574",
    "accent_cold": "#74A5D4",
    "accent_alert": "#D47474",
    
    # Text
    "text_primary": "#E6EDF3",
    "text_secondary": "#8B949E",
    "text_muted": "#5A5A5A",
    
    # Borders
    "border": "#2A2A2A",
    "border_subtle": "#1F1F1F",
    
    # Temporal colors (for fading)
    "current": [125, 154, 125, 255],      # Muted Sage - 100% opacity
    "recent": [90, 125, 154, 200],        # Slate Blue - fading
    "old": [90, 125, 154, 100],           # Slate Blue - more faded
    "ancient": [90, 125, 154, 50],        # Slate Blue - almost gone
}


# =============================================================================
# GLOBE CONFIGURATION
# =============================================================================

GLOBE_CONFIG = {
    "mapbox_style": "mapbox://styles/mapbox/satellite-v9",
    "initial_view": {
        "latitude": 25,
        "longitude": 10,
        "zoom": 1.5,
        "pitch": 40,
        "bearing": 0,
    },
    "controller": {
        "scrollZoom": True,
        "dragPan": True,
        "dragRotate": True,
        "doubleClickZoom": True,
    },
}


# =============================================================================
# TEMPORAL FADING ENGINE
# =============================================================================

class TemporalFadingEngine:
    """
    Engine for calculating temporal fading effects on map layers.
    
    Events fade from Muted Sage (current) to Slate Blue (old) based on age.
    
    Formula: Opacity(E) = max(0, 1 - (t_current - t_event) / decay_window)
    """
    
    def __init__(
        self,
        decay_window_hours: int = 72,
        current_color: List[int] = None,
        faded_color: List[int] = None,
    ):
        """
        Initialize the fading engine.
        
        Args:
            decay_window_hours: Hours over which events fully fade
            current_color: RGBA color for current events [R, G, B, A]
            faded_color: RGBA color for fully faded events
        """
        self.decay_window = decay_window_hours
        self.current_color = current_color or GAIA_PALETTE["current"]
        self.faded_color = faded_color or GAIA_PALETTE["ancient"]
    
    def calculate_opacity(
        self,
        event_time: datetime,
        current_time: datetime,
    ) -> float:
        """
        Calculate opacity for an event based on age.
        
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
    
    def calculate_color(
        self,
        event_time: datetime,
        current_time: datetime,
    ) -> List[int]:
        """
        Calculate interpolated color for an event based on age.
        
        Current events: Muted Sage
        Old events: Slate Blue with reduced opacity
        
        Args:
            event_time: Timestamp of the event
            current_time: Current display timestamp
            
        Returns:
            RGBA color list [R, G, B, A]
        """
        opacity = self.calculate_opacity(event_time, current_time)
        
        # Interpolate between colors based on age
        t = 1.0 - opacity  # t=0 is current, t=1 is fully faded
        
        # Current color (Muted Sage)
        c1 = self.current_color
        # Faded color (Slate Blue, reduced opacity)
        c2 = self.faded_color
        
        return [
            int(c1[0] + t * (c2[0] - c1[0])),
            int(c1[1] + t * (c2[1] - c1[1])),
            int(c1[2] + t * (c2[2] - c1[2])),
            int(c1[3] * opacity),  # Opacity fades
        ]
    
    def apply_to_dataframe(
        self,
        df: pd.DataFrame,
        current_time: datetime,
        date_col: str = "record_date",
    ) -> pd.DataFrame:
        """
        Apply temporal fading to a DataFrame of events.
        
        Adds columns: _opacity, _color_r, _color_g, _color_b, _color_a
        
        Args:
            df: DataFrame with events
            current_time: Current display timestamp
            date_col: Column containing event timestamps
            
        Returns:
            DataFrame with fading columns added
        """
        if df.empty or date_col not in df.columns:
            return df
        
        result = df.copy()
        
        # Ensure datetime
        result[date_col] = pd.to_datetime(result[date_col])
        
        # Calculate opacity for each event
        result["_opacity"] = result[date_col].apply(
            lambda t: self.calculate_opacity(t, current_time)
        )
        
        # Filter out fully faded events
        result = result[result["_opacity"] > 0.05]
        
        if result.empty:
            return result
        
        # Calculate colors
        colors = result[date_col].apply(
            lambda t: self.calculate_color(t, current_time)
        )
        
        result["_color_r"] = colors.apply(lambda c: c[0])
        result["_color_g"] = colors.apply(lambda c: c[1])
        result["_color_b"] = colors.apply(lambda c: c[2])
        result["_color_a"] = colors.apply(lambda c: c[3])
        
        return result


# =============================================================================
# GAIA GLOBE RENDERER
# =============================================================================

def render_gaia_globe(
    df: pd.DataFrame,
    current_timestamp: Optional[datetime] = None,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    size_col: str = "mention_count",
    date_col: str = "record_date",
    decay_window_hours: int = 72,
    height: int = 600,
    show_heatmap: bool = False,
) -> Optional["pdk.Deck"]:
    """
    Render the GAIA tactical globe with temporal fading.
    
    Args:
        df: DataFrame with geographic events
        current_timestamp: Current time for fading calculation
        lat_col: Latitude column name
        lon_col: Longitude column name
        size_col: Column for point size scaling
        date_col: Column with event timestamps
        decay_window_hours: Hours for fading effect
        height: Map height in pixels
        show_heatmap: Show heatmap layer instead of scatter
        
    Returns:
        Pydeck Deck object or None
    """
    if not PYDECK_AVAILABLE:
        return None
    
    if df.empty:
        return None
    
    # Prepare data
    globe_df = prepare_geo_data_for_globe(df, lat_col, lon_col)
    
    if globe_df.empty:
        return None
    
    # Apply temporal fading if timestamp provided
    if current_timestamp is not None and date_col in globe_df.columns:
        fading_engine = TemporalFadingEngine(decay_window_hours=decay_window_hours)
        globe_df = fading_engine.apply_to_dataframe(globe_df, current_timestamp, date_col)
    else:
        # Default styling without fading
        globe_df["_opacity"] = 1.0
        globe_df["_color_r"] = GAIA_PALETTE["current"][0]
        globe_df["_color_g"] = GAIA_PALETTE["current"][1]
        globe_df["_color_b"] = GAIA_PALETTE["current"][2]
        globe_df["_color_a"] = GAIA_PALETTE["current"][3]
    
    if globe_df.empty:
        return None
    
    # Normalize size
    if size_col in globe_df.columns:
        max_size = globe_df[size_col].max()
        if max_size > 0:
            globe_df["_size"] = (globe_df[size_col] / max_size) * 100000
        else:
            globe_df["_size"] = 50000
    else:
        globe_df["_size"] = 50000
    
    # Create layer
    if show_heatmap:
        layer = pdk.Layer(
            "HeatmapLayer",
            data=globe_df,
            get_position=[lon_col, lat_col],
            get_weight="_size",
            radiusPixels=50,
            intensity=1,
            threshold=0.1,
            color_range=[
                [90, 125, 154, 50],
                [90, 125, 154, 100],
                [125, 154, 125, 150],
                [125, 154, 125, 200],
            ],
        )
    else:
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=globe_df,
            get_position=[lon_col, lat_col],
            get_radius="_size",
            radius_scale=1,
            radius_min_pixels=3,
            radius_max_pixels=40,
            get_fill_color=["_color_r", "_color_g", "_color_b", "_color_a"],
            pickable=True,
            opacity=0.9,
            stroked=True,
            get_line_color=[255, 255, 255, 50],
            line_width_min_pixels=1,
        )
    
    view_state = pdk.ViewState(
        latitude=GLOBE_CONFIG["initial_view"]["latitude"],
        longitude=GLOBE_CONFIG["initial_view"]["longitude"],
        zoom=GLOBE_CONFIG["initial_view"]["zoom"],
        pitch=GLOBE_CONFIG["initial_view"]["pitch"],
        bearing=GLOBE_CONFIG["initial_view"]["bearing"],
    )
    
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style=GLOBE_CONFIG["mapbox_style"],
        tooltip={
            "html": _generate_command_center_tooltip(),
            "style": _get_tooltip_style(),
        },
    )
    
    return deck


def render_command_center_globe(
    current_events: pd.DataFrame,
    lookback_events: pd.DataFrame,
    current_timestamp: datetime,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    height: int = 600,
) -> Optional["pdk.Deck"]:
    """
    Render Command Center globe with dual-layer visualization.
    
    Current events: Bright Muted Sage
    Lookback events: Fading Slate Blue
    
    Args:
        current_events: Events at current timestamp
        lookback_events: Events within lookback window (with _opacity column)
        current_timestamp: Current display timestamp
        lat_col: Latitude column name
        lon_col: Longitude column name
        height: Map height in pixels
        
    Returns:
        Pydeck Deck object or None
    """
    if not PYDECK_AVAILABLE:
        return None
    
    layers = []
    
    # Lookback layer (faded slate blue)
    if not lookback_events.empty and lat_col in lookback_events.columns:
        lookback_df = prepare_geo_data_for_globe(lookback_events, lat_col, lon_col)
        
        if not lookback_df.empty:
            # Apply opacity-based coloring
            if "_opacity" not in lookback_df.columns:
                lookback_df["_opacity"] = 0.5
            
            lookback_df["_color_r"] = 90
            lookback_df["_color_g"] = 125
            lookback_df["_color_b"] = 154
            lookback_df["_color_a"] = (lookback_df["_opacity"] * 150).astype(int)
            
            if "mention_count" in lookback_df.columns:
                max_size = lookback_df["mention_count"].max()
                lookback_df["_size"] = (lookback_df["mention_count"] / max(max_size, 1)) * 80000
            else:
                lookback_df["_size"] = 40000
            
            lookback_layer = pdk.Layer(
                "ScatterplotLayer",
                data=lookback_df,
                get_position=[lon_col, lat_col],
                get_radius="_size",
                radius_scale=1,
                radius_min_pixels=2,
                radius_max_pixels=30,
                get_fill_color=["_color_r", "_color_g", "_color_b", "_color_a"],
                pickable=True,
                opacity=0.7,
            )
            layers.append(lookback_layer)
    
    # Current events layer (bright muted sage)
    if not current_events.empty and lat_col in current_events.columns:
        current_df = prepare_geo_data_for_globe(current_events, lat_col, lon_col)
        
        if not current_df.empty:
            current_df["_color_r"] = 125
            current_df["_color_g"] = 154
            current_df["_color_b"] = 125
            current_df["_color_a"] = 255
            
            if "mention_count" in current_df.columns:
                max_size = current_df["mention_count"].max()
                current_df["_size"] = (current_df["mention_count"] / max(max_size, 1)) * 100000
            else:
                current_df["_size"] = 50000
            
            current_layer = pdk.Layer(
                "ScatterplotLayer",
                data=current_df,
                get_position=[lon_col, lat_col],
                get_radius="_size",
                radius_scale=1,
                radius_min_pixels=4,
                radius_max_pixels=50,
                get_fill_color=["_color_r", "_color_g", "_color_b", "_color_a"],
                pickable=True,
                opacity=1.0,
                stroked=True,
                get_line_color=[255, 255, 255, 100],
                line_width_min_pixels=2,
            )
            layers.append(current_layer)
    
    if not layers:
        return None
    
    view_state = pdk.ViewState(
        latitude=25,
        longitude=10,
        zoom=1.5,
        pitch=40,
        bearing=0,
    )
    
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=GLOBE_CONFIG["mapbox_style"],
        tooltip={
            "html": _generate_command_center_tooltip(),
            "style": _get_tooltip_style(),
        },
    )
    
    return deck


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def prepare_geo_data_for_globe(
    df: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
) -> pd.DataFrame:
    """
    Prepare geographic data for globe visualization.
    
    Args:
        df: Input DataFrame
        lat_col: Latitude column name
        lon_col: Longitude column name
        
    Returns:
        Cleaned DataFrame ready for visualization
    """
    if df.empty:
        return df
    
    result = df.copy()
    
    # Ensure coordinate columns exist
    if lat_col not in result.columns:
        result[lat_col] = 0.0
    if lon_col not in result.columns:
        result[lon_col] = 0.0
    
    # Convert to numeric
    result[lat_col] = pd.to_numeric(result[lat_col], errors="coerce")
    result[lon_col] = pd.to_numeric(result[lon_col], errors="coerce")
    
    # Filter invalid coordinates
    result = result[
        result[lat_col].notna() &
        result[lon_col].notna() &
        (result[lat_col].abs() <= 90) &
        (result[lon_col].abs() <= 180) &
        ((result[lat_col] != 0) | (result[lon_col] != 0))
    ]
    
    return result


def _generate_command_center_tooltip() -> str:
    """Generate HTML template for Command Center tooltip."""
    return """
    <div style="font-family: 'IBM Plex Mono', monospace; min-width: 180px;">
        <div style="font-size: 12px; font-weight: 600; color: #7D9A7D; margin-bottom: 6px; border-bottom: 1px solid #2A2A2A; padding-bottom: 4px;">
            ◉ {country_name}
        </div>
        <div style="font-size: 10px; color: #8B949E; line-height: 1.6;">
            <div>MENTIONS <span style="color: #5A7D9A; float: right;">{mention_count}</span></div>
            <div>SENTIMENT <span style="color: #7D9A7D; float: right;">{sentiment_score}</span></div>
            <div>COORDS <span style="color: #5A5A5A; float: right;">{latitude:.2f}, {longitude:.2f}</span></div>
        </div>
    </div>
    """


def _get_tooltip_style() -> Dict[str, str]:
    """Get tooltip CSS style."""
    return {
        "backgroundColor": "#0A0A0A",
        "color": "#E6EDF3",
        "fontFamily": "'IBM Plex Mono', monospace",
        "fontSize": "11px",
        "padding": "10px",
        "borderRadius": "2px",
        "border": "1px solid #2A2A2A",
        "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.5)",
    }


# =============================================================================
# CSS FILTERS FOR OBSIDIAN LOOK
# =============================================================================

def get_map_css_filter() -> str:
    """
    Get CSS filter for satellite map to achieve Obsidian look.
    
    Apply this to the pydeck container element.
    """
    return """
    filter: 
        saturate(0.6) 
        contrast(1.1) 
        brightness(0.85);
    """


def get_command_center_css() -> str:
    """
    Get complete CSS for Command Center globe container.
    
    Returns:
        CSS string for injection
    """
    return """
    <style>
        /* Command Center Globe Container */
        .command-center-globe {
            position: relative;
            background-color: #050505;
            border: 1px solid #2A2A2A;
            border-radius: 2px;
            overflow: hidden;
        }
        
        /* Map filter for Obsidian look */
        .command-center-globe iframe,
        .command-center-globe canvas {
            filter: saturate(0.6) contrast(1.1) brightness(0.85);
        }
        
        /* HUD Overlay Container */
        .hud-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            pointer-events: none;
            z-index: 100;
        }
        
        /* HUD Controls Panel */
        .hud-controls {
            position: absolute;
            bottom: 60px;
            left: 16px;
            right: 16px;
            background: rgba(5, 5, 5, 0.85);
            border: 1px solid #2A2A2A;
            border-radius: 2px;
            padding: 12px 16px;
            pointer-events: auto;
        }
        
        /* HUD Metrics Panel */
        .hud-metrics {
            position: absolute;
            top: 16px;
            right: 16px;
            background: rgba(5, 5, 5, 0.85);
            border: 1px solid #2A2A2A;
            border-radius: 2px;
            padding: 12px 16px;
            min-width: 180px;
            pointer-events: auto;
        }
        
        /* HUD Label */
        .hud-label {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 9px;
            color: #5A5A5A;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 4px;
        }
        
        /* HUD Value */
        .hud-value {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 16px;
            color: #E6EDF3;
            font-weight: 500;
        }
        
        .hud-value.positive {
            color: #7D9A7D;
        }
        
        .hud-value.negative {
            color: #D47474;
        }
        
        /* News Ticker */
        .news-ticker-bar {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 36px;
            background: rgba(5, 5, 5, 0.9);
            border-top: 1px solid #2A2A2A;
            overflow: hidden;
            display: flex;
            align-items: center;
        }
        
        .ticker-label {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 9px;
            color: #5A5A5A;
            text-transform: uppercase;
            padding: 0 12px;
            border-right: 1px solid #2A2A2A;
        }
        
        .ticker-content {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 11px;
            color: #5A7D9A;
            white-space: nowrap;
            animation: ticker-scroll 30s linear infinite;
            padding-left: 100%;
        }
        
        @keyframes ticker-scroll {
            0% { transform: translateX(0); }
            100% { transform: translateX(-100%); }
        }
        
        /* Timestamp Badge */
        .timestamp-badge {
            position: absolute;
            top: 16px;
            left: 16px;
            background: rgba(5, 5, 5, 0.85);
            border: 1px solid #7D9A7D;
            border-radius: 2px;
            padding: 8px 12px;
            pointer-events: auto;
        }
        
        .timestamp-badge .label {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 9px;
            color: #5A5A5A;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
        
        .timestamp-badge .value {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 14px;
            color: #7D9A7D;
            font-weight: 500;
        }
    </style>
    """
