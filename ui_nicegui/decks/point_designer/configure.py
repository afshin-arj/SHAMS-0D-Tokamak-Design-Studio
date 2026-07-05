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

from ui_nicegui.lib.pd_solver_helpers import inputs_stale

from ui_nicegui.lib.session_store import apply_template_overrides, clear_point_designer

from ui_nicegui.lib.ui_safe_numbers import finite_ui_number

from ui_nicegui.session import DesignSession





def _render_overlay_groups(session: DesignSession) -> None:
    ui.label(
        "Authority & plant overlays — master toggles"
    ).classes("text-subtitle2 q-mt-md")
    ui.label(
        "Quick enable/disable for governance modules. Detailed numeric caps appear below when enabled, "
        "and some modules also have dedicated sections above."
    ).classes("text-caption q-mb-sm")

    for group_id, toggles in OVERLAY_GROUP_SPECS:

        with ui.expansion(overlay_group_title(group_id), icon="tune").classes("w-full"):

            ui.label(overlay_group_caption(group_id)).classes("text-caption q-mb-sm")

            for key, default in toggles:

                session.overlay.setdefault(key, default)

                with ui.column().classes("gap-0 q-mb-xs"):

                    ui.checkbox(

                        overlay_display_label(key),

                        value=bool(session.overlay.get(key, default)),

                        on_change=lambda e, k=key: session.overlay.__setitem__(k, bool(e.value)),

                    )

                    ui.label(overlay_caption(key)).classes("text-caption text-grey q-pl-lg")





def render_configure(session: DesignSession, *, on_evaluate) -> None:

    inp = session.inputs

    seed_overlay_defaults(session.overlay)



    ui.label("Control Deck").classes("text-subtitle1")

    ui.button(

        "New machine (clear Point Designer)",

        icon="delete_sweep",

        on_click=lambda: (clear_point_designer(session), ui.notify("Point Designer cleared.", type="info")),

    ).props("outline").classes("q-mb-sm")

    render_design_governance(session)

    for section_id in CONFIGURE_SECTION_ORDER:

        title, icon, help_text = CONFIGURE_SECTIONS[section_id]



        if section_id == "templates":

            with ui.expansion(title, icon=icon).classes("w-full"):

                ui.label(help_text).classes("text-caption q-mb-sm")

                names = template_names()

                if not names:

                    ui.label("No industrial scenario templates found.").classes("text-caption")

                else:

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



                    ui.button("Load template into Point Designer", on_click=_load_template).classes("q-mt-sm")

            continue



        with ui.expansion(title, icon=icon).classes("w-full"):

            ui.label(help_text).classes("text-caption q-mb-sm")



            if section_id == "machine_geometry":

                with ui.grid(columns=2).classes("w-full gap-2"):

                    ui.number("R0 (m)", value=finite_ui_number(inp["R0_m"], unset=1.81), min=0.01, step=0.01,

                              on_change=lambda e: inp.__setitem__("R0_m", e.value))

                    ui.number("a (m)", value=finite_ui_number(inp["a_m"], unset=0.62), min=0.1, step=0.01,

                              on_change=lambda e: inp.__setitem__("a_m", e.value))

                    ui.number("kappa", value=finite_ui_number(inp["kappa"], unset=1.8), min=1.0, max=3.2, step=0.05,

                              on_change=lambda e: inp.__setitem__("kappa", e.value))

                    ui.number("delta", value=finite_ui_number(inp["delta"], unset=0.0), min=0.0, max=0.8, step=0.02,

                              on_change=lambda e: inp.__setitem__("delta", e.value))

                    ui.number("B0 (T)", value=finite_ui_number(inp["Bt_T"], unset=10.0), min=0.5, max=25.0, step=0.1,

                              on_change=lambda e: inp.__setitem__("Bt_T", e.value))



            elif section_id == "plasma_state":

                with ui.grid(columns=2).classes("w-full gap-2"):

                    ui.number("Ti (keV)", value=finite_ui_number(inp["Ti_keV"], unset=10.0), min=1.0, max=40.0, step=0.25,

                              on_change=lambda e: inp.__setitem__("Ti_keV", e.value))

                    ui.number("Ti/Te", value=finite_ui_number(inp["Ti_over_Te"], unset=1.0), min=0.5, step=0.1,

                              on_change=lambda e: inp.__setitem__("Ti_over_Te", e.value))

                    ui.number("Ip (MA)", value=finite_ui_number(inp["Ip_MA"], unset=8.0), min=0.1, step=0.1,

                              on_change=lambda e: inp.__setitem__("Ip_MA", e.value))

                    ui.number("fG", value=finite_ui_number(inp["fG"], unset=0.8), min=0.0, max=2.0, step=0.01,

                              on_change=lambda e: inp.__setitem__("fG", e.value))

                    ui.number("Zeff", value=finite_ui_number(inp["zeff"], unset=1.8), min=1.0, step=0.05,

                              on_change=lambda e: inp.__setitem__("zeff", e.value))

                    ui.number("Fuel dilution", value=finite_ui_number(inp["dilution_fuel"], unset=0.85), min=0.0, max=1.0, step=0.01,

                              on_change=lambda e: inp.__setitem__("dilution_fuel", e.value))



            elif section_id == "heating_fuel":

                with ui.grid(columns=2).classes("w-full gap-2"):

                    ui.number("Paux (MW)", value=finite_ui_number(inp["Paux_MW"], unset=50.0), min=0.0, max=500.0, step=1.0,

                              on_change=lambda e: inp.__setitem__("Paux_MW", e.value))

                    ui.number("Paux for Q (MW)", value=finite_ui_number(inp["Paux_for_Q_MW"], unset=50.0), min=0.0, step=0.1,

                              on_change=lambda e: inp.__setitem__("Paux_for_Q_MW", e.value))

                    ui.select(["DT", "DD"], label="Fuel mode", value=inp["fuel_mode"],

                              on_change=lambda e: inp.__setitem__("fuel_mode", e.value))



            elif section_id == "model_options":

                render_model_options(session, embedded=True)



            elif section_id == "power_composition":

                render_power_composition(session, embedded=True)



            elif section_id == "magnets_shielding":

                with ui.grid(columns=2).classes("w-full gap-2"):

                    ui.select(

                        ["HTS_REBCO", "LTS_NB3SN", "LTS_NBTI", "COPPER"],

                        label="Magnet technology",

                        value=inp["magnet_technology"],

                        on_change=lambda e: inp.__setitem__("magnet_technology", e.value),

                    )

                    ui.number("Tcoil (K)", value=finite_ui_number(inp["Tcoil_K"], unset=20.0), min=4.0, max=300.0, step=1.0,

                              on_change=lambda e: inp.__setitem__("Tcoil_K", e.value))

                    ui.number("Shield thickness (m)", value=finite_ui_number(inp["t_shield_m"], unset=0.8), min=0.0, step=0.01,

                              on_change=lambda e: inp.__setitem__("t_shield_m", e.value))



            elif section_id == "engineering_plant":

                render_engineering_plant(session, embedded=True)

                render_nuclear_dataset_intake(session)



            elif section_id == "operating_targets":

                render_operating_targets(session, embedded=True)



    _render_overlay_groups(session)

    render_overlay_numeric_panels(session)
    render_advanced_materials(session)
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

