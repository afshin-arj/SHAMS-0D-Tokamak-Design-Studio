"""Control Contracts telemetry view (read-only Streamlit parity)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.pd_parity_helpers import (
    control_cs_row,
    control_pf_caps_row,
    control_signed_margins,
    control_vs_caps_row,
    fmt_num,
    magnet_v400_summary,
    v398_control_ledger,
)
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def _dict_table_row(d: dict) -> None:
    if not d:
        ui.label("No data.").classes("text-caption")
        return
    ui.table(
        columns=[{"name": k, "label": k, "field": k, "align": "left"} for k in d.keys()],
        rows=[{k: fmt_num(v) if v is not None else "—" for k, v in d.items()}],
        row_key=list(d.keys())[0],
    ).classes("w-full")


def render_control_contracts(session: DesignSession) -> None:
    out = session.pd_last_outputs or session.last_eval
    if not isinstance(out, dict):
        return

    ui.label("Control Contracts").classes("text-subtitle1")
    ui.label(
        "Envelope-based control feasibility. Computes requirements only; does not modify physics."
    ).classes("text-caption q-mb-sm")

    art = session.pd_last_artifact or {}
    inputs_dict = art.get("inputs") if isinstance(art, dict) else session.inputs
    enabled = bool((inputs_dict or {}).get("include_control_contracts", False))

    if not enabled:
        ui.label(
            "Control contracts are OFF. Enable **Control system contracts** in Configure."
        ).classes("text-orange")
        return

    auth = out.get("control_contracts_authority")
    budg = out.get("control_budget_ledger")
    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-1"):
            ui.label("Authority tags").classes("text-subtitle2")
            if isinstance(auth, dict) and auth:
                render_json_blob(auth)
            else:
                ui.label("Authority tags not available.").classes("text-caption")
        with ui.column().classes("flex-2"):
            ui.label("Control budget ledger").classes("text-subtitle2")
            if isinstance(budg, dict) and budg:
                brows = [{"key": str(k), "value": fmt_num(v)} for k, v in budg.items()]
                ui.table(
                    columns=[
                        {"name": "key", "label": "Key", "field": "key", "align": "left"},
                        {"name": "value", "label": "Value", "field": "value", "align": "left"},
                    ],
                    rows=brows,
                    row_key="key",
                ).classes("w-full")
            else:
                ui.label("No budget ledger available.").classes("text-caption")

    with ui.tabs().classes("w-full q-mt-sm") as tabs:
        t_vs = ui.tab("VS Control")
        t_pf = ui.tab("PF Envelope")
        t_sol = ui.tab("SOL Control")
        t_rwm = ui.tab("RWM (MHD)")

    with ui.tab_panels(tabs, value=t_vs).classes("w-full"):
        with ui.tab_panel(t_vs):
            kpi_row([
                ("τ_VS (s)", fmt_num(out.get("tau_VS_s"))),
                ("γ_VS (1/s)", fmt_num(out.get("gamma_VS_s_inv"))),
                ("BW req (Hz)", fmt_num(out.get("vs_bandwidth_req_Hz"))),
            ])
            ui.label("Proxy mapping: vs_margin → τ_VS via vs_tau_nominal_s; BW ≈ vs_bw_factor·γ/(2π).").classes(
                "text-caption"
            )
            ui.label("Caps (optional)").classes("text-subtitle2")
            _dict_table_row(control_vs_caps_row(out))
            margins = control_signed_margins(out, "vs")
            if margins:
                ui.label("Signed margins (cap − required)").classes("text-subtitle2 q-mt-sm")
                _dict_table_row(margins)

        with ui.tab_panel(t_pf):
            kpi_row([
                ("I_peak (MA)", fmt_num(out.get("pf_I_peak_MA"))),
                ("dI/dt (MA/s)", fmt_num(out.get("pf_dIdt_peak_MA_s"))),
                ("V_peak (V)", fmt_num(out.get("pf_V_peak_V"))),
                ("P_peak (MW)", fmt_num(out.get("pf_P_peak_MW"))),
            ])
            ui.label(f"Pulse energy proxy (MJ): {fmt_num(out.get('pf_E_pulse_MJ'))}").classes("text-body2")
            ui.label("CS / Volt-seconds (pulsed) bookkeeping").classes("text-subtitle2 q-mt-sm")
            _dict_table_row(control_cs_row(out))
            ui.label(
                "Canonical ramp–flat–ramp waveform; V ≈ L_eff·dI/dt + R_eff·I."
            ).classes("text-caption")

            v398 = v398_control_ledger(out)
            with ui.expansion("Control ledger (VS budget + headroom + RWM overlay)", icon="account_balance").classes(
                "w-full"
            ):
                if v398:
                    kpi_row([
                        ("VS budget margin", fmt_num(v398.get("vs_budget_margin"))),
                        ("VDE headroom", fmt_num(v398.get("vde_headroom"))),
                        ("RWM proximity idx", fmt_num(v398.get("rwm_index"))),
                    ])
                    ui.label("Tiers").classes("text-subtitle2")
                    render_json_blob({
                        "vde_headroom_tier": v398.get("vde_headroom_tier"),
                        "rwm_proximity_tier": v398.get("rwm_proximity_tier"),
                    })
                    ui.label("Ledger table").classes("text-subtitle2 q-mt-sm")
                    _dict_table_row({
                        k: v398[k]
                        for k in (
                            "psi_req_Vs", "psi_av_Vs", "vs_budget_margin",
                            "vde_power_headroom", "vde_bw_headroom", "rwm_index",
                        )
                        if k in v398
                    })
                    ui.label("Governance-only overlay: no PF circuit solve; no transport/equilibrium iteration.").classes(
                        "text-caption"
                    )
                else:
                    ui.label("Control stability ledger disabled (enable in Configure).").classes("text-caption")

            ui.label("Caps (optional)").classes("text-subtitle2 q-mt-sm")
            _dict_table_row(control_pf_caps_row(out))
            margins = control_signed_margins(out, "pf")
            if margins:
                ui.label("Signed margins (cap − required)").classes("text-subtitle2")
                _dict_table_row(margins)
            wf = out.get("pf_waveform_decimated")
            if isinstance(wf, list) and wf and isinstance(wf[0], dict):
                ui.label("Decimated waveform (t, I)").classes("text-subtitle2 q-mt-sm")
                cols = [{"name": c, "label": c, "field": c} for c in wf[0].keys()]
                ui.table(columns=cols, rows=wf[:80], row_key=cols[0]["field"]).classes("w-full")

        with ui.tab_panel(t_sol):
            kpi_row([
                ("q_target", fmt_num(out.get("q_div_target_MW_m2"))),
                ("f_SOL+div required", fmt_num(out.get("detachment_f_sol_div_required"))),
                ("Prad_SOL+div req (MW)", fmt_num(out.get("detachment_prad_sol_div_required_MW"))),
                ("f_z required", fmt_num(out.get("detachment_f_z_required"))),
            ])
            ui.label(
                "Detachment authority is algebraic: q_div_target → required SOL+div radiation → implied impurity fraction."
            ).classes("text-caption")
            margins = control_signed_margins(out, "sol")
            if margins:
                ui.label("Signed margin (cap − required)").classes("text-subtitle2 q-mt-sm")
                _dict_table_row(margins)

        with ui.tab_panel(t_rwm):
            rwm_on = bool((inputs_dict or {}).get("include_rwm_screening", False))
            if not rwm_on:
                ui.label(
                    "RWM screening is OFF. Enable include_rwm_screening to compute RWM control requirements."
                ).classes("text-caption")
            else:
                kpi_row([
                    ("Regime", str(out.get("rwm_regime", ""))),
                    ("βN_NW", fmt_num(out.get("rwm_betaN_no_wall"))),
                    ("βN_IW", fmt_num(out.get("rwm_betaN_ideal_wall"))),
                    ("χ", fmt_num(out.get("rwm_chi"))),
                ])
                kpi_row([
                    ("τ_w (s)", fmt_num(out.get("rwm_tau_w_s"))),
                    ("BW req (Hz)", fmt_num(out.get("rwm_bandwidth_req_Hz"))),
                    ("P req (MW)", fmt_num(out.get("rwm_control_power_req_MW"))),
                ])
                ui.label("Caps (optional; default to VS caps if not provided)").classes("text-subtitle2")
                _dict_table_row({
                    "bw_req_Hz": out.get("rwm_bandwidth_req_Hz"),
                    "bw_max_Hz": out.get("rwm_bandwidth_max_Hz"),
                    "P_req_MW": out.get("rwm_control_power_req_MW"),
                    "P_max_MW": out.get("rwm_control_power_max_MW"),
                    "ok": out.get("rwm_control_ok"),
                })
                margins = control_signed_margins(out, "rwm")
                if margins:
                    ui.label("Signed margins (cap − required)").classes("text-subtitle2")
                    _dict_table_row(margins)

    v400 = magnet_v400_summary(out)
    with ui.expansion("Magnet technology authority (B–T–J–stress–quench ledger)", icon="bolt").classes(
        "w-full q-mt-md"
    ):
        if v400:
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
        else:
            ui.label("Magnet technology ledger is disabled or unavailable for this run.").classes("text-caption")

    from ui_nicegui.lib.pd_parity_helpers import magnet_v410_summary

    v410 = magnet_v410_summary(out)
    with ui.expansion("Magnet SC system (v410) — TF / PF / CS depth [PROXY]", icon="hub").classes(
        "w-full q-mt-md"
    ):
        if v410:
            ui.badge("PROXY overlay — not PROCESS MFILE parity").props("color=orange")
            kpi_row([
                ("System margin", fmt_num(v410["system_margin"])),
                ("System tier", str(v410["system_tier"])),
                ("Dominant family", str(v410["dominant_family"])),
                ("Family margin", fmt_num(v410["dominant_family_margin"])),
            ])
            ui.label("Per-family margins (TF / PF / CS)").classes("text-subtitle2")
            render_json_blob(v410["family_margins"])
            ui.label("Per-family tiers / dominant aspects").classes("text-subtitle2 q-mt-sm")
            render_json_blob({"tiers": v410["family_tiers"], "dominants": v410["family_dominants"]})
            if v410.get("provenance"):
                ui.label(str(v410["provenance"])).classes("text-caption q-mt-sm")
        else:
            ui.label(
                "TF/PF/CS SC system depth (v410) is OFF — enable include_magnet_sc_system_authority_v410."
            ).classes("text-caption")

    from ui_nicegui.lib.pd_parity_helpers import machine_v412_summary

    v412 = machine_v412_summary(out)
    with ui.expansion("Machine-build / radial closure (v412) [PROXY]", icon="view_timeline").classes(
        "w-full q-mt-md"
    ):
        if v412:
            ui.badge("PROXY overlay — not PROCESS MFILE parity").props("color=orange")
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
            if v412.get("provenance"):
                ui.label(str(v412["provenance"])).classes("text-caption")
        else:
            ui.label(
                "Machine-build / radial closure (v412) is OFF — enable include_machine_build_authority_v412."
            ).classes("text-caption")

    from ui_nicegui.lib.pd_parity_helpers import plant_v419_summary

    v419 = plant_v419_summary(out)
    with ui.expansion("Plant Sankey ledger (v419) [PROXY]", icon="account_tree").classes(
        "w-full q-mt-md"
    ):
        if v419:
            ui.badge("PROXY overlay — not PROCESS MFILE parity").props("color=orange")
            kpi_row([
                ("System tier", str(v419["system_tier"])),
                ("Conservation", "OK" if v419.get("conservation_ok") else "FAIL"),
                ("Dominant", str(v419.get("dominant_aspect", "-"))),
                ("f_recirc", fmt_num(v419.get("f_recirc"))),
            ])
            if v419.get("recirc_breakdown"):
                ui.label("Recirc breakdown [MW(e)]").classes("text-subtitle2")
                render_json_blob(v419["recirc_breakdown"])
            if v419.get("narrative"):
                ui.label(str(v419["narrative"])).classes("text-caption q-mt-sm")
            if v419.get("provenance"):
                ui.label(str(v419["provenance"])).classes("text-caption")
            ui.label(
                "Pe_net display must use plant_kpi_honesty.v1 watermark on hard-infeasible points."
            ).classes("text-caption text-orange")
        else:
            ui.label(
                "Plant Sankey ledger (v419) is OFF — enable include_plant_sankey_ledger_authority_v419."
            ).classes("text-caption")

    from ui_nicegui.lib.pd_parity_helpers import avail_v420_summary

    v420 = avail_v420_summary(out)
    with ui.expansion("Availability→OPEX/LCOE coupling (v420) [PROXY]", icon="timeline").classes(
        "w-full q-mt-md"
    ):
        if v420:
            ui.badge("PROXY overlay — not PROCESS MFILE parity").props("color=orange")
            kpi_row([
                ("Availability", fmt_num(v420.get("availability"))),
                ("A source", str(v420.get("availability_source", "-"))),
                ("OPEX [MUSD/y]", fmt_num(v420.get("OPEX_total_MUSD_per_y"))),
                ("LCOE PROXY [USD/MWh]", fmt_num(v420.get("LCOE_USD_per_MWh"))),
            ])
            kpi_row([
                ("Dominant OPEX", str(v420.get("dominant_opex_driver", "-"))),
                ("CAPEX basis", str(v420.get("CAPEX_source", "-"))),
                ("Replacement basis", str(v420.get("replacement_source", "-"))),
                ("Consistency", "OK" if v420.get("consistency_ok") else "FAIL"),
            ])
            if v420.get("opex_breakdown_MUSD_per_y"):
                ui.label("OPEX breakdown [MUSD/y]").classes("text-subtitle2")
                render_json_blob(v420["opex_breakdown_MUSD_per_y"])
            if v420.get("narrative"):
                ui.label(str(v420["narrative"])).classes("text-caption q-mt-sm")
            if v420.get("provenance"):
                ui.label(str(v420["provenance"])).classes("text-caption")
            ui.label(
                "LCOE display must use plant_kpi_honesty.v1 watermark on hard-infeasible points."
            ).classes("text-caption text-orange")
        else:
            ui.label(
                "Availability→OPEX/LCOE coupling (v420) is OFF — enable include_availability_opex_lcoe_authority_v420."
            ).classes("text-caption")
