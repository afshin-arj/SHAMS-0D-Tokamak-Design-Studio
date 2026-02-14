from __future__ import annotations
"""Preference-Aware Decision Layer (v114)

This module is *post-feasibility* and *non-optimizing*.

It takes v113 design candidates and applies user-stated preferences as *annotations*:
- transparent weights
- normalized metrics
- per-candidate scores
- Pareto sets across candidates (using derived metrics only)

No physics changes. No solver changes. No automatic 'best design' selection.

Preference schema (JSON-serializable dict):
{
  "kind": "shams_preferences_v114",
  "created_utc": "...",
  "weights": {
    "margin": 1.0,
    "robustness": 1.0,
    "boundary_clearance": 1.0,
    "compactness": 0.3,
    "low_aux_power": 0.2
  },
  "notes": ["..."]
}

Metrics used (best-effort, derived):
- margin: worst_hard_margin_frac (higher is better)
- robustness: family_feasible_fraction (higher is better)
- boundary_clearance: mean of available boundary distances (higher is better) [2D slice proxy]
- compactness: -R0_m (smaller R0 better) normalized to (higher better)
- low_aux_power: -Paux_MW (smaller better) normalized to (higher better)
"""

from typing import Any, Dict, List, Optional, Tuple
import time
import math

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def template_preferences() -> Dict[str, Any]:
    return {
        "kind": "shams_preferences_v114",
        "created_utc": _created_utc(),
        "weights": {
            "margin": 1.0,
            "robustness": 1.0,
            "boundary_clearance": 0.7,
            "compactness": 0.3,
            "low_aux_power": 0.2,
        },
        "notes": [
            "Preferences are annotations only: they DO NOT change feasibility and DO NOT run optimizers.",
            "Weights are relative importance. Setting a weight to 0 disables the metric.",
        ],
    }

