"""Systems Mode Apply / recovery CTA feasibility gating."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_next_action_hint_gates_infeasible_only_candidates():
    from ui_nicegui.lib.systems_labels import next_action_hint

    ready = next_action_hint(
        has_artifact=True,
        artifact_source="systems_solve",
        targets_ok=True,
        precheck_ok=True,
        solve_ok=True,
        n_candidates=3,
        n_feasible=2,
    )
    assert "feasible candidate" in ready
    assert "promote on **4 · Apply**" in ready

    diag = next_action_hint(
        has_artifact=True,
        artifact_source="systems_solve",
        targets_ok=True,
        precheck_ok=True,
        solve_ok=True,
        n_candidates=3,
        n_feasible=0,
    )
    assert "none intent-feasible" in diag
    assert "diagnostic seed" in diag
    assert "ready — promote" not in diag


def test_next_action_hint_recovery_without_feasible():
    from ui_nicegui.lib.systems_labels import next_action_hint

    msg = next_action_hint(
        has_artifact=True,
        artifact_source="systems_recovery",
        targets_ok=True,
        precheck_ok=True,
        solve_ok=True,
        n_candidates=1,
        n_feasible=0,
    )
    assert "without a feasible point" in msg
    assert "diagnostic seed" in msg


def test_has_systems_closure_rejects_infeasible_recovery():
    from types import SimpleNamespace

    from ui_nicegui.lib.helm_workflow_guide import has_systems_closure, suggest_next_deck

    sess = SimpleNamespace(
        systems_last_solve_artifact={"source": "systems_recovery", "verdict": "INFEASIBLE"},
        systems_last_solve_result=None,
        pd_last_outputs={"Q_DT_eqv": 1.0},
        last_eval=None,
        pd_verdict_summary_cache={"loaded": True, "feasible": True},
        cmp_slot_a=None,
        cmp_slot_b=None,
        cmp_use_slot_a=True,
        cmp_use_slot_b=True,
        scan_cartography_report=None,
        scan_cartography_artifact=None,
    )
    assert has_systems_closure(sess) is False
    deck, reason = suggest_next_deck(sess, "Systems Mode")
    assert deck is None
    assert "close systems" in reason.lower() or "precheck" in reason.lower() or "continue" in reason.lower()
    assert "Systems closed" not in reason


def test_apply_and_recover_ui_wire_gates():
    apply_src = Path("ui_nicegui/decks/systems_mode/apply_ui.py").read_text(encoding="utf-8")
    assert "Apply diagnostic seed to PD & re-evaluate" in apply_src
    assert "No feasible candidate selected" in apply_src
    assert 'for c in cands if bool(c.get("feasible"))' in apply_src

    rec_src = Path("ui_nicegui/decks/systems_mode/recover_ui.py").read_text(encoding="utf-8")
    assert "Apply diagnostic seed → Point Designer" in rec_src
    assert "Apply best feasible → Point Designer" in rec_src
    assert "diagnostic: bool = False" in rec_src

    helm = Path("ui_nicegui/lib/helm_workflow_guide.py").read_text(encoding="utf-8")
    assert "explicit diagnostic seed" in helm
    assert "_systems_artifact_intent_feasible" in helm
