"""Scan Lab interpret tab — narratives, local insights, next-tier tools, claims."""
from __future__ import annotations

import json
from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.decks.scan_lab import results
from ui_nicegui.lib.scan_archive_helpers import compute_repo_fingerprints
from ui_nicegui.lib.scan_insight_display import format_causality_trace, format_insight_dict
from ui_nicegui.lib.scan_helpers import SCAN_VAR_KEYS
from ui_nicegui.lib.scan_insights_helpers import (
    LOCAL_INSIGHTS,
    NEXT_TIER_TOOLS,
    build_claim_evidence,
    build_claim_pdf,
    counterfactual,
    explain_impossible,
    falsify_claim,
    guided_walkthrough,
    intent_narrative,
    irrelevant_constraints,
    local_scaling,
    null_direction_from_trace,
    path_follow_scan,
    projection_stability,
    regime_label,
    stress_hotspots,
    surprise_regions,
    time_to_failure,
    topology_alerts,
    uncertainty_stress,
)
from ui_nicegui.lib.scan_workbench_helpers import (
    dominance_map_png_bytes,
    run_causality_trace,
)
from ui_nicegui.session import DesignSession


def render_interpret_tab(
    session: DesignSession,
    rep: dict,
    *,
    on_update: Optional[Callable[[], None]] = None,
) -> None:
    intents = list(rep.get("intents") or session.scan_cart_intents or ["Reactor"])
    if not intents:
        empty_state("Run a cartography scan first.", kind="info")
        return

    ui.label("Landscape summary").classes("text-subtitle1")
    ui.label("Dominance ranking and per-intent narratives from the frozen scan.").classes(
        "text-caption q-mb-sm"
    )
    results.render_scan_results(session, rep)

    for it in intents:
        plain = intent_narrative(rep, str(it))
        alerts = topology_alerts(rep, str(it))
        if plain or alerts:
            with ui.expansion(f"Intent narrative — {it}", icon="article", value=bool(plain)).classes(
                "w-full"
            ):
                if plain:
                    ui.markdown(plain)
                for a in alerts:
                    ui.label(a).classes("text-caption text-orange")

    ui.separator().classes("q-my-md")
    _render_local_insights(session, rep, intents)
    ui.separator().classes("q-my-md")
    _render_next_tier(session, rep, intents)
    ui.separator().classes("q-my-md")
    _render_expert_claims(session, rep, intents)


def _cell_picker(session: DesignSession, rep: dict) -> tuple[int, int]:
    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    session.scan_wb_i = max(0, min(int(session.scan_wb_i), max(0, len(x_vals) - 1)))
    session.scan_wb_j = max(0, min(int(session.scan_wb_j), max(0, len(y_vals) - 1)))
    with ui.row().classes("w-full gap-4"):
        ui.slider(
            min=0,
            max=max(0, len(x_vals) - 1),
            step=1,
            value=session.scan_wb_i,
            on_change=lambda e: setattr(session, "scan_wb_i", int(e.value)),
        ).props("label").classes("flex-1")
        ui.slider(
            min=0,
            max=max(0, len(y_vals) - 1),
            step=1,
            value=session.scan_wb_j,
            on_change=lambda e: setattr(session, "scan_wb_j", int(e.value)),
        ).props("label").classes("flex-1")
    ui.label(
        f"Cell (i,j)=({session.scan_wb_i},{session.scan_wb_j}) · "
        f"x≈{x_vals[session.scan_wb_i] if x_vals else '-'} · "
        f"y≈{y_vals[session.scan_wb_j] if y_vals else '-'}"
    ).classes("text-caption q-mb-sm")
    return session.scan_wb_i, session.scan_wb_j


