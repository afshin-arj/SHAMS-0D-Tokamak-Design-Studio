"""Pareto Lab — Interpret & Audit tab."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.lib.pareto_helpers import FOCUS_METRIC_KEYS, metric_label
from ui_nicegui.lib.pareto_interpret_helpers import (
    detect_free_lunch_steps,
    enrich_pareto_front,
    explain_segment,
    explain_why_not,
    interaction_matrix,
    knee_candidates,
    objective_relevance_table,
    objective_sanity_warnings,
    policy_filter_front,
    possible_next_questions,
    redundancy_pairs,
    sampling_honesty,
    scan_lab_focus,
    systems_mode_handoff,
    trade_narrative,
    v351_empty_region_report,
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
    bounds = pareto_last.get("bounds") or {}
    x_key = session.pareto_plot_x or (obj_keys[0] if obj_keys else "R0_m")
    y_key = session.pareto_plot_y or (obj_keys[1] if len(obj_keys) > 1 else "P_e_net_MW")
    thr = float(pareto_last.get("robust_margin_thr") or session.pareto_robust_margin_thr or 0.1)

    enriched = pareto_last.get("pareto_enriched")
    if not isinstance(enriched, list) or not enriched:
        enriched = enrich_pareto_front(pareto, feasible, x_key=x_key, y_key=y_key, robust_margin_thr=thr)
        pareto_last["pareto_enriched"] = enriched

    ui.label("Trade-off audit").classes("text-subtitle2")
    ui.markdown(trade_narrative(pareto_last)).classes("text-caption")

    for q in possible_next_questions(pareto_last):
        ui.label(f"→ {q}").classes("text-caption text-grey")

    warns = objective_sanity_warnings(
        objectives, str(pareto_last.get("intent_mode") or session.pareto_intent_mode), pareto_last
    )
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
    with ui.expansion("Sampling honesty (coverage / density)", icon="analytics", value=bool(honesty.get("incompleteness_flags"))).classes("w-full"):
        for flag in honesty.get("incompleteness_flags") or []:
            ui.label(flag).classes("text-caption text-orange")
        ui.json(honesty)

    with ui.expansion("Governance parity (Pareto vs Point Designer)", icon="verified", value=session.pareto_teaching_mode).classes("w-full"):
        ui.label(
            f"Feasibility mode: {pareto_last.get('feasibility_mode', 'governance+intent')} — "
            "Pareto feasible = no intent-blocking hard failures on unified governance ledger."
        ).classes("text-caption q-mb-sm")
        if str(pareto_last.get("intent_mode", "")).startswith("Both") and pareto_last.get("pareto_union"):
            ui.label(
                f"Both-intent union Pareto (re-nominated): {len(pareto_last.get('pareto_union') or [])} points"
            ).classes("text-caption text-grey")
        n_gov_only = sum(
            1 for r in (feasible or [])
            if r.get("governance_feasible") is False and r.get("is_feasible") is True
        )
        if n_gov_only:
            ui.label(
                f"{n_gov_only} points are Pareto-feasible under Research intent but not governance-feasible — expected under intent lens."
            ).classes("text-caption text-orange")

    rel = objective_relevance_table(feasible, pareto, obj_keys)
    if rel:
        with ui.expansion("Objective relevance on front", icon="insights").classes("w-full"):
            ui.table(
                columns=[
                    {"name": "objective", "label": "Objective", "field": "objective"},
                    {"name": "relevance", "label": "Relevance", "field": "relevance"},
                    {"name": "std_front", "label": "σ front", "field": "std_front"},
                ],
                rows=rel,
                row_key="objective",
            ).classes("w-full")

    free_lunch = detect_free_lunch_steps(pareto, x_key, y_key, objectives)
    if free_lunch:
        with ui.expansion("No-free-lunch check (projection steps)", icon="warning").classes("w-full"):
            for step in free_lunch[:6]:
                ui.label(step.get("note", "")).classes("text-caption text-orange")

    if feasible and obj_keys:
        try:
            empty_rep = v351_empty_region_report(
                pareto_last.get("all") or feasible,
                x_key=x_key,
                y_key=y_key,
            )
            with ui.expansion("Empty-region diagnostics (slice bins)", icon="grid_off").classes("w-full"):
                ui.json(empty_rep)
        except Exception:
            pass

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

        @ui.refreshable
        def _seg_panel() -> None:
            seg = int(seg_sel.value or 0)
            seg_rows = [p for p in enriched if int(p.get("segment_id", 0)) == seg]
            exp = explain_segment(seg_rows, y_key=y_key, bounds_keys=list(bounds.keys()) if bounds else None)
            ui.markdown(exp.get("narrative", "")).classes("text-body2")
            if seg_rows:
                ui.table(
                    columns=[
                        {"name": "geography", "label": "geo", "field": "geography"},
                        {"name": "dominant_constraint", "label": "dominant", "field": "dominant_constraint", "align": "left"},
                        {"name": "confidence", "label": "conf", "field": "confidence"},
                    ],
                    rows=seg_rows[:15],
                    row_key="geography",
                ).classes("w-full")

        seg_sel.on("update:model-value", lambda: _seg_panel.refresh())
        _seg_panel()

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
        ui.label("Knee region candidates (descriptive — not recommendations)").classes("text-subtitle2 q-mt-md")
        rows = [
            {"rank": i, **{k: p.get(k) for k in obj_keys[:4]}, "knee_score": p.get("knee_score")}
            for i, p in enumerate(knees)
        ]
        ui.table(
            columns=[{"name": "rank", "label": "#", "field": "rank"}, {"name": "knee_score", "label": "score", "field": "knee_score"}]
            + [{"name": k, "label": metric_label(k), "field": k} for k in obj_keys[:4]],
            rows=rows,
            row_key="rank",
        ).classes("w-full")

    if pareto and len(pareto) >= 3:
        with ui.expansion("Pareto timeline (scrub along front)", icon="timeline").classes("w-full q-mt-md"):
            order = sorted(range(len(pareto)), key=lambda i: float(pareto[i].get(x_key) or 0))
            t_idx = ui.slider(min=0, max=len(order) - 1, value=0, step=1).classes("w-full")

            @ui.refreshable
            def _timeline_point() -> None:
                i = order[int(t_idx.value or 0)]
                p = pareto[i]
                ui.label(f"Index {i} · {x_key}={p.get(x_key)} · {y_key}={p.get(y_key)}").classes("text-caption")
                ui.label(f"Dominant: {p.get('dominant_constraint')} · margin {p.get('min_constraint_margin')}").classes("text-caption")

            t_idx.on("update:model-value", lambda: _timeline_point.refresh())
            _timeline_point()

    with ui.expansion("Policy lens (recompute front from feasible set)", icon="filter_alt").classes("w-full q-mt-md"):
        tbr_min = ui.number("TBR min", value=1.0, step=0.05).classes("w-32")
        qdiv_max = ui.number("q_div max [MW/m²]", value=15.0, step=0.5).classes("w-36")
        sigma_max = ui.number("σ_vm max [MPa]", value=600.0, step=10.0).classes("w-36")
        hts_min = ui.number("HTS margin min", value=0.0, step=0.05).classes("w-32")

        def _apply_policy() -> None:
            if len(objectives) < 2:
                ui.notify("Need ≥2 objectives for Pareto recompute", type="warning")
                return
            filtered = policy_filter_front(
                feasible,
                objectives,
                tbr_min=float(tbr_min.value) if tbr_min.value is not None else None,
                qdiv_max=float(qdiv_max.value) if qdiv_max.value is not None else None,
                sigma_max=float(sigma_max.value) if sigma_max.value is not None else None,
                hts_min=float(hts_min.value) if hts_min.value is not None else None,
            )
            ui.notify(
                f"Policy lens: {len(filtered)} Pareto points from {len(feasible)} feasible samples",
                type="info",
            )
            session.pareto_policy_filtered = filtered
            _policy_table.refresh()

        ui.button("Apply policy filter + recompute Pareto", icon="filter_list", on_click=_apply_policy).props("outline q-mb-sm")
        _policy_table(session)

    if pareto:
        with ui.expansion("Point inspector", icon="search", value=session.pareto_teaching_mode).classes("w-full q-mt-md"):
            idx = ui.number("Pareto index", value=0, min=0, max=max(len(pareto) - 1, 0), step=1).classes("w-32")
            focus = [k for k in (session.pareto_focus_metrics or FOCUS_METRIC_KEYS) if k in (pareto[0] or {})]

            @ui.refreshable
            def _inspect() -> None:
                i = int(idx.value or 0)
                if i < 0 or i >= len(pareto):
                    return
                p = pareto[i]
                lines = [f"**Dominant:** {p.get('dominant_constraint')} · margin {p.get('min_constraint_margin')}"]
                for fk in focus:
                    if fk in p:
                        lines.append(f"- {metric_label(fk)}: {p.get(fk)}")
                ui.markdown("\n".join(lines))

                def _scan() -> None:
                    focus = scan_lab_focus(
                        p, bounds, objectives, plot_x=x_key, plot_y=y_key,
                    )
                    session.scan_probe_focus = focus
                    session.scan_cart_x_key = str(focus.get("x_key") or x_key)
                    session.scan_cart_y_key = str(focus.get("y_key") or y_key)
                    session.scan_workflow_step = "2 · Map & Probe"
                    switch_deck("Scan Lab")
                    ui.notify("Opened Scan Lab with Pareto focus.", type="info")

                def _systems() -> None:
                    session.systems_mode_queue = [systems_mode_handoff(p, bounds)]
                    session.systems_workflow_step = "1 · Targets"
                    switch_deck("Systems Mode")
                    ui.notify("Opened Systems Mode with queued inputs.", type="info")

                with ui.row().classes("gap-2 q-mt-sm"):
                    ui.button("Scan Lab focus", icon="map", on_click=_scan).props("flat outline")
                    ui.button("Systems Mode", icon="hub", on_click=_systems).props("flat outline")

            idx.on("update:model-value", lambda: _inspect.refresh())
            _inspect()

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


@ui.refreshable
def _policy_table(session: DesignSession) -> None:
    rows = getattr(session, "pareto_policy_filtered", None)
    if not isinstance(rows, list) or not rows:
        return
    ui.label(f"Policy-recomputed front ({len(rows)} points)").classes("text-caption")
    ui.table(
        columns=[
            {"name": "dominant_constraint", "label": "Dominant", "field": "dominant_constraint"},
            {"name": "TBR", "label": "TBR", "field": "TBR"},
            {"name": "q_div_MW_m2", "label": "q_div", "field": "q_div_MW_m2"},
            {"name": "sigma_vm_MPa", "label": "σ_vm", "field": "sigma_vm_MPa"},
        ],
        rows=rows[:30],
        row_key="dominant_constraint",
    ).classes("w-full")
