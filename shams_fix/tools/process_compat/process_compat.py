from __future__ import annotations
"""
PROCESS-compatibility helpers for SHAMS–FUSION-X.

Design principles:
- Additive only: no physics/solver behavior changes.
- Feasibility-first: operate only on SHAMS-evaluated points.
- Explicit outputs: margins, active constraints, failure modes.

These tools are intended to help external workflows (including PROCESS)
consume SHAMS feasible sets and to re-audit externally optimized points.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import hashlib, json, math

@dataclass(frozen=True)
class ConstraintRecord:
    name: str
    value: float
    lo: Optional[float]
    hi: Optional[float]
    ok: bool
    residual: float
    signed_margin: float  # >0 means inside bounds; <0 means violated

def _signed_margin(value: float, lo: Optional[float], hi: Optional[float]) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    margins = []
    if lo is not None:
        margins.append(value - lo)
    if hi is not None:
        margins.append(hi - value)
    if not margins:
        return float("nan")
    # Positive means inside all declared bounds. If any bound violated, at least one margin is negative.
    return float(min(margins))

def constraints_to_records(constraints: List[Any]) -> List[ConstraintRecord]:
    """
    Convert SHAMS constraints objects (Constraint) to stable records.
    """
    out: List[ConstraintRecord] = []
    for c in constraints:
        try:
            name = str(getattr(c, "name", ""))
            value = float(getattr(c, "value", float("nan")))
            lo = getattr(c, "lo", None)
            hi = getattr(c, "hi", None)
            lo_f = None if lo is None else float(lo)
            hi_f = None if hi is None else float(hi)
            ok = bool(getattr(c, "ok", False))
            residual = float(c.residual()) if hasattr(c, "residual") else (0.0 if ok else float("nan"))
            sm = _signed_margin(value, lo_f, hi_f)
        except Exception:
            # Keep it robust; never crash a run because a single constraint is malformed.
            name, value, lo_f, hi_f, ok, residual, sm = "", float("nan"), None, None, False, float("nan"), float("nan")
        out.append(ConstraintRecord(name=name, value=value, lo=lo_f, hi=hi_f, ok=ok, residual=residual, signed_margin=sm))
    return out

def active_constraints(records: List[ConstraintRecord], top_k: int = 5, **_ignored: object) -> List[ConstraintRecord]:
    """
    Return the most limiting constraints by smallest signed margin (feasible) or most negative (infeasible).
    """
    def key(r: ConstraintRecord) -> float:
        if isinstance(r.signed_margin, float) and math.isnan(r.signed_margin):
            return float("inf")
        return r.signed_margin
    ranked = sorted(records, key=key)
    return ranked[:max(1, int(top_k))]

def feasibility_flag(records: List[ConstraintRecord], **_ignored: object) -> bool:
    return all(r.ok for r in records if r.name)

def failure_mode(records: List[ConstraintRecord], **_ignored: object) -> str:
    """
    Conservative failure-mode label. This is intentionally simple and stable.
    """
    if feasibility_flag(records):
        return "feasible"
    return "infeasible_constraint_violation"

def constraint_set_hash(records: List[ConstraintRecord]) -> str:
    """
    Hash names and bounds only (not values) to identify the constraint set.
    """
    payload = [{"name": r.name, "lo": r.lo, "hi": r.hi} for r in records if r.name]
    blob = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()

def to_jsonable(records: List[ConstraintRecord]) -> List[Dict[str, Any]]:
    return [
        {
            "name": r.name,
            "value": r.value,
            "lo": r.lo,
            "hi": r.hi,
            "ok": r.ok,
            "residual": r.residual,
            "signed_margin": r.signed_margin,
        }
        for r in records
    ]

def nondominated_mask(points: List[Dict[str, Any]], objectives: List[Tuple[str, str]]) -> List[bool]:
    """
    Simple Pareto nondominance filter.
    objectives: list of (key, sense) where sense is 'min' or 'max'.
    """
    def better_or_equal(a, b) -> bool:
        for k, s in objectives:
            av, bv = a.get(k, float("nan")), b.get(k, float("nan"))
            if math.isnan(av) or math.isnan(bv):
                return False
            if s == "min" and av > bv:  # worse
                return False
            if s == "max" and av < bv:
                return False
        return True

    def strictly_better(a, b) -> bool:
        strictly = False
        for k, s in objectives:
            av, bv = a.get(k, float("nan")), b.get(k, float("nan"))
            if math.isnan(av) or math.isnan(bv):
                return False
            if s == "min":
                if av < bv: strictly = True
                elif av > bv: return False
            else:
                if av > bv: strictly = True
                elif av < bv: return False
        return strictly

    n = len(points)
    nd = [True] * n
    for i in range(n):
        if not nd[i]:
            continue
        for j in range(n):
            if i == j:
                continue
            if better_or_equal(points[j], points[i]) and strictly_better(points[j], points[i]):
                nd[i] = False
                break
    return nd
