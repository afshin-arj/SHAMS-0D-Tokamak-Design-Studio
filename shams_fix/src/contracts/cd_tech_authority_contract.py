from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple
import hashlib
import json


def _canon(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): _canon(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_canon(v) for v in x]
    if isinstance(x, float):
        # canonical float (avoid 1e-08 vs 0.00000001 diffs)
        if x != x:
            return "NaN"
        if x == float("inf"):
            return "Inf"
        if x == float("-inf"):
            return "-Inf"
        return float(f"{x:.16g}")
    return x


def _sha256_of_canon_json(obj: Any) -> str:
    canon = _canon(obj)
    payload = json.dumps(canon, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class CDTechAuthorityContract:
    schema_version: str
    contract_id: str
    authority: str
    fragile_margin_frac: float
    tech_regimes: Dict[str, Dict[str, Any]]
    required_terms: Tuple[str, ...]
    notes: str = ""


def load_cd_tech_authority_contract(repo_root: Path) -> Tuple[CDTechAuthorityContract, str]:
    path = Path(repo_root) / "contracts" / "cd_tech_authority_contract.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    sha = _sha256_of_canon_json(data)

    return (
        CDTechAuthorityContract(
            schema_version=str(data.get("schema_version", "1.0")),
            contract_id=str(data.get("contract_id", "cd_tech_authority_contract")),
            authority=str(data.get("authority", "CURRENT_DRIVE_TECH")),
            fragile_margin_frac=float(data.get("fragile_margin_frac", 0.05)),
            tech_regimes=dict(data.get("tech_regimes", {}) or {}),
            required_terms=tuple(str(x) for x in (data.get("required_terms", []) or [])),
            notes=str(data.get("notes", "") or ""),
        ),
        sha,
    )
