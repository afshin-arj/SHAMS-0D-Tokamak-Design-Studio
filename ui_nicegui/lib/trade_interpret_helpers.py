"""Trade Study interpretability — narratives, blocking, capsule restore."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def blocking_constraints(records: list, *, top_k: int = 8) -> List[tuple[str, int]]:
    counts: dict[str, int] = {}
    for row in records:
        if row.get("is_feasible"):
            continue
        dom = str(row.get("dominant_constraint") or "(unknown)")
        counts[dom] = counts.get(dom, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])[:top_k]


def study_narrative(rep: dict) -> str:
    summary = rep.get("summary") or {}
    meta = rep.get("meta") or {}
    objs = meta.get("objectives") or summary.get("objectives") or []
    lines = [
        "# Trade study summary",
        "",
        f"- Samples: {summary.get('n_samples', '-')} · Feasible: {summary.get('n_feasible', '-')} · Pareto: {summary.get('n_pareto', '-')}",
        f"- Feasible fraction: {100.0 * float(summary.get('feasible_fraction', 0.0)):.1f}%",
        f"- Confidence: {summary.get('confidence', '-')}",
        f"- Knob set: {summary.get('knob_set', rep.get('knob_set_name', '-'))}",
        f"- Objectives: {', '.join(objs) if objs else '-'}",
        f"- Seed: {summary.get('seed', meta.get('seed', '-'))}",
        "",
        "Budgeted LHS over declared knobs — descriptive trade-off slice, not a design recommendation.",
    ]
    return "\n".join(lines)


def restore_study_capsule(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Invalid capsule")
    if payload.get("schema") != "shams.study_capsule.v1" and "records" not in payload:
        raise ValueError("Not a study capsule")
    from ui_nicegui.lib.trade_study_helpers import summarize_trade_study

    rep = {
        "meta": dict(payload.get("meta") or {}),
        "records": list(payload.get("records") or []),
        "feasible": list(payload.get("feasible") or []),
        "pareto": list(payload.get("pareto") or []),
        "knob_set_name": (payload.get("knob_set") or {}).get("name"),
    }
    rep["summary"] = summarize_trade_study(rep)
    return rep


def promote_row(session, row: dict, bound_keys: list[str]) -> None:
    for k in bound_keys:
        if k in row and row[k] is not None:
            try:
                session.inputs[k] = float(row[k])
            except (TypeError, ValueError):
                pass


def capsule_from_restore(payload: dict) -> dict:
    if payload.get("schema") == "shams.study_capsule.v1":
        return dict(payload)
    return {
        "schema": "shams.study_capsule.v1",
        "meta": payload.get("meta") or {},
        "knob_set": {"name": payload.get("knob_set_name"), "bounds": (payload.get("meta") or {}).get("bounds", {})},
        "objectives": (payload.get("meta") or {}).get("objectives") or [],
        "objective_senses": (payload.get("meta") or {}).get("objective_senses") or {},
        "records": payload.get("records") or [],
        "feasible": payload.get("feasible") or [],
        "pareto": payload.get("pareto") or [],
    }
