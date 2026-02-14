from __future__ import annotations

"""Deterministic Design-Family Regime Maps & Narratives (v324)

Purpose
-------
Given a set of evaluated designs (typically a Trade Study record list), build:

1) Deterministic clustering of *feasible* designs into "families".
2) Regime labels driven by the closest-to-violation (dominant) constraint
   enriched via the SHAMS constraint taxonomy.
3) Reviewer-ready artifacts: regime summary table, cluster stats, and
   narrative paragraphs.

Design rules
------------
- Additive only: does not modify evaluator truth or any feasibility.
- Deterministic: no hidden randomness; stable ordering.
- Solver-free: clustering uses quantized bin keys + deterministic merging.
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import math
import time


def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _is_num(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def _safe_float(x: Any, default: float = float("nan")) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def _pick_first(d: Dict[str, Any], keys: Sequence[str]) -> Optional[str]:
    for k in keys:
        if k in d and _is_num(d.get(k)):
            return k
    return None


def select_default_features(records: Sequence[Dict[str, Any]], *, max_features: int = 6) -> List[str]:
    """Choose a stable, informative set of numeric features for clustering.

    Strategy:
    - Prefer canonical tokamak/system descriptors if present.
    - Fall back to any numeric columns with non-trivial variance.
    """
    if not records:
        return []

    # Canonical priority list (best-effort; only those present will be used).
    preferred = [
        # geometry / field / current
        "R0_m",
        "a_m",
        "kappa",
        "delta",
        "B0_T",
        "Ip_MA",
        # performance
        "P_fusion_MW",
        "P_e_net_MW",
        "Q_plasma",
        "Q",
        # exhaust / loads
        "q_div_MW_m2",
        "q_div_MWm2",
        "W_wall_MW_m2",
        "W_wall_MWm2",
        "beta_N",
        "q95",
    ]

    present = []
    seen = set()
    for k in preferred:
        if k in seen:
            continue
        if any((_is_num(r.get(k)) for r in records)):
            present.append(k)
            seen.add(k)
        if len(present) >= max_features:
            return present

    # Fallback: any numeric keys with variance.
    # Build candidate set from first N rows to bound cost.
    cand: List[str] = []
    for r in records[:80]:
        if not isinstance(r, dict):
            continue
        for k, v in r.items():
            if isinstance(k, str) and k not in seen and _is_num(v):
                cand.append(k)
                seen.add(k)

    # Keep those with non-trivial spread.
    scored: List[Tuple[float, str]] = []
    for k in cand:
        vals = [_safe_float(r.get(k)) for r in records if _is_num(r.get(k))]
        if len(vals) < 8:
            continue
        lo, hi = min(vals), max(vals)
        spread = float(hi - lo)
        if spread <= 0.0:
            continue
        scored.append((spread, k))

    scored.sort(reverse=True)
    for _, k in scored:
        present.append(k)
        if len(present) >= max_features:
            break

    return present


@dataclass(frozen=True)
class _Binner:
    lo: float
    hi: float
    step: float
    n_bins: int

    def bin_index(self, x: float) -> int:
        if not math.isfinite(x):
            return -1
        if self.step <= 0:
            return 0
        v = max(self.lo, min(self.hi, x))
        i = int(math.floor((v - self.lo) / self.step))
        return max(0, min(self.n_bins - 1, i))


def _build_binner(vals: List[float], *, max_bins: int = 12) -> _Binner:
    vals = [v for v in vals if math.isfinite(v)]
    if not vals:
        return _Binner(0.0, 1.0, 1.0, 1)
    lo = min(vals)
    hi = max(vals)
    if hi - lo < 1e-12:
        return _Binner(lo, lo + 1e-12, 1e-12, 1)
    # Robust-ish step: range / max_bins
    step = (hi - lo) / float(max_bins)
    step = max(step, 1e-12)
    return _Binner(lo, hi, step, max_bins)


def _vector_distance(a: Sequence[float], b: Sequence[float]) -> float:
    # L1 on finite entries, deterministic
    s = 0.0
    for x, y in zip(a, b):
        if math.isfinite(x) and math.isfinite(y):
            s += abs(x - y)
        else:
            s += 1e6
    return s


def _centroid(rows: Sequence[Dict[str, Any]], feats: Sequence[str]) -> List[float]:
    out: List[float] = []
    for k in feats:
        vs = [_safe_float(r.get(k)) for r in rows if _is_num(r.get(k))]
        if vs:
            out.append(sum(vs) / float(len(vs)))
        else:
            out.append(float("nan"))
    return out


def _stable_sort_keys(keys: Iterable[str]) -> List[str]:
    return sorted([str(k) for k in keys])


def _label_from_mechanism_group(mg: str) -> str:
    mg = str(mg).upper().strip()
    if mg in ("PLASMA", "EXHAUST", "MAGNETS", "NEUTRONICS", "COST", "CONTROL"):
        return f"{mg}-limited"
    return "GENERAL-limited"


def build_regime_maps_report(
    *,
    records: Sequence[Dict[str, Any]],
    features: Optional[Sequence[str]] = None,
    min_cluster_size: int = 6,
    max_bins: int = 12,
) -> Dict[str, Any]:
    """Build the v324 regime maps report.

    Inputs
    ------
    records:
        A list of Trade Study rows, each containing at minimum:
        - is_feasible: bool
        - min_margin_frac: float
        - dominant_constraint: str (best-effort)

    Returns
    -------
    A deterministic, audit-ready dict.
    """

    created = _created_utc()
    feats = list(features) if features is not None else select_default_features(records)
    feats = [f for f in feats if isinstance(f, str)]

    feas = [r for r in (records or []) if isinstance(r, dict) and bool(r.get("is_feasible"))]
    if not feas:
        return {
            "kind": "shams_regime_maps_report",
            "version": "v324",
            "created_utc": created,
            "error": "No feasible records provided.",
            "n_records": int(len(records or [])),
            "n_feasible": 0,
            "features": feats,
        }

    # Build per-feature binners on feasible rows.
    binners: Dict[str, _Binner] = {}
    for k in feats:
        vals = [_safe_float(r.get(k)) for r in feas if _is_num(r.get(k))]
        binners[k] = _build_binner(vals, max_bins=int(max_bins))

    # Initial bin-key clusters
    clusters: Dict[Tuple[int, ...], List[Dict[str, Any]]] = {}
    for r in feas:
        key = tuple(binners[k].bin_index(_safe_float(r.get(k))) for k in feats)
        clusters.setdefault(key, []).append(r)

    # Deterministic merge of tiny clusters into nearest centroid cluster.
    # Build centroid map first.
    centroids: Dict[Tuple[int, ...], List[float]] = {k: _centroid(v, feats) for k, v in clusters.items()}

    # Identify large clusters.
    big_keys = [k for k, v in clusters.items() if len(v) >= int(min_cluster_size)]
    if not big_keys:
        # If everything is tiny, just take the largest as an anchor.
        big_keys = [max(clusters.items(), key=lambda kv: len(kv[1]))[0]]

    # Above string hack is unnecessary; do deterministic order directly.
    keys_sorted = sorted(clusters.keys(), key=lambda kk: (len(clusters[kk]), str(kk)))
    for kk in keys_sorted:
        if kk in big_keys:
            continue
        rows = clusters.get(kk, [])
        if not rows:
            continue
        c = centroids.get(kk) or _centroid(rows, feats)
        # Find nearest big cluster
        best = None
        best_d = None
        for bk in big_keys:
            d = _vector_distance(c, centroids.get(bk) or _centroid(clusters[bk], feats))
            if best_d is None or d < best_d:
                best_d = d
                best = bk
        if best is None:
            continue
        clusters[best].extend(rows)
        clusters[kk] = []

    # Prune empty clusters
    clusters = {k: v for k, v in clusters.items() if v}

    # Regime labeling via constraint taxonomy.
    from constraints.taxonomy import enrich_constraint_meta

    cluster_items: List[Dict[str, Any]] = []
    for idx, (k, rows) in enumerate(sorted(clusters.items(), key=lambda kv: (-len(kv[1]), str(kv[0])))):
        # Determine representative dominant constraint + mechanism group
        dom_counts: Dict[str, int] = {}
        mg_counts: Dict[str, int] = {}
        for r in rows:
            dc = str(r.get("dominant_constraint") or "")
            dom_counts[dc] = dom_counts.get(dc, 0) + 1
            meta = enrich_constraint_meta(dc)
            mg = str(meta.get("mechanism_group", "GENERAL"))
            mg_counts[mg] = mg_counts.get(mg, 0) + 1

        dominant_constraint = max(dom_counts.items(), key=lambda kv: (kv[1], kv[0]))[0] if dom_counts else ""
        dominant_mg = max(mg_counts.items(), key=lambda kv: (kv[1], kv[0]))[0] if mg_counts else "GENERAL"
        meta = enrich_constraint_meta(dominant_constraint)
        regime_label = _label_from_mechanism_group(dominant_mg)

        # Stats
        feat_stats: Dict[str, Dict[str, float]] = {}
        for fk in feats:
            vs = sorted([_safe_float(r.get(fk)) for r in rows if _is_num(r.get(fk))])
            if not vs:
                continue
            mid = vs[len(vs) // 2]
            feat_stats[fk] = {
                "min": float(vs[0]),
                "median": float(mid),
                "max": float(vs[-1]),
            }

        margins = sorted([_safe_float(r.get("min_margin_frac")) for r in rows if _is_num(r.get("min_margin_frac"))])
        mmin = float(margins[0]) if margins else float("nan")
        mmed = float(margins[len(margins) // 2]) if margins else float("nan")

        narrative = (
            f"Family #{idx} contains {len(rows)} feasible designs. "
            f"Closest-to-violation screen is typically `{dominant_constraint}` "
            f"→ mechanism group **{dominant_mg}** ({regime_label}). "
            f"Median hard-margin fraction ≈ {mmed:.3g} (min ≈ {mmin:.3g})."
        )

        cluster_items.append(
            {
                "cluster_id": int(idx),
                "n": int(len(rows)),
                "regime_label": regime_label,
                "dominant_mechanism_group": dominant_mg,
                "dominant_constraint": dominant_constraint,
                "authority": {
                    "subsystem": meta.get("subsystem"),
                    "authority_tier": meta.get("authority_tier"),
                    "validity_domain": meta.get("validity_domain"),
                },
                "margin": {"min_margin_frac": mmin, "median_margin_frac": mmed},
                "feature_stats": feat_stats,
                "narrative": narrative,
                "member_indices": [int(r.get("i")) for r in rows if isinstance(r.get("i"), int)],
            }
        )

    # Per-point assignment (index in original feasible list is not stable; use the record's own i if present)
    assignments: List[Dict[str, Any]] = []
    # Build a lookup by id (i) if present, else by object identity
    id_to_cluster: Dict[int, int] = {}
    for c in cluster_items:
        cid = int(c["cluster_id"])
        for ii in c.get("member_indices", []) or []:
            if isinstance(ii, int):
                id_to_cluster[ii] = cid
    for r in feas:
        rid = r.get("i")
        cid = id_to_cluster.get(rid) if isinstance(rid, int) else None
        assignments.append(
            {
                "i": int(rid) if isinstance(rid, int) else None,
                "cluster_id": cid,
                "regime_label": (cluster_items[cid]["regime_label"] if (cid is not None and 0 <= cid < len(cluster_items)) else None),
                "min_margin_frac": _safe_float(r.get("min_margin_frac")),
            }
        )

    return {
        "kind": "shams_regime_maps_report",
        "version": "v324",
        "created_utc": created,
        "n_records": int(len(records or [])),
        "n_feasible": int(len(feas)),
        "features": feats,
        "clustering": {
            "min_cluster_size": int(min_cluster_size),
            "max_bins": int(max_bins),
            "n_clusters": int(len(cluster_items)),
        },
        "clusters": cluster_items,
        "assignments": assignments,
    }
