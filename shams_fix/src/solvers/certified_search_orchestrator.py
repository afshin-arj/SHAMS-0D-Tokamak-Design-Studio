"""Certified Search Orchestrator 2.0 (v340.0).

This module provides a deterministic, budgeted exploration orchestrator that
operates strictly **outside** the frozen evaluator. It is not an internal
optimizer.

Design laws:
- No mutation of truth models.
- No solvers inside truth.
- Deterministic generation of candidate points.
- Full trace logging suitable for evidence packs.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, replace
from typing import Any, Callable, Dict, List, Optional, Tuple
import hashlib
import json

from solvers.budgeted_search import SearchResult, SearchSpec, SearchVar, run_budgeted_search

from extopt.surrogate_accel import propose_candidates


@dataclass(frozen=True)
class SearchStage:
    """One stage in an orchestrated certified search."""

    name: str
    method: str = "halton"  # lhs | grid | halton | surrogate
    budget: int = 64
    seed: int = 0
    local_refine: bool = False
    local_shrink: float = 0.35  # fraction of original range width to keep

    # surrogate-stage controls (v341.0)
    surrogate_pool_mult: int = 50  # candidate pool multiplier vs stage budget
    surrogate_kappa: float = 0.5
    surrogate_ridge_alpha: float = 1e-3
    surrogate_feas_margin_key: str = "min_margin_frac"


@dataclass(frozen=True)
class OrchestratorSpec:
    variables: Tuple[SearchVar, ...]
    stages: Tuple[SearchStage, ...]


def _clamp(x: float, lo: float, hi: float) -> float:
    return float(min(max(float(x), float(lo)), float(hi)))


def _local_bounds(
    base_vars: List[SearchVar],
    best_x: Dict[str, float],
    shrink: float,
) -> List[SearchVar]:
    """Build local-refinement bounds around best_x."""
    out: List[SearchVar] = []
    s = float(max(0.05, min(0.95, shrink)))
    for v in base_vars:
        w = float(v.hi - v.lo)
        c = float(best_x.get(v.name, (v.lo + v.hi) * 0.5))
        half = 0.5 * s * w
        lo = _clamp(c - half, v.lo, v.hi)
        hi = _clamp(c + half, v.lo, v.hi)
        if hi <= lo:
            hi = lo + 1e-12
        out.append(SearchVar(name=v.name, lo=float(lo), hi=float(hi)))
    return out


def run_orchestrated_certified_search(
    base_inputs: Any,
    spec: OrchestratorSpec,
    verifier: Callable[[Any], Tuple[str, float, Dict[str, Any]]],
    builder: Callable[[Any, Dict[str, float]], Any],
) -> Dict[str, Any]:
    """Run a multi-stage certified search and return an evidence artifact (v2).

    Returns a dict suitable for storage in the DSG chronicle and for evidence packs.
    """

    base_vars = list(spec.variables)
    stage_results: List[SearchResult] = []
    best_record_x: Optional[Dict[str, float]] = None
    best_score: Optional[float] = None
    best_stage: Optional[str] = None

    for stage in spec.stages:
        stage_vars = base_vars
        if stage.local_refine and best_record_x is not None:
            stage_vars = _local_bounds(base_vars, best_record_x, shrink=float(stage.local_shrink))
        if str(stage.method) == "surrogate":
            # v341.0: feasible-first surrogate acceleration (non-authoritative).
            # Train on accumulated prior records and propose new candidates deterministically.
            prior_records = []
            for prev in stage_results:
                for r in prev.records:
                    row = dict(r.x)
                    row["score"] = float(r.score)
                    ev = dict(r.evidence or {})
                    # Feasibility proxy from constraint bookkeeping if available
                    mm = ev.get(str(stage.surrogate_feas_margin_key))
                    if mm is None:
                        mm = ev.get("worst_hard_margin_frac")
                    try:
                        row[str(stage.surrogate_feas_margin_key)] = float(mm) if mm is not None else float("nan")
                    except Exception:
                        row[str(stage.surrogate_feas_margin_key)] = float("nan")
                    row["is_feasible"] = bool(str(r.verdict) == "PASS")
                    prior_records.append(row)

            bounds = {v.name: (float(v.lo), float(v.hi)) for v in stage_vars}
            n_pool = int(max(64, int(stage.budget) * int(stage.surrogate_pool_mult)))
            try:
                if len(prior_records) < 16:
                    raise ValueError("insufficient prior records")
                proposals = propose_candidates(
                    records=prior_records,
                    bounds=bounds,
                    objective_key="score",
                    objective_sense="max",
                    feasibility_margin_key=str(stage.surrogate_feas_margin_key),
                    n_pool=n_pool,
                    n_propose=int(stage.budget),
                    seed=int(stage.seed),
                    kappa=float(stage.surrogate_kappa),
                    ridge_alpha=float(stage.surrogate_ridge_alpha),
                )
            except Exception:
                # deterministic fallback
                proposals = []

            # If surrogate could not propose candidates, deterministically fall back to Halton.
            if not proposals:
                sr = run_budgeted_search(
                    base_inputs,
                    SearchSpec(
                        variables=tuple(stage_vars),
                        budget=int(stage.budget),
                        seed=int(stage.seed),
                        method="halton",
                    ),
                    verifier=verifier,
                    builder=builder,
                )
                stage_results.append(sr)
                if sr.best_record is not None:
                    if best_score is None or float(sr.best_record.score) > float(best_score):
                        best_score = float(sr.best_record.score)
                        best_record_x = dict(sr.best_record.x)
                        best_stage = str(stage.name)
                continue

            # Verify proposals; build SearchResult-like record set.
            from solvers.budgeted_search import SearchRecord
            recs = []
            best_i = None
            best_rec = None
            for i, x in enumerate(proposals):
                cand = builder(base_inputs, {k: float(v) for k, v in x.items()})
                verdict, score, evidence = verifier(cand)
                rec = SearchRecord(i=i, x=dict(x), verdict=str(verdict), score=float(score), evidence=dict(evidence))
                recs.append(rec)
                if rec.verdict == "PASS":
                    if best_rec is None or rec.score > best_rec.score:
                        best_rec = rec
                        best_i = i

            # digest compatible with SearchResult
            payload = {
                "spec": {
                    "variables": [v.__dict__ for v in stage_vars],
                    "budget": int(stage.budget),
                    "seed": int(stage.seed),
                    "method": str(stage.method),
                },
                "best_index": best_i,
                "records": [{"i": r.i, "x": r.x, "verdict": r.verdict, "score": r.score} for r in recs],
            }
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            digest = hashlib.sha256(raw).hexdigest()
            sr = SearchResult(
                spec=SearchSpec(variables=tuple(stage_vars), budget=int(stage.budget), seed=int(stage.seed), method=str(stage.method)),
                records=tuple(recs),
                best_index=best_i,
                best_record=best_rec,
                digest=digest,
            )
        else:
            sr = run_budgeted_search(
                base_inputs,
                SearchSpec(
                    variables=tuple(stage_vars),
                    budget=int(stage.budget),
                    seed=int(stage.seed),
                    method=str(stage.method),
                ),
                verifier=verifier,
                builder=builder,
            )
        stage_results.append(sr)
        if sr.best_record is not None:
            if best_score is None or float(sr.best_record.score) > float(best_score):
                best_score = float(sr.best_record.score)
                best_record_x = dict(sr.best_record.x)
                best_stage = str(stage.name)

    artifact = {
        "schema_version": "certified_search_orchestrator_evidence.v2",
        "spec": {
            "variables": [asdict(v) for v in spec.variables],
            "stages": [asdict(s) for s in spec.stages],
        },
        "best": {
            "stage": best_stage,
            "score": best_score,
            "x": best_record_x,
        },
        "stages": [
            {
                "name": str(spec.stages[i].name),
                "digest": str(sr.digest),
                "method": str(sr.spec.method),
                "budget": int(sr.spec.budget),
                "seed": int(sr.spec.seed),
                "records": [
                    {
                        "i": int(r.i),
                        "x": dict(r.x),
                        "verdict": str(r.verdict),
                        "score": float(r.score),
                        "evidence": dict(r.evidence or {}),
                    }
                    for r in sr.records
                ],
                "best_index": (int(sr.best_index) if sr.best_index is not None else None),
            }
            for i, sr in enumerate(stage_results)
        ],
    }

    # deterministic orchestrator digest
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
    artifact["digest"] = hashlib.sha256(raw).hexdigest()
    return artifact
