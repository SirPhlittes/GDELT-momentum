"""
GDELT v4.4 Unified Intelligence Dashboard - Command Center
============================================================
Multidimensional Analysis Update

v4.4 Features:
- Layer Selector: Tactical Momentum, Bivariate Crisis, Conflict Hubs
- @st.fragment: Smooth layer switching without full reload
- Bivariate Crisis Map: 3x3 Sentiment × Momentum color matrix
- Conflict Hubs: Protest/Conflict event visualization
- Source Trust Stacked Area Chart: Tier distribution over time
- Enhanced tooltips with Z-Score

v4.3.1 Fixes (retained):
- SQL: GEO_TEMPORAL_DAILY template with record_date for Chronos
- Temporal: Robust handling when record_date is missing
- Mapping: Centroid fallback when lat/lon is 0 or NULL
- Mapbox: Token check with dark theme fallback

Run with: streamlit run gdelt_v4/app/unified_dashboard.py

Author: Philip Hendrik Littau
Version: 4.4.0
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gdelt_v4.services.gdelt_service import GDELTService
from gdelt_v4.models.experiment import BaseExperiment, AnalysisMode
from gdelt_v4.config.settings import GDELTConfig
from gdelt_v4.query.library import (
    DOMAIN_OPTIONS,
    FOCUS_OPTIONS,
    TARGET_OPTIONS,
    assemble_query,
    validate_assembled_query,
)
from gdelt_v4.query.parser import BooleanParser
from gdelt_v4.ui.institutional_theme import (
    OBSIDIAN_PALETTE,
    get_chart_layout,
    get_map_layout,
    get_institutional_colorscale,
    render_command_header_html,
    render_hud_metrics_html,
    render_ticker_html,
)
from gdelt_v4.engines.temporal import (
    TemporalEngine,
    TemporalResult,
    TemporalSlice,
    TemporalFrame,
    ReplayState,
    NewsTicker,
    get_global_replay_state,
)
from gdelt_v4.mapping.geospatial import (
    GAIA_PALETTE,
    render_gaia_globe,
    render_command_center_globe,
    prepare_geo_data_for_globe,
    TemporalFadingEngine,
    get_command_center_css,
    PYDECK_AVAILABLE,
    # v4.4: Multidimensional analysis
    LayerMode,
    get_bivariate_color,
    apply_bivariate_colors,
    apply_conflict_colors,
    get_bivariate_legend_html,
    BIVARIATE_COLOR_MATRIX,
    CONFLICT_COLORS,
)
from gdelt_v4.mapping.country_codes import (
    get_mapper as get_country_mapper,
    get_country_centroid,
)

# Try to import pydeck
try:
    import pydeck as pdk
except ImportError:
    pdk = None


# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="GDELT Forecast Lab · Command Center",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Deep Obsidian Command Center CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');
    
    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    div[data-testid="stToolbar"] {display: none;}
    div[data-testid="stDecoration"] {display: none;}
    div[data-testid="stStatusWidget"] {display: none;}
    header {visibility: hidden;}
    [data-testid="stSidebar"] {display: none !important;}
    section[data-testid="stSidebar"] {display: none !important;}
    
    /* Root variables - Deep Obsidian */
    :root {
        --bg-deep: #050505;
        --bg-primary: #0A0A0A;
        --bg-secondary: #111111;
        --bg-tertiary: #1A1A1A;
        --border-primary: #2A2A2A;
        --border-secondary: #1F1F1F;
        --text-primary: #E6EDF3;
        --text-secondary: #8B949E;
        --text-muted: #5A5A5A;
        --slate-blue: #5A7D9A;
        --muted-sage: #7D9A7D;
        --accent-warm: #D4A574;
        --accent-cold: #74A5D4;
    }
    
    /* Main app background - Deep Obsidian */
    .stApp {
        background-color: var(--bg-deep);
    }
    
    .main .block-container {
        padding: 0.5rem 1.5rem;
        max-width: 100%;
    }
    
    /* Typography - IBM Plex Mono dominance */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif;
        color: var(--text-primary);
        font-weight: 600;
    }
    
    p, span, label, .stMarkdown {
        font-family: 'Inter', sans-serif;
        color: var(--text-secondary);
        font-size: 13px;
    }
    
    /* Fixed Command Header */
    .command-header {
        background: linear-gradient(180deg, #0A0A0A 0%, #050505 100%);
        border-bottom: 1px solid var(--border-primary);
        padding: 10px 20px;
        margin: -0.5rem -1.5rem 0.5rem -1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .header-brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .header-icon {
        color: var(--muted-sage);
        font-size: 16px;
    }
    
    .header-title {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 15px;
        font-weight: 600;
        color: var(--text-primary);
        letter-spacing: 0.02em;
    }
    
    .header-version {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        color: var(--text-muted);
        border: 1px solid var(--border-primary);
        padding: 2px 8px;
        border-radius: 2px;
    }
    
    .header-time {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        color: var(--slate-blue);
    }
    
    /* Metrics styling - Monospace */
    [data-testid="stMetricValue"] {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.4rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    [data-testid="stMetricLabel"] {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        font-weight: 500;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    
    /* Tabs styling - Command Center */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background-color: var(--bg-secondary);
        border-bottom: 1px solid var(--border-primary);
        padding: 0 16px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        color: var(--text-muted);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        font-weight: 500;
        padding: 12px 20px;
        letter-spacing: 0.05em;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: transparent;
        border-bottom: 2px solid var(--muted-sage);
        color: var(--muted-sage);
    }
    
    /* Inputs - Deep dark */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        background-color: var(--bg-primary);
        border: 1px solid var(--border-primary);
        color: var(--text-primary);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 13px;
        border-radius: 2px;
    }
    
    .stTextInput label,
    .stTextArea label,
    .stNumberInput label,
    .stSelectbox label {
        color: var(--text-muted);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    
    /* Buttons - Minimal */
    .stButton > button {
        background-color: var(--bg-tertiary);
        border: 1px solid var(--border-primary);
        color: var(--text-primary);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        font-weight: 500;
        border-radius: 2px;
        letter-spacing: 0.05em;
    }
    
    .stButton > button:hover {
        background-color: var(--bg-secondary);
        border-color: var(--slate-blue);
    }
    
    .stButton > button[kind="primary"] {
        background-color: var(--muted-sage);
        border-color: var(--muted-sage);
        color: var(--bg-deep);
    }
    
    /* ========== COMMAND CENTER HUD ========== */
    
    .command-center-container {
        position: relative;
        background: var(--bg-deep);
        border: 1px solid var(--border-primary);
        border-radius: 2px;
        overflow: hidden;
    }
    
    .hud-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        pointer-events: none;
        z-index: 100;
    }
    
    .hud-metrics {
        position: absolute;
        top: 12px;
        right: 12px;
        background: rgba(5, 5, 5, 0.92);
        border: 1px solid var(--border-primary);
        border-radius: 2px;
        padding: 12px 16px;
        min-width: 180px;
        pointer-events: auto;
    }
    
    .hud-metric {
        margin-bottom: 10px;
    }
    
    .hud-metric:last-child {
        margin-bottom: 0;
    }
    
    .hud-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 9px;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 2px;
    }
    
    .hud-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    .hud-value.positive { color: var(--muted-sage); }
    .hud-value.negative { color: #D47474; }
    
    .timestamp-badge {
        position: absolute;
        top: 12px;
        left: 12px;
        background: rgba(5, 5, 5, 0.92);
        border: 1px solid var(--muted-sage);
        border-radius: 2px;
        padding: 8px 12px;
        pointer-events: auto;
    }
    
    .timestamp-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 8px;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    
    .timestamp-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 13px;
        color: var(--muted-sage);
        font-weight: 600;
    }
    
    /* ========== CHRONOS CONTROL DECK ========== */
    
    .control-deck {
        background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-deep) 100%);
        border: 1px solid var(--border-primary);
        border-top: none;
        border-radius: 0 0 2px 2px;
        padding: 12px 16px;
    }
    
    .control-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 9px;
        color: var(--muted-sage);
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    
    /* Slider styling */
    .stSlider > div > div > div {
        background-color: var(--border-secondary) !important;
    }
    
    .stSlider > div > div > div > div {
        background-color: var(--slate-blue) !important;
    }
    
    /* ========== NEWS TICKER ========== */
    
    .ticker-bar {
        background: var(--bg-deep);
        border: 1px solid var(--border-primary);
        border-top: none;
        padding: 10px 16px;
        display: flex;
        align-items: center;
        overflow: hidden;
    }
    
    .ticker-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 9px;
        color: var(--muted-sage);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        padding-right: 16px;
        border-right: 1px solid var(--border-primary);
        white-space: nowrap;
    }
    
    .ticker-content {
        flex: 1;
        overflow: hidden;
        padding-left: 16px;
    }
    
    .ticker-scroll {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        color: var(--slate-blue);
        white-space: nowrap;
        display: inline-block;
        animation: ticker-scroll 40s linear infinite;
    }
    
    @keyframes ticker-scroll {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }
    
    /* ========== PYDECK OBSIDIAN FILTER ========== */
    
    [data-testid="stDeckGlChart"] iframe,
    .stDeckGlChart iframe {
        filter: saturate(0.55) contrast(1.12) brightness(0.82) !important;
    }
    
    /* DataFrames */
    .stDataFrame {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {width: 6px; height: 6px;}
    ::-webkit-scrollbar-track {background: var(--bg-deep);}
    ::-webkit-scrollbar-thumb {background: var(--border-primary); border-radius: 3px;}
    
    /* Container borders */
    [data-testid="stVerticalBlock"] > div[style*="border"] {
        border-color: var(--border-primary) !important;
        background-color: var(--bg-secondary) !important;
        border-radius: 2px !important;
    }
    
    /* Alerts */
    .stInfo {
        background-color: rgba(90, 125, 154, 0.1);
        border: 1px solid rgba(90, 125, 154, 0.3);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
    }
    
    .stSuccess {
        background-color: rgba(125, 154, 125, 0.1);
        border: 1px solid rgba(125, 154, 125, 0.3);
    }
    
    .stError {
        background-color: rgba(212, 116, 116, 0.1);
        border: 1px solid rgba(212, 116, 116, 0.3);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: var(--bg-secondary);
        border: 1px solid var(--border-primary);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE
# =============================================================================

if "experiments" not in st.session_state:
    st.session_state.experiments = []

if "results" not in st.session_state:
    st.session_state.results = {}

# Command Center temporal state
if "temporal_result" not in st.session_state:
    st.session_state.temporal_result = None

if "replay_state" not in st.session_state:
    st.session_state.replay_state = ReplayState()

if "current_frame_idx" not in st.session_state:
    st.session_state.current_frame_idx = 0

if "is_replaying" not in st.session_state:
    st.session_state.is_replaying = False

if "service" not in st.session_state:
    creds_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "ecstatic-effort-482316-r6-60e3e1bf05e1.json"
    )
    if os.path.exists(creds_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
    config = GDELTConfig.from_env()
    st.session_state.service = GDELTService(config)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_time_series_chart(df: pd.DataFrame, label: str) -> go.Figure:
    """Create institutional time series chart."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.02,
    )
    
    fig.add_trace(
        go.Scatter(
            x=df["record_date"],
            y=df["mention_count"],
            mode="lines",
            name="Volume",
            line=dict(color=GAIA_PALETTE["slate_blue"], width=1.5),
            fill="tozeroy",
            fillcolor="rgba(90, 125, 154, 0.15)",
        ),
        row=1, col=1
    )
    
    if "momentum_zscore" in df.columns:
        colors = [
            GAIA_PALETTE["muted_sage"] if z >= 0 else GAIA_PALETTE["accent_warm"]
            for z in df["momentum_zscore"]
        ]
        fig.add_trace(
            go.Bar(
                x=df["record_date"],
                y=df["momentum_zscore"],
                name="Momentum",
                marker_color=colors,
                marker_line_width=0,
            ),
            row=2, col=1
        )
        fig.add_hline(y=0, row=2, col=1, line_color="#2A2A2A", line_width=1)
    
    fig.update_layout(
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Mono", color="#8B949E", size=10),
        showlegend=False,
        margin=dict(l=50, r=20, t=20, b=40),
        xaxis=dict(gridcolor="#1F1F1F", linecolor="#2A2A2A"),
        xaxis2=dict(gridcolor="#1F1F1F", linecolor="#2A2A2A"),
        yaxis=dict(gridcolor="#1F1F1F", linecolor="#2A2A2A", title="VOLUME"),
        yaxis2=dict(gridcolor="#1F1F1F", linecolor="#2A2A2A", title="Z-SCORE"),
    )
    
    return fig


