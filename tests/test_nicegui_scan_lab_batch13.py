"""Phase 13: Scan Lab workbench — dominance maps, causality, families, atlas."""
from __future__ import annotations

import pytest

from ui_nicegui.decks.scan_lab import workbench
from ui_nicegui.lib.scan_helpers import default_scan_bounds, run_cartography_scan
from ui_nicegui.lib.scan_workbench_helpers import (
    SCAN_WB_VIEWS,
    build_atlas_pdf_bytes,
    build_design_families,
    build_point_grid,
    dominance_labels,
    plotly_dominance_figure,
    probe_promote_inputs,
    run_causality_trace,
)
from ui_nicegui.session import DesignSession


def _small_scan_report() -> dict:
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
        include_outputs=False,
    )


def test_workbench_renderer_import() -> None:
    assert callable(workbench.render_workbench)


def test_build_point_grid() -> None:
    rep = _small_scan_report()
    grid = build_point_grid(rep)
    assert len(grid) == int(rep.get("n_points") or 0)


def test_dominance_labels_nonempty() -> None:
    rep = _small_scan_report()
    labels = dominance_labels(rep, "Reactor")
    assert isinstance(labels, list)
    assert len(labels) >= 1


def test_plotly_dominance_figure() -> None:
    rep = _small_scan_report()
    fig = plotly_dominance_figure(rep, "Reactor")
    assert fig is not None
    assert fig.data


def test_probe_promote_inputs() -> None:
    rep = _small_scan_report()
    grid = build_point_grid(rep)
    cell = grid[(0, 0)]
    cand = probe_promote_inputs(rep, cell)
    assert "Ip_MA" in cand
    assert "R0_m" in cand


def test_causality_trace_smoke() -> None:
    rep = _small_scan_report()
    grid = build_point_grid(rep)
    # find a failing cell if any
    i, j = 0, 0
    for (ii, jj), cell in grid.items():
        intent = (cell.get("intent") or {}).get("Reactor") or {}
        if not bool(intent.get("blocking_feasible")):
            i, j = ii, jj
            break
    s = DesignSession()
    tr = run_causality_trace(
        s.build_point_inputs(),
        rep,
        intent="Reactor",
        i=i,
        j=j,
        rel_step=0.01,
    )
    assert isinstance(tr, dict)
    assert "constraint" in tr or tr.get("status") == "skipped"


def test_design_families_smoke() -> None:
    rep = _small_scan_report()
    try:
        art = build_design_families(rep, intent="Reactor", min_points=4)
    except RuntimeError:
        pytest.skip("design family engine unavailable")
    assert isinstance(art, dict)
    assert "families" in art


def test_atlas_pdf_smoke() -> None:
    rep = _small_scan_report()
    try:
        pdf = build_atlas_pdf_bytes(rep, ["Reactor"], title="Test Atlas")
    except (RuntimeError, ModuleNotFoundError) as exc:
        pytest.skip(str(exc))
    assert isinstance(pdf, (bytes, bytearray))
    assert len(pdf) > 100


def test_scan_wb_views_defined() -> None:
    assert "Dominance (blocking)" in SCAN_WB_VIEWS
    assert "Feasibility (blocking)" in SCAN_WB_VIEWS
