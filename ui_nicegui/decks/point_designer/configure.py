"""Configure tab — Truth Console inputs + templates + overlay catalog."""
from __future__ import annotations

import json

from nicegui import ui

from ui_nicegui.decks.point_designer.configure_advanced_materials import render_advanced_materials
from ui_nicegui.decks.point_designer.configure_engineering import render_engineering_plant
from ui_nicegui.decks.point_designer.configure_governance import render_design_governance
from ui_nicegui.decks.point_designer.configure_nuclear_intake import render_nuclear_dataset_intake
from ui_nicegui.decks.point_designer.configure_operating_targets import render_operating_targets
from ui_nicegui.decks.point_designer.configure_physics import render_model_options, render_power_composition
from ui_nicegui.decks.point_designer.configure_systems_bridge import render_systems_precheck_bridge
from ui_nicegui.lib.lazy_expansion import lazy_expansion
from ui_nicegui.lib.pd_overlay_catalog import OVERLAY_GROUP_SPECS, seed_overlay_defaults
from ui_nicegui.lib.pd_overlay_knobs import render_overlay_numeric_panels
from ui_nicegui.lib.pd_panel_labels import (
    CONFIGURE_SECTION_ORDER,
    CONFIGURE_SECTIONS,
    overlay_caption,
    overlay_display_label,
    overlay_group_caption,
    overlay_group_title,
)
from ui_nicegui.lib.pd_parity_helpers import load_industrial_template, template_names
from ui_nicegui.lib.pd_input_guardrails import unrealistic_point_input_warnings
from ui_nicegui.lib.pd_solver_banner import solver_target_rows
from ui_nicegui.lib.pd_solver_helpers import inputs_stale
from ui_nicegui.lib.session_store import apply_template_overrides, clear_point_designer
from ui_nicegui.lib.ui_safe_numbers import finite_ui_number
from ui_nicegui.session import DesignSession


def _render_overlay_groups(session: DesignSession) -> None:
    ui.label("Authority & plant overlays — master toggles").classes("text-subtitle2 q-mt-md")
    ui.label(
        "Quick enable/disable for governance modules. Detailed numeric caps appear below when enabled, "
        "and some modules also have dedicated sections above."
    ).classes("text-caption q-mb-sm")

    for group_id, toggles in OVERLAY_GROUP_SPECS:

        def _group_body(gid=group_id, items=toggles) -> None:
            ui.label(overlay_group_caption(gid)).classes("text-caption q-mb-sm")
            for key, default in items:
                session.overlay.setdefault(key, default)
                with ui.column().classes("gap-0 q-mb-xs"):
                    ui.checkbox(
                        overlay_display_label(key),
                        value=bool(session.overlay.get(key, default)),
                        on_change=lambda e, k=key: session.overlay.__setitem__(k, bool(e.value)),
                    )
                    ui.label(overlay_caption(key)).classes("text-caption text-grey q-pl-lg")

        lazy_expansion(overlay_group_title(group_id), icon="tune", body=_group_body)


def _render_templates(session: DesignSession, *, on_refresh=None) -> None:
    names = template_names()
    if not names:
        ui.label("No industrial scenario templates found.").classes("text-caption")
        return

    sel = ui.select(["(select)"] + names, label="Template", value="(select)").classes("w-full")
    preview = ui.textarea(value="").props("readonly outlined dense rows=6").classes("w-full")

    def _preview_template() -> None:
        if sel.value and sel.value != "(select)":
            _, payload = load_industrial_template(str(sel.value))
            preview.value = json.dumps(payload, indent=2, sort_keys=True, default=str)
        else:
            preview.value = ""

    sel.on("update:model-value", lambda: _preview_template())

    def _load_template() -> None:
        if not sel.value or sel.value == "(select)":
            ui.notify("Select a template first.", type="warning")
            return
        overrides, _ = load_industrial_template(str(sel.value))
        clear_point_designer(session)
        apply_template_overrides(session, overrides)
        ui.notify(f"Loaded template: {sel.value}", type="positive")
        if on_refresh:
            on_refresh()

    ui.button("Load template into Point Designer", on_click=_load_template).classes("q-mt-sm")
    ui.label(
        "Industrial templates apply a **partial merge** of listed keys only — residual "
        "inputs (e.g. Zeff, δ, confinement scaling) from the prior machine are retained. "
        "For a full clean basis, load a Champion / reference preset from Helm or Studio entry."
    ).classes("text-caption text-orange q-mb-sm")


