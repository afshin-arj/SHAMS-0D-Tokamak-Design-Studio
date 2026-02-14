"""Bootstrap & Pressure Self-Consistency Authority contract loader.

Deterministic, audit-safe.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Tuple


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_bootstrap_pressure_selfconsistency_contract(repo_root: Path) -> Tuple[Dict[str, Any], str]:
    """Load contract JSON and return (contract_dict, sha256_hex)."""
    p = repo_root / "contracts" / "bootstrap_pressure_selfconsistency_authority_contract.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    sha = hashlib.sha256(_canonical_json_bytes(data)).hexdigest()
    return data, sha
