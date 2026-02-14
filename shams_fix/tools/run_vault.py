from __future__ import annotations
"""Run Vault (v130)

Persistent, append-only vault for run artifacts and exported bundles.

Design goals:
- Never lose results due to Streamlit reruns or download actions.
- Deterministic storage layout with content hashing.
- Zero effect on physics/solver behavior (storage only).
- Safe by default: creates new entries, never overwrites.

Vault layout (relative to repo root by default):
  out_run_vault/
    INDEX.jsonl
    entries/<YYYYMMDD>/<HHMMSS>__<kind>__<shortsha>/
      meta.json
      payload.json (if JSON-serializable)
      payload.bin  (if bytes)
      files/<name> (optional attachments)

API:
- ensure_vault_dir
- write_entry
- list_entries (reads INDEX.jsonl)
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import json, time, hashlib, os

def _utcstamp() -> Tuple[str,str]:
    t = time.gmtime()
    return time.strftime("%Y%m%d", t), time.strftime("%H%M%S", t)

def _sha256_bytes(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def _json_bytes(obj: Any) -> Optional[bytes]:
    try:
        return json.dumps(obj, indent=2, sort_keys=True).encode("utf-8")
    except Exception:
        return None

def ensure_vault_dir(root: Path) -> Path:
    v = root / "out_run_vault"
    (v / "entries").mkdir(parents=True, exist_ok=True)
    (v / "INDEX.jsonl").touch(exist_ok=True)
    return v

def write_entry(
    *,
    root: Path,
    kind: str,
    payload: Any,
    mode: str = "",
    tags: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, bytes]] = None,
) -> Dict[str, Any]:
    """Append a vault entry. Returns metadata dict."""
    vault = ensure_vault_dir(root)
    ymd, hms = _utcstamp()

    # Determine content hash
    b_json = _json_bytes(payload)
    if b_json is not None:
        sha = _sha256_bytes(b_json)
    elif isinstance(payload, (bytes, bytearray)):
        sha = _sha256_bytes(bytes(payload))
    else:
        sha = _sha256_bytes(repr(payload).encode("utf-8"))

    short = sha[:10]
    safe_kind = "".join(ch for ch in (kind or "run") if ch.isalnum() or ch in ("-","_"))[:64] or "run"
    safe_mode = "".join(ch for ch in (mode or "") if ch.isalnum() or ch in ("-","_"))[:64]
    folder = vault / "entries" / ymd / f"{hms}__{safe_kind}{'__'+safe_mode if safe_mode else ''}__{short}"
    folder.mkdir(parents=True, exist_ok=True)

    meta = {
        "kind": "shams_vault_entry",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ymd": ymd,
        "hms": hms,
        "entry_dir": str(folder.relative_to(vault)),
        "record_kind": kind,
        "mode": mode,
        "sha256": sha,
        "tags": tags or {},
    }
    (folder / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")

    # payload storage
    if b_json is not None:
        (folder / "payload.json").write_bytes(b_json)
    elif isinstance(payload, (bytes, bytearray)):
        (folder / "payload.bin").write_bytes(bytes(payload))
    else:
        (folder / "payload.txt").write_text(repr(payload), encoding="utf-8")

    # attachments
    if files:
        fdir = folder / "files"
        fdir.mkdir(parents=True, exist_ok=True)
        for name, b in files.items():
            # prevent path traversal
            name = name.replace("\\","/").split("/")[-1]
            (fdir / name).write_bytes(b)

    # append index
    with (vault / "INDEX.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(meta, sort_keys=True) + "\n")

    return meta

def list_entries(root: Path, limit: int = 50) -> List[Dict[str, Any]]:
    vault = ensure_vault_dir(root)
    idx = vault / "INDEX.jsonl"
    if not idx.exists():
        return []
    lines = idx.read_text(encoding="utf-8", errors="replace").splitlines()
    out=[]
    for ln in reversed(lines[-max(limit,1):]):
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out
