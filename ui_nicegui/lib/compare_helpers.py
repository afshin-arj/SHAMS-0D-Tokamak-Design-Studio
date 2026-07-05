"""Compare deck helpers (Batch 8)."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

COMPARE_METRICS: List[str] = [
    "Q",
    "Q_DT_eqv",
    "Pfus_total_MW",
    "P_fus_MW",
    "P_e_net_MW",
    "betaN",
    "q95",
    "Bpeak_TF_T",
    "B_peak_T",
    "q_div_MW_m2",
    "neutron_wall_load_MW_m2",
    "COE_proxy_USD_per_MWh",
]


def _pick_output(out: dict, key: str) -> Any:
    if key in out:
        return out.get(key)
    aliases = {
        "Q": ["Q_DT_eqv"],
        "Q_DT_eqv": ["Q"],
        "Pfus_total_MW": ["P_fus_MW"],
        "P_fus_MW": ["Pfus_total_MW"],
        "Bpeak_TF_T": ["B_peak_T"],
        "B_peak_T": ["Bpeak_TF_T"],
    }
    for alt in aliases.get(key, []):
        if alt in out:
            return out.get(alt)
    return float("nan")


def normalize_compare_artifact(art: dict) -> dict:
    if not isinstance(art, dict):
        return {}
    out = dict(art.get("outputs") or {})
    cons = art.get("constraints")
    if (not cons) and out:
        try:
            from ui_nicegui.lib.verdict_core import constraint_table_rows

            cons = [
                {
                    "name": r["name"],
                    "residual": r["residual"],
                    "passed": r["passed"],
                    "value": r["value"],
                    "limit": r["limit"],
                }
                for r in constraint_table_rows(out)
            ]
        except Exception:
            cons = []
    inputs = art.get("inputs") if isinstance(art.get("inputs"), dict) else {}
    ih = art.get("inputs_hash")
    if not ih and inputs:
        ih = hashlib.sha256(
            json.dumps(inputs, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:12]
    return {
        "outputs": out,
        "inputs": inputs,
        "constraints": list(cons or []),
        "inputs_hash": ih,
        "label": art.get("label") or art.get("deck") or "artifact",
    }


def artifact_from_point(session) -> Optional[dict]:
    from ui_nicegui.lib.artifact_access import get_point_artifact_triple

    art, inp, out = get_point_artifact_triple(session)
    if not isinstance(out, dict) or not out:
        return None
    base = dict(art) if isinstance(art, dict) else {}
    base.setdefault("inputs", inp or dict(session.inputs))
    base.setdefault("outputs", out)
    base["label"] = "Point Designer"
    return normalize_compare_artifact(base)


def slot_meta(art: dict, *, label: str) -> dict:
    norm = normalize_compare_artifact(art)
    return {
        "ts_unix": float(time.time()),
        "inputs_hash": str(norm.get("inputs_hash") or ""),
        "label": label,
    }


def metric_diff_rows(art_a: dict, art_b: dict) -> List[Dict[str, Any]]:
    out_a = normalize_compare_artifact(art_a).get("outputs") or {}
    out_b = normalize_compare_artifact(art_b).get("outputs") or {}
    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for k in COMPARE_METRICS:
        if k in seen:
            continue
        a = _pick_output(out_a, k)
        b = _pick_output(out_b, k)
        if a != a and b != b:
            continue
        seen.add(k)
        try:
            da = float(a)
            db = float(b)
            d = db - da
        except (TypeError, ValueError):
            d = ""
        rows.append({"metric": k, "A": a, "B": b, "B-A": d})
    return rows


def constraint_rows(art: dict, *, limit: int = 20) -> List[Dict[str, Any]]:
    cons = normalize_compare_artifact(art).get("constraints") or []
    rows = [c for c in cons if isinstance(c, dict)]
    rows.sort(key=lambda r: float(r.get("residual", float("-inf")) if r.get("residual") == r.get("residual") else -1e30), reverse=True)
    return rows[:limit]


def summarize_comparison(art_a: dict, art_b: dict) -> Dict[str, Any]:
    from ui_nicegui.lib.verdict_core import verdict_summary

    na = normalize_compare_artifact(art_a)
    nb = normalize_compare_artifact(art_b)
    sa = verdict_summary(na.get("outputs") or {})
    sb = verdict_summary(nb.get("outputs") or {})
    diffs = metric_diff_rows(art_a, art_b)
    top_delta = "-"
    top_val = 0.0
    for row in diffs:
        d = row.get("B-A")
        if isinstance(d, (int, float)) and d == d:
            if abs(float(d)) >= abs(top_val):
                top_val = float(d)
                top_delta = f"{row.get('metric')} ({top_val:+.3g})"
    return {
        "loaded": True,
        "verdict_a": sa.get("verdict", "n/a"),
        "verdict_b": sb.get("verdict", "n/a"),
        "dominant_a": sa.get("dominant", "-"),
        "dominant_b": sb.get("dominant", "-"),
        "top_delta": top_delta,
        "n_metrics": len(diffs),
    }


def comparison_markdown(art_a: dict, art_b: dict) -> str:
    rows = metric_diff_rows(art_a, art_b)
    lines = ["# SHAMS Artifact Comparison", "", "## Key metrics", ""]
    lines.append("| metric | A | B | B-A |")
    lines.append("| --- | --- | --- | --- |")
    for r in rows:
        lines.append(f"| {r.get('metric')} | {r.get('A')} | {r.get('B')} | {r.get('B-A')} |")
    lines.extend(["", "## Worst constraints (A)", ""])
    for c in constraint_rows(art_a):
        lines.append(f"- {c.get('name')}: residual={c.get('residual')}")
    lines.extend(["", "## Worst constraints (B)", ""])
    for c in constraint_rows(art_b):
        lines.append(f"- {c.get('name')}: residual={c.get('residual')}")
    return "\n".join(lines)
