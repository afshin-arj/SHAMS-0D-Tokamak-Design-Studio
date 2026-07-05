"""Build PointInputs from NiceGUI session (no Streamlit imports)."""
from __future__ import annotations

from dataclasses import asdict, fields
from typing import Any

from ui.point_inputs_factory import make_point_inputs_from, strip_point_input_knob_dupes

from ui_nicegui.session import DesignSession

try:
    from schema.inputs import PointInputs
except ImportError:
    from src.schema.inputs import PointInputs

# Explicit overlay / authority keys merged after base construction (priority: overlay > inputs > knobs).
_PRIORITY_OVERLAY_KEYS = frozenset({
    "include_transport_contracts_v371",
    "include_transport_envelope_v396",
    "include_tauE_user_scaling_v396",
    "include_profile_proxy_v397",
    "include_profile_family_v358",
    "include_profile_contracts_v397",
    "include_control_stability_authority_v398",
    "include_impurity_v399",
    "include_magnet_technology_authority_v400",
    "include_neutronics_materials_coupling_v372",
    "include_neutronics_materials_library_v403",
    "include_neutronics_materials_authority_v401",
    "include_neutronics_activation_v390",
    "include_neutronics_shield_attenuation_v392",
    "include_structural_life_authority_v404",
    "include_structural_life_v404",
    "include_nuclear_data_authority_v407",
    "include_authority_dominance_v402",
    "include_elm_transient_heat_v409",
    "include_tritium_tight_closure",
    "include_radiation",
    "include_alpha_loss",
    "include_hmode_physics",
    "include_synchrotron",
    "include_bootstrap_pressure_selfconsistency",
    "include_control_contracts",
    "include_current_drive",
    "include_economics_v360",
    "include_economics_v383",
    "include_cost_authority_v388",
    "include_structural_stress_v389",
    "include_availability_replacement_v359",
    "include_availability_reliability_v391",
    "include_materials_lifetime_v384",
    "include_maintenance_scheduling_v368",
    "cd_mix_enable",
})


def _point_input_field_names() -> set[str]:
    return {f.name for f in fields(PointInputs)}


def _collect_session_overrides(session: DesignSession) -> dict[str, Any]:
    """Merge all session dicts into PointInputs-compatible overrides."""
    names = _point_input_field_names()
    merged: dict[str, Any] = {}
    for src in (session.knobs, session.inputs, session.overlay):
        for key, value in (src or {}).items():
            if key in names:
                merged[key] = value
    return merged


def _merge_overlay(session: DesignSession, inp: Any) -> Any:
    """Apply session fields onto PointInputs (overlay > inputs > knobs precedence for toggles)."""
    names = _point_input_field_names()
    overrides = _collect_session_overrides(session)
    if not overrides:
        return inp
    data = asdict(inp) if hasattr(inp, "__dataclass_fields__") else dict(inp)
    data.update(overrides)
    # Overlay toggles win for explicit authority keys
    for key in _PRIORITY_OVERLAY_KEYS:
        if key in names and key in session.overlay:
            data[key] = session.overlay[key]
    return PointInputs(**{k: v for k, v in data.items() if k in names})


def build_point_inputs(session: DesignSession):
    """Assemble PointInputs from session fields (Truth Console core path)."""
    inp = session.inputs
    names = _point_input_field_names()
    knobs = strip_point_input_knob_dupes(
        session.knobs,
        "Tcoil_K", "magnet_technology", "Bt_T", "R0_m", "a_m", "kappa", "delta",
        "Ip_MA", "fG", "Paux_MW", "Ti_keV",
    )
    extra_knobs = {k: v for k, v in knobs.items() if k in names}

    fuel = str(inp.get("fuel_mode", "DT"))
    include_secondary = bool(session.pd_include_secondary_dt) if fuel == "DD" else False

    scaling = str(inp.get("confinement_scaling", "IPB98y2"))
    base = make_point_inputs_from(
        knobs,
        R0_m=float(inp.get("R0_m", 1.81)),
        a_m=float(inp.get("a_m", 0.62)),
        kappa=float(inp.get("kappa", 1.8)),
        delta=float(inp.get("delta", 0.0)),
        Bt_T=float(inp.get("Bt_T", 10.0)),
        magnet_technology=str(inp.get("magnet_technology", "HTS_REBCO")),
        Tcoil_K=float(inp.get("Tcoil_K", 20.0)),
        Ip_MA=float(inp.get("Ip_MA", 8.0)),
        Ti_keV=float(inp.get("Ti_keV", 10.0)),
        fG=float(inp.get("fG", 0.8)),
        t_shield_m=float(inp.get("t_shield_m", 0.8)),
        Paux_MW=float(inp.get("Paux_MW", 50.0)),
        Ti_over_Te=float(inp.get("Ti_over_Te", 1.0)),
        confinement_scaling=scaling,
        confinement_model=scaling.lower(),
        zeff=float(inp.get("zeff", 1.8)),
        dilution_fuel=float(inp.get("dilution_fuel", 0.85)),
        fuel_mode=fuel,
        include_secondary_DT=include_secondary,
        tritium_retention=float(session.pd_tritium_retention) if include_secondary else 0.0,
        tau_T_loss_s=float(session.pd_tau_t_loss_s) if include_secondary else 1.0,
        use_lambda_q=bool(inp.get("use_lambda_q", True)),
        profile_model=str(inp.get("profile_model", "none")),
        profile_mode=bool(inp.get("profile_mode", False)),
        include_radiation=bool(session.overlay.get("include_radiation", False)),
        include_alpha_loss=bool(session.overlay.get("include_alpha_loss", True)),
        include_hmode_physics=bool(session.overlay.get("include_hmode_physics", True)),
        include_synchrotron=bool(session.overlay.get("include_synchrotron", True)),
        include_magnet_technology_authority_v400=bool(session.overlay.get(
            "include_magnet_technology_authority_v400", True
        )),
        include_transport_envelope_v396=bool(session.overlay.get(
            "include_transport_envelope_v396", True
        )),
        include_profile_proxy_v397=bool(session.overlay.get("include_profile_proxy_v397", False)),
        include_tritium_tight_closure=bool(session.overlay.get("include_tritium_tight_closure", False)),
        include_control_contracts=bool(session.overlay.get("include_control_contracts", False)),
        include_current_drive=bool(session.overlay.get("include_current_drive", False)),
        include_bootstrap_pressure_selfconsistency=bool(session.overlay.get(
            "include_bootstrap_pressure_selfconsistency", False
        )),
        include_authority_dominance_v402=bool(session.overlay.get("include_authority_dominance_v402", True)),
        cd_mix_enable=bool(session.overlay.get("cd_mix_enable", False)),
        **extra_knobs,
    )
    return _merge_overlay(session, base)
