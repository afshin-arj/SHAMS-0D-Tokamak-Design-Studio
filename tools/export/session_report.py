from __future__ import annotations
"""Session Report Export (v99)

Creates a single zip containing:
- run_ledger.json (full session history)
- pinned/ (payloads for pinned runs)
- diffs/ (field-path diffs for each pinned pair; best-effort)
- exports/ (optional: unified bundle bytes if provided)

Designed for offline journal/regulator packages.
"""
import io, json, zipfile, itertools, time, hashlib
from typing import Any, Dict, List, Optional

def _json_diff_paths(a: Any, b: Any, path: str = "") -> List[str]:
    diffs: List[str] = []
    if type(a) != type(b):
        diffs.append(path or "<root>")
        return diffs
    if isinstance(a, dict):
        keys = set(a.keys()) | set(b.keys())
        for k in sorted(keys):
            diffs += _json_diff_paths(a.get(k, "<missing>"), b.get(k, "<missing>"), (path + "/" + str(k)) if path else "/" + str(k))
        return diffs
    if isinstance(a, list):
        n = max(len(a), len(b))
        for i in range(n):
            aa = a[i] if i < len(a) else "<missing>"
            bb = b[i] if i < len(b) else "<missing>"
            diffs += _json_diff_paths(aa, bb, f"{path}[{i}]")
        return diffs
    if a != b:
        diffs.append(path or "<root>")
    return diffs

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def build_session_report_zip(
    version: str,
    run_history: List[Dict[str, Any]],
    pinned_ids: List[str],
    unified_export_bundle_bytes: Optional[bytes] = None,
) -> bytes:
    buf = io.BytesIO()
    created_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # map runs
    run_map = {r.get("id"): r for r in (run_history or []) if isinstance(r, dict) and r.get("id")}
    pinned_runs = [run_map[i] for i in pinned_ids if i in run_map]

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # ledger
        ledger = {
            "kind": "shams_session_report",
            "version": version,
            "created_utc": created_utc,
            "run_count": len(run_history or []),
            "pinned_count": len(pinned_runs),
            "pinned_ids": pinned_ids,
            "run_history": run_history or [],
        }
        z.writestr("run_ledger.json", json.dumps(ledger, indent=2, sort_keys=True))

        # pinned payloads
        for r in pinned_runs:
            rid = r.get("id", "run")
            payload = r.get("payload", {})
            z.writestr(f"pinned/{rid}.json", json.dumps(payload, indent=2, sort_keys=True))

        # diffs between pinned pairs
        for a, b in itertools.combinations(pinned_runs, 2):
            aid, bid = a.get("id","A"), b.get("id","B")
            diffs = _json_diff_paths(a.get("payload",{}), b.get("payload",{}))
            z.writestr(f"diffs/{aid}__VS__{bid}.txt", "\n".join(diffs[:2000]))

        # include unified export bundle if provided
        if isinstance(unified_export_bundle_bytes, (bytes, bytearray)) and len(unified_export_bundle_bytes) > 0:
            z.writestr("exports/shams_export_bundle.zip", bytes(unified_export_bundle_bytes))
            z.writestr("exports/shams_export_bundle.sha256", _sha256_bytes(bytes(unified_export_bundle_bytes)))

        z.writestr("README.txt", "SHAMS Session Report (v99)\nIncludes run ledger + pinned runs + diffs.\n")
    return buf.getvalue()