def _render_local_insights(session: DesignSession, rep: dict, intents: list) -> None:
    ui.label("Local cell insights").classes("text-subtitle1")
    ui.label(
        "Finite-difference and neighborhood tools at the probed cell — not full sensitivity studies."
    ).classes("text-caption q-mb-sm")
    _cell_picker(session, rep)
    if session.scan_local_insight not in LOCAL_INSIGHTS:
        session.scan_local_insight = LOCAL_INSIGHTS[0]
    ui.select(
        LOCAL_INSIGHTS,
        label="Insight",
        value=session.scan_local_insight,
        on_change=lambda e: setattr(session, "scan_local_insight", str(e.value)),
    ).classes("w-full q-mb-sm")
    ui.select(
        intents,
        label="Intent lens",
        value=session.scan_wb_intent if session.scan_wb_intent in intents else intents[0],
        on_change=lambda e: setattr(session, "scan_wb_intent", str(e.value)),
    ).classes("w-full q-mb-sm")

    insight = session.scan_local_insight
    i, j = session.scan_wb_i, session.scan_wb_j
    it = session.scan_wb_intent

    @ui.refreshable
    def _out_panel() -> None:
        pass

    async def _run_local() -> None:
        ui.notify(f"Computing {insight}…", type="info")
        try:
            if insight == "Causality trace":
                tr = await run.io_bound(
                    run_causality_trace,
                    session.build_point_inputs(),
                    rep,
                    intent=str(it),
                    i=i,
                    j=j,
                    rel_step=float(session.scan_causality_rel_step),
                )
                session.scan_causality_last = tr
            elif insight == "Time-to-failure along knob":
                knob = str(rep.get("x_key") or "Ip_MA")
                tr = await run.io_bound(
                    time_to_failure,
                    session.build_point_inputs(),
                    rep,
                    str(it),
                    i,
                    j,
                    knob,
                    float(session.scan_causality_rel_step),
                )
                session.scan_causality_last = tr
            elif insight == "Uncertainty stress-test":
                tr = await run.io_bound(
                    uncertainty_stress,
                    session.build_point_inputs(),
                    rep,
                    str(it),
                    i,
                    j,
                )
                session.scan_causality_last = tr
            elif insight == "Null direction (2D)":
                tr = await run.io_bound(
                    run_causality_trace,
                    session.build_point_inputs(),
                    rep,
                    intent=str(it),
                    i=i,
                    j=j,
                    rel_step=float(session.scan_causality_rel_step),
                )
                session.scan_causality_last = null_direction_from_trace(
                    tr,
                    x_key=str(rep.get("x_key") or ""),
                    y_key=str(rep.get("y_key") or ""),
                )
            ui.notify("Local insight complete.", type="positive")
            _local_results.refresh()
        except Exception as exc:
            ui.notify(f"Insight failed: {exc}", type="negative")

    if insight == "Causality trace":
        ui.slider(
            min=0.005,
            max=0.05,
            step=0.005,
            value=session.scan_causality_rel_step,
            on_change=lambda e: setattr(session, "scan_causality_rel_step", float(e.value)),
        ).props("label").classes("w-full")
    ui.button("Run local insight", icon="play_arrow", on_click=_run_local).props("outline q-mb-sm")
    _local_results(session)


@ui.refreshable
def _local_results(session: DesignSession) -> None:
    tr = session.scan_causality_last
    if not isinstance(tr, dict):
        return
    if tr.get("status") == "skipped":
        ui.label(str(tr.get("reason") or "Skipped")).classes("text-caption text-grey")
        return
    plain = format_causality_trace(tr) or format_insight_dict(tr)
    if plain:
        ui.markdown(plain).classes("text-body2 q-mb-sm")
    with ui.expansion("Raw JSON", icon="data_object").classes("w-full"):
        ui.code(json.dumps(tr, indent=2, default=str)[:4000], language="json").classes("w-full")


