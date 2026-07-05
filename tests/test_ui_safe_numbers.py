"""ui.number must never receive NaN — NiceGUI raises on load."""
from __future__ import annotations

import math

from ui_nicegui.lib.ui_safe_numbers import finite_ui_number


def test_finite_ui_number_maps_nan_to_unset():
    assert finite_ui_number(float("nan")) == 0.0
    assert finite_ui_number(float("nan"), unset=1.5) == 1.5


def test_finite_ui_number_preserves_finite():
    assert finite_ui_number(2.5) == 2.5
    assert finite_ui_number("3.0") == 3.0


def test_finite_ui_number_maps_inf():
    assert math.isfinite(finite_ui_number(float("inf")))
    assert math.isfinite(finite_ui_number(float("-inf")))
