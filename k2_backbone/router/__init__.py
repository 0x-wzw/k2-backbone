"""K2-Backbone Router — imports the 10-D dimension map as single source of truth."""

import sys
from pathlib import Path

_neuroswarm_path = Path(__file__).parent.parent.parent / "frameworks" / "neuroswarm"
if str(_neuroswarm_path) not in sys.path:
    sys.path.insert(0, str(_neuroswarm_path))

from neuroswarm.swarm.dimension_map import (
    DIMENSION_MAP,
    DIMENSION_FALLBACK,
    DIMENSION_DESCRIPTIONS,
)

__all__ = [
    "DIMENSION_MAP",
    "DIMENSION_FALLBACK",
    "DIMENSION_DESCRIPTIONS",
]