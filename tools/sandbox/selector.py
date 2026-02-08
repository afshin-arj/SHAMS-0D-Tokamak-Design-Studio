from __future__ import annotations
"""
Optimization Sandbox (SAFE):
- Operates ONLY on SHAMS frozen feasible sets (e.g., feasible_scan.json).
- Never relaxes constraints.
- Produces rankings/selections and manifest hashes.
- Optional SHAMS re-audit of Top-K candidates for confidence.

NON-AUTHORITATIVE: This layer does not change SHAMS truth.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional
import hashlib, json, math

@dataclass(frozen=True)
class Objective:
    key: str
    sense: str  # "min" or "max"
    weight: float = 1.0

def _get_metric(point: Dict[str, Any], key: str) -> float:
    # Key may be at root or inside outputs
    if key in point and isinstance(point[key], (int, float)):
        return float(point[key])
    out = point.get("outputs", {})
    if isinstance(out, dict) and key in out and isinstance(out[key], (int, float)):
        return float(out[key])
    return float("nan")

def _normalize(vals: List[float]) -> List[float]:
    good = [v for v in vals if not (isinstance(v, float) and math.isnan(v))]
    if not good:
        return [float("nan")] * len(vals)
    lo, hi = min(good), max(good)
    if hi == lo:
        return [0.0 if not math.isnan(v) else float("nan") for v in vals]
    return [(v - lo) / (hi - lo) if not math.isnan(v) else float("nan") for v in vals]

def rank_feasible_points(points: List[Dict[str, Any]], objectives: List[Objective]) -> List[Dict[str, Any]]:
    """
    Weighted sum on normalized objectives (explicit & simple).
    For min objectives, lower is better; we invert so higher score is better.
    """
    if not objectives:
        raise ValueError("No objectives provided")

    # Precompute normalized values per objective
    norm_by_obj: Dict[str, List[float]] = {}
    for obj in objectives:
        raw = [_get_metric(p, obj.key) for p in points]
        norm = _normalize(raw)
        if obj.sense == "min":
            norm = [1.0 - v if not math.isnan(v) else float("nan") for v in norm]
        norm_by_obj[obj.key] = norm

    ranked = []
    for i, p in enumerate(points):
        score = 0.0
        ok = True
        contrib = {}
        for obj in objectives:
            v = norm_by_obj[obj.key][i]
            if math.isnan(v):
                ok = False
                break
            c = obj.weight * v
            score += c
            contrib[obj.key] = {"sense": obj.sense, "weight": obj.weight, "norm": v, "contrib": c, "raw": _get_metric(p, obj.key)}
        if not ok:
            continue
        q = dict(p)
        q["_sandbox_score"] = score
        q["_sandbox_objective_contrib"] = contrib
        ranked.append(q)

    ranked.sort(key=lambda x: x["_sandbox_score"], reverse=True)
    return ranked

def manifest_hash(obj: Any) -> str:
    blob = json.dumps(obj, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()

def filter_by_min_margin(points: List[Dict[str, Any]], min_margin: Optional[float]) -> List[Dict[str, Any]]:
    if min_margin is None:
        return points
    out = []
    for p in points:
        m = p.get("min_signed_margin", None)
        if isinstance(m, (int, float)) and m >= float(min_margin):
            out.append(p)
    return out
