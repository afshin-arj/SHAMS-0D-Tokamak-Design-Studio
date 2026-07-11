"""Control Room workflow tests."""
from __future__ import annotations

from ui_nicegui.decks.control_room import render_control_room
from ui_nicegui.lib.control_room_helpers import ARTIFACT_TABS, BENCHMARK_REFERENCE_ROWS, CONST_TABS
from ui_nicegui.lib.control_room_labels import CR_WORKFLOW_TABS, DECISION_TO_TAB, normalize_cr_tab
from ui_nicegui.lib.cr_governance_helpers import (
    authority_confidence_rows,
    constraint_ledger_rows,
    constraint_names,
    decision_consequences_summary,
    design_confidence_class,
)
from ui_nicegui.session import DesignSession


def test_control_room_renderer_import() -> None:
    assert callable(render_control_room)


def test_cr_workflow_tabs() -> None:
    assert len(CR_WORKFLOW_TABS) == 6
    assert normalize_cr_tab("Orientation") == "1 · Orient"
    assert DECISION_TO_TAB["Audit study provenance & replay"] == "3 · Provenance"


def test_constitution_and_artifact_tabs_extended() -> None:
    assert "Assumptions" in CONST_TABS
    assert "Constraints" in CONST_TABS
    assert "Constraint Provenance" in CONST_TABS
    assert "Benchmark Reference" in ARTIFACT_TABS


def test_benchmark_reference_rows() -> None:
    assert len(BENCHMARK_REFERENCE_ROWS) >= 8
    assert any(r["Tokamak"] == "ITER" for r in BENCHMARK_REFERENCE_ROWS)


def test_governance_helpers_on_minimal_artifact() -> None:
    art = {
        "authority_confidence": {
            "design": {"design_confidence_class": "B"},
            "subsystems": {"confinement": {"confidence_class": "B", "authority_tier": "parametric", "involved": True}},
        },
        "decision_consequences": {"decision_posture": "CAUTION", "primary_risk_driver": "q95"},
        "constraint_ledger": {
            "entries": [{"name": "q95", "passed": False, "margin_frac": -0.1, "failed": True}],
        },
        "constraints": [{"name": "q95", "failed": True, "margin": -0.1}],
    }
    assert design_confidence_class(art) == "B"
    assert len(authority_confidence_rows(art)) == 1
    assert decision_consequences_summary(art)["decision_posture"] == "CAUTION"
    assert constraint_names(art) == ["q95"]
    rows = constraint_ledger_rows(art, failed_only=True)
    assert rows and rows[0]["name"] == "q95"


def test_session_cr_workflow_fields() -> None:
    s = DesignSession()
    assert s.cr_workflow_step == "1 · Orient"
    assert s.cr_teaching_mode is True
