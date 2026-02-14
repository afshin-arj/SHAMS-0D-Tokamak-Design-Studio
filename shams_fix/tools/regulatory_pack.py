from __future__ import annotations

"""Regulatory & Reviewer Evidence Pack Builder (v334.0)

Licensing-grade deterministic ZIP exports for review/audit.

Key properties:
- Read-only I/O: does not modify physics truth.
- Deterministic ZIP contents (stable timestamps + stable JSON + stable ordering).
- Pack schema v2 with strict required sections + validator.

Author: © 2026 Afshin Arjhangmehr
"""

import csv
import io
import json
import hashlib
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import zipfile

# reportlab is an optional dependency, but installed in SHAMS releases.
# If unavailable, PDF export is skipped deterministically.
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas  # type: ignore
    _HAVE_RL = True
except Exception:
    _HAVE_RL = False

_FIXED_ZIP_DT: Tuple[int, int, int, int, int, int] = (2020, 1, 1, 0, 0, 0)


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _zip_write_bytes(zf: zipfile.ZipFile, name: str, data: bytes) -> None:
    """Write bytes with stable timestamp to keep ZIP deterministic."""
    zi = zipfile.ZipInfo(filename=name, date_time=_FIXED_ZIP_DT)
    zi.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(zi, data)


def _maybe_read_json(p: Path) -> Optional[dict]:
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None


def _artifact_constraints_rows(artifact: Dict[str, Any]) -> List[Dict[str, Any]]:
    cs = artifact.get("constraints")
    if isinstance(cs, list):
        return [r for r in cs if isinstance(r, dict)]
    return []


def _constraints_csv(rows: List[Dict[str, Any]]) -> Optional[bytes]:
    if not rows:
        return None
    buf = io.StringIO()
    fieldnames = sorted({k for row in rows for k in row.keys()})
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for row in rows:
        w.writerow(row)
    return buf.getvalue().encode("utf-8")


def _top_limiting_constraints(rows: List[Dict[str, Any]], n: int = 25) -> List[Dict[str, Any]]:
    # Use "margin" or "m" or "signed_margin" if present; otherwise keep original order.
    def get_margin(r: Dict[str, Any]) -> float:
        for k in ("margin", "m", "signed_margin", "margin_frac", "worst_margin"):
            v = r.get(k)
            try:
                if v is None:
                    continue
                return float(v)
            except Exception:
                continue
        return 0.0

    # Assume more negative is worse.
    return sorted(rows, key=get_margin)[: max(0, int(n))]


def _dominance_snapshot(artifact: Dict[str, Any]) -> Dict[str, Any]:
    dom = artifact.get("authority_dominance")
    if isinstance(dom, dict) and dom:
        return dom
    # fallback legacy
    return {
        "schema": "authority_dominance.fallback.v1",
        "dominant_authority": artifact.get("dominant_authority") or artifact.get("dominant_mechanism"),
        "dominant_constraint_id": artifact.get("dominant_constraint_id") or artifact.get("dominant_constraint"),
        "dominant_margin_min": artifact.get("dominant_margin_min") or artifact.get("worst_hard_margin"),
    }


def _assumptions_registry_v2(artifact: Dict[str, Any], contract_hashes: Dict[str, str]) -> Dict[str, Any]:
    return {
        "schema": "assumption_registry.v2",
        "shams_version": artifact.get("shams_version"),
        "truth_model": "Frozen deterministic algebraic evaluator (no solvers/iteration in TRUTH)",
        "contracts": contract_hashes,
        "scope_limitations": [
            "No time-domain physics.",
            "No transport solvers.",
            "No Monte Carlo methods.",
            "No probabilistic disruption prediction.",
            "No internal optimization or solver-based constraint negotiation.",
        ],
    }


