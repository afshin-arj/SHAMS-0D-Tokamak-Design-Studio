from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from evaluator.core import Evaluator
try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore


@dataclass(frozen=True)
class ConstraintActionExplanation:
    constraint_name: str
    why_failed: str
    dominant_inputs: List[Tuple[str, float]]
    recommended_knob_moves: List[str]


def explain_failing_constraint(
    evaluator: Evaluator,
    inp: PointInputs,
    constraint_name: str,
    *,
    candidate_inputs: Optional[List[str]] = None,
    top_n: int = 5,
    rel_step: float = 1e-3,
) -> ConstraintActionExplanation:
    """Explain a failing constraint in a transparent, PROCESS-inspired way.

    This is intentionally conservative:
    - uses local finite-difference sensitivities of *constraint margin* to inputs
    - recommends knob moves based on sign of sensitivity
    - does not assume an optimizer
    """
    res = evaluator.evaluate(inp)
    cons = res.out.get("constraints") or []
    c = None
    for ci in cons:
        if str(ci.get("name")) == str(constraint_name):
            c = ci
            break
    if c is None:
        return ConstraintActionExplanation(
            constraint_name=constraint_name,
            why_failed="Constraint not found in outputs.",
            dominant_inputs=[],
            recommended_knob_moves=[],
        )

    passed = bool(c.get("passed", True))
    sense = str(c.get("sense", "<="))
    val = c.get("value")
    lim = c.get("limit")
    mf = c.get("margin_frac")
    if passed:
        why = "Constraint currently passes."
    else:
        why = f"Failed because value {sense} limit is violated (value={val}, limit={lim}, margin_frac={mf})."

    # Sensitivities: d(margin_frac)/d(input)
    if candidate_inputs is None:
        candidate_inputs = [k for k, v in inp.__dict__.items() if isinstance(v, (int, float))]

    dom: List[Tuple[str, float]] = []
    for k in candidate_inputs:
        try:
            deriv = evaluator.derivative(inp, out_key=f"constraint_margin_frac::{constraint_name}", in_key=k, rel_step=rel_step)
            if deriv is None:
                continue
            dom.append((k, float(deriv)))
        except Exception:
            continue

    # Rank by absolute magnitude
    dom.sort(key=lambda kv: abs(kv[1]), reverse=True)
    dom = dom[:top_n]

    moves: List[str] = []
    if not passed and dom:
        for k, dmdx in dom[:min(3, len(dom))]:
            if dmdx == 0:
                continue
            # Want to increase margin_frac toward >= 0
            direction = "increase" if dmdx > 0 else "decrease"
            moves.append(f"{direction} `{k}` (locally improves margin; sensitivity={dmdx:+.3g})")

    return ConstraintActionExplanation(
        constraint_name=str(constraint_name),
        why_failed=why,
        dominant_inputs=dom,
        recommended_knob_moves=moves,
    )
