from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .utils import stable_sha256


@dataclass(frozen=True)
class DiskCache:
    """Simple deterministic disk cache.

    Cache keys are SHA256 fingerprints derived from (inputs, intent, evaluator label,
    schema version). The cache is an acceleration feature only; results must be
    identical with cache on/off.
    """

    root: Path

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def key_for(self, payload: Dict[str, Any]) -> str:
        return stable_sha256(payload)

    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        p = self.root / f"{key}.json"
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def put_json(self, key: str, obj: Dict[str, Any]) -> Path:
        p = self.root / f"{key}.json"
        tmp = self.root / f"{key}.tmp"
        tmp.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(p)
        return p
