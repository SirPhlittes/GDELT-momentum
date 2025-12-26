"""
GDELT v4.3 Institutional Obsidian Theme - Command Center Edition
=================================================================
Professional dark-mode theme for enterprise intelligence dashboards.

Design principles:
- High information density ("War Room" aesthetic)
- Neutral, desaturated color palette
- Monospace typography for data (IBM Plex Mono)
- No glow effects, no gradients
- Sharp borders, minimal padding
- Command Center HUD integration

Inspired by: Palantir Foundry, Reuters Eikon, Bloomberg Terminal

Author: Philip Hendrik Littau
Version: 4.3.0
"""

from typing import Dict, Any

# =============================================================================
# OBSIDIAN COLOR PALETTE
# =============================================================================

OBSIDIAN_PALETTE = {
    # Backgrounds
    "bg_primary": "#0E1117",      # Deep Obsidian - main background
    "bg_secondary": "#161B22",    # Elevated surfaces (sidebar, cards)
    "bg_tertiary": "#1C2128",     # Hover states
    "bg_input": "#0D1117",        # Input fields
    
    # Borders
    "border_primary": "#30363D",  # Primary borders
    "border_secondary": "#21262D", # Subtle borders (grid lines)
    "border_focus": "#58A6FF",    # Focus states
    
    # Text
    "text_primary": "#E6EDF3",    # Primary text
    "text_secondary": "#8B949E",  # Secondary text / labels
    "text_muted": "#6E7681",      # Muted text
    "text_link": "#58A6FF",       # Links
    
    # Functional - Positive
    "positive_primary": "#42A5F5", # Muted Steel Blue
    "positive_secondary": "#81C784", # Soft Sage
    "positive_muted": "#238636",  # Subtle green
    
    # Functional - Negative
    "negative_primary": "#E57373", # Dull Coral
    "negative_secondary": "#FF8A65", # Muted Amber
    "negative_muted": "#DA3633",  # Subtle red
    
    # Functional - Neutral
    "neutral_primary": "#8B949E", # Neutral gray
    "warning": "#D29922",         # Warning amber
    
    # Chart colors (desaturated)
    "chart_blue": "#42A5F5",
    "chart_green": "#81C784",
    "chart_red": "#E57373",
    "chart_amber": "#FF8A65",
    "chart_purple": "#B39DDB",
    "chart_cyan": "#80DEEA",
    "chart_gray": "#6E7681",
    
    # Map colors
    "map_low": "#1F2937",
    "map_mid": "#2D4A5E",
    "map_high": "#42A5F5",
    "map_land": "#161B22",
    "map_border": "#30363D",
}

# =============================================================================
# STREAMLIT CSS INJECTION
# =============================================================================

