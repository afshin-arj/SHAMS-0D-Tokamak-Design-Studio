from __future__ import annotations

"""Licensing Evidence Pack — Tier 2 (v355.0)

This pack is an extension of the reviewer/regulatory pack (v334 schema v2),
adding stronger industrial/governance evidence sections:

- full contract fingerprint registry (all contracts/*.json)
- explicit authority stack audit snapshot
- replay intent payload (intent + inputs if present)
- regime transition report (v353) when available
- certification reports (v352) when present in-session or provided as extra

Key properties (hard requirements):
- Read-only I/O (does not modify physics truth).
- Deterministic ZIP bytes (stable ordering + stable timestamps + stable JSON).
- Strict pack manifest with per-file SHA-256.

Author: © 2026 Afshin Arjhangmehr
"""

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import zipfile


_FIXED_ZIP_DT: Tuple[int, int, int, int, int, int] = (2020, 1, 1, 0, 0, 0)


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _zip_write_bytes(zf: zipfile.ZipFile, name: str, data: bytes) -> None:
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


def _contract_registry(repo_root: Path) -> Dict[str, Any]:
    contracts_dir = repo_root / "contracts"
    reg: List[Dict[str, Any]] = []
    if contracts_dir.exists():
        for p in sorted(contracts_dir.glob("*.json"), key=lambda x: x.name):
            obj = _maybe_read_json(p)
            if obj is None:
                reg.append({"file": p.name, "ok": False})
                continue
            js = _stable_json(obj).encode("utf-8")
            reg.append({
                "file": p.name,
                "ok": True,
                "schema": obj.get("schema"),
                "sha256_stable_json": _sha256_bytes(js),
                "sha256_file_bytes": _sha256_bytes(p.read_bytes()),
            })
    return {"schema": "contract_registry.v1", "contracts": reg}


def _authority_audit_snapshot(artifact: Dict[str, Any], contract_registry: Dict[str, Any]) -> Dict[str, Any]:
    # Collect contract stamp keys in artifact.
    stamps = {}
    for k, v in sorted(artifact.items(), key=lambda kv: kv[0]):
        if isinstance(k, str) and k.endswith("_contract_sha256") and isinstance(v, str) and v:
            stamps[k] = v

    # Dominance snapshot (best-effort)
    dom = artifact.get("authority_dominance")
    if not (isinstance(dom, dict) and dom):
        dom = {
            "dominant_authority": artifact.get("dominant_authority") or artifact.get("dominant_mechanism"),
            "dominant_constraint_id": artifact.get("dominant_constraint_id") or artifact.get("dominant_constraint"),
            "dominant_margin_min": artifact.get("dominant_margin_min") or artifact.get("worst_hard_margin"),
        }

    return {
        "schema": "authority_audit_snapshot.v1",
        "shams_version": artifact.get("shams_version"),
        "verdict": artifact.get("verdict"),
        "dominance": dom,
        "contract_stamps_from_artifact": stamps,
        "contracts_registry_count": len((contract_registry.get("contracts") or [])) if isinstance(contract_registry, dict) else 0,
    }


def _replay_payload(artifact: Dict[str, Any]) -> Dict[str, Any]:
    # Prefer explicit inputs if present, otherwise preserve intent.
    intent = artifact.get("intent")
    inputs = artifact.get("inputs") or artifact.get("point_inputs") or artifact.get("PointInputs")
    out = {"schema": "replay_payload.v1", "intent": intent}
    if isinstance(inputs, dict) and inputs:
        out["inputs"] = inputs
    return out


@dataclass
class PackValidationResult:
    ok: bool
    errors: List[str]
    warnings: List[str]