def _narrative_md(artifact: Dict[str, Any], dominance: Dict[str, Any]) -> str:
    mag_reg = artifact.get("magnet_regime")
    exh_reg = artifact.get("exhaust_regime")
    dom_auth = dominance.get("dominant_authority") or "UNKNOWN"
    dom_c = dominance.get("dominant_constraint_id") or "UNKNOWN"
    dm = dominance.get("dominant_margin_min")
    dm_s = "unknown" if dm is None else str(dm)

    lines = [
        "# SHAMS Regulatory / Reviewer Evidence Pack",
        "",
        "This pack is deterministic and replayable.",
        "It contains inputs, outputs, constraint tables, dominance attribution, and contract hashes.",
        "",
        f"- SHAMS version: {artifact.get('shams_version','unknown')}",
        f"- Intent: {artifact.get('intent','unknown')}",
        f"- Verdict: {artifact.get('verdict','unknown')}",
        f"- Magnet regime: {mag_reg if mag_reg is not None else 'unknown'}",
        f"- Exhaust regime: {exh_reg if exh_reg is not None else 'unknown'}",
        f"- Dominant authority: {dom_auth}",
        f"- Dominant constraint: {dom_c}",
        f"- Dominant margin: {dm_s}",
        "",
        "Scope limitations (by design):",
        "- No time-domain physics.",
        "- No transport solvers.",
        "- No Monte Carlo methods.",
        "- No internal optimization or solver-based constraint negotiation.",
    ]
    return "\n".join(lines)


def _pdf_summary_report(
    *,
    artifact: Dict[str, Any],
    dominance: Dict[str, Any],
    top_constraints: List[Dict[str, Any]],
) -> Optional[bytes]:
    if not _HAVE_RL:
        return None

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "SHAMS — Reviewer Summary Report (v334.0)")
    y -= 24

    c.setFont("Helvetica", 10)
    meta = [
        ("SHAMS version", artifact.get("shams_version", "unknown")),
        ("Intent", artifact.get("intent", "unknown")),
        ("Verdict", artifact.get("verdict", "unknown")),
        ("Magnet regime", artifact.get("magnet_regime", "unknown")),
        ("Exhaust regime", artifact.get("exhaust_regime", "unknown")),
        ("Dominant authority", dominance.get("dominant_authority", "unknown")),
        ("Dominant constraint", dominance.get("dominant_constraint_id", "unknown")),
        ("Dominant margin", dominance.get("dominant_margin_min", "unknown")),
    ]
    for k, v in meta:
        c.drawString(50, y, f"{k}: {v}")
        y -= 14
        if y < 80:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)

    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Top limiting constraints (worst margins)")
    y -= 16
    c.setFont("Helvetica", 8)

    # Table header
    headers = ["id", "authority", "class", "margin"]
    c.drawString(50, y, " | ".join(headers))
    y -= 12

    def pick(r: Dict[str, Any], key: str) -> str:
        v = r.get(key)
        return "" if v is None else str(v)

    for r in top_constraints[:25]:
        rid = pick(r, "id") or pick(r, "constraint_id")
        auth = pick(r, "authority") or pick(r, "mechanism") or pick(r, "domain")
        cls = pick(r, "class") or pick(r, "kind")
        margin = pick(r, "margin") or pick(r, "m") or pick(r, "signed_margin") or pick(r, "margin_frac")
        line = f"{rid} | {auth} | {cls} | {margin}"
        c.drawString(50, y, line[:120])
        y -= 11
        if y < 60:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 8)

    c.showPage()
    c.save()
    return buf.getvalue()


