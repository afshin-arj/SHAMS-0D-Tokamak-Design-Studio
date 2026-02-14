from __future__ import annotations
"""
Local sensitivity analysis (finite-difference), PROCESS-style.

Goal: give designers immediate intuition for which knobs move key outputs,
without requiring full optimization runs.

This module is intentionally lightweight:
- Uses central finite differences where possible
- Works on the PointInputs dataclass
- Calls the standard hot_ion_point() evaluator

Returned sensitivities are *local* derivatives at the chosen point.
"""
from dataclasses import replace
from typing import Dict, Iterable, Callable, Tuple, Any

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    try:
        from models.inputs import PointInputs  # type: ignore
    except Exception:
        from models.inputs import PointInputs  # type: ignore

MetricFn = Callable[[PointInputs], Dict[str, float]]

def finite_difference_sensitivities(
    base: PointInputs,
    evaluator: MetricFn,
    params: Iterable[str],
    outputs: Iterable[str],
    rel_step: float = 1e-3,
    abs_steps: Dict[str, float] | None = None,
) -> Dict[str, Dict[str, float]]:
    """
    Compute d(output)/d(param) using central differences.

    - rel_step: default relative perturbation (e.g. 1e-3 -> 0.1%)
    - abs_steps: optional per-parameter absolute step override

    Returns: sens[output][param] = derivative (output units per param unit)
    """
    abs_steps = abs_steps or {}
    base_out = evaluator(base)
    sens: Dict[str, Dict[str, float]] = {o: {} for o in outputs}

    for p in params:
        if not hasattr(base, p):
            continue
        x0 = getattr(base, p)
        if x0 is None:
            continue
        try:
            x0f = float(x0)
        except Exception:
            continue

        h = abs_steps.get(p, abs(x0f) * rel_step if x0f != 0.0 else rel_step)
        if h == 0.0:
            h = rel_step

        # Build +h and -h points
        plus = replace(base, **{p: x0f + h})
        minus = replace(base, **{p: x0f - h})

        out_p = evaluator(plus)
        out_m = evaluator(minus)

        for o in outputs:
            yp = float(out_p.get(o, float("nan")))
            ym = float(out_m.get(o, float("nan")))
            if yp != yp or ym != ym:  # NaN guard
                continue
            sens[o][p] = (yp - ym) / (2.0 * h)

    # Helpful: include base outputs snapshot
    sens["_base"] = {o: float(base_out.get(o, float("nan"))) for o in outputs}  # type: ignore
    return sens
