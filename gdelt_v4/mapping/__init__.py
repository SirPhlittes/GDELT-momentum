"""Geographic mapping utilities for GDELT v4.4."""

from gdelt_v4.mapping.country_codes import CountryCodeMapper, FIPS_TO_ISO3, ISO3_TO_NAME
from gdelt_v4.mapping.geospatial import (
    GAIA_PALETTE,
    PYDECK_AVAILABLE,
    LayerMode,
    TemporalFadingEngine,
    # Globe rendering
    render_gaia_globe,
    render_command_center_globe,
    prepare_geo_data_for_globe,
    # v4.4: Bivariate & Conflict
    get_bivariate_color,
    apply_bivariate_colors,
    apply_conflict_colors,
    get_bivariate_legend_html,
    BIVARIATE_COLOR_MATRIX,
    CONFLICT_COLORS,
    # CSS
    get_command_center_css,
    get_map_css_filter,
)

__all__ = [
    "CountryCodeMapper",
    "FIPS_TO_ISO3",
    "ISO3_TO_NAME",
    "GAIA_PALETTE",
    "PYDECK_AVAILABLE",
    "LayerMode",
    "TemporalFadingEngine",
    "render_gaia_globe",
    "render_command_center_globe",
    "prepare_geo_data_for_globe",
    "get_bivariate_color",
    "apply_bivariate_colors",
    "apply_conflict_colors",
    "get_bivariate_legend_html",
    "BIVARIATE_COLOR_MATRIX",
    "CONFLICT_COLORS",
    "get_command_center_css",
    "get_map_css_filter",
]