def create_entity_chart(df: pd.DataFrame, entity_type: str) -> go.Figure:
    """Create institutional entity bar chart."""
    if df.empty:
        return None
    
    color = GAIA_PALETTE["slate_blue"] if entity_type == "person" else GAIA_PALETTE["muted_sage"]
    
    fig = go.Figure(go.Bar(
        x=df["mention_count"],
        y=df["entity_name"],
        orientation="h",
        marker_color=color,
        marker_line_width=0,
        text=df["mention_count"],
        textposition="inside",
        textfont=dict(family="IBM Plex Mono", size=10, color="#050505"),
    ))
    
    fig.update_layout(
        height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Mono", color="#8B949E", size=10),
        margin=dict(l=140, r=20, t=10, b=30),
        xaxis=dict(showgrid=False, linecolor="#2A2A2A"),
        yaxis=dict(showgrid=False, autorange="reversed", linecolor="#2A2A2A"),
    )
    
    return fig


def create_geo_map(df: pd.DataFrame, z_col: str, title: str) -> go.Figure:
    """Create institutional choropleth map."""
    if df.empty or "iso3" not in df.columns:
        return None
    
    colorscale = [[0, "#1F2937"], [0.5, "#2D4A5E"], [1, "#5A7D9A"]]
    
    fig = go.Figure(go.Choropleth(
        locations=df["iso3"],
        z=df[z_col],
        locationmode="ISO-3",
        colorscale=colorscale,
        marker_line_color="#1F1F1F",
        marker_line_width=0.3,
        colorbar=dict(
            title=dict(text=title.upper(), font=dict(family="IBM Plex Mono", size=9, color="#5A5A5A")),
            tickfont=dict(family="IBM Plex Mono", size=9, color="#5A5A5A"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="#2A2A2A",
            borderwidth=1,
            len=0.5,
            thickness=10,
        ),
        hovertemplate="<b>%{text}</b><br>" + f"{title}: %{{z:.2f}}<br><extra></extra>",
        text=df.get("country_name", df["iso3"]),
    ))
    
    fig.update_layout(
        height=450,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        geo=dict(
            bgcolor="rgba(0,0,0,0)",
            showframe=False,
            showcoastlines=True,
            coastlinecolor="#2A2A2A",
            coastlinewidth=0.5,
            showland=True,
            landcolor="#0A0A0A",
            showocean=True,
            oceancolor="#050505",
            showcountries=True,
            countrycolor="#1F1F1F",
            countrywidth=0.3,
            showlakes=False,
            projection_type="equirectangular",
        ),
    )
    
    return fig


# =============================================================================
# COMMAND HEADER
# =============================================================================

st.markdown(f"""
<div class="command-header">
    <div class="header-brand">
        <span class="header-icon">◉</span>
        <span class="header-title">GDELT FORECAST LAB</span>
        <span class="header-version">v4.4 · MULTIDIMENSIONAL</span>
    </div>
    <div class="header-time">{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</div>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# NAVIGATION TABS
# =============================================================================

tabs = st.tabs(["📝 QUERY", "◉ COMMAND CENTER", "📊 INTEL", "👤 ENTITIES", "🛡️ INTEGRITY"])


# =============================================================================
# TAB 0: QUERY BUILDER
# =============================================================================

with tabs[0]:
    st.markdown("### Query Assembly System")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.container(border=True):
            st.markdown("##### Tactical Query Builder")
            
            c1, c2 = st.columns(2)
            with c1:
                label = st.text_input("EXPERIMENT ID", placeholder="e.g., CHINA_TRADE_Q4")
            with c2:
                mode = st.selectbox(
                    "MODE",
                    ["basic", "entities", "source_trust", "full"],
                    format_func=lambda x: {"basic": "STANDARD", "entities": "ENTITIES", "source_trust": "INTEGRITY", "full": "COMPREHENSIVE"}.get(x, x.upper())
                )
            
            st.markdown("---")
            st.markdown("##### Query Components")
            
            domain_selection = st.selectbox(
                "DOMAIN",
                options=[opt[0] for opt in DOMAIN_OPTIONS],
                format_func=lambda x: next((opt[1] for opt in DOMAIN_OPTIONS if opt[0] == x), x),
            )
            
            focus_selection = st.selectbox(
                "FOCUS",
                options=[opt[0] for opt in FOCUS_OPTIONS],
                format_func=lambda x: next((opt[1] for opt in FOCUS_OPTIONS if opt[0] == x), x),
            )
            
            target_selection = st.selectbox(
                "TARGET",
                options=[opt[0] for opt in TARGET_OPTIONS],
                format_func=lambda x: next((opt[1] for opt in TARGET_OPTIONS if opt[0] == x), x),
            )
            
            custom_keywords = st.text_input(
                "CUSTOM KEYWORDS (Optional)",
                placeholder="e.g., EPSTEIN, TRUMP",
            )
            
            st.markdown("---")
            
            assembled_query = assemble_query(
                domain=domain_selection,
                focus=focus_selection,
                target=target_selection,
                custom_keywords=custom_keywords,
            )
            
            if assembled_query:
                st.markdown("##### Assembled Query")
                st.code(assembled_query, language=None)
                
                is_valid, error_msg = validate_assembled_query(assembled_query)
                if not is_valid:
                    st.error(f"Validation: {error_msg}")
                else:
                    try:
                        parser = BooleanParser()
                        parsed = parser.parse(assembled_query)
                        if parsed.is_empty():
                            st.warning("Query parsed but resulted in empty conditions")
                        else:
                            st.success("✓ Query valid")
                    except Exception as e:
                        st.error(f"Parser: {str(e)}")
            else:
                st.info("Select at least one component to assemble a query")
            
            st.markdown("---")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                days = st.number_input("DAYS", min_value=1, max_value=30, value=7)
            with c2:
                sample = st.number_input("SAMPLE %", min_value=1, max_value=100, value=10)
            with c3:
                st.markdown("")
                st.markdown("")
                if st.button("➕ ADD", use_container_width=True, type="primary"):
                    if not label:
                        st.warning("Required: Experiment ID")
                    elif not assembled_query:
                        st.warning("Required: At least one query component")
                    else:
                        is_valid, error_msg = validate_assembled_query(assembled_query)
                        if not is_valid:
                            st.error(f"Cannot add: {error_msg}")
                        else:
                            try:
                                parser = BooleanParser()
                                parser.parse(assembled_query)
                                experiment = BaseExperiment.create(
                                    label=label,
                                    boolean_string=assembled_query,
                                    days=days,
                                    sample_percent=sample,
                                    mode=mode,
                                )
                                st.session_state.experiments.append(experiment)
                                st.success(f"✓ '{label}' added")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Parse failed: {str(e)}")
    
    with col2:
        st.markdown("##### Active Experiments")
        
        if st.session_state.experiments:
            for i, exp in enumerate(st.session_state.experiments):
                with st.container(border=True):
                    cols = st.columns([4, 1])
                    with cols[0]:
                        st.markdown(f"**{exp.label}**")
                        st.caption(f"{exp.boolean_string[:30]}..." if len(exp.boolean_string) > 30 else exp.boolean_string)
                    with cols[1]:
                        if st.button("✕", key=f"del_{i}"):
                            st.session_state.experiments.pop(i)
                            st.rerun()
            
            st.markdown("")
            if st.button("🚀 EXECUTE", type="primary", use_container_width=True):
                with st.spinner("Analyzing..."):
                    results = st.session_state.service.analyze_batch(
                        st.session_state.experiments,
                        include_geo=True,
                        include_entities=mode in ("entities", "full"),
                        include_source_trust=mode in ("source_trust", "full"),
                    )
                    st.session_state.results = results
                    st.session_state.temporal_result = None  # Reset temporal for new data
                    st.success("✓ Analysis complete! Navigate to COMMAND CENTER.")
        else:
            st.info("No experiments configured.")
        
        st.markdown("##### System Status")
        if st.session_state.results:
            metrics = st.session_state.service.get_metrics()
            st.caption(f"QUERIES: {metrics['connector']['query_count']}")
            st.caption(f"DATA: {metrics['connector']['total_gb_billed']:.2f} GB")
            st.caption(f"COST: ${metrics['connector']['estimated_total_cost_usd']:.4f}")
        else:
            st.caption("AWAITING EXECUTION")


# =============================================================================
# TAB 1: COMMAND CENTER (Fused GAIA + CHRONOS) - v4.4 Multidimensional
# =============================================================================

# v4.4: Initialize layer mode in session state
if "layer_mode" not in st.session_state:
    st.session_state.layer_mode = LayerMode.TACTICAL_MOMENTUM


@st.fragment
def render_command_center_globe_fragment(
    layer_mode: str,
    globe_df: pd.DataFrame,
    current_timestamp: datetime,
    current_slice,
):
    """
    v4.4: Fragment for isolated re-rendering of globe visualization.
    
    This fragment enables smooth layer switching and temporal replay
    without full app reload.
    """
    if globe_df.empty:
        # v4.4: Layer-specific empty data messages
        if layer_mode == LayerMode.CONFLICT_HUBS:
            message = "NO CONFLICT EVENTS FOUND"
            hint = "No protest/conflict themes detected in query results"
        elif layer_mode == LayerMode.BIVARIATE_CRISIS:
            message = "NO DATA FOR BIVARIATE ANALYSIS"
            hint = "Ensure geo data with sentiment is available"
        else:
            message = "NO DATA FOR THIS FRAME"
            hint = "Adjust temporal position or check query"
        
        st.markdown(f"""
        <div style="text-align: center; padding: 80px; background: #0A0A0A; border: 1px solid #2A2A2A; border-radius: 2px;">
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #5A5A5A;">
                {message}
            </div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #3A3A3A; margin-top: 8px;">
                {hint}
            </div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Apply colors based on layer mode
    if layer_mode == LayerMode.BIVARIATE_CRISIS:
        # v4.4: Bivariate Crisis Map - Sentiment × Momentum
        globe_df = apply_bivariate_colors(
            globe_df,
            sentiment_col="sentiment_score",
            momentum_col="momentum_zscore",
        )
    elif layer_mode == LayerMode.CONFLICT_HUBS:
        # v4.4: Conflict Hubs - Protest/Conflict colors
        globe_df = apply_conflict_colors(
            globe_df,
            protest_col="protest_count",
            conflict_col="conflict_count",
        )
    else:
        # Default: Tactical Momentum with temporal fading
        fading_engine = TemporalFadingEngine(decay_window_hours=72)
        
        if "record_date" in globe_df.columns:
            globe_df = fading_engine.apply_to_dataframe(globe_df, current_timestamp)
        else:
            globe_df["_color_r"] = 125
            globe_df["_color_g"] = 154
            globe_df["_color_b"] = 125
            globe_df["_color_a"] = 200
    
    # Calculate radius based on mention count
    size_col = "mention_count" if "mention_count" in globe_df.columns else "total_events"
    if size_col in globe_df.columns:
        max_mc = globe_df[size_col].max()
        globe_df["_radius"] = (globe_df[size_col] / max(max_mc, 1)) * 80000 + 20000
    else:
        globe_df["_radius"] = 50000
    
    # Create pydeck layer
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=globe_df,
        get_position=["longitude", "latitude"],
        get_radius="_radius",
        radius_scale=1,
        radius_min_pixels=4,
        radius_max_pixels=45,
        get_fill_color=["_color_r", "_color_g", "_color_b", "_color_a"],
        pickable=True,
        opacity=0.9,
        stroked=True,
        get_line_color=[255, 255, 255, 40],
        line_width_min_pixels=1,
    )
    
    view_state = pdk.ViewState(
        latitude=20,
        longitude=0,
        zoom=1.3,
        pitch=40,
        bearing=0,
    )
    
    # v4.4: Check for Mapbox token, fallback to dark theme
    mapbox_token = os.environ.get("MAPBOX_ACCESS_TOKEN", "")
    map_style = "mapbox://styles/mapbox/satellite-v9" if mapbox_token else "dark"
    
    # v4.4: Enhanced tooltips with momentum Z-score
    tooltip_html = """<div style="font-family: 'IBM Plex Mono'; font-size: 11px;">
        <b style="color: #7D9A7D;">{country_name}</b><br/>
        Mentions: {mention_count}<br/>
        Sentiment: {sentiment_score}<br/>
        Momentum: {momentum_zscore}σ
    </div>"""
    
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style=map_style,
        tooltip={
            "html": tooltip_html,
            "style": {
                "backgroundColor": "#0A0A0A",
                "color": "#E6EDF3",
                "padding": "10px",
                "border": "1px solid #2A2A2A",
                "borderRadius": "2px",
            },
        },
    )
    
    st.pydeck_chart(deck, use_container_width=True, height=480)
    
    # v4.4: Show layer-specific legend
    if layer_mode == LayerMode.BIVARIATE_CRISIS:
        st.markdown(get_bivariate_legend_html(), unsafe_allow_html=True)
    elif layer_mode == LayerMode.CONFLICT_HUBS:
        st.markdown("""
        <div style="font-family: 'IBM Plex Mono'; font-size: 9px; color: #5A5A5A; display: flex; gap: 16px; margin-top: 8px;">
            <span><span style="color: rgb(255,180,100);">●</span> Protest</span>
            <span><span style="color: rgb(212,74,74);">●</span> Conflict</span>
            <span><span style="color: rgb(255,138,101);">●</span> Mixed</span>
        </div>
        """, unsafe_allow_html=True)
    
    if not mapbox_token:
        st.caption("ℹ️ Set MAPBOX_ACCESS_TOKEN for satellite view")