def export_licensing_evidence_tier2_zip(
    repo_root: Path,
    artifact: Dict[str, Any],
    out_zip_path: Path,
    *,
    basename: str = "licensing_pack_tier2",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Export Tier 2 licensing evidence pack (schema v3). Returns PACK_MANIFEST dict."""

    extra = extra or {}
    contract_reg = _contract_registry(repo_root)
    authority_audit = _authority_audit_snapshot(artifact, contract_reg)
    replay = _replay_payload(artifact)

    regime = artifact.get("regime_transitions")
    if not isinstance(regime, dict):
        # common alternative keys
        regime = artifact.get("regime_labels") if isinstance(artifact.get("regime_labels"), dict) else None

    certification = extra.get("certification") if isinstance(extra.get("certification"), dict) else None

    pack: Dict[str, bytes] = {}
    pack["artifact.json"] = _stable_json(artifact).encode("utf-8")
    pack["contracts/contracts_index.json"] = _stable_json(contract_reg).encode("utf-8")
    pack["governance/authority_audit.json"] = _stable_json(authority_audit).encode("utf-8")
    pack["replay/replay_payload.json"] = _stable_json(replay).encode("utf-8")

    if isinstance(regime, dict):
        pack["analysis/regime_transitions.json"] = _stable_json(regime).encode("utf-8")

    if isinstance(certification, dict):
        pack["certification/robust_envelope_certification.json"] = _stable_json(certification).encode("utf-8")

    # Optional: include repo manifests if present
    for mf in ("MANIFEST_SHA256.txt", "MANIFEST_UPGRADE_SHA256.txt"):
        p = repo_root / mf
        if p.exists():
            pack[f"repo/{mf}"] = p.read_bytes()

    # Optional: include README + VERSION
    for fn in ("README.md", "VERSION", "VERSION.txt", "RELEASE_NOTES.md"):
        p = repo_root / fn
        if p.exists():
            pack[f"repo/{fn}"] = p.read_bytes()

    # Build PACK_MANIFEST schema v3
    files = []
    for name in sorted(pack.keys()):
        files.append({"path": name, "sha256": _sha256_bytes(pack[name])})

    pack_manifest = {
        "schema": "licensing_evidence_pack.v3",
        "kind": "tier2",
        "basename": basename,
        "shams_version": artifact.get("shams_version"),
        "verdict": artifact.get("verdict"),
        "files": files,
    }
    pack["PACK_MANIFEST.json"] = _stable_json(pack_manifest).encode("utf-8")

    out_zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip_path, "w") as zf:
        for name in sorted(pack.keys()):
            _zip_write_bytes(zf, name, pack[name])

    return pack_manifest


def validate_licensing_pack_tier2_zip(zip_path: Path) -> PackValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    if not zip_path.exists():
        return PackValidationResult(ok=False, errors=["ZIP does not exist"], warnings=[])

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = set(zf.namelist())
            if "PACK_MANIFEST.json" not in names:
                errors.append("Missing PACK_MANIFEST.json")
                return PackValidationResult(ok=False, errors=errors, warnings=warnings)

            man = json.loads(zf.read("PACK_MANIFEST.json").decode("utf-8"))
            if str(man.get("schema")) != "licensing_evidence_pack.v3":
                errors.append("PACK_MANIFEST schema mismatch")

            files = man.get("files")
            if not isinstance(files, list) or not files:
                errors.append("PACK_MANIFEST missing files list")
                files = []

            # Verify per-file SHA
            for rec in files:
                if not isinstance(rec, dict):
                    continue
                p = rec.get("path")
                s = rec.get("sha256")
                if not isinstance(p, str) or not isinstance(s, str):
                    continue
                if p not in names:
                    errors.append(f"Missing file listed in manifest: {p}")
                    continue
                b = zf.read(p)
                if _sha256_bytes(b) != s:
                    errors.append(f"SHA mismatch: {p}")

            # Required sections
            for req in (
                "artifact.json",
                "contracts/contracts_index.json",
                "governance/authority_audit.json",
                "replay/replay_payload.json",
            ):
                if req not in names:
                    errors.append(f"Missing required section: {req}")

    except Exception as e:
        errors.append(f"Failed to read ZIP: {e}")

    return PackValidationResult(ok=(len(errors) == 0), errors=errors, warnings=warnings)
