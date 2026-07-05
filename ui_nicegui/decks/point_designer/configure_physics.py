"""Model options, profiles, power & composition — Point Designer Configure."""

from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.pd_panel_labels import CONFIGURE_SECTIONS
from ui_nicegui.lib.ui_safe_numbers import finite_ui_number
from ui_nicegui.session import DesignSession

_CONFINEMENT_LABELS = {
    "IPB98y2": "IPB98(y,2) (H98 basis)",
    "ITER89P": "ITER89-P (L-mode)",
    "KG": "Kaye–Goldston (L-mode)",
    "NEOALC": "Neo-Alcator (ohmic/L)",
    "MIRNOV": "Mirnov (ohmic)",
    "SHIMOMURA": "Shimomura (L-mode)",
}
_CONFINEMENT_REVERSE = {v: k for k, v in _CONFINEMENT_LABELS.items()}

_PROFILE_FAMILIES = [
    "CORE_FLAT",
    "CORE_PEAKED",
    "PEDESTAL_MODERATE",
    "PEDESTAL_STRONG",
    "HYBRID_CORE_PEAKED_PED",
]


def _knob(session: DesignSession, key: str, default):
    raw = session.knobs.get(key, default)
    return finite_ui_number(raw, unset=finite_ui_number(default, unset=0.0))


def _inp(session: DesignSession, key: str, default):
    if key not in session.inputs:
        session.inputs[key] = default
    return session.inputs[key]


def _num_inp(session: DesignSession, key: str, default) -> float:
    return finite_ui_number(session.inputs.get(key, default), unset=finite_ui_number(default, unset=0.0))


def _overlay(session: DesignSession, key: str, default: bool) -> bool:
    return bool(session.overlay.setdefault(key, default))


def _set_overlay(session: DesignSession, key: str, value: bool) -> None:
    session.overlay[key] = bool(value)


