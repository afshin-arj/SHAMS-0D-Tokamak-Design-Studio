"""Feasibility completion assistant — propose / apply / undo (Streamlit parity)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ui_nicegui.lib.pd_intent_policy import hard_constraint_names_for_intent
from ui_nicegui.lib.systems_state_helpers import resolve_systems_problem


def _get_evaluator():
    from ui_nicegui.evaluate import ui_evaluator

    return ui_evaluator(origin="NiceGUI:SystemsAssistant", cache_enabled=True, cache_max=4096)


def propose_feasibility_changes(
    session: Any,
    *,
    n_random: int = 8,
    seed: int = 1337,
) -> List[dict]:
    try:
        from src.systems.feasibility_completion import propose_feasibility_completion
    except ImportError:
        from systems.feasibility_completion import propose_feasibility_completion  # type: ignore

    base, targets, variables = resolve_systems_problem(session)
    if not targets or not variables:
        return []
    ev = _get_evaluator()
    hard = hard_constraint_names_for_intent(session.design_intent)
    props = propose_feasibility_completion(
        base,
        targets,
        variables,
        evaluator=ev,
        include_random=True,
        n_random=int(n_random),
        seed=int(seed),
        max_k_changes=2,
        hard_constraint_names=hard if hard else None,
    )
    out: List[dict] = []
    for p in props:
        out.append({
            "kind": str(getattr(p, "kind", "")),
            "description": str(getattr(p, "description", "")),
            "score": float(getattr(p, "score", 0.0)),
            "changes": dict(getattr(p, "changes", {}) or {}),
        })
    out.sort(key=lambda x: float(x.get("score", 0)), reverse=True)
    return out[:8]
