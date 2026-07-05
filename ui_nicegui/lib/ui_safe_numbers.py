"""Finite numeric values for NiceGUI ui.number (NaN/inf break the widget)."""
from __future__ import annotations

import math
from typing import Any


def finite_ui_number(value: Any, *, unset: float = 0.0) -> float:
    """Return a finite float for ui.number. NaN/inf/missing map to ``unset``."""
    try:
        x = float(value)
    except (TypeError, ValueError):
        return unset
    return x if math.isfinite(x) else unset