def render_model_options(session: DesignSession, *, embedded: bool = False) -> None:
    """Confinement scaling, transport/profile authorities (v371/v396/v397/v372/v358/v349)."""
    inp = session.inputs
    title, icon, help_text = CONFIGURE_SECTIONS["model_options"]

    def _body() -> None:
        scaling = str(inp.get("confinement_scaling", "IPB98y2"))
        label = _CONFINEMENT_LABELS.get(scaling, _CONFINEMENT_LABELS["IPB98y2"])
        ui.select(
            list(_CONFINEMENT_REVERSE.keys()),
            label="H-factor reference scaling",
            value=label,
            on_change=lambda e: inp.__setitem__(
                "confinement_scaling", _CONFINEMENT_REVERSE.get(str(e.value), "IPB98y2")
            ),
        ).classes("w-full")

        # transport contracts
        with ui.expansion("Transport feasibility contracts", icon="route").classes("w-full"):
            en = _overlay(session, "include_transport_contracts_v371", False)
            ui.checkbox(
                "Enable transport contract diagnostics",
                value=en,
                on_change=lambda e: _set_overlay(session, "include_transport_contracts_v371", e.value),
            )
            with ui.grid(columns=2).classes("w-full gap-2"):
                ui.number(
                    "H_required max (optimistic)",
                    value=float(_knob(session, "H_required_max_optimistic", 2.0)),
                    min=0.5, max=5.0, step=0.05,
                    on_change=lambda e: session.knobs.__setitem__("H_required_max_optimistic", e.value),
                )
                ui.number(
                    "H_required max (robust)",
                    value=float(_knob(session, "H_required_max_robust", 1.5)),
                    min=0.5, max=5.0, step=0.05,
                    on_change=lambda e: session.knobs.__setitem__("H_required_max_robust", e.value),
                )

        # transport envelope
        with ui.expansion("Multi-scaling confinement envelope", icon="stacked_line_chart").classes("w-full"):
            en396 = _overlay(session, "include_transport_envelope_v396", True)
            ui.checkbox(
                "Enable transport envelope diagnostics",
                value=en396,
                on_change=lambda e: _set_overlay(session, "include_transport_envelope_v396", e.value),
            )
            ui.number(
                "Max transport spread ratio",
                value=float(_knob(session, "transport_spread_max_v396", 4.0)),
                min=1.0, max=20.0, step=0.1,
                on_change=lambda e: session.knobs.__setitem__("transport_spread_max_v396", e.value),
            )
            user_scaling = bool(_inp(session, "include_tauE_user_scaling_v396", False))
            ui.checkbox(
                "Include user τE scaling vector",
                value=user_scaling,
                on_change=lambda e: inp.__setitem__("include_tauE_user_scaling_v396", bool(e.value)),
            )

        # profile proxy
        with ui.expansion("Kinetic profile peaking proxy", icon="show_chart").classes("w-full"):
            en397 = _overlay(session, "include_profile_proxy_v397", False)
            ui.checkbox(
                "Enable profile proxy authority",
                value=en397,
                on_change=lambda e: _set_overlay(session, "include_profile_proxy_v397", e.value),
            )
            with ui.grid(columns=3).classes("w-full gap-2"):
                for key, label, default in (
                    ("profile_alpha_n_v397", "n profile α", 1.0),
                    ("profile_beta_n_v397", "n profile β", 1.0),
                    ("profile_alpha_T_v397", "T profile α", 1.5),
                    ("profile_beta_T_v397", "T profile β", 1.0),
                    ("profile_alpha_j_v397", "j profile α", 1.5),
                    ("profile_beta_j_v397", "j profile β", 1.0),
                ):
                    ui.number(
                        label,
                        value=float(_knob(session, key, default)),
                        min=0.5, max=8.0, step=0.1,
                        on_change=lambda e, k=key: session.knobs.__setitem__(k, e.value),
                    )
            ui.slider(
                min=0.0, max=1.0, step=0.05,
                value=float(_knob(session, "profile_shear_shape_v397", 0.5)),
                on_change=lambda e: session.knobs.__setitem__("profile_shear_shape_v397", e.value),
            ).props('label color="primary"').classes("w-full")
            ui.label("Shear-shape knob").classes("text-caption")

        # neutronics–materials coupling
        with ui.expansion("Neutronics–materials coupling", icon="science").classes("w-full"):
            en372 = _overlay(session, "include_neutronics_materials_coupling_v372", False)
            ui.checkbox(
                "Enable neutronics–materials coupling",
                value=en372,
                on_change=lambda e: _set_overlay(session, "include_neutronics_materials_coupling_v372", e.value),
            )
            with ui.grid(columns=2).classes("w-full gap-2"):
                ui.select(
                    ["RAFM", "W", "SiC", "ODS"],
                    label="Material class",
                    value=str(_inp(session, "nm_material_class_v372", "RAFM")),
                    on_change=lambda e: inp.__setitem__("nm_material_class_v372", e.value),
                )
                ui.select(
                    ["soft", "nominal", "hard"],
                    label="Spectrum class",
                    value=str(_inp(session, "nm_spectrum_class_v372", "nominal")),
                    on_change=lambda e: inp.__setitem__("nm_spectrum_class_v372", e.value),
                )

        ui.select(
            ["none", "parabolic", "pedestal"],
            label="Analytic profiles (½-D scaffold)",
            value=str(_inp(session, "profile_model", "none")),
            on_change=lambda e: inp.__setitem__("profile_model", e.value),
        ).classes("w-full")

        with ui.grid(columns=2).classes("w-full gap-2"):
            ui.number(
                "nₑ peaking (alpha)",
                value=float(_inp(session, "profile_peaking_ne", 1.0)),
                min=0.0, step=0.1,
                on_change=lambda e: inp.__setitem__("profile_peaking_ne", e.value),
            )
            ui.number(
                "T peaking (alpha)",
                value=float(_inp(session, "profile_peaking_T", 1.5)),
                min=0.0, step=0.1,
                on_change=lambda e: inp.__setitem__("profile_peaking_T", e.value),
            )

        ui.checkbox(
            "Enable 1.5D profile authority diagnostics",
            value=bool(_inp(session, "profile_mode", False)),
            on_change=lambda e: inp.__setitem__("profile_mode", bool(e.value)),
        )

        # profile family
        with ui.expansion("Profile family library", icon="category").classes("w-full"):
            en358 = _overlay(session, "include_profile_family_v358", False)
            ui.checkbox(
                "Enable profile family transport proxy",
                value=en358,
                on_change=lambda e: _set_overlay(session, "include_profile_family_v358", e.value),
            )
            pf = str(_inp(session, "profile_family_v358", "CORE_FLAT")).upper().replace(" ", "_")
            ui.select(
                _PROFILE_FAMILIES,
                label="Profile family",
                value=pf if pf in _PROFILE_FAMILIES else "CORE_FLAT",
                on_change=lambda e: inp.__setitem__("profile_family_v358", e.value),
            ).classes("w-full")
            for key, label, lo, hi, default in (
                ("profile_family_pedestal_frac", "Pedestal fraction", 0.0, 0.4, 0.0),
                ("profile_family_peaking_p", "Pressure peaking", 0.7, 2.0, 1.0),
                ("profile_family_peaking_j", "Current peaking", 0.7, 2.0, 1.0),
                ("profile_family_confinement_mult", "Confinement multiplier", 0.5, 1.8, 1.0),
            ):
                ui.slider(
                    min=lo, max=hi, step=0.01,
                    value=float(_knob(session, key, default)),
                    on_change=lambda e, k=key: session.knobs.__setitem__(k, e.value),
                ).props('label color="primary"').classes("w-full")
                ui.label(label).classes("text-caption")

        with ui.grid(columns=3).classes("w-full gap-2"):
            ui.number(
                "Core T exponent α_T",
                value=float(_inp(session, "profile_alpha_T", 1.5)),
                min=0.0, step=0.1,
                on_change=lambda e: inp.__setitem__("profile_alpha_T", e.value),
            )
            ui.number(
                "Core n exponent α_n",
                value=float(_inp(session, "profile_alpha_n", 1.0)),
                min=0.0, step=0.1,
                on_change=lambda e: inp.__setitem__("profile_alpha_n", e.value),
            )
            ui.slider(
                min=0.0, max=1.0, step=0.05,
                value=float(_inp(session, "profile_shear_shape", 0.5)),
                on_change=lambda e: inp.__setitem__("profile_shear_shape", e.value),
            ).props('label color="primary"')
            ui.label("Shear shape (0..1)").classes("text-caption")

        ui.select(
            ["proxy", "improved"],
            label="Bootstrap proxy model",
            value=str(_inp(session, "bootstrap_model", "proxy")),
            on_change=lambda e: inp.__setitem__("bootstrap_model", e.value),
        ).classes("w-full")

        en349 = _overlay(session, "include_bootstrap_pressure_selfconsistency", False)
        ui.checkbox(
            "Bootstrap–pressure self-consistency",
            value=en349,
            on_change=lambda e: _set_overlay(session, "include_bootstrap_pressure_selfconsistency", e.value),
        )
        if en349:
            ui.number(
                "Max |Δf_bs|",
                value=float(_knob(session, "f_bootstrap_consistency_abs_max", 0.08)),
                min=0.0, max=0.5, step=0.01,
                on_change=lambda e: session.knobs.__setitem__("f_bootstrap_consistency_abs_max", e.value),
            )

    if embedded:
        _body()
    else:
        with ui.expansion(title, icon=icon).classes("w-full"):
            ui.label(help_text).classes("text-caption q-mb-sm")
            _body()


