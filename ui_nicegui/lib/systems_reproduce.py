"""Reproduce, diff, and regression helpers for Systems run history."""

from __future__ import annotations

import json
import time
from typing import Any, List


def json_structural_diff(a: Any, b: Any, path: str = "") -> List[str]:
    diffs: List[str] = []
    if type(a) != type(b):
        diffs.append(path or "<root>")
        return diffs
    if isinstance(a, dict):
        keys = set(a.keys()) | set(b.keys())
        for k in sorted(keys):
            p = f"{path}/{k}" if path else f"/{k}"
            diffs.extend(json_structural_diff(a.get(k, "<missing>"), b.get(k, "<missing>"), p))
        return diffs
    if isinstance(a, list):
        n = max(len(a), len(b))
        for i in range(n):
            ai = a[i] if i < len(a) else "<missing>"
            bi = b[i] if i < len(b) else "<missing>"
            diffs.extend(json_structural_diff(ai, bi, f"{path}[{i}]"))
        return diffs
    if a != b:
        diffs.append(path or "<root>")
    return diffs


def systems_run_records(session: Any) -> List[dict]:
    cards = list(getattr(session, "systems_run_cards", None) or [])
    out: List[dict] = []
    for i, rc in enumerate(reversed(cards)):
        if not isinstance(rc, dict):
            continue
        rid = str(rc.get("id") or f"run_{len(cards)-i}")
        ts = rc.get("ts")
        try:
            ts_s = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(ts))) if ts else "-"
        except (TypeError, ValueError, OSError):
            ts_s = str(ts or "-")
        kind = str(rc.get("kind") or "Run")
        mode = str((rc.get("outcome") or {}).get("reason") or "")
        out.append({
            "id": rid,
            "ts": ts_s,
            "kind": kind,
            "mode": mode,
            "payload": rc.get("payload") if isinstance(rc.get("payload"), dict) else {},
            "settings": rc.get("settings") if isinstance(rc.get("settings"), dict) else {},
            "outcome": rc.get("outcome") if isinstance(rc.get("outcome"), dict) else {},
        })
    return out


def regression_json_from_run(run: dict) -> str:
    payload = run.get("payload") if isinstance(run.get("payload"), dict) else {}
    reg = {
        "run_id": run.get("id"),
        "schema_version": payload.get("schema_version"),
        "design_intent": payload.get("design_intent"),
        "inputs_hash": payload.get("inputs_hash"),
        "expected": {
            "ok": payload.get("ok") if isinstance(payload, dict) else (run.get("outcome") or {}).get("ok"),
            "reason": payload.get("reason") if isinstance(payload, dict) else (run.get("outcome") or {}).get("reason"),
        },
    }
    return json.dumps(reg, indent=2, sort_keys=True, default=str)
