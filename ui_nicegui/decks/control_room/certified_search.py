"""Control Room — certified search orchestrator (Chronicle).

Honesty: Proposed — SHAMS-certified (Phase 1.3); VERIFIED vs REJECTED + atlas note.
"""
from __future__ import annotations

from nicegui import run, ui

from ui_nicegui.components.certified_opt_honesty_banner import (
    render_atlas_reject_note,
    render_certified_opt_honesty_banner,
)
from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.certified_opt_honesty import (
    BEST_PROPOSED_LABEL,
    REJECTED_KPI_LABEL,
    VERIFIED_KPI_LABEL,
    counts_from_pass_fail_rows,
    format_verified_rejected_counts,
)
from ui_nicegui.lib.control_room_helpers import report_to_json_bytes
from ui_nicegui.lib.cr_chronicle_helpers import (
    flatten_certified_search_table_rows,
    run_orchestrated_certified_search_nicegui,
)
from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


_KNOB_OPTIONS = [
    ("Bt_T", 2.0, 25.0),
    ("Ip_MA", 1.0, 25.0),
    ("Paux_MW", 0.0, 200.0),
    ("Ti_keV", 1.0, 40.0),
    ("fG", 0.2, 1.2),
    ("kappa", 1.0, 2.6),
    ("a_m", 0.2, 3.0),
    ("R0_m", 0.8, 12.0),
]


