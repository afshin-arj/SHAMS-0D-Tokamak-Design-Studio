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
        from ui_nicegui.lib.run_lock import (
            acquire as runlock_acquire,
            release as runlock_release,
            status as runlock_status,
            current_lease,
            lease_valid,
        )

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
        lease = current_lease()
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
            if not lease_valid(lease):
                ui.notify("Run was force-cleared — discarding results.", type="warning")
                return
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
            if lease_valid(lease):
                runlock_release("ControlRoom", lease)

    ui.button("Run certified search", icon="travel_explore", on_click=_run).props("color=primary outline q-mt-sm")

    async def _evidence_zip() -> None:
        art = session.v340_cert_search_last
        if not isinstance(art, dict):
            ui.notify("Run certified search first", type="warning")
            return
        try:
            from tools.simple_evidence_zip import build_simple_evidence_zip_bytes
            from ui_nicegui.lib.cr_artifacts_helpers import watermark_run_artifact_export

            export = watermark_run_artifact_export(art)
            # PHYS-KPI-001: watermark nested stage/record claim KPIs on REJECTED rows.
            stages_out = []
            has_infeasible = False
            for stg in export.get("stages") or []:
                if not isinstance(stg, dict):
                    stages_out.append(stg)
                    continue
                stg2 = dict(stg)
                recs = list(stg2.get("records") or [])
                if any(str(r.get("verdict") or "").upper() not in ("PASS", "VERIFIED", "FEASIBLE", "OK") for r in recs if isinstance(r, dict)):
                    has_infeasible = True
                if recs:
                    stg2["records"] = watermark_certified_search_rows(recs)
                stages_out.append(stg2)
            if stages_out:
                export["stages"] = stages_out
            best = export.get("best")
            if isinstance(best, dict):
                bv = str(best.get("verdict") or "").upper()
                if bv not in ("PASS", "VERIFIED", "FEASIBLE", "OK"):
                    has_infeasible = True
                    wm = watermark_certified_search_rows([best])
                    export["best"] = wm[0] if wm else best
            if has_infeasible:
                export["phys_kpi_note"] = (
                    "PHYS-KPI-001: claim KPIs / scores on REJECTED rows are "
                    "— (diagnostic) — not design claims."
                )

            b = await run.io_bound(
                build_simple_evidence_zip_bytes,
                export,
                basename=f"certified_search_{str(art.get('digest', ''))[:12]}",
            )
            ui.download(b, "certified_search_evidence.zip")
        except Exception as exc:
            ui.notify(f"Evidence pack failed: {exc}", type="negative")

    ui.button("Build evidence ZIP", icon="folder_zip", on_click=_evidence_zip).props("flat outline q-mt-xs")
    _results(session)


def watermark_certified_search_rows(rows: list) -> list[dict]:
    """PHYS-KPI-001: suppress claim KPIs on REJECTED / FAIL certified-search rows."""
    from ui_nicegui.lib.plant_kpi_honesty_ui import format_claim_kpi_for_table, is_claim_kpi_key

    out_rows: list[dict] = []
    for r in rows:
        rr = dict(r)
        verdict = str(rr.get("verdict") or "").upper()
        feasible = verdict in ("PASS", "VERIFIED", "FEASIBLE", "OK")
        for k, v in list(rr.items()):
            key = str(k)
            # Evidence-prefixed objective values e.g. e_objective_value
            claim_key = key
            if key.startswith("e_") and is_claim_kpi_key(key[2:]):
                claim_key = key[2:]
            elif key == "e_objective_value":
                claim_key = str(rr.get("e_objective") or rr.get("objective") or "Q_DT_eqv")
            elif key == "score" and not feasible:
                rr[k] = "— (diagnostic)"
                continue
            if is_claim_kpi_key(claim_key) or (
                key == "e_objective_value" and not feasible
            ):
                rr[k] = format_claim_kpi_for_table(
                    claim_key if is_claim_kpi_key(claim_key) else "Q_DT_eqv",
                    v,
                    feasible=feasible,
                )
        out_rows.append(rr)
    return out_rows


