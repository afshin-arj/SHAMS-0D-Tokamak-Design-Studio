"""Engineering & plant feasibility — confidence, subsystems, build, CD, control."""

from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.pd_panel_labels import CONFIGURE_SECTIONS
from ui_nicegui.lib.ui_safe_numbers import finite_ui_number
from ui_nicegui.session import DesignSession

_WARN_FRACS = {
    "Conservative": {"max": 0.85, "min": 1.20},
    "Nominal": {"max": 0.90, "min": 1.10},
    "Aggressive": {"max": 0.95, "min": 1.05},
}

_CONFIDENCE_PRESETS = {
    "Conservative": {
        "tblanket_m": 0.60, "t_vv_m": 0.08, "t_gap_m": 0.03,
        "t_tf_struct_m": 0.18, "t_tf_wind_m": 0.12,
        "Bpeak_factor": 1.30, "sigma_allow_MPa": 800.0,
        "q_div_max_MW_m2": 7.0, "TBR_min": 1.10, "P_net_min_MW": 0.0,
    },
    "Nominal": {
        "tblanket_m": 0.50, "t_vv_m": 0.06, "t_gap_m": 0.02,
        "t_tf_struct_m": 0.15, "t_tf_wind_m": 0.10,
        "Bpeak_factor": 1.25, "sigma_allow_MPa": 850.0,
        "q_div_max_MW_m2": 10.0, "TBR_min": 1.05, "P_net_min_MW": 0.0,
    },
    "Aggressive": {
        "tblanket_m": 0.40, "t_vv_m": 0.05, "t_gap_m": 0.015,
        "t_tf_struct_m": 0.12, "t_tf_wind_m": 0.08,
        "Bpeak_factor": 1.20, "sigma_allow_MPa": 900.0,
        "q_div_max_MW_m2": 15.0, "TBR_min": 1.00, "P_net_min_MW": 0.0,
    },
}


def _knob(session: DesignSession, key: str, default):
    if key not in session.knobs:
        session.knobs[key] = default
    return session.knobs[key]


def _num_knob(session: DesignSession, key: str, default) -> float:
    raw = session.knobs.get(key, default)
    return finite_ui_number(raw, unset=finite_ui_number(default, unset=0.0))


def _subsystem(session: DesignSession, key: str, default: bool = True) -> bool:
    subs = session.knobs.setdefault("_subsystem_enabled", {})
    return bool(subs.setdefault(key, default))


def _set_subsystem(session: DesignSession, key: str, value: bool) -> None:
    subs = session.knobs.setdefault("_subsystem_enabled", {})
    subs[key] = bool(value)


def _apply_confidence(session: DesignSession, level: str) -> None:
    session.knobs["pd_confidence"] = level
    fracs = _WARN_FRACS.get(level, _WARN_FRACS["Nominal"])
    session.knobs["_warn_frac_max"] = fracs["max"]
    session.knobs["_warn_frac_min"] = fracs["min"]
    preset = _CONFIDENCE_PRESETS.get(level, _CONFIDENCE_PRESETS["Nominal"])
    for k, v in preset.items():
        session.knobs[k] = v


