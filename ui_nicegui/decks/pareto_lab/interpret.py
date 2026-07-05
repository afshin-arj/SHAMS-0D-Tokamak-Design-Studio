"""Pareto Lab — Interpret & Audit tab."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.lib.pareto_interpret_helpers import (
    enrich_pareto_front,
    explain_why_not,
    interaction_matrix,
    knee_candidates,
    objective_sanity_warnings,
    redundancy_pairs,
    sampling_honesty,
    trade_narrative,
)
from ui_nicegui.session import DesignSession


def render_interpret_tab(
    session: DesignSession,
    pareto_last: dict,
    *,
    on_update: Optional[Callable[[], None]] = None,
) -> None:
    pareto = pareto_last.get("pareto") or []
    feasible = pareto_last.get("feasible") or []
    objectives = pareto_last.get("objectives") or {}
    obj_keys = list(objectives.keys()) if isinstance(objectives, dict) else []
    summary = pareto_last.get("summary") or {}
    x_key = session.pareto_plot_x or (obj_keys[0] if obj_keys else "R0_m")
    y_key = session.pareto_plot_y or (obj_keys[1] if len(obj_keys) > 1 else "P_e_net_MW")
    thr = float(pareto_last.get("robust_margin_thr") or session.pareto_robust_margin_thr or 0.1)

    enriched = pareto_last.get("pareto_enriched")
    if not isinstance(enriched, list) or not enriched:
        enriched = enrich_pareto_front(pareto, feasible, x_key=x_key, y_key=y_key, robust_margin_thr=thr)
        pareto_last["pareto_enriched"] = enriched

    ui.label("Trade-off audit").classes("text-subtitle2")
    ui.markdown(trade_narrative(pareto_last)).classes("text-caption")

    warns = objective_sanity_warnings(objectives, str(pareto_last.get("intent_mode") or session.pareto_intent_mode))
    with ui.expansion("Objective sanity (warnings only)", icon="rule", value=bool(warns)).classes("w-full"):
        if warns:
            for w in warns:
                ui.label(w).classes("text-caption text-orange")
        else:
            ui.label("No obvious objective-contract red flags.").classes("text-caption text-positive")

    why = explain_why_not(pareto_last)
    if why.get("messages") or why.get("failure_counts"):
        with ui.expansion("Explain why not (empty feasible / empty front)", icon="help").classes("w-full"):
            for msg in why.get("messages") or []:
                ui.label(msg).classes("text-caption text-orange")
            for name, n in why.get("failure_counts") or []:
                ui.label(f"{name}: {n} samples").classes("text-caption")

    honesty = sampling_honesty(pareto_last)
    with ui.expansion("Sampling honesty (coverage / density)", icon="analytics").classes("w-full"):
        ui.json(honesty)

    with ui.expansion("Self-audit checklist", icon="fact_check", value=session.pareto_teaching_mode).classes("w-full"):
        checks = [
            ("≥2 objectives declared", len(obj_keys) >= 2),
            ("Feasible samples exist", len(feasible) > 0),
            ("Non-dominated front produced", len(pareto) > 0),
            ("Intent mode recorded", bool(pareto_last.get("intent_mode"))),
            ("Seed recorded (replayable)", pareto_last.get("seed") is not None),
        ]
        for label, ok in checks:
            ui.label(f"{'✓' if ok else '✗'} {label}").classes(
                "text-caption" + (" text-positive" if ok else " text-orange")
            )

    if enriched:
        ui.label("Frontier annotations (segment · geography · confidence)").classes("text-subtitle2 q-mt-md")
        seg_ids = sorted({int(p.get("segment_id", 0)) for p in enriched})
        seg_sel = ui.select([str(s) for s in seg_ids], label="Explain front segment", value=str(seg_ids[0])).classes("w-full")
        seg = int(seg_sel.value or 0)
        seg_rows = [p for p in enriched if int(p.get("segment_id", 0)) == seg][:20]
        if seg_rows:
            ui.table(
                columns=[
                    {"name": "segment_id", "label": "seg", "field": "segment_id"},
                    {"name": "geography", "label": "geo", "field": "geography"},
                    {"name": "freedom_left", "label": "freedom", "field": "freedom_left"},
                    {"name": "dominant_constraint", "label": "dominant", "field": "dominant_constraint", "align": "left"},
                    {"name": "confidence", "label": "conf", "field": "confidence"},
                ],
                rows=seg_rows,
                row_key="segment_id",
            ).classes("w-full")

    if len(obj_keys) >= 2 and feasible:
        keys, mat_rows = interaction_matrix(feasible, obj_keys)
        ui.label("Objective interaction matrix").classes("text-subtitle2 q-mt-md")
        if mat_rows:
            ui.table(
                columns=[{"name": k, "label": k, "field": k} for k in ["objective"] + keys],
                rows=mat_rows,
                row_key="objective",
            ).classes("w-full")
        redundant = redundancy_pairs(feasible, obj_keys)
        if redundant:
            with ui.expansion("Redundant objective pairs (|ρ| ≥ 0.92)", icon="warning").classes("w-full"):
                for a, b, v in redundant:
                    ui.label(f"{a} ↔ {b}: ρ = {v:.2f}").classes("text-caption")

    knees = knee_candidates(pareto, x_key, y_key)
    if knees:
        ui.label("Knee region candidates").classes("text-subtitle2 q-mt-md")
        rows = [
            {"rank": i, **{k: p.get(k) for k in obj_keys[:4]}, "knee_score": p.get("knee_score")}
            for i, p in enumerate(knees)
        ]
        ui.table(
            columns=[{"name": "rank", "label": "#", "field": "rank"}, {"name": "knee_score", "label": "score", "field": "knee_score"}]
            + [{"name": k, "label": k, "field": k} for k in obj_keys[:4]],
            rows=rows,
            row_key="rank",
        ).classes("w-full")

    ui.separator().classes("q-my-sm")
    ui.label("Run metadata").classes("text-subtitle2")
    ui.json({
        "intent_mode": pareto_last.get("intent_mode"),
        "n_samples": pareto_last.get("n_samples"),
        "seed": pareto_last.get("seed"),
        "robust_margin_thr": pareto_last.get("robust_margin_thr"),
        "top_constraint": summary.get("top_constraint"),
        "confidence": summary.get("confidence"),
    })