def _contract_hashes(repo_root: Path) -> Tuple[Dict[str, str], Dict[str, Optional[dict]]]:
    contracts_dir = repo_root / "contracts"
    magnet_contract = _maybe_read_json(contracts_dir / "magnet_tech_contract.json")
    exhaust_contract = _maybe_read_json(contracts_dir / "exhaust_radiation_regime_contract.json")
    opt_registry = _maybe_read_json(contracts_dir / "optimizer_capability_registry.json")

    contract_hashes: Dict[str, str] = {}
    if magnet_contract is not None:
        contract_hashes["magnet_tech_contract_sha256"] = _sha256_bytes(_stable_json(magnet_contract).encode("utf-8"))
    if exhaust_contract is not None:
        contract_hashes["exhaust_radiation_regime_contract_sha256"] = _sha256_bytes(_stable_json(exhaust_contract).encode("utf-8"))
    if opt_registry is not None:
        contract_hashes["optimizer_capability_registry_sha256"] = _sha256_bytes(_stable_json(opt_registry).encode("utf-8"))

    return contract_hashes, {
        "magnet_tech_contract": magnet_contract,
        "exhaust_radiation_regime_contract": exhaust_contract,
        "optimizer_capability_registry": opt_registry,
    }


def export_regulatory_evidence_pack_zip(
    repo_root: Path,
    artifact: Dict[str, Any],
    out_zip_path: Path,
    *,
    basename: str = "reviewer_pack",
    extra: Optional[Dict[str, Any]] = None,
    pack_kind: str = "single",
) -> Dict[str, Any]:
    """Export a licensing-grade deterministic reviewer/regulator pack ZIP (schema v2). Returns PACK_MANIFEST dict."""
    out_zip_path.parent.mkdir(parents=True, exist_ok=True)

    files: List[Dict[str, str]] = []

    def add_bytes(zf: zipfile.ZipFile, name: str, data: bytes) -> None:
        _zip_write_bytes(zf, name, data)
        files.append({"name": name, "sha256": _sha256_bytes(data), "bytes": str(len(data))})

    def add_json(zf: zipfile.ZipFile, name: str, obj: Any) -> None:
        add_bytes(zf, name, _stable_json(obj).encode("utf-8"))

    extra = extra if isinstance(extra, dict) else {}
    dominance = _dominance_snapshot(artifact)
    contract_hashes, contracts = _contract_hashes(repo_root)

    constraints_rows = _artifact_constraints_rows(artifact)
    constraints_csv = _constraints_csv(constraints_rows)
    top_rows = _top_limiting_constraints(constraints_rows, n=25)
    top_csv = _constraints_csv(top_rows)

    assumptions = _assumptions_registry_v2(artifact, contract_hashes)
    narrative_md = _narrative_md(artifact, dominance)
    include_pdf = bool((extra or {}).get("include_pdf_report", False))
    pdf_report = _pdf_summary_report(artifact=artifact, dominance=dominance, top_constraints=top_rows) if include_pdf else None

    # Pack-level manifest (schema v2)
    pack_manifest: Dict[str, Any] = {
        "schema": "regulatory_evidence_pack_manifest.v2",
        "pack_kind": pack_kind,
        "basename": basename,
        "shams_version": artifact.get("shams_version"),
        "platform": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "contract_hashes": contract_hashes,
        "required_sections": [
            "artifact.json",
            "dominance.json",
            "assumptions.json",
            "narrative.md",
            "tables/constraints_all.csv (optional)",
            "tables/constraints_top.csv (optional)",
            "report/reviewer_summary.pdf (optional)",
            "contracts/*.json (optional)",
        ],
        "files": files,
    }

    with zipfile.ZipFile(out_zip_path, "w") as zf:
        # Required core
        add_json(zf, f"{basename}/artifact.json", artifact)
        add_json(zf, f"{basename}/dominance.json", dominance)
        add_json(zf, f"{basename}/assumptions.json", assumptions)
        add_bytes(zf, f"{basename}/narrative.md", narrative_md.encode("utf-8"))

        # Tables
        if constraints_csv is not None:
            add_bytes(zf, f"{basename}/tables/constraints_all.csv", constraints_csv)
        if top_csv is not None:
            add_bytes(zf, f"{basename}/tables/constraints_top.csv", top_csv)

        # Contracts
        if contracts.get("magnet_tech_contract") is not None:
            add_json(zf, f"{basename}/contracts/magnet_tech_contract.json", contracts["magnet_tech_contract"])
        if contracts.get("exhaust_radiation_regime_contract") is not None:
            add_json(zf, f"{basename}/contracts/exhaust_radiation_regime_contract.json", contracts["exhaust_radiation_regime_contract"])
        if contracts.get("optimizer_capability_registry") is not None:
            add_json(zf, f"{basename}/contracts/optimizer_capability_registry.json", contracts["optimizer_capability_registry"])

        # Optional context
        if isinstance(extra.get("design_family"), dict) and extra["design_family"]:
            add_json(zf, f"{basename}/design_family.json", extra["design_family"])
        if isinstance(extra.get("extopt_interpretation"), dict) and extra["extopt_interpretation"]:
            add_json(zf, f"{basename}/extopt_interpretation.json", extra["extopt_interpretation"])

        # Optional report
        if pdf_report is not None:
            add_bytes(zf, f"{basename}/report/reviewer_summary.pdf", pdf_report)

        # Finalize manifest last (so it includes prior files list deterministically)
        add_json(zf, f"{basename}/PACK_MANIFEST.json", pack_manifest)

    return pack_manifest