with tabs[1]:
    if not st.session_state.results:
        st.markdown("""
        <div style="text-align: center; padding: 60px 40px; background: #0A0A0A; border: 1px solid #2A2A2A; border-radius: 2px;">
            <div style="font-size: 56px; margin-bottom: 20px;">◉</div>
            <div style="font-family: 'IBM Plex Mono', monospace; color: #7D9A7D; font-size: 16px; font-weight: 600; letter-spacing: 0.1em;">
                COMMAND CENTER
            </div>
            <div style="font-family: 'IBM Plex Mono', monospace; color: #5A5A5A; font-size: 11px; margin-top: 12px;">
                GAIA Tactical Globe · CHRONOS Temporal Engine
            </div>
            <div style="font-family: 'IBM Plex Mono', monospace; color: #5A7D9A; font-size: 10px; margin-top: 24px;">
                Configure and execute an experiment to activate
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        first_label = list(st.session_state.results.keys())[0]
        first_result = st.session_state.results[first_label]
        ts_data = first_result.time_series.df
        geo_data = first_result.geo_data.df
        
        # Initialize temporal engine
        if st.session_state.temporal_result is None and not ts_data.empty:
            engine = TemporalEngine(window=7, lookback_hours=72)
            st.session_state.temporal_result = engine.slice_result(ts_data, geo_data)
        
        temporal_result = st.session_state.temporal_result
        dates = temporal_result.get_dates() if temporal_result else []
        
        if dates:
            current_idx = st.session_state.current_frame_idx
            if current_idx >= len(dates):
                current_idx = 0
                st.session_state.current_frame_idx = 0
            
            current_date = dates[current_idx]
            current_slice = temporal_result.get_slice(current_date)
            
            # Get frame with lookback for fading
            engine = TemporalEngine(lookback_hours=72)
            current_timestamp = datetime.strptime(current_date, "%Y-%m-%d")
            frame = engine.get_frame(temporal_result, current_timestamp)
            
            # ===== v4.4: LAYER SELECTOR HUD =====
            layer_col, spacer_col = st.columns([2, 5])
            with layer_col:
                layer_mode = st.selectbox(
                    "VISUALIZATION LAYER",
                    [
                        LayerMode.TACTICAL_MOMENTUM,
                        LayerMode.BIVARIATE_CRISIS,
                        LayerMode.CONFLICT_HUBS,
                    ],
                    format_func=lambda x: {
                        LayerMode.TACTICAL_MOMENTUM: "🔥 Tactical Momentum",
                        LayerMode.BIVARIATE_CRISIS: "⚡ Bivariate Crisis Map",
                        LayerMode.CONFLICT_HUBS: "⚔️ Conflict Hubs",
                    }.get(x, str(x)),
                    key="cc_layer_selector",
                    label_visibility="collapsed",
                )
                st.session_state.layer_mode = layer_mode
            
            # ===== GLOBE CONTAINER =====
            st.markdown('<div class="command-center-container">', unsafe_allow_html=True)
            
            # HUD overlays (HTML)
            momentum_class = "positive" if current_slice.momentum_zscore >= 0 else "negative"
            sentiment_class = "positive" if current_slice.sentiment_avg >= 0 else "negative"
            
            col_main, col_hud = st.columns([3, 1])
            
            with col_main:
                # v4.4: Globe rendering with Layer Selector and Fragment pattern
                if pdk is not None:
                    country_mapper = get_country_mapper()
                    
                    # v4.4: Select data source based on layer mode
                    if layer_mode == LayerMode.CONFLICT_HUBS:
                        # Use conflict data for Conflict Hubs layer
                        if first_result.has_conflict_data:
                            source_df = first_result.conflict_data.copy()
                            # Apply centroid fallback
                            if "iso3" in source_df.columns:
                                source_df = country_mapper.add_centroids_to_dataframe(
                                    source_df, iso3_column="iso3",
                                    lat_column="latitude", lon_column="longitude",
                                    overwrite_zeros=True
                                )
                        else:
                            # No conflict data available
                            source_df = pd.DataFrame()
                    else:
                        # Standard geo data for Momentum and Bivariate modes
                        source_df = frame.all_events if not frame.all_events.empty else geo_data
                        
                        # v4.3.1: Apply centroid fallback for missing coordinates
                        if "iso3" in source_df.columns:
                            source_df = country_mapper.add_centroids_to_dataframe(
                                source_df, 
                                iso3_column="iso3",
                                lat_column="latitude",
                                lon_column="longitude",
                                overwrite_zeros=True
                            )
                    
                    globe_df = prepare_geo_data_for_globe(source_df)
                    
                    # v4.4: Validate required columns before rendering
                    if layer_mode == LayerMode.BIVARIATE_CRISIS:
                        # Ensure momentum_zscore exists for Bivariate
                        if "momentum_zscore" not in globe_df.columns and not globe_df.empty:
                            globe_df["momentum_zscore"] = 0.0
                        if "sentiment_score" not in globe_df.columns and not globe_df.empty:
                            globe_df["sentiment_score"] = 0.0
                    
                    elif layer_mode == LayerMode.CONFLICT_HUBS:
                        # Ensure conflict columns exist
                        if "protest_count" not in globe_df.columns and not globe_df.empty:
                            globe_df["protest_count"] = 0
                        if "conflict_count" not in globe_df.columns and not globe_df.empty:
                            globe_df["conflict_count"] = 0
                    
                    # v4.4: Render globe with fragment pattern for smooth updates
                    render_command_center_globe_fragment(
                        layer_mode=layer_mode,
                        globe_df=globe_df,
                        current_timestamp=current_timestamp,
                        current_slice=current_slice,
                    )
                else:
                    # Fallback to Plotly choropleth
                    if "iso3" in geo_data.columns:
                        fig = create_geo_map(geo_data, "mention_count", "Volume")
                        if fig:
                            st.plotly_chart(fig, use_container_width=True, key="cc_fallback_map")
                    else:
                        st.warning("⚠️ Install pydeck for 3D globe: pip install pydeck")
            
            with col_hud:
                # HUD Metrics Panel
                st.markdown(f"""
                <div style="background: rgba(5,5,5,0.92); border: 1px solid #2A2A2A; border-radius: 2px; padding: 14px;">
                    <div class="hud-metric">
                        <div class="hud-label">Temporal Position</div>
                        <div class="hud-value" style="color: #7D9A7D;">{current_date}</div>
                    </div>
                    <div class="hud-metric" style="margin-top: 14px;">
                        <div class="hud-label">Momentum Z-Score</div>
                        <div class="hud-value {momentum_class}">{current_slice.momentum_zscore:+.2f}σ</div>
                    </div>
                    <div class="hud-metric" style="margin-top: 14px;">
                        <div class="hud-label">Sentiment</div>
                        <div class="hud-value {sentiment_class}">{current_slice.sentiment_avg:+.2f}</div>
                    </div>
                    <div class="hud-metric" style="margin-top: 14px;">
                        <div class="hud-label">Mentions</div>
                        <div class="hud-value">{current_slice.mention_count:,}</div>
                    </div>
                    <div class="hud-metric" style="margin-top: 14px;">
                        <div class="hud-label">Active Regions</div>
                        <div class="hud-value">{len(current_slice.geo_data) if current_slice.geo_data is not None else 0}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # ===== CHRONOS CONTROL DECK =====
            st.markdown('<div class="control-deck">', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
            
            with col1:
                new_idx = st.slider(
                    "TEMPORAL AXIS",
                    min_value=0,
                    max_value=len(dates) - 1,
                    value=current_idx,
                    format=f"T-%d",
                    key="chronos_slider_cc",
                    label_visibility="collapsed",
                )
                if new_idx != st.session_state.current_frame_idx:
                    st.session_state.current_frame_idx = new_idx
            
            with col2:
                if st.button("▶" if not st.session_state.is_replaying else "⏸", use_container_width=True, key="play_cc"):
                    st.session_state.is_replaying = not st.session_state.is_replaying
            
            with col3:
                if st.button("⟲", use_container_width=True, key="reset_cc"):
                    st.session_state.current_frame_idx = 0
                    st.session_state.is_replaying = False
            
            with col4:
                st.markdown(f"<div style='text-align: center; font-family: IBM Plex Mono; font-size: 11px; color: #5A7D9A; padding-top: 8px;'>{current_idx + 1}/{len(dates)}</div>", unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # ===== NEWS TICKER =====
            ticker_items = []
            if current_slice.geo_data is not None and not current_slice.geo_data.empty:
                ticker_data = NewsTicker.generate_from_slice(current_slice, max_items=8)
                ticker_items = [item["formatted"] for item in ticker_data]
            
            if ticker_items:
                ticker_text = " │ ".join(ticker_items) + " │ " + " │ ".join(ticker_items)  # Duplicate for scroll
            else:
                ticker_text = "Awaiting data feed..."
            
            st.markdown(f"""
            <div class="ticker-bar">
                <div class="ticker-label">LIVE FEED</div>
                <div class="ticker-content">
                    <div class="ticker-scroll">{ticker_text}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # ===== MOMENTUM TIMELINE =====
            st.markdown("##### Momentum Timeline")
            momentum_df = temporal_result.get_momentum_series()
            if not momentum_df.empty:
                fig = go.Figure()
                
                colors = [
                    GAIA_PALETTE["muted_sage"] if z >= 0 else GAIA_PALETTE["accent_warm"]
                    for z in momentum_df["momentum_zscore"]
                ]
                
                fig.add_trace(go.Bar(
                    x=momentum_df["date"],
                    y=momentum_df["momentum_zscore"],
                    marker_color=colors,
                    name="Z-Score",
                ))
                
                # Current position marker
                fig.add_vline(
                    x=current_date,
                    line_color=GAIA_PALETTE["slate_blue"],
                    line_width=2,
                    line_dash="dash",
                )
                
                fig.update_layout(
                    height=180,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="IBM Plex Mono", color="#5A5A5A", size=9),
                    margin=dict(l=40, r=20, t=10, b=30),
                    xaxis=dict(gridcolor="#1F1F1F", linecolor="#2A2A2A"),
                    yaxis=dict(gridcolor="#1F1F1F", linecolor="#2A2A2A", title="Z"),
                    showlegend=False,
                )
                
                st.plotly_chart(fig, use_container_width=True, key="cc_momentum_timeline")
            
            # v4.3.1: Improved auto-replay with status indicator
            if st.session_state.is_replaying:
                # Show replay status
                replay_status = st.empty()
                replay_status.markdown(
                    f"""<div style="font-family: 'IBM Plex Mono'; font-size: 10px; color: #7D9A7D; text-align: center; padding: 4px;">
                        ▶ REPLAY ACTIVE · Frame {current_idx + 1}/{len(dates)}
                    </div>""",
                    unsafe_allow_html=True
                )
                
                # Advance frame with shorter delay for smoother experience
                time.sleep(0.5)
                
                if st.session_state.current_frame_idx < len(dates) - 1:
                    st.session_state.current_frame_idx += 1
                else:
                    # Loop or stop
                    st.session_state.current_frame_idx = 0
                    # Optionally stop at end: st.session_state.is_replaying = False
                
                st.rerun()
        else:
            # v4.3.1: "No Data" overlay in Obsidian style
            st.markdown("""
            <div style="text-align: center; padding: 60px 40px; background: #0A0A0A; border: 1px solid #2A2A2A; border-radius: 2px;">
                <div style="font-size: 36px; margin-bottom: 16px; color: #3A3A3A;">⏱</div>
                <div style="font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #5A5A5A;">
                    NO TEMPORAL DATA AVAILABLE
                </div>
                <div style="font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #3A3A3A; margin-top: 8px;">
                    Execute a query with temporal geo data
                </div>
            </div>
            """, unsafe_allow_html=True)


# =============================================================================
# TAB 2: INTELLIGENCE
# =============================================================================

with tabs[2]:
    if not st.session_state.results:
        st.info("Configure experiments in QUERY tab and execute to see results.")
    else:
        first_label = list(st.session_state.results.keys())[0]
        first_result = st.session_state.results[first_label]
        ts_data = first_result.time_series.df
        
        if not ts_data.empty:
            cols = st.columns(4)
            with cols[0]:
                total = ts_data["mention_count"].sum() if "mention_count" in ts_data.columns else 0
                st.metric("TOTAL MENTIONS", f"{int(total):,}")
            with cols[1]:
                avg_sent = ts_data["sentiment_score"].mean() if "sentiment_score" in ts_data.columns else 0
                st.metric("AVG SENTIMENT", f"{avg_sent:+.2f}")
            with cols[2]:
                if "momentum_zscore" in ts_data.columns:
                    max_mom = ts_data["momentum_zscore"].max()
                    st.metric("PEAK MOMENTUM", f"{max_mom:+.2f}σ")
                else:
                    st.metric("PEAK MOMENTUM", "—")
            with cols[3]:
                days_count = len(ts_data["record_date"].unique()) if "record_date" in ts_data.columns else 0
                st.metric("OBSERVATION DAYS", days_count)
            
            st.markdown("")
            
            if "record_date" in ts_data.columns and "mention_count" in ts_data.columns:
                fig = create_time_series_chart(ts_data, first_label)
                st.plotly_chart(fig, use_container_width=True, key="intel_ts")
            
            with st.expander("RAW DATA"):
                st.dataframe(ts_data, use_container_width=True, height=180)
        else:
            st.warning("No time series data available")


# =============================================================================
# TAB 3: ENTITIES
# =============================================================================

with tabs[3]:
    st.markdown("### Entity Intelligence")
    
    if not st.session_state.results:
        st.info("Configure and execute an experiment to see entity data.")
    else:
        first_result = st.session_state.results[list(st.session_state.results.keys())[0]]
        
        if first_result.has_entities:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### TOP PERSONS")
                persons = first_result.entities.top_persons(8)
                if not persons.empty:
                    fig = create_entity_chart(persons, "person")
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, key="ent_persons")
                else:
                    st.caption("No person entities extracted")
            with col2:
                st.markdown("##### TOP ORGANIZATIONS")
                orgs = first_result.entities.top_organizations(8)
                if not orgs.empty:
                    fig = create_entity_chart(orgs, "organization")
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, key="ent_orgs")
                else:
                    st.caption("No organization entities extracted")
        else:
            st.info("Entity extraction not enabled. Select ENTITIES or COMPREHENSIVE mode.")


# =============================================================================
# TAB 4: INTEGRITY - v4.4 with Stacked Area Chart
# =============================================================================

with tabs[4]:
    st.markdown("### Source Integrity Analysis")
    
    if not st.session_state.results:
        st.info("Configure and execute an experiment to see integrity data.")
    else:
        first_result = st.session_state.results[list(st.session_state.results.keys())[0]]
        
        if first_result.has_source_trust and first_result.integrity:
            integrity = first_result.integrity
            
            cols = st.columns(4)
            with cols[0]:
                st.metric("INTEGRITY RATIO", f"{integrity.integrity_ratio:.2f}")
            with cols[1]:
                st.metric("TIER 1 SHARE", f"{integrity.tier1_percentage:.1f}%")
            with cols[2]:
                st.metric("TIER 3 SHARE", f"{integrity.tier3_percentage:.1f}%")
            with cols[3]:
                status_map = {"organic": "● ORGANIC", "mixed": "● MIXED", "artificial": "● ARTIFICIAL", "propaganda_risk": "● RISK"}
                st.metric("STATUS", status_map.get(integrity.status, integrity.status.upper()))
            
            st.markdown("")
            
            source_df = first_result.source_trust.df
            
            # v4.4: Stacked Area Chart for Source Trust over Time
            if not source_df.empty and "tier" in source_df.columns:
                st.markdown("##### Source Trust Timeline")
                
                # Check if temporal data is available
                if "record_date" in source_df.columns:
                    # Aggregate by date and tier
                    tier_daily = source_df.groupby(["record_date", "tier"])["mention_count"].sum().reset_index()
                    tier_daily = tier_daily.pivot(index="record_date", columns="tier", values="mention_count").fillna(0)
                    tier_daily = tier_daily.reset_index()
                    
                    # Rename columns for display
                    tier_names = {1: "Tier 1 (Verified)", 2: "Tier 2 (General)", 3: "Tier 3 (Unverified)"}
                    tier_colors = {
                        "Tier 1 (Verified)": GAIA_PALETTE["muted_sage"],
                        "Tier 2 (General)": GAIA_PALETTE["slate_blue"],
                        "Tier 3 (Unverified)": GAIA_PALETTE["accent_alert"],
                    }
                    
                    fig = go.Figure()
                    
                    for tier in [1, 2, 3]:
                        if tier in tier_daily.columns:
                            fig.add_trace(go.Scatter(
                                x=tier_daily["record_date"],
                                y=tier_daily[tier],
                                name=tier_names.get(tier, f"Tier {tier}"),
                                mode="lines",
                                stackgroup="one",
                                fillcolor=tier_colors.get(tier_names.get(tier), "#5A5A5A"),
                                line=dict(color=tier_colors.get(tier_names.get(tier), "#5A5A5A"), width=0),
                            ))
                    
                    fig.update_layout(
                        height=280,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="IBM Plex Mono", color="#5A5A5A", size=9),
                        margin=dict(l=40, r=20, t=30, b=30),
                        xaxis=dict(
                            gridcolor="#1F1F1F",
                            linecolor="#2A2A2A",
                            title="",
                        ),
                        yaxis=dict(
                            gridcolor="#1F1F1F",
                            linecolor="#2A2A2A",
                            title="Volume",
                        ),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="left",
                            x=0,
                            font=dict(size=9),
                            bgcolor="rgba(0,0,0,0)",
                        ),
                        hovermode="x unified",
                    )
                    
                    st.plotly_chart(fig, use_container_width=True, key="integrity_stacked_area")
                else:
                    # Fallback: Show tier distribution as bar chart
                    tier_totals = source_df.groupby("tier")["mention_count"].sum().reset_index()
                    tier_totals["tier_name"] = tier_totals["tier"].map({1: "Verified", 2: "General", 3: "Unverified"})
                    
                    fig = go.Figure(go.Bar(
                        x=tier_totals["tier_name"],
                        y=tier_totals["mention_count"],
                        marker_color=[GAIA_PALETTE["muted_sage"], GAIA_PALETTE["slate_blue"], GAIA_PALETTE["accent_alert"]],
                    ))
                    
                    fig.update_layout(
                        height=200,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="IBM Plex Mono", color="#5A5A5A", size=9),
                        margin=dict(l=40, r=20, t=10, b=30),
                        xaxis=dict(gridcolor="#1F1F1F", linecolor="#2A2A2A"),
                        yaxis=dict(gridcolor="#1F1F1F", linecolor="#2A2A2A", title="Volume"),
                    )
                    
                    st.plotly_chart(fig, use_container_width=True, key="integrity_tier_bar")
                
                st.markdown("##### TOP DOMAINS BY TIER")
                for tier in [1, 2, 3]:
                    tier_data = source_df[source_df["tier"] == tier].nlargest(3, "mention_count")
                    if not tier_data.empty:
                        tier_label = {1: "VERIFIED", 2: "GENERAL", 3: "UNVERIFIED"}[tier]
                        with st.expander(f"TIER {tier} · {tier_label}"):
                            st.dataframe(tier_data[["domain", "mention_count"]], use_container_width=True, hide_index=True)
        else:
            st.info("Source trust not enabled. Select INTEGRITY or COMPREHENSIVE mode.")


# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center;">
    <span style="font-family: 'IBM Plex Mono', monospace; font-size: 9px; color: #5A5A5A;">
        GDELT FORECAST LAB v4.4 · MULTIDIMENSIONAL INTELLIGENCE · 2025
    </span>
    <span style="font-family: 'IBM Plex Mono', monospace; font-size: 9px; color: #5A7D9A;">
        GAIA · CHRONOS · DEEP TECH INTELLIGENCE
    </span>
</div>
""", unsafe_allow_html=True)
