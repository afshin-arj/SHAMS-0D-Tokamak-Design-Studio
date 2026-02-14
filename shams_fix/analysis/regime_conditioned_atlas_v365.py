"""SHAMS v365.0 — Regime-Conditioned Pareto Atlas 2.0

Build a Pareto atlas conditioned by regime and governance classes.

This is a *post-processing* module: it consumes previously-evaluated candidate
records and produces deterministic atlas artifacts.

Core laws satisfied
-------------------
1. Frozen truth: does not modify evaluator outputs
2. Separation of concerns: pure interpretation/governance layer
3. Feasibility-first: Pareto sets are extracted within chosen feasibility class
4. Audit safety: stable JSON serialization + content fingerprinting

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


Json = Dict[str, Any]


def _stable_json_dumps(obj: Any) -> str:
    """Stable, audit-friendly JSON."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def fingerprint_json(obj: Any) -> str:
    """SHA-256 fingerprint of stable JSON encoding."""
    h = hashlib.sha256()
    h.update(_stable_json_dumps(obj).encode("utf-8"))
    return h.hexdigest()


@dataclass(frozen=True)
class MetricSpec:
    key: str
    direction: str  # "min" or "max"

    def __post_init__(self) -> None:
        if self.direction not in ("min", "max"):
            raise ValueError(f"MetricSpec.direction must be 'min' or 'max', got {self.direction!r}")


@dataclass(frozen=True)
class AtlasConfig:
    conditioning_axes: Tuple[str, ...]
    min_bucket_size: int
    feasibility_gate: str  # "any_feasible", "optimistic", "robust", "robust_only"
    metrics: Tuple[MetricSpec, ...]

    def __post_init__(self) -> None:
        if self.min_bucket_size < 1:
            raise ValueError("min_bucket_size must be >= 1")
        if self.feasibility_gate not in ("any_feasible", "optimistic", "robust", "robust_only"):
            raise ValueError("Invalid feasibility_gate")


def extract_labels(rec: Mapping[str, Any]) -> Json:
    """Extract regime / governance labels from a record.

    Expected (best-effort) keys:
      - plasma_regime
      - exhaust_regime
      - magnet_regime
      - dominance_label (or dominance)
      - optimistic_feasible / robust_feasible (v362)
    """
    dom = rec.get("dominance_label") or rec.get("dominance") or rec.get("dominant") or "UNKNOWN"
    plasma = rec.get("plasma_regime") or rec.get("regime_plasma") or "UNKNOWN"
    exhaust = rec.get("exhaust_regime") or rec.get("regime_exhaust") or "UNKNOWN"
    magnet = rec.get("magnet_regime") or rec.get("regime_magnet") or "UNKNOWN"

    opt = bool(rec.get("optimistic_feasible")) if "optimistic_feasible" in rec else None
    rob = bool(rec.get("robust_feasible")) if "robust_feasible" in rec else None

    # Robustness class
    if opt is True and rob is True:
        rclass = "ROBUST"
    elif opt is True and rob is False:
        rclass = "MIRAGE"
    elif opt is False and rob is False:
        rclass = "INFEASIBLE"
    else:
        rclass = "UNKNOWN"

    return {
        "plasma_regime": str(plasma),
        "exhaust_regime": str(exhaust),
        "magnet_regime": str(magnet),
        "dominance_label": str(dom),
        "robustness_class": rclass,
        "optimistic_feasible": opt,
        "robust_feasible": rob,
    }


def _is_feasible(rec: Mapping[str, Any], gate: str) -> bool:
    # Try v362 flags first
    opt = rec.get("optimistic_feasible")
    rob = rec.get("robust_feasible")

    # Fallback: common single-shot verdict fields
    verdict = rec.get("feasible")
    if verdict is None:
        verdict = rec.get("verdict")
    if isinstance(verdict, str):
        verdict_bool = verdict.lower() in ("feasible", "true", "yes", "pass")
    else:
        verdict_bool = bool(verdict) if verdict is not None else False

    if gate == "any_feasible":
        if opt is None and rob is None:
            return verdict_bool
        return bool(opt) or bool(rob)
    if gate == "optimistic":
        return bool(opt) if opt is not None else verdict_bool
    if gate == "robust":
        return bool(rob) if rob is not None else verdict_bool
    if gate == "robust_only":
        return bool(rob) is True
    raise ValueError("invalid gate")


