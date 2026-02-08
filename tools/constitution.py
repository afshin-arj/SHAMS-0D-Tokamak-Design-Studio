from __future__ import annotations
"""Constitution tools (v120)

Produces an integrity manifest for constitutional documents and registry.
Additive only; no physics/solver impact.
"""
from typing import Dict, Any, List
from pathlib import Path
import time, hashlib, json

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

CONSTITUTION_FILES = [
    "ARCHITECTURE.md",
    "GOVERNANCE.md",
    "LAYER_MODEL.md",
    "NON_OPTIMIZER_MANIFESTO.md",
    "CITATION.cff",
    "ui/layer_registry.py",
]

def build_constitution_manifest(repo_root: str = ".", version: str = "v120") -> Dict[str, Any]:
    root = Path(repo_root)
    files: Dict[str, Dict[str, Any]] = {}
    for rel in CONSTITUTION_FILES:
        p = root / rel
        if p.exists():
            b = p.read_bytes()
            files[rel] = {"sha256": _sha256_bytes(b), "bytes": len(b)}
        else:
            files[rel] = {"missing": True}
    return {
        "kind":"shams_constitution_manifest",
        "version": version,
        "created_utc": _created_utc(),
        "files": files,
        "notes":[
            "Constitutional release integrity manifest.",
            "Files listed here define the layer rules and governance.",
        ],
    }
