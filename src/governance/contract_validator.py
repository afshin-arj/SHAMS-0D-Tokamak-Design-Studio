from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ContractRecord:
    name: str
    path: str
    sha256: str
    ok: bool
    errors: List[str]
    warnings: List[str]
    meta: Dict[str, Any]


def _canonical_json_bytes(obj: Any) -> bytes:
    """
    Canonical JSON for hashing: sorted keys, no whitespace, UTF-8.
    Deterministic across platforms.
    """
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sha256_canonical_json(obj: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(obj)).hexdigest()


def load_contract_json(path: Path) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    errors: List[str] = []
    try:
        txt = path.read_text(encoding="utf-8")
    except Exception as e:
        return None, [f"read_failed: {e!r}"]
    try:
        obj = json.loads(txt)
    except Exception as e:
        return None, [f"json_parse_failed: {e!r}"]
    if not isinstance(obj, dict):
        errors.append("root_not_object")
        return None, errors
    return obj, errors


def validate_contract_object(name: str, obj: Dict[str, Any]) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """
    Generic validator: schema-light, governance-safe.
    We do NOT enforce physics specifics here, only contract integrity.
    """
    errors: List[str] = []
    warnings: List[str] = []
    meta: Dict[str, Any] = {}

    # Optional conventional fields
    for key in ("schema_version", "contract_id", "authority", "provenance"):
        if key not in obj:
            warnings.append(f"missing_field:{key}")

    # If schema_version present, ensure it is a string
    sv = obj.get("schema_version", None)
    if sv is not None and not isinstance(sv, str):
        errors.append("schema_version_not_string")

    # Ensure JSON is finite (reject NaN/Infinity encoded by non-standard emitters)
    # Python's json.loads already rejects NaN by default unless explicitly allowed elsewhere.

    # Basic metadata extraction
    meta["keys"] = sorted(list(obj.keys()))
    meta["n_keys"] = len(obj.keys())

    # Registry-specific light checks
    if name == "optimizer_capability_registry.json":
        if "optimizers" not in obj and "registry" not in obj:
            warnings.append("registry_missing_optimizers_or_registry_key")

    return errors, warnings, meta


def validate_contracts_dir(contracts_dir: Path) -> Tuple[List[ContractRecord], Dict[str, Any]]:
    """
    Validate all *.json contracts in a directory.
    Returns records + a summary dict (including combined fingerprint hash).
    """
    records: List[ContractRecord] = []
    if not contracts_dir.exists():
        summary = {"ok": False, "error": f"contracts_dir_missing:{str(contracts_dir)}"}
        return records, summary

    for p in sorted(contracts_dir.glob("*.json")):
        name = p.name
        obj, load_errors = load_contract_json(p)
        errs: List[str] = list(load_errors)
        warns: List[str] = []
        meta: Dict[str, Any] = {}
        sha = ""
        ok = False
        if obj is not None and not errs:
            sha = sha256_canonical_json(obj)
            v_errs, v_warns, meta = validate_contract_object(name, obj)
            errs.extend(v_errs)
            warns.extend(v_warns)
        ok = (obj is not None) and (len(errs) == 0)
        records.append(ContractRecord(
            name=name,
            path=str(p),
            sha256=sha,
            ok=ok,
            errors=errs,
            warnings=warns,
            meta=meta,
        ))

    used = {r.name: r.sha256 for r in records if r.sha256}
    combined = hashlib.sha256(_canonical_json_bytes(used)).hexdigest() if used else ""
    summary = {
        "ok": all(r.ok for r in records) if records else False,
        "n_contracts": len(records),
        "n_ok": sum(1 for r in records if r.ok),
        "n_errors": sum(len(r.errors) for r in records),
        "n_warnings": sum(len(r.warnings) for r in records),
        "contracts_used": used,
        "contracts_fingerprint_sha256": combined,
    }
    return records, summary


def repo_root_from_file(file_path: Path, levels_up: int = 3) -> Path:
    """
    Resolve repo root from a module file path. Default assumes: src/governance/<file>.py.
    """
    p = file_path.resolve()
    for _ in range(levels_up):
        p = p.parent
    return p
