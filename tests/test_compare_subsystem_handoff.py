"""Compare deck subsystem diff and handoff helpers."""
from __future__ import annotations

from ui_nicegui.lib.compare_helpers import (
    apply_artifact_inputs,
    subsystem_diff_rows,
    summarize_comparison,
)
from ui_nicegui.session import DesignSession


def test_subsystem_diff_detects_change() -> None:
    a = {
        "outputs": {
            "Q_DT_eqv": 5.0,
            "q95": 3.0,
            "q_div_MW_m2": 5.0,
            "B_peak_T": 12.0,
            "TBR": 1.1,
        }
    }
    b = {
        "outputs": {
            "Q_DT_eqv": 5.0,
            "q95": 3.0,
            "q_div_MW_m2": 25.0,
            "B_peak_T": 12.0,
            "TBR": 1.1,
        }
    }
    rows = subsystem_diff_rows(a, b)
    assert rows
    changed = [r for r in rows if r.get("changed")]
    assert changed


def test_summarize_includes_subsystem_diff() -> None:
    a = {"outputs": {"Q_DT_eqv": 1.0, "q95": 4.0}}
    b = {"outputs": {"Q_DT_eqv": 2.0, "q95": 2.0}}
    s = summarize_comparison(a, b)
    assert "subsystem_diff" in s
    assert isinstance(s["subsystem_diff"], list)


def test_apply_artifact_inputs() -> None:
    session = DesignSession()
    before = float(session.inputs.get("R0_m", 0))
    session.pd_last_outputs = {"Q_DT_eqv": 12.0}
    session.pd_last_artifact = {"outputs": {"Q_DT_eqv": 12.0}}
    session.pd_last_run_ts = 1.0
    art = {"inputs": {"R0_m": before + 0.5, "Paux_MW": 40.0}}
    n = apply_artifact_inputs(session, art)
    assert n >= 1
    assert float(session.inputs["R0_m"]) == before + 0.5
    assert session.pd_last_outputs is None
    assert session.pd_last_artifact is None


def test_seed_promotes_invalidate_point_designer() -> None:
    """Compare / Pareto / Trade / Scan seed helpers clear prior-machine KPIs."""
    from pathlib import Path

    assert "invalidate_point_designer_after_seed" in Path(
        "ui_nicegui/lib/pd_handoff.py"
    ).read_text(encoding="utf-8")
    assert "invalidate_point_designer_after_seed" in Path(
        "ui_nicegui/lib/compare_helpers.py"
    ).read_text(encoding="utf-8")
    assert "invalidate_point_designer_after_seed" in Path(
        "ui_nicegui/lib/pareto_interpret_helpers.py"
    ).read_text(encoding="utf-8")
    assert "invalidate_point_designer_after_seed" in Path(
        "ui_nicegui/lib/trade_interpret_helpers.py"
    ).read_text(encoding="utf-8")
    assert "invalidate_point_designer_after_seed" in Path(
        "ui_nicegui/lib/scan_workbench_helpers.py"
    ).read_text(encoding="utf-8")
    assert "prior KPIs cleared" in Path(
        "ui_nicegui/decks/compare/export_panel.py"
    ).read_text(encoding="utf-8")
    assert "invalidate_point_designer_after_seed" in Path(
        "ui_nicegui/components/dsg_sidebar.py"
    ).read_text(encoding="utf-8")
    assert "invalidate_point_designer_after_seed" in Path(
        "ui_nicegui/decks/reactor_design_forge/handoff_panel.py"
    ).read_text(encoding="utf-8")
