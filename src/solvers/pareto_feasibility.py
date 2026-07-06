"""Pareto Lab feasibility — unified governance + intent-aware blocking (Point Designer parity)."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

try:
    from constraints.unified import build_all_constraints, dominant_failing_constraint
    from constraints.constraints import constraint_is_hard
except ImportError:
    from src.constraints.unified import build_all_constraints, dominant_failing_constraint
    from src.constraints.constraints import constraint_is_hard

# Mirrors ui_nicegui/lib/pd_intent_policy.py and src/decision/requirements_trace.py
_INTENT_HARD = {
    "reactor": {"q95", "q_div", "P_SOL/R", "sigma_vm", "B_peak", "TF_SC", "HTS margin", "TBR", "NWL"},
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


def intent_key(intent_key: str) -> str:
    s = str(intent_key or "Reactor").strip().lower()
    if s.startswith("research") or s.startswith("experimental") or "research" in s:
        return "research"
    return "reactor"


def _canonical_constraint_name(name: str) -> str:
    s = str(name or "").strip()
    sl = s.lower()
    if sl == "q95" or sl.startswith("q95"):
        return "q95"
    if "divertor" in sl and "heat" in sl:
        return "q_div"
    if "sol power" in sl or "p_sol" in sl or "p_sol/r" in sl:
        return "P_SOL/R"
    if "von mises" in sl:
        return "sigma_vm"
    if "hoop" in sl:
        return "sigma_hoop"
    if "tf peak field" in sl or "peak field" in sl or sl == "b_peak":
        return "B_peak"
    if "hts margin" in sl:
        return "HTS margin"
    if "tbr" in sl or "tritium breeding" in sl:
        return "TBR"
    if "neutron" in sl and "wall" in sl:
        return "NWL"
    if "tf_sc" in sl or "superconductor" in sl:
        return "TF_SC"
    return s


def _classify_failed(failed_canon: List[str], *, design_intent: str) -> Dict[str, List[str]]:
    k = intent_key(design_intent)
    hard = _INTENT_HARD.get(k, set())
    soft = _INTENT_SOFT.get(k, set())
    ignore = _INTENT_IGNORE.get(k, set())
    blocking: List[str] = []
    diagnostic: List[str] = []
    ignored: List[str] = []
    for name in failed_canon:
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


def annotate_pareto_feasibility(out: Dict[str, Any], design_intent: str) -> Dict[str, Any]:
    """Return feasibility annotation aligned with Point Designer governance + intent policy."""
    bundle = build_all_constraints(out)
    gov_feasible = bool(bundle.governance_feasible)
    gov_dom = dominant_failing_constraint(bundle, use_governance=True)

    failed_canon: List[str] = []
    mmin = float("inf")
    dom_tight = None
    for c in bundle.governance:
        if not constraint_is_hard(c):
            continue
        m = float(c.margin)
        if m != m:
            if not bool(c.passed):
                m = -1e9
            else:
                m = float("nan")
        if m == m and m < mmin:
            mmin = m
            dom_tight = _canonical_constraint_name(str(c.name))
        if not bool(c.passed):
            failed_canon.append(_canonical_constraint_name(str(c.name)))

    cls = _classify_failed(failed_canon, design_intent=design_intent)
    blocking = cls["blocking"]
    pareto_feasible = len(blocking) == 0

    if not pareto_feasible:
        dom_name = blocking[0] if blocking else (gov_dom or dom_tight or "(unknown)")
    else:
        dom_name = dom_tight or "(none)"

    return {
        "is_feasible": bool(pareto_feasible),
        "governance_feasible": gov_feasible,
        "dominant_constraint": str(dom_name),
        "min_constraint_margin": float(mmin) if mmin != float("inf") else float("nan"),
        "first_failure": str(dom_name) if not pareto_feasible else "",
        "blocking_failures": list(blocking),
        "diagnostic_failures": list(cls["diagnostic"]),
        "ignored_failures": list(cls["ignored"]),
        "feasibility_mode": "governance+intent",
        "governance_dominant": gov_dom,
    }


def pareto_feasibility_tuple(out: Dict[str, Any], design_intent: str) -> Tuple[bool, str, float]:
    ann = annotate_pareto_feasibility(out, design_intent)
    return (
        bool(ann["is_feasible"]),
        str(ann["dominant_constraint"]),
        float(ann["min_constraint_margin"]),
    )
