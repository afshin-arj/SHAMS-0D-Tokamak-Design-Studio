from __future__ import annotations

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


@dataclass(frozen=True)
class CurrentProfileProxyThresholds:
    fragile_margin_frac: float
    ni_consistency_tol_frac: float
    regimes: Dict[str, Dict[str, float]]
    required_terms: Dict[str, Any]
    repair_map: Dict[str, Any]


def _repo_root_from_here() -> Path:
    # src/contracts/<file>.py -> src/contracts -> src -> repo_root
    return Path(__file__).resolve().parents[2]


def load_current_profile_proxy_contract(repo_root: Path | None = None) -> Tuple[CurrentProfileProxyThresholds, str]:
    rr = repo_root or _repo_root_from_here()
    p = rr / "contracts" / "current_profile_proxy_authority_contract.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    canon = _canonical_json(raw)
    sha = hashlib.sha256(canon.encode("utf-8")).hexdigest()

    glob = raw.get("global", {}) or {}
    thr = CurrentProfileProxyThresholds(
        fragile_margin_frac=float(glob.get("fragile_margin_frac", 0.05)),
        ni_consistency_tol_frac=float(glob.get("ni_consistency_tol_frac", 0.08)),
        regimes=dict(raw.get("regimes", {}) or {}),
        required_terms=dict(raw.get("required_terms", {}) or {}),
        repair_map=dict(raw.get("repair_map", {}) or {}),
    )
    return thr, sha

