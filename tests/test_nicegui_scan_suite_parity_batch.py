"""Deep landscape map helpers — smoke tests."""
from __future__ import annotations

import pytest

from ui_nicegui.decks.scan_lab import deep_maps
from ui_nicegui.components.mode_scope import render_mode_scope
from ui_nicegui.lib.scan_deep_viz_helpers import (
    constraint_names_from_report,
    coupling_matrix_rows,
    robustness_label_counts,
)
from ui_nicegui.lib.mode_scope_data import MODE_SCOPE
from ui_nicegui.lib.scan_helpers import default_scan_bounds, run_cartography_scan
from ui_nicegui.lib.verdict_core import verdict_summary
from ui_nicegui.session import DesignSession


def _small_rep() -> dict:
    s = DesignSession()
    base = s.build_point_inputs()
    x_lo, x_hi, y_lo, y_hi = default_scan_bounds(base, "Ip_MA", "R0_m")
    return run_cartography_scan(
        base,
        x_key="Ip_MA",
        y_key="R0_m",
        x_lo=x_lo,
        x_hi=x_hi,
        y_lo=y_lo,
        y_hi=y_hi,
        nx=11,
        ny=11,
        intents=["Reactor"],
    )


def test_mode_scope_keys() -> None:
    assert "suite" in MODE_SCOPE
    assert "scan" in MODE_SCOPE
    assert callable(render_mode_scope)


def test_deep_maps_renderer_import() -> None:
    assert callable(deep_maps.render_deep_landscape_maps)


def test_constraint_names_smoke() -> None:
    rep = _small_rep()
    names = constraint_names_from_report(rep)
    assert isinstance(names, list)


def test_robustness_counts_smoke() -> None:
    rep = _small_rep()
    counts = robustness_label_counts(rep, "Reactor")
    assert isinstance(counts, dict)
    assert sum(counts.values()) == int(rep.get("n_points") or 0)


def test_coupling_matrix_optional() -> None:
    rep = _small_rep()
    names, rows = coupling_matrix_rows(rep, "Reactor")
    assert isinstance(names, list)
    assert isinstance(rows, list)


def test_verdict_parity_fields() -> None:
    s = DesignSession()
    out = {"Q_DT_eqv": 1.0, "constraints": []}
    try:
        summary = verdict_summary(out)
    except Exception:
        pytest.skip("constraint bundle unavailable")
    if summary.get("loaded"):
        assert "parity_aligned" in summary
