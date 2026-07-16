from __future__ import annotations

"""PROCESS parity corpus loader + honesty gate (independence ticket 1.3).

Corpus path: ``benchmarks/parity/process_reference_cases.json``

Rules
-----
* Never invent PROCESS / MFILE numeric KPIs.
* ``METHOD-ONLY`` cases must keep all ``process_reference`` KPI values null/absent.
* ``NUMERIC`` cases require a declared provenance source for PROCESS numbers.
* Every case must point at a hashed delta dossier under ``benchmarks/parity/dossiers/``.

© 2026 Afshin Arjhangmehr
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
import math

from .delta_dossier import (
    build_delta_dossier,
    classify_dossier_status,
    has_numeric_process_kpis,
    render_delta_dossier_markdown,
)
from .process_map import map_shams_to_process_like

SCHEMA_V1 = "process.parity_cases.v1"
SCHEMA_V2 = "process.parity_cases.v2"
ALLOWED_SCHEMAS = {SCHEMA_V1, SCHEMA_V2}
ALLOWED_STATUS = {"METHOD-ONLY", "NUMERIC"}

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_PATH = _REPO_ROOT / "benchmarks" / "parity" / "process_reference_cases.json"
DEFAULT_DOSSIER_DIR = _REPO_ROOT / "benchmarks" / "parity" / "dossiers"

# KPI keys that must remain null under METHOD-ONLY honesty.
_PROCESS_KPI_KEYS = (
    "Q_plasma",
    "Q_eng",
    "Pe_net_MW",
    "Pe_gross_MW",
    "P_fus_MW",
    "P_aux_MW",
    "P_recirc_MW",
    "recirc_frac",
    "P_el_net_W",
    "P_fus_W",
    "P_el_net_MW",
)


def _canon_for_hash(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _canon_for_hash(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, (list, tuple)):
        return [_canon_for_hash(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj):
            return "NaN"
        if math.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        return obj
    return obj


def canonical_dumps(obj: Any) -> str:
    return json.dumps(_canon_for_hash(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(obj: Any) -> str:
    return hashlib.sha256(canonical_dumps(obj).encode("utf-8")).hexdigest()


def load_process_reference_corpus(path: Optional[Path] = None) -> Dict[str, Any]:
    p = Path(path) if path is not None else DEFAULT_CORPUS_PATH
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("process_reference_cases.json must be a JSON object")
    schema = str(raw.get("schema_version") or raw.get("schema") or "")
    if schema not in ALLOWED_SCHEMAS:
        raise ValueError(f"Unsupported corpus schema: {schema!r}")
    cases = raw.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Corpus must contain a non-empty 'cases' list")
    return raw


def _null_or_absent_kpis(process_reference: Dict[str, Any]) -> List[str]:
    """Return KPI keys that are illegally non-null for METHOD-ONLY."""
    bad: List[str] = []
    for k in _PROCESS_KPI_KEYS:
        if k in process_reference and process_reference.get(k) is not None:
            bad.append(k)
    # Also catch nested kpis
    nested = process_reference.get("kpis")
    if isinstance(nested, dict):
        for k in _PROCESS_KPI_KEYS:
            if k in nested and nested.get(k) is not None:
                bad.append(f"kpis.{k}")
    return bad


def validate_corpus_honesty(corpus: Dict[str, Any]) -> List[str]:
    """Return a list of honesty / schema violations (empty = OK)."""
    issues: List[str] = []
    cases = corpus.get("cases") if isinstance(corpus.get("cases"), list) else []
    if not cases:
        issues.append("corpus has no cases")
        return issues

    corpus_status = str(corpus.get("corpus_status") or "").strip()
    if corpus.get("schema_version") == SCHEMA_V2 and corpus_status not in ALLOWED_STATUS:
        issues.append(f"corpus_status must be one of {sorted(ALLOWED_STATUS)}")

    for i, case in enumerate(cases):
        if not isinstance(case, dict):
            issues.append(f"cases[{i}] is not an object")
            continue
        cid = str(case.get("case_id") or f"idx{i}")
        status = str(case.get("dossier_status") or corpus_status or "METHOD-ONLY").strip()
        if status not in ALLOWED_STATUS:
            issues.append(f"{cid}: dossier_status must be METHOD-ONLY or NUMERIC")
            continue

        pref = case.get("process_reference")
        if pref is None:
            pref = {}
        if not isinstance(pref, dict):
            issues.append(f"{cid}: process_reference must be an object")
            continue

        if status == "METHOD-ONLY":
            bad = _null_or_absent_kpis(pref)
            if bad:
                issues.append(
                    f"{cid}: METHOD-ONLY forbids non-null PROCESS KPIs {bad} "
                    "(do not invent MFILE numbers)"
                )
            if has_numeric_process_kpis(pref):
                issues.append(f"{cid}: METHOD-ONLY but process_reference has numeric KPIs")
        else:
            # NUMERIC requires provenance + at least one real KPI
            if not has_numeric_process_kpis(pref):
                issues.append(f"{cid}: NUMERIC status requires at least one non-null PROCESS KPI")
            prov = case.get("provenance") if isinstance(case.get("provenance"), dict) else {}
            src = prov.get("process_reference_source")
            if not src:
                issues.append(f"{cid}: NUMERIC requires provenance.process_reference_source")

        inputs = case.get("inputs")
        if not isinstance(inputs, dict) or not inputs:
            issues.append(f"{cid}: inputs must be a non-empty PointInputs-compatible object")

        dd = case.get("delta_dossier") if isinstance(case.get("delta_dossier"), dict) else {}
        if not dd.get("path"):
            issues.append(f"{cid}: delta_dossier.path is required")
        if not dd.get("sha256") or len(str(dd.get("sha256"))) < 32:
            issues.append(f"{cid}: delta_dossier.sha256 is required (hashed dossier)")

    return issues


def _repo_relative(path: Path, repo_root: Optional[Path] = None) -> Path:
    root = Path(repo_root) if repo_root is not None else _REPO_ROOT
    try:
        return path.resolve().relative_to(root.resolve())
    except Exception:
        return path


def resolve_dossier_path(case: Dict[str, Any], *, repo_root: Optional[Path] = None) -> Path:
    root = Path(repo_root) if repo_root is not None else _REPO_ROOT
    dd = case.get("delta_dossier") if isinstance(case.get("delta_dossier"), dict) else {}
    rel = str(dd.get("path") or "")
    if not rel:
        cid = str(case.get("case_id") or "unknown")
        return root / "benchmarks" / "parity" / "dossiers" / f"{cid}_delta_dossier.json"
    p = Path(rel)
    return p if p.is_absolute() else (root / p)


def build_case_delta_dossier(
    case: Dict[str, Any],
    *,
    evaluate: bool = True,
) -> Dict[str, Any]:
    """Build a delta dossier for one corpus case.

    For METHOD-ONLY, ``process_payload`` is omitted even if process_reference exists
    with nulls — classification stays honest.
    """
    cid = str(case.get("case_id") or "unknown")
    inputs = dict(case.get("inputs") or {})
    status = str(case.get("dossier_status") or "METHOD-ONLY").strip()
    pref = case.get("process_reference") if isinstance(case.get("process_reference"), dict) else {}

    mapping_payload = None
    try:
        mapping_payload = map_shams_to_process_like(inputs).to_dict()
    except Exception as ex:
        mapping_payload = {"schema": "shams_process_map_error.v1", "error": str(ex)}

    art: Dict[str, Any]
    if evaluate:
        try:
            from models.inputs import PointInputs  # type: ignore
            from evaluator.core import Evaluator  # type: ignore
            from constraints.system import build_constraints_from_outputs  # type: ignore
            from shams_io.run_artifact import build_run_artifact  # type: ignore
        except Exception:
            from src.models.inputs import PointInputs  # type: ignore
            from src.evaluator.core import Evaluator  # type: ignore
            from src.constraints.system import build_constraints_from_outputs  # type: ignore
            from src.shams_io.run_artifact import build_run_artifact  # type: ignore

        ev = Evaluator(label=f"parity_corpus::{cid}", cache_enabled=False)
        pi = PointInputs(**inputs)
        evr = ev.evaluate(pi)
        if not evr.ok:
            art = {
                "schema_version": "shams_run_artifact.v1",
                "kind": "shams_run_artifact",
                "inputs": inputs,
                "outputs": {},
                "constraints": [],
                "kpis": {"feasible_hard": False, "min_hard_margin": float("nan")},
                "verdict": "NO-SOLUTION",
                "error": evr.message,
            }
        else:
            out = evr.out
            cons = build_constraints_from_outputs(out, design_intent=f"parity_corpus::{cid}")
            art = build_run_artifact(inputs=inputs, outputs=out, constraints=cons)
    else:
        art = {
            "schema_version": "shams_run_artifact.v1",
            "kind": "shams_run_artifact",
            "inputs": inputs,
            "outputs": {},
            "constraints": [],
            "kpis": {},
            "verdict": "UNEVALUATED",
        }

    process_payload: Optional[Dict[str, Any]] = None
    if status == "NUMERIC" and has_numeric_process_kpis(pref):
        process_payload = dict(pref)

    dossier = build_delta_dossier(
        case_id=cid,
        shams_artifact=art,
        process_payload=process_payload,
        mapping_payload=mapping_payload,
    )
    # Force declared status (NUMERIC only when payload actually has numbers)
    dossier["dossier_status"] = classify_dossier_status(process_payload)
    if dossier["dossier_status"] == "METHOD-ONLY":
        dossier["has_process_reference"] = False
        dossier.setdefault(
            "honesty",
            {
                "label": "METHOD-ONLY",
                "statement": (
                    "No numeric PROCESS reference KPIs were supplied. "
                    "This dossier records SHAMS diagnostics and mapping assumptions only; "
                    "it does not invent MFILE / OUT.DAT values."
                ),
            },
        )
    dossier["markdown"] = render_delta_dossier_markdown(dossier)
    dossier["corpus"] = {
        "case_id": cid,
        "declared_status": status,
        "provenance": case.get("provenance") if isinstance(case.get("provenance"), dict) else {},
    }
    return dossier


def dossier_hash_payload(dossier: Dict[str, Any]) -> Dict[str, Any]:
    """Stable subset hashed for corpus integrity (exclude large markdown)."""
    skip = {"markdown"}
    return {k: v for k, v in dossier.items() if k not in skip}


def materialize_case_dossier(
    case: Dict[str, Any],
    *,
    repo_root: Optional[Path] = None,
    write: bool = True,
) -> Tuple[Dict[str, Any], str, Path]:
    """Build dossier, compute sha256, optionally write JSON + MD beside it."""
    root = Path(repo_root) if repo_root is not None else _REPO_ROOT
    dossier = build_case_delta_dossier(case, evaluate=True)
    digest = sha256_hex(dossier_hash_payload(dossier))
    path = resolve_dossier_path(case, repo_root=root)
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(dossier)
        payload["sha256"] = digest
        path.write_text(json.dumps(dossier_hash_payload(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        md_path = path.with_suffix(".md")
        md_path.write_text(str(dossier.get("markdown") or ""), encoding="utf-8")
    return dossier, digest, path


def verify_corpus_dossier_hashes(
    corpus: Optional[Dict[str, Any]] = None,
    *,
    path: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    rebuild: bool = False,
) -> Dict[str, Any]:
    """Verify each case's stored sha256 matches the on-disk (or rebuilt) dossier."""
    root = Path(repo_root) if repo_root is not None else _REPO_ROOT
    corp = corpus if corpus is not None else load_process_reference_corpus(path)
    rows: List[Dict[str, Any]] = []
    ok = True
    for case in corp.get("cases", []):
        if not isinstance(case, dict):
            continue
        cid = str(case.get("case_id") or "")
        expected = str((case.get("delta_dossier") or {}).get("sha256") or "")
        dpath = resolve_dossier_path(case, repo_root=root)
        if rebuild or not dpath.exists():
            _, digest, _ = materialize_case_dossier(case, repo_root=root, write=False)
            match = digest == expected
            rows.append(
                {
                    "case_id": cid,
                    "path": str(_repo_relative(dpath, root)),
                    "expected": expected,
                    "actual": digest,
                    "match": match,
                    "source": "rebuild",
                }
            )
            ok = ok and match
            continue
        on_disk = json.loads(dpath.read_text(encoding="utf-8"))
        # Prefer embedded sha256; else hash payload without sha256/markdown
        embedded = str(on_disk.get("sha256") or "")
        payload = {k: v for k, v in on_disk.items() if k not in {"sha256", "markdown"}}
        digest = embedded or sha256_hex(payload)
        # Recompute from payload for integrity
        recomputed = sha256_hex(payload)
        match = (expected == recomputed) and (not embedded or embedded == recomputed)
        rows.append(
            {
                "case_id": cid,
                "path": str(_repo_relative(dpath, root)),
                "expected": expected,
                "actual": recomputed,
                "match": match,
                "source": "disk",
            }
        )
        ok = ok and match
    return {"ok": ok, "cases": rows}


def refresh_corpus_hashes(
    *,
    corpus_path: Optional[Path] = None,
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Rebuild dossiers on disk and rewrite corpus delta_dossier.sha256 fields."""
    root = Path(repo_root) if repo_root is not None else _REPO_ROOT
    cpath = Path(corpus_path) if corpus_path is not None else DEFAULT_CORPUS_PATH
    corp = load_process_reference_corpus(cpath)
    updated_cases: List[Dict[str, Any]] = []
    for case in corp.get("cases", []):
        if not isinstance(case, dict):
            continue
        c = dict(case)
        _, digest, path = materialize_case_dossier(c, repo_root=root, write=True)
        rel = str(_repo_relative(path, root)).replace("\\", "/")
        c["delta_dossier"] = {"path": rel, "sha256": digest}
        updated_cases.append(c)
    corp["cases"] = updated_cases
    corp["schema_version"] = SCHEMA_V2
    if "corpus_status" not in corp:
        # Prefer METHOD-ONLY if any case is METHOD-ONLY
        statuses = {str(c.get("dossier_status") or "") for c in updated_cases}
        corp["corpus_status"] = "NUMERIC" if statuses == {"NUMERIC"} else "METHOD-ONLY"
    cpath.write_text(json.dumps(corp, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return corp
