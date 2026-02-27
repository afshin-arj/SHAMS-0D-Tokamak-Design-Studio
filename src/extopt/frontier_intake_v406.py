from __future__ import annotations

"""External Optimizer Interpretation Layer — Frontier Intake (v406).

Purpose
-------
Deterministically ingest external optimizer outputs (CSV/JSON candidate sets),
re-evaluate each candidate through frozen truth, apply governance overlays:

  - feasibility-first summaries (hard constraints)
  - optimistic vs robust lane evaluation (UQ-lite interval corners)
  - mirage detection (optimistic pass, robust fail)
  - feasible-only Pareto front reconstruction (purely algebraic filtering)

Design laws (hard):
  - No truth mutation.
  - No optimization.
  - Deterministic ordering, hashing, and outputs.
  - Explicit schema versioning.

Author: © 2026 Afshin Arjhangmehr
"""

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:  # pragma: no cover
    from models.inputs import PointInputs  # type: ignore

from .batch import BatchEvalConfig, evaluate_concept_family
from .family import ConceptFamily, ConceptCandidate
from ..uq_contracts.spec import UncertaintyContractSpec
from ..uq_contracts.runner import run_uncertainty_contract_for_point


# -------------------------
# Small utilities
# -------------------------

def _stable_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def _as_float(v: Any) -> Optional[float]:
    try:
        x = float(v)
        # NaN/inf considered invalid
        import math
        if not math.isfinite(x):
            return None
        return x
    except Exception:
        return None

def _as_str(v: Any) -> str:
    return "" if v is None else str(v)

def _sorted_dict(d: Mapping[str, Any]) -> Dict[str, Any]:
    return {k: d[k] for k in sorted(d.keys())}

def _read_version(repo_root: Path) -> str:
    for name in ("VERSION", "VERSION.txt"):
        p = repo_root / name
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    return "unknown"


# -------------------------
# Candidate set parsing
# -------------------------

@dataclass(frozen=True)
class CandidateSet:
    schema_version: str
    candidates: List[Dict[str, Any]]
    meta: Dict[str, Any]

def parse_candidate_set_json(data: Mapping[str, Any]) -> CandidateSet:
    if not isinstance(data, Mapping):
        raise TypeError("candidate_set JSON must be an object")
    schema = _as_str(data.get("schema_version") or data.get("schema") or "").strip()
    if not schema:
        raise ValueError("candidate_set JSON missing schema_version")
    cands = data.get("candidates")
    if not isinstance(cands, list):
        raise TypeError("candidate_set.candidates must be a list")
    out: List[Dict[str, Any]] = []
    for i, c in enumerate(cands):
        if not isinstance(c, Mapping):
            continue
        # allow either 'overrides' dict or direct knob dict
        ov = c.get("overrides")
        if isinstance(ov, Mapping):
            overrides = dict(ov)
        else:
            overrides = {k: v for k, v in c.items() if k not in {"id", "name", "overrides"}}
        cid = _as_str(c.get("id") or c.get("name") or f"cand_{i:05d}")
        out.append({"id": cid, "overrides": _sorted_dict(overrides)})
    meta = dict(data.get("meta") or {}) if isinstance(data.get("meta"), Mapping) else {}
    return CandidateSet(schema_version=schema, candidates=out, meta=_sorted_dict(meta))

def parse_candidate_set_csv(csv_bytes: bytes) -> CandidateSet:
    # Deterministic: UTF-8 only; comma-delimited; first row headers.
    text = csv_bytes.decode("utf-8")
    f = io.StringIO(text)
    reader = csv.DictReader(f)
    if reader.fieldnames is None:
        raise ValueError("CSV missing header row")
    headers = [h.strip() for h in reader.fieldnames if h is not None]
    if not headers:
        raise ValueError("CSV has empty header row")

    # reserved columns
    reserved = {"id", "name"}
    cand_rows: List[Dict[str, Any]] = []
    for idx, row in enumerate(reader):
        if not isinstance(row, Mapping):
            continue
        rid = (row.get("id") or row.get("name") or f"cand_{idx:05d}")
        overrides: Dict[str, Any] = {}
        for h in headers:
            if h in reserved:
                continue
            v = row.get(h)
            if v is None or str(v).strip() == "":
                continue
            # try numeric
            fv = _as_float(v)
            overrides[h] = fv if fv is not None else str(v)
        cand_rows.append({"id": _as_str(rid), "overrides": _sorted_dict(overrides)})

    return CandidateSet(
        schema_version="shams.extopt_candidate_set.csv.v1",
        candidates=cand_rows,
        meta={"source": "csv", "columns": headers},
    )


