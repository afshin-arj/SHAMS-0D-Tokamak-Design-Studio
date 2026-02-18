from __future__ import annotations

"""Certified External Optimizer Orchestrator 2.0 (v385).

This module is a *governance-grade importer/verifier* for external optimizer outputs.

Core guarantees
--------------
- Frozen truth is never modified.
- No optimization is performed inside SHAMS.
- Candidate designs are re-evaluated deterministically using the frozen evaluator.
- Outputs are exported as deterministic evidence bundles with SHA-256 manifests.

Supported inputs (v385)
-----------------------
1) Concept family YAML (concept_family.v1)
   - Common interchange format for external runs and SHAMS “lite” optimizers.
   - Candidates are defined as overrides on top of base_inputs.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .batch import BatchEvalConfig, evaluate_concept_family
from .bundle import BundleCandidate, BundleProvenance, export_bundle_zip
from .evidence import export_evidence_pack
from .family import load_concept_family


def _stable_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()


def _read_version(repo_root: Path) -> str:
    for name in ("VERSION", "VERSION.txt"):
        p = repo_root / name
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    return "unknown"


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _run_manifest_sha256(run_dir: Path) -> Dict[str, str]:
    man: Dict[str, str] = {}
    for fp in sorted([p for p in run_dir.rglob("*") if p.is_file()]):
        rel = fp.relative_to(run_dir).as_posix()
        man[rel] = _sha256_bytes(fp.read_bytes())
    return man


@dataclass(frozen=True)
class OrchestratorRunSpec:
    schema: str = "shams_extopt_orchestrator_runspec.v385"
    evaluator_label: str = "hot_ion_point"
    intent: str = "research"
    include_evidence_packs: bool = True
    cache_enabled: bool = True


@dataclass(frozen=True)
class OrchestratorRunResult:
    schema: str
    shams_version: str
    family_name: str
    intent: str
    evaluator_label: str
    n_total: int
    n_feasible: int
    pass_rate: float
    run_dir: str
    bundle_zip: str
    run_manifest_sha256: Dict[str, str]
    summary: Dict[str, Any]


def run_orchestrator_v385_from_concept_family(
    *,
    concept_family_yaml: Path,
    repo_root: Path,
    out_dir: Path,
    runspec: Optional[OrchestratorRunSpec] = None,
) -> OrchestratorRunResult:
    """Import a concept family YAML, deterministically verify candidates, export evidence."""

    rs = runspec or OrchestratorRunSpec()
    concept_family_yaml = Path(concept_family_yaml)
    repo_root = Path(repo_root)
    out_dir = Path(out_dir)
    _ensure_dir(out_dir)

    fam = load_concept_family(concept_family_yaml)
    intent = str(rs.intent or fam.intent)

    run_dir = out_dir / f"extopt_orchestrator_v385_{concept_family_yaml.stem}"
    _ensure_dir(run_dir)

    cfg = BatchEvalConfig(
        evaluator_label=str(rs.evaluator_label),
        cache_dir=(repo_root / "runs" / "disk_cache"),
        cache_enabled=bool(rs.cache_enabled),
    )

    # intent affects constraints; override without mutating source file
    fam2 = fam
    if intent != fam.intent:
        from dataclasses import replace
        fam2 = replace(fam, intent=intent)

    ber = evaluate_concept_family(fam2, config=cfg, repo_root=repo_root)

    bundle_candidates: List[BundleCandidate] = []
    evidence_paths: Dict[str, Path] = {}
    if bool(rs.include_evidence_packs):
        _ensure_dir(run_dir / "evidence_packs")

    for r in ber.results:
        bundle_candidates.append(BundleCandidate(cid=str(r.cid), artifact=r.artifact, cache_hit=bool(r.cache_hit)))
        if bool(rs.include_evidence_packs):
            ep = export_evidence_pack(r.artifact, run_dir / "evidence_packs", basename=str(r.cid))
            p = Path(str(ep.get("out_zip", "")))
            if p.exists():
                evidence_paths[str(r.cid)] = p

    prov = BundleProvenance(
        shams_version=_read_version(repo_root),
        evaluator_label=str(rs.evaluator_label),
        intent=str(intent),
        family_name=str(fam.name),
        family_source=str(concept_family_yaml.name),
    )

    bundle_zip = run_dir / f"extopt_bundle_v385_{concept_family_yaml.stem}.zip"
    export_bundle_zip(
        out_zip=bundle_zip,
        candidates=bundle_candidates,
        provenance=prov,
        include_artifact_json=True,
        include_evidence_packs=bool(rs.include_evidence_packs),
        evidence_pack_paths=evidence_paths,
    )

    ledger = {
        "schema": "shams_extopt_orchestrator_run_ledger.v385",
        "shams_version": prov.shams_version,
        "evaluator_label": prov.evaluator_label,
        "intent": prov.intent,
        "family": {
            "schema_version": getattr(fam, "schema_version", ""),
            "name": fam.name,
            "source": prov.family_source,
            "notes": getattr(fam, "notes", ""),
        },
        "summary": ber.summary,
        "outputs": {
            "bundle_zip": bundle_zip.name,
            "include_evidence_packs": bool(rs.include_evidence_packs),
            "n_evidence_packs": int(len(evidence_paths)),
        },
    }
    (run_dir / "run_ledger.json").write_bytes(_stable_json_bytes(ledger))
    run_manifest = _run_manifest_sha256(run_dir)
    (run_dir / "RUN_MANIFEST_SHA256.json").write_bytes(_stable_json_bytes(run_manifest))

    res = OrchestratorRunResult(
        schema="shams_extopt_orchestrator_run_result.v385",
        shams_version=prov.shams_version,
        family_name=str(fam.name),
        intent=str(intent),
        evaluator_label=str(rs.evaluator_label),
        n_total=int(ber.n_total),
        n_feasible=int(ber.n_feasible),
        pass_rate=float(ber.pass_rate),
        run_dir=str(run_dir),
        bundle_zip=str(bundle_zip),
        run_manifest_sha256=run_manifest,
        summary=ber.summary,
    )
    (run_dir / "run_result.json").write_bytes(_stable_json_bytes(res.__dict__))
    return res