def render_certified_search(session: DesignSession) -> None:
    ui.label("Certified Search").classes("text-subtitle1")
    ui.label(
        "Budgeted multi-knob search (external to truth). Each candidate is verified by the frozen evaluator."
    ).classes("text-caption q-mb-sm")
    render_certified_opt_honesty_banner("certified_search")

    try:
        base = session.build_point_inputs()
    except Exception:
        base = None
    if base is None:
        empty_state("Run a point in **Point Designer** first so a base point exists.", kind="info")
        ui.button("Open Point Designer", icon="open_in_new", on_click=lambda: switch_deck("Point Designer")).props(
            "flat outline q-mt-sm"
        )
        return

    chosen = ui.select(
        [k[0] for k in _KNOB_OPTIONS],
        label="Knobs (up to 4)",
        value=["Bt_T", "Ip_MA"],
        multiple=True,
    ).classes("w-full")
    mode = ui.select(
        ["Single objective", "Multi-objective Pareto"],
        label="Mode",
        value="Single objective",
    ).classes("w-full")
    objective = ui.select(
        ["Q_DT_eqv", "Pfus_total_MW", "P_e_net_MW"],
        label="Score objective (VERIFIED / PASS-only ranking)",
        value="Q_DT_eqv",
    ).classes("w-full")

    lo_inputs: dict = {}
    hi_inputs: dict = {}
    with ui.expansion("Knob bounds", icon="tune", value=True).classes("w-full"):
        for name, _lo, _hi in _KNOB_OPTIONS:
            if hasattr(base, name):
                lo_inputs[name] = ui.number(f"{name} lo", value=float(getattr(base, name)), step=0.1)
                hi_inputs[name] = ui.number(f"{name} hi", value=float(getattr(base, name)) + 1.0, step=0.1)

    with ui.row().classes("w-full gap-md flex-wrap"):
        budget = ui.number("Budget", value=96, min=8, max=2048, step=8)
        seed = ui.number("Seed", value=0, min=0, max=10000, step=1)
        method = ui.select(["halton", "lhs", "grid"], label="Method", value="halton")
        two_stage = ui.checkbox("Two-stage refine", value=True)
    stage2_frac = ui.number("Stage-2 budget fraction", value=0.35, min=0.1, max=0.8, step=0.05)
    stage2_shrink = ui.number("Stage-2 local shrink", value=0.35, min=0.1, max=0.8, step=0.05)
    stage2_method = ui.select(["grid", "halton", "lhs"], label="Stage-2 method", value="grid")
    insert_surr = ui.checkbox("Insert surrogate stage (non-authoritative)", value=False)
    surr_frac = ui.number("Surrogate budget fraction", value=0.2, min=0.05, max=0.6, step=0.05)

    async def _run() -> None:
        from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status

        knobs = list(chosen.value or [])
        if not knobs:
            ui.notify("Select at least one knob", type="warning")
            return
        if len(knobs) > 4:
            ui.notify("Select at most 4 knobs", type="warning")
            return
        locked, task, is_owner = runlock_status("ControlRoom")
        if locked and not is_owner:
            ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
            return
        if not runlock_acquire("Control Room: Certified search", "ControlRoom"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        variables = []
        for name in knobs:
            lo_w = lo_inputs.get(name)
            hi_w = hi_inputs.get(name)
            lo = float(lo_w.value if lo_w else getattr(base, name))
            hi = float(hi_w.value if hi_w else lo + 1.0)
            if hi <= lo:
                hi = lo + 1e-6
            variables.append({"name": name, "lo": lo, "hi": hi})
        try:
            art = await run.io_bound(
                run_orchestrated_certified_search_nicegui,
                base,
                variables=variables,
                budget=int(budget.value or 96),
                seed=int(seed.value or 0),
                method=str(method.value or "halton"),
                objective=str(objective.value or "Q_DT_eqv"),
                two_stage=bool(two_stage.value),
                stage2_budget_frac=float(stage2_frac.value or 0.35),
                stage2_shrink=float(stage2_shrink.value or 0.35),
                stage2_method=str(stage2_method.value or "grid"),
                insert_surr=bool(insert_surr.value),
                surr_frac=float(surr_frac.value or 0.2),
                surr_pool_mult=50,
                surr_kappa=0.5,
                surr_ridge=1e-3,
                mode="pareto" if str(mode.value).startswith("Multi") else "single",
                pareto_objectives=[{"key": "R0_m", "sense": "min"}, {"key": "P_e_net_MW", "sense": "max"}],
            )
            session.v340_cert_search_last = art
            n_pass = 0
            n_tot = 0
            for stg in art.get("stages") or []:
                recs = stg.get("records") or []
                n_tot += len(recs)
                n_pass += sum(1 for r in recs if r.get("verdict") == "PASS")
            n_rej = max(0, n_tot - n_pass)
            ui.notify(
                f"Certified search done — {format_verified_rejected_counts(n_verified=n_pass, n_rejected=n_rej, n_candidates=n_tot)}",
                type="positive",
            )
            _results.refresh(session)
        except Exception as exc:
            ui.notify(f"Certified search failed: {exc}", type="negative")
        finally:
            runlock_release("ControlRoom")

    ui.button("Run certified search", icon="travel_explore", on_click=_run).props("color=primary outline q-mt-sm")

    async def _evidence_zip() -> None:
        art = session.v340_cert_search_last
        if not isinstance(art, dict):
            ui.notify("Run certified search first", type="warning")
            return
        try:
            from tools.simple_evidence_zip import build_simple_evidence_zip_bytes

            b = await run.io_bound(
                build_simple_evidence_zip_bytes,
                art,
                basename=f"certified_search_{str(art.get('digest', ''))[:12]}",
            )
            ui.download(b, "certified_search_evidence.zip")
        except Exception as exc:
            ui.notify(f"Evidence pack failed: {exc}", type="negative")

    ui.button("Build evidence ZIP", icon="folder_zip", on_click=_evidence_zip).props("flat outline q-mt-xs")
    _results(session)


@ui.refreshable
def _results(session: DesignSession) -> None:
    art = session.v340_cert_search_last
    if not isinstance(art, dict) or not art.get("schema_version"):
        return
    rows = flatten_certified_search_table_rows(art)
    n_verified, n_rejected = counts_from_pass_fail_rows(rows)
    kpi_row(
        [
            ("Candidates", str(len(rows))),
            (VERIFIED_KPI_LABEL, str(n_verified)),
            (REJECTED_KPI_LABEL, str(n_rejected)),
            ("Digest", str(art.get("digest", "-"))[:12]),
        ]
    )
    ui.label(
        format_verified_rejected_counts(
            n_verified=n_verified,
            n_rejected=n_rejected,
            n_candidates=len(rows),
        )
    ).classes("text-caption q-mb-xs")
    if n_rejected > 0:
        render_atlas_reject_note()
    if rows:
        cols = list(rows[0].keys())[:12]
        ui.table(
            columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in cols],
            rows=[{c: r.get(c) for c in cols} for r in rows[:100]],
            row_key="stage",
        ).classes("w-full q-mb-sm")
    best = art.get("best")
    if isinstance(best, dict):
        with ui.expansion(BEST_PROPOSED_LABEL, icon="star").classes("w-full"):
            render_json_blob(best)
    ui.button(
        "Download certified search JSON",
        icon="download",
        on_click=lambda: ui.download(report_to_json_bytes(art), "certified_search.json"),
    ).props("flat outline")