def promote_certified_search_x_to_point_designer(session: DesignSession, best: dict) -> int:
    """Seed ``best['x']`` (or flat knobs) into Point Designer and clear prior KPIs."""
    if not isinstance(best, dict):
        return 0
    x = best.get("x") if isinstance(best.get("x"), dict) else None
    if not x:
        # Flattened table rows store knobs at top level.
        x = {
            k: v
            for k, v in best.items()
            if k in (session.inputs or {}) and v is not None and k not in (
                "stage", "i", "verdict", "score", "x", "evidence"
            )
        }
    n = 0
    for k, v in (x or {}).items():
        if k not in session.inputs:
            continue
        try:
            session.inputs[k] = float(v)
            n += 1
        except (TypeError, ValueError):
            pass
    if n:
        from ui_nicegui.lib.pd_handoff import invalidate_point_designer_after_seed

        invalidate_point_designer_after_seed(session)
    return n


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
        ui.label(
            "PHYS-KPI-001: claim KPIs / scores on REJECTED rows are — (diagnostic) — not design claims."
        ).classes("text-caption text-orange q-mb-xs")
    if rows:
        display = watermark_certified_search_rows(rows[:100])
        cols = list(display[0].keys())[:12]
        ui.table(
            columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in cols],
            rows=[{c: r.get(c) for c in cols} for r in display],
            row_key="stage",
        ).classes("w-full q-mb-sm")
    best = art.get("best")
    if isinstance(best, dict):
        with ui.expansion(BEST_PROPOSED_LABEL, icon="star").classes("w-full"):
            bv = str(best.get("verdict") or "").upper()
            if bv in ("PASS", "VERIFIED", "FEASIBLE", "OK") or not bv:
                # Single-objective best blob may omit verdict (PASS-only ranking).
                render_json_blob(best)
            else:
                wm = watermark_certified_search_rows([best])
                render_json_blob(wm[0] if wm else best)
                ui.label(
                    "PHYS-KPI-001: best blob claim FoMs watermarked — not VERIFIED design claims."
                ).classes("text-caption text-orange")

        def _promote_best() -> None:
            n = promote_certified_search_x_to_point_designer(session, best)
            if n <= 0:
                ui.notify("Best candidate has no overlapping inputs to promote.", type="warning")
                return
            from ui_nicegui.lib.pd_handoff import navigate_to_point_designer
            from ui_nicegui.lib.navigation import refresh_helm, refresh_status

            refresh_helm()
            refresh_status()
            navigate_to_point_designer(session)
            ui.notify(
                f"Promoted {n} certified-search knobs → Point Designer — "
                "prior KPIs cleared; Evaluate Point to re-certify.",
                type="warning",
            )

        ui.button(
            "Promote best → Point Designer",
            icon="upload",
            on_click=_promote_best,
        ).props("outline color=primary q-mt-sm data-testid=cr-cert-promote-best")

    def _download_cert() -> None:
        export = dict(art)
        raw_rows = flatten_certified_search_table_rows(art)
        export["table_rows_watermarked"] = watermark_certified_search_rows(raw_rows)
        best = export.get("best")
        if isinstance(best, dict):
            bv = str(best.get("verdict") or "").upper()
            if bv not in ("PASS", "VERIFIED", "FEASIBLE", "OK"):
                wm = watermark_certified_search_rows([best])
                export["best"] = wm[0] if wm else best
        export["phys_kpi_note"] = (
            "PHYS-KPI-001: claim KPIs / scores on REJECTED rows are "
            "— (diagnostic) — not design claims."
        )
        ui.download(report_to_json_bytes(export), "certified_search.json")

    ui.button(
        "Download certified search JSON",
        icon="download",
        on_click=_download_cert,
    ).props("flat outline")
