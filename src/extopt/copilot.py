"""External Optimizer Co-Pilot (v342.0).

This module provides *orchestration and interpretation* helpers for external
optimizers, without running any optimizer internally.

Key properties (SHAMS law):

- No solver-based negotiation.
- No optimization inside physics truth.
- Deterministic, audit-friendly I/O (run folders, traces, hashes).

The co-pilot evaluates candidate sets (typically provided by an external
optimizer) using the frozen evaluator, then produces:

- optimizer_trace.json (candidate-level verdicts + dominant killers)
- interpretation_report.json (attrition summary + narrative)
- optional per-candidate evidence packs (dossiers)

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import json
import hashlib

from .family import ConceptFamily, load_concept_family
from .batch import BatchEvalConfig, BatchEvalResult, evaluate_concept_family
from .evidence import export_evidence_pack
from .interpretation import interpret_optimizer_trace


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def build_optimizer_trace_from_batch(
    batch: BatchEvalResult,
    *,
    optimizer_name: str,
    run_id: str,
) -> Dict[str, Any]:
    """Convert BatchEvalResult to the reference optimizer_trace.json schema."""
    candidates: List[Dict[str, Any]] = []
    for r in batch.results:
        art = r.artifact if isinstance(r.artifact, dict) else {}
        kpis = art.get("kpis", {}) if isinstance(art.get("kpis"), dict) else {}
        verdict = "FEASIBLE" if bool(kpis.get("feasible_hard", False)) else "INFEASIBLE"
        candidates.append(
            {
                "cid": r.cid,
                "verdict": verdict,
                "min_hard_margin": kpis.get("min_hard_margin"),
                "dominant_authority": art.get("dominant_authority")
                or art.get("dominant_mechanism")
                or "UNKNOWN",
                "dominant_constraint": art.get("dominant_constraint")
                or art.get("dominant_constraint_id")
                or "UNKNOWN",
            }
        )

    return {
        "schema_version": "shams.optimizer_trace.v1",
        "optimizer": str(optimizer_name),
        "run_id": str(run_id),
        "intent": str(batch.intent),
        "family": str(batch.family_name),
        "n_total": int(batch.n_total),
        "n_feasible": int(batch.n_feasible),
        "candidates": candidates,
    }


@dataclass(frozen=True)
class CoPilotRunResult:
    run_dir: Path
    trace_path: Path
    report_path: Path
    manifest_path: Path
    n_total: int
    n_feasible: int


def run_copilot_from_concept_family(
    concept_family_path: Path,
    *,
    optimizer_name: str,
    run_dir: Path,
    evaluator_label: str = "hot_ion_point",
    cache_dir: Optional[Path] = None,
    export_candidate_packs: bool = True,
) -> CoPilotRunResult:
    """Evaluate an external-optimizer candidate set (as a concept family YAML).

    Writes a deterministic run folder containing trace + interpretation.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    family: ConceptFamily = load_concept_family(concept_family_path)

    batch = evaluate_concept_family(
        family,
        config=BatchEvalConfig(evaluator_label=evaluator_label, cache_dir=cache_dir),
        repo_root=run_dir,
    )

    run_id = run_dir.name
    trace = build_optimizer_trace_from_batch(batch, optimizer_name=optimizer_name, run_id=run_id)
    report = interpret_optimizer_trace(trace)

    # Persist primary artifacts
    (run_dir / "inputs").mkdir(exist_ok=True)
    (run_dir / "inputs" / concept_family_path.name).write_text(
        concept_family_path.read_text(encoding="utf-8"), encoding="utf-8"
    )

    trace_path = run_dir / "optimizer_trace.json"
    report_path = run_dir / "interpretation_report.json"
    _write_json(trace_path, trace)
    _write_json(report_path, report)

    # Candidate summaries + optional evidence packs
    cands_dir = run_dir / "candidates"
    cands_dir.mkdir(exist_ok=True)
    summaries: List[Dict[str, Any]] = []
    packs_dir = run_dir / "evidence_packs"
    if export_candidate_packs:
        packs_dir.mkdir(exist_ok=True)

    for r in batch.results:
        art = r.artifact if isinstance(r.artifact, dict) else {}
        kpis = art.get("kpis", {}) if isinstance(art.get("kpis"), dict) else {}
        summaries.append(
            {
                "cid": r.cid,
                "feasible_hard": bool(kpis.get("feasible_hard", False)),
                "min_hard_margin": kpis.get("min_hard_margin"),
                "dominant_authority": art.get("dominant_authority")
                or art.get("dominant_mechanism")
                or "UNKNOWN",
                "dominant_constraint": art.get("dominant_constraint")
                or art.get("dominant_constraint_id")
                or "UNKNOWN",
                "cache_hit": bool(r.cache_hit),
            }
        )
        _write_json(cands_dir / f"{r.cid}.json", art)
        if export_candidate_packs:
            export_evidence_pack(art, packs_dir, basename=str(r.cid))

    _write_json(run_dir / "eval_results.json", {"schema": "extopt_eval_results.v1", "results": summaries})

    # Deterministic manifest with per-file hashes
    manifest: Dict[str, Any] = {
        "schema_version": "shams.extopt_copilot_manifest.v1",
        "run_id": run_id,
        "optimizer": str(optimizer_name),
        "evaluator_label": str(evaluator_label),
        "n_total": int(batch.n_total),
        "n_feasible": int(batch.n_feasible),
        "files": {},
    }
    for p in sorted(run_dir.rglob("*")):
        if p.is_file():
            rel = p.relative_to(run_dir).as_posix()
            manifest["files"][rel] = _sha256_file(p)

    manifest_path = run_dir / "RUN_MANIFEST_SHA256.json"
    _write_json(manifest_path, manifest)

    return CoPilotRunResult(
        run_dir=run_dir,
        trace_path=trace_path,
        report_path=report_path,
        manifest_path=manifest_path,
        n_total=int(batch.n_total),
        n_feasible=int(batch.n_feasible),
    )
