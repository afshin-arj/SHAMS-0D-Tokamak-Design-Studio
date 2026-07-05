"""Design-intent constraint policy (mirrors ui/app.py intent sets)."""
from __future__ import annotations

from typing import Any, Dict, List, Set

_INTENT_HARD = {
    "reactor": {"q95", "q_div", "P_SOL/R", "sigma_vm", "B_peak", "HTS margin", "TBR", "NWL"},
    "research": {"q95"},
}
_INTENT_SOFT = {
    "reactor": set(),
    "research": {"q_div", "P_SOL/R", "sigma_vm", "B_peak", "HTS margin", "NWL"},
}
_INTENT_IGNORE = {
    "reactor": set(),
    "research": {"TBR"},
}


def design_intent_key(design_intent: str) -> str:
    s = str(design_intent or "").strip().lower()
    if s.startswith("experimental") or s.startswith("research") or "research" in s:
        return "research"
    return "reactor"


def constraint_policy_snapshot(design_intent: str) -> Dict[str, Any]:
    k = design_intent_key(design_intent)
    return {
        "design_intent": str(design_intent),
        "intent_key": k,
        "hard_blocking": sorted(_INTENT_HARD.get(k, set())),
        "diagnostic_only": sorted(_INTENT_SOFT.get(k, set())),
        "ignored": sorted(_INTENT_IGNORE.get(k, set())),
    }


def classify_failed_constraints(
    failed_names: List[str] | None,
    *,
    design_intent: str,
) -> Dict[str, List[str]]:
    k = design_intent_key(design_intent)
    hard: Set[str] = _INTENT_HARD.get(k, set())
    soft: Set[str] = _INTENT_SOFT.get(k, set())
    ignore: Set[str] = _INTENT_IGNORE.get(k, set())
    blocking: List[str] = []
    diagnostic: List[str] = []
    ignored: List[str] = []
    for name in failed_names or []:
        nm = str(name)
        if nm in ignore:
            ignored.append(nm)
        elif nm in soft:
            diagnostic.append(nm)
        elif nm in hard or k == "reactor":
            blocking.append(nm)
        else:
            diagnostic.append(nm)
    return {"blocking": blocking, "diagnostic": diagnostic, "ignored": ignored}


def hard_constraint_names_for_intent(design_intent: str) -> Set[str]:
    k = design_intent_key(design_intent)
    return set(_INTENT_HARD.get(k, set()))


def ignored_constraint_names_for_intent(design_intent: str) -> Set[str]:
    k = design_intent_key(design_intent)
    return set(_INTENT_IGNORE.get(k, set()))


def policy_caption(design_intent: str) -> str:
    pol = constraint_policy_snapshot(design_intent)
    if pol.get("intent_key") == "reactor":
        return "Policy: Reactor hard constraints enforced."
    return "Policy: Research intent — only q95 is blocking; engineering limits are diagnostic; TBR ignored."
