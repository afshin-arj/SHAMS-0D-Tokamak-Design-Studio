"""Publication Benchmarks extended helpers."""
from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ui_nicegui.bootstrap import repo_root


def list_crosscode_items() -> List[Tuple[str, Path]]:
    from benchmarks.crosscode.crosscode_compare import list_crosscode_constitutions

    return list_crosscode_constitutions()


def compare_crosscode(code_path: Path, intent: str) -> dict:
    from benchmarks.crosscode.crosscode_compare import compare_to_shams_intent, load_crosscode_constitution

    cc = load_crosscode_constitution(code_path)
    return compare_to_shams_intent(intent, cc)


def crosscode_clause_rows(comp: dict) -> List[dict]:
    baseline = comp.get("baseline_constitution") or {}
    external = ((comp.get("crosscode_constitution") or {}).get("clauses") or {})
    rows = []
    for k in sorted(external.keys()):
        rows.append({
            "clause": k,
            "shams": baseline.get(k, "(missing)"),
            "external": external.get(k, ""),
        })
    return rows


def validate_contracts() -> Tuple[list, dict]:
    from src.governance.contract_validator import validate_contracts_dir

    contracts_dir = Path(repo_root()) / "contracts"
    recs, summary = validate_contracts_dir(contracts_dir)
    return recs, summary


def load_contract(name: str) -> Tuple[Optional[dict], List[str]]:
    from src.governance.contract_validator import load_contract_json

    p = Path(repo_root()) / "contracts" / name
    return load_contract_json(p)


def contract_bundle_zip() -> bytes:
    from src.governance.contract_validator import validate_contracts_dir

    contracts_dir = Path(repo_root()) / "contracts"
    recs, summary = validate_contracts_dir(contracts_dir)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for r in recs:
            p = contracts_dir / r.name
            if p.exists():
                z.writestr(f"contracts/{r.name}", p.read_bytes())
        z.writestr("CONTRACTS_MANIFEST.json", json.dumps(summary, indent=2, sort_keys=True))
    return buf.getvalue()


def contract_structural_diff(obj_a: dict, obj_b: dict) -> dict:
    keys_a = set(obj_a.keys())
    keys_b = set(obj_b.keys())
    return {
        "only_in_a": sorted(keys_a - keys_b),
        "only_in_b": sorted(keys_b - keys_a),
        "in_both": sorted(keys_a & keys_b),
    }


def read_topology_regression_report() -> Optional[dict]:
    p = Path(repo_root()) / "verification" / "topology_regression_report.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def run_publication_benchmark_pack(*, also_opposite_intent: bool = True) -> dict:
    root = Path(repo_root())
    ts = time.strftime("%Y%m%d_%H%M%S")
    outdir = root / "benchmarks" / "publication" / "out_ui" / ts
    outdir.mkdir(parents=True, exist_ok=True)
    cases = root / "benchmarks" / "publication" / "cases_point_designer.json"
    runner = root / "benchmarks" / "publication" / "run_point_designer_benchmarks.py"
    cmd = [sys.executable, str(runner), "--cases", str(cases), "--outdir", str(outdir)]
    if also_opposite_intent:
        cmd.append("--also-run-opposite-intent")
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(root))
    return {
        "returncode": int(proc.returncode),
        "outdir": str(outdir),
        "stdout": (proc.stdout or "")[:8000],
        "stderr": (proc.stderr or "")[:8000],
    }


def read_pack_topology(outdir: str) -> Optional[dict]:
    p = Path(outdir) / "topology.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_baseline_packs() -> List[str]:
    base_dir = Path(repo_root()) / "benchmarks" / "publication" / "baselines"
    if not base_dir.is_dir():
        return [str(base_dir)]
    opts = sorted(str(p) for p in base_dir.iterdir())
    return opts or [str(base_dir)]


def explain_benchmark_delta(*, baseline: str, candidate: str) -> dict:
    root = Path(repo_root())
    runner = root / "benchmarks" / "publication" / "explain_delta.py"
    proc = subprocess.run(
        [sys.executable, str(runner), "--baseline", baseline, "--candidate", candidate],
        capture_output=True,
        text=True,
        cwd=str(root),
    )
    delta_path = Path(candidate) / "delta.md"
    delta_text = ""
    if delta_path.is_file():
        delta_text = delta_path.read_text(encoding="utf-8", errors="replace")[:12000]
    return {
        "returncode": int(proc.returncode),
        "stdout": (proc.stdout or "")[:4000],
        "stderr": (proc.stderr or "")[:4000],
        "delta_md": delta_text,
    }


def session_cache_sources(session) -> Dict[str, Any]:
    return {
        "pd_last_outputs": getattr(session, "pd_last_artifact", None) or getattr(session, "last_eval", None),
        "systems_last_solution": getattr(session, "systems_last_solve_artifact", None),
        "scan_last_artifact": getattr(session, "scan_last_artifact", None) or getattr(session, "scan_cartography_artifact", None),
        "pareto_last_front": getattr(session, "pareto_last_front", None),
        "extopt_last_run": getattr(session, "extopt_last_run", None),
        "surrogate_v386_last_screening_run": getattr(session, "surrogate_v386_last_screening_run", None),
    }


def pick_session_run_artifact(session) -> Optional[dict]:
    """Best-effort current run artifact for reviewer/licensing packs."""
    for key in (
        "pd_last_artifact",
        "systems_last_solve_artifact",
        "last_eval",
    ):
        art = getattr(session, key, None)
        if isinstance(art, dict) and art:
            return art
    triple = session_cache_sources(session)
    for key in ("pd_last_outputs", "systems_last_solution"):
        art = triple.get(key)
        if isinstance(art, dict) and art:
            return art
    return None