def render_engineering_plant(session: DesignSession, *, embedded: bool = False) -> None:
    """Confidence presets, subsystem toggles, build/magnets/divertor/neutronics, CD, control."""
    inp = session.inputs
    title, icon, help_text = CONFIGURE_SECTIONS["engineering_plant"]
    confidence = str(session.knobs.get("pd_confidence", "Nominal"))
    if confidence not in _WARN_FRACS:
        confidence = "Nominal"
        _apply_confidence(session, confidence)

    def _body() -> None:
        ui.toggle(
            ["Conservative", "Nominal", "Aggressive"],
            value=confidence,
            on_change=lambda e: (
                _apply_confidence(session, str(e.value)),
                ui.notify(f"Engineering confidence → {e.value} (limits updated; re-evaluate).", type="info"),
            ),
        ).props("spread no-caps").classes("q-mb-sm")
        ui.label("Confidence level — controls default assumptions and WARN bands.").classes("text-caption")
        ui.label(
            "Availability and structural-life numeric caps: enable the matching overlays below, "
            "then open Authority overlay numeric panels at the bottom of Configure."
        ).classes("text-caption q-mb-sm")

        with ui.grid(columns=2).classes("w-full gap-2"):
            for key, label, default in (
                ("build", "Build & radial build", True),
                ("magnets", "Magnets & HTS", True),
                ("divertor", "Divertor / SOL", True),
                ("neutronics", "Neutronics (TBR, lifetime)", True),
                ("net_power", "Net power / electrical balance", True),
                ("fuelcycle", "Fuel-cycle (tritium throughput)", False),
            ):
                ui.checkbox(
                    label,
                    value=_subsystem(session, key, default),
                    on_change=lambda e, k=key: _set_subsystem(session, k, e.value),
                )

        session.overlay.setdefault("include_economics_v360", False)
        ui.checkbox(
            "Plant economics overlay (CAPEX proxy)",
            value=bool(session.overlay.get("include_economics_v360", False)),
            on_change=lambda e: session.overlay.__setitem__("include_economics_v360", bool(e.value)),
        )

        if _subsystem(session, "build"):
            with ui.expansion("Radial build thicknesses", icon="layers").classes("w-full"):
                preset = _CONFIDENCE_PRESETS.get(confidence, _CONFIDENCE_PRESETS["Nominal"])
                with ui.grid(columns=2).classes("w-full gap-2"):
                    for key, label in (
                        ("tblanket_m", "Blanket thickness (m)"),
                        ("t_vv_m", "VV thickness (m)"),
                        ("t_gap_m", "Inboard gap (m)"),
                        ("t_tf_struct_m", "TF structure (m)"),
                        ("t_tf_wind_m", "TF winding pack (m)"),
                    ):
                        ui.number(
                            label,
                            value=_num_knob(session, key, preset.get(key, 0.1)),
                            min=0.0, step=0.005,
                            on_change=lambda e, k=key: session.knobs.__setitem__(k, e.value),
                        )

        if _subsystem(session, "magnets"):
            with ui.expansion("Magnets & HTS limits", icon="electrical_services").classes("w-full"):
                preset = _CONFIDENCE_PRESETS.get(confidence, _CONFIDENCE_PRESETS["Nominal"])
                with ui.grid(columns=2).classes("w-full gap-2"):
                    ui.number(
                        "B_peak/B₀ factor",
                        value=_num_knob(session, "Bpeak_factor", preset["Bpeak_factor"]),
                        min=1.0, step=0.01,
                        on_change=lambda e: session.knobs.__setitem__("Bpeak_factor", e.value),
                    )
                    ui.number(
                        "Allowable hoop stress (MPa)",
                        value=_num_knob(session, "sigma_allow_MPa", preset["sigma_allow_MPa"]),
                        min=10.0, step=10.0,
                        on_change=lambda e: session.knobs.__setitem__("sigma_allow_MPa", e.value),
                    )

        if _subsystem(session, "divertor"):
            with ui.expansion("Divertor / SOL limits", icon="whatshot").classes("w-full"):
                preset = _CONFIDENCE_PRESETS.get(confidence, _CONFIDENCE_PRESETS["Nominal"])
                ui.number(
                    "Max divertor heat flux (MW/m²)",
                    value=_num_knob(session, "q_div_max_MW_m2", preset["q_div_max_MW_m2"]),
                    min=0.1, step=0.5,
                    on_change=lambda e: session.knobs.__setitem__("q_div_max_MW_m2", e.value),
                )

        with ui.expansion("Exhaust & performance screening caps", icon="filter_alt").classes("w-full"):
            ui.label(
                "Optional hard/diagnostic caps on PointInputs — leave blank to disable."
            ).classes("text-caption q-mb-sm")
            with ui.grid(columns=2).classes("w-full gap-2"):
                ui.number(
                    "Detachment index min",
                    value=finite_ui_number(inp.get("detachment_index_min", float("nan"))),
                    step=0.05,
                    on_change=lambda e: inp.__setitem__("detachment_index_min", e.value),
                )
                ui.number(
                    "Detachment index max",
                    value=finite_ui_number(inp.get("detachment_index_max", float("nan"))),
                    step=0.05,
                    on_change=lambda e: inp.__setitem__("detachment_index_max", e.value),
                )
                ui.number(
                    "Max total radiative fraction",
                    value=finite_ui_number(inp.get("f_rad_total_max", float("nan"))),
                    min=0.0, max=2.0, step=0.05,
                    on_change=lambda e: inp.__setitem__("f_rad_total_max", e.value),
                )
                ui.number(
                    "Min fuel-ion fraction",
                    value=finite_ui_number(inp.get("fuel_ion_fraction_min", float("nan"))),
                    min=0.0, max=1.0, step=0.01,
                    on_change=lambda e: inp.__setitem__("fuel_ion_fraction_min", e.value),
                )
                ui.number(
                    "Min Q_effective",
                    value=finite_ui_number(inp.get("Q_effective_min", float("nan"))),
                    min=0.0, step=0.05,
                    on_change=lambda e: inp.__setitem__("Q_effective_min", e.value),
                )

        if _subsystem(session, "neutronics"):
            with ui.expansion("Neutronics screening", icon="shield").classes("w-full"):
                preset = _CONFIDENCE_PRESETS.get(confidence, _CONFIDENCE_PRESETS["Nominal"])
                with ui.grid(columns=2).classes("w-full gap-2"):
                    ui.number(
                        "Minimum TBR",
                        value=_num_knob(session, "TBR_min", preset["TBR_min"]),
                        min=0.0, step=0.01,
                        on_change=lambda e: session.knobs.__setitem__("TBR_min", e.value),
                    )
                    ui.number(
                        "Neutron port fraction",
                        value=_num_knob(session, "port_fraction", 0.05),
                        min=0.0, max=0.5, step=0.01,
                        on_change=lambda e: session.knobs.__setitem__("port_fraction", e.value),
                    )
                    ui.number(
                        "Li-6 enrichment",
                        value=_num_knob(session, "li6_enrichment", 0.6),
                        min=0.0, max=1.0, step=0.01,
                        on_change=lambda e: session.knobs.__setitem__("li6_enrichment", e.value),
                    )
                    ui.number(
                        "Max neutron wall load (MW/m²)",
                        value=_num_knob(session, "neutron_wall_load_max_MW_m2", float("nan")),
                        min=0.0, step=0.5,
                        on_change=lambda e: session.knobs.__setitem__("neutron_wall_load_max_MW_m2", e.value),
                    )
                    ui.number(
                        "Max FW DPA per year",
                        value=_num_knob(session, "fw_dpa_max_per_year", float("nan")),
                        min=0.0, step=0.5,
                        on_change=lambda e: session.knobs.__setitem__("fw_dpa_max_per_year", e.value),
                    )
                ui.select(
                    ["LiPb", "FLiBe", "PbLi", "FLiBeBe"],
                    label="Blanket archetype",
                    value=str(_knob(session, "blanket_type", "LiPb")),
                    on_change=lambda e: session.knobs.__setitem__("blanket_type", e.value),
                ).classes("w-full")
                with ui.grid(columns=2).classes("w-full gap-2"):
                    for key, label in (
                        ("fw_material", "First-wall material tag"),
                        ("blanket_material", "Blanket material tag"),
                        ("shield_material", "Shield material tag"),
                    ):
                        ui.input(
                            label,
                            value=str(_knob(session, key, "RAFM")),
                            on_change=lambda e, k=key: session.knobs.__setitem__(k, e.value),
                        )

        with ui.expansion("Current drive & NI closure", icon="electric_bolt").classes("w-full"):
            session.overlay.setdefault("include_current_drive", False)
            ui.checkbox(
                "Current drive & NI closure (compute P_cd)",
                value=bool(session.overlay.get("include_current_drive", False)),
                on_change=lambda e: session.overlay.__setitem__("include_current_drive", bool(e.value)),
            )
            with ui.grid(columns=2).classes("w-full gap-2"):
                ui.number(
                    "Target f_NI",
                    value=_num_knob(session, "f_noninductive_target", 1.0),
                    min=0.0, max=1.2, step=0.02,
                    on_change=lambda e: session.knobs.__setitem__("f_noninductive_target", e.value),
                )
                ui.number(
                    "Max launched CD power (MW)",
                    value=_num_knob(session, "Pcd_max_MW", 200.0),
                    min=0.0, step=10.0,
                    on_change=lambda e: session.knobs.__setitem__("Pcd_max_MW", e.value),
                )
            ui.select(
                ["ECCD", "LHCD", "NBI", "ICRF"],
                label="CD actuator",
                value=str(_knob(session, "cd_actuator", "ECCD")),
                on_change=lambda e: session.knobs.__setitem__("cd_actuator", e.value),
            ).classes("w-full")
            session.overlay.setdefault("cd_mix_enable", False)
            ui.checkbox(
                "Enable CD actuator mix",
                value=bool(session.overlay.get("cd_mix_enable", False)),
                on_change=lambda e: session.overlay.__setitem__("cd_mix_enable", bool(e.value)),
            )

        with ui.expansion("Control system contracts", icon="tune").classes("w-full"):
            session.overlay.setdefault("include_control_contracts", False)
            ui.checkbox(
                "Enable control contracts (VS/PF/SOL/RWM)",
                value=bool(session.overlay.get("include_control_contracts", False)),
                on_change=lambda e: session.overlay.__setitem__("include_control_contracts", bool(e.value)),
            )
            with ui.grid(columns=2).classes("w-full gap-2"):
                for key, label in (
                    ("vs_control_power_max_MW", "Max VS control power (MW)"),
                    ("pf_I_peak_max_MA", "Max PF peak current (MA)"),
                    ("rwm_control_power_max_MW", "Max RWM control power (MW)"),
                ):
                    ui.number(
                        label,
                        value=_num_knob(session, key, float("nan")),
                        min=0.0, step=0.5,
                        on_change=lambda e, k=key: session.knobs.__setitem__(k, e.value),
                    )

        with ui.expansion("Irradiation damage → strength", icon="construction").classes("w-full"):
            session.overlay.setdefault("include_damage_strength_coupling_v393", False)
            ui.checkbox(
                "Enable damage → strength coupling",
                value=bool(session.overlay.get("include_damage_strength_coupling_v393", False)),
                on_change=lambda e: session.overlay.__setitem__(
                    "include_damage_strength_coupling_v393", bool(e.value)
                ),
            )
            with ui.grid(columns=2).classes("w-full gap-2"):
                ui.number(
                    "Design life (FPY)",
                    value=_num_knob(session, "design_life_fpy_v393", 10.0),
                    min=0.0, step=1.0,
                    on_change=lambda e: session.knobs.__setitem__("design_life_fpy_v393", e.value),
                )
                ui.number(
                    "Degradation slope k (1/DPA)",
                    value=_num_knob(session, "k_allow_deg_per_dpa_v393", 0.003),
                    min=0.0, step=0.001,
                    on_change=lambda e: session.knobs.__setitem__("k_allow_deg_per_dpa_v393", e.value),
                )

        if _subsystem(session, "net_power"):
            preset = _CONFIDENCE_PRESETS.get(confidence, _CONFIDENCE_PRESETS["Nominal"])
            ui.number(
                "Minimum net electric power (MW)",
                value=_num_knob(session, "P_net_min_MW", preset["P_net_min_MW"]),
                step=10.0,
                on_change=lambda e: session.knobs.__setitem__("P_net_min_MW", e.value),
            )

        ui.number(
            "Neutron shield thickness (m)",
            value=finite_ui_number(inp.get("t_shield_m", 0.8), unset=0.8),
            min=0.0, step=0.01,
            on_change=lambda e: inp.__setitem__("t_shield_m", e.value),
        )

    if embedded:
        _body()
    else:
        with ui.expansion(title, icon=icon).classes("w-full"):
            ui.label(help_text).classes("text-caption q-mb-sm")
            _body()
