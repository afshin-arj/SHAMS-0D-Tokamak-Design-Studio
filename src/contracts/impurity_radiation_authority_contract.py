"""
SHAMS — Impurity Species & Radiation Partition Authority Contract
Author: © 2026 Afshin Arjhangmehr

Truth-safe: deterministic contract loading + SHA-256 fingerprinting.
No solvers. No iteration.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import hashlib
from typing import Any, Dict


@dataclass(frozen=True)
class ImpurityRadiationAuthorityContract:
    schema_version: str
    contract_id: str
    authority: str
    thresholds: Dict[str, float]
    species_library: Dict[str, Any]
    fragility: Dict[str, float]
    sha256: str


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_impurity_radiation_contract(repo_root: Path) -> ImpurityRadiationAuthorityContract:
    """
    Load contracts/impurity_radiation_authority_contract.json from repo root.
    """
    path = Path(repo_root) / "contracts" / "impurity_radiation_authority_contract.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    sha = _sha256_bytes(_canonical_json_bytes(raw))
    return ImpurityRadiationAuthorityContract(
        schema_version=str(raw.get("schema_version", "1.0")),
        contract_id=str(raw.get("contract_id", "impurity_radiation_authority_contract")),
        authority=str(raw.get("authority", "RADIATION")),
        thresholds=dict(raw.get("thresholds", {})),
        species_library=dict(raw.get("species_library", {})),
        fragility=dict(raw.get("fragility", {})),
        sha256=sha,
    )