INSTITUTIONAL_CSS = """
<style>
    /* ========== FONT IMPORTS ========== */
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600&display=swap');
    
    /* ========== ROOT VARIABLES ========== */
    :root {
        --bg-primary: #0E1117;
        --bg-secondary: #161B22;
        --bg-tertiary: #1C2128;
        --bg-input: #0D1117;
        --border-primary: #30363D;
        --border-secondary: #21262D;
        --border-focus: #58A6FF;
        --text-primary: #E6EDF3;
        --text-secondary: #8B949E;
        --text-muted: #6E7681;
        --positive: #42A5F5;
        --negative: #E57373;
        --warning: #D29922;
    }
    
    /* ========== HIDE STREAMLIT DEFAULTS ========== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Hide the red line at top but keep header functional */
    .stApp > header {
        background-color: transparent;
    }
    
    /* Keep header visible for sidebar toggle */
    header {
        visibility: visible !important;
    }
    
    div[data-testid="stToolbar"] {
        display: none;
    }
    
    div[data-testid="stDecoration"] {
        display: none;
    }
    
    div[data-testid="stStatusWidget"] {
        display: none;
    }
    
    /* ========== MAIN APP BACKGROUND ========== */
    .stApp {
        background-color: var(--bg-primary);
    }
    
    .main .block-container {
        padding: 1rem 2rem;
        max-width: 100%;
    }
    
    /* ========== SIDEBAR ========== */
    section[data-testid="stSidebar"],
    [data-testid="stSidebar"] {
        background-color: var(--bg-secondary) !important;
        border-right: 1px solid var(--border-primary) !important;
        visibility: visible !important;
        display: block !important;
        z-index: 999 !important;
        position: relative !important;
        width: 21rem !important;
    }
    
    /* Ensure sidebar content is visible */
    [data-testid="stSidebar"] > div,
    section[data-testid="stSidebar"] > div {
        visibility: visible !important;
        display: block !important;
    }
    
    /* Sidebar navigation button - make it visible */
    button[kind="header"],
    button[data-testid="baseButton-header"],
    .stApp header button {
        visibility: visible !important;
        display: block !important;
        z-index: 1000 !important;
    }
    
    /* Sidebar content wrapper */
    [data-testid="stSidebar"] [data-testid="stSidebarContent"],
    [data-testid="stSidebarContent"] {
        visibility: visible !important;
        display: block !important;
    }
    
    /* Force sidebar to be visible and expanded */
    .stApp [data-testid="stSidebar"] {
        transform: translateX(0) !important;
        visibility: visible !important;
        display: block !important;
        opacity: 1 !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: var(--text-primary);
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--text-primary);
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        letter-spacing: -0.02em;
    }
    
    [data-testid="stSidebar"] .stCaption {
        color: var(--text-muted);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
    }
    
    /* ========== TYPOGRAPHY ========== */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif;
        color: var(--text-primary);
        font-weight: 600;
        letter-spacing: -0.02em;
    }
    
    h1 { font-size: 1.75rem; margin-bottom: 0.5rem; }
    h2 { font-size: 1.25rem; margin-bottom: 0.5rem; }
    h3 { font-size: 1rem; margin-bottom: 0.25rem; }
    
    p, span, label, .stMarkdown {
        font-family: 'Inter', sans-serif;
        color: var(--text-secondary);
        font-size: 13px;
    }
    
    /* Monospace for data */
    .stDataFrame, .stTable, code, pre {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 12px;
    }
    
    /* ========== INPUTS ========== */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        background-color: var(--bg-input);
        border: 1px solid var(--border-primary);
        color: var(--text-primary);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 13px;
        border-radius: 2px;
        padding: 8px 12px;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--border-focus);
        box-shadow: none;
    }
    
    .stTextInput label,
    .stTextArea label,
    .stNumberInput label,
    .stSelectbox label,
    .stSlider label {
        color: var(--text-secondary);
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* ========== SELECT BOX ========== */
    .stSelectbox > div > div {
        background-color: var(--bg-input);
        border: 1px solid var(--border-primary);
        border-radius: 2px;
    }
    
    .stSelectbox > div > div > div {
        color: var(--text-primary);
    }
    
    /* ========== SLIDER ========== */
    .stSlider > div > div > div {
        background-color: var(--border-secondary);
    }
    
    .stSlider > div > div > div > div {
        background-color: var(--positive);
    }
    
    /* ========== BUTTONS ========== */
    .stButton > button {
        background-color: var(--bg-tertiary);
        border: 1px solid var(--border-primary);
        color: var(--text-primary);
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        font-weight: 500;
        border-radius: 2px;
        padding: 8px 16px;
        transition: all 0.15s ease;
    }
    
    .stButton > button:hover {
        background-color: var(--bg-input);
        border-color: var(--text-muted);
    }
    
    .stButton > button[kind="primary"] {
        background-color: var(--positive);
        border-color: var(--positive);
        color: var(--bg-primary);
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #5BAEF7;
        border-color: #5BAEF7;
    }
    
    /* ========== TABS ========== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background-color: transparent;
        border-bottom: 1px solid var(--border-primary);
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        border-radius: 0;
        color: var(--text-muted);
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        font-weight: 500;
        padding: 12px 20px;
        margin-bottom: -1px;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-primary);
        background-color: transparent;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: transparent;
        border-bottom: 2px solid var(--positive);
        color: var(--text-primary);
    }
    
    /* ========== METRICS ========== */
    [data-testid="stMetricValue"] {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.75rem;
        font-weight: 600;
        color: var(--text-primary);
    }
    
    [data-testid="stMetricLabel"] {
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        font-weight: 500;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    
    [data-testid="stMetricDelta"] {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
    }
    
    [data-testid="stMetricDelta"] svg {
        display: none;
    }
    
    /* Metric container - flat box */
    div[data-testid="metric-container"] {
        background-color: var(--bg-secondary);
        border: 1px solid var(--border-primary);
        border-radius: 2px;
        padding: 12px 16px;
    }
    
    /* ========== EXPANDER ========== */
    .streamlit-expanderHeader {
        background-color: var(--bg-secondary);
        border: 1px solid var(--border-primary);
        border-radius: 2px;
        color: var(--text-primary);
        font-family: 'Inter', sans-serif;
        font-size: 13px;
    }
    
    .streamlit-expanderContent {
        background-color: var(--bg-secondary);
        border: 1px solid var(--border-primary);
        border-top: none;
    }
    
    /* ========== DATAFRAME ========== */
    .stDataFrame {
        border: 1px solid var(--border-primary);
    }
    
    .stDataFrame [data-testid="stDataFrameResizable"] {
        background-color: var(--bg-secondary);
    }
    
    /* ========== DIVIDER ========== */
    hr {
        border-color: var(--border-primary);
        margin: 1rem 0;
    }
    
    /* ========== ALERTS ========== */
    .stAlert {
        background-color: var(--bg-secondary);
        border: 1px solid var(--border-primary);
        border-radius: 2px;
        color: var(--text-secondary);
    }
    
    .stAlert[data-baseweb="notification"] {
        background-color: var(--bg-secondary);
    }
    
    /* ========== SPINNER ========== */
    .stSpinner > div {
        border-color: var(--positive) transparent transparent transparent;
    }
    
    /* ========== CONTAINER BORDERS ========== */
    [data-testid="stVerticalBlock"] > div[style*="border"] {
        border-color: var(--border-primary) !important;
        background-color: var(--bg-secondary) !important;
        border-radius: 2px !important;
    }
    
    /* ========== PLOTLY OVERRIDES ========== */
    .js-plotly-plot .plotly .modebar {
        background-color: transparent !important;
    }
    
    .js-plotly-plot .plotly .modebar-btn {
        color: var(--text-muted) !important;
    }
    
    .js-plotly-plot .plotly .modebar-btn:hover {
        color: var(--text-primary) !important;
    }
    
    /* ========== SCROLLBAR ========== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-primary);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--border-primary);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-muted);
    }
    
    /* ========== HIGH DENSITY MODE ========== */
    .stMarkdown {
        margin-bottom: 0.25rem;
    }
    
    .element-container {
        margin-bottom: 0.5rem;
    }
    
    /* ========== INFO BOX ========== */
    .stInfo {
        background-color: rgba(66, 165, 245, 0.1);
        border: 1px solid rgba(66, 165, 245, 0.3);
        color: var(--text-secondary);
    }
    
    .stWarning {
        background-color: rgba(210, 153, 34, 0.1);
        border: 1px solid rgba(210, 153, 34, 0.3);
    }
    
    .stSuccess {
        background-color: rgba(129, 199, 132, 0.1);
        border: 1px solid rgba(129, 199, 132, 0.3);
    }
    
    .stError {
        background-color: rgba(229, 115, 115, 0.1);
        border: 1px solid rgba(229, 115, 115, 0.3);
    }
    
    /* ========== COMMAND CENTER STYLES v4.3 ========== */
    
    /* Fixed Header Bar */
    .command-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 48px;
        background: linear-gradient(180deg, #0A0A0A 0%, #050505 100%);
        border-bottom: 1px solid #2A2A2A;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 24px;
        z-index: 9999;
        font-family: 'IBM Plex Mono', monospace;
    }
    
    .command-header .brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .command-header .brand-icon {
        color: #7D9A7D;
        font-size: 14px;
    }
    
    .command-header .brand-title {
        color: #E6EDF3;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    
    .command-header .brand-version {
        color: #5A5A5A;
        font-size: 11px;
        border: 1px solid #2A2A2A;
        padding: 2px 8px;
        border-radius: 2px;
    }
    
    .command-header .timestamp {
        color: #5A7D9A;
        font-size: 11px;
        font-weight: 500;
    }
    
    /* Main content offset for fixed header */
    .main .block-container {
        padding-top: 64px !important;
    }
    
    /* HUD Overlay Containers */
    .hud-container {
        position: relative;
        background: #050505;
        border: 1px solid #2A2A2A;
        border-radius: 2px;
        overflow: hidden;
    }
    
    .hud-metrics-panel {
        position: absolute;
        top: 16px;
        right: 16px;
        background: rgba(5, 5, 5, 0.92);
        border: 1px solid #2A2A2A;
        border-radius: 2px;
        padding: 16px;
        min-width: 200px;
        z-index: 100;
    }
    
    .hud-metric {
        margin-bottom: 12px;
    }
    
    .hud-metric:last-child {
        margin-bottom: 0;
    }
    
    .hud-metric-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 9px;
        color: #5A5A5A;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 4px;
    }
    
    .hud-metric-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 18px;
        font-weight: 600;
        color: #E6EDF3;
    }
    
    .hud-metric-value.positive {
        color: #7D9A7D;
    }
    
    .hud-metric-value.negative {
        color: #D47474;
    }
    
    /* Timestamp Badge */
    .timestamp-badge {
        position: absolute;
        top: 16px;
        left: 16px;
        background: rgba(5, 5, 5, 0.92);
        border: 1px solid #7D9A7D;
        border-radius: 2px;
        padding: 10px 14px;
        z-index: 100;
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
        font-weight: 600;
    }
    
    /* Control Deck */
    .control-deck {
        background: rgba(5, 5, 5, 0.95);
        border-top: 1px solid #2A2A2A;
        padding: 12px 20px;
        display: flex;
        align-items: center;
        gap: 16px;
    }
    
    .control-btn {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        background: #111111;
        border: 1px solid #2A2A2A;
        color: #8B949E;
        padding: 6px 12px;
        border-radius: 2px;
        cursor: pointer;
        transition: all 0.15s ease;
    }
    
    .control-btn:hover {
        background: #1C1C1C;
        border-color: #3A3A3A;
        color: #E6EDF3;
    }
    
    .control-btn.active {
        background: #7D9A7D;
        border-color: #7D9A7D;
        color: #050505;
    }
    
    .control-slider {
        flex: 1;
        height: 4px;
        background: #1F1F1F;
        border-radius: 2px;
        position: relative;
    }
    
    .control-slider-fill {
        height: 100%;
        background: linear-gradient(90deg, #5A7D9A, #7D9A7D);
        border-radius: 2px;
    }
    
    /* News Ticker Bar */
    .ticker-bar {
        height: 36px;
        background: #050505;
        border-top: 1px solid #2A2A2A;
        display: flex;
        align-items: center;
        overflow: hidden;
    }
    
    .ticker-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 9px;
        color: #5A5A5A;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        padding: 0 16px;
        border-right: 1px solid #2A2A2A;
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
        color: #5A7D9A;
        white-space: nowrap;
        animation: ticker-scroll 45s linear infinite;
    }
    
    @keyframes ticker-scroll {
        0% { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
    }
    
    /* Globe Container with Obsidian Filter */
    .globe-container iframe,
    .globe-container canvas {
        filter: saturate(0.6) contrast(1.1) brightness(0.85);
    }
    
    /* Pydeck Container Styling */
    [data-testid="stDeckGlChart"],
    .stDeckGlChart,
    iframe[title*="pydeck"] {
        filter: saturate(0.6) contrast(1.1) brightness(0.85);
    }
    
    /* Status Indicators */
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }
    
    .status-dot.active {
        background: #7D9A7D;
        box-shadow: 0 0 8px rgba(125, 154, 125, 0.5);
    }
    
    .status-dot.inactive {
        background: #5A5A5A;
    }
    
    .status-dot.warning {
        background: #D4A574;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
</style>
"""


