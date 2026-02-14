from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, List, Optional, Tuple, Set
import math
import random


def _is_hard_enforced(c: Any, hard_set: Optional[Set[str]]) -> bool:
    """Return True if this constraint should be treated as 'hard' under the active policy."""
    name = str(getattr(c, 'name', ''))
    sev = str(getattr(c, 'severity', 'soft'))
    if hard_set is None:
        return sev == 'hard'
    return name in hard_set


try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:  # pragma: no cover
    from models.inputs import PointInputs  # type: ignore

try:
    from ..constraints.constraints import evaluate_constraints  # type: ignore
except Exception:  # pragma: no cover
    from constraints.constraints import evaluate_constraints  # type: ignore


def _clamp(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))


def _isfinite(x: float) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def normalized_distance(seed: Dict[str, float], x: Dict[str, float], bounds: Dict[str, Dict[str, float]], weights: Optional[Dict[str, float]] = None) -> float:
    """Normalized squared distance in bound-scaled space."""
    s = 0.0
    for k, b in bounds.items():
        lo = float(b.get('lo', float('nan')))
        hi = float(b.get('hi', float('nan')))
        if not (_isfinite(lo) and _isfinite(hi) and hi > lo):
            continue
        w = float((weights or {}).get(k, 1.0))
        dx = (float(x.get(k, (lo + hi) / 2.0)) - float(seed.get(k, (lo + hi) / 2.0))) / (hi - lo)
        s += w * dx * dx
    return float(s)


def hard_violation_score(constraints: List[Any], nan_penalty: float = 1e6, hard_constraint_names: Optional[Set[str]] = None) -> Tuple[float, Dict[str, float]]:
    """Return (V, per_constraint_violation) for hard constraints.

    - If a hard constraint margin is NaN/non-finite, apply nan_penalty.
    - Otherwise violation is max(0, -margin).
    """
    total = 0.0
    per: Dict[str, float] = {}
    hard_set = set(hard_constraint_names) if hard_constraint_names else None
    for c in constraints:
        name = str(getattr(c, 'name', ''))
        if not _is_hard_enforced(c, hard_set):
            continue
        m = getattr(c, 'margin', float('nan'))
        if not _isfinite(m):
            v = float(nan_penalty)
        else:
            v = float(max(0.0, -float(m)))
        per[name] = v
        total += v
    return float(total), per


