from __future__ import annotations
from typing import Any, Dict, List, Optional, Sequence, Tuple
import math
import numpy as np

def _safe_float(x: Any) -> float:
    try:
        v = float(x)
        return v
    except Exception:
        return float('nan')

def normalize_inputs(candidates: List[Dict[str, Any]], keys: Sequence[str]) -> np.ndarray:
    X = np.array([[ _safe_float((c.get('inputs') or {}).get(k)) for k in keys] for c in candidates], dtype=float)
    # impute non-finite with median
    for j in range(X.shape[1]):
        col = X[:, j]
        good = col[np.isfinite(col)]
        med = float(np.median(good)) if len(good) else 0.0
        col[~np.isfinite(col)] = med
        lo = float(np.min(good)) if len(good) else med - 1.0
        hi = float(np.max(good)) if len(good) else med + 1.0
        span = (hi - lo) if hi != lo else 1.0
        X[:, j] = (col - lo) / span
    return X

def diversity_prune(candidates: List[Dict[str, Any]], keys: Sequence[str], k: int) -> List[Dict[str, Any]]:
    if len(candidates) <= k:
        return candidates
    X = normalize_inputs(candidates, keys)
    chosen = [0]
    dist = np.full(len(candidates), np.inf)
    for _ in range(1, int(k)):
        last = chosen[-1]
        d = np.linalg.norm(X - X[last], axis=1)
        dist = np.minimum(dist, d)
        nxt = int(np.argmax(dist))
        if nxt in chosen:
            break
        chosen.append(nxt)
    return [candidates[i] for i in chosen]

def dominates(a: Dict[str, Any], b: Dict[str, Any], objectives: List[Dict[str, Any]]) -> bool:
    """Return True if a Pareto-dominates b under objective list.
    Objective dict fields: key, sense ('min'|'max')
    Values pulled from candidate['outputs'] primarily, fallback to candidate['cost'] or top-level.
    """
    better_or_equal = True
    strictly_better = False
    for o in objectives:
        k = str(o.get('key'))
        sense = str(o.get('sense', 'max'))
        def getv(c):
            out = c.get('outputs') or {}
            if isinstance(out, dict) and k in out:
                return _safe_float(out.get(k))
            cost = c.get('cost') or {}
            if isinstance(cost, dict) and k in cost:
                return _safe_float(cost.get(k))
            return _safe_float(c.get(k))
        va, vb = getv(a), getv(b)
        if not (math.isfinite(va) and math.isfinite(vb)):
            return False
        if sense == 'min':
            if va > vb + 1e-12:
                better_or_equal = False
                break
            if va < vb - 1e-12:
                strictly_better = True
        else:
            if va < vb - 1e-12:
                better_or_equal = False
                break
            if va > vb + 1e-12:
                strictly_better = True
    return bool(better_or_equal and strictly_better)

def annotate_dominance(archive: List[Dict[str, Any]], objectives: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    feas = [c for c in archive if bool(c.get('feasible', False))]
    if not feas or not objectives:
        for c in archive:
            c['is_dominant'] = False
        return archive
    non_dom = []
    for i,a in enumerate(feas):
        dom = False
        for j,b in enumerate(feas):
            if i==j: 
                continue
            if dominates(b,a,objectives):
                dom = True
                break
        if not dom:
            non_dom.append(a)
    non_dom_ids = set(id(x) for x in non_dom)
    for c in archive:
        c['is_dominant'] = (id(c) in non_dom_ids)
    return archive