def _is_num(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False

def _get_margin(c: Dict[str, Any]) -> Optional[float]:
    feas = c.get("feasibility", {})
    if isinstance(feas, dict) and _is_num(feas.get("worst_hard_margin_frac")):
        return float(feas["worst_hard_margin_frac"])
    return None

def _get_robust(c: Dict[str, Any]) -> Optional[float]:
    rob = c.get("robustness", {})
    if isinstance(rob, dict) and _is_num(rob.get("family_feasible_fraction")):
        return float(rob["family_feasible_fraction"])
    return None

def _get_boundary_clearance(c: Dict[str, Any]) -> Optional[float]:
    bd = c.get("boundary_distance_2d", {})
    if not isinstance(bd, dict):
        return None
    vals = [float(v) for v in bd.values() if _is_num(v)]
    if not vals:
        return None
    return float(sum(vals) / len(vals))

def _get_compactness(c: Dict[str, Any]) -> Optional[float]:
    inp = c.get("inputs", {})
    if isinstance(inp, dict) and _is_num(inp.get("R0_m")):
        return -float(inp["R0_m"])
    return None

def _get_low_aux_power(c: Dict[str, Any]) -> Optional[float]:
    inp = c.get("inputs", {})
    if isinstance(inp, dict) and _is_num(inp.get("Paux_MW")):
        return -float(inp["Paux_MW"])
    return None

_METRIC_FUNS = {
    "margin": _get_margin,
    "robustness": _get_robust,
    "boundary_clearance": _get_boundary_clearance,
    "compactness": _get_compactness,
    "low_aux_power": _get_low_aux_power,
}

def _minmax(vals: List[float]) -> Tuple[float, float]:
    lo = min(vals); hi = max(vals)
    if hi - lo < 1e-12:
        hi = lo + 1e-12
    return lo, hi

def _normalize(v: float, lo: float, hi: float) -> float:
    return (v - lo) / (hi - lo)

def annotate_candidates_with_preferences(
    candidates: List[Dict[str, Any]],
    preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    prefs = preferences if isinstance(preferences, dict) else template_preferences()
    weights = prefs.get("weights", {})
    if not isinstance(weights, dict):
        weights = {}

    # compute raw metrics
    metric_raw: Dict[str, List[Optional[float]]] = {m: [] for m in _METRIC_FUNS.keys()}
    for c in candidates or []:
        for m, f in _METRIC_FUNS.items():
            metric_raw[m].append(f(c) if isinstance(c, dict) else None)

    # compute min/max per metric (over available)
    metric_bounds: Dict[str, Tuple[float, float]] = {}
    for m, arr in metric_raw.items():
        vals = [v for v in arr if _is_num(v)]
        if vals:
            metric_bounds[m] = _minmax([float(v) for v in vals])

    # annotate each candidate
    annotated: List[Dict[str, Any]] = []
    for i, c in enumerate(candidates or []):
        if not isinstance(c, dict):
            continue
        scores = {}
        normed = {}
        total = 0.0
        wsum = 0.0
        for m, f in _METRIC_FUNS.items():
            w = weights.get(m, 0.0)
            try:
                w = float(w)
            except Exception:
                w = 0.0
            raw = f(c)
            if (raw is None) or (m not in metric_bounds) or (w == 0.0):
                continue
            lo, hi = metric_bounds[m]
            n = _normalize(float(raw), lo, hi)
            normed[m] = n
            scores[m] = w * n
            total += w * n
            wsum += abs(w)

        composite = (total / wsum) if wsum > 0 else None
        out = dict(c)
        out["preference_annotation_v114"] = {
            "kind": "shams_candidate_preference_annotation_v114",
            "created_utc": _created_utc(),
            "preferences": {"weights": weights},
            "metrics_raw": {m: metric_raw[m][i] for m in metric_raw.keys()},
            "metrics_normalized": normed,
            "metric_scores": scores,
            "composite_score": composite,
            "disclaimer": "Annotation only. Not an optimizer; does not select a 'best' design.",
        }
        annotated.append(out)

    return {
        "kind": "shams_preference_annotation_bundle_v114",
        "created_utc": _created_utc(),
        "preferences": prefs,
        "metric_bounds": {m: [float(a), float(b)] for m, (a, b) in metric_bounds.items()},
        "candidates": annotated,
    }

def _dominates(a: Dict[str, Any], b: Dict[str, Any], keys: List[str]) -> bool:
    """Return True if a dominates b on all keys (>=) and strictly better on at least one."""
    better = False
    for k in keys:
        av = a.get(k); bv = b.get(k)
        if not (_is_num(av) and _is_num(bv)):
            return False
        av = float(av); bv = float(bv)
        if av < bv:
            return False
        if av > bv:
            better = True
    return better

def pareto_sets_from_annotations(
    annotated_bundle: Dict[str, Any],
    metrics: Optional[List[str]] = None,
    max_fronts: int = 3,
) -> Dict[str, Any]:
    """Compute Pareto fronts across candidates using normalized metrics."""
    if not isinstance(annotated_bundle, dict):
        return {"kind":"shams_pareto_sets_v114","created_utc": _created_utc(), "fronts": []}
    cands = annotated_bundle.get("candidates", [])
    if not isinstance(cands, list):
        return {"kind":"shams_pareto_sets_v114","created_utc": _created_utc(), "fronts": []}

    if metrics is None:
        metrics = ["margin", "robustness", "boundary_clearance"]
    metrics = [m for m in metrics if isinstance(m, str)]

    # Build points as dict with id + normalized metrics available
    pts = []
    for c in cands:
        if not isinstance(c, dict):
            continue
        ann = c.get("preference_annotation_v114", {})
        norm = ann.get("metrics_normalized", {}) if isinstance(ann, dict) else {}
        if not isinstance(norm, dict):
            continue
        row = {"id": c.get("source_artifact_id")}
        ok = True
        for m in metrics:
            if m not in norm or not _is_num(norm[m]):
                ok = False
                break
            row[m] = float(norm[m])
        if ok:
            pts.append(row)

    remaining = pts[:]
    fronts = []
    for _ in range(int(max_fronts)):
        front = []
        for a in remaining:
            dominated = False
            for b in remaining:
                if a is b:
                    continue
                if _dominates(b, a, metrics):
                    dominated = True
                    break
            if not dominated:
                front.append(a)
        if not front:
            break
        # remove
        rem2 = []
        front_ids = {f["id"] for f in front}
        for r in remaining:
            if r.get("id") not in front_ids:
                rem2.append(r)
        remaining = rem2
        fronts.append(front)

    return {
        "kind": "shams_pareto_sets_v114",
        "created_utc": _created_utc(),
        "metrics": metrics,
        "fronts": fronts,
        "n_points": len(pts),
    }
