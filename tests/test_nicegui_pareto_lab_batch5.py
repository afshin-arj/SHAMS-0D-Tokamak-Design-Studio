"""Batch 5: Pareto Lab feasible-only frontier wiring."""
from __future__ import annotations

from ui_nicegui.decks.pareto_lab import render_pareto_lab
from ui_nicegui.lib.pareto_helpers import (
    artifact_to_json_bytes,
    build_pareto_artifact,
    default_bounds,
    run_pareto_study,
    summarize_pareto_run,
)
from ui_nicegui.session import DesignSession


def test_pareto_lab_renderer_import() -> None:
    assert callable(render_pareto_lab)


def test_default_bounds() -> None:
    s = DesignSession()
    b = default_bounds(s.build_point_inputs())
    assert b["R0_m"][1] > b["R0_m"][0]
    assert b["fG"] == (0.3, 1.1)


def test_run_pareto_study_smoke() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    bounds = default_bounds(base)
    result = run_pareto_study(
        base,
        bounds=bounds,
        objectives={"R0_m": "min", "P_e_net_MW": "max"},
        n_samples=24,
        seed=42,
        intent_mode="Reactor",
    )
    assert isinstance(result.get("feasible"), list)
    assert isinstance(result.get("pareto"), list)
    assert isinstance(result.get("summary"), dict)
    summary = summarize_pareto_run(result)
    assert "n_feasible" in summary
    assert summary["confidence"] in ("High", "Moderate", "Low", "Sparse")


def test_pareto_artifact_export() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    result = run_pareto_study(
        base,
        bounds=default_bounds(base),
        objectives={"R0_m": "min", "Bt_T": "max"},
        n_samples=20,
        seed=1,
        intent_mode="Reactor",
    )
    art = build_pareto_artifact(result)
    data = artifact_to_json_bytes(art)
    assert b"shams.pareto.v1" in data
