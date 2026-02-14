from __future__ import annotations
import json, hashlib, time
from pathlib import Path
from typing import Dict, Any, Optional

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def build_manifest(version: str, export_kind: str, files: Dict[str, Path], inline_bytes: Optional[Dict[str, bytes]] = None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    inline_bytes = inline_bytes or {}
    meta = meta or {}
    out = {
        "kind": "shams_export_manifest",
        "version": version,
        "export_kind": export_kind,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "files": {},
        "inline": {},
        "meta": meta,
    }
    for k, p in files.items():
        if p and p.exists() and p.is_file():
            out["files"][k] = {"path": str(p), "sha256": _sha256_file(p), "bytes": p.stat().st_size}
    for k, b in inline_bytes.items():
        out["inline"][k] = {"sha256": _sha256_bytes(b), "bytes": len(b)}
    return out

def write_manifest_json(manifest: Dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
