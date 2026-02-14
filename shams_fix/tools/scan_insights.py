from __future__ import annotations

"""Scan Lab — extra insight helpers (0‑D).

Additive, deterministic utilities that enrich Scan Lab without turning it into an optimizer.

Implements:
1) Constraint causality traces (finite-difference sensitivity chain)
2) Worst-case envelope scanning (local uncertainty stress test)
3) Uncertainty-aware dominance (dominant-constraint probabilities)
4) Time-to-failure intuition (percent push-to-fail along knobs)
5) Null-direction discovery (flat direction in 2D scan)

Design rules:
- Uses the same frozen evaluator; never relaxes constraints.
- Deterministic given seed.
"""

from dataclasses import replace
import math
import random
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def _constraint_margin_by_name(constraints: List[Dict[str, Any]], name: str) -> Optional[float]:
    target = (name or "").strip().lower()
    for c in constraints or []:
        if not isinstance(c, dict):
            continue
        if str(c.get("severity", "hard")).lower() != "hard":
            continue
        nm = str(c.get("name", "")).strip().lower()
        if nm != target:
            continue
        m = c.get("margin_frac")
        try:
            mm = float(m)
            if _finite(mm):
                return mm
        except Exception:
            pass
    return None


def build_causality_trace(
    *,
    evaluator,
    base_inputs,
    point_overrides: Dict[str, float],
    constraint_name: str,
    knobs: List[str],
    rel_step: float = 0.01,
) -> Dict[str, Any]:
    """Finite-difference sensitivity trace for a specific hard constraint.

Returns a compact, reproducible explanation: which knobs most change the
constraint margin, and through which key outputs (if present).

This is not symbolic algebra — it's a local sensitivity report.
"""
    # Build point
    p = base_inputs
    try:
        p = replace(base_inputs, **{k: float(v) for k, v in (point_overrides or {}).items()})
    except Exception:
        pass

    res0 = evaluator.evaluate(p)
    out0 = dict(res0.out or {})
    cons0 = out0.get("constraints") or []
    m0 = _constraint_margin_by_name(cons0, constraint_name)

    drivers: List[Dict[str, Any]] = []
    for k in knobs or []:
        if not hasattr(p, k):
            continue
        try:
            v0 = float(getattr(p, k))
        except Exception:
            continue
        if not _finite(v0) or v0 == 0:
            continue
        dv = rel_step * abs(v0)

        # central difference
        try:
            p_hi = replace(p, **{k: v0 + dv})
            p_lo = replace(p, **{k: v0 - dv})
        except Exception:
            continue
        r_hi = evaluator.evaluate(p_hi)
        r_lo = evaluator.evaluate(p_lo)
        o_hi = dict(r_hi.out or {})
        o_lo = dict(r_lo.out or {})
        m_hi = _constraint_margin_by_name(o_hi.get("constraints") or [], constraint_name)
        m_lo = _constraint_margin_by_name(o_lo.get("constraints") or [], constraint_name)
        if not _finite(m_hi) or not _finite(m_lo):
            continue
        dmdk = (float(m_hi) - float(m_lo)) / (2.0 * dv)

        # Key outputs that help explain (optional)
        explain_keys = ["P_fus_MW", "P_sep_MW", "q_div_MW_m2", "B_peak_T", "q95", "TBR", "sigma_vm_MPa", "HTS_margin"]
        deltas = {}
        for kk in explain_keys:
            if kk in out0 and kk in o_hi:
                try:
                    deltas[kk] = float(o_hi.get(kk)) - float(out0.get(kk))
                except Exception:
                    pass
        drivers.append({
            "knob": k,
            "v0": float(v0),
            "rel_step": float(rel_step),
            "d_margin_d_knob": float(dmdk),
            "margin_delta_plus": float(m_hi) - float(m0) if _finite(m0) else None,
            "margin_delta_minus": float(m_lo) - float(m0) if _finite(m0) else None,
            "output_deltas_plus": deltas,
        })

    drivers.sort(key=lambda d: abs(float(d.get("d_margin_d_knob", 0.0))), reverse=True)
    return {
        "constraint": str(constraint_name),
        "margin0": float(m0) if _finite(m0) else None,
        "point": {k: float(v) for k, v in (point_overrides or {}).items()},
        "drivers": drivers[: min(8, len(drivers))],
        "note": "Local sensitivity (finite differences). Not a global proof.",
    }


