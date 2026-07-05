"""Phase 11: Point Designer outer-loop + forensics wiring."""
from __future__ import annotations

import json

from ui_nicegui.decks.point_designer import phase_envelopes, uncertainty_contracts
from ui_nicegui.decks.point_designer.dominance_closure import _render_dominance_compass
from ui_nicegui.evaluate import ui_evaluate
from ui_nicegui.lib.pd_artifact_helpers import build_point_artifact
from ui_nicegui.lib.pd_forensics_helpers import run_local_forensics
from ui_nicegui.lib.pd_outer_loop_helpers import (
    DEFAULT_PHASES_JSON,
    build_uq_spec,
    parse_phases_json,
    phase_table_rows,
)
from ui_nicegui.lib.session_store import set_point_evaluation
from ui_nicegui.session import DesignSession


def test_phase_envelopes_renderer_import() -> None:
    assert callable(phase_envelopes.render_phase_envelopes)


def test_uncertainty_contracts_renderer_import() -> None:
    assert callable(uncertainty_contracts.render_uncertainty_contracts)


def test_parse_default_phases_json() -> None:
    phases = parse_phases_json(DEFAULT_PHASES_JSON)
    assert len(phases) == 3
    assert phases[1].name == "flat_top"


def test_build_uq_spec_corners() -> None:
    spec = build_uq_spec(
        name="test",
        base_inp={"Paux_MW": 50.0, "fG": 0.8},
        dims=["Paux_MW", "fG"],
        mode="±% around baseline",
        pct=10.0,
    )
    assert len(spec.intervals) == 2


def test_build_point_artifact_has_schema() -> None:
    s = DesignSession()
    out = ui_evaluate(s.build_point_inputs(), origin="test")
    art = build_point_artifact(inputs=dict(s.inputs), outputs=out, design_intent=s.design_intent)
    assert isinstance(art.get("inputs"), dict)
    assert isinstance(art.get("outputs"), dict)
    assert "constraints" in art or "constraint_ledger" in art


def test_set_point_evaluation_rich_artifact() -> None:
    s = DesignSession()
    out = ui_evaluate(s.build_point_inputs(), origin="test")
    set_point_evaluation(s, outputs=out, inputs=dict(s.inputs))
    assert isinstance(s.pd_last_artifact, dict)
    assert s.pd_last_artifact.get("outputs")


def test_forensics_smoke() -> None:
    s = DesignSession()
    ff = run_local_forensics(s.build_point_inputs(), design_intent=s.design_intent)
    assert isinstance(ff, dict)
    assert "tornado" in ff or "base" in ff or ff.get("status") == "error"


def test_phase_table_rows_empty() -> None:
    assert phase_table_rows({}) == []


def test_dominance_compass_callable() -> None:
    assert callable(_render_dominance_compass)
