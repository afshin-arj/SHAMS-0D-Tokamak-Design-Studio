"""
NI Closure Authority Contract loader (deterministic, audit-safe)

Author: © 2026 Afshin Arjhangmehr
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import hashlib
from typing import Any, Dict, Tuple

def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def load_ni_closure_authority_contract(repo_root: Path) -> Tuple[Dict[str, Any], str]:
    """
    Load contracts/ni_closure_authority_contract.json and return (contract_dict, sha256_hex).
    Never mutates input; deterministic bytes via canonical JSON encoding.
    """
    p = repo_root / "contracts" / "ni_closure_authority_contract.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    h = hashlib.sha256(_canonical_json_bytes(data)).hexdigest()
    return data, h
