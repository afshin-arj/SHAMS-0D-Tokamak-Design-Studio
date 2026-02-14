from __future__ import annotations

"""Optimization Sandbox — Archive Intelligence (descriptive).

Provides light-weight clustering/coverage cues for the Candidate Machine Archive.

Discipline:
- No selection, no best-point logic.
- These summaries are derived from already-evaluated archive entries.
"""

from typing import Any, Dict, List, Sequence

import math
import numpy as np


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _vector(inp: Dict[str, Any], keys: Sequence[str]) -> np.ndarray:
    return np.array([_safe_float(inp.get(k)) for k in keys], dtype=float)


def ladder_histogram(archive: List[Dict[str, Any]]) -> Dict[str, int]:
    h: Dict[str, int] = {}
    for r in archive or []:
        s = str(r.get("feasibility_state") or ("feasible" if r.get("feasible") else "infeasible"))
        h[s] = int(h.get(s, 0)) + 1
    return h


def regime_clusters_summary(
    *,
    archive: List[Dict[str, Any]],
    var_keys: Sequence[str],
    max_k: int = 10,
    seed: int = 0,
) -> Dict[str, Any]:
    """A minimal clustering summary for feasible points.

    Returns cluster centers and counts using k-means when available.
    If scikit-learn is not available, returns a simple random-centroid fallback.
    """
    feas = [r for r in (archive or []) if r.get("feasible", False)]
    if len(feas) < 8 or len(var_keys) < 1:
        return {"ok": False, "reason": "insufficient_feasible_points", "n_feasible": int(len(feas))}

    X = np.array([_vector(r.get("inputs") or {}, var_keys) for r in feas], dtype=float)
    for j in range(X.shape[1]):
        col = X[:, j]
        good = col[np.isfinite(col)]
        med = float(np.median(good)) if good.size else 0.0
        col[~np.isfinite(col)] = med
        X[:, j] = col

    # choose k ~ sqrt(n/2) capped
    k = int(min(max_k, max(2, round(math.sqrt(len(feas) / 2)))))

    labels = None
    centers = None
    try:
        from sklearn.cluster import KMeans  # type: ignore

        km = KMeans(n_clusters=k, random_state=seed, n_init=10)
        labels = km.fit_predict(X)
        centers = km.cluster_centers_
    except Exception:
        rng = np.random.default_rng(seed)
        idx = rng.choice(np.arange(len(feas)), size=k, replace=False)
        centers = X[idx]
        labels = np.argmin(((X[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2), axis=1)

    clusters: List[Dict[str, Any]] = []
    for ci in range(int(k)):
        members = np.where(labels == ci)[0]
        if members.size == 0:
            continue
        clusters.append({
            "id": int(ci),
            "n": int(members.size),
            "center": {k2: float(v2) for k2, v2 in zip(var_keys, centers[ci].tolist())},
        })
    clusters.sort(key=lambda c: int(c.get("n", 0)), reverse=True)

    return {
        "ok": True,
        "n_feasible": int(len(feas)),
        "k": int(k),
        "clusters": clusters,
        "note": "Clusters remember regimes; they are descriptive only.",
    }