def _get_metric_value(rec: Mapping[str, Any], key: str) -> Optional[float]:
    """Best-effort metric retrieval.

    Supports either flat keys, or nested outputs dicts.
    """
    if key in rec and rec[key] is not None:
        try:
            return float(rec[key])
        except Exception:
            return None
    for out_key in ("outputs", "metrics", "report", "summary"):
        if isinstance(rec.get(out_key), Mapping):
            m = rec[out_key]
            if key in m and m[key] is not None:
                try:
                    return float(m[key])
                except Exception:
                    return None
    return None


def pareto_mask(values: List[List[float]], dirs: List[str]) -> List[bool]:
    """Return mask of non-dominated points.

    values: N x M list. dirs: M list of "min" or "max".
    """
    n = len(values)
    m = len(dirs)
    keep = [True] * n
    for i in range(n):
        if not keep[i]:
            continue
        vi = values[i]
        for j in range(n):
            if i == j or not keep[i]:
                continue
            vj = values[j]
            # j dominates i if no worse in all metrics and better in at least one
            no_worse = True
            strictly_better = False
            for k in range(m):
                if dirs[k] == "min":
                    if vj[k] > vi[k]:
                        no_worse = False
                        break
                    if vj[k] < vi[k]:
                        strictly_better = True
                else:  # max
                    if vj[k] < vi[k]:
                        no_worse = False
                        break
                    if vj[k] > vi[k]:
                        strictly_better = True
            if no_worse and strictly_better:
                keep[i] = False
    return keep


def bucket_key(labels: Mapping[str, Any], axes: Sequence[str]) -> Tuple[str, ...]:
    return tuple(str(labels.get(ax, "UNKNOWN")) for ax in axes)


def build_regime_conditioned_atlas(
    records: Iterable[Mapping[str, Any]],
    config: AtlasConfig,
) -> Json:
    """Build atlas buckets and Pareto sets.

    Returns a JSON-serializable dictionary with:
      - config
      - fingerprint
      - buckets: list with counts
      - pareto_sets: list per bucket
    """
    rec_list: List[Json] = []
    for r in records:
        rr: Json = dict(r)
        labels = extract_labels(rr)
        rr["_labels"] = labels
        rr["_feasible_gate"] = _is_feasible(labels | rr, config.feasibility_gate)  # type: ignore
        rec_list.append(rr)

    # Bucket
    buckets: Dict[Tuple[str, ...], List[Json]] = {}
    for rr in rec_list:
        key = bucket_key(rr["_labels"], config.conditioning_axes)
        buckets.setdefault(key, []).append(rr)

    # Prepare outputs
    bucket_rows: List[Json] = []
    pareto_rows: List[Json] = []
    dirs = [ms.direction for ms in config.metrics]

    for key, rs in sorted(buckets.items(), key=lambda kv: kv[0]):
        n_total = len(rs)
        n_feas = sum(1 for rr in rs if rr.get("_feasible_gate"))
        if n_total < config.min_bucket_size:
            continue
        bucket_rows.append({
            "bucket": key,
            "count_total": n_total,
            "count_feasible": n_feas,
        })

        # Pareto over feasible subset
        feas_rs = [rr for rr in rs if rr.get("_feasible_gate")]
        if not feas_rs:
            continue

        # Build metric matrix, drop rows with missing metrics
        vals: List[List[float]] = []
        kept: List[Json] = []
        for rr in feas_rs:
            row: List[float] = []
            ok = True
            for ms in config.metrics:
                v = _get_metric_value(rr, ms.key)
                if v is None:
                    ok = False
                    break
                row.append(v)
            if ok:
                vals.append(row)
                kept.append(rr)
        if not kept:
            continue
        mask = pareto_mask(vals, dirs)
        for rr, vv, mk in zip(kept, vals, mask):
            if not mk:
                continue
            pareto_rows.append({
                "bucket": key,
                "candidate_id": rr.get("candidate_id") or rr.get("id") or rr.get("uuid") or None,
                "dominance_label": rr["_labels"].get("dominance_label"),
                "robustness_class": rr["_labels"].get("robustness_class"),
                "metrics": {ms.key: vv[i] for i, ms in enumerate(config.metrics)},
            })

    out: Json = {
        "schema": "shams_regime_conditioned_atlas.v365",
        "config": {
            "conditioning_axes": list(config.conditioning_axes),
            "min_bucket_size": config.min_bucket_size,
            "feasibility_gate": config.feasibility_gate,
            "metrics": [{"key": ms.key, "direction": ms.direction} for ms in config.metrics],
        },
        "buckets": bucket_rows,
        "pareto_sets": pareto_rows,
    }
    out["fingerprint_sha256"] = fingerprint_json(out)
    return out
