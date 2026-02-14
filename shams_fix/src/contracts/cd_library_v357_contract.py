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
        # canonical float representation
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
class CDLibraryV357Contract:
    contract_id: str
    version: str
    title: str
    author: str
    validity: str
    fragile_margin_frac: float
    regimes: Dict[str, Dict[str, Any]]


def load_cd_library_v357_contract(repo_root: Path) -> Tuple[CDLibraryV357Contract, str]:
    path = Path(repo_root) / "contracts" / "cd_library_v357_contract.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    sha = _sha256_of_canon_json(data)

    return (
        CDLibraryV357Contract(
            contract_id=str(data.get("contract_id", "cd_library_v357_contract")),
            version=str(data.get("version", "v357.0")),
            title=str(data.get("title", "")),
            author=str(data.get("author", "")),
            validity=str(data.get("validity", "")),
            fragile_margin_frac=float(data.get("fragile_margin_frac", 0.05)),
            regimes=dict(data.get("regimes", {}) or {}),
        ),
        sha,
    )