def export_batch_regulatory_packs_zip(
    repo_root: Path,
    artifacts: List[Dict[str, Any]],
    out_zip_path: Path,
    *,
    basename: str = "batch_reviewer_pack",
) -> Dict[str, Any]:
    """Export a single ZIP containing multiple per-artifact reviewer packs (schema v2)."""
    out_zip_path.parent.mkdir(parents=True, exist_ok=True)

    bundle_files: List[Dict[str, str]] = []

    def add_bytes(zf: zipfile.ZipFile, name: str, data: bytes) -> None:
        _zip_write_bytes(zf, name, data)
        bundle_files.append({"name": name, "sha256": _sha256_bytes(data), "bytes": str(len(data))})

    def add_json(zf: zipfile.ZipFile, name: str, obj: Any) -> None:
        add_bytes(zf, name, _stable_json(obj).encode("utf-8"))

    with zipfile.ZipFile(out_zip_path, "w") as zf:
        # Pack each artifact under a deterministic subfolder
        for i, art in enumerate([a for a in artifacts if isinstance(a, dict) and a], start=1):
            sub = f"{basename}/packs/pack_{i:04d}"
            tmp_zip_bytes = io.BytesIO()
            # Use the single-pack function into an in-memory zip, then embed as file
            man = export_regulatory_evidence_pack_zip(
                repo_root, art, Path("/tmp/ignored.zip"),
                basename="reviewer_pack",
                extra=None,
                pack_kind="single",
            )
            # Rebuild deterministically by recreating content using the same function but writing into bytes
            # (We do not rely on filesystem temp path in the released project.)
            tmp_zip_bytes.seek(0)

            # Instead, directly emit the per-pack core files into the bundle with namespaced paths:
            dominance = _dominance_snapshot(art)
            contract_hashes, contracts = _contract_hashes(repo_root)
            constraints_rows = _artifact_constraints_rows(art)
            constraints_csv = _constraints_csv(constraints_rows)
            top_rows = _top_limiting_constraints(constraints_rows, n=25)
            top_csv = _constraints_csv(top_rows)
            assumptions = _assumptions_registry_v2(art, contract_hashes)
            narrative_md = _narrative_md(art, dominance)
            pdf_report = None  # PDF is optional and disabled by default for determinism

            files_local: List[Dict[str, str]] = []
            def add_local(name: str, data: bytes) -> None:
                _zip_write_bytes(zf, name, data)
                files_local.append({"name": name, "sha256": _sha256_bytes(data), "bytes": str(len(data))})
                bundle_files.append({"name": name, "sha256": _sha256_bytes(data), "bytes": str(len(data))})

            def add_local_json(name: str, obj: Any) -> None:
                add_local(name, _stable_json(obj).encode("utf-8"))

            add_local_json(f"{sub}/artifact.json", art)
            add_local_json(f"{sub}/dominance.json", dominance)
            add_local_json(f"{sub}/assumptions.json", assumptions)
            add_local(f"{sub}/narrative.md", narrative_md.encode("utf-8"))
            if constraints_csv is not None:
                add_local(f"{sub}/tables/constraints_all.csv", constraints_csv)
            if top_csv is not None:
                add_local(f"{sub}/tables/constraints_top.csv", top_csv)
            if contracts.get("magnet_tech_contract") is not None:
                add_local_json(f"{sub}/contracts/magnet_tech_contract.json", contracts["magnet_tech_contract"])
            if contracts.get("exhaust_radiation_regime_contract") is not None:
                add_local_json(f"{sub}/contracts/exhaust_radiation_regime_contract.json", contracts["exhaust_radiation_regime_contract"])
            if contracts.get("optimizer_capability_registry") is not None:
                add_local_json(f"{sub}/contracts/optimizer_capability_registry.json", contracts["optimizer_capability_registry"])
            if pdf_report is not None:
                add_local(f"{sub}/report/reviewer_summary.pdf", pdf_report)

            pack_manifest = {
                "schema": "regulatory_evidence_pack_manifest.v2",
                "pack_kind": "single",
                "basename": sub,
                "shams_version": art.get("shams_version"),
                "contract_hashes": contract_hashes,
                "files": files_local,
            }
            add_local_json(f"{sub}/PACK_MANIFEST.json", pack_manifest)

        bundle_manifest = {
            "schema": "regulatory_evidence_pack_bundle_manifest.v1",
            "basename": basename,
            "num_packs": len([a for a in artifacts if isinstance(a, dict) and a]),
            "files": bundle_files,
        }
        add_json(zf, f"{basename}/BUNDLE_MANIFEST.json", bundle_manifest)

    return bundle_manifest