def nan_diagnostics(constraints: List[Any], hard_constraint_names: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    """Return structured info for any hard constraints that are numerically invalid.

    A constraint becomes "numerically invalid" when its value or limit is non-finite,
    which causes its margin to become NaN. We treat this as a hard failure with a
    large penalty in recovery, but we also surface the *cause* for debugging.
    """
    diags: List[Dict[str, Any]] = []
    hard_set = set(hard_constraint_names) if hard_constraint_names else None
    for c in constraints:
        try:
            if not _is_hard_enforced(c, hard_set):
                continue
        except Exception:
            continue
        try:
            name = str(getattr(c, 'name', ''))
            value = getattr(c, 'value', float('nan'))
            limit = getattr(c, 'limit', float('nan'))
            sense = str(getattr(c, 'sense', ''))
            m = getattr(c, 'margin', float('nan'))
            if (not _isfinite(m)) or (not _isfinite(value)) or (not _isfinite(limit)):
                diags.append({
                    'name': name,
                    'value': float(value) if _isfinite(value) else float('nan'),
                    'limit': float(limit) if _isfinite(limit) else float('nan'),
                    'sense': sense,
                    'margin': float(m) if _isfinite(m) else float('nan'),
                })
        except Exception:
            continue
    return diags


def _build_inputs(base: PointInputs, x: Dict[str, float]) -> PointInputs:
    # filter only valid PointInputs fields
    fields = getattr(base, '__dataclass_fields__', {})
    d: Dict[str, Any] = {}
    for k, v in x.items():
        if k in fields:
            try:
                d[k] = float(v)
            except Exception:
                pass
    return replace(base, **d)


def _evaluate(evaluator: Any, base: PointInputs, x: Dict[str, float], hard_constraint_names: Optional[Set[str]] = None) -> Tuple[bool, Dict[str, float], List[Any], float, Dict[str, float], List[Dict[str, Any]]]:
    """Evaluate a candidate point.

    Returns: (ok_eval, outputs, constraints, V, per_violation, nan_diags)
    """
    inp = _build_inputs(base, x)
    res = evaluator.evaluate(inp)
    if not getattr(res, 'ok', True):
        return False, {}, [], float('inf'), {}, []
    out = getattr(res, 'out', {}) or {}
    try:
        cons = evaluate_constraints(out)
    except Exception:
        cons = []
    V, per = hard_violation_score(cons, hard_constraint_names=hard_constraint_names)
    ndiag = nan_diagnostics(cons, hard_constraint_names=hard_constraint_names)
    return True, out, cons, V, per, ndiag


def recover_feasible_near_seed(
    *,
    base: PointInputs,
    variables: Dict[str, Dict[str, float]],
    evaluator: Any,
    seed: Optional[Dict[str, float]] = None,
    weights: Optional[Dict[str, float]] = None,
    rng_seed: int = 123,
    budget_evals: int = 200,
    local_steps: int = 60,
    multi_start: int = 30,
    initial_step_frac: float = 0.15,
    min_step_frac: float = 0.01,
    hard_constraint_names: Optional[Set[str]] = None,
    return_trace: bool = False,
    trace_keep: int = 2000,
) -> Dict[str, Any]:
    """Attempt to find a feasible point close to seed.

    The search is deterministic given rng_seed.

    variables is a dict: {var: {'lo': float, 'hi': float}}

    Returns a dict with fields:
      ok: bool
      reason: str
      best_point: {var: value}
      seed_point: {var: value}
      best_V: float
      best_distance: float
      best_violations: {constraint: violation}
      best_margins: {constraint: margin}
      evals: int
    """

    # Optional evaluation trace for UI/debugging and frontier visualization.
    # Kept intentionally lightweight: each item stores x, V, feasible flag, and
    # (if available) the single most violated constraint.
    trace: List[Dict[str, Any]] = []

    def _trace_add(x: Dict[str, float], ok_eval: bool, V: float, per: Dict[str, float]) -> None:
        if not return_trace:
            return
        try:
            dom = None
            if isinstance(per, dict) and per:
                dom = max(per.items(), key=lambda kv: float(kv[1]))[0]
            trace.append({
                'x': {k: float(v) for k, v in (x or {}).items()},
                'ok_eval': bool(ok_eval),
                'V': float(V),
                'feasible': bool(float(V) <= 0.0),
                'dominant': dom,
            })
            # bound memory
            if int(trace_keep) > 0 and len(trace) > int(trace_keep):
                del trace[: max(1, len(trace) - int(trace_keep))]
        except Exception:
            return

    # Prepare bounds in canonical form and seed
    bounds: Dict[str, Dict[str, float]] = {}
    for k, b in (variables or {}).items():
        try:
            lo = float(b.get('lo'))
            hi = float(b.get('hi'))
        except Exception:
            continue
        if not (_isfinite(lo) and _isfinite(hi) and hi > lo):
            continue
        bounds[str(k)] = {'lo': lo, 'hi': hi}

    if not bounds:
        return {'ok': False, 'reason': 'no_variables', 'evals': 0, 'trace': trace if return_trace else None}

    # Seed defaults to midpoint
    seed_pt: Dict[str, float] = {}
    for k, b in bounds.items():
        mid = (b['lo'] + b['hi']) / 2.0
        seed_pt[k] = float(mid)
    if isinstance(seed, dict):
        for k, v in seed.items():
            if k in bounds and _isfinite(v):
                seed_pt[k] = _clamp(float(v), bounds[k]['lo'], bounds[k]['hi'])

    rng = random.Random(int(rng_seed))

    # Canonical hard-constraint enforcement set for this recovery run.
    # If None, we fall back to constraint.severity == 'hard'.
    hard_set = set(hard_constraint_names) if hard_constraint_names else None

    # Evaluate seed
    evals = 0
    ok_eval, out, cons, V, per, ndiag = _evaluate(evaluator, base, seed_pt, hard_constraint_names=hard_constraint_names)
    _trace_add(seed_pt, ok_eval, float(V), per)
    evals += 1

    best_point = dict(seed_pt)
    best_V = float(V)
    best_per = dict(per)
    best_nan = list(ndiag)

    # Extract margins
    best_margins: Dict[str, float] = {}
    for c in cons:
        try:
            if _is_hard_enforced(c, hard_set):
                best_margins[str(getattr(c, 'name', ''))] = float(getattr(c, 'margin', float('nan')))
        except Exception:
            pass


    def is_feasible(Vv: float) -> bool:
        return float(Vv) <= 0.0

    best_dist = normalized_distance(seed_pt, best_point, bounds, weights)

    # If seed is feasible, return immediately.
    if is_feasible(best_V):
        return {
            'ok': True,
            'reason': 'seed_feasible',
            'seed_point': seed_pt,
            'best_point': best_point,
            'best_V': best_V,
            'best_distance': best_dist,
            'best_violations': best_per,
            'best_margins': best_margins,
            'best_nan': best_nan,
            'evals': evals,
            'trace': trace if return_trace else None,
        }

    # --- Stage 1: Local coordinate search in a trust region around current best ---
    step_frac = float(max(min(initial_step_frac, 1.0), 0.01))

    var_keys = list(bounds.keys())

    def propose_neighbors(center: Dict[str, float], sf: float) -> List[Dict[str, float]]:
        props: List[Dict[str, float]] = []
        for k in var_keys:
            lo = bounds[k]['lo']
            hi = bounds[k]['hi']
            span = hi - lo
            step = sf * span
            for sgn in (-1.0, 1.0):
                x = dict(center)
                x[k] = _clamp(float(center[k]) + sgn * step, lo, hi)
                props.append(x)
        # Deterministic shuffle (so it doesn't bias earlier keys)
        rng.shuffle(props)
        return props

    local_budget = int(min(local_steps, max(0, budget_evals - evals)))
    it = 0
    while it < local_budget and evals < budget_evals:
        improved = False
        for cand in propose_neighbors(best_point, step_frac):
            ok_eval, out, cons, Vc, perc, _ndi = _evaluate(evaluator, base, cand, hard_constraint_names=hard_constraint_names)
            _trace_add(cand, ok_eval, float(Vc), perc)
            evals += 1
            if not ok_eval:
                continue

            if (Vc < best_V - 1e-12):
                best_point = dict(cand)
                best_V = float(Vc)
                best_per = dict(perc)
                best_margins = {}
                for c in cons:
                    try:
                        if _is_hard_enforced(c, hard_set):
                            best_margins[str(getattr(c, 'name', ''))] = float(getattr(c, 'margin', float('nan')))
                    except Exception:
                        pass
                best_nan = nan_diagnostics(cons, hard_constraint_names=hard_constraint_names)
                best_dist = normalized_distance(seed_pt, best_point, bounds, weights)
                improved = True

                if is_feasible(best_V):
                    return {
                        'ok': True,
                        'reason': 'local_repair',
                        'seed_point': seed_pt,
                        'best_point': best_point,
                        'best_V': best_V,
                        'best_distance': best_dist,
                        'best_violations': best_per,
                        'best_margins': best_margins,
                        'best_nan': best_nan,
                        'evals': evals,
                    }

            # Stop if budget
            if evals >= budget_evals:
                break

        # Adapt step size
        if improved:
            step_frac = min(0.5, step_frac * 1.15)
        else:
            step_frac = max(float(min_step_frac), step_frac * 0.6)
        it += 1

    # --- Stage 2: Multi-start cloud around seed (normalized jitter) ---
    remaining = max(0, budget_evals - evals)
    n_ms = int(min(multi_start, remaining))

    def sample_near_seed() -> Dict[str, float]:
        x = {}
        for k, b in bounds.items():
            lo = b['lo']
            hi = b['hi']
            mid = seed_pt[k]
            span = hi - lo
            # Jitter ~ N(0, 0.2) in normalized space, truncated.
            z = rng.gauss(0.0, 0.20)
            z = max(-0.8, min(0.8, z))
            x[k] = _clamp(mid + z * span, lo, hi)
        return x

    best_feasible: Optional[Dict[str, Any]] = None

    for _ in range(n_ms):
        cand = sample_near_seed()
        ok_eval, out, cons, Vc, perc, _ndi = _evaluate(evaluator, base, cand, hard_constraint_names=hard_constraint_names)
        _trace_add(cand, ok_eval, float(Vc), perc)
        evals += 1
        if not ok_eval:
            continue

        dist = normalized_distance(seed_pt, cand, bounds, weights)
        if is_feasible(Vc):
            margins: Dict[str, float] = {}
            for c in cons:
                try:
                    if _is_hard_enforced(c, hard_set):
                        margins[str(getattr(c, 'name', ''))] = float(getattr(c, 'margin', float('nan')))
                except Exception:
                    pass
            rec = {
                'point': dict(cand),
                'V': float(Vc),
                'dist': float(dist),
                'violations': dict(perc),
                'margins': margins,
                'nan': nan_diagnostics(cons, hard_constraint_names=hard_constraint_names),
            }
            if (best_feasible is None) or (rec['dist'] < best_feasible['dist'] - 1e-12):
                best_feasible = rec
        else:
            # Track best infeasible too
            if (Vc < best_V - 1e-12) or (abs(Vc - best_V) <= 1e-12 and dist < best_dist - 1e-12):
                best_point = dict(cand)
                best_V = float(Vc)
                best_per = dict(perc)
                best_dist = float(dist)
                best_margins = {}
                for c in cons:
                    try:
                        if _is_hard_enforced(c, hard_set):
                            best_margins[str(getattr(c, 'name', ''))] = float(getattr(c, 'margin', float('nan')))
                    except Exception:
                        pass
                best_nan = nan_diagnostics(cons, hard_constraint_names=hard_constraint_names)

    if best_feasible is not None:
        return {
            'ok': True,
            'reason': 'multistart',
            'seed_point': seed_pt,
            'best_point': best_feasible['point'],
            'best_V': best_feasible['V'],
            'best_distance': best_feasible['dist'],
            'best_violations': best_feasible['violations'],
            'best_margins': best_feasible['margins'],
            'best_nan': best_feasible.get('nan', []),
            'evals': evals,
            'trace': trace if return_trace else None,
        }

    return {
        'ok': False,
        'reason': 'no_feasible_found',
        'seed_point': seed_pt,
        'best_point': best_point,
        'best_V': best_V,
        'best_distance': best_dist,
        'best_violations': best_per,
        'best_margins': best_margins,
        'best_nan': best_nan,
        'evals': evals,
        'trace': trace if return_trace else None,
    }
