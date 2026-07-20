"""Systems Mode session-state merge — base overrides, bounds, targets, undo."""

from __future__ import annotations

from dataclasses import fields, replace
from typing import Any, Dict, Tuple

from ui_nicegui.lib.systems_precheck import build_targets_and_variables


def validate_systems_problem(
    targets: Dict[str, float],
    variables: Dict[str, Tuple[float, float, float]],
) -> tuple[bool, str]:
    """Newton solve requires #targets == #variables."""
    nt, nv = len(targets), len(variables)
    if nt == 0 or nv == 0:
        return False, "Enable at least one performance target and one adjustable variable."
    if nt != nv:
        return (
            False,
            f"Target solve needs equal counts ({nt} targets vs {nv} knobs). "
            "Example: Q + H98 → enable I_p and f_G; or drop one target.",
        )
    return True, ""


def apply_input_overrides(base, overrides: Dict[str, float] | None):
    if not overrides:
        return base
    valid = {f.name for f in fields(base)}
    kwargs = {k: float(v) for k, v in overrides.items() if k in valid}
    return replace(base, **kwargs) if kwargs else base


def apply_bounds_overrides(
    variables: Dict[str, Tuple[float, float, float]],
    bounds_overrides: Dict[str, Dict[str, float]] | None,
) -> Dict[str, Tuple[float, float, float]]:
    if not bounds_overrides:
        return dict(variables)
    out = dict(variables)
    for vk, bc in bounds_overrides.items():
        if vk not in out or not isinstance(bc, dict):
            continue
        x0, lo, hi = out[vk]
        x02 = float(bc.get("x0", x0))
        lo2 = float(bc.get("lo", lo))
        hi2 = float(bc.get("hi", hi))
        out[vk] = (x02, lo2, hi2)
    return out


def apply_target_overrides(
    targets: Dict[str, float],
    target_overrides: Dict[str, float] | None,
) -> Dict[str, float]:
    if not target_overrides:
        return dict(targets)
    out = dict(targets)
    for k, v in target_overrides.items():
        out[k] = float(v)
    return out


def merge_base_overrides_into_session(session: Any, overrides: Dict[str, float]) -> None:
    for k, v in overrides.items():
        if k in session.inputs:
            session.inputs[k] = float(v)
    hist = list(getattr(session, "systems_base_history", []) or [])
    hist.append({"base_overrides": dict(getattr(session, "systems_base_overrides", {}) or {}), "source": "apply"})
    session.systems_base_history = hist[-20:]
    session.systems_base_overrides = dict(overrides)
    # Inputs changed — keep prior PD outputs but refresh Helm so STALE posture is visible.
    try:
        from ui_nicegui.lib.navigation import refresh_helm, refresh_status

        refresh_helm()
        refresh_status()
    except Exception:
        pass


def resolve_systems_problem(session: Any, base=None) -> tuple[Any, Dict[str, float], Dict[str, Tuple[float, float, float]]]:
    """Return (base_with_overrides, targets, variables) for precheck/solve/atlas."""
    if base is None:
        base = session.build_point_inputs()
    bo = dict(getattr(session, "systems_base_overrides", {}) or {})
    if bo:
        base = apply_input_overrides(base, bo)
    io = dict(getattr(session, "systems_inputs_overrides", {}) or {})
    base = apply_input_overrides(base, io)
    targets, variables = build_targets_and_variables(session, base)
    targets = apply_target_overrides(targets, getattr(session, "systems_targets_overrides", None))
    variables = apply_bounds_overrides(variables, getattr(session, "systems_bounds_overrides", None))
    return base, targets, variables


def push_assistant_undo(session: Any, *, targets: dict, variables: dict) -> None:
    stack = list(getattr(session, "systems_undo_stack", []) or [])
    stack.append({
        "targets": dict(getattr(session, "systems_targets_overrides", {}) or {}),
        "bounds_overrides": dict(getattr(session, "systems_bounds_overrides", {}) or {}),
        "inputs_overrides": dict(getattr(session, "systems_inputs_overrides", {}) or {}),
        "session_targets": dict(targets),
        "session_variables_keys": list(variables.keys()),
    })
    session.systems_undo_stack = stack[-12:]


def pop_assistant_undo(session: Any) -> bool:
    stack = list(getattr(session, "systems_undo_stack", []) or [])
    if not stack:
        return False
    last = stack.pop()
    session.systems_undo_stack = stack
    session.systems_targets_overrides = dict(last.get("targets") or {})
    session.systems_bounds_overrides = dict(last.get("bounds_overrides") or {})
    session.systems_inputs_overrides = dict(last.get("inputs_overrides") or {})
    return True


def apply_proposal_to_session(session: Any, proposal: dict) -> None:
    ch = proposal.get("changes") or {}
    if "bounds" in ch:
        bo = dict(getattr(session, "systems_bounds_overrides", {}) or {})
        for vk, bc in (ch.get("bounds") or {}).items():
            if isinstance(bc, dict):
                bo[vk] = {k: float(v) for k, v in bc.items() if v is not None}
        session.systems_bounds_overrides = bo
    if "targets" in ch:
        to = dict(getattr(session, "systems_targets_overrides", {}) or {})
        for tk, tv in (ch.get("targets") or {}).items():
            to[tk] = float(tv)
        session.systems_targets_overrides = to
    if "constraints" in ch:
        ov = dict(getattr(session, "systems_inputs_overrides", {}) or {})
        for kk, vv in (ch.get("constraints") or {}).items():
            ov[kk] = float(vv)
        session.systems_inputs_overrides = ov
    session.systems_last_applied_change = dict(proposal)


def append_journal(session: Any, kind: str, payload: dict | None = None) -> None:
    import time

    j = list(getattr(session, "systems_journal", []) or [])
    j.append({
        "ts_unix": time.time(),
        "kind": str(kind),
        "workflow_step": str(getattr(session, "systems_workflow_step", "")),
        "design_intent": str(getattr(session, "design_intent", "")),
        **(payload or {}),
    })
    session.systems_journal = j[-200:]
