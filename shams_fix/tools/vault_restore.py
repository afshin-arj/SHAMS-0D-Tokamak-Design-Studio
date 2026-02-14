from __future__ import annotations
"""Vault Restore + Replay (v131)

Loads entries from out_run_vault and extracts stored payloads and attachments.
Does not evaluate physics/solvers; purely IO + integration with UI ledger.

Entry layout comes from tools.run_vault.
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import json

def _vault_root(repo_root: Path) -> Path:
    return repo_root / "out_run_vault"

def list_entries(repo_root: Path, limit: int = 50) -> List[Dict[str, Any]]:
    idx = _vault_root(repo_root) / "INDEX.jsonl"
    if not idx.exists():
        return []
    lines = idx.read_text(encoding="utf-8", errors="replace").splitlines()
    out=[]
    for ln in reversed(lines[-max(1,limit):]):
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out

def _entry_dir(repo_root: Path, entry_dir: str) -> Path:
    # entry_dir stored relative to vault root (entries/...)
    return _vault_root(repo_root) / entry_dir

def load_entry_payload(repo_root: Path, entry_meta: Dict[str, Any]) -> Any:
    entry_dir = str(entry_meta.get("entry_dir") or "")
    if not entry_dir:
        raise ValueError("entry_meta missing entry_dir")
    d = _entry_dir(repo_root, entry_dir)
    pj = d / "payload.json"
    pb = d / "payload.bin"
    pt = d / "payload.txt"
    if pj.exists():
        return json.loads(pj.read_text(encoding="utf-8"))
    if pb.exists():
        return pb.read_bytes()
    if pt.exists():
        return pt.read_text(encoding="utf-8", errors="replace")
    raise FileNotFoundError("payload.* not found for entry")

def list_entry_files(repo_root: Path, entry_meta: Dict[str, Any]) -> List[str]:
    entry_dir = str(entry_meta.get("entry_dir") or "")
    d = _entry_dir(repo_root, entry_dir)
    fdir = d / "files"
    if not fdir.exists():
        return []
    return [p.name for p in sorted(fdir.glob("*")) if p.is_file()]

def read_entry_file(repo_root: Path, entry_meta: Dict[str, Any], filename: str) -> bytes:
    entry_dir = str(entry_meta.get("entry_dir") or "")
    d = _entry_dir(repo_root, entry_dir)
    f = d / "files" / Path(filename).name
    if not f.exists():
        raise FileNotFoundError(filename)
    return f.read_bytes()