def uncertainty_stress_test(
    *,
    evaluator,
    base_inputs,
    point_overrides: Dict[str, float],
    intent: str,
    nuisance_keys: List[str],
    rel_unc: float = 0.03,
    n_samples: int = 60,
    seed: int = 7,
) -> Dict[str, Any]:
    """Worst-case envelope scan around a point.

Perturbs selected nuisance keys by ±rel_unc (uniform) and evaluates the
intent-feasibility and dominant constraint distribution.
"""
    from tools.scan_cartography import intent_feasible

    p0 = base_inputs
    try:
        p0 = replace(base_inputs, **{k: float(v) for k, v in (point_overrides or {}).items()})
    except Exception:
        pass

    rng = random.Random(int(seed))
    dom_counts: Dict[str, int] = {}
    ok = 0
    worst_margin = float("inf")
    worst_dom: Optional[str] = None
    worst_sample: Dict[str, float] = {}

    for _ in range(int(max(1, n_samples))):
        kwargs = {}
        for k in nuisance_keys or []:
            if not hasattr(p0, k):
                continue
            try:
                v = float(getattr(p0, k))
            except Exception:
                continue
            if not _finite(v):
                continue
            dv = (2.0 * rng.random() - 1.0) * float(rel_unc) * (abs(v) if v != 0 else 1.0)
            kwargs[k] = v + dv
        try:
            p = replace(p0, **kwargs)
        except Exception:
            p = p0

        res = evaluator.evaluate(p)
        cons = (dict(res.out or {}).get("constraints") or [])
        summ = intent_feasible(cons, intent)
        dom = str(summ.get("dominant_blocking") or "PASS")
        dom_counts[dom] = dom_counts.get(dom, 0) + 1
        if bool(summ.get("blocking_feasible")):
            ok += 1
        mm = summ.get("min_blocking_margin")
        try:
            m = float(mm)
        except Exception:
            m = float("nan")
        if _finite(m) and m < worst_margin:
            worst_margin = float(m)
            worst_dom = dom
            worst_sample = {k: float(v) for k, v in kwargs.items()}

    tot = int(max(1, n_samples))
    dom_probs = {k: v / tot for k, v in sorted(dom_counts.items(), key=lambda kv: kv[1], reverse=True)}
    return {
        "intent": str(intent),
        "n_samples": tot,
        "rel_unc": float(rel_unc),
        "ok_prob": ok / tot,
        "dominant_probs": dom_probs,
        "worst_min_margin": float(worst_margin) if _finite(worst_margin) else None,
        "worst_dominant": worst_dom,
        "worst_sample_overrides": worst_sample,
    }


def time_to_failure_along_knob(
    *,
    evaluator,
    base_inputs,
    point_overrides: Dict[str, float],
    intent: str,
    knob: str,
    direction: float,
    max_rel: float = 0.5,
    tol: float = 1e-3,
    max_iter: int = 24,
) -> Optional[float]:
    """Return the relative change (fraction of current) until point becomes infeasible.

Binary searches along a single knob direction from a starting feasible point.
Returns None if point is already infeasible or never fails within max_rel.
"""
    from tools.scan_cartography import intent_feasible

    p0 = base_inputs
    try:
        p0 = replace(base_inputs, **{k: float(v) for k, v in (point_overrides or {}).items()})
    except Exception:
        pass
    if not hasattr(p0, knob):
        return None
    try:
        v0 = float(getattr(p0, knob))
    except Exception:
        return None
    if not _finite(v0) or v0 == 0:
        return None

    def ok_at(rel: float) -> bool:
        try:
            p = replace(p0, **{knob: v0 * (1.0 + float(rel) * float(direction))})
        except Exception:
            p = p0
        res = evaluator.evaluate(p)
        cons = (dict(res.out or {}).get("constraints") or [])
        return bool(intent_feasible(cons, intent).get("blocking_feasible"))

    if not ok_at(0.0):
        return None

    lo = 0.0
    hi = float(max_rel)
    if ok_at(hi):
        return None
    for _ in range(int(max_iter)):
        mid = 0.5 * (lo + hi)
        if ok_at(mid):
            lo = mid
        else:
            hi = mid
        if abs(hi - lo) < float(tol):
            break
    return float(hi)


def null_direction_2d(gx: float, gy: float) -> Dict[str, Any]:
    """Given gradient components, return a unit 'flat' direction (perpendicular)."""
    try:
        gx = float(gx)
        gy = float(gy)
    except Exception:
        return {"ok": False}
    n = math.hypot(gx, gy)
    if not _finite(n) or n <= 0:
        return {"ok": False}
    # gradient points to increasing margin; flat direction is perpendicular
    fx, fy = -gy / n, gx / n
    return {"ok": True, "flat_dir": [float(fx), float(fy)], "grad_dir": [float(gx / n), float(gy / n)]}