def apply_institutional_theme() -> str:
    """
    Apply the Institutional Obsidian theme to a Streamlit app.
    
    Usage:
        import streamlit as st
        from gdelt_v4.ui import apply_institutional_theme
        
        st.markdown(apply_institutional_theme(), unsafe_allow_html=True)
    
    Returns:
        CSS string to inject via st.markdown
    """
    return INSTITUTIONAL_CSS


def get_chart_layout(
    title: str = "",
    height: int = 400,
    show_legend: bool = True,
) -> Dict[str, Any]:
    """
    Get Plotly layout configuration for institutional theme.
    
    Args:
        title: Chart title
        height: Chart height in pixels
        show_legend: Whether to show legend
        
    Returns:
        Plotly layout dictionary
    """
    return {
        "title": {
            "text": title,
            "font": {
                "family": "Inter, sans-serif",
                "size": 14,
                "color": OBSIDIAN_PALETTE["text_primary"],
            },
            "x": 0,
            "xanchor": "left",
        },
        "height": height,
        "showlegend": show_legend,
        "legend": {
            "font": {
                "family": "Inter, sans-serif",
                "size": 11,
                "color": OBSIDIAN_PALETTE["text_secondary"],
            },
            "bgcolor": "rgba(0,0,0,0)",
            "bordercolor": OBSIDIAN_PALETTE["border_primary"],
            "borderwidth": 1,
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {
            "family": "IBM Plex Mono, monospace",
            "color": OBSIDIAN_PALETTE["text_secondary"],
            "size": 11,
        },
        "margin": {"l": 50, "r": 20, "t": 40, "b": 40},
        "xaxis": {
            "gridcolor": OBSIDIAN_PALETTE["border_secondary"],
            "gridwidth": 1,
            "linecolor": OBSIDIAN_PALETTE["border_primary"],
            "linewidth": 1,
            "tickfont": {
                "family": "IBM Plex Mono, monospace",
                "size": 10,
                "color": OBSIDIAN_PALETTE["text_muted"],
            },
            "title_font": {
                "family": "Inter, sans-serif",
                "size": 11,
                "color": OBSIDIAN_PALETTE["text_secondary"],
            },
        },
        "yaxis": {
            "gridcolor": OBSIDIAN_PALETTE["border_secondary"],
            "gridwidth": 1,
            "linecolor": OBSIDIAN_PALETTE["border_primary"],
            "linewidth": 1,
            "tickfont": {
                "family": "IBM Plex Mono, monospace",
                "size": 10,
                "color": OBSIDIAN_PALETTE["text_muted"],
            },
            "title_font": {
                "family": "Inter, sans-serif",
                "size": 11,
                "color": OBSIDIAN_PALETTE["text_secondary"],
            },
        },
        "hoverlabel": {
            "bgcolor": OBSIDIAN_PALETTE["bg_secondary"],
            "bordercolor": OBSIDIAN_PALETTE["border_primary"],
            "font": {
                "family": "IBM Plex Mono, monospace",
                "size": 11,
                "color": OBSIDIAN_PALETTE["text_primary"],
            },
        },
    }


def get_map_layout(
    title: str = "",
    height: int = 600,
) -> Dict[str, Any]:
    """
    Get Plotly geo/map layout configuration for institutional theme.
    
    Args:
        title: Map title
        height: Map height in pixels
        
    Returns:
        Plotly layout dictionary for geo charts
    """
    return {
        "title": {
            "text": title,
            "font": {
                "family": "Inter, sans-serif",
                "size": 14,
                "color": OBSIDIAN_PALETTE["text_primary"],
            },
            "x": 0,
            "xanchor": "left",
        },
        "height": height,
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": {"l": 0, "r": 0, "t": 40, "b": 0},
        "geo": {
            "bgcolor": "rgba(0,0,0,0)",
            "showframe": False,
            "showcoastlines": True,
            "coastlinecolor": OBSIDIAN_PALETTE["border_primary"],
            "coastlinewidth": 0.5,
            "showland": True,
            "landcolor": OBSIDIAN_PALETTE["map_land"],
            "showocean": True,
            "oceancolor": OBSIDIAN_PALETTE["bg_primary"],
            "showcountries": True,
            "countrycolor": OBSIDIAN_PALETTE["border_secondary"],
            "countrywidth": 0.5,
            "showlakes": False,
            "projection_type": "equirectangular",
        },
        "coloraxis": {
            "colorbar": {
                "bgcolor": "rgba(0,0,0,0)",
                "bordercolor": OBSIDIAN_PALETTE["border_primary"],
                "borderwidth": 1,
                "tickfont": {
                    "family": "IBM Plex Mono, monospace",
                    "size": 10,
                    "color": OBSIDIAN_PALETTE["text_muted"],
                },
                "title": {
                    "font": {
                        "family": "Inter, sans-serif",
                        "size": 11,
                        "color": OBSIDIAN_PALETTE["text_secondary"],
                    },
                },
            },
        },
    }


def get_command_center_css() -> str:
    """
    Get additional CSS for Command Center mode.
    
    Apply after the base institutional theme for full Command Center styling.
    
    Returns:
        CSS string for st.markdown injection
    """
    return """
    <style>
        /* Command Center Deep Background */
        .stApp {
            background-color: #050505 !important;
        }
        
        /* Increase contrast for satellite map */
        [data-testid="stDeckGlChart"] iframe,
        .stDeckGlChart iframe {
            filter: saturate(0.5) contrast(1.15) brightness(0.8) !important;
        }
    </style>
    """


def render_command_header_html(
    title: str = "GDELT FORECAST LAB",
    version: str = "v4.3",
    subtitle: str = "COMMAND CENTER",
    timestamp: str = "",
) -> str:
    """
    Generate HTML for the fixed Command Center header.
    
    Args:
        title: Main title text
        version: Version string
        subtitle: Subtitle text
        timestamp: Current UTC timestamp
        
    Returns:
        HTML string for st.markdown injection
    """
    if not timestamp:
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    return f"""
    <div class="command-header">
        <div class="brand">
            <span class="brand-icon">◉</span>
            <span class="brand-title">{title}</span>
            <span class="brand-version">{version} · {subtitle}</span>
        </div>
        <div class="timestamp">{timestamp}</div>
    </div>
    """


def render_hud_metrics_html(
    momentum: float = 0.0,
    sentiment: float = 0.0,
    mentions: int = 0,
    countries: int = 0,
) -> str:
    """
    Generate HTML for the HUD metrics panel overlay.
    
    Args:
        momentum: Current momentum Z-score
        sentiment: Current average sentiment
        mentions: Total mention count
        countries: Number of active countries
        
    Returns:
        HTML string for st.markdown injection
    """
    momentum_class = "positive" if momentum >= 0 else "negative"
    sentiment_class = "positive" if sentiment >= 0 else "negative"
    
    return f"""
    <div class="hud-metrics-panel">
        <div class="hud-metric">
            <div class="hud-metric-label">Momentum Z-Score</div>
            <div class="hud-metric-value {momentum_class}">{momentum:+.2f}σ</div>
        </div>
        <div class="hud-metric">
            <div class="hud-metric-label">Sentiment</div>
            <div class="hud-metric-value {sentiment_class}">{sentiment:+.2f}</div>
        </div>
        <div class="hud-metric">
            <div class="hud-metric-label">Mentions</div>
            <div class="hud-metric-value">{mentions:,}</div>
        </div>
        <div class="hud-metric">
            <div class="hud-metric-label">Active Regions</div>
            <div class="hud-metric-value">{countries}</div>
        </div>
    </div>
    """


def render_timestamp_badge_html(timestamp: str = "", label: str = "TEMPORAL POSITION") -> str:
    """
    Generate HTML for the timestamp badge overlay.
    
    Args:
        timestamp: Timestamp to display
        label: Label text
        
    Returns:
        HTML string for st.markdown injection
    """
    return f"""
    <div class="timestamp-badge">
        <div class="label">{label}</div>
        <div class="value">{timestamp}</div>
    </div>
    """


def render_ticker_html(items: list = None, label: str = "LIVE FEED") -> str:
    """
    Generate HTML for the news ticker bar.
    
    Args:
        items: List of ticker item strings
        label: Ticker label
        
    Returns:
        HTML string for st.markdown injection
    """
    if not items:
        items = ["No data available"]
    
    ticker_content = " │ ".join(items)
    
    return f"""
    <div class="ticker-bar">
        <div class="ticker-label">{label}</div>
        <div class="ticker-content">
            <div class="ticker-scroll">{ticker_content}</div>
        </div>
    </div>
    """


def get_institutional_colorscale(mode: str = "sequential") -> list:
    """
    Get color scales for institutional theme.
    
    Args:
        mode: "sequential", "diverging", or "categorical"
        
    Returns:
        List of color stops for Plotly
    """
    if mode == "sequential":
        return [
            [0.0, OBSIDIAN_PALETTE["map_low"]],
            [0.5, OBSIDIAN_PALETTE["map_mid"]],
            [1.0, OBSIDIAN_PALETTE["map_high"]],
        ]
    elif mode == "diverging":
        return [
            [0.0, OBSIDIAN_PALETTE["negative_primary"]],
            [0.5, OBSIDIAN_PALETTE["bg_tertiary"]],
            [1.0, OBSIDIAN_PALETTE["positive_primary"]],
        ]
    elif mode == "categorical":
        return [
            OBSIDIAN_PALETTE["chart_blue"],
            OBSIDIAN_PALETTE["chart_green"],
            OBSIDIAN_PALETTE["chart_amber"],
            OBSIDIAN_PALETTE["chart_purple"],
            OBSIDIAN_PALETTE["chart_cyan"],
            OBSIDIAN_PALETTE["chart_red"],
        ]
    else:
        return [[0.0, OBSIDIAN_PALETTE["map_low"]], [1.0, OBSIDIAN_PALETTE["map_high"]]]

