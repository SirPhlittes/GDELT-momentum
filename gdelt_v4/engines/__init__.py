"""Momentum and temporal calculation engines for GDELT v4.2."""

from gdelt_v4.engines.momentum import UnifiedMomentumEngine, MomentumMode
from gdelt_v4.engines.temporal import (
    TemporalEngine,
    TemporalResult,
    TemporalSlice,
    ReplayState,
    NewsTicker,
)

__all__ = [
    "UnifiedMomentumEngine",
    "MomentumMode",
    "TemporalEngine",
    "TemporalResult",
    "TemporalSlice",
    "ReplayState",
    "NewsTicker",
]

