"""Systems Mode provenance honesty — PD fallback vs real Systems solve."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_normalize_never_invents_systems_solve_for_pd_blob():
    from ui_nicegui.lib.systems_artifact import (
        fetch_systems_artifact,
        normalize_systems_artifact_source,
    )
    from ui_nicegui.session import DesignSession

    assert normalize_systems_artifact_source({}) == "point_designer_fallback"
    assert (
        normalize_systems_artifact_source({"source": "systems_solve"}) == "systems_solve"
    )
    assert (
        normalize_systems_artifact_source({"source": "point_designer_apply"})
        == "point_designer_apply"
    )

    s = DesignSession()
    s.systems_last_solve_artifact = {
        "verdict": "FEASIBLE",
        "outputs": {"Q_DT_eqv": 5.0, "P_e_net_MW": 100.0},
        # missing source — Apply residue must not become systems_solve
    }
    art = fetch_systems_artifact(s)
    assert isinstance(art, dict)
    assert art.get("source") == "point_designer_fallback"


def test_has_systems_closure_ignores_pd_apply():
    from ui_nicegui.lib.helm_workflow_guide import has_systems_closure

    sess = SimpleNamespace(
        systems_last_solve_artifact={
            "source": "point_designer_apply",
            "verdict": "FEASIBLE",
            "outputs": {"Q_DT_eqv": 3.0},
        },
        systems_last_solve_result=None,
    )
    assert has_systems_closure(sess) is False

    sess.systems_last_solve_artifact = {
        "source": "systems_solve",
        "verdict": "FEASIBLE",
        "outputs": {"Q_DT_eqv": 3.0},
    }
    assert has_systems_closure(sess) is True

    sess.systems_last_solve_artifact = {"source": "systems_recovery", "verdict": "INFEASIBLE"}
    assert has_systems_closure(sess) is True

    sess.systems_last_solve_artifact = None
    sess.systems_last_solve_result = {"ok": True}
    assert has_systems_closure(sess) is True


def test_next_action_hint_apply_not_systems_solve():
    from ui_nicegui.lib.systems_labels import next_action_hint

    msg = next_action_hint(
        has_artifact=True,
        artifact_source="point_designer_apply",
        targets_ok=True,
        precheck_ok=True,
        solve_ok=True,
        n_candidates=2,
    )
    assert "not a Systems solve" in msg
    assert "target solve" in msg.lower()


def test_cockpit_markdown_labels_pd_source():
    from ui_nicegui.lib.systems_cockpit import build_compact_cockpit_markdown

    md = build_compact_cockpit_markdown(
        SimpleNamespace(systems_decision_state=None),
        {
            "source": "point_designer_fallback",
            "verdict": "INFEASIBLE",
            "outputs": {"Q_DT_eqv": 12.0, "Pfus_total_MW": 500.0},
        },
    )
    assert "Artifact source: point_designer_fallback" in md
    assert "not a Systems Mode target solve" in md


def test_apply_ui_sets_point_designer_apply_source():
    src = Path("ui_nicegui/decks/systems_mode/apply_ui.py").read_text(encoding="utf-8")
    assert 'applied_art["source"] = "point_designer_apply"' in src


def test_systems_posture_stale_and_apply_labels():
    init_src = Path("ui_nicegui/decks/systems_mode/__init__.py").read_text(encoding="utf-8")
    assert "inputs_stale" in init_src
    assert "point_designer_apply" in init_src
    assert "systems_recovery" in init_src
    vsrc = Path("ui_nicegui/decks/systems_mode/verdict.py").read_text(encoding="utf-8")
    assert "POINT DESIGNER APPLY" in vsrc
    assert "SYSTEMS RECOVERY" in vsrc
    dsrc = Path("ui_nicegui/decks/systems_mode/diagnostics_ui.py").read_text(encoding="utf-8")
    assert "NOT A SYSTEMS SOLVE" in dsrc
    assert "is_systems_result_source" in dsrc