def render_power_composition(session: DesignSession, *, embedded: bool = False) -> None:
    """Radiation, exhaust (v320/v348), alpha, H-mode, NI screens."""
    inp = session.inputs
    title, icon, help_text = CONFIGURE_SECTIONS["power_composition"]

    def _body() -> None:
        with ui.expansion("Physics include/exclude", icon="toggle_on").classes("w-full"):
            for key, label, default in (
                ("include_radiation", "Core radiation & impurities", False),
                ("include_alpha_loss", "Alpha-particle loss fraction", True),
                ("include_hmode_physics", "H-mode access threshold (P_LH)", True),
            ):
                session.overlay.setdefault(key, default)
                ui.checkbox(
                    label,
                    value=bool(session.overlay.get(key, default)),
                    on_change=lambda e, k=key: session.overlay.__setitem__(k, bool(e.value)),
                )
            ui.checkbox(
                "Include SOL width (λq) proxy",
                value=bool(_inp(session, "use_lambda_q", True)),
                on_change=lambda e: inp.__setitem__("use_lambda_q", bool(e.value)),
            )

        if bool(session.overlay.get("include_radiation", False)):
            with ui.grid(columns=2).classes("w-full gap-2"):
                ui.number(
                    "Zeff",
                    value=float(inp.get("zeff", 1.5)),
                    min=1.0, step=0.1,
                    on_change=lambda e: inp.__setitem__("zeff", e.value),
                )
                ui.number(
                    "Fuel dilution",
                    value=float(inp.get("dilution_fuel", 0.85)),
                    min=0.0, max=1.0, step=0.01,
                    on_change=lambda e: inp.__setitem__("dilution_fuel", e.value),
                )
                ui.number(
                    "Core radiation fraction f_rad,core",
                    value=float(_inp(session, "f_rad_core", 0.20)),
                    min=0.0, max=0.95, step=0.01,
                    on_change=lambda e: inp.__setitem__("f_rad_core", e.value),
                )
            ui.select(
                ["fractional", "impurity_mix"],
                label="Radiation model",
                value=str(_inp(session, "radiation_model", "fractional")),
                on_change=lambda e: inp.__setitem__("radiation_model", e.value),
            ).classes("w-full")
            ui.select(
                ["proxy_v1", "radas_openadas_v1"],
                label="Lz(Te) database",
                value=str(_inp(session, "radiation_db", "proxy_v1")),
                on_change=lambda e: inp.__setitem__("radiation_db", e.value),
            ).classes("w-full")
            ui.select(
                ["C", "N", "Ne", "Ar", "W"],
                label="Impurity species",
                value=str(_inp(session, "impurity_species", "C")),
                on_change=lambda e: inp.__setitem__("impurity_species", e.value),
            ).classes("w-full")
            session.overlay.setdefault("include_synchrotron", True)
            ui.checkbox(
                "Include synchrotron radiation",
                value=bool(session.overlay.get("include_synchrotron", True)),
                on_change=lambda e: session.overlay.__setitem__("include_synchrotron", bool(e.value)),
            )

            with ui.expansion("Impurity radiation & detachment", icon="opacity").classes("w-full"):
                with ui.grid(columns=2).classes("w-full gap-2"):
                    ui.select(
                        ["C", "N", "Ne", "Ar", "W"],
                        label="Contract species",
                        value=str(_inp(session, "impurity_contract_species", "Ne")),
                        on_change=lambda e: inp.__setitem__("impurity_contract_species", e.value),
                    )
                    ui.number(
                        "Contract seeding f_z",
                        value=float(_inp(session, "impurity_contract_f_z", 3e-4)),
                        min=0.0, max=0.01, step=1e-5,
                        on_change=lambda e: inp.__setitem__("impurity_contract_f_z", e.value),
                    )
                for key, label in (
                    ("impurity_partition_core", "Partition: core"),
                    ("impurity_partition_edge", "Partition: edge"),
                    ("impurity_partition_sol", "Partition: SOL"),
                    ("impurity_partition_div", "Partition: divertor"),
                ):
                    ui.slider(
                        min=0.0, max=1.0, step=0.01,
                        value=float(_inp(session, key, 0.25)),
                        on_change=lambda e, k=key: inp.__setitem__(k, e.value),
                    ).props('label color="primary"').classes("w-full")
                    ui.label(label).classes("text-caption")
                ui.checkbox(
                    "Enable q_div target inversion",
                    value=bool(_inp(session, "include_sol_radiation_control", False)),
                    on_change=lambda e: inp.__setitem__("include_sol_radiation_control", bool(e.value)),
                )
                ui.number(
                    "q_div target (MW/m²)",
                    value=float(_knob(session, "q_div_target_MW_m2", 10.0)),
                    min=0.1, step=0.5,
                    on_change=lambda e: session.knobs.__setitem__("q_div_target_MW_m2", e.value),
                )

            with ui.expansion("Edge–core coupled exhaust", icon="sync_alt").classes("w-full"):
                ui.checkbox(
                    "Enable edge–core coupled exhaust",
                    value=bool(_inp(session, "include_edge_core_coupled_exhaust", False)),
                    on_change=lambda e: inp.__setitem__("include_edge_core_coupled_exhaust", bool(e.value)),
                )
                ui.slider(
                    min=0.0, max=1.0, step=0.05,
                    value=float(_inp(session, "edge_core_coupling_chi_core", 0.25)),
                    on_change=lambda e: inp.__setitem__("edge_core_coupling_chi_core", e.value),
                ).props('label color="primary"').classes("w-full")
                ui.label("Coupling coefficient χ_core").classes("text-caption")

        if bool(session.overlay.get("include_alpha_loss", True)):
            ui.number(
                "Alpha heating loss fraction",
                value=float(_inp(session, "alpha_loss_frac", 0.05)),
                min=0.0, max=1.0, step=0.01,
                on_change=lambda e: inp.__setitem__("alpha_loss_frac", e.value),
            )

        with ui.expansion("Power-channel bookkeeping", icon="bolt").classes("w-full"):
            ui.slider(
                min=0.0, max=1.0, step=0.01,
                value=float(_inp(session, "f_alpha_to_ion", 0.85)),
                on_change=lambda e: inp.__setitem__("f_alpha_to_ion", e.value),
            ).props('label color="primary"').classes("w-full")
            ui.label("Alpha deposition to ions f_α→i").classes("text-caption")
            ui.slider(
                min=0.0, max=1.0, step=0.01,
                value=float(_inp(session, "f_aux_to_ion", 0.50)),
                on_change=lambda e: inp.__setitem__("f_aux_to_ion", e.value),
            ).props('label color="primary"').classes("w-full")
            ui.label("Aux deposition to ions f_aux→i").classes("text-caption")

        with ui.expansion("Non-inductive & risk screens", icon="electric_bolt").classes("w-full"):
            ui.checkbox(
                "Enable current-drive closure (proxy)",
                value=bool(_inp(session, "cd_enable", False)),
                on_change=lambda e: inp.__setitem__("cd_enable", bool(e.value)),
            )
            ui.select(
                ["NBI", "EC", "LH"],
                label="CD method",
                value=str(_inp(session, "cd_method", "NBI")),
                on_change=lambda e: inp.__setitem__("cd_method", e.value),
            ).classes("w-full")
            ui.number(
                "Min non-inductive fraction f_NI,min",
                value=finite_ui_number(_knob(session, "f_NI_min", float("nan"))),
                min=0.0, max=1.0, step=0.05,
                on_change=lambda e: session.knobs.__setitem__("f_NI_min", e.value),
            )
            ui.number(
                "Max disruption risk proxy",
                value=finite_ui_number(_knob(session, "disruption_risk_max", float("nan"))),
                min=0.0, step=0.1,
                on_change=lambda e: session.knobs.__setitem__("disruption_risk_max", e.value),
            )

    if embedded:
        _body()
    else:
        with ui.expansion(title, icon=icon).classes("w-full"):
            ui.label(help_text).classes("text-caption q-mb-sm")
            _body()