# -------------------------
# Pareto front
# -------------------------

@dataclass(frozen=True)
class ParetoObjective:
    key: str
    sense: str = "min"  # "min" | "max"

    def normalized_sense(self) -> str:
        s = str(self.sense or "min").strip().lower()
        return "max" if s == "max" else "min"

def _pareto_dominates(a: Mapping[str, float], b: Mapping[str, float], objectives: Sequence[ParetoObjective]) -> bool:
    better_or_equal = True
    strictly_better = False
    for o in objectives:
        k = str(o.key)
        va = float(a.get(k, float("nan")))
        vb = float(b.get(k, float("nan")))
        import math
        if not (math.isfinite(va) and math.isfinite(vb)):
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

def pareto_front(rows: List[Dict[str, Any]], objectives: Sequence[ParetoObjective]) -> List[Dict[str, Any]]:
    # Pre-extract objective vectors; skip rows missing objective values.
    pts: List[Tuple[Dict[str, Any], Dict[str, float]]] = []
    for r in rows:
        vec: Dict[str, float] = {}
        ok = True
        for o in objectives:
            v = _as_float(r.get(o.key))
            if v is None:
                ok = False
                break
            vec[str(o.key)] = float(v)
        if ok:
            pts.append((r, vec))

    front: List[Dict[str, Any]] = []
    for i, (ri, pi) in enumerate(pts):
        dominated = False
        for j, (_rj, pj) in enumerate(pts):
            if i == j:
                continue
            if _pareto_dominates(pj, pi, objectives):
                dominated = True
                break
        if not dominated:
            front.append(ri)

    # Deterministic stable ordering: preserve original order from `rows`
    row_ids = {id(r): i for i, r in enumerate(rows)}
    front.sort(key=lambda r: row_ids.get(id(r), 10**9))
    return front


# -------------------------
# Frontier intake orchestrator (v406)
# -------------------------

@dataclass(frozen=True)
class FrontierIntakeRunSpec:
    schema_version: str = "shams.extopt_frontier_intake_runspec.v406"
    evaluator_label: str = "hot_ion_point"
    intent: str = "reactor"
    include_run_artifacts: bool = True
    include_lane_artifacts: bool = False
    # UQ-lite interval spec selection:
    optimistic_label: str = "optimistic"
    robust_label: str = "robust"
    include_pareto: bool = True

def _coerce_point_inputs(base_inputs: Mapping[str, Any]) -> PointInputs:
    # Accept either already-typed PointInputs or a dict compatible with PointInputs(**...).
    if isinstance(base_inputs, PointInputs):
        return base_inputs
    if not isinstance(base_inputs, Mapping):
        raise TypeError("base_inputs must be a dict compatible with PointInputs")
    try:
        return PointInputs(**dict(base_inputs))
    except Exception as e:  # pragma: no cover
        raise ValueError(f"base_inputs could not be parsed into PointInputs: {e}")

def _concept_family_from_base_and_candidates(base_inputs: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]], *, intent: str) -> ConceptFamily:
    base = dict(base_inputs)
    cands: List[ConceptCandidate] = []
    for i, c in enumerate(candidates):
        cid = _as_str(c.get("id") or f"cand_{i:05d}")
        ov = c.get("overrides") if isinstance(c.get("overrides"), Mapping) else {}
        cands.append(ConceptCandidate(cid=cid, overrides=dict(ov)))
    return ConceptFamily(
        schema_version="concept_family.v1",
        name="extopt_frontier_intake",
        intent=str(intent or "research"),
        base_inputs=base,
        candidates=cands,
        notes="Generated by frontier_intake_v406 (firewalled).",
    )

