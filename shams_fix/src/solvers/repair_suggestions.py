"""Repair suggestions (v296.0).

Explanatory-only tool:
- Proposes bounded deltas to reduce dominant constraint residuals.
- Must be verified by frozen truth; this module does NOT claim feasibility.

Inputs are expected to come from deterministic sensitivity packs.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


@dataclass(frozen=True)
class RepairKnob:
    name: str
    lo: float
    hi: float


@dataclass(frozen=True)
class RepairCandidate:
    deltas: Dict[str, float]
    rationale: str
    estimated_residual_reduction: float


def propose_repair_candidates(
    residuals: Dict[str, float],
    jacobian: Dict[str, Dict[str, float]],
    knobs: List[RepairKnob],
    k: int = 6,
    step_fraction: float = 0.35,
) -> List[RepairCandidate]:
    """Generate a small set of deterministic repair candidates.

    Args:
        residuals: constraint residuals (positive means violation).
        jacobian: nested dict jacobian[constraint][var] ~ d(residual)/dvar.
        knobs: allowed knobs and bounds.
        k: number of candidates.
        step_fraction: fraction of knob range for proposed delta.

    Returns:
        List of RepairCandidate. Deterministic ordering.
    """

    # Select most-violated constraints
    viol = [(c, float(r)) for c, r in residuals.items() if float(r) > 0.0]
    viol.sort(key=lambda x: x[1], reverse=True)
    top_constraints = [c for c, _ in viol[: max(1, min(3, len(viol)) )]]

    knob_map = {kb.name: kb for kb in knobs}

    candidates: List[RepairCandidate] = []

    for c in top_constraints:
        grads = jacobian.get(c, {})
        # Rank knobs by ability to reduce residual: want negative delta*grad.
        scored: List[Tuple[str, float]] = []
        for vn, g in grads.items():
            if vn not in knob_map:
                continue
            g = float(g)
            if g == 0.0:
                continue
            # If increasing var reduces residual (g<0), positive delta helps.
            scored.append((vn, abs(g)))
        scored.sort(key=lambda x: x[1], reverse=True)

        for vn, _ in scored[: max(1, min(3, len(scored)) )]:
            kb = knob_map[vn]
            span = kb.hi - kb.lo
            delta = step_fraction * span
            # direction from gradient sign: residual decreases if delta * grad < 0
            g = float(grads.get(vn, 0.0))
            if g > 0:
                delta = -abs(delta)
            else:
                delta = abs(delta)

            est = abs(delta * g)
            cand = RepairCandidate(
                deltas={vn: float(delta)},
                rationale=f"Reduce '{c}' via knob '{vn}' (grad={g:+.3g})",
                estimated_residual_reduction=float(est),
            )
            candidates.append(cand)

    # Deterministic pruning
    candidates.sort(key=lambda cc: (cc.estimated_residual_reduction, cc.rationale), reverse=True)
    return candidates[: max(0, int(k))]
