"""Certified Search Orchestrator 3.0 (v405.0.0).

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

from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, List, Optional, Tuple
import hashlib
import json

from shams_io.run_artifact import build_run_artifact

from uq_contracts.runner import run_uncertainty_contract_for_point
from uq_contracts.spec import optimistic_uncertainty_contract, robust_uncertainty_contract

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
    """Run a multi-stage certified search and return an evidence artifact (v3).

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
        "schema_version": "certified_search_orchestrator_evidence.v3",
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


@dataclass(frozen=True)
class ParetoObjective:
    """One objective with an explicit sense."""

    key: str
    sense: str = "min"  # "min" | "max"

    def normalized_sense(self) -> str:
        s = str(self.sense or "min").strip().lower()
        return "max" if s == "max" else "min"


def _isfinite(x: Any) -> bool:
    try:
        import math

        return math.isfinite(float(x))
    except Exception:
        return False


def _pareto_dominates(a: Dict[str, float], b: Dict[str, float], objectives: List[ParetoObjective]) -> bool:
    better_or_equal = True
    strictly_better = False
    for o in objectives:
        k = str(o.key)
        va = float(a.get(k, float("nan")))
        vb = float(b.get(k, float("nan")))
        if not (_isfinite(va) and _isfinite(vb)):
            return False
        if o.normalized_sense() == "min":
            if va > vb:
                better_or_equal = False
            elif va < vb:
                strictly_better = True
        else:
            if va < vb:
                better_or_equal = False
            elif va > vb:
                strictly_better = True
    return bool(better_or_equal and strictly_better)


def _pareto_front(rows: List[Dict[str, Any]], objectives: List[ParetoObjective]) -> List[Dict[str, Any]]:
    pts: List[Tuple[Dict[str, Any], Dict[str, float]]] = []
    for r in rows:
        p: Dict[str, float] = {}
        ok = True
        for o in objectives:
            v = r.get(o.key, float("nan"))
            try:
                p[str(o.key)] = float(v)
            except Exception:
                ok = False
                break
            if not _isfinite(p[str(o.key)]):
                ok = False
                break
        if ok:
            pts.append((r, p))

    front: List[Dict[str, Any]] = []
    for i, (ri, pi) in enumerate(pts):
        dominated = False
        for j, (rj, pj) in enumerate(pts):
            if i == j:
                continue
            if _pareto_dominates(pj, pi, objectives):
                dominated = True
                break
        if not dominated:
            front.append(ri)
    return front


