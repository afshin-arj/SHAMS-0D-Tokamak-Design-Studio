from __future__ import annotations

"""Deterministic bracketing solvers.

These utilities provide solver-like convenience while preserving SHAMS law:
- the frozen evaluator is the only truth
- iteration is bounded and fully logged
- outputs are verifiable bounds / certified candidates

Typical use-cases
-----------------
- Find minimum Paux such that Q_DT_eqv >= Q_min
- Find maximum fG such that q_div_MW_m2 <= cap

The caller supplies a scalar function f(x) computed from a PointInputs point via
hot_ion_point, along with a feasibility predicate.
"""

from dataclasses import asdict, replace
from typing import Callable, Dict, Any, Optional, Tuple

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore

from physics.hot_ion import hot_ion_point
from constraints.system import build_constraints_from_outputs, summarize_constraints


class BracketingError(RuntimeError):
    pass


def bisection_bound(
    base: PointInputs,
    var: str,
    lo: float,
    hi: float,
    *,
    target: Callable[[Dict[str, Any]], float],
    sense: str,
    threshold: float,
    require_feasible: bool = True,
    n_iter: int = 24,
) -> Dict[str, Any]:
    """Bounded bisection on a single variable.

    Parameters
    ----------
    sense: 'ge' or 'le'
        We seek the smallest x meeting target(out) >= threshold (ge) or <= threshold (le).

    Returns
    -------
    dict with keys:
      - status: OK | BRACKET_FAIL
      - best: verified candidate artifact (inputs/outputs/constraints_summary)
      - log: list of evaluated points (x, target, feasible, worst_margin)
    """
    if sense not in {"ge", "le"}:
        raise ValueError("sense must be 'ge' or 'le'")
    if n_iter < 1:
        n_iter = 1

    def _eval(x: float) -> Tuple[float, bool, Dict[str, Any]]:
        inp = replace(base, **{var: float(x)})
        out = hot_ion_point(inp)
        cs = build_constraints_from_outputs(out)
        summ = summarize_constraints(cs).to_dict()
        feas = bool(summ.get("feasible", False))
        y = float(target(out))
        art = {
            "inputs": dict(inp.__dict__),
            "outputs": dict(out),
            "constraints_summary": summ,
        }
        return y, feas, art

    log = []

    y_lo, feas_lo, art_lo = _eval(lo)
    y_hi, feas_hi, art_hi = _eval(hi)

    def _meets(y: float) -> bool:
        return (y >= threshold) if sense == "ge" else (y <= threshold)

    ok_lo = _meets(y_lo) and (feas_lo or not require_feasible)
    ok_hi = _meets(y_hi) and (feas_hi or not require_feasible)

    log.append({"x": float(lo), "target": float(y_lo), "feasible": bool(feas_lo), "meets": bool(ok_lo)})
    log.append({"x": float(hi), "target": float(y_hi), "feasible": bool(feas_hi), "meets": bool(ok_hi)})

    if not ok_hi and not ok_lo:
        return {"schema_version": "bracketing.v1", "status": "BRACKET_FAIL", "reason": "no_endpoint_meets", "log": log}

    # Want smallest meeting point: ensure hi meets.
    if not ok_hi and ok_lo:
        # swap
        lo, hi = hi, lo
        y_lo, y_hi = y_hi, y_lo
        feas_lo, feas_hi = feas_hi, feas_lo
        art_lo, art_hi = art_hi, art_lo
        ok_lo, ok_hi = ok_hi, ok_lo

    if not ok_hi:
        return {"schema_version": "bracketing.v1", "status": "BRACKET_FAIL", "reason": "no_hi_meets", "log": log}

    best = art_hi
    for _ in range(int(n_iter)):
        mid = 0.5 * (lo + hi)
        y_m, feas_m, art_m = _eval(mid)
        ok_m = _meets(y_m) and (feas_m or not require_feasible)
        log.append({"x": float(mid), "target": float(y_m), "feasible": bool(feas_m), "meets": bool(ok_m)})
        if ok_m:
            hi = mid
            best = art_m
        else:
            lo = mid

    return {"schema_version": "bracketing.v1", "status": "OK", "best": best, "log": log, "var": var, "sense": sense, "threshold": float(threshold)}