def run_frontier_intake_v406(
    *,
    repo_root: Path,
    base_inputs: Mapping[str, Any],
    candidate_set: CandidateSet,
    objectives: Sequence[ParetoObjective],
    run_spec: FrontierIntakeRunSpec,
    optimistic_spec: UncertaintyContractSpec,
    robust_spec: UncertaintyContractSpec,
) -> Dict[str, Any]:
    """Run deterministic intake + verification + lane governance.

    Returns an artifact dict with embedded candidate summaries and optional artifacts.
    """
    ver = _read_version(repo_root)

    base_pi = _coerce_point_inputs(base_inputs)
    base_inputs_bytes = _stable_json_bytes(dict(base_inputs))
    base_inputs_hash = _sha256_bytes(base_inputs_bytes)

    cand_bytes = _stable_json_bytes({
        "schema_version": candidate_set.schema_version,
        "meta": candidate_set.meta,
        "candidates": candidate_set.candidates,
    })
    cand_hash = _sha256_bytes(cand_bytes)

    # Evaluate nominal candidates through frozen evaluator via extopt.batch
    fam = _concept_family_from_base_and_candidates(dict(base_inputs), candidate_set.candidates, intent=run_spec.intent)
    cfg = BatchEvalConfig(evaluator_label=run_spec.evaluator_label, intent=run_spec.intent, cache_enabled=True)
    rows, _meta = evaluate_concept_family(repo_root=repo_root, family=fam, config=cfg)

    # Build lookup
    by_id: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        if isinstance(r, dict):
            by_id[_as_str(r.get("id"))] = r

    # Lane evaluation
    candidates_out: List[Dict[str, Any]] = []
    for c in candidate_set.candidates:
        cid = _as_str(c.get("id"))
        r = by_id.get(cid, {})
        ra = r.get("run_artifact") if isinstance(r.get("run_artifact"), dict) else None

        # summary fields expected on row
        feasible = bool(r.get("feasible", False))
        verdict = _as_str(r.get("verdict") or ("PASS" if feasible else "FAIL")).upper()
        min_hard_margin = _as_float(r.get("min_hard_margin"))
        dom_auth = _as_str(r.get("dominant_authority") or r.get("dominant_mechanism") or "")
        dom_con = _as_str(r.get("dominant_constraint") or r.get("dominant_constraint_id") or "")

        # Objective extraction: allow pulling from row fields, then from run_artifact.kpis
        obj_vals: Dict[str, Optional[float]] = {}
        kpis = {}
        try:
            if isinstance(ra, dict):
                kpis = ra.get("kpis") if isinstance(ra.get("kpis"), dict) else {}
        except Exception:
            kpis = {}

        for o in objectives:
            k = str(o.key)
            v = _as_float(r.get(k))
            if v is None:
                v = _as_float(kpis.get(k)) if isinstance(kpis, dict) else None
            obj_vals[k] = v

        # Build PointInputs for lane evaluation
        # Merge base with overrides and coerce again
        merged = dict(base_inputs)
        merged.update(dict(c.get("overrides") or {}))
        pi = _coerce_point_inputs(merged)

        lane_opt = None
        lane_rob = None
        try:
            lane_opt = run_uncertainty_contract_for_point(
                pi,
                optimistic_spec,
                label_prefix=f"{run_spec.optimistic_label}_{cid}",
                include_corner_artifacts=bool(run_spec.include_lane_artifacts),
            )
        except Exception as e:
            lane_opt = {"schema_version": "uq_contract_error.v1", "error": _as_str(e)}
        try:
            lane_rob = run_uncertainty_contract_for_point(
                pi,
                robust_spec,
                label_prefix=f"{run_spec.robust_label}_{cid}",
                include_corner_artifacts=bool(run_spec.include_lane_artifacts),
            )
        except Exception as e:
            lane_rob = {"schema_version": "uq_contract_error.v1", "error": _as_str(e)}

        # Verdicts
        opt_pass = bool(isinstance(lane_opt, dict) and lane_opt.get("verdict") in {"ROBUST_PASS", "PASS"})
        rob_pass = bool(isinstance(lane_rob, dict) and lane_rob.get("verdict") in {"ROBUST_PASS", "PASS"})
        mirage = bool(opt_pass and (not rob_pass))

        cand_out: Dict[str, Any] = {
            "id": cid,
            "overrides": dict(c.get("overrides") or {}),
            "nominal": {
                "verdict": verdict,
                "feasible": bool(feasible),
                "min_hard_margin": min_hard_margin,
                "dominant_authority": dom_auth,
                "dominant_constraint": dom_con,
            },
            "objectives": obj_vals,
            "lane_optimistic": {
                "verdict": _as_str(lane_opt.get("verdict")) if isinstance(lane_opt, dict) else "",
                "artifact": lane_opt if bool(run_spec.include_lane_artifacts) else None,
            },
            "lane_robust": {
                "verdict": _as_str(lane_rob.get("verdict")) if isinstance(lane_rob, dict) else "",
                "artifact": lane_rob if bool(run_spec.include_lane_artifacts) else None,
            },
            "mirage": mirage,
            "run_artifact": ra if bool(run_spec.include_run_artifacts) else None,
        }

        candidates_out.append(cand_out)

    # Pareto fronts (feasible-only by lane)
    pareto: Dict[str, Any] = {}
    if run_spec.include_pareto and objectives:
        # Construct row dicts for pareto based on objectives and lane filters
        def _row_for_pareto(c: Dict[str, Any]) -> Dict[str, Any]:
            d = {"id": c.get("id"), "mirage": c.get("mirage", False)}
            for o in objectives:
                d[o.key] = c.get("objectives", {}).get(o.key)
            return d

        opt_rows = []
        rob_rows = []
        for c in candidates_out:
            opt_ok = _as_str(c.get("lane_optimistic", {}).get("verdict")).upper() in {"ROBUST_PASS", "PASS"}
            rob_ok = _as_str(c.get("lane_robust", {}).get("verdict")).upper() in {"ROBUST_PASS", "PASS"}
            if opt_ok:
                opt_rows.append(_row_for_pareto(c))
            if rob_ok:
                rob_rows.append(_row_for_pareto(c))

        pareto["objectives"] = [ {"key": o.key, "sense": o.normalized_sense()} for o in objectives ]
        pareto["optimistic_front"] = pareto_front(opt_rows, objectives)
        pareto["robust_front"] = pareto_front(rob_rows, objectives)

        opt_ids = {str(r.get("id")) for r in pareto["optimistic_front"]}
        rob_ids = {str(r.get("id")) for r in pareto["robust_front"]}
        for c in candidates_out:
            c["in_pareto_front"] = {
                "optimistic": str(c.get("id")) in opt_ids,
                "robust": str(c.get("id")) in rob_ids,
            }

    artifact: Dict[str, Any] = {
        "schema_version": "shams.extopt_frontier_intake_evidence.v406",
        "shams_version": ver,
        "run_spec": json.loads(_stable_json_bytes({
            "schema_version": run_spec.schema_version,
            "evaluator_label": run_spec.evaluator_label,
            "intent": run_spec.intent,
            "include_run_artifacts": bool(run_spec.include_run_artifacts),
            "include_lane_artifacts": bool(run_spec.include_lane_artifacts),
            "include_pareto": bool(run_spec.include_pareto),
            "optimistic_label": run_spec.optimistic_label,
            "robust_label": run_spec.robust_label,
        }).decode("utf-8")),
        "inputs": {
            "base_inputs_sha256": base_inputs_hash,
            "candidate_set_sha256": cand_hash,
            "candidate_set_schema": candidate_set.schema_version,
            "candidate_set_meta": candidate_set.meta,
        },
        "uq_specs": {
            "optimistic": json.loads(_stable_json_bytes(optimistic_spec.to_dict()).decode("utf-8")) if hasattr(optimistic_spec, "to_dict") else {},
            "robust": json.loads(_stable_json_bytes(robust_spec.to_dict()).decode("utf-8")) if hasattr(robust_spec, "to_dict") else {},
        },
        "candidates": candidates_out,
        "pareto": pareto,
        "digest": _sha256_bytes(_stable_json_bytes({"base": base_inputs_hash, "cand": cand_hash, "objectives": [o.key for o in objectives]})),
    }
    return artifact