def _render_section_body(session: DesignSession, section_id: str) -> None:
    inp = session.inputs

    if section_id == "machine_geometry":
        with ui.grid(columns=2).classes("w-full gap-2"):
            ui.number(
                "R₀ (m)",
                value=finite_ui_number(inp["R0_m"], unset=1.81),
                min=0.01,
                step=0.01,
                on_change=lambda e: inp.__setitem__("R0_m", e.value),
            )
            ui.number(
                "a (m)",
                value=finite_ui_number(inp["a_m"], unset=0.62),
                min=0.1,
                step=0.01,
                on_change=lambda e: inp.__setitem__("a_m", e.value),
            )
            ui.number(
                "κ (–)",
                value=finite_ui_number(inp["kappa"], unset=1.8),
                min=1.0,
                max=3.2,
                step=0.05,
                on_change=lambda e: inp.__setitem__("kappa", e.value),
            )
            ui.number(
                "δ (–)",
                value=finite_ui_number(inp["delta"], unset=0.0),
                min=0.0,
                max=0.8,
                step=0.02,
                on_change=lambda e: inp.__setitem__("delta", e.value),
            )
            ui.number(
                "B₀ (T)",
                value=finite_ui_number(inp["Bt_T"], unset=10.0),
                min=0.5,
                max=25.0,
                step=0.1,
                on_change=lambda e: inp.__setitem__("Bt_T", e.value),
            )
        return

    if section_id == "plasma_state":
        with ui.grid(columns=2).classes("w-full gap-2"):
            ui.number(
                "Ti (keV)",
                value=finite_ui_number(inp["Ti_keV"], unset=10.0),
                min=1.0,
                max=40.0,
                step=0.25,
                on_change=lambda e: inp.__setitem__("Ti_keV", e.value),
            )
            ui.number(
                "Ti/Te",
                value=finite_ui_number(inp["Ti_over_Te"], unset=1.0),
                min=0.5,
                step=0.1,
                on_change=lambda e: inp.__setitem__("Ti_over_Te", e.value),
            )
            ui.number(
                "Ip (MA)",
                value=finite_ui_number(inp["Ip_MA"], unset=8.0),
                min=0.1,
                step=0.1,
                on_change=lambda e: inp.__setitem__("Ip_MA", e.value),
            )
            ui.number(
                "fG",
                value=finite_ui_number(inp["fG"], unset=0.8),
                min=0.0,
                max=2.0,
                step=0.01,
                on_change=lambda e: inp.__setitem__("fG", e.value),
            )
            ui.number(
                "Zeff",
                value=finite_ui_number(inp["zeff"], unset=1.8),
                min=1.0,
                step=0.05,
                on_change=lambda e: inp.__setitem__("zeff", e.value),
            )
            ui.number(
                "Fuel dilution",
                value=finite_ui_number(inp["dilution_fuel"], unset=0.85),
                min=0.0,
                max=1.0,
                step=0.01,
                on_change=lambda e: inp.__setitem__("dilution_fuel", e.value),
            )
        return

    if section_id == "heating_fuel":
        with ui.grid(columns=2).classes("w-full gap-2"):
            ui.number(
                "Paux (MW)",
                value=finite_ui_number(inp["Paux_MW"], unset=50.0),
                min=0.0,
                max=500.0,
                step=1.0,
                on_change=lambda e: inp.__setitem__("Paux_MW", e.value),
            )
            ui.number(
                "Paux for Q_DT_eqv (MW)",
                value=finite_ui_number(inp["Paux_for_Q_MW"], unset=50.0),
                min=0.0,
                step=0.1,
                on_change=lambda e: inp.__setitem__("Paux_for_Q_MW", e.value),
            )
        ui.label("Fuel mode is set in Operating targets & solver.").classes("text-caption")
        return

    if section_id == "model_options":
        render_model_options(session, embedded=True)
        return

    if section_id == "power_composition":
        render_power_composition(session, embedded=True)
        return

    if section_id == "magnets_shielding":
        with ui.grid(columns=2).classes("w-full gap-2"):
            ui.select(
                ["HTS_REBCO", "LTS_NB3SN", "LTS_NBTI", "COPPER"],
                label="Magnet technology",
                value=inp["magnet_technology"],
                on_change=lambda e: inp.__setitem__("magnet_technology", e.value),
            )
            ui.number(
                "Tcoil (K)",
                value=finite_ui_number(inp["Tcoil_K"], unset=20.0),
                min=4.0,
                max=300.0,
                step=1.0,
                on_change=lambda e: inp.__setitem__("Tcoil_K", e.value),
            )
            ui.number(
                "Shield thickness (m)",
                value=finite_ui_number(inp["t_shield_m"], unset=0.8),
                min=0.0,
                step=0.01,
                on_change=lambda e: inp.__setitem__("t_shield_m", e.value),
            )
        return

    if section_id == "engineering_plant":
        render_engineering_plant(session, embedded=True)
        render_nuclear_dataset_intake(session)
        return

    if section_id == "operating_targets":
        render_operating_targets(session, embedded=True)