def artifact_snapshot(art: dict) -> dict:
    return {
        "shams_version": art.get("shams_version"),
        "intent": art.get("intent"),
        "verdict": art.get("verdict"),
        "dominant_mechanism": art.get("dominant_mechanism") or art.get("dominant_authority"),
        "magnet_regime": art.get("magnet_regime"),
        "exhaust_regime": art.get("exhaust_regime"),
    }


def build_regulatory_reviewer_pack(session, *, repo: Optional[Path] = None) -> bytes:
    from tools.regulatory_pack import export_regulatory_evidence_pack_zip

    root = Path(repo or repo_root())
    art = pick_session_run_artifact(session)
    if not isinstance(art, dict) or not art:
        raise ValueError("No session run artifact — evaluate in Point Designer or Systems Mode first.")
    extra: Dict[str, Any] = {}
    fam = getattr(session, "design_families_last", None)
    if isinstance(fam, dict) and fam:
        extra["design_family"] = fam
    out_dir = root / "ui_runs" / "regulatory_evidence_pack"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_zip = out_dir / "reviewer_pack_v334.zip"
    export_regulatory_evidence_pack_zip(root, art, out_zip, extra=extra, basename="reviewer_pack")
    return out_zip.read_bytes()


def validate_regulatory_pack_bytes(data: bytes) -> dict:
    import tempfile

    from tools.regulatory_pack import validate_regulatory_pack_zip

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(data)
        path = Path(tmp.name)
    try:
        res = validate_regulatory_pack_zip(path)
        return {
            "ok": bool(res.ok),
            "warnings": list(res.warnings or []),
            "errors": list(res.errors or []),
        }
    finally:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


def build_licensing_tier2_pack(session, *, repo: Optional[Path] = None) -> bytes:
    from tools.licensing_pack_v355 import export_licensing_evidence_tier2_zip

    root = Path(repo or repo_root())
    art = pick_session_run_artifact(session)
    if not isinstance(art, dict) or not art:
        raise ValueError("No session run artifact — evaluate in Point Designer or Systems Mode first.")
    extra: Dict[str, Any] = {}
    cert = getattr(session, "robust_pareto_last", None) or getattr(session, "v352_last_certification", None)
    if isinstance(cert, dict) and cert:
        extra["certification"] = cert
    out_dir = root / "ui_runs" / "licensing_evidence_tier2"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_zip = out_dir / "licensing_pack_tier2_v355.zip"
    export_licensing_evidence_tier2_zip(root, art, out_zip, extra=extra, basename="licensing_pack_tier2")
    return out_zip.read_bytes()


def validate_licensing_pack_bytes(data: bytes) -> dict:
    import tempfile

    from tools.licensing_pack_v355 import validate_licensing_pack_tier2_zip

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(data)
        path = Path(tmp.name)
    try:
        res = validate_licensing_pack_tier2_zip(path)
        return {
            "ok": bool(res.ok),
            "warnings": list(res.warnings or []),
            "errors": list(res.errors or []),
        }
    finally:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class EvidencePackResult:
    zip_path: Path
    index: dict
    zip_bytes: bytes


def build_evidence_pack_v387(
    out_zip: Path,
    *,
    shams_version: str,
    sources: Dict[str, Any],
    include: Dict[str, bool],
    notes: str = "",
) -> EvidencePackResult:
    """Deterministic evidence ZIP from cached session artifacts (export-only)."""
    out_zip = Path(out_zip)
    out_zip.parent.mkdir(parents=True, exist_ok=True)

    included: Dict[str, Any] = {}
    for key, flag in sorted(include.items()):
        if not flag:
            continue
        val = sources.get(key)
        if isinstance(val, (dict, list)):
            included[key] = val

    index = {
        "schema": "evidence_pack_v387.index.v1",
        "shams_version": shams_version,
        "notes": notes,
        "included_sources": sorted(included.keys()),
        "n_sources": len(included),
    }
    provenance = {
        "schema": "evidence_pack_v387.provenance.v1",
        "generator": "NiceGUI",
        "shams_version": shams_version,
    }
    narrative = (
        "# SHAMS Evidence Pack\n\n"
        "Deterministic export from cached session artifacts. No physics recomputation.\n\n"
        f"Sources included: {', '.join(index['included_sources']) or '(none)'}\n"
    )
    if notes.strip():
        narrative += f"\n## Reviewer notes\n\n{notes.strip()}\n"

    buf = io.BytesIO()
    manifest: Dict[str, str] = {}
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        def _add(name: str, payload: bytes) -> None:
            z.writestr(name, payload)
            manifest[name] = _sha256_bytes(payload)

        _add("EVIDENCE_INDEX.json", json.dumps(index, indent=2, sort_keys=True).encode("utf-8"))
        _add("EVIDENCE_INDEX_FINAL.json", json.dumps(index, indent=2, sort_keys=True).encode("utf-8"))
        _add("RUN_PROVENANCE.json", json.dumps(provenance, indent=2, sort_keys=True).encode("utf-8"))
        _add("NARRATIVE_STUB.md", narrative.encode("utf-8"))
        for key in sorted(included.keys()):
            payload = json.dumps(included[key], indent=2, sort_keys=True, default=str).encode("utf-8")
            _add(f"sources/{key}.json", payload)
        _add("MANIFEST_SHA256.json", json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8"))

    zip_bytes = buf.getvalue()
    out_zip.write_bytes(zip_bytes)
    index = dict(index)
    index["manifest_sha256"] = _sha256_bytes(zip_bytes)
    index["zip_path"] = str(out_zip)
    return EvidencePackResult(zip_path=out_zip, index=index, zip_bytes=zip_bytes)