def run_orchestrated_certified_pareto_search(
    *,
    base_inputs: Any,
    spec: OrchestratorSpec,
    objectives: List[ParetoObjective],
    builder: Callable[[Any, Dict[str, float]], Any],
    evaluator_fn: Callable[[Any], Dict[str, Any]],
    constraints_fn: Callable[[Dict[str, Any], Any], List[Dict[str, Any]]],
    max_frontier: int = 40,
    filter_mirage: bool = True,
) -> Dict[str, Any]:
    """Certified Search Orchestrator 3.0.

    Produces a deterministic multi-stage candidate set, then extracts a feasible-first
    Pareto frontier under user-declared objectives.

    Lanes:
      - optimistic lane: optimistic_uncertainty_contract
      - robust lane:     robust_uncertainty_contract

    This function is *not* an optimizer; it is a budgeted exploration orchestrator.
    """

    if not objectives:
        raise ValueError("objectives must be non-empty")

    # ---- Stage exploration (reuse v3 artifact layout) ----
    # Verifier uses nominal feasibility; score is not used for Pareto (kept for compatibility).
    def _verifier(inp_obj: Any) -> Tuple[str, float, Dict[str, Any]]:
        out = evaluator_fn(inp_obj)
        cons = constraints_fn(out, inp_obj)
        ok = all((not bool(c.get("failed"))) for c in (cons or []))
        ev = {
            "n_failed": int(sum(1 for c in (cons or []) if c.get("failed"))),
            "top_blocker": (next((c.get("name") for c in (cons or []) if c.get("failed")), None)),
        }
        # Compatibility score: prefer PASS, then higher global margin.
        gm = out.get("global_min_margin_v402", float("nan"))
        try:
            ev["global_min_margin_v402"] = float(gm)
        except Exception:
            ev["global_min_margin_v402"] = float("nan")
        score = float(ev["global_min_margin_v402"]) if ok else float("-inf")
        return ("PASS" if ok else "FAIL"), score, ev

    base_art = run_orchestrated_certified_search(
        base_inputs,
        spec,
        verifier=_verifier,
        builder=builder,
    )

    # ---- Flatten candidate records ----
    all_rows: List[Dict[str, Any]] = []
    for stg in (base_art.get("stages") or []):
        for r in (stg.get("records") or []):
            if not isinstance(r, dict):
                continue
            row = {
                "stage": str(stg.get("name", "")),
                "i": int(r.get("i", 0)),
                "verdict": str(r.get("verdict", "")),
                **(r.get("x") or {}),
            }
            # Inject objective columns if present in evidence later
            all_rows.append(row)

    # Evaluate objective values deterministically for each candidate
    enriched: List[Dict[str, Any]] = []
    for row in all_rows:
        x = {k: float(v) for k, v in row.items() if k not in {"stage", "i", "verdict"} and isinstance(v, (int, float))}
        inp_obj = builder(base_inputs, x)
        out = evaluator_fn(inp_obj)
        cons = constraints_fn(out, inp_obj)
        ok = all((not bool(c.get("failed"))) for c in (cons or []))
        rr = dict(row)
        rr["is_feasible"] = bool(ok)
        rr["global_dominant_authority_v402"] = str(out.get("global_dominant_authority_v402", ""))
        try:
            rr["global_min_margin_v402"] = float(out.get("global_min_margin_v402", float("nan")))
        except Exception:
            rr["global_min_margin_v402"] = float("nan")
        rr["mirage_flag_v402"] = bool(out.get("mirage_flag_v402", False))
        for o in objectives:
            rr[str(o.key)] = out.get(str(o.key), float("nan"))
        # Keep a compact, UI-friendly blocker summary
        rr["n_failed"] = int(sum(1 for c in (cons or []) if c.get("failed")))
        rr["top_blocker"] = next((c.get("name") for c in (cons or []) if c.get("failed")), "")
        enriched.append(rr)

    feas = [r for r in enriched if bool(r.get("is_feasible", False))]
    frontier = _pareto_front(feas, objectives)

    # Deterministic lane evaluation for frontier points (budgeted)
    candidates: List[Dict[str, Any]] = []
    max_frontier = max(1, int(max_frontier))

    def _cid(r: Dict[str, Any]) -> str:
        payload = {"x": {k: r.get(k) for k in sorted(r.keys()) if k not in {"stage", "i", "verdict"}}}
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    for r in frontier[:max_frontier]:
        x = {k: float(v) for k, v in r.items() if k not in {"stage", "i", "verdict"} and isinstance(v, (int, float))}
        inp_obj = builder(base_inputs, x)
        out = evaluator_fn(inp_obj)
        cons = constraints_fn(out, inp_obj)

        # Build canonical run artifact (nominal)
        run_art = build_run_artifact(
            inputs=dict(getattr(inp_obj, "__dict__", {}) or {}),
            outputs=dict(out or {}),
            constraints=list(cons or []),
            meta={"mode": "certified_search_orchestrator", "label": f"v405:{_cid(r)}"},
            solver={"message": "certified_search_orchestrator_v405"},
            economics=dict((out or {}).get("_economics", {})) if isinstance(out, dict) else {},
        )

        opt_spec = optimistic_uncertainty_contract(inp_obj)
        rob_spec = robust_uncertainty_contract(inp_obj)
        try:
            lane_opt = run_uncertainty_contract_for_point(inp_obj, opt_spec, label_prefix="laneO")
        except Exception:
            lane_opt = None
        try:
            lane_rob = run_uncertainty_contract_for_point(inp_obj, rob_spec, label_prefix="laneR")
        except Exception:
            lane_rob = None

        def _verdict(uq: Any) -> str:
            if not isinstance(uq, dict):
                return ""
            s = uq.get("summary") or {}
            return str((s or {}).get("verdict", ""))

        opt_v = _verdict(lane_opt)
        rob_v = _verdict(lane_rob)
        is_mirage = bool(opt_v == "ROBUST_PASS" and rob_v != "ROBUST_PASS")

        if filter_mirage and is_mirage:
            continue

        candidates.append(
            {
                "id": _cid(r),
                "x": x,
                "objectives": {str(o.key): float(r.get(str(o.key), float("nan"))) for o in objectives},
                "global_min_margin_v402": float(r.get("global_min_margin_v402", float("nan"))),
                "global_dominant_authority_v402": str(r.get("global_dominant_authority_v402", "")),
                "mirage_flag_v402": bool(r.get("mirage_flag_v402", False)),
                "lane_optimistic_verdict": str(opt_v),
                "lane_robust_verdict": str(rob_v),
                "is_mirage_lane": bool(is_mirage),
                "run_artifact": run_art,
                "lane_optimistic": lane_opt,
                "lane_robust": lane_rob,
            }
        )

    # Add v405 metadata on top of base_art (preserving v3 schema)
    base_art.setdefault("v405", {})
    base_art["v405"] = {
        "objectives": [asdict(o) for o in objectives],
        "max_frontier": int(max_frontier),
        "filter_mirage": bool(filter_mirage),
    }
    base_art["candidates"] = candidates

    raw = json.dumps(base_art, sort_keys=True, separators=(",", ":")).encode("utf-8")
    base_art["digest"] = hashlib.sha256(raw).hexdigest()
    return base_art