def render_configure(session: DesignSession, *, on_evaluate, on_refresh=None) -> None:
    inp = session.inputs
    seed_overlay_defaults(session.overlay)

    ui.label("Control Deck").classes("text-subtitle1")
    with ui.row().classes("w-full items-center gap-2 q-mb-sm flex-wrap"):
        ui.checkbox(
            "Confirm clear evaluation history",
            value=bool(getattr(session, "pd_clear_confirm", False)),
            on_change=lambda e: setattr(session, "pd_clear_confirm", bool(e.value)),
        )

        def _clear_pd() -> None:
            if not bool(getattr(session, "pd_clear_confirm", False)):
                ui.notify("Check Confirm clear evaluation history first.", type="warning")
                return
            clear_point_designer(session)
            session.pd_clear_confirm = False
            ui.notify(
                "Cleared Point Designer evaluation history (outputs/artifacts). "
                "Machine inputs were not reset.",
                type="info",
            )
            if on_refresh:
                on_refresh()

        ui.button(
            "Clear evaluation history",
            icon="delete_sweep",
            on_click=_clear_pd,
        ).props("outline")
    ui.label(
        "Clears last evaluate outputs, artifacts, and forensics — does **not** reset machine inputs. "
        "Use Templates / presets for a clean basis."
    ).classes("text-caption text-grey q-mb-sm")

    render_design_governance(session)

    if str(session.pd_eval_mode) in ("solver", "envelope") and session.pd_last_outputs:
        paux = finite_ui_number(inp.get("Paux_MW"), unset=0)
        ui.label(
            f"Last solve operating point: Ip = {finite_ui_number(inp.get('Ip_MA'), unset=0):.4g} MA, "
            f"fG = {finite_ui_number(inp.get('fG'), unset=0):.4g}, Paux = {paux:.4g} MW"
        ).classes("text-caption text-info q-mb-sm")
        tgt_rows = solver_target_rows(session)
        if tgt_rows:
            ui.table(
                columns=[
                    {"name": "quantity", "label": "Quantity", "field": "quantity", "align": "left"},
                    {"name": "target", "label": "Target", "field": "target"},
                    {"name": "achieved", "label": "Achieved", "field": "achieved"},
                    {"name": "status", "label": "Status", "field": "status"},
                ],
                rows=tgt_rows,
                row_key="quantity",
            ).classes("w-full q-mb-sm")

    try:
        guardrails = unrealistic_point_input_warnings(session.build_point_inputs())
    except Exception:
        guardrails = []
    if guardrails:
        with ui.expansion("Input guardrails (review before evaluate)", icon="warning").classes("w-full q-mb-sm"):
            for line in guardrails[:6]:
                ui.label(line).classes("text-caption text-orange")

    # Lazy bodies: deck-switch remount must not rebuild every Configure widget tree.
    for section_id in CONFIGURE_SECTION_ORDER:
        title, icon, help_text = CONFIGURE_SECTIONS[section_id]
        if section_id == "templates":
            lazy_expansion(
                title,
                icon=icon,
                help_text=help_text,
                body=lambda s=session, r=on_refresh: _render_templates(s, on_refresh=r),
            )
            continue
        lazy_expansion(
            title,
            icon=icon,
            help_text=help_text,
            body=lambda sid=section_id: _render_section_body(session, sid),
        )

    _render_overlay_groups(session)

    lazy_expansion(
        "Authority overlay numeric panels",
        icon="tune",
        help_text="Numeric caps for enabled overlays — open after enabling toggles above.",
        body=lambda: render_overlay_numeric_panels(session),
    )
    lazy_expansion(
        "Advanced materials & nuclear data inputs",
        icon="science",
        body=lambda: render_advanced_materials(session, embedded=True),
    )
    render_systems_precheck_bridge(session)

    ui.separator()

    if session.pd_last_run_ts and inputs_stale(session):
        ui.label("Inputs changed since last evaluation — click Evaluate Point to refresh.").classes(
            "text-warning q-mb-sm"
        )

    ui.button("Evaluate Point", color="primary", on_click=on_evaluate).classes("w-full")

    if session.pd_last_run_ts:
        from datetime import datetime

        ui.label(
            f"Last evaluation: {datetime.fromtimestamp(session.pd_last_run_ts).strftime('%Y-%m-%d %H:%M:%S')}"
        ).classes("text-caption text-grey")
