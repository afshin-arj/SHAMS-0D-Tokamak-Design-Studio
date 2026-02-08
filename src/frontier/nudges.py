from __future__ import annotations

"""Feasibility frontier navigation helpers.

These utilities upgrade the existing 'nearest-feasible' concept with
directional nudges based on local finite-difference sensitivities.

They are *advisory*: they do not mutate the design automatically.
"""

from dataclasses import replace
from typing import List, Dict, Any, Sequence, Optional, Tuple
import math

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore
from physics.hot_ion import hot_ion_point
from constraints.constraints import evaluate_constraints
from solvers.sensitivity import finite_difference_sensitivities


DEFAULT_KNOBS: Tuple[str, ...] = (
    "R0_m",
    "a_m",
    "B0_T",
    "Ip_MA",
    "kappa",
    "delta",
    "f_Greenwald",
    "q95_target",
)


def _constraint_margin(c) -> float:
    # consistent with run_artifact margin convention
    if getattr(c, "sense", "<=") == "<=":
        return float(getattr(c, "limit") - getattr(c, "value"))
    return float(getattr(c, "value") - getattr(c, "limit"))


def directional_nudges(
    base: PointInputs,
    *,
    knobs: Sequence[str] = DEFAULT_KNOBS,
    objective_key: str = "LCOE_proxy_USD_per_MWh",
    rel_step: float = 1e-3,
    max_suggestions: int = 8,
) -> List[Dict[str, Any]]:
    """Return a ranked list of knob nudges that improve feasibility with minimal objective penalty.

    Ranking heuristic:
    - prefer knobs with strong positive effect on *worst* hard constraint margin
    - penalize knobs that worsen objective (higher LCOE)
    """
    out0 = hot_ion_point(base) or {}
    cons0 = evaluate_constraints(out0)
    hard = [c for c in cons0 if bool(getattr(c, "hard", True))]
    failing = [c for c in hard if not bool(getattr(c, "passed", True))]

    if not failing:
        return []

    # define margin outputs for sensitivity analysis (one key per failing constraint)
    # We compute margins by re-evaluating constraints at perturbed points.
    def evaluator(inp: PointInputs) -> Dict[str, float]:
        out = hot_ion_point(inp) or {}
        cons = evaluate_constraints(out)
        d: Dict[str, float] = {}
        for c in cons:
            key = str(getattr(c, "key", getattr(c, "name", "constraint")))
            d[f"margin::{key}"] = _constraint_margin(c)
        # objective
        if objective_key in out and isinstance(out[objective_key], (int, float)):
            d[objective_key] = float(out[objective_key])
        else:
            # fallback objective
            d[objective_key] = float(out.get("COE_proxy_USD_per_MWh", float("nan")))
        return d

    fail_keys = [str(getattr(c, "key", getattr(c, "name", "constraint"))) for c in failing]
    outputs = [f"margin::{k}" for k in fail_keys] + [objective_key]
    sens = finite_difference_sensitivities(base, evaluator=evaluator, params=knobs, outputs=outputs, rel_step=rel_step)

    # choose the worst constraint by margin (most negative)
    margins = {k: float(evaluator(base).get(f"margin::{k}", float("nan"))) for k in fail_keys}
    worst_key = min(margins, key=lambda k: margins[k])
    worst_margin = margins[worst_key]

    suggestions: List[Dict[str, Any]] = []
    for knob in knobs:
        dmargin = sens.get(f"margin::{worst_key}", {}).get(knob, 0.0)
        dobj = sens.get(objective_key, {}).get(knob, 0.0)
        if not math.isfinite(dmargin) or abs(dmargin) < 1e-12:
            continue

        # required delta to bring margin to zero (linear)
        delta = (-worst_margin) / dmargin
        # ignore extreme deltas
        if not math.isfinite(delta) or abs(delta) > 10*max(abs(getattr(base, knob, 1.0)), 1.0):
            continue

        # objective change estimate
        obj_pen = dobj * delta
        # score: fix per objective penalty (higher is better); small epsilon to avoid div0
        score = (abs(-worst_margin) / (abs(obj_pen) + 1e-6)) * (1.0 if delta*dmargin > 0 else 0.1)

        suggestions.append({
            "worst_constraint_key": worst_key,
            "worst_margin": float(worst_margin),
            "knob": knob,
            "delta": float(delta),
            "dmargin_dknob": float(dmargin),
            "dobj_dknob": float(dobj),
            "objective_key": objective_key,
            "objective_delta_est": float(obj_pen),
            "score": float(score),
        })

    suggestions.sort(key=lambda s: s["score"], reverse=True)
    return suggestions[:max_suggestions]
