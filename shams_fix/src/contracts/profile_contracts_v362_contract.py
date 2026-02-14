from __future__ import annotations

"""Profile Contracts 2.0 (v362.0) contract loader.

Loads a deterministic JSON contract that defines optimistic/robust envelopes over
profile-family knobs (v358).

This is a *governance-only* contract:
- it does not change frozen truth
- it only parameterizes a finite corner evaluation procedure

© 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple
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
            return "Infinity" if x > 0 else "-Infinity"
        return repr(float(x))
    if x is None or isinstance(x, (bool, int, str)):
        return x
    try:
        if hasattr(x, "item"):
            return _canon(x.item())
    except Exception:
        pass
    return str(x)


def _canonical_json(obj: Any) -> str:
    canon = _canon(obj)
    return json.dumps(canon, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _repo_root_from_here() -> Path:
    # src/contracts/<file>.py -> src/contracts -> src -> repo_root
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ProfileContractsV362:
    schema_version: str
    presets: Dict[str, Any]
    axes: Dict[str, Any]
    notes: str = ""


def load_profile_contracts_v362(repo_root: Path | None = None) -> Tuple[ProfileContractsV362, str]:
    rr = repo_root or _repo_root_from_here()
    p = rr / "contracts" / "profile_contracts_v362_contract.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    canon = _canonical_json(raw)
    sha = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    con = ProfileContractsV362(
        schema_version=str(raw.get("schema_version", "profile_contracts.v362")),
        presets=dict(raw.get("presets", {}) or {}),
        axes=dict(raw.get("axes", {}) or {}),
        notes=str(raw.get("notes", "")),
    )
    return con, sha