def _render_next_tier(session: DesignSession, rep: dict, intents: list) -> None:
    ui.label("Landscape insights (0-D)").classes("text-subtitle1")
    ui.label("Interpretability over the full scan — no optimization, no constraint relaxation.").classes(
        "text-caption q-mb-sm"
    )
    if session.scan_next_tier_pick not in NEXT_TIER_TOOLS:
        session.scan_next_tier_pick = NEXT_TIER_TOOLS[0]
    ui.select(
        NEXT_TIER_TOOLS,
        label="Tool",
        value=session.scan_next_tier_pick,
        on_change=lambda e: setattr(session, "scan_next_tier_pick", str(e.value)),
    ).classes("w-full q-mb-sm")

    pick = session.scan_next_tier_pick
    needs_cell = pick in {
        "Local scaling law",
        "Regime label at cell",
        "Counterfactual lens",
        "Projection stability",
    }
    i = j = 0
    if needs_cell:
        i, j = _cell_picker(session, rep)

    ui.select(
        intents,
        label="Intent lens",
        value=session.scan_wb_intent if session.scan_wb_intent in intents else intents[0],
        on_change=lambda e: setattr(session, "scan_wb_intent", str(e.value)),
    ).classes("w-full q-mb-sm")

    @ui.refreshable
    def _tier_out() -> None:
        pass

    async def _run_tier() -> None:
        it = str(session.scan_wb_intent)
        ui.notify(f"Running {pick}…", type="info")
        try:
            out: dict = {}
            if pick == "Explain infeasible region":
                out = await run.io_bound(explain_impossible, rep, it)
            elif pick == "Constraint irrelevance":
                out = await run.io_bound(irrelevant_constraints, rep, it)
            elif pick == "Assumption stress hotspots":
                out = await run.io_bound(stress_hotspots, rep, it)
            elif pick == "Surprise detector":
                out = await run.io_bound(surprise_regions, rep, it)
            elif pick == "Local scaling law":
                out = await run.io_bound(local_scaling, rep, it, i, j)
            elif pick == "Regime label at cell":
                out = await run.io_bound(regime_label, rep, it, i, j)
            elif pick == "Counterfactual lens":
                out = await run.io_bound(counterfactual, rep, it, "TBR")
            elif pick == "Projection stability":
                z = str(getattr(session, "scan_slice_z_key", "") or SCAN_VAR_KEYS[0])
                if z in (str(rep.get("x_key")), str(rep.get("y_key"))):
                    z = next((k for k in SCAN_VAR_KEYS if k not in (rep.get("x_key"), rep.get("y_key"))), z)
                out = await run.io_bound(
                    projection_stability,
                    session.build_point_inputs(),
                    rep,
                    it,
                    i,
                    j,
                    z,
                    float(getattr(session, "scan_slice_rel_step", 0.05)),
                )
            elif pick == "Path-follow scan":
                out = await run.io_bound(
                    path_follow_scan,
                    session.build_point_inputs(),
                    rep,
                    target_output="q95",
                    intent=it,
                )
                session.scan_path_follow_last = out
            elif pick == "Guided walkthrough":
                steps = guided_walkthrough()
                session.scan_causality_last = {"steps": steps}
                _tier_results.refresh()
                ui.notify("Walkthrough loaded.", type="positive")
                return
            session.scan_causality_last = out if isinstance(out, dict) else {"result": out}
            _tier_results.refresh()
            ui.notify("Insight complete.", type="positive")
        except Exception as exc:
            ui.notify(f"Tool failed: {exc}", type="negative")

    if pick == "Counterfactual lens":
        ui.label("Visualization only — does not change frozen physics.").classes(
            "text-caption text-orange q-mb-xs"
        )
    if pick == "Path-follow scan":
        ui.label("Follows y to hold a target output as x varies along the scan axis.").classes(
            "text-caption q-mb-xs"
        )

    ui.button("Run landscape insight", icon="analytics", on_click=_run_tier).props("outline q-mb-sm")
    _tier_results(session)


@ui.refreshable
def _tier_results(session: DesignSession) -> None:
    tr = session.scan_causality_last
    if not isinstance(tr, dict):
        return
    if "steps" in tr:
        for s in tr.get("steps") or []:
            if isinstance(s, dict):
                ui.label(f"{s.get('step')}. {s.get('title')} — {s.get('hint')}").classes("text-caption")
        return
    plain = format_insight_dict(tr)
    if plain:
        ui.markdown(plain).classes("text-body2 q-mb-sm")
    with ui.expansion("Raw JSON", icon="data_object").classes("w-full"):
        ui.code(json.dumps(tr, indent=2, default=str)[:5000], language="json").classes("w-full")
    pf = session.scan_path_follow_last
    if isinstance(pf, dict) and pf.get("path"):
        ui.label("Path-follow trajectory").classes("text-subtitle2 q-mt-sm")
        ui.code(json.dumps(pf.get("path")[:20], indent=2, default=str), language="json").classes("w-full")


