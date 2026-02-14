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
            return 'NaN'
        if math.isinf(x):
            return 'Infinity' if x > 0 else '-Infinity'
        return repr(float(x))
    if x is None or isinstance(x, (bool, int, str)):
        return x
    try:
        if hasattr(x, 'item'):
            return _canon(x.item())
    except Exception:
        pass
    return str(x)


def _canonical_json(obj: Any) -> str:
    canon = _canon(obj)
    return json.dumps(canon, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


@dataclass(frozen=True)
class ControlStabilityContract:
    data: Dict[str, Any]
    sha256: str


def load_control_stability_contract(repo_root: str | Path) -> ControlStabilityContract:
    repo_root = Path(repo_root)
    p = repo_root / 'contracts' / 'control_stability_authority_contract.json'
    data = json.loads(p.read_text(encoding='utf-8'))
    canon = _canonical_json(data)
    sha = hashlib.sha256(canon.encode('utf-8')).hexdigest()
    return ControlStabilityContract(data=data, sha256=sha)


def contract_defaults(contract: ControlStabilityContract) -> Dict[str, Any]:
    d = contract.data.get('defaults')
    return d if isinstance(d, dict) else {}
