"""Mission Snapshot telemetry view — verdict-first KPIs + expert strips."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.decks.point_designer.pd_physics_deepening import DEEP_VIEWS, render_physics_deepening
from ui_nicegui.lib.pd_hero_kpis import hero_diagnostic_notes, hero_kpi_cells
from ui_nicegui.lib.pd_parity_helpers import (
    assumptions_snapshot,
    authority_contract_rows,
    build_coils_metrics,
    constraint_provenance,
    constraint_radar_rows,
    constraint_suggestion,
    dominant_limiter_summary,
    fmt_num,
    fuel_cycle_caps_caption,
    fuel_cycle_metric_groups,
    infeasibility_trace,
    magnet_card_metrics,
    avail_v420_summary,
    costing_v421_summary,
    magnet_v400_summary,
    magnet_v410_summary,
    machine_v412_summary,
    plant_v419_summary,
    point_summary_rows,
    raw_telemetry_rows,
    regime_compass_rows,
)
from ui_nicegui.lib.verdict_core import verdict_summary
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def render_mission_snapshot(session: DesignSession) -> None:
    out = session.pd_last_outputs or session.last_eval
    if not isinstance(out, dict):
        return

    summary = verdict_summary(out)
    art = session.pd_last_artifact if isinstance(session.pd_last_artifact, dict) else {}
    rs = art.get("run_summary") if isinstance(art.get("run_summary"), dict) else {}
    headline = rs.get("headline") if isinstance(rs.get("headline"), dict) else {}
    for note in hero_diagnostic_notes(
        out,
        summary,
        design_intent=str(session.design_intent),
        fuel_mode=str(session.inputs.get("fuel_mode", "DT")),
        headline=headline,
    ):
        ui.markdown(note).classes("text-caption text-orange q-mb-sm")

    # PHYS-KPI-001: use hero cells (suppress Q/H98/Pfus/P_net claims on INFEASIBLE).
    cells = hero_kpi_cells(
        out,
        summary,
        design_intent=str(session.design_intent),
        fuel_mode=str(session.inputs.get("fuel_mode", "DT")),
        headline=headline,
    )
    kpi_row([(c.label, c.display) for c in cells])
    ui.label(
        "Q = Pfus / P_aux (auxiliary heating only). n·T is a pressure proxy, not Lawson n·T·τE."
    ).classes("text-caption text-grey q-mb-sm")

    trace = infeasibility_trace(out)
    if trace:
        with ui.expansion("Why infeasible? (constraint trace)", icon="warning").classes("w-full"):
            for row in trace:
                ui.markdown(
                    f"**{row['constraint']}** — `{row['output_key']}` = {row['value']:.4g} "
                    f"({row['sense']} {row['limit']:.4g})"
                )

    art = session.pd_last_artifact or {}
    include_rad = bool(session.overlay.get("include_radiation", False))
    use_lq = bool(session.inputs.get("use_lambda_q", True))

    with ui.expansion("Inboard build & coil stress", icon="architecture").classes("w-full"):
        coils = build_coils_metrics(out)
        for i in range(0, len(coils), 4):
            kpi_row(coils[i : i + 4])
        enforce = float(out.get("enforce_radial_build", 0.0) or 0.0)
        if enforce >= 0.5:
            ui.label(
                "Radial-build closure enforcement is ON (inboard_margin_m ≥ 0 is a hard constraint)."
            ).classes("text-info text-caption")
        else:
            ui.label(
                "Radial-build closure enforcement is OFF by default; enable in Configure if desired."
            ).classes("text-caption")

    with ui.expansion("Subsystem contract validity", icon="verified").classes("w-full"):
        rows, n_proxy = authority_contract_rows(out)
        if rows:
            ui.table(
                columns=[
                    {"name": "subsystem", "label": "Subsystem", "field": "subsystem", "align": "left"},
                    {"name": "tier", "label": "Tier", "field": "tier"},
                    {"name": "validity", "label": "Validity", "field": "validity", "align": "left"},
                ],
                rows=rows,
                row_key="subsystem",
            ).classes("w-full")
            if n_proxy > 0:
                ui.label(f"{n_proxy} subsystems tagged as PROXY for this run.").classes("text-orange text-caption")
            else:
                ui.label(
                    "No subsystems flagged as pure PROXY (some may still be semi-authoritative)."
                ).classes("text-positive text-caption")
        else:
            ui.label("Authority contracts unavailable.").classes("text-caption")
        ui.label("Contracts are declarative metadata; they do not change physics.").classes("text-caption")

    with ui.expansion("Fuel Cycle · Lifetime · Availability", icon="battery_charging_full").classes("w-full"):
        for group in fuel_cycle_metric_groups(out):
            kpi_row(group)
        ui.label(fuel_cycle_caps_caption(out)).classes("text-caption q-mt-sm")
        led391 = out.get("availability_ledger_v391")
        if isinstance(led391, list) and led391 and isinstance(led391[0], dict):
            with ui.expansion("Availability reliability ledger", icon="list").classes("w-full"):
                cols = [{"name": c, "label": c, "field": c, "align": "left"} for c in led391[0].keys()]
                ui.table(columns=cols, rows=led391[:40], row_key=cols[0]["field"]).classes("w-full")

    with ui.expansion("Model Scope & Assumptions", icon="description").classes("w-full"):
        ui.markdown(
            "**Badges:** **Authoritative** = used in feasibility/constraints · "
            "**Proxy** = approximate model · **Diagnostic** = non-blocking checks"
        ).classes("text-caption")
        ui.label("Assumptions snapshot (UI-level):").classes("text-subtitle2")
        render_json_blob(assumptions_snapshot(session))
        mc = out.get("model_cards")
        if isinstance(mc, dict) and mc:
            ui.label("Model cards (provenance):").classes("text-subtitle2 q-mt-sm")
            render_json_blob(mc)

    _magnet_card(out)
    v400 = magnet_v400_summary(out)
    if v400:
        with ui.expansion("Magnet technology margin ledger", icon="electrical_services").classes("w-full"):
            ui.label("B–J–stress margin stack for TF technology class.").classes("text-caption q-mb-sm")
            kpi_row([
                ("Combined margin", fmt_num(v400["combined_margin"])),
                ("Tier", str(v400["tier"])),
                ("Dominant", str(v400["dominant"])),
                ("Dominant margin", fmt_num(v400["dominant_margin"])),
            ])
            ui.label("Per-aspect margins").classes("text-subtitle2")
            render_json_blob(v400["per_aspect_margins"])
            ui.label("Per-aspect tiers").classes("text-subtitle2 q-mt-sm")
            render_json_blob(v400["per_aspect_tiers"])

    v410 = magnet_v410_summary(out)
    if v410:
        with ui.expansion("Magnet SC system / TF/PF/CS SC [PROXY]", icon="hub").classes("w-full"):
            ui.badge("PROXY overlay").props("color=orange")
            ui.label(
                "Per-family TF/PF/CS superconducting & engineering margins beyond magnet technology margins."
            ).classes("text-caption q-mb-sm")
            kpi_row([
                ("System margin", fmt_num(v410["system_margin"])),
                ("System tier", str(v410["system_tier"])),
                ("Dominant family", str(v410["dominant_family"])),
                ("Family margin", fmt_num(v410["dominant_family_margin"])),
            ])
            ui.label("Per-family margins").classes("text-subtitle2")
            render_json_blob(v410["family_margins"])
            ui.label("Per-family tiers / dominants").classes("text-subtitle2 q-mt-sm")
            render_json_blob({"tiers": v410["family_tiers"], "dominants": v410["family_dominants"]})

    v412 = machine_v412_summary(out)
    if v412:
        with ui.expansion("Machine build closure / Radial machine-build [PROXY]", icon="view_timeline").classes("w-full"):
            ui.badge("PROXY overlay").props("color=orange")
            ui.label(
                "Layer-stack consistency, clearances, and outboard envelope narrative."
            ).classes("text-caption q-mb-sm")
            kpi_row([
                ("System margin", fmt_num(v412["system_margin"])),
                ("System tier", str(v412["system_tier"])),
                ("Dominant aspect", str(v412["dominant_aspect"])),
                ("Inboard margin [m]", fmt_num(v412["inboard_margin_m"])),
            ])
            ui.label("Aspect margins").classes("text-subtitle2")
            render_json_blob(v412["aspect_margins"])
            if v412.get("narrative"):
                ui.label(str(v412["narrative"])).classes("text-caption q-mt-sm")

    v419 = plant_v419_summary(out)
    if v419:
        with ui.expansion("Plant Sankey ledger [PROXY]", icon="account_tree").classes("w-full"):
            ui.badge("PROXY overlay — Pe_net watermarked").props("color=orange")
            ui.label(
                "Source→sink thermal/electric flows with recirculating breakdown and conservation checks."
            ).classes("text-caption q-mb-sm")
            from ui_nicegui.lib.plant_kpi_honesty_ui import pe_net_display

            kpi_row([
                ("System tier", str(v419["system_tier"])),
                ("Conservation", "OK" if v419.get("conservation_ok") else "FAIL"),
                ("f_recirc", fmt_num(v419.get("f_recirc"))),
                ("Pe_net [MW]", pe_net_display(out, artifact=art, design_intent=str(session.design_intent))),
            ])
            if v419.get("recirc_breakdown"):
                ui.label("Recirc breakdown [MW(e)]").classes("text-subtitle2")
                render_json_blob(v419["recirc_breakdown"])
            if v419.get("narrative"):
                ui.label(str(v419["narrative"])).classes("text-caption q-mt-sm")

    v420 = avail_v420_summary(out)
    if v420:
        with ui.expansion("Availability–OPEX–LCOE [PROXY]", icon="timeline").classes("w-full"):
            ui.badge("PROXY overlay — LCOE watermarked").props("color=orange")
            ui.label(
                "One availability chain feeds operating hours, annual energy, OPEX, and LCOE consistently."
            ).classes("text-caption q-mb-sm")
            from ui_nicegui.lib.plant_kpi_honesty_ui import lcoe_display

            kpi_row([
                ("Availability", fmt_num(v420.get("availability"))),
                ("A source", str(v420.get("availability_source", "-"))),
                ("E_net [MWh/y]", fmt_num(v420.get("E_net_MWh_per_y"))),
                ("OPEX [MUSD/y]", fmt_num(v420.get("OPEX_total_MUSD_per_y"))),
                ("LCOE [USD/MWh]", lcoe_display(out, artifact=art, design_intent=str(session.design_intent))),
                ("Consistency", "OK" if v420.get("consistency_ok") else "FAIL"),
            ])
            if v420.get("opex_breakdown_MUSD_per_y"):
                ui.label("OPEX breakdown [MUSD/y]").classes("text-subtitle2")
                render_json_blob(v420["opex_breakdown_MUSD_per_y"])
            if v420.get("narrative"):
                ui.label(str(v420["narrative"])).classes("text-caption q-mt-sm")

    c421 = costing_v421_summary(out)
    if c421:
        with ui.expansion("Bottom-up modular costing [PROXY]", icon="receipt_long").classes("w-full"):
            ui.badge("PROXY overlay — not 1990 Generomak").props("color=orange")
            ui.label(
                "Modular direct/indirect CAPEX account ledger with explicit drivers and transparent unit rates."
            ).classes("text-caption q-mb-sm")
            from ui_nicegui.lib.plant_kpi_honesty_ui import bottom_up_lcoe_display

            kpi_row([
                ("Total CAPEX [MUSD]", fmt_num(c421.get("CAPEX_total_MUSD"))),
                ("Direct [MUSD]", fmt_num(c421.get("direct_subtotal_MUSD"))),
                ("Indirect [MUSD]", fmt_num(c421.get("indirect_subtotal_MUSD"))),
                ("Dominant account", str(c421.get("dominant_account", "-"))),
                ("LCOE [USD/MWh]", bottom_up_lcoe_display(out, artifact=art, design_intent=str(session.design_intent))),
                ("Consistency", "OK" if c421.get("consistency_ok") else "FAIL"),
            ])
            if c421.get("account_ledger"):
                ui.label("CAPEX account ledger [MUSD]").classes("text-subtitle2")
                render_json_blob({
                    str(r.get("account")): r.get("cost_MUSD")
                    for r in c421["account_ledger"]
                    if isinstance(r, dict)
                })
            if c421.get("narrative"):
                ui.label(str(c421["narrative"])).classes("text-caption q-mt-sm")

    with ui.expansion("Regime compass (sanity checks)", icon="explore").classes("w-full"):
        ui.label("Expert quick-check panel. Values are diagnostic unless explicitly constrained.").classes(
            "text-caption"
        )
        show_unc = ui.checkbox("Show proxy uncertainty bands (diagnostic)", value=False)
        unc_proxy = ui.slider(min=0.0, max=0.5, value=0.15, step=0.01).bind_visibility_from(show_unc, "value")
        unc_neut = ui.slider(min=0.0, max=0.5, value=0.20, step=0.01).bind_visibility_from(show_unc, "value")

        @ui.refreshable
        def _compass() -> None:
            rows = regime_compass_rows(
                out,
                include_radiation=include_rad,
                use_lambda_q=use_lq,
                show_unc=bool(show_unc.value),
                unc_proxy_frac=float(unc_proxy.value or 0.15),
                unc_neut_frac=float(unc_neut.value or 0.20),
            )
            ui.table(
                columns=[
                    {"name": "metric", "label": "Metric", "field": "metric", "align": "left"},
                    {"name": "value", "label": "Value", "field": "value"},
                    {"name": "units", "label": "Units", "field": "units"},
                    {"name": "type", "label": "Type", "field": "type"},
                    {"name": "typical", "label": "Typical", "field": "typical"},
                    {"name": "flag", "label": "Flag", "field": "flag"},
                    {"name": "unc", "label": "Unc", "field": "unc"},
                ],
                rows=rows,
                row_key="metric",
            ).classes("w-full")

        show_unc.on("update:model-value", lambda: _compass.refresh())
        unc_proxy.on("update:model-value", lambda: _compass.refresh())
        unc_neut.on("update:model-value", lambda: _compass.refresh())
        _compass()

    with ui.expansion("Constraint radar (pass/fail & margins)", icon="radar").classes("w-full"):
        rows_c = constraint_radar_rows(out, art if isinstance(art, dict) else None)
        if not rows_c:
            ui.label("No constraints evaluated (missing keys).").classes("text-caption")
        else:
            ui.table(
                columns=[
                    {"name": "constraint", "label": "Constraint", "field": "constraint", "align": "left"},
                    {"name": "passed", "label": "Passed", "field": "passed"},
                    {"name": "severity", "label": "Severity", "field": "severity"},
                    {"name": "margin_frac", "label": "Margin", "field": "margin_frac"},
                    {"name": "value", "label": "Value", "field": "value"},
                    {"name": "limit", "label": "Limit", "field": "limit"},
                    {"name": "sense", "label": "Sense", "field": "sense"},
                ],
                rows=rows_c,
                row_key="constraint",
            ).classes("w-full")
            dom_msg = dominant_limiter_summary(rows_c)
            if dom_msg:
                ui.markdown(dom_msg).classes("text-info")
            failed = [r for r in rows_c if not r["passed"] and str(r.get("severity", "hard")) == "hard"]
            soft_failed = [r for r in rows_c if not r["passed"] and str(r.get("severity")) == "soft"]
            if failed:
                ui.label(f"{len(failed)} hard constraint(s) failed.").classes("text-negative")
            if soft_failed:
                ui.label(f"{len(soft_failed)} soft constraint(s) failed (screening only).").classes("text-orange")
            names = [r["constraint"] for r in rows_c]
            if names:
                pick = ui.select(names, label="Constraint details", value=names[0])
                with ui.expansion("Definition + drivers", icon="info").classes("w-full"):
                    @ui.refreshable
                    def _prov() -> None:
                        rec = next((r for r in rows_c if r["constraint"] == pick.value), {})
                        render_json_blob({
                            "sense": rec.get("sense"),
                            "value": rec.get("value"),
                            "limit": rec.get("limit"),
                            "passed": rec.get("passed"),
                            "margin_frac": rec.get("margin_frac"),
                            "note": rec.get("note"),
                        })
                        prov = constraint_provenance(str(pick.value or ""))
                        if prov:
                            render_json_blob(prov)
                        else:
                            ui.label("No additional provenance notes registered.").classes("text-caption")

                    pick.on("update:model-value", lambda: _prov.refresh())
                    _prov()
            if failed or soft_failed:
                ui.label("Actionable suggestions (rule-of-thumb):").classes("text-subtitle2 q-mt-sm")
                for r in failed + soft_failed:
                    ui.markdown(f"• **{r['constraint']}**: {constraint_suggestion(r['constraint'])}").classes(
                        "text-body2"
                    )

    with ui.expansion(
        f"Physics deepening ({len(DEEP_VIEWS)} decks)",
        icon="science",
    ).classes("w-full"):
        try:
            base = session.build_point_inputs()
        except Exception:
            base = None
        render_physics_deepening(out, base=base)

    with ui.expansion("Point summary (compact)", icon="table_chart").classes("w-full"):
        feas = bool(verdict_summary(out).get("feasible"))
        if not feas:
            ui.label(
                "PHYS-KPI-001: H98 / Q / Pfus / P_net below are diagnostic residue on an INFEASIBLE point — not design claims."
            ).classes("text-caption text-orange q-mb-xs")
        ps = point_summary_rows(out, feasible=feas)
        if ps:
            ui.table(
                columns=[
                    {"name": "quantity", "label": "Quantity", "field": "quantity", "align": "left"},
                    {"name": "value", "label": "Value", "field": "value"},
                ],
                rows=ps,
                row_key="quantity",
            ).classes("w-full")
        else:
            ui.label("No summary metrics available.").classes("text-caption")

    with ui.expansion("Raw telemetry (diagnostic keys)", icon="data_object").classes("w-full"):
        rt = raw_telemetry_rows(out)
        ui.table(
            columns=[
                {"name": "key", "label": "Output key", "field": "key", "align": "left"},
                {"name": "value", "label": "Value", "field": "value", "align": "left"},
            ],
            rows=rt,
            row_key="key",
        ).classes("w-full")


def _magnet_card(out: dict) -> None:
    mc = magnet_card_metrics(out)
    ui.label("Magnet Card").classes("text-subtitle1 q-mt-sm")
    kpi_row([
        ("TF technology", mc["tech"]),
        (
            "TF superconducting",
            "YES" if mc["tf_sc"] == 1.0 else ("NO" if mc["tf_sc"] == 0.0 else "n/a"),
        ),
        (
            "SC margin" if mc["tf_sc"] == 1.0 else "TF ohmic [MW]",
            mc["sc_margin_display"] if mc["tf_sc"] == 1.0 else fmt_num(mc["p_tf_ohm"]),
        ),
        ("Tcoil [K]", fmt_num(mc["tcoil_K"])),
    ])
    if mc["tf_note"]:
        ui.label(f"TF_SC policy: {mc['tf_note']}").classes("text-caption")
    from ui_nicegui.lib.plant_kpi_honesty_ui import pe_net_display

    kpi_row([
        (
            "SC margin" if mc["tf_sc"] == 1.0 else "TF ohmic [MW]",
            mc["sc_margin_display"] if mc["tf_sc"] == 1.0 else fmt_num(mc["p_tf_ohm"]),
        ),
        ("Lifetime [yr]", fmt_num(mc["hts_lifetime_yr"])),
        ("Vdump [kV]", fmt_num(mc["V_dump_kV"])),
        ("P_net,e [MW]", pe_net_display(out)),
    ])
