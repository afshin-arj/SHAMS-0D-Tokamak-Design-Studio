"""Batch 6: Trade Study Studio wiring."""
from __future__ import annotations

from ui_nicegui.decks.trade_study_studio import render_trade_study_studio
from ui_nicegui.lib.trade_study_helpers import (
    build_study_capsule,
    default_objectives,
    objectives_catalog,
    report_to_json_bytes,
    run_studio_trade_study,
    summarize_trade_study,
)
from ui_nicegui.session import DesignSession

try:
    from src.trade_studies.spec import default_knob_sets
except ImportError:
    from trade_studies.spec import default_knob_sets  # type: ignore


def test_trade_study_renderer_import() -> None:
    assert callable(render_trade_study_studio)


def test_default_objectives_nonempty() -> None:
    objs = default_objectives()
    assert isinstance(objs, list)
    assert len(objs) >= 1


def test_run_studio_trade_study_smoke() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    ks = default_knob_sets()[0]
    objectives = default_objectives()[:2]
    _, catalog_senses = objectives_catalog()
    senses = {o: catalog_senses.get(o, "min") for o in objectives}
    rep = run_studio_trade_study(
        base,
        knob_set=ks,
        objectives=objectives,
        objective_senses=senses,
        n_samples=20,
        seed=3,
    )
    assert isinstance(rep.get("records"), list)
    assert len(rep["records"]) == 20
    assert isinstance(rep.get("summary"), dict)
    summary = summarize_trade_study(rep)
    assert summary["n_samples"] == 20
    assert summary["confidence"] in ("High", "Moderate", "Low", "Sparse")


def test_study_capsule_and_export() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    ks = default_knob_sets()[1]
    objectives = ["min_R0"]
    rep = run_studio_trade_study(
        base,
        knob_set=ks,
        objectives=objectives,
        objective_senses={"min_R0": "min"},
        n_samples=15,
        seed=1,
    )
    cap = build_study_capsule(rep, base, ks, lane_mode="Nominal only")
    assert cap.get("schema") == "shams.study_capsule.v1"
    assert cap.get("id")
    data = report_to_json_bytes(rep)
    assert b"trade_study.v1" in data or b"records" in data
