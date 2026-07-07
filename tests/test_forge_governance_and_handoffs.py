"""Forge governance fields and export handoff panel."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ui_nicegui.decks.reactor_design_forge import handoff_panel
from ui_nicegui.lib.forge_machine_finder_helpers import evaluate_forge_candidate, make_evaluate_fn
from ui_nicegui.session import DesignSession


def test_evaluate_forge_candidate_governance_fields() -> None:
    from dataclasses import asdict

    s = DesignSession()
    res = evaluate_forge_candidate(asdict(s.build_point_inputs()), "Research")
    assert "governance_feasible" in res
    assert "intent_feasible" in res
    assert isinstance(res.get("blocking_failures"), list)


def test_make_evaluate_fn_other_intent_tracking() -> None:
    calls: list[str] = []

    def _fake_eval(inp, intent, **kw):
        calls.append(str(intent))
        return {
            "feasible": True,
            "outputs": {},
            "constraints": [],
            "min_signed_margin": 0.1,
        }

    fn = make_evaluate_fn("Reactor", [], track_other_intent=True)
    with patch(
        "ui_nicegui.lib.forge_machine_finder_helpers.evaluate_forge_candidate",
        side_effect=_fake_eval,
    ):
        res = fn({"R0_m": 2.0})
    assert "Research" in calls
    assert res.get("other_intent") == "Research"


def test_handoff_panel_callable() -> None:
    assert callable(handoff_panel.render_archive_handoffs)


def test_legacy_streamlit_forge_removed() -> None:
    root = Path(__file__).resolve().parents[1]
    assert not (root / "ui" / "decks" / "reactor_design_forge.py").exists()
