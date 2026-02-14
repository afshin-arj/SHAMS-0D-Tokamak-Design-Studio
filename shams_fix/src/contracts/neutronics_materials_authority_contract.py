from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
import hashlib
import json
import math


def _canon(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): _canon(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_canon(v) for v in x]
    if isinstance(x, float):
        if math.isnan(x):
            return "NaN"
        if math.isinf(x):
            return "Inf" if x > 0 else "-Inf"
    return x


def _sha256_of_canon_json(d: Dict[str, Any]) -> str:
    blob = json.dumps(_canon(d), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


@dataclass(frozen=True)
class NeutronicsMaterialsContract:
    data: Dict[str, Any]
    sha256: str

    @property
    def limits(self) -> Dict[str, float]:
        return {str(k): float(v) for k, v in (self.data.get("limits") or {}).items()}

    @property
    def fragile_margin_frac(self) -> float:
        return float((self.data.get("fragility") or {}).get("fragile_margin_frac", 0.10))


def load_neutronics_materials_contract(repo_root: Path) -> NeutronicsMaterialsContract:
    p = repo_root / "contracts" / "neutronics_materials_authority_contract.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    sha = _sha256_of_canon_json(data)
    return NeutronicsMaterialsContract(data=data, sha256=sha)
