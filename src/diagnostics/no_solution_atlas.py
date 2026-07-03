"""NO-SOLUTION mechanism atlas (PROPOSAL-028)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from constraints.unified import build_all_constraints, dominant_failing_constraint
    from constraints.constraints import constraint_is_hard
except ImportError:
    from src.constraints.unified import build_all_constraints, dominant_failing_constraint
    from src.constraints.constraints import constraint_is_hard

_MECHANISM_TOKENS: Dict[str, tuple] = {
    "MAGNET": ("magnet", "tf", "hts", "b_peak", "quench", "v400", "v288", "structural"),
    "EXHAUST": ("exhaust", "div", "detachment", "sol", "prad", "v399", "v380", "elm", "v409", "heat flux"),
    "NEUTRONICS": ("neutronics", "tbr", "dpa", "v403", "v401", "v407", "v392", "nuclear"),
    "CONTROL": ("control", "vs_", "vde", "rwm", "v398", "v374", "stability", "mhd"),
    "TRANSPORT": ("transport", "confinement", "h98", "tau", "v396", "spread"),
    "PROFILE": ("profile", "peaking", "q95", "q0", "bootstrap", "v397"),
    "PLANT": ("plant", "economics", "availability", "v384", "v391", "capex", "cd_mix", "v408"),
    "FUEL_CYCLE": ("tritium", "fuel", "v405", "inventory", "tbr"),
}


def classify_mechanism(constraint_name: Optional[str]) -> str:
    if not constraint_name:
        return "GENERAL"
    low = str(constraint_name).lower()
    for mech, tokens in _MECHANISM_TOKENS.items():
        if any(t in low for t in tokens):
            return mech
    return "GENERAL"


def build_no_solution_atlas(
    out: Dict[str, Any],
    *,
    design_intent: Optional[str] = None,
) -> Dict[str, Any]:
    """Classify NO-SOLUTION / infeasibility by dominant mechanism (point-design scope)."""
    if not isinstance(out, dict) or not out:
        return {
            "schema": "no_solution_atlas.v1",
            "verdict": "UNKNOWN",
            "dominant_constraint": "",
            "dominant_mechanism": "GENERAL",
            "mechanism_map": {},
            "hard_failures": [],
        }

    bundle = build_all_constraints(out, design_intent=design_intent)
    dom = dominant_failing_constraint(bundle, use_governance=True)
    hard_failures: List[Dict[str, Any]] = []
    mechanism_map: Dict[str, List[str]] = {}

    for c in bundle.governance:
        if not constraint_is_hard(c):
            continue
        if bool(getattr(c, "passed", True)):
            continue
        name = str(getattr(c, "name", ""))
        mech = classify_mechanism(name)
        mechanism_map.setdefault(mech, []).append(name)
        hard_failures.append(
            {
                "name": name,
                "mechanism": mech,
                "value": float(getattr(c, "value", float("nan"))),
                "limit": float(getattr(c, "limit", float("nan"))),
                "sense": str(getattr(c, "sense", "<=")),
            }
        )

    feasible = dom is None and bundle.governance_feasible
    return {
        "schema": "no_solution_atlas.v1",
        "verdict": "FEASIBLE" if feasible else "INFEASIBLE",
        "dominant_constraint": dom or "",
        "dominant_mechanism": classify_mechanism(dom),
        "mechanism_map": {k: sorted(v) for k, v in sorted(mechanism_map.items())},
        "hard_failures": hard_failures,
        "n_hard_failures": len(hard_failures),
        "parity_aligned": bool(bundle.parity.get("pipelines_aligned", True)),
    }
