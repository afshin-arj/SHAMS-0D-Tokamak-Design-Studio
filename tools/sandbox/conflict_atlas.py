from __future__ import annotations

"""Optimization Sandbox — Constraint Conflict Atlas.

Purpose:
- Accumulate *descriptive* evidence of constraint–constraint conflicts across runs.
- No ranking, no recommendations, no truth claims.

Inputs are typically sourced from the vNext Resistance Report (which itself is derived
from frozen-evaluator trace/archive records).
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple


def _pair(a: str, b: str) -> Tuple[str, str]:
    a = str(a)
    b = str(b)
    return (a, b) if a <= b else (b, a)


def new_atlas() -> Dict[str, Any]:
    return {
        "schema": "shams.opt_sandbox.conflict_atlas.v1",
        "pairs": {},  # "A|B" -> {count, sum_strength, max_strength}
        "notes": "Descriptive atlas accumulated from Resistance Reports. Not a decision engine.",
    }


def update_atlas(atlas: Dict[str, Any], resistance_report: Dict[str, Any]) -> Dict[str, Any]:
    """Merge one resistance report into the atlas."""
    if not isinstance(atlas, dict):
        atlas = new_atlas()
    pairs = atlas.setdefault("pairs", {})
    conflicts = (resistance_report or {}).get("conflicts") or []
    if not isinstance(conflicts, list):
        return atlas

    for item in conflicts:
        if not isinstance(item, dict):
            continue
        a = item.get("a") or item.get("constraint_a")
        b = item.get("b") or item.get("constraint_b")
        if not a or not b:
            continue
        strength = item.get("strength")
        try:
            s = float(strength)
        except Exception:
            s = 0.0
        x, y = _pair(str(a), str(b))
        key = f"{x}|{y}"
        rec = pairs.get(key) or {"a": x, "b": y, "count": 0, "sum_strength": 0.0, "max_strength": 0.0}
        rec["count"] = int(rec.get("count", 0)) + 1
        rec["sum_strength"] = float(rec.get("sum_strength", 0.0)) + float(s)
        rec["max_strength"] = max(float(rec.get("max_strength", 0.0)), float(s))
        pairs[key] = rec
    return atlas


def summarize_atlas(atlas: Dict[str, Any], top_n: int = 20) -> List[Dict[str, Any]]:
    pairs = (atlas or {}).get("pairs") or {}
    rows: List[Dict[str, Any]] = []
    for _k, rec in pairs.items():
        if not isinstance(rec, dict):
            continue
        c = int(rec.get("count", 0))
        ss = float(rec.get("sum_strength", 0.0))
        rows.append({
            "a": rec.get("a"),
            "b": rec.get("b"),
            "count": c,
            "avg_strength": (ss / c) if c > 0 else 0.0,
            "max_strength": float(rec.get("max_strength", 0.0)),
        })
    rows.sort(key=lambda r: (r.get("count", 0), r.get("max_strength", 0.0)), reverse=True)
    return rows[: int(top_n)]
