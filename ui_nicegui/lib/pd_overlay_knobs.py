"""Conditional numeric sub-knobs for Point Designer authority overlays."""

from __future__ import annotations

from typing import List, Tuple

from nicegui import ui

from ui_nicegui.lib.pd_panel_labels import overlay_numeric_title
from ui_nicegui.lib.ui_safe_numbers import finite_ui_number
from ui_nicegui.session import DesignSession

# (overlay_flag, [(knobs_key, label, default, min, max, step), ...])
OVERLAY_NUMERIC_PANELS: List[Tuple[str, List[Tuple[str, str, float, float, float, float]]]] = [
    (
        "include_transport_contracts_v371",
        [
            ("H_required_max_optimistic", "H_required max (optimistic)", 1.25, 0.5, 3.0, 0.05),
            ("H_required_max_robust", "H_required max (robust)", 1.15, 0.5, 3.0, 0.05),
        ],
    ),
    (
        "include_transport_envelope_v396",
        [
            ("transport_spread_max_v396", "Transport spread max", 0.35, 0.0, 2.0, 0.01),
            ("tauE_user_C_v396", "τE scaling coefficient C", 1.0, 0.01, 10.0, 0.01),
            ("tauE_user_exp_Ip_v396", "τE exponent Ip", -0.93, -3.0, 1.0, 0.01),
            ("tauE_user_exp_Bt_v396", "τE exponent Bt", 0.15, -1.0, 1.0, 0.01),
            ("tauE_user_exp_ne_v396", "τE exponent ne", -0.41, -2.0, 1.0, 0.01),
            ("tauE_user_exp_Ploss_v396", "τE exponent Ploss", -0.69, -2.0, 1.0, 0.01),
            ("tauE_user_exp_R_v396", "τE exponent R", 0.0, -2.0, 2.0, 0.01),
            ("tauE_user_exp_eps_v396", "τE exponent eps", 0.0, -2.0, 2.0, 0.01),
            ("tauE_user_exp_kappa_v396", "τE exponent kappa", 0.0, -2.0, 2.0, 0.01),
            ("tauE_user_exp_M_v396", "τE exponent M", 0.0, -2.0, 2.0, 0.01),
        ],
    ),
    (
        "include_profile_proxy_v397",
        [
            ("profile_alpha_T_v397", "Temperature profile α_T", 2.0, 0.0, 10.0, 0.1),
            ("profile_beta_T_v397", "Temperature profile β_T", 1.5, 0.0, 10.0, 0.1),
            ("profile_alpha_n_v397", "Density profile α_n", 1.0, 0.0, 10.0, 0.1),
            ("profile_beta_n_v397", "Density profile β_n", 1.0, 0.0, 10.0, 0.1),
            ("profile_alpha_j_v397", "Current profile α_j", 1.5, 0.0, 10.0, 0.1),
            ("profile_beta_j_v397", "Current profile β_j", 1.0, 0.0, 10.0, 0.1),
            ("profile_shear_shape_v397", "Shear-shape knob", 0.5, 0.0, 1.0, 0.05),
            ("profile_peaking_p_max_v397", "Pressure peaking p_max", 3.0, 1.0, 10.0, 0.1),
            ("q95_proxy_min_v397", "q95 proxy minimum", 2.5, 1.0, 10.0, 0.1),
            ("q0_proxy_min_v397", "q0 proxy minimum", 1.0, 0.5, 5.0, 0.1),
            ("bootstrap_localization_max_v397", "Bootstrap localization max", 0.6, 0.0, 1.0, 0.05),
        ],
    ),
    (
        "include_profile_family_v358",
        [
            ("profile_family_pedestal_frac", "Pedestal fraction", 0.0, 0.0, 0.4, 0.01),
            ("profile_family_peaking_p", "Pressure peaking", 1.0, 0.7, 2.0, 0.01),
            ("profile_family_peaking_j", "Current peaking", 1.0, 0.7, 2.0, 0.01),
            ("profile_family_shear_shape", "Shear shape", 0.5, 0.0, 1.0, 0.01),
            ("profile_family_confinement_mult", "Confinement multiplier", 1.0, 0.5, 1.8, 0.01),
            ("profile_family_bootstrap_mult", "Bootstrap multiplier", 1.0, 0.5, 1.8, 0.01),
        ],
    ),
    (
        "include_bootstrap_pressure_selfconsistency",
        [
            ("f_bootstrap_consistency_abs_max", "Max |Δf_bs|", 0.08, 0.0, 0.5, 0.01),
        ],
    ),
    (
        "include_neutronics_materials_coupling_v372",
        [
            ("nm_T_oper_C_v372", "Operating temperature (°C)", 500.0, 0.0, 2000.0, 10.0),
            ("dpa_rate_eff_max_v372", "DPA-rate cap (DPA/FPY)", 20.0, 0.0, 100.0, 1.0),
            ("damage_margin_min_v372", "Min damage margin", 0.0, 0.0, 2.0, 0.05),
        ],
    ),
    (
        "include_magnet_technology_authority_v400",
        [
            ("magnet_margin_min_v400", "Magnet margin min", float("nan"), 0.0, 2.0, 0.05),
            ("b_margin_min_v400", "Field margin min", float("nan"), 0.0, 2.0, 0.05),
            ("j_margin_min_v400", "Current density margin min", float("nan"), 0.0, 2.0, 0.05),
            ("stress_margin_min_v400", "Stress margin min", float("nan"), 0.0, 2.0, 0.05),
        ],
    ),
    (
        "include_control_stability_authority_v398",
        [
            ("vs_budget_margin_min_v398", "VS budget margin min", float("nan"), 0.0, 2.0, 0.05),
            ("vde_headroom_min_v398", "VDE headroom min", float("nan"), 0.0, 2.0, 0.05),
            ("rwm_proximity_index_max_v398", "RWM proximity index max", float("nan"), 0.0, 5.0, 0.05),
        ],
    ),
    (
        "include_impurity_v399",
        [
            ("zeff_max_v399", "Zeff max", 2.5, 1.0, 5.0, 0.05),
            ("prad_core_frac_max_v399", "Core radiation fraction max", 0.5, 0.0, 1.0, 0.01),
            ("prad_total_frac_max_v399", "Total radiation fraction max", 0.8, 0.0, 1.0, 0.01),
            ("detachment_margin_min_v399", "Detachment margin min", float("nan"), 0.0, 2.0, 0.05),
        ],
    ),
    (
        "include_damage_strength_coupling_v393",
        [
            ("design_life_fpy_v393", "Design life (FPY)", 10.0, 0.0, 50.0, 1.0),
            ("k_allow_deg_per_dpa_v393", "Degradation slope k (1/DPA)", 0.003, 0.0, 0.1, 0.001),
            ("min_allow_frac_v393", "Min allowable fraction floor", 0.5, 0.0, 1.0, 0.05),
            ("dpa_factor_tf_v393", "DPA shielding factor TF", 0.05, 0.0, 1.0, 0.01),
            ("dpa_factor_cs_v393", "DPA shielding factor CS/PF", 0.05, 0.0, 1.0, 0.01),
            ("dpa_factor_vv_v393", "DPA shielding factor VV", 0.20, 0.0, 1.0, 0.01),
        ],
    ),
    (
        "cd_mix_enable",
        [
            ("cd_mix_frac_eccd", "Mix fraction: ECCD", 1.0, 0.0, 1.0, 0.05),
            ("cd_mix_frac_lhcd", "Mix fraction: LHCD", 0.0, 0.0, 1.0, 0.05),
            ("cd_mix_frac_nbi", "Mix fraction: NBI", 0.0, 0.0, 1.0, 0.05),
            ("cd_mix_frac_icrf", "Mix fraction: ICRF", 0.0, 0.0, 1.0, 0.05),
        ],
    ),
    (
        "include_availability_replacement_v359",
        [
            ("planned_outage_base", "Planned outage base", 0.05, 0.0, 0.5, 0.01),
            ("availability_v359_min", "Min availability", float("nan"), 0.0, 1.0, 0.01),
            ("LCOE_max_USD_per_MWh", "Max LCOE (USD/MWh)", float("nan"), 0.0, 500.0, 1.0),
        ],
    ),
    (
        "include_maintenance_scheduling_v368",
        [
            ("maintenance_planning_horizon_yr", "Planning horizon (yr)", float("nan"), 1.0, 50.0, 1.0),
            ("outage_fraction_v368_max", "Max outage fraction", float("nan"), 0.0, 1.0, 0.01),
            ("availability_v368_min", "Min availability", float("nan"), 0.0, 1.0, 0.01),
        ],
    ),
    (
        "include_economics_v360",
        [
            ("opex_fixed_MUSD_per_y", "Fixed OPEX (MUSD/y)", 0.0, 0.0, 500.0, 1.0),
            ("OPEX_max_MUSD_per_y", "Max OPEX (MUSD/y)", float("nan"), 0.0, 500.0, 1.0),
        ],
    ),
    (
        "include_economics_v383",
        [
            ("CAPEX_structured_max_MUSD", "Max structured CAPEX (MUSD)", float("nan"), 0.0, 50000.0, 10.0),
            ("LCOE_lite_max_USD_per_MWh", "Max LCOE lite (USD/MWh)", float("nan"), 0.0, 500.0, 1.0),
        ],
    ),
    (
        "include_cost_authority_v388",
        [
            ("CAPEX_industrial_max_MUSD", "Max industrial CAPEX (MUSD)", float("nan"), 0.0, 50000.0, 10.0),
            ("LCOE_lite_v388_max_USD_per_MWh", "Max LCOE v388 (USD/MWh)", float("nan"), 0.0, 500.0, 1.0),
        ],
    ),
    (
        "include_structural_stress_v389",
        [
            ("tf_struct_margin_min_v389", "TF structural margin min", 1.0, 0.0, 5.0, 0.05),
            ("vv_struct_margin_min_v389", "VV structural margin min", 1.0, 0.0, 5.0, 0.05),
        ],
    ),
    (
        "include_neutronics_activation_v390",
        [
            ("fw_dpa_limit_v390", "FW DPA limit", 20.0, 0.0, 200.0, 1.0),
            ("shield_margin_min_cm_v390", "Shield margin min (cm)", float("nan"), 0.0, 100.0, 1.0),
        ],
    ),
    (
        "include_neutronics_shield_attenuation_v392",
        [
            ("atten_len_bioshield_m_v392", "Bioshield attenuation length (m)", 0.35, 0.01, 5.0, 0.01),
            ("bioshield_dose_rate_max_uSv_h_v392", "Max bioshield dose (µSv/h)", float("nan"), 0.0, 1000.0, 1.0),
        ],
    ),
    (
        "include_neutronics_materials_authority_v401",
        [
            ("nm_fragile_margin_frac_v401", "Fragile margin fraction", 0.10, 0.0, 0.5, 0.01),
        ],
    ),
    (
        "include_structural_life_v404",
        [
            ("struct_global_min_margin_v404", "Global min margin", float("nan"), 0.0, 2.0, 0.05),
        ],
    ),
    (
        "include_materials_lifetime_v384",
        [
            ("capacity_factor_min_v384", "Min capacity factor", float("nan"), 0.0, 1.0, 0.01),
            ("fw_lifetime_min_yr_v384", "Min FW lifetime (yr)", float("nan"), 0.0, 50.0, 0.5),
        ],
    ),
    (
        "include_availability_reliability_v391",
        [
            ("planned_outage_days_per_y_v391", "Planned outage days/y", 30.0, 0.0, 365.0, 1.0),
            ("availability_min_v391", "Min availability", float("nan"), 0.0, 1.0, 0.01),
        ],
    ),
    (
        "include_nuclear_data_authority_v407",
        [
            ("fast_attenuation_min_v403", "Fast attenuation min (proxy)", float("nan"), 0.0, 1.0, 0.01),
        ],
    ),
]


def _knob(session: DesignSession, key: str, default: float) -> float:
    v = session.knobs.get(key, default)
    return finite_ui_number(v, unset=finite_ui_number(default, unset=0.0))


def _overlay_enabled(session: DesignSession, flag: str) -> bool:
    return bool(session.overlay.get(flag, False))


def render_overlay_numeric_panels(session: DesignSession) -> None:
    """Show numeric sub-knobs when parent overlay toggles are enabled."""
    any_visible = False
    for flag, fields in OVERLAY_NUMERIC_PANELS:
        if not _overlay_enabled(session, flag):
            continue
        any_visible = True
        title = overlay_numeric_title(flag)
        with ui.expansion(title, icon="tune").classes("w-full"):
            with ui.grid(columns=2).classes("w-full gap-2"):
                for key, label, default, lo, hi, step in fields:
                    val = _knob(session, key, default)

                    def _set(e, k=key) -> None:
                        session.knobs[k] = e.value

                    ui.number(
                        label,
                        value=val,
                        min=lo,
                        max=hi,
                        step=step,
                        on_change=_set,
                    )
    if not any_visible:
        ui.label("Enable physics or authority overlays above to expose numeric sub-knobs.").classes(
            "text-caption text-grey"
        )