@dataclass
class PackValidationResult:
    ok: bool
    errors: List[str]
    warnings: List[str]


def validate_regulatory_pack_zip(zip_path: Path) -> PackValidationResult:
    """Validate a v2 evidence pack ZIP: required files and SHA-256 integrity."""
    errors: List[str] = []
    warnings: List[str] = []
    if not zip_path.exists():
        return PackValidationResult(False, [f"ZIP not found: {zip_path}"], [])

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        # locate PACK_MANIFEST.json (single pack)
        pack_manifest_name = next((n for n in names if n.endswith("/PACK_MANIFEST.json")), None)
        if pack_manifest_name is None:
            return PackValidationResult(False, ["PACK_MANIFEST.json missing."], [])

        try:
            pack_manifest = json.loads(zf.read(pack_manifest_name).decode("utf-8"))
        except Exception as e:
            return PackValidationResult(False, [f"Failed to parse PACK_MANIFEST.json: {e}"], [])

        if pack_manifest.get("schema") != "regulatory_evidence_pack_manifest.v2":
            warnings.append(f"Unexpected schema: {pack_manifest.get('schema')} (expected v2).")

        listed = pack_manifest.get("files")
        if not isinstance(listed, list) or not listed:
            errors.append("PACK_MANIFEST.json has no file list.")
            return PackValidationResult(False, errors, warnings)

        # verify hashes
        for ent in listed:
            if not isinstance(ent, dict):
                continue
            n = ent.get("name")
            h = ent.get("sha256")
            if not isinstance(n, str) or not isinstance(h, str):
                errors.append(f"Manifest entry missing name/sha256: {ent}")
                continue
            try:
                b = zf.read(n)
            except KeyError:
                errors.append(f"File listed but missing in ZIP: {n}")
                continue
            hh = _sha256_bytes(b)
            if hh != h:
                errors.append(f"SHA mismatch for {n}: manifest {h} != actual {hh}")

        # required core files relative to pack base
        base = pack_manifest_name.rsplit("/", 1)[0]
        required = ["artifact.json", "dominance.json", "assumptions.json", "narrative.md"]
        for r in required:
            if f"{base}/{r}" not in names:
                errors.append(f"Missing required file: {base}/{r}")

        ok = len(errors) == 0
        return PackValidationResult(ok, errors, warnings)