def _render_expert_claims(session: DesignSession, rep: dict, intents: list) -> None:
    with ui.expansion("Expert argument tools (claims + falsification)", icon="gavel").classes("w-full"):
        ui.label("Turn scan results into audit-grade claims — includes falsification lens.").classes(
            "text-caption q-mb-sm"
        )
        if session.scan_claim_intent not in intents:
            session.scan_claim_intent = str(intents[0])
        ui.select(
            intents,
            label="Intent",
            value=session.scan_claim_intent,
            on_change=lambda e: setattr(session, "scan_claim_intent", str(e.value)),
        ).classes("w-full")
        ui.select(
            ["Dominance", "Robustness"],
            label="Claim type",
            value=session.scan_claim_type or "Dominance",
            on_change=lambda e: setattr(session, "scan_claim_type", str(e.value)),
        ).classes("w-full")
        ui.input(
            "Expected (for falsification)",
            value=session.scan_claim_expected,
            on_change=lambda e: setattr(session, "scan_claim_expected", str(e.value or "")),
        ).classes("w-full")
        ui.input(
            "Claim title",
            value=session.scan_claim_title or f"Scan claim — {session.scan_claim_type}",
            on_change=lambda e: setattr(session, "scan_claim_title", str(e.value or "")),
        ).classes("w-full")
        ui.textarea(
            "Claim statement",
            value=session.scan_claim_statement,
            on_change=lambda e: setattr(session, "scan_claim_statement", str(e.value or "")),
        ).classes("w-full")

        async def _falsify() -> None:
            try:
                fx = await run.io_bound(
                    falsify_claim,
                    rep,
                    session.scan_claim_intent,
                    session.scan_claim_type,
                    session.scan_claim_expected,
                )
                session.scan_claim_falsify_last = fx
                _claim_panel.refresh()
                ui.notify("Falsification complete.", type="info")
            except Exception as exc:
                ui.notify(str(exc), type="negative")

        async def _export_claim() -> None:
            try:
                from tools.scan_expert_features import ScanClaim

                ev = build_claim_evidence(rep, session.scan_claim_intent)
                png = dominance_map_png_bytes(rep, session.scan_claim_intent)
                cl = ScanClaim(
                    title=session.scan_claim_title or "Scan claim",
                    statement=session.scan_claim_statement or "",
                    intent=session.scan_claim_intent,
                    claim_type=session.scan_claim_type,
                    notes=session.scan_claim_notes,
                )
                fps = compute_repo_fingerprints()

                def _build() -> bytes:
                    return build_claim_pdf(
                        claim=cl,
                        evidence=ev,
                        map_png=png,
                        fingerprint=fps,
                    )

                pdf = await run.io_bound(_build)
                session.scan_claim_pdf_bytes = pdf
                session.scan_claim_last = {
                    "title": session.scan_claim_title,
                    "statement": session.scan_claim_statement,
                    "intent": session.scan_claim_intent,
                    "type": session.scan_claim_type,
                }
                _claim_panel.refresh()
                ui.notify("Claim PDF ready.", type="positive")
            except Exception as exc:
                ui.notify(f"Claim export failed: {exc}", type="negative")

        with ui.row().classes("gap-2"):
            ui.button("Try to falsify", icon="science", on_click=_falsify).props("outline")
            ui.button("Export claim PDF", icon="picture_as_pdf", on_click=_export_claim).props("outline")
        _claim_panel(session)


@ui.refreshable
def _claim_panel(session: DesignSession) -> None:
    fx = session.scan_claim_falsify_last
    if isinstance(fx, dict) and fx:
        ui.markdown(
            f"Counterexamples: **{fx.get('n_counterexamples', '-')}** · {fx.get('note', '')}"
        ).classes("text-caption q-mt-sm")
    pdf = session.scan_claim_pdf_bytes
    if isinstance(pdf, (bytes, bytearray)) and len(pdf) > 100:
        ui.button(
            "Download claim PDF",
            icon="download",
            on_click=lambda: ui.download(bytes(pdf), "shams_scan_claim.pdf"),
        ).props("flat outline q-mt-sm")
