from __future__ import annotations
"""SHAMS hot-ion 0-D plasma model core.

This module computes a single operating point ("zero-D" / volume-averaged) for a tokamak-like device.
Over time SHAMS has grown PROCESS-inspired features while remaining Windows-native and lightweight:

- Optional *analytic profiles* (parabolic / pedestal) used for derived averages and diagnostics
- Radiation model options (fractional vs impurity-driven core radiation)
- Engineering hooks (TF coil peak field / HTS margin / stress)
- Plant power closure and simple neutronics / divertor proxies

Design intent:
- Keep the legacy point model stable and fast for scans.
- When optional submodels are enabled, add outputs/constraints without breaking existing callers.

Key entrypoint: ``hot_ion_point(inputs, Paux_for_Q_MW=None) -> dict``.
"""
import math
import json
from pathlib import Path
from typing import Any, Dict, Optional

try:
    # Preferred when imported as `src.physics.*` (application/runtime)
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    try:
        # Preferred when tests add `<repo>/src` to sys.path (so `models` is top-level)
        from models.inputs import PointInputs  # type: ignore
    except Exception:
        # Back-compat fallback
        from models.inputs import PointInputs  # type: ignore
try:
    # Preferred when imported as `src.physics.*`
    from ..profiles.profiles import ParabolicProfile, PedestalProfile, PlasmaProfiles  # type: ignore
    from ..profiles.profile_bundle import (
        ProfileSpec,
        evaluate_profile_bundle,
        profile_assumption_tag,
    )  # type: ignore
    from ..profiles.family_v358 import compute_profile_family_factors_v358  # type: ignore
except Exception:
    # Back-compat when `<repo>/src` is on sys.path (so `profiles` is top-level)
    from profiles.profiles import ParabolicProfile, PedestalProfile, PlasmaProfiles  # type: ignore
    from profiles.profile_bundle import (
        ProfileSpec,
        evaluate_profile_bundle,
        profile_assumption_tag,
    )  # type: ignore
    from profiles.family_v358 import compute_profile_family_factors_v358  # type: ignore
from .radiation import (
    ImpurityMix,
    bremsstrahlung_W,
    estimate_zeff_from_mix,
    estimate_zeff_from_single_impurity,
    total_core_radiation_W,
)
from .impurities.species_library import ImpurityContract, evaluate_impurity_radiation_partition
from .plant import plant_power_closure, electric_efficiency
from .current_drive import cd_gamma_and_efficiency
try:
    from ..economics.cost import cost_proxies  # type: ignore
    from ..analysis.mhd_risk import compute_mhd_and_vs_risk  # type: ignore
    from ..diagnostics.disruption_risk import evaluate_disruption_risk  # type: ignore
    from ..diagnostics.stability_risk import evaluate_stability_risk  # type: ignore
    from ..analysis.control_contracts import compute_control_contracts  # type: ignore
    from ..contracts.control_stability_authority_contract import load_control_stability_contract, contract_defaults  # type: ignore
    from ..contracts.plasma_regime_authority_contract import load_plasma_regime_contract
    from ..contracts.impurity_radiation_authority_contract import load_impurity_radiation_contract  # type: ignore
    from ..analysis.impurity_radiation import evaluate_impurity_radiation  # type: ignore  # type: ignore
    from ..analysis.plasma_regime import evaluate_plasma_regime  # type: ignore
    from ..analysis.availability import compute_availability  # type: ignore
    from ..availability.ledger_v359 import compute_availability_replacement_v359  # type: ignore
    from ..maintenance.scheduling_v368 import compute_maintenance_schedule_v368  # type: ignore
    # v367.0 module is under repo-root `analysis/` namespace for test/runtime wiring
    from analysis.materials_lifetime_v367 import compute_materials_lifetime_closure_v367  # type: ignore
    from analysis.materials_lifetime_v384 import compute_materials_lifetime_tightening_v384  # type: ignore
    from ..analysis.tritium import compute_tritium_cycle  # type: ignore
    from ..engineering.pf_system import pf_system_proxy  # type: ignore
except Exception:
    from economics.cost import cost_proxies  # type: ignore
    from analysis.mhd_risk import compute_mhd_and_vs_risk  # type: ignore
    from diagnostics.disruption_risk import evaluate_disruption_risk  # type: ignore
    from diagnostics.stability_risk import evaluate_stability_risk  # type: ignore
    from analysis.control_contracts import compute_control_contracts  # type: ignore
    from contracts.control_stability_authority_contract import load_control_stability_contract, contract_defaults  # type: ignore
    from contracts.plasma_regime_authority_contract import load_plasma_regime_contract  # type: ignore
    from analysis.plasma_regime import evaluate_plasma_regime  # type: ignore
    from analysis.availability import compute_availability  # type: ignore
    from availability.ledger_v359 import compute_availability_replacement_v359  # type: ignore
    from maintenance.scheduling_v368 import compute_maintenance_schedule_v368  # type: ignore
    from analysis.materials_lifetime_v367 import compute_materials_lifetime_closure_v367  # type: ignore
    from analysis.materials_lifetime_v384 import compute_materials_lifetime_tightening_v384  # type: ignore
    from analysis.tritium import compute_tritium_cycle  # type: ignore
    from engineering.pf_system import pf_system_proxy  # type: ignore
from .profiles import build_profiles_from_volume_avgs, gradient_proxy_at_pedestal
from .divertor import divertor_two_regime
from .exhaust import evaluate_exhaust_with_known_lambda_q, q_midplane_from_lambda_q
from .control_stability import compute_vertical_stability, compute_pf_envelope
from .mhd_rwm import compute_rwm_screening
from .neutronics import neutronics_proxies

# Governance-only post-processing authorities (must be import-safe).
try:
    from analysis.transport_contracts_v371 import evaluate_transport_contracts_v371  # type: ignore
except Exception:
    evaluate_transport_contracts_v371 = None  # type: ignore

try:
    from analysis.neutronics_materials_coupling_v372 import evaluate_neutronics_materials_coupling_v372  # type: ignore
except Exception:
    evaluate_neutronics_materials_coupling_v372 = None  # type: ignore


try:
    # Preferred when imported as `src.physics.*`
    from ..engineering.thermal_hydraulics import coolant_pumping_power_MW, coolant_dT_K  # type: ignore
    from ..analysis.time_evolution import pulsed_summary  # type: ignore
    from ..engineering.radial_stack import build_default_stack, neutron_attenuation_factor, nuclear_heating_MW  # type: ignore
    from ..engineering.materials_library import get_material, MaterialNeutronProps  # type: ignore
    from ..engineering.neutronics_materials_authority import compute_neutronics_materials_bundle  # type: ignore
    from ..engineering.tf_coil import (
        TFCoilGeom,
        HTSCriticalSurface,
        B_peak_T as B_peak_T_tf,
        engineering_current_density_A_m2,
        hts_margin as hts_margin_cs_func,
        von_mises_stress_MPa,
    )  # type: ignore
    from ..engineering.pf_cs import cs_flux_swing_proxy  # type: ignore
    from ..engineering.coil_thermal import tf_coil_heat_proxy  # type: ignore
    from ..engineering.structural_stress_authority_v389 import compute_structural_stress_bundle_v389  # type: ignore
    from ..engineering.neutronics_activation_authority_v390 import compute_neutronics_activation_bundle_v390  # type: ignore
    from ..phase1_models import (
        tokamak_volume,
        tokamak_surface_area,
        first_wall_area_proxy,
        greenwald_density_20,
        p_LH_martin08,
        tauE_ipb98y2,
        tauE_iter89p,
        tauE_kaye_goldston,
        tauE_neo_alcator,
        tauE_mirnov,
        tauE_shimomura,
        H98_from_tauE,
        bosch_hale_sigmav,
        eich_lambda_q_mm,
        neutron_shield_capture,
        MW_TO_W,
        KEV_TO_J,
        Bpol_outboard_midplane_T,
        betaN_from_beta,
        q95_proxy_cyl,
        bootstrap_fraction_proxy,
        bootstrap_fraction_improved,
        bootstrap_fraction_sauter_proxy,
        lambda_q_eich14_mm,
    )  # type: ignore
    from ..phase1_systems import (
        RadialBuild,
        inboard_build_ok,
        B_peak_T,
        hoop_stress_MPa,
        hts_operating_margin,
        sc_operating_margin,
        tf_sc_flag,
        copper_tf_ohmic_power_MW,
        tf_current_A,
        tf_stored_energy_J,
        dump_voltage_kV,
        connection_length_m,
        divertor_q_MW_m2,
        TBR_proxy,
        HTS_fluence_per_fpy_n_m2,
        cryoplant_electric_MW,
        joint_loss_W,
        current_drive_power_MW,
        net_electric_MW,
    )  # type: ignore
except Exception:
    # Back-compat when `<repo>/src` is on sys.path
    from engineering.thermal_hydraulics import coolant_pumping_power_MW, coolant_dT_K  # type: ignore
    from analysis.time_evolution import pulsed_summary  # type: ignore
    from engineering.radial_stack import build_default_stack, neutron_attenuation_factor, nuclear_heating_MW  # type: ignore
    from engineering.materials_library import get_material, MaterialNeutronProps  # type: ignore
    from engineering.neutronics_materials_authority import compute_neutronics_materials_bundle  # type: ignore
    from engineering.tf_coil import (
        TFCoilGeom,
        HTSCriticalSurface,
        B_peak_T as B_peak_T_tf,
        engineering_current_density_A_m2,
        hts_margin as hts_margin_cs_func,
        von_mises_stress_MPa,
    )  # type: ignore
    from engineering.pf_cs import cs_flux_swing_proxy  # type: ignore
    from engineering.coil_thermal import tf_coil_heat_proxy  # type: ignore
    from engineering.neutronics_activation_authority_v390 import compute_neutronics_activation_bundle_v390  # type: ignore
    from phase1_models import (
        tokamak_volume,
        tokamak_surface_area,
        first_wall_area_proxy,
        greenwald_density_20,
        p_LH_martin08,
        tauE_ipb98y2,
        tauE_iter89p,
        tauE_kaye_goldston,
        tauE_neo_alcator,
        tauE_mirnov,
        tauE_shimomura,
        H98_from_tauE,
        bosch_hale_sigmav,
        eich_lambda_q_mm,
        neutron_shield_capture,
        MW_TO_W,
        KEV_TO_J,
        Bpol_outboard_midplane_T,
        betaN_from_beta,
        q95_proxy_cyl,
        bootstrap_fraction_proxy,
        bootstrap_fraction_improved,
        bootstrap_fraction_sauter_proxy,
        lambda_q_eich14_mm,
    )  # type: ignore
    from phase1_systems import (
        RadialBuild,
        inboard_build_ok,
        B_peak_T,
        hoop_stress_MPa,
        hts_operating_margin,
        sc_operating_margin,
        tf_sc_flag,
        copper_tf_ohmic_power_MW,
        tf_current_A,
        tf_stored_energy_J,
        dump_voltage_kV,
        connection_length_m,
        divertor_q_MW_m2,
        TBR_proxy,
        HTS_fluence_per_fpy_n_m2,
        cryoplant_electric_MW,
        joint_loss_W,
        current_drive_power_MW,
        net_electric_MW,
    )  # type: ignore

    # v371.0: transport contract library (governance only; post-processing)
    from analysis.transport_contracts_v371 import evaluate_transport_contracts_v371  # type: ignore

    # v372.0: neutronics–materials coupling (governance only; post-processing)
    from analysis.neutronics_materials_coupling_v372 import evaluate_neutronics_materials_coupling_v372  # type: ignore

_B_peak_T_tf = B_peak_T_tf  # keep a stable alias for the coil-geometry helper

def _hot_ion_point_uncached(inp: PointInputs, Paux_for_Q_MW: Optional[float] = None) -> Dict[str, float]:
    """
    Compute a Phase-1 operating point (0-D) with additional screening models.

    Returns a dict with:
      - performance: Pfus, Q, H98, tauE
      - power balance: Pin, Prad(core), P_SOL, etc.
      - engineering proxies: neutron wall loading, captured neutron power fraction
      - screening proxies: betaN_proxy, q95_proxy, f_bs_proxy
      - added "clean point design" screens:
          radial build + Bpeak + stress,
          HTS margin + dump voltage,
          divertor heat flux,
          TBR + HTS lifetime,
          net electric power closure.
    """
    # Output accumulator (must be defined early because many downstream blocks
    # write provenance/diagnostics before the final return assembly).
    # Keep this explicit and deterministic.
    out: Dict[str, Any] = {}
    # Repository root (used only for governance contracts / artifact stamping).
    # Must not influence physics beyond explicit contract defaults.
    repo_root = Path(__file__).resolve().parents[2]
    # ---------------------------
    # Geometry (tokamak proxies)
    # ---------------------------
    V = tokamak_volume(inp.R0_m, inp.a_m, inp.kappa)
    S = tokamak_surface_area(inp.R0_m, inp.a_m, inp.kappa)
    A_fw = first_wall_area_proxy(inp.R0_m, inp.a_m, inp.kappa)

    Ti = inp.Ti_keV
    Te = Ti / max(inp.Ti_over_Te, 1e-9)
    # ---------------------------
    # Optional analytic profiles (PROCESS-like scaffold)
    # ---------------------------
    profiles = None
    if (inp.profile_model or "none").lower() in ("parabolic", "pedestal", "eped"):
        # placeholders until ne/T are known; we rebuild after density calc
        if (inp.profile_model or "none").lower() == "pedestal":
            ne_prof = PedestalProfile(f_avg=1.0, alpha_core=max(inp.profile_peaking_ne, 0.0), rho_ped=inp.pedestal_rho_ped, f_edge_frac=inp.pedestal_edge_frac)
            Ti_prof = PedestalProfile(f_avg=1.0, alpha_core=max(inp.profile_peaking_T, 0.0), rho_ped=inp.pedestal_rho_ped, f_edge_frac=inp.pedestal_edge_frac)
            Te_prof = PedestalProfile(f_avg=1.0, alpha_core=max(inp.profile_peaking_T, 0.0), rho_ped=inp.pedestal_rho_ped, f_edge_frac=inp.pedestal_edge_frac)
        else:
            ne_prof = ParabolicProfile(f_avg=1.0, alpha=max(inp.profile_peaking_ne, 0.0))
            Ti_prof = ParabolicProfile(f_avg=1.0, alpha=max(inp.profile_peaking_T, 0.0))
            Te_prof = ParabolicProfile(f_avg=1.0, alpha=max(inp.profile_peaking_T, 0.0))
        profiles = PlasmaProfiles(ne=ne_prof, Ti=Ti_prof, Te=Te_prof)

    # ---------------------------
    # Density via Greenwald fraction
    # ---------------------------
    nGW20 = greenwald_density_20(inp.Ip_MA, inp.a_m)
    ne20 = inp.fG * nGW20
    ne_m3 = ne20 * 1e20
    if profiles is not None:
        # rebuild profiles with the now-known volume averages
        if (inp.profile_model or "none").lower() == "pedestal":
            profiles = PlasmaProfiles(
                ne=PedestalProfile(f_avg=ne_m3, alpha_core=max(inp.profile_peaking_ne, 0.0), rho_ped=inp.pedestal_rho_ped, f_edge_frac=inp.pedestal_edge_frac),
                Ti=PedestalProfile(f_avg=Ti, alpha_core=max(inp.profile_peaking_T, 0.0), rho_ped=inp.pedestal_rho_ped, f_edge_frac=inp.pedestal_edge_frac),
                Te=PedestalProfile(f_avg=Te, alpha_core=max(inp.profile_peaking_T, 0.0), rho_ped=inp.pedestal_rho_ped, f_edge_frac=inp.pedestal_edge_frac),
            )
        else:
            profiles = PlasmaProfiles(
                ne=ParabolicProfile(f_avg=ne_m3, alpha=max(inp.profile_peaking_ne, 0.0)),
                Ti=ParabolicProfile(f_avg=Ti, alpha=max(inp.profile_peaking_T, 0.0)),
                Te=ParabolicProfile(f_avg=Te, alpha=max(inp.profile_peaking_T, 0.0)),
            )

    # ---------------------------
    # Profile-derived averages (PROCESS-like diagnostics)
    # ---------------------------
    prof_stats = {
        'ne0_over_neV': float('nan'),
        'Ti0_over_TiV': float('nan'),
        'Te0_over_TeV': float('nan'),
        'ne_line_over_neV': float('nan'),
        'Ti_line_over_TiV': float('nan'),
        'Te_line_over_TeV': float('nan'),
        'ne2_over_neV2': float('nan'),
    }
    if profiles is not None:
        try:
            prof_stats.update({k: float(v) for k, v in profiles.derived_averages().items()})
        except Exception:
            pass

    # Fusion power (0-D, Maxwellian)
    # ---------------------------
    sv_DT = bosch_hale_sigmav(Ti, "DT")
    sv_DD = bosch_hale_sigmav(Ti, "DD_Tp") + bosch_hale_sigmav(Ti, "DD_He3n")

    # Fuel composition closure
    # - DT mode: assume 50/50 D/T ion mix (nD ~= nT ~= 0.5 ne)
    # - DD mode: assume pure deuterium ions (nD ~= ne), with optional secondary DT burn
    #           from tritium produced via the DD (d,p)T branch.
    fuel_mode = (inp.fuel_mode or "DT").upper()

    if fuel_mode == "DT":
        nD = 0.5 * ne_m3
        nT = 0.5 * ne_m3
    elif fuel_mode == "DD":
        nD = ne_m3
        nT = 0.0  # will be set by secondary-burn closure below (if enabled)
    else:
        raise ValueError(f"Unknown fuel_mode={inp.fuel_mode!r}; expected 'DT' or 'DD'")

    # ----------------
    # Fusion reactions (thermal Maxwellian reactivities; Bosch–Hale)
    # ----------------
    # Energies (MeV) and branch bookkeeping
    E_DT_MeV = 17.6
    E_DT_alpha_MeV = 3.5
    E_DT_n_MeV = 14.1

    # DD branches:
    #   D + D -> T (1.01 MeV) + p (3.02 MeV)      (charged products)
    #   D + D -> He3 (0.82 MeV) + n (2.45 MeV)
    E_DD_Tp_total_MeV = 4.03
    E_DD_Tp_charged_MeV = 4.03
    E_DD_He3n_total_MeV = 3.27
    E_DD_He3n_charged_MeV = 0.82
    E_DD_He3n_n_MeV = 2.45

    J_per_MeV = 1.602176634e-13

    sigv_DT = bosch_hale_sigmav(Ti, "DT")
    sigv_DD_Tp = bosch_hale_sigmav(Ti, "DD_Tp")
    sigv_DD_He3n = bosch_hale_sigmav(Ti, "DD_He3n")

    # Reaction rates [1/(m^3 s)]
    #  - DT: nD nT <σv>
    #  - DD: (1/2) nD^2 <σv> (identical reactants)
    R_DT = nD * nT * sigv_DT
    R_DD_Tp = 0.5 * nD * nD * sigv_DD_Tp
    R_DD_He3n = 0.5 * nD * nD * sigv_DD_He3n

    # In DD mode, optionally include secondary DT burn from DD-produced tritium.
    # Steady-state closure:
    #   production rate of T  = R_DD_Tp
    #   available-to-burn fraction = tritium_retention
    #   losses modeled by tau_T_loss_s
    #   consumption by DT burn = R_DT
    if fuel_mode == "DD" and bool(inp.include_secondary_DT):
        tau_T = max(float(inp.tau_T_loss_s), 1e-6)
        f_ret = min(max(float(inp.tritium_retention), 0.0), 1.0)

        # Solve for nT from: 0 = f_ret*R_DD_Tp - nT/tau_T - nD*nT*sigv_DT
        # => nT = (f_ret*R_DD_Tp) / (1/tau_T + nD*sigv_DT)
        nT = (f_ret * R_DD_Tp) / ((1.0 / tau_T) + (nD * sigv_DT))

        # Update DT rate with this nT
        R_DT = nD * nT * sigv_DT

    # Powers [MW]
    Pfus_DT_MW = (R_DT * (E_DT_MeV * J_per_MeV) * V) / 1e6
    Pfus_DD_MW = ((R_DD_Tp * (E_DD_Tp_total_MeV * J_per_MeV) +
                   R_DD_He3n * (E_DD_He3n_total_MeV * J_per_MeV)) * V) / 1e6

    # Charged-particle heating (proxy) [MW]
    P_charged_DT_MW = (R_DT * (E_DT_alpha_MeV * J_per_MeV) * V) / 1e6
    P_charged_DD_MW = ((R_DD_Tp * (E_DD_Tp_charged_MeV * J_per_MeV) +
                        R_DD_He3n * (E_DD_He3n_charged_MeV * J_per_MeV)) * V) / 1e6

    # Neutron power (proxy) [MW]
    P_n_DT_MW = (R_DT * (E_DT_n_MeV * J_per_MeV) * V) / 1e6
    P_n_DD_MW = (R_DD_He3n * (E_DD_He3n_n_MeV * J_per_MeV) * V) / 1e6

    # Apply "fuel dilution" to the fusion output used for Q.
    # (Phase-1 convention: treat dilution as a multiplicative performance penalty.)
    #
    # Optional helium-ash dilution (opt-in; default off):
    # Pfus_for_Q *= (1 - f_He_ash)^2
    ash_mode = str(getattr(inp, "ash_dilution_mode", "off") or "off").lower()
    f_he_ash = float(getattr(inp, "f_He_ash", 0.0) or 0.0)
    f_he_ash = min(max(f_he_ash, 0.0), 0.9)
    ash_factor = 1.0
    if ash_mode == "fixed_fraction":
        ash_factor = max((1.0 - f_he_ash) ** 2, 0.0)

    Pfus_for_Q_MW = (Pfus_DT_MW + Pfus_DD_MW) * inp.dilution_fuel * ash_factor
    Pfus_DT_adj_MW = Pfus_for_Q_MW  # alias for UI/legacy naming
    # Optional profile-integrated fusion diagnostic (PROCESS-like scaffold)
    Pfus_profile_MW = float("nan")
    ne_peak_fac = Ti_peak_fac = Te_peak_fac = float("nan")
    if profiles is not None:
        ne_peak_fac, Ti_peak_fac, Te_peak_fac = profiles.peaking_factors()

        def integrand(rho: float) -> float:
            ne_loc = profiles.ne.value(rho)
            Ti_loc = profiles.Ti.value(rho)
            sv_loc = bosch_hale_sigmav(Ti_loc, "DT")
            return (ne_loc**2) * sv_loc

        n = 400
        s = 0.0
        w = 0.0
        for i in range(n):
            r = (i + 0.5) / n
            weight = 2.0 * r
            s += integrand(r) * weight
            w += weight
        avg_n2sv = s / max(w, 1e-30)


        # DT fusion energy per reaction (J)
        E_FUS_J = E_DT_MeV * 1e6 * 1.602176634e-19
        nDnT_factor = 0.25  # 50/50 D-T
        Pfus_profile_W = nDnT_factor * avg_n2sv * E_FUS_J * V
        Pfus_profile_MW = Pfus_profile_W / 1e6

    Pfus_DD_W = Pfus_DD_MW * 1e6
    Pfus_DT_W = Pfus_DT_MW * 1e6
    Pfus_DT_adj_W = Pfus_DT_adj_MW * 1e6


    # ---------------------------
    # Neutron fractions (proxy)
    # ---------------------------
    # For this Phase-1 model:
    # - DT is treated as "equivalent" alpha-heating only (see below),
    # - DD neutron fraction is used for wall-loading proxy only.
    frac_n_DD = 0.5
    P_n_W = frac_n_DD * Pfus_DD_W

    # Shield capture proxy (placeholder): eps_n = 1 - exp(-t/lambda)
    eps_n = neutron_shield_capture(inp.t_shield_m)
    P_n_captured_W = eps_n * P_n_W
    S_n_W_m2 = P_n_W / max(A_fw, 1e-9)

    # ---------------------------
    # Radiation & power balance
    # ---------------------------
    if inp.include_radiation:
        # Diagnostic brems (placeholder; not used for power balance constraint)
        P_brem_MW = bremsstrahlung_W(ne_m3, Te, inp.zeff, V) / MW_TO_W
    else:
        P_brem_MW = 0.0

    # Alpha heating from DT-equivalent fusion (keep Phase-1 convention), with optional
    # prompt-loss proxy (opt-in) for fast-particle physics transparency.
    alpha_loss_model = str(getattr(inp, "alpha_loss_model", "fixed") or "fixed").lower()
    alpha_prompt_loss_k = float(getattr(inp, "alpha_prompt_loss_k", 0.0) or 0.0)

    # rho* proxy for alpha prompt loss model
    rho_star = float("nan")
    try:
        # Ion gyroradius proxy (D/T scale), using Ti and Bt.
        # rho_i = sqrt(m_i * Ti_J) / (e * B)
        m_i = 2.5 * 1.66053906660e-27  # kg (D/T average, proxy)
        Ti_J = max(Ti, 1e-9) * KEV_TO_J
        rho_i = (m_i * Ti_J) ** 0.5 / (1.602176634e-19 * max(inp.Bt_T, 1e-9))
        rho_star = rho_i / max(inp.a_m, 1e-9)
    except Exception:
        rho_star = float("nan")

    alpha_loss_frac_eff = float(inp.alpha_loss_frac)
    if alpha_loss_model == "rho_star":
        alpha_loss_frac_eff = float(inp.alpha_loss_frac) + alpha_prompt_loss_k * (rho_star if rho_star == rho_star else 0.0)

    alpha_loss_frac_eff = min(max(alpha_loss_frac_eff, 0.0), 0.9)

    if inp.include_alpha_loss:
        Palpha_MW = 0.2 * Pfus_DT_adj_MW * (1.0 - alpha_loss_frac_eff)
    else:
        Palpha_MW = 0.2 * Pfus_DT_adj_MW

    # Total input power (legacy): Pin = Paux + Palpha (kept unchanged)
    Pin_MW = inp.Paux_MW + Palpha_MW

    # --- Burn / ignition transparency metrics (diagnostic; does not change operating point) ---
    # Definitions are explicit to remain reviewer-audit-safe.
    #   - Ploss_MW is defined later as Pin - Prad_core (core) ...
    # Here we store Palpha now; M_ign is computed after Ploss is defined.

    # --- Transparent ion/electron channel bookkeeping (does not change totals) ---
    # Alpha ion/electron partition can be a simple opt-in proxy while keeping defaults.
    alpha_part_model = str(getattr(inp, "alpha_partition_model", "fixed") or "fixed").lower()
    alpha_part_k = float(getattr(inp, "alpha_partition_k", 0.0) or 0.0)

    f_alpha_i = float(getattr(inp, "f_alpha_to_ion", 0.85) or 0.0)
    if alpha_part_model == "te_ratio":
        # Very simple transparency proxy: shift fraction slightly with Te/(Ti+Te).
        x = Te / max((Ti + Te), 1e-9)
        f_alpha_i = f_alpha_i - alpha_part_k * (x - 0.5)

    f_aux_i = float(getattr(inp, "f_aux_to_ion", 0.50) or 0.0)
    f_alpha_i = min(max(f_alpha_i, 0.0), 1.0)
    f_aux_i = min(max(f_aux_i, 0.0), 1.0)

    Palpha_i_MW = Palpha_MW * f_alpha_i
    Palpha_e_MW = Palpha_MW * (1.0 - f_alpha_i)
    Paux_i_MW = inp.Paux_MW * f_aux_i
    Paux_e_MW = inp.Paux_MW * (1.0 - f_aux_i)

    # Ion↔electron equilibration power (diagnostic ledger term).
    # Sign convention: P_ie > 0 means power flows from ions to electrons (Ti > Te).
    P_ie_MW = float("nan")
    tau_ei_s = float("nan")
    if bool(getattr(inp, "include_P_ie", True)):
        try:
            # very lightweight Spitzer-like equilibration time proxy [s]
            # tau_ei ~ C * Te^(3/2) / (ne20)
            tau_ei_s = 0.12 * (max(Te, 1e-6) ** 1.5) / max(ne20, 1e-6)
            dT_keV = (Ti - Te)
            P_ie_MW = (1.5 * ne_m3 * V * (dT_keV * KEV_TO_J) / max(tau_ei_s, 1e-9)) / 1e6
        except Exception:
            P_ie_MW = float("nan")
            tau_ei_s = float("nan")
    # --------------------------
    # Core radiation model
    # --------------------------
    Prad_core_MW = 0.0
    rad_breakdown = {"P_brem_W": 0.0, "P_sync_W": 0.0, "P_line_W": 0.0, "P_total_W": 0.0}

    if inp.include_radiation:
        mode = (inp.radiation_model or "fractional").lower()
        if mode == "physics":
            species = str(getattr(inp, "impurity_species", "C"))
            frac = float(getattr(inp, "impurity_frac", 0.0))
            mix_str = str(getattr(inp, "impurity_mix", "") or "").strip()

            # Optional multi-impurity mix parsing (stringified JSON dict).
            mix_fracs = None
            if mix_str:
                try:
                    obj = json.loads(mix_str)
                    if isinstance(obj, dict):
                        mix_fracs = {str(k): float(v) for k, v in obj.items() if float(v) > 0.0}
                        if len(mix_fracs) == 0:
                            mix_fracs = None
                except Exception:
                    mix_fracs = None

            zeff_mode = str(getattr(inp, "zeff_mode", "fixed") or "fixed").lower()
            zeff_val = float(getattr(inp, "zeff", 1.8))
            if zeff_mode in {"from_impurity", "from_mix"}:
                if isinstance(mix_fracs, dict):
                    zeff_val = estimate_zeff_from_mix(mix_fracs)
                else:
                    zeff_val = estimate_zeff_from_single_impurity(species, frac)

            mix = ImpurityMix(
                zeff=zeff_val,
                species=species,
                frac=frac,
                species_fracs=mix_fracs,
            )
            rad_breakdown = total_core_radiation_W(
                ne_m3=ne_m3,
                Te_keV=Te,
                B_T=inp.Bt_T,
                R0_m=inp.R0_m,
                a_m=inp.a_m,
                volume_m3=V,
                mix=mix,
                include_synchrotron=bool(getattr(inp, "include_synchrotron", True)),
                include_line=True,
                lz_db_id=str(getattr(inp, "radiation_db", "proxy_v1") or "proxy_v1"),
            )
            Prad_core_MW = rad_breakdown["P_total_W"] / 1e6
            # Provenance for audit-grade reviewer packs
            out["radiation_lz_db_id"] = rad_breakdown.get("LZ_DB_ID", "")
            out["radiation_lz_db_sha256"] = rad_breakdown.get("LZ_DB_SHA256", "")
        else:
            # Default behavior: explicit radiated fraction (legacy)
            f_core = min(max(inp.f_rad_core, 0.0), 0.95)
            Prad_core_MW = f_core * Pin_MW

    # Power crossing separatrix (steady-state, 0-D):
    # P_SOL = Pin - Prad_core
    P_SOL_MW = max(Pin_MW - Prad_core_MW, 1e-9)

    # Explicit SOL/divertor radiated power partition (v228+)
    # Uses existing f_rad_div screening parameter; does not change core balance.
    Prad_SOL_MW = float("nan")
    try:
        f_div = float(getattr(inp, "f_rad_div", float("nan")))
        if f_div == f_div:
            f_div = min(max(f_div, 0.0), 0.95)
            Prad_SOL_MW = f_div * P_SOL_MW
    except Exception:
        Prad_SOL_MW = float("nan")

    P_SOL_over_R_MW_m = P_SOL_MW / max(inp.R0_m, 1e-9)

    # For confinement scaling, use Ploss as the power *not* radiated in the core.
    Ploss_MW = P_SOL_MW

    # Ignition-like margins (diagnostic):
    # - Core-loss margin: Palpha / Ploss (where Ploss excludes core radiation by definition).
    # - Total-loss margin: Palpha / (Ploss + Prad_core).
    M_ign_core = Palpha_MW / max(Ploss_MW, 1e-12)
    M_ign_total = Palpha_MW / max((Ploss_MW + Prad_core_MW), 1e-12)

    # ---------------------------
    # Thermal stored energy and confinement
    # ---------------------------
    W_J = 3.0 * ne_m3 * ((Te + Ti) * KEV_TO_J) * V
    W_MJ = W_J / 1e6

    # ---------------------------------------------------------------------
    # v358.0: Profile Family Library Authority (transport proxy, deterministic)
    # ---------------------------------------------------------------------
    pf_confinement_mult_eff = 1.0
    pf_bootstrap_mult_eff = 1.0
    pf_tag = "CORE_FLAT"
    try:
        if bool(getattr(inp, "include_profile_family_v358", False)):
            pf = compute_profile_family_factors_v358(
                family_raw=str(getattr(inp, "profile_family_v358", "CORE_FLAT")),
                p_peaking=float(getattr(inp, "profile_family_peaking_p", 1.0)),
                j_peaking=float(getattr(inp, "profile_family_peaking_j", 1.0)),
                shear_shape=float(getattr(inp, "profile_family_shear_shape", 0.5)),
                pedestal_frac=float(getattr(inp, "profile_family_pedestal_frac", 0.0)),
                confinement_mult_user=float(getattr(inp, "profile_family_confinement_mult", 1.0)),
                bootstrap_mult_user=float(getattr(inp, "profile_family_bootstrap_mult", 1.0)),
            )
            pf_confinement_mult_eff = float(pf.confinement_mult_eff)
            pf_bootstrap_mult_eff = float(pf.bootstrap_mult_eff)
            pf_tag = str(pf.tag)
            out["profile_family_tag"] = pf_tag
            out["profile_family_confinement_mult_eff"] = pf_confinement_mult_eff
            out["profile_family_bootstrap_mult_eff"] = pf_bootstrap_mult_eff
            out["profile_family_validity"] = pf.validity
            out["profile_family_p_peaking"] = float(pf.p_peaking)
            out["profile_family_j_peaking"] = float(pf.j_peaking)
            out["profile_family_shear_shape"] = float(pf.shear_shape)
            out["profile_family_pedestal_frac"] = float(pf.pedestal_frac)
        else:
            out["profile_family_tag"] = "DISABLED"
            out["profile_family_confinement_mult_eff"] = 1.0
            out["profile_family_bootstrap_mult_eff"] = 1.0
            out["profile_family_validity"] = {"v358_profile_family": False}
            out["profile_family_p_peaking"] = float("nan")
            out["profile_family_j_peaking"] = float("nan")
            out["profile_family_shear_shape"] = float("nan")
            out["profile_family_pedestal_frac"] = float("nan")
    except Exception:
        out["profile_family_tag"] = "ERROR"
        out["profile_family_confinement_mult_eff"] = float("nan")
        out["profile_family_bootstrap_mult_eff"] = float("nan")
        out["profile_family_validity"] = {"v358_profile_family": False, "error": True}
        out["profile_family_p_peaking"] = float("nan")
        out["profile_family_j_peaking"] = float("nan")
        out["profile_family_shear_shape"] = float("nan")
        out["profile_family_pedestal_frac"] = float("nan")
        pf_confinement_mult_eff = 1.0
        pf_bootstrap_mult_eff = 1.0
        pf_tag = "CORE_FLAT"
    # Contract fingerprint
    out["profile_family_contract_sha256"] = "fb01217507eaca85e571822be593426f693aba406885eb5a0ed07839835637ef"

    tauE_s = (W_MJ / max(Ploss_MW, 1e-9)) * max(getattr(inp, 'confinement_mult', 1.0), 0.0) * max(pf_confinement_mult_eff, 0.0)

    tauIPB_s = tauE_ipb98y2(
        Ip_MA=inp.Ip_MA, Bt_T=inp.Bt_T, ne20=ne20,
        Ploss_MW=Ploss_MW, R_m=inp.R0_m, a_m=inp.a_m,
        kappa=inp.kappa, M_amu=inp.A_eff
    )

    # L-mode comparator (ITER89P), used for optional confinement-regime coupling diagnostics.
    tauITER89_s = tauE_iter89p(
        Ip_MA=inp.Ip_MA, Bt_T=inp.Bt_T, ne20=ne20,
        Ploss_MW=Ploss_MW, R_m=inp.R0_m, a_m=inp.a_m,
        kappa=inp.kappa, M_amu=inp.A_eff
    )
    # Optional confinement scaling comparison
    tauScaling_s = tauIPB_s
    scaling_raw = getattr(inp, 'confinement_scaling', None)
    if scaling_raw is None:
        # Back-compat: older UI used 'confinement_model'
        scaling_raw = getattr(inp, 'confinement_model', 'ipb98y2')
    scaling = (str(scaling_raw) or 'IPB98y2').upper().replace(' ', '')
    # Reference scaling for reporting an H-factor comparator. Default remains IPB98(y,2).
    # Additional PROCESS-inspired comparators are provided for sensitivity studies.
    if scaling in {"ITER89P", "ITER89-P", "89P"}:
        tauScaling_s = tauE_iter89p(
            Ip_MA=inp.Ip_MA, Bt_T=inp.Bt_T, ne20=ne20,
            Ploss_MW=Ploss_MW, R_m=inp.R0_m, a_m=inp.a_m,
            kappa=inp.kappa, M_amu=inp.A_eff
        )
    elif scaling in {"KG", "KAYE", "KAYE-GOLDSTON", "KAYEGOLDSTON"}:
        tauScaling_s = tauE_kaye_goldston(
            Ip_MA=inp.Ip_MA, Bt_T=inp.Bt_T, ne20_lineavg=ne20,
            Ploss_MW=Ploss_MW, R_m=inp.R0_m, a_m=inp.a_m,
            kappa=inp.kappa, M_amu=inp.A_eff
        )
    elif scaling in {"NEOALC", "NEO-ALCATOR", "NEOALCATOR", "NA"}:
        qstar = q95_proxy_cyl(inp.R0_m, inp.a_m, inp.Bt_T, inp.Ip_MA, inp.kappa)
        tauScaling_s = tauE_neo_alcator(ne20_lineavg=ne20, R_m=inp.R0_m, a_m=inp.a_m, qstar=qstar)
    elif scaling in {"MIRNOV"}:
        tauScaling_s = tauE_mirnov(a_m=inp.a_m, kappa=inp.kappa, Ip_MA=inp.Ip_MA)
    elif scaling in {"SHIMOMURA", "SHIMO"}:
        tauScaling_s = tauE_shimomura(R_m=inp.R0_m, a_m=inp.a_m, Bt_T=inp.Bt_T, kappa=inp.kappa, M_amu=inp.A_eff)
    # Optional transport stiffness degradation (diagnostic, bounded)
    c_stiff = float(getattr(inp, "transport_stiffness_c", 0.0) or 0.0)
    Ploss_ref = float(getattr(inp, "Ploss_ref_MW", 100.0) or 100.0)
    stiff_fac = 1.0 + c_stiff * max(0.0, (Ploss_MW / max(Ploss_ref, 1e-9)) - 1.0)
    tauE_eff_s = tauE_s / max(stiff_fac, 1e-9)

    H98 = tauE_eff_s / max(tauIPB_s, 1e-12)
    H_scaling = tauE_eff_s / max(tauScaling_s, 1e-12)

    # Optional confinement-regime coupling (diagnostic only; does not change tauE_eff_s)
    # Compute a regime label from the Martin08 P_LH proxy (when available) and report
    # H_regime referenced to ITER89P in L-mode and IPB98y2 in H-mode.
    confinement_regime = "unknown"
    H_regime = float('nan')
    try:
        if bool(getattr(inp, "couple_regime_to_confinement", False)) and bool(getattr(inp, "include_hmode_physics", True)):
            PLH_tmp = p_LH_martin08(ne20, inp.Bt_T, S, A_eff=inp.A_eff)
            f_access = float(getattr(inp, "f_LH_access", 1.0) or 1.0)
            if math.isfinite(PLH_tmp) and PLH_tmp > 0:
                confinement_regime = "H" if (Pin_MW >= f_access * PLH_tmp) else "L"
                tau_iter89 = tauE_iter89p(
                    Ip_MA=inp.Ip_MA, Bt_T=inp.Bt_T, ne20=ne20,
                    Ploss_MW=Ploss_MW, R_m=inp.R0_m, a_m=inp.a_m,
                    kappa=inp.kappa, M_amu=inp.A_eff
                )
                tau_ref = tauIPB_s if confinement_regime == "H" else tau_iter89
                H_regime = tauE_eff_s / max(tau_ref, 1e-12)
    except Exception:
        confinement_regime = "unknown"
        H_regime = float('nan')

    # --- Derived (transparent) performance requirements ---
    # tauE_required is the energy confinement time implied by steady-state power balance W/Ploss.
    tauE_required_s = (W_MJ / max(Ploss_MW, 1e-9))
    # "Required H" expresses how much confinement (relative to IPB98(y,2)) is needed
    # to sustain the computed (Ti,Te,ne) operating point.
    H_required = tauE_required_s / max(tauIPB_s, 1e-12)

    # --- Power/confinement self-consistency residual (diagnostic; optional constraint) ---
    # Compare the power crossing the separatrix to the power implied by the chosen confinement scaling.
    # This is a feasibility/robustness diagnostic only; it does not change the operating point unless
    # explicitly constrained.
    cm = max(float(getattr(inp, 'confinement_mult', 1.0) or 0.0), 0.0)
    tauE_model_s = (tauScaling_s * cm) / max(stiff_fac, 1e-9)
    Ploss_from_tauE_model_MW = W_MJ / max(tauE_model_s, 1e-9)
    power_balance_residual_MW = Ploss_MW - Ploss_from_tauE_model_MW

    # Q definition (DT-equivalent) as in prior scripts
    Q_denom = inp.Paux_MW if Paux_for_Q_MW is None else Paux_for_Q_MW
    Q_DT_eqv = Pfus_DT_adj_MW / max(Q_denom, 1e-9)

    # -----------------------------------------------------------------
    # v371.0: Transport Contract Library (governance-only; no truth edits)
    # -----------------------------------------------------------------
    transport_contract_v371: Dict[str, Any] = {}
    try:
        if evaluate_transport_contracts_v371 is None:
            raise RuntimeError("transport contract module not importable")
        transport_contract_v371 = evaluate_transport_contracts_v371(
            inp=inp,
            out_partial={
                "ne20": ne20,
                "P_SOL_MW": Ploss_MW,
                "S_m2": S,
                "Paux_MW": float(getattr(inp, "Paux_MW", 0.0) or 0.0),
                "Palpha_dep_MW": float(locals().get("Palpha_dep_MW", 0.0) or 0.0),
                "Pin_MW": Pin_MW,
                "tauIPB_s": tauIPB_s,
                "tauE_required_s": tauE_required_s,
                "H_required": H_required,
            },
        )
    except Exception as e:
        transport_contract_v371 = {
            "transport_contracts_v371_enabled": False,
            "transport_contracts_v371_error": f"{type(e).__name__}: {e}",
        }

    # ---------------------------
    # Particle sustainability (optional diagnostic closure)
    # ---------------------------
    tau_p_s = float("nan")
    S_fuel_required_1e22_per_s = float("nan")
    fueling_ok = float("nan")
    if bool(getattr(inp, "include_particle_balance", False)):
        tau_p_over = float(getattr(inp, "tau_p_over_tauE", 3.0) or 0.0)
        tau_p_s = max(tau_p_over, 0.0) * max(tauE_eff_s, 0.0)
        if tau_p_s > 0.0:
            N_e = ne_m3 * V
            S_fuel_required_1e22_per_s = (N_e / tau_p_s) / 1e22
        # Optional cap (treated as feasibility constraint if set)
        Smax = float(getattr(inp, "S_fuel_max_1e22_per_s", float("nan")))
        if Smax == Smax and Smax > 0.0:
            fueling_ok = 1.0 if (S_fuel_required_1e22_per_s <= Smax) else 0.0
        else:
            fueling_ok = 1.0

    out: Dict[str, float] = {
        # Inputs
        "R0_m": inp.R0_m,
        "a_m": inp.a_m,
        "kappa": inp.kappa,
        "delta": float(getattr(inp, "delta", 0.0) or 0.0),
        "kappa_max": float(getattr(inp, "kappa_max", float("nan"))),
        "delta_min": float(getattr(inp, "delta_min", float("nan"))),
        "delta_max": float(getattr(inp, "delta_max", float("nan"))),
        "B0_T": inp.Bt_T,
        "Ip_MA": inp.Ip_MA,
        "Ti_keV": Ti,
        "Te_keV": Te,
        "profile_model": inp.profile_model,
        "profile_peaking_ne": inp.profile_peaking_ne,
        "profile_peaking_T": inp.profile_peaking_T,
        "ne0_over_neV": prof_stats["ne0_over_neV"],
        "Ti0_over_TiV": prof_stats["Ti0_over_TiV"],
        "Te0_over_TeV": prof_stats["Te0_over_TeV"],
        "ne_line_over_neV": prof_stats["ne_line_over_neV"],
        "Ti_line_over_TiV": prof_stats["Ti_line_over_TiV"],
        "Te_line_over_TeV": prof_stats["Te_line_over_TeV"],
        "ne2_over_neV2": prof_stats["ne2_over_neV2"],

        # Density / particle clarity (expert auditability)
        # - fG: Greenwald fraction input
        # - nGW: Greenwald density in 1e20 m^-3 units
        # - ne20: line-avg electron density proxy (1e20 m^-3 units)
        # - ne_m3: same density in SI units (m^-3)
        "fG": float(inp.fG),
        "f_G": float(inp.fG),  # legacy key (kept)
        "nGW": float(nGW20),
        "ne_m3": float(ne_m3),
        "t_shield_m": inp.t_shield_m,

        # Geometry
        "V": V,
        "A_fw_m2": A_fw,
        "ne20": ne20,
        "fuel_mode": fuel_mode,
        "nT_over_ne": (nT / ne_m3) if ne_m3>0 else 0.0,
        "tritium_retention": float(inp.tritium_retention),
        "tau_T_loss_s": float(inp.tau_T_loss_s),
        "include_secondary_DT": float(bool(inp.include_secondary_DT)),

        # Fusion
        "Pfus_DD_MW": Pfus_DD_MW,
        "Pfus_DT_eqv_MW": Pfus_DT_MW,
        "Pfus_DT_adj_MW": Pfus_DT_adj_MW,
        "Pfus_DT_MW": Pfus_DT_MW,
        # Optional ash dilution proxy (defaults off)
        "ash_dilution_mode": ash_mode,
        "f_He_ash": f_he_ash,
        "ash_factor": ash_factor,
        "Pfus_profile_MW": Pfus_profile_MW,
        "ne_peaking": ne_peak_fac,
        "T_peaking": Ti_peak_fac,
        "P_charged_DT_MW": P_charged_DT_MW,
        "P_charged_DD_MW": P_charged_DD_MW,
        "P_n_DT_MW": P_n_DT_MW,
        "P_n_DD_MW": P_n_DD_MW,

        # Power balance
        "Paux_MW": inp.Paux_MW,
        # Alpha prompt-loss / partition diagnostics (defaults preserve legacy)
        "alpha_loss_model": alpha_loss_model,
        "alpha_loss_frac_eff": alpha_loss_frac_eff,
        "rho_star": rho_star,
        "alpha_partition_model": alpha_part_model,
        "f_alpha_to_ion_eff": f_alpha_i,
        "Palpha_MW": Palpha_MW,
        "Pin_MW": Pin_MW,
        "Palpha_i_MW": Palpha_i_MW,
        "Palpha_e_MW": Palpha_e_MW,
        "Paux_i_MW": Paux_i_MW,
        "Paux_e_MW": Paux_e_MW,
        "P_ie_MW": P_ie_MW,
        "tau_ei_s": tau_ei_s,
        "P_brem_MW": P_brem_MW,
        "Prad_core_MW": Prad_core_MW,
        "Prad_SOL_MW": Prad_SOL_MW,
        "Prad_total_MW": float(Prad_core_MW + (Prad_SOL_MW if Prad_SOL_MW == Prad_SOL_MW else 0.0)),
        "Prad_brem_MW": rad_breakdown.get("P_brem_W",0.0)/1e6,
        "Prad_sync_MW": rad_breakdown.get("P_sync_W",0.0)/1e6,
        "Prad_line_MW": rad_breakdown.get("P_line_W",0.0)/1e6,
        "include_radiation": bool(getattr(inp, "include_radiation", False)),
        "zeff": float(getattr(inp, "zeff", float("nan"))),
        "zeff_mode": str(getattr(inp, "zeff_mode", "fixed")),
        "dilution_fuel": float(getattr(inp, "dilution_fuel", float("nan"))),
        "ash_dilution_mode": str(getattr(inp, "ash_dilution_mode", "off")),
        "f_He_ash": float(getattr(inp, "f_He_ash", 0.0)),
        "radiation_model": (inp.radiation_model or "fractional"),
        "radiation_db": str(getattr(inp, "radiation_db", "proxy_v1") or "proxy_v1"),
        "radiation_db_id_used": str(rad_breakdown.get("LZ_DB_ID", "")),
        "radiation_db_sha256": str(rad_breakdown.get("LZ_DB_SHA256", "")),
        "profile_model": str(getattr(inp, "profile_model", "none")),
        "profile_mode": bool(getattr(inp, "profile_mode", False)),
        "bootstrap_model": str(getattr(inp, "bootstrap_model", "proxy")),
        "P_SOL_MW": P_SOL_MW,
        "P_SOL_over_R_MW_m": P_SOL_over_R_MW_m,
        "P_SOL_over_R_max_MW_m": inp.P_SOL_over_R_max_MW_m,
        "Ploss_MW": Ploss_MW,

        # Burn / ignition transparency (diagnostic; optional constraint via ignition_margin_min)
        "P_loss_total_MW": float(Ploss_MW + Prad_core_MW),
        "M_ign": float(M_ign_core),
        "M_ign_total": float(M_ign_total),
        "ignition_margin_min": float(getattr(inp, "ignition_margin_min", float("nan"))),

        # Confinement
        "W_MJ": W_MJ,
        "tauE_s": tauE_s,
        "tauIPB98_s": tauIPB_s,
        "H98": H98,
        "tauE_eff_s": tauE_eff_s,
        "tauScaling_s": tauScaling_s,
        "H_scaling": H_scaling,
        # Derived requirements (outputs, not targets)
        "tauE_required_s": tauE_required_s,
        "H_required": H_required,
        # Power/confinement self-consistency diagnostic
        "Ploss_from_tauE_model_MW": Ploss_from_tauE_model_MW,
        "power_balance_residual_MW": power_balance_residual_MW,
        "power_balance_tol_MW": float(getattr(inp, "power_balance_tol_MW", float("nan"))),
        # Optional stability caps (screening proxies)
        "betaN_max": float(getattr(inp, "betaN_max", float("nan"))),
        "betaN_troyon_max": float(getattr(inp, "betaN_troyon_max", float("nan"))),
        "q95_min": float(getattr(inp, "q95_min", float("nan"))),
        "Q_DT_eqv": Q_DT_eqv,
        "tau_p_s": tau_p_s,
        "S_fuel_required_1e22_per_s": S_fuel_required_1e22_per_s,
        "S_fuel_max_1e22_per_s": float(getattr(inp, "S_fuel_max_1e22_per_s", float("nan"))),
        "fueling_ok": fueling_ok,

        # Neutron/shield proxies
        "eps_n": eps_n,
        "P_n_captured_MW": P_n_captured_W / MW_TO_W,
        "S_n_W_m2": S_n_W_m2,
    }

    # ---------------------------
    # H-mode access check (Martin-08)
    # ---------------------------
    if inp.include_hmode_physics:
        PLH = p_LH_martin08(ne20, inp.Bt_T, S, A_eff=inp.A_eff)
        out["P_LH_MW"] = PLH
        if inp.require_Hmode:
            margin = 1.0 + max(inp.PLH_margin, 0.0)
            out["P_LH_required_MW"] = margin * PLH
            out["LH_ok"] = 1.0 if inp.Paux_MW >= margin * PLH else 0.0
        else:
            out["P_LH_required_MW"] = float("nan")
            out["LH_ok"] = 1.0
    else:
        out["P_LH_MW"] = float("nan")
        out["P_LH_required_MW"] = float("nan")
        out["LH_ok"] = float("nan")

    # --- Confinement regime coupling (diagnostic; no truth mutation) ---
    # Determine L/H label from P_heat vs Martin08 P_LH and report a regime-referenced H-factor.
    try:
        f_lh = float(getattr(inp, "f_LH_access", 1.0) or 1.0)
    except Exception:
        f_lh = 1.0
    f_lh = min(max(f_lh, 0.2), 5.0)

    PLH_val = float(out.get("P_LH_MW", float("nan")))
    if math.isfinite(PLH_val):
        confinement_regime = "H" if float(Pin_MW) >= f_lh * PLH_val else "L"
    else:
        confinement_regime = "unknown"

    H_regime = float("nan")
    try:
        if bool(getattr(inp, "couple_regime_to_confinement", False)) and confinement_regime in {"H", "L"}:
            tau_ref = float(tauIPB_s) if confinement_regime == "H" else float(tauITER89_s)
            H_regime = float(tauE_eff_s) / max(tau_ref, 1e-12)
    except Exception:
        H_regime = float("nan")

    out["f_LH_access"] = float(f_lh)
    out["confinement_regime"] = str(confinement_regime)
    out["H_regime"] = float(H_regime)
    out["tauITER89_s"] = float(tauITER89_s)

    # ---------------------------    # ---------------------------
    # Optional SOL width metric (Eich λq)
    # ---------------------------
    if inp.use_lambda_q:
        Bpol = Bpol_outboard_midplane_T(inp.Ip_MA, inp.a_m)
        out["Bpol_out_mid_T"] = Bpol
        out["lambda_q_mm"] = lambda_q_eich14_mm(Bpol, factor=float(inp.lambda_q_factor))
    else:
        out["Bpol_out_mid_T"] = float("nan")
        out["lambda_q_mm"] = float("nan")


    # Screening proxies (β, βN, q95, bootstrap)
    # ---------------------------
    p_Pa = ne_m3 * ((Te + Ti) * KEV_TO_J)
    B2_over_2mu0 = (inp.Bt_T**2) / (2.0 * 4e-7 * math.pi)
    beta = p_Pa / max(B2_over_2mu0, 1e-30)
    betaN = betaN_from_beta(beta, inp.a_m, inp.Bt_T, inp.Ip_MA)
    
    q95 = q95_proxy_cyl(inp.R0_m, inp.a_m, inp.Bt_T, inp.Ip_MA, inp.kappa)

    # -------------------------------------------------------------------------
    # Cross-check (non-authoritative): PROCESS-style q95–Ip–Bt relation
    # -------------------------------------------------------------------------
    # This is a *sanity* diagnostic inspired by the common PROCESS relation used
    # in lightweight system codes (e.g., Toka_LITE). It does NOT feed back into
    # any solver logic and does not change feasibility.
    try:
        A = float(inp.R0_m) / max(float(inp.a_m), 1e-12)
        k = float(getattr(inp, "kappa", 1.0) or 1.0)
        d = float(getattr(inp, "delta", 0.0) or 0.0)
        den = (1.0 - A * A)
        if abs(den) < 1e-12:
            den = 1e-12
        f1 = (1.17 - 0.65 * A * A) / den
        f2 = 0.5 * (1.0 + k * k)
        f3 = 1.0 + 2.0 * d * d - 1.2 * d * d * d
        fq_proc = float(f1 * f2 * f3)
        Ip_proc_MA = float(5.0 * inp.a_m * inp.a_m * inp.Bt_T / max(q95 * inp.R0_m * fq_proc, 1e-30))
        out["q95_proc_fq"] = fq_proc
        out["Ip_from_q95_PROCESS_MA"] = Ip_proc_MA
        out["Ip_vs_PROCESS_ratio"] = float(inp.Ip_MA / max(Ip_proc_MA, 1e-12))
    except Exception:
        out["q95_proc_fq"] = float("nan")
        out["Ip_from_q95_PROCESS_MA"] = float("nan")
        out["Ip_vs_PROCESS_ratio"] = float("nan")

    # ---------------------------
    # Optional EPED-like pedestal surrogate (lightweight)
    # ---------------------------
    # If profile_model == 'eped' OR eped_surrogate is True, auto-set pedestal width
    # from simple performance proxies. This is NOT a full EPED model; it provides
    # PROCESS-like sensitivity of fusion/radiation to pedestal shape.
    out["rho_ped"] = float("nan")
    out["w_ped"] = float("nan")
    if profiles is not None and ((inp.profile_model or "none").lower() == "eped" or getattr(inp, "eped_surrogate", False)):
        eps = inp.a_m / max(inp.R0_m, 1e-9)
        beta_p = beta / max(eps, 1e-9)
        w_ped = max(0.03, min(0.12, 0.05 * math.sqrt(max(beta_p, 0.0))))
        rho_ped = max(0.80, min(0.98, 1.0 - w_ped))
        profiles = PlasmaProfiles(
            ne=PedestalProfile(f_avg=ne_m3, alpha_core=max(inp.profile_peaking_ne, 0.0), rho_ped=rho_ped, f_edge_frac=inp.pedestal_edge_frac),
            Ti=PedestalProfile(f_avg=Ti, alpha_core=max(inp.profile_peaking_T, 0.0), rho_ped=rho_ped, f_edge_frac=inp.pedestal_edge_frac),
            Te=PedestalProfile(f_avg=Te, alpha_core=max(inp.profile_peaking_T, 0.0), rho_ped=rho_ped, f_edge_frac=inp.pedestal_edge_frac),
        )
        try:
            prof_stats.update(profiles.derived_averages())
        except Exception:
            pass
        out["rho_ped"] = rho_ped
        out["w_ped"] = w_ped

    # Bootstrap/current fraction model selection (policy-tagged)
    bs_mode = (inp.bootstrap_model or "proxy").strip().lower()
    out["bootstrap_model"] = bs_mode
    eps = inp.a_m / max(inp.R0_m, 1e-9)
    out["eps"] = eps
    out["C_bs"] = float(getattr(inp, "C_bs", 0.15) or 0.15)
    beta_p = beta / max(eps, 1e-9)
    # default grad proxy =0; updated later if analytic profiles are enabled
    grad_proxy = 0.0
    if bs_mode == "improved":
        fbs = bootstrap_fraction_improved(beta_p, q95, eps)
    elif bs_mode == "sauter":
        # Sauter-inspired proxy: becomes profile-sensitive when profile diagnostics are enabled.
        fbs = bootstrap_fraction_sauter_proxy(beta_p, q95, eps, grad_proxy=grad_proxy)
    else:
        fbs = bootstrap_fraction_proxy(betaN, q95, C_bs=inp.C_bs)

    # Optional profile-informed adjustment (diagnostic-strength, bounded)
    if getattr(inp, "profile_mode", False):
        try:
            prof = build_profiles_from_volume_avgs(
                Tbar_keV=inp.Ti_keV,
                nbar20=ne20,
                alpha_T=float(getattr(inp, "profile_alpha_T", 1.5)),
                alpha_n=float(getattr(inp, "profile_alpha_n", 1.0)),
                ngrid=51,
                pedestal_enabled=bool(getattr(inp, "pedestal_enabled", False)),
                ped_width_a=float(getattr(inp, "pedestal_width_a", 0.05)),
                ped_top_T_frac=float(getattr(inp, "pedestal_top_T_frac", 0.6)),
                ped_top_n_frac=float(getattr(inp, "pedestal_top_n_frac", 0.8)),
                pedestal_model=str(getattr(inp, "profile_pedestal_model", getattr(inp, "pedestal_model", "tanh"))),
                pedestal_edge_T_frac=float(getattr(inp, "pedestal_edge_T_frac", getattr(inp, "pedestal_edge_frac", 0.2))),
                pedestal_edge_n_frac=float(getattr(inp, "pedestal_edge_n_frac", getattr(inp, "pedestal_edge_frac", 0.2))),
            )
            gp = gradient_proxy_at_pedestal(prof)
            g = float(gp.get("abs_dlnp_dr@r~0.9", 0.0))
            # Profile sensitivity:
            # - For legacy proxies: small bounded multiplier
            # - For 'sauter' proxy: recompute with grad-proxy as an explicit input
            if bs_mode == "sauter":
                fbs = bootstrap_fraction_sauter_proxy(beta_p, q95, eps, grad_proxy=g)
            else:
                fbs *= min(1.25, 1.0 + 0.08 * g)
            out["profile_meta"] = prof.meta
            out["profile_grad_proxy"] = gp
        except Exception:
            # Profile diagnostics should never crash point evaluation
            pass
    out["beta_proxy"] = beta
    out["beta_N"] = betaN
    out["betaN_proxy"] = betaN
    out["q95_proxy"] = q95

    out["f_bs_proxy"] = fbs

    # ---------------------------------------------------------------------
    # v296.0: 1.5D profile authority bundle (deterministic, non-iterative)
    # ---------------------------------------------------------------------
    try:
        # Map existing UI knobs into a compact profile spec.
        # profile_peaking_T and profile_peaking_ne are legacy shape knobs (>=0).
        ppk = 1.0 + 0.15 * max(0.0, float(getattr(inp, "profile_peaking_T", 0.0)))
        jpk = 1.0 + 0.10 * max(0.0, float(getattr(inp, "profile_peaking_ne", 0.0)))
        shear = float(getattr(inp, "profile_shear_shape", 0.5))
        # v358 profile family override: when enabled, use certified family shape factors
        try:
            if bool(getattr(inp, "include_profile_family_v358", False)) and (out.get("profile_family_p_peaking") == out.get("profile_family_p_peaking")):
                # Map p_peaking -> legacy ppk knob, and j_peaking -> legacy jpk knob
                ppk = float(out.get("profile_family_p_peaking", ppk))
                jpk = float(out.get("profile_family_j_peaking", jpk))
                shear = float(out.get("profile_family_shear_shape", shear))
        except Exception:
            pass

        pb = evaluate_profile_bundle(ProfileSpec(p_peaking=ppk, j_peaking=jpk, shear_shape=shear), beta_n=betaN, q95=q95, r_major_m=inp.R0_m, a_minor_m=inp.a_m)
        out["profile_p_peaking"] = pb.p_peaking
        out["profile_j_peaking"] = pb.j_peaking
        out["profile_li_proxy"] = pb.li_proxy
        out["profile_qmin_proxy"] = pb.qmin_proxy
        out["profile_f_bootstrap_proxy"] = pb.f_bootstrap
        out["profile_validity"] = pb.validity
        out["profile_assumption_tag"] = profile_assumption_tag(pb)
    except Exception:
        out["profile_p_peaking"] = float("nan")
        out["profile_j_peaking"] = float("nan")
        out["profile_li_proxy"] = float("nan")
        out["profile_qmin_proxy"] = float("nan")
        out["profile_f_bootstrap_proxy"] = float("nan")
        out["profile_validity"] = {}
        out["profile_assumption_tag"] = "PROFILE:unknown"


    # =========================================================================
    # Added: (2b) Current drive closure (very lightweight, SPARC-style bookkeeping)
    # =========================================================================
    Ip_A = inp.Ip_MA * 1e6
    # Use the profile-bundle bootstrap proxy when available to maintain self-consistency
    _fbs_used = out.get("profile_f_bootstrap_proxy", float("nan"))
    try:
        _fbs_used = float(_fbs_used)
    except Exception:
        _fbs_used = float("nan")
    if not ( _fbs_used == _fbs_used and abs(_fbs_used) < 1e300 ):
        try:
            _fbs_used = float(fbs)
        except Exception:
            _fbs_used = float("nan")
    I_bs_A = (_fbs_used * Ip_A) if (_fbs_used == _fbs_used and abs(_fbs_used) < 1e300) else float("nan")
    P_CD_MW = float(getattr(inp, "P_CD_MW", 0.0))
    eta_CD_A_W = float(getattr(inp, "eta_CD_A_W", 0.04e-6))
    I_cd_A = max(0.0, eta_CD_A_W * (P_CD_MW * 1e6))
    f_NI = (I_bs_A + I_cd_A) / max(Ip_A, 1e-9) if (I_bs_A == I_bs_A) else float("nan")
    out["P_CD_MW"] = P_CD_MW
    out["eta_CD_A_W"] = eta_CD_A_W
    out["I_bs_MA"] = I_bs_A / 1e6 if (I_bs_A == I_bs_A) else float("nan")
    out["I_cd_MA"] = I_cd_A / 1e6
    out["f_NI"] = f_NI

        # =========================================================================
    # Added: (1) radial build + TF peak field mapping + hoop stress
    # =========================================================================
    # v23 upgrade: explicit inboard stack solver (still transparent sums).
    from engineering.radial_stack_solver import build_inboard_stack_from_inputs, inboard_stack_closure, suggest_stack_repairs

    stack = build_inboard_stack_from_inputs(inp)
    closure = inboard_stack_closure(inp.R0_m, inp.a_m, stack, delta=float(getattr(inp, "delta", 0.0) or 0.0))

    ok_build = bool(closure["radial_build_ok"] >= 0.5)
    R_coil_inner = float(closure["R_coil_inner_m"])

    # Backward-compatible scalar keys (used by constraints/UI)
    out["inboard_space_m"] = float(closure["inboard_space_m"])
    out["spent_noncoil_m"] = float(closure["spent_noncoil_m"])
    out["inboard_build_total_m"] = float(closure["inboard_build_total_m"])
    out["inboard_margin_m"] = float(closure["inboard_margin_m"])
    out["stack_ok"] = float(closure["stack_ok"])

    # Structured stack for reports/UI (optional; ignored by legacy consumers)
    out["radial_stack"] = [r.to_dict() for r in stack]
    out["stack_repairs"] = suggest_stack_repairs(out["inboard_margin_m"])

    if ok_build:
        Bpk = B_peak_T(inp.Bt_T, inp.R0_m, R_coil_inner, peak_factor=inp.Bpeak_factor)
        sigma_MPa = hoop_stress_MPa(Bpk, R_coil_inner, inp.t_tf_struct_m)
    else:
        # If the inboard stack does not close, downstream magnet/HTS metrics are undefined.
        Bpk = float("nan")
        sigma_MPa = float("nan")

    out["R_coil_inner_m"] = float(R_coil_inner)
    out["radial_build_ok"] = float(closure["radial_build_ok"])
    out["B_peak_T"] = float(Bpk)
    out["B_peak_allow_T"] = float(inp.B_peak_allow_T)
    out["H98_allow"] = float(getattr(inp, "H98_allow", float("nan")))
    out["sigma_hoop_MPa"] = float(sigma_MPa)
    out["sigma_vm_MPa"] = von_mises_stress_MPa(Bpk, R_coil_inner, inp.t_tf_struct_m) if math.isfinite(Bpk) else float("nan")
    out["sigma_allow_MPa"] = float(inp.sigma_allow_MPa)


    

    # =========================================================================
    # Added: (2) Magnet Technology Authority 4.1 (LTS/HTS/Cu) -> regime contract
    # =========================================================================
    tech = str(getattr(inp, "magnet_technology", "HTS_REBCO") or "HTS_REBCO").strip().upper()
    out["magnet_technology"] = tech
    out["tf_sc_flag"] = float(tf_sc_flag(tech))

    # Contract-driven regime and limits (no runtime overrides).
    try:
        from ..contracts.magnet_tech_contract import (
            CONTRACT_SHA256,
            infer_magnet_regime,
            limits_for_regime,
            regime_consistent,
            classify_fragility,
        )  # type: ignore
        regime = infer_magnet_regime(tech)
        lims = limits_for_regime(regime)
        out["magnet_regime"] = str(regime)
        out["magnet_contract_sha256"] = str(CONTRACT_SHA256)
        out.update(lims.to_outputs_dict())
        out["magnet_regime_consistent"] = float(1.0 if regime_consistent(tech, regime) else 0.0)
    except Exception:
        # Fail-safe: keep legacy behavior if contract import fails (should not happen).
        out["magnet_regime"] = "UNKNOWN"
        out["magnet_contract_sha256"] = ""
        out["magnet_regime_consistent"] = float("nan")

    # Technology temperature (used by SC critical-surface proxy).
    out["Tcoil_K"] = float(getattr(inp, "Tcoil_K", 20.0))

    # Engineering current density proxy (A/mm^2): NI/A with A ~ t_tf_wind * (2*kappa*a).
    try:
        MU0 = 4e-7 * math.pi
        wp_width_m = float(getattr(inp, "t_tf_wind_m", 0.0))
        wp_height_m = 2.0 * float(inp.kappa) * float(inp.a_m)
        area_wp_m2 = max(wp_width_m * wp_height_m, 1e-12)
        J_eng_A_m2 = required_ampere_turns_A(float(inp.Bt_T), float(inp.R0_m)) / area_wp_m2
        out["J_eng_A_mm2"] = float(J_eng_A_m2 / 1e6)
    except Exception:
        out["J_eng_A_mm2"] = float("nan")

    # SC (HTS/LTS) margin proxy
    if math.isfinite(Bpk) and out.get("tf_sc_flag", 0.0) >= 0.5 and out.get("magnet_regime_consistent", 1.0) >= 0.5:
        # Unified SC margin (back-compat key kept as hts_margin)
        hts_margin = sc_operating_margin(
            Bpk,
            out["Tcoil_K"],
            tech,
            strain=getattr(inp, "hts_strain", 0.0),
            strain_crit=getattr(inp, "hts_strain_crit", 0.004),
            Jc_mult=float(getattr(inp, "hts_Jc_mult", 1.0)),
        )
        out["hts_margin"] = float(hts_margin)
        # hts_margin_min is already provided by contract (fallback to legacy input if absent)
        if "hts_margin_min" not in out or not math.isfinite(float(out.get("hts_margin_min", float("nan")))):
            out["hts_margin_min"] = float(getattr(inp, "hts_margin_min", 1.0))
        out["P_tf_ohmic_MW"] = float("nan")
    elif math.isfinite(Bpk) and tech == "COPPER":
        # Copper: margin not defined; provide resistive power proxy.
        wp_area = float(getattr(inp, "t_tf_wind_m", 0.0)) * (2.0 * float(inp.kappa) * float(inp.a_m))
        MU0 = 4e-7 * math.pi
        Jop = (float(inp.Bt_T) * 2.0 * math.pi * float(inp.R0_m) / MU0) / max(wp_area, 1e-12)
        out["P_tf_ohmic_MW"] = float(copper_tf_ohmic_power_MW(Jop, wp_area, float(inp.R0_m)))
        out["hts_margin"] = float("nan")
    else:
        # Undefined build or unknown tech
        out["hts_margin"] = float("nan")
        out["P_tf_ohmic_MW"] = float("nan")

    # Quench proxy margin (conservative, deterministic):
    # use the minimum of (dump-voltage headroom) and coil thermal margin when available.
    try:
        vdump = float(out.get("V_dump_kV", float("nan")))
        vmax = float(out.get("Vmax_kV", float("nan")))
        dv = (vmax - vdump) / max(vmax, 1e-9) if (math.isfinite(vdump) and math.isfinite(vmax)) else float("nan")
        th = float(out.get("coil_thermal_margin", float("nan")))
        qproxy = min(dv, th) if (math.isfinite(dv) and math.isfinite(th)) else (dv if math.isfinite(dv) else th)
        out["quench_proxy_margin"] = float(qproxy)
    except Exception:
        out["quench_proxy_margin"] = float("nan")

    # Magnet min-margin diagnostic (for verdict banners / fragility).
    try:
        margins = []
        # Signed margins as fractions (positive ok). Where limits exist.
        if math.isfinite(float(out.get("B_peak_T", float("nan")))) and math.isfinite(float(out.get("B_peak_allow_T", float("nan")))):
            margins.append((float(out["B_peak_allow_T"]) - float(out["B_peak_T"])) / max(float(out["B_peak_allow_T"]), 1e-9))
        if math.isfinite(float(out.get("sigma_vm_MPa", float("nan")))) and math.isfinite(float(out.get("sigma_allow_MPa", float("nan")))):
            margins.append((float(out["sigma_allow_MPa"]) - float(out["sigma_vm_MPa"])) / max(float(out["sigma_allow_MPa"]), 1e-9))
        if math.isfinite(float(out.get("J_eng_A_mm2", float("nan")))) and math.isfinite(float(out.get("J_eng_max_A_mm2", float("nan")))):
            margins.append((float(out["J_eng_max_A_mm2"]) - float(out["J_eng_A_mm2"])) / max(float(out["J_eng_max_A_mm2"]), 1e-9))
        if math.isfinite(float(out.get("coil_heat_nuclear_MW", float("nan")))) and math.isfinite(float(out.get("coil_heat_nuclear_max_MW", float("nan")))):
            margins.append((float(out["coil_heat_nuclear_max_MW"]) - float(out["coil_heat_nuclear_MW"])) / max(float(out["coil_heat_nuclear_max_MW"]), 1e-9))
        if margins:
            mmin = min(margins)
        else:
            mmin = float("nan")
        out["magnet_margin_min"] = float(mmin)
        try:
            out["magnet_fragility_class"] = str(classify_fragility(float(mmin)))
        except Exception:
            out["magnet_fragility_class"] = "UNKNOWN"
    except Exception:
        out["magnet_margin_min"] = float("nan")
        out["magnet_fragility_class"] = "UNKNOWN"


# Stored energy / dump voltage proxy (TF system)
    # Effective magnetic volume proxy:
    #   - take toroidal circumference ~ 2πR0
    #   - vertical extent ~ 2 κ a
    #   - radial thickness ~ (t_tf_wind + t_tf_struct)
    # This is *not* a real coil volume; it is only a scaling for E.
    h_tf = 2.0 * inp.kappa * inp.a_m
    t_tf_total = inp.t_tf_wind_m + inp.t_tf_struct_m
    V_tf_eff = inp.tf_energy_volume_factor * (2.0 * math.pi * inp.R0_m) * h_tf * max(t_tf_total, 1e-6)

    if math.isfinite(Bpk) and ok_build:
        I_tf = tf_current_A(Bpk, max(R_coil_inner, 1e-6), N_turns=inp.N_tf_turns)
        E_tf = tf_stored_energy_J(Bpk, V_tf_eff)
        Vdump_kV = dump_voltage_kV(E_tf, I_tf, inp.tau_dump_s)
    else:
        I_tf = float("nan")
        E_tf = float("nan")
        Vdump_kV = float("nan")

    out["I_tf_A"] = I_tf
    out["E_tf_MJ"] = E_tf / 1e6
    out["V_dump_kV"] = Vdump_kV
    out["Vmax_kV"] = inp.Vmax_kV
    out["tau_dump_s"] = inp.tau_dump_s
    out["N_tf_turns"] = float(inp.N_tf_turns)

    # =========================================================================
    # Added: (3) Divertor / SOL exhaust (unified API)
    # =========================================================================
    lam_mm = out.get("lambda_q_mm", float("nan"))
    f_div = min(max(float(getattr(inp, "f_rad_div", 0.0)), 0.0), 0.99)

    if math.isfinite(lam_mm):
        ex = evaluate_exhaust_with_known_lambda_q(
            P_SOL_MW=float(P_SOL_MW),
            R0_m=float(inp.R0_m),
            q95=float(q95),
            A_fw_m2=float(A_fw),
            Bpol_out_mid_T=float(out.get("Bpol_out_mid_T", float("nan"))),
            lambda_q_mm=float(lam_mm),
            flux_expansion=float(inp.flux_expansion),
            n_strike_points=int(getattr(inp, "n_strike_points", 2)),
            f_rad_div=float(f_div),
            P_SOL_over_R_max_MW_m=float(inp.P_SOL_over_R_max_MW_m),
            f_Lpar=float(getattr(inp, "f_Lpar", 1.0)),
            advanced_divertor_factor=float(getattr(inp, "advanced_divertor_factor", 1.0) or 1.0),
            f_wet=float(getattr(inp, "f_wet_divertor", 1.0) or 1.0),
        )
        q_mid = q_midplane_from_lambda_q(P_SOL_MW=float(P_SOL_MW), R0_m=float(inp.R0_m), lambda_q_mm=float(lam_mm))
        out.update({
            "f_rad_div": float(ex.f_rad_div),
            "flux_expansion": float(ex.flux_expansion),
            "n_strike_points": int(ex.n_strike_points),
            "f_wet_divertor": float(ex.f_wet),
            "Lpar_m": float(ex.Lpar_m),
            "q_div_MW_m2": float(ex.q_div_MW_m2),
            "q_div_max_MW_m2": float(inp.q_div_max_MW_m2),
            "div_regime": str(ex.div_regime),
            "f_rad_div_eff": float(ex.f_rad_div_eff),
            "P_div_MW": float(ex.P_div_MW),
            "q_midplane_MW_m2": float(q_mid),
            "q_midplane_W_m2": float(q_mid) * 1e6,
            "q_div_W_m2": float(ex.q_div_MW_m2) * 1e6,
            "q_div_max_W_m2": float(inp.q_div_max_MW_m2) * 1e6,

            # v375 exhaust authority transparency
            "lambda_q_mm_raw": float(ex.lambda_q_mm_raw),
            "flux_expansion_raw": float(ex.flux_expansion_raw),
            "n_strike_points_raw": int(ex.n_strike_points_raw),
            "f_wet_raw": float(ex.f_wet_raw),
            "q_div_unit_suspect": float(ex.q_div_unit_suspect),
            "exhaust_authority_contract_sha256": str(ex.exhaust_authority_contract_sha256),
        })

        # Optional SOL radiative control (diagnostic transparency)
        # If enabled and a q_div target is provided, compute the required SOL radiation fraction
        # assuming q_div scales approximately linearly with P_SOL reaching the divertor.
        try:
            q_target = float(getattr(inp, "q_div_target_MW_m2", float("nan")))
            if bool(getattr(inp, "include_sol_radiation_control", False)) and math.isfinite(q_target) and q_target > 0.0:
                q_no = float(ex.q_div_MW_m2)
                if math.isfinite(q_no) and q_no > 0.0:
                    f_required = 1.0 - (q_target / q_no)
                    f_required = min(max(f_required, 0.0), 0.95)
                    out["f_rad_SOL_required"] = float(f_required)
                    out["q_div_target_MW_m2"] = float(q_target)
                    out["q_div_with_SOL_rad_MW_m2"] = float(q_no * (1.0 - f_required))
                    out["SOL_rad_control_ok"] = 1.0 if (q_no * (1.0 - f_required)) <= q_target * 1.001 else 0.0
                else:
                    out["f_rad_SOL_required"] = float("nan")
                    out["q_div_target_MW_m2"] = float(q_target)
                    out["q_div_with_SOL_rad_MW_m2"] = float("nan")
                    out["SOL_rad_control_ok"] = float("nan")
            else:
                out["f_rad_SOL_required"] = float("nan")
                out["q_div_target_MW_m2"] = float("nan")
                out["q_div_with_SOL_rad_MW_m2"] = float("nan")
                out["SOL_rad_control_ok"] = float("nan")
        except Exception:
            out["f_rad_SOL_required"] = float("nan")
            out["q_div_target_MW_m2"] = float("nan")
            out["q_div_with_SOL_rad_MW_m2"] = float("nan")
            out["SOL_rad_control_ok"] = float("nan")
    else:
        out.update({
            "f_rad_div": float(f_div),
            "flux_expansion": float(inp.flux_expansion),
            "n_strike_points": int(getattr(inp, "n_strike_points", 2)),
            "Lpar_m": float(connection_length_m(q95, inp.R0_m, f_Lpar=float(getattr(inp, "f_Lpar", 1.0)))),
            "q_div_MW_m2": float("nan"),
            "q_div_max_MW_m2": float(inp.q_div_max_MW_m2),
            "div_regime": "unknown",
            "f_rad_div_eff": float("nan"),
            "P_div_MW": float("nan"),
            "q_midplane_MW_m2": float("nan"),
            "q_midplane_W_m2": float("nan"),
            "q_div_W_m2": float("nan"),
            "q_div_max_W_m2": float(inp.q_div_max_MW_m2) * 1e6,
        })

    out["P_SOL_MW"] = float(P_SOL_MW)

    # ---------------------------
    # v320.0 Impurity radiation partitions + detachment authority (deterministic)
    # ---------------------------
    try:
        from .impurities.detachment_authority import detachment_requirement_from_target

        _sp = str(getattr(inp, "impurity_contract_species", getattr(inp, "impurity_species", "") ) or "").strip()
        _sp = _sp if _sp in {"C","N","Ne","Ar","W"} else "Ne"
        _fz = float(getattr(inp, "impurity_contract_f_z", getattr(inp, "impurity_frac", 0.0)) or 0.0)

        _f_core = float(getattr(inp, "impurity_partition_core", 0.50) or 0.50)
        _f_edge = float(getattr(inp, "impurity_partition_edge", 0.20) or 0.20)
        _f_sol  = float(getattr(inp, "impurity_partition_sol",  0.20) or 0.20)
        _f_div  = float(getattr(inp, "impurity_partition_div",  0.10) or 0.10)

        rp = evaluate_impurity_radiation_partition(
            ImpurityContract(species=_sp, f_z=_fz, f_core=_f_core, f_edge=_f_edge, f_sol=_f_sol, f_divertor=_f_div),
            ne20=float(ne20),
            volume_m3=float(V),
            t_keV=float(Ti),
        )
        out["impurity_contract_species"] = str(_sp)
        out["impurity_contract_f_z"] = float(_fz)
        out["impurity_prad_total_MW"] = float(rp.prad_total_MW)
        out["impurity_prad_core_MW"] = float(rp.prad_core_MW)
        out["impurity_prad_edge_MW"] = float(rp.prad_edge_MW)
        out["impurity_prad_sol_MW"] = float(rp.prad_sol_MW)
        out["impurity_prad_div_MW"] = float(rp.prad_div_MW)
        out["impurity_zeff_proxy"] = float(rp.zeff_proxy)
        out["impurity_fuel_ion_fraction"] = float(rp.fuel_ion_fraction)
        out["impurity_validity"] = dict(rp.validity)

        # Detachment authority: invert q_div target -> required SOL+div radiation and implied f_z.
        q_target = float(getattr(inp, "q_div_target_MW_m2", float("nan")))
        out["detachment_fz_max"] = float(getattr(inp, "detachment_fz_max", float("nan")))

        # (v348.0) Edge–Core Coupled Exhaust Authority (defaults; always present)
        out["edge_core_coupling_active"] = 0.0
        out["edge_core_coupling_chi_core"] = float(getattr(inp, "edge_core_coupling_chi_core", 0.25) or 0.25)
        out["edge_core_coupling_contract_sha256"] = ""
        out["edge_core_coupling_delta_Prad_core_MW"] = float("nan")
        out["P_SOL_edge_core_MW"] = float("nan")
        out["f_rad_core_edge_core"] = float("nan")
        out["edge_core_coupling_validity"] = {}

        if bool(getattr(inp, "include_sol_radiation_control", False)) and math.isfinite(q_target) and q_target > 0.0:
            q_no = float(out.get("q_div_MW_m2", float("nan")))
            dr = detachment_requirement_from_target(
                species=_sp, ne20=float(ne20), volume_m3=float(V),
                P_SOL_MW=float(P_SOL_MW), q_div_no_rad_MW_m2=q_no, q_div_target_MW_m2=q_target,
                T_sol_keV=float(getattr(inp, "T_sol_keV", 0.08) or 0.08),
                f_V_sol_div=float(getattr(inp, "f_V_sol_div", 0.12) or 0.12),
            )
            out["detachment_f_sol_div_required"] = float(dr.f_sol_div_required)
            out["detachment_prad_sol_div_required_MW"] = float(dr.prad_sol_div_required_MW)
            out["detachment_f_z_required"] = float(dr.f_z_required)
            out["detachment_Lz_sol_Wm3"] = float(dr.lz_sol_Wm3)
            out["detachment_validity"] = dict(dr.validity)


            # (v348.0) Edge–Core Coupled Exhaust Authority
            # One-pass power-flow closure: increased core radiation reduces P_SOL, which relaxes divertor metrics.
            if bool(getattr(inp, "include_edge_core_coupled_exhaust", False)):
                try:
                    from src.contracts.edge_core_coupled_exhaust_contract import (
                        apply_edge_core_coupling,
                        CONTRACT_SHA256 as _EC_CONTRACT_SHA,
                    )

                    chi_core = float(getattr(inp, "edge_core_coupling_chi_core", 0.25) or 0.25)
                    chi_core = min(max(chi_core, 0.0), 1.0)

                    res = apply_edge_core_coupling(
                        Pin_MW=float(Pin_MW),
                        Prad_core_MW=float(Prad_core_MW),
                        Ploss_MW=float(Ploss_MW),
                        P_SOL_MW=float(P_SOL_MW),
                        Prad_sol_div_required_MW=float(dr.prad_sol_div_required_MW),
                        chi_core=float(chi_core),
                        f_rad_core_edge_core_max=float(getattr(inp, "f_rad_core_edge_core_max", float("nan"))),
                    )

                    out["edge_core_coupling_active"] = 1.0
                    out["edge_core_coupling_chi_core"] = float(chi_core)
                    out["edge_core_coupling_contract_sha256"] = str(_EC_CONTRACT_SHA)
                    out["edge_core_coupling_delta_Prad_core_MW"] = float(res.delta_Prad_core_MW)
                    out["P_SOL_edge_core_MW"] = float(res.P_SOL_eff_MW)
                    out["f_rad_core_edge_core"] = float(res.f_rad_core_edge_core)
                    out["edge_core_coupling_validity"] = dict(res.validity)

                    # backup base divertor/exhaust proxies then overwrite with coupled evaluation (no iteration)
                    out["q_div_MW_m2_base"] = float(out.get("q_div_MW_m2", float("nan")))
                    out["P_div_MW_base"] = float(out.get("P_div_MW", float("nan")))
                    out["div_regime_base"] = str(out.get("div_regime", ""))
                    out["f_rad_div_eff_base"] = float(out.get("f_rad_div_eff", float("nan")))

                    lam_mm = float(out.get("lambda_q_mm", float("nan")))
                    if math.isfinite(lam_mm):
                        ex_ec = evaluate_exhaust_with_known_lambda_q(
                            P_SOL_MW=float(res.P_SOL_eff_MW),
                            R0_m=float(inp.R0_m),
                            q95=float(q95),
                            A_fw_m2=float(A_fw),
                            Bpol_out_mid_T=float(out.get("Bpol_out_mid_T", float("nan"))),
                            lambda_q_mm=float(lam_mm),
                            flux_expansion=float(inp.flux_expansion),
                            n_strike_points=int(getattr(inp, "n_strike_points", 2)),
                            f_rad_div=float(min(max(float(getattr(inp, "f_rad_div", 0.0)), 0.0), 0.99)),
                            P_SOL_over_R_max_MW_m=float(inp.P_SOL_over_R_max_MW_m),
                            f_Lpar=float(getattr(inp, "f_Lpar", 1.0)),
                            advanced_divertor_factor=float(getattr(inp, "advanced_divertor_factor", 1.0) or 1.0),
                            f_wet=float(getattr(inp, "f_wet_divertor", 1.0) or 1.0),
                        )
                        q_mid_ec = q_midplane_from_lambda_q(
                            P_SOL_MW=float(res.P_SOL_eff_MW),
                            R0_m=float(inp.R0_m),
                            lambda_q_mm=float(lam_mm),
                        )
                        out.update({
                            "q_div_MW_m2": float(ex_ec.q_div_MW_m2),
                            "div_regime": str(ex_ec.div_regime),
                            "f_rad_div_eff": float(ex_ec.f_rad_div_eff),
                            "P_div_MW": float(ex_ec.P_div_MW),
                            "q_midplane_MW_m2": float(ex_ec.q_midplane_MW_m2),
                            "q_midplane_W_m2": float(ex_ec.q_midplane_MW_m2) * 1e6,
                            "q_div_W_m2": float(ex_ec.q_div_MW_m2) * 1e6,
                            "P_SOL_over_R_edge_core_MW_m": float(res.P_SOL_eff_MW) / max(float(inp.R0_m), 1e-9),
                            "q_midplane_edge_core_MW_m2": float(q_mid_ec),

                            # v375 exhaust authority transparency (edge-core coupled)
                            "f_wet_divertor": float(ex_ec.f_wet),
                            "lambda_q_mm_raw": float(ex_ec.lambda_q_mm_raw),
                            "flux_expansion_raw": float(ex_ec.flux_expansion_raw),
                            "n_strike_points_raw": int(ex_ec.n_strike_points_raw),
                            "f_wet_raw": float(ex_ec.f_wet_raw),
                            "q_div_unit_suspect": float(ex_ec.q_div_unit_suspect),
                            "exhaust_authority_contract_sha256": str(ex_ec.exhaust_authority_contract_sha256),
                        })
                except Exception:
                    out["edge_core_coupling_active"] = 0.0
                    out["edge_core_coupling_validity"] = {"status": "exception"}
        else:
            out["detachment_f_sol_div_required"] = float("nan")
            out["detachment_prad_sol_div_required_MW"] = float("nan")
            out["detachment_f_z_required"] = float("nan")
            out["detachment_Lz_sol_Wm3"] = float("nan")
            out["detachment_fz_max"] = float(getattr(inp, "detachment_fz_max", float("nan")))
            out["detachment_validity"] = {}

        # (v348.0) Edge–Core Coupled Exhaust Authority fallbacks
        out["edge_core_coupling_active"] = 0.0
        out["edge_core_coupling_chi_core"] = float(getattr(inp, "edge_core_coupling_chi_core", 0.25) or 0.25)
        out["edge_core_coupling_contract_sha256"] = ""
        out["edge_core_coupling_delta_Prad_core_MW"] = float("nan")
        out["P_SOL_edge_core_MW"] = float("nan")
        out["f_rad_core_edge_core"] = float("nan")
        out["edge_core_coupling_validity"] = {}
    except Exception:
        out["impurity_contract_species"] = ""
        out["impurity_contract_f_z"] = float("nan")
        out["impurity_prad_total_MW"] = float("nan")
        out["impurity_prad_core_MW"] = float("nan")
        out["impurity_prad_edge_MW"] = float("nan")
        out["impurity_prad_sol_MW"] = float("nan")
        out["impurity_prad_div_MW"] = float("nan")
        out["impurity_zeff_proxy"] = float("nan")
        out["impurity_fuel_ion_fraction"] = float("nan")
        out["impurity_validity"] = {}
        out["detachment_f_sol_div_required"] = float("nan")
        out["detachment_prad_sol_div_required_MW"] = float("nan")
        out["detachment_f_z_required"] = float("nan")
        out["detachment_Lz_sol_Wm3"] = float("nan")
        out["detachment_fz_max"] = float("nan")
        out["detachment_validity"] = {}

    

    # ---------------------------
    # v329.0 Exhaust & Radiation Regime Authority (deterministic)
    # ---------------------------
    try:
        from src.contracts.exhaust_radiation_regime_contract import classify_exhaust_regime, CONTRACT_SHA256 as _EXH_CONTRACT_SHA
        _q = float(out.get('q_div_MW_m2', float('nan')))
        _qmax = float(out.get('q_div_max_MW_m2', float('nan')))
        _fr = float(out.get('f_rad_div_eff', out.get('f_rad_div', float('nan'))))
        _thr = float(getattr(inp, 'P_SOL_over_R_max_MW_m', float('nan')))
        _freq = float(out.get('detachment_f_sol_div_required', float('nan')))
        cls = classify_exhaust_regime(
            P_SOL_MW=float(out.get('P_SOL_MW', float('nan'))),
            R0_m=float(getattr(inp, 'R0_m', float('nan'))),
            P_SOL_over_R_max_MW_m=float(_thr),
            q_div_MW_m2=float(_q),
            q_div_max_MW_m2=float(_qmax),
            f_rad_div_eff=float(_fr),
            f_sol_div_required=float(_freq),
        )
        out.update(cls.to_outputs_dict())
        out['exhaust_regime_validity'] = {'contract_sha256': str(_EXH_CONTRACT_SHA)}
    except Exception:
        out['exhaust_regime'] = 'unknown'
        out['exhaust_fragility_class'] = 'UNKNOWN'
        out['exhaust_min_margin_frac'] = float('nan')
        out['exhaust_detach_metric_MW_m'] = float('nan')
        out['exhaust_detach_thr_MW_m'] = float('nan')
        out['exhaust_detach_margin_MW_m'] = float('nan')
        out['exhaust_q_margin_MW_m2'] = float('nan')
        out['exhaust_radiation_dominated'] = float('nan')
        out['exhaust_contract_sha256'] = ''

    # ---------------------------
    # v296.0 Disruption risk tiering (screening)
    # ---------------------------
    try:
        _betaN_lim = float(getattr(inp, "betaN_max", float("nan")))
        if not (_betaN_lim == _betaN_lim) or _betaN_lim <= 0:
            _betaN_lim = 3.5
        _beta_margin = float(betaN) / max(_betaN_lim, 1e-9)
        _qmin = float(out.get("profile_qmin_proxy", float("nan")))
        if not (_qmin == _qmin):
            _qmin = max(0.7, 0.6*float(q95))
        _Prad = float(out.get("Prad_MW", out.get("Prad_core_MW", 0.0)))
        _Pin = float(out.get("P_in_MW", out.get("Pin_MW", 1.0)))
        _prad_frac = _Prad / max(_Pin, 1e-9)
        dr = evaluate_disruption_risk(f_greenwald=float(inp.fG), beta_n_margin=_beta_margin, qmin=_qmin, prad_frac=_prad_frac)
        out["disruption_risk_tier"] = str(dr.tier)
        out["disruption_dominant_driver"] = str(dr.dominant_driver)
        out["disruption_risk_index"] = float(dr.risk_index)
        out["disruption_risk_components"] = dict(dr.components)
    except Exception:
        out["disruption_risk_tier"] = "UNKNOWN"
        out["disruption_dominant_driver"] = "unknown"
        out["disruption_risk_index"] = float("nan")
        out["disruption_risk_components"] = {}
    out["P_SOL_over_R_MW_m"] = float(P_SOL_over_R_MW_m)
    out["q_midplane_max_MW_m2"] = float(getattr(inp, "q_midplane_max_MW_m2", float("nan")))
    out["P_SOL_over_R_limit_MW_m"] = float(getattr(inp, "P_SOL_over_R_limit_MW_m", float("nan")))

    # =========================================================================
    # Added: (4) Neutronics lifetime/TBR feasibility
    # =========================================================================
    TBR = TBR_proxy(
        t_blanket_m=inp.t_blanket_m,
        coverage=inp.blanket_coverage,
        lambda_m=inp.TBR_lambda_m,
        multiplier=inp.TBR_multiplier,
    )
    out["blanket_coverage"] = inp.blanket_coverage
    out["TBR"] = TBR
    out["TBR_min"] = inp.TBR_min

    fluence_per_fpy = HTS_fluence_per_fpy_n_m2(
        S_n_W_m2=S_n_W_m2,
        attenuation_len_m=inp.atten_len_m,
        shield_m=inp.t_shield_m + inp.t_blanket_m,  # effective shielding to TF (very coarse)
        f_geom=inp.f_geom_to_tf,
    )
    years_to_limit = (inp.hts_fluence_limit_n_m2 / max(fluence_per_fpy, 1e-30)) if fluence_per_fpy > 0 else float("inf")
    out["hts_fluence_per_fpy_n_m2"] = fluence_per_fpy
    out["hts_fluence_limit_n_m2"] = inp.hts_fluence_limit_n_m2
    out["hts_lifetime_yr"] = years_to_limit
    # Additional neutronics proxies (PROCESS-like bookkeeping)
    neut = neutronics_proxies(
        Pfus_MW=max(Pfus_DT_adj_MW + Pfus_DD_MW, 0.0),
        A_fw_m2=float(A_fw),
        hts_fluence_limit_n_m2=inp.hts_fluence_limit_n_m2,
        atten_len_m=inp.atten_len_m,
        t_shield_m=inp.t_shield_m + inp.t_blanket_m,
        f_geom_to_tf=inp.f_geom_to_tf,
    )
    out["neutron_wall_load_MW_m2"] = neut.neutron_wall_load_MW_m2
    out["fluence_n_m2_per_fpy"] = neut.fluence_n_m2_per_fpy

    # -------------------------------------------------------------------------
    # Neutronics/materials authority hardening (stack attenuation + nuclear loads)
    # -------------------------------------------------------------------------
    try:
        # v309.0 neutronics/materials authority (proxy): multi-group attenuation,
        # nuclear heating partitioning, DPA/He/lifetime, temperature/stress windows,
        # and improved TBR proxy.
        _nm = compute_neutronics_materials_bundle(out, inp)
        out.update(_nm)

        # Back-compat key: some panels / docs used neutron_attenuation_factor.
        # Map it to the fast attenuation factor.
        out["neutron_attenuation_factor"] = float(out.get("neutron_attenuation_fast", float("nan")))

        # Keep the earlier stack-fluence visibility feature using the updated attenuation.
        nwl = float(out.get("neutron_wall_load_MW_m2", float("nan")))
        att_fast = float(out.get("neutron_attenuation_fast", float("nan")))
        nflux_fw = max(nwl if nwl == nwl else 0.0, 0.0) * 3.5e19  # n/m^2/s (very rough proxy)
        nflux_tf = nflux_fw * (att_fast if att_fast == att_fast else 0.0) * max(float(getattr(inp, "f_geom_to_tf", 0.0)), 0.0)
        fpy_s = 365.25 * 24.0 * 3600.0
        fluence_tf_stack = nflux_tf * fpy_s
        out["hts_fluence_per_fpy_stack_n_m2"] = float(fluence_tf_stack)
        out["hts_lifetime_stack_yr"] = float(getattr(inp, "hts_fluence_limit_n_m2", 0.0)) / max(fluence_tf_stack, 1e-30)
    except Exception:
        # keep conservative behavior; the canonical proxy remains available above
        out.setdefault("neutron_attenuation_factor", float("nan"))
        out.setdefault("P_nuc_total_MW", float("nan"))


    # =========================================================================
    # Added: Neutronics & Activation Authority 3.0 (v390.0.0) — optional, algebraic
    # =========================================================================
    try:
        na390 = compute_neutronics_activation_bundle_v390(out, inp)
        if isinstance(na390, dict):
            out.update(na390)
    except Exception:
        pass

    # Optional screening cap (NaN disables)
    out["neutron_wall_load_max_MW_m2"] = float(getattr(inp, "neutron_wall_load_max_MW_m2", float("nan")))

    out["lifetime_min_yr"] = inp.lifetime_min_yr
    out["neutron_wall_load_max_MW_m2"] = getattr(inp, "neutron_wall_load_max_MW_m2", float("nan"))

    # =========================================================================
    # Added: (5) Plant power / recirculating power closure -> net electric
    # =========================================================================
    Pfus_total_MW = max(Pfus_DT_adj_MW + Pfus_DD_MW, 0.0)

    # Use current-drive launch power from earlier closure if available.
    # =========================================================================
    # Added: Current-drive / non-inductive fraction closure (transparent proxy)
    # =========================================================================
    # If enabled, compute a required launched CD power to meet a target
    # non-inductive fraction: f_NI = f_bs + I_cd/Ip.
    if bool(getattr(inp, "include_current_drive", False)):
        try:
            f_bs = float(out.get("f_bs_proxy", 0.0))
            f_target = float(getattr(inp, "f_noninductive_target", 1.0))
            cd = cd_gamma_and_efficiency(out, inp)
            gamma = float(cd.gamma_A_per_W)  # A/W
            out["cd_model_used"] = cd.model
            out["cd_actuator_used"] = cd.actuator
            out["gamma_cd_A_per_W_used"] = float(cd.gamma_A_per_W)
            out["eta_cd_wallplug_used"] = float(cd.eta_wallplug)
            Pcd_max = float(getattr(inp, "Pcd_max_MW", 200.0))
            out["Pcd_max_MW"] = float(Pcd_max)
            Ip_A = max(float(inp.Ip_MA) * 1e6, 1e-6)
            Icd_req_A = max((f_target - f_bs) * Ip_A, 0.0)
            Pcd_req_MW = (Icd_req_A / max(gamma, 1e-12)) / 1e6
            out["P_cd_required_MW"] = float(Pcd_req_MW)
            Pcd_launch = min(max(Pcd_req_MW, 0.0), max(Pcd_max, 0.0))
            out["cd_power_saturated"] = 1.0 if (Pcd_req_MW > Pcd_max + 1e-9) else 0.0
            Icd_A = Pcd_launch * 1e6 * max(gamma, 0.0)
            f_NI = f_bs + Icd_A / Ip_A
            out["P_cd_launch_MW"] = float(Pcd_launch)

            # Derived channel feasibility proxies (deterministic)
            try:
                tech = str(out.get("cd_actuator_used", "ECCD")).strip().upper()
            except Exception:
                tech = "ECCD"

            # ECCD launcher power density proxy
            if tech == "ECCD":
                area = float(out.get("eccd_launcher_area_m2", float('nan')))
                if area == area and area > 0.0:
                    out["eccd_launcher_power_density_MW_m2"] = float(Pcd_launch) / area
                else:
                    out["eccd_launcher_power_density_MW_m2"] = float('nan')
            else:
                out["eccd_launcher_power_density_MW_m2"] = float('nan')

            # NBI shine-through proxy (screening): decreases with density and path length; increases with beam energy.
            if tech == "NBI":
                try:
                    ne20 = float(out.get("ne_bar_1e20_m3", out.get("nbar20", out.get("ne20", float('nan')))))
                    R0 = float(out.get("R0_m", getattr(inp, "R0_m", 6.2)))
                    E = float(out.get("nbi_beam_energy_keV", float(getattr(inp, "nbi_beam_energy_keV", 500.0))))
                    ne20 = max(0.05, min(5.0, ne20))
                    R0 = max(0.5, min(20.0, R0))
                    E = max(50.0, min(5000.0, E))
                    # optical depth proxy
                    tau = 0.8 * ne20 * (R0 / 6.0)
                    st_frac = (E / 500.0) ** 0.25 * (2.718281828459045 ** (-tau))
                    out["nbi_shinethrough_frac"] = float(max(0.0, min(0.5, st_frac)))
                except Exception:
                    out["nbi_shinethrough_frac"] = float('nan')
            else:
                out["nbi_shinethrough_frac"] = float('nan')
            out["I_cd_MA"] = float(Icd_A / 1e6)
            out["f_noninductive"] = float(f_NI)
            out["f_noninductive_target"] = float(f_target)

            # v357.0 CD library diagnostics (pure algebraic bookkeeping)
            out["include_cd_library_v357"] = bool(getattr(inp, "include_cd_library_v357", False))
            try:
                tech = str(cd.actuator).strip().upper()
            except Exception:
                tech = "ECCD"

            # User-declared channel knobs (echoed for audit)
            if tech == "LHCD":
                out["lhcd_n_parallel"] = float(getattr(inp, "lhcd_n_parallel", float('nan')))
            else:
                out["lhcd_n_parallel"] = float('nan')

            if tech == "ECCD":
                area = float(getattr(inp, "eccd_launcher_area_m2", float('nan')))
                out["eccd_launcher_area_m2"] = area
                out["eccd_launch_factor"] = float(getattr(inp, "eccd_launch_factor", float('nan')))
            else:
                out["eccd_launcher_area_m2"] = float('nan')
                out["eccd_launch_factor"] = float('nan')

            if tech == "NBI":
                out["nbi_beam_energy_keV"] = float(getattr(inp, "nbi_beam_energy_keV", float('nan')))
            else:
                out["nbi_beam_energy_keV"] = float('nan')

            # Optional hard caps (NaN disables) surfaced to the constraints ledger
            out["lhcd_n_parallel_min"] = float(getattr(inp, "lhcd_n_parallel_min", float('nan')))
            out["lhcd_n_parallel_max"] = float(getattr(inp, "lhcd_n_parallel_max", float('nan')))
            out["eccd_launcher_power_density_max_MW_m2"] = float(getattr(inp, "eccd_launcher_power_density_max_MW_m2", float('nan')))
            out["nbi_shinethrough_frac_max"] = float(getattr(inp, "nbi_shinethrough_frac_max", float('nan')))
        except Exception:
            out["P_cd_launch_MW"] = float(out.get("P_cd_launch_MW", 0.0))
    else:
        out["P_cd_launch_MW"] = float(out.get("P_cd_launch_MW", 0.0))

    # q-profile plausibility proxy (very lightweight): set q0 as a bounded fraction of q95.
    if "q95_proxy" in out:
        try:
            q95 = float(out["q95_proxy"])
            out["q0_proxy"] = float(max(0.2, 0.5 * q95))
        except Exception:
            pass

    # Carry q-profile bounds into outputs so the constraint system can read them.
    out["q95_min"] = float(getattr(inp, "q95_min", float("nan")))
    out["q95_max"] = float(getattr(inp, "q95_max", float("nan")))
    out["q0_min"] = float(getattr(inp, "q0_min", float("nan")))
    Pcd_launch_MW = float(out.get("P_cd_launch_MW", 0.0)) if isinstance(out, dict) else 0.0

    
    # (5) Plant power / recirculating power closure -> net electric
    # Compute coolant-side pumping power and a simple thermal-cycle efficiency proxy.
    try:
        P_pumps_model_MW = coolant_pumping_power_MW(
            float(Pfus_total_MW) * float(getattr(inp, "blanket_energy_mult", 1.0)),
            getattr(inp, "coolant", "Helium"),
        )
    except Exception:
        P_pumps_model_MW = 0.0

    P_pumps_in_MW = float(getattr(inp, "P_pumps_MW", float("nan")))
    P_pumps_use_MW = P_pumps_model_MW if not (P_pumps_in_MW == P_pumps_in_MW) else P_pumps_in_MW

    eta_elec_model = str(getattr(inp, "eta_elec_model", "auto")).strip().lower()
    if eta_elec_model == "auto":
        eta_elec_use = electric_efficiency(getattr(inp, "coolant", "Helium"), float(getattr(inp, "T_outlet_K", 900.0)))
    else:
        eta_elec_use = float(getattr(inp, "eta_elec", 0.40))

    plant = plant_power_closure(
        Pfus_MW=Pfus_total_MW,
        Paux_MW=inp.Paux_MW,
        Pcd_launch_MW=Pcd_launch_MW,
        eta_elec=eta_elec_use,
        blanket_energy_mult=getattr(inp, "blanket_energy_mult", 1.0),
        eta_aux_wallplug=getattr(inp, "eta_aux_wallplug", 0.40),
        eta_cd_wallplug=float(out.get("eta_cd_wallplug_used", getattr(inp, "eta_cd_wallplug", 0.33))),
        P_balance_of_plant_MW=getattr(inp, "P_balance_of_plant_MW", 20.0),
        P_pumps_MW=P_pumps_use_MW,
        P_cryo_20K_MW=getattr(inp, "P_cryo_20K_MW", 0.0),
        cryo_COP=getattr(inp, "cryo_COP", 0.02),
        P_tf_ohmic_MW=float(out.get("P_tf_ohmic_MW", 0.0)) if out.get("P_tf_ohmic_MW", 0.0) == out.get("P_tf_ohmic_MW", 0.0) else 0.0,
        eta_tf_wallplug=float(getattr(inp, "eta_tf_wallplug", 0.95)),
    )

    out["Pfus_total_MW"] = plant.Pfus_MW
    out["Pth_total_MW"] = plant.Pth_MW
    out["P_e_gross_MW"] = plant.Pe_gross_MW
    out["P_recirc_MW"] = plant.Precirc_MW
    out["P_e_net_MW"] = plant.Pe_net_MW
    out["Qe"] = plant.Qe

    # TF coil thermal margin proxy (nuclear + AC losses vs cooling capacity)
    try:
        coil_th = tf_coil_heat_proxy(
            float(out.get("neutron_wall_load_MW_m2", 0.0)),
            float(out.get("Bpeak_TF_T", float("nan"))),
            k_nuclear_MW_per_MW_m2=float(getattr(inp, "coil_nuclear_heat_coeff_MW_per_MW_m2", 0.2)),
            cooling_capacity_MW=float(getattr(inp, "coil_cooling_capacity_MW", 5.0)),
        )
        out["coil_heat_MW"] = coil_th.P_heat_MW
        out["coil_heat_nuclear_MW"] = coil_th.P_nuclear_MW
        out["coil_heat_ac_MW"] = coil_th.P_ac_MW
        out["coil_cooling_capacity_MW"] = coil_th.cooling_capacity_MW
        out["coil_thermal_margin"] = coil_th.margin
        out["coil_heat_max_MW"] = float(getattr(inp, "coil_heat_max_MW", float("nan")))
    except Exception:
        pass

    # -----------------------------------------------------------------
    # (v367.0) Materials lifetime closure (post-processing-only)
    # -----------------------------------------------------------------
    try:
        ml = compute_materials_lifetime_closure_v367(out, inp)
        if isinstance(ml, dict):
            out.update(ml)
            # Prefer the closure-derived replacement intervals when available.
            # This is deterministic post-processing and does not alter neutronics/materials physics.
            if "fw_replace_interval_y_v367" in ml:
                try:
                    out["fw_replace_interval_y"] = float(ml["fw_replace_interval_y_v367"])
                except Exception:
                    pass
            if "blanket_replace_interval_y_v367" in ml:
                try:
                    out["blanket_replace_interval_y"] = float(ml["blanket_replace_interval_y_v367"])
                except Exception:
                    pass
    except Exception:
        pass

    # -----------------------------------------------------------------
    # (v384.0.0) Materials & lifetime tightening (governance overlay; OFF by default)
    # -----------------------------------------------------------------
    try:
        # Record policy inputs for downstream constraint evaluation and evidence packs.
        out["include_materials_lifetime_v384"] = bool(getattr(inp, "include_materials_lifetime_v384", False))
        out["fw_lifetime_min_yr_v384"] = float(getattr(inp, "fw_lifetime_min_yr_v384", float("nan")))
        out["blanket_lifetime_min_yr_v384"] = float(getattr(inp, "blanket_lifetime_min_yr_v384", float("nan")))
        out["divertor_lifetime_min_yr_v384"] = float(getattr(inp, "divertor_lifetime_min_yr_v384", float("nan")))
        out["magnet_lifetime_min_yr_v384"] = float(getattr(inp, "magnet_lifetime_min_yr_v384", float("nan")))
        out["replacement_cost_max_MUSD_per_y_v384"] = float(getattr(inp, "replacement_cost_max_MUSD_per_y_v384", float("nan")))
        out["capacity_factor_min_v384"] = float(getattr(inp, "capacity_factor_min_v384", float("nan")))

        ml384 = compute_materials_lifetime_tightening_v384(out, inp)
        if isinstance(ml384, dict):
            out.update(ml384)
    except Exception:
        pass

    # CS flux swing proxy (for pulsed feasibility); recorded even in steady-state for transparency.
    try:
        cs = cs_flux_swing_proxy(
            R0_m=float(inp.R0_m),
            a_m=float(inp.a_m),
            Ip_MA=float(inp.Ip_MA),
            t_burn_s=float(getattr(inp, "t_burn_s", 7200.0)),
            cs_Bmax_T=float(getattr(inp, "cs_Bmax_T", 12.0)),
            cs_fill_factor=float(getattr(inp, "cs_fill_factor", 0.6)),
            cs_radius_factor=float(getattr(inp, "cs_radius_factor", 0.30)),
            cs_flux_mult=float(getattr(inp, "cs_flux_mult", 1.0)),
            pulse_ramp_s=float(getattr(inp, "pulse_ramp_s", 300.0)),
        )
        out["cs_Lp_H"] = cs.Lp_H
        out["cs_flux_required_Wb"] = cs.flux_required_Wb
        out["cs_flux_available_Wb"] = cs.flux_available_Wb
        out["cs_V_loop_ramp_V"] = cs.V_loop_ramp_V
        out["cs_V_loop_max_V"] = float(getattr(inp, "cs_V_loop_max_V", float("nan")))
        out["cs_flux_margin"] = cs.margin
        out["cs_flux_margin_min"] = float(getattr(inp, "cs_flux_margin_min", float("nan")))
    except Exception:
        pass

    # =========================================================================
    # Added: Structural Stress Authority (v389.0.0) — optional, algebraic
    # =========================================================================
    try:
        ss389 = compute_structural_stress_bundle_v389(out, inp)
        if isinstance(ss389, dict):
            out.update(ss389)
    except Exception:
        pass

    out["P_net_min_MW"] = getattr(inp, "P_net_min_MW", float("nan"))

    # =========================================================================
    # Added: Thermal-hydraulics / pumping power and radial-stack neutronics bookkeeping
    # =========================================================================
    try:
        out["P_pump_MW"] = coolant_pumping_power_MW(float(out.get("Pth_total_MW", 0.0)), getattr(inp, "coolant", "Helium"))
        out["coolant_dT_K"] = coolant_dT_K(float(out.get("Pth_total_MW", 0.0)), float(getattr(inp, "coolant_flow_m3_s", 0.05)), getattr(inp, "coolant", "Helium"))
    except Exception:
        out["P_pump_MW"] = float("nan")
        out["coolant_dT_K"] = float("nan")

    try:
        _stack = build_default_stack(inp.__dict__)
        out["neutron_attenuation_factor"] = neutron_attenuation_factor(_stack)
        out.update(nuclear_heating_MW(float(out.get("Pfus_total_MW", 0.0)), _stack))
    except Exception:
        out["neutron_attenuation_factor"] = float("nan")
    # =========================================================================
    # Added: (6) Pulsed operation / flux consumption proxy
    # =========================================================================
    # When steady_state is False, estimate a flat-top duration from available
    # transformer flux swing and required loop voltage (Spitzer resistive proxy).
    out["t_flat_s"] = float("nan")
    out["pulse_min_s"] = float(getattr(inp, "pulse_min_s", float("nan")))
    out["V_loop_req_V"] = float("nan")
    out["V_loop_max_V"] = float(getattr(inp, "V_loop_max_V", float("nan")))
    out["flux_swing_Wb"] = float(getattr(inp, "flux_swing_Wb", float("nan")))
    out["flux_avail_Wb"] = float("nan")
    out["V_loop_over_max"] = float("nan")
    if not inp.steady_state:
        try:
            Ip_A = inp.Ip_MA * 1e6
            Te_eV = max(Te * 1e3, 1.0)
            lnL = 17.0
            Ze = max(float(out.get("Zeff", inp.zeff)), 1.0)
            # Spitzer resistivity [ohm-m] (very approximate)
            eta = 5.2e-5 * Ze * lnL / (Te_eV ** 1.5)
            Lp = 2.0 * math.pi * inp.R0_m
            A_cs = math.pi * inp.a_m**2 * inp.kappa
            R_plasma = eta * Lp / max(A_cs, 1e-12)
            V_req = Ip_A * R_plasma

            li = float(getattr(inp, "li_internal", 0.8))
            L_H = 4e-7 * math.pi * inp.R0_m * (math.log(max(8.0 * inp.R0_m / max(inp.a_m, 1e-6), 1.0)) - 2.0 + 0.5 * li)
            psi_L = L_H * Ip_A
            flux_avail = max(float(getattr(inp, "flux_swing_Wb", 0.0)) - psi_L, 0.0)

            out["V_loop_req_V"] = V_req
            out["flux_avail_Wb"] = flux_avail

            Vmax = max(float(getattr(inp, "V_loop_max_V", 0.0)), 1e-6)
            out["V_loop_over_max"] = V_req / max(Vmax, 1e-12)

            V_used = max(V_req, 1e-6)
            out["t_flat_s"] = flux_avail / V_used
            # Cycle count proxy (fatigue): assume repeating pulse+ dwell at given availability.
            t_dwell = max(float(getattr(inp, "t_dwell_s", 600.0)), 0.0)
            avail = float(getattr(inp, "availability", 0.70))
            t_cycle = max(out["t_flat_s"] + t_dwell, 1e-6)
            out["t_dwell_s"] = t_dwell
            out["cycles_per_year"] = (max(min(avail, 1.0), 0.0) * 8760.0 * 3600.0) / t_cycle
            out["cycles_max"] = float(getattr(inp, "cycles_max", float("nan")))
        except Exception:
            pass

    # Duty factor + average net power for pulsed studies (slow-time proxy)
    try:
        t_burn = float(out.get("t_flat_s", float('nan')))
        if not (t_burn == t_burn) or t_burn <= 0:  # NaN or non-positive
            t_burn = float(getattr(inp, "t_burn_s", 7200.0))
        t_dwell = float(getattr(inp, "t_dwell_s", 600.0))
        ps = pulsed_summary(t_burn, t_dwell)
        out["t_burn_s"] = ps["t_burn_s"]
        out["duty_factor"] = ps["duty_factor"]
        out["cycles_per_year"] = ps["cycles_per_year"]
        out["P_e_net_avg_MW"] = float(out.get("P_e_net_MW", float('nan'))) * ps["duty_factor"]
    except Exception:
        out["t_burn_s"] = float("nan")
        out["duty_factor"] = float("nan")
        out["P_e_net_avg_MW"] = float("nan")

    # ---------------------------------------------------------------------
    # Pulse scenario contract (quasi-static override for bookkeeping only)
    # ---------------------------------------------------------------------
    # This does NOT re-solve plasma physics. It only overrides the pulsed timing
    # proxies used for PF-average power, cycle counts, and governance outputs.
    try:
        from control.pulse_scenarios import apply_pulse_scenario  # type: ignore
        sc_inp = apply_pulse_scenario(dict(getattr(inp, "__dict__", {})))
        out["pulse_scenario_used"] = str(sc_inp.get("pulse_scenario_used", "as_input"))
        if out["pulse_scenario_used"] != "as_input":
            out["t_burn_s"] = float(sc_inp.get("t_burn_s", out.get("t_burn_s", float('nan'))))
            out["t_dwell_s"] = float(sc_inp.get("t_dwell_s", out.get("t_dwell_s", float('nan'))))
            ps2 = pulsed_summary(out["t_burn_s"], out["t_dwell_s"])
            out["duty_factor"] = ps2["duty_factor"]
            out["cycles_per_year"] = ps2["cycles_per_year"]
            out["P_e_net_avg_MW"] = float(out.get("P_e_net_MW", float('nan'))) * ps2["duty_factor"]
    except Exception:
        out.setdefault("pulse_scenario_used", "as_input")


    # =========================================================================

    # =========================================================================
    # Added: Risk / PF / Materials / Availability / Tritium (reactor-grade proxies)
    # =========================================================================

    # First-wall dpa/year proxy from neutron wall load (transparent scaling)
    try:
        nwl = float(out.get("neutron_wall_load_MW_m2", float("nan")))
        # Heuristic order-of-magnitude proxy: ~5 dpa/year per MW/m^2.
        out["fw_dpa_per_year"] = 5.0 * max(nwl if nwl == nwl else 0.0, 0.0)
        out["fw_dpa_max_per_year"] = float(getattr(inp, "fw_dpa_max_per_year", float("nan")))
    except Exception:
        out["fw_dpa_per_year"] = float("nan")

    # Divertor erosion proxy (mm/year) from peak heat flux and duty factor
    try:
        qd = float(out.get("q_div_peak_MW_m2", out.get("q_div_MW_m2", float("nan"))))
        duty = float(out.get("duty_factor", float("nan")))
        if not (duty == duty):
            duty = float(getattr(inp, "availability", 0.70))
        # Heuristic: erosion scales ~ q^2 and duty factor
        out["div_erosion_mm_per_year"] = 0.2 * max(qd if qd == qd else 0.0, 0.0) ** 2 * max(min(duty, 1.0), 0.0)
        out["div_erosion_max_mm_per_y"] = float(getattr(inp, "div_erosion_max_mm_per_y", float("nan")))
    except Exception:
        out["div_erosion_mm_per_year"] = float("nan")

    # PF system proxy beyond CS flux swing (screening)
    try:
        ramp_time_s = float(getattr(inp, "pulse_ramp_s", 300.0))
        ramp_rate_MA_s = float(inp.Ip_MA) / max(ramp_time_s, 1e-6)
        pf = pf_system_proxy(float(inp.R0_m), float(inp.a_m), float(inp.kappa), float(inp.Ip_MA), ramp_rate_MA_s)
        out["pf_I_pf_MA"] = pf.I_pf_MA
        out["pf_stress_proxy"] = pf.stress_proxy
        out["pf_current_max_MA"] = float(getattr(inp, "pf_current_max_MA", float("nan")))
        out["pf_stress_max"] = float(getattr(inp, "pf_stress_max", float("nan")))
    except Exception:
        pass

    # Envelope-based control contracts (v226.0) — deterministic, no physics mutation
    try:
        # v335.0: control authority contract provides deterministic defaults for optional caps
        _ctl_contract = None
        _ctl_caps = {}
        try:
            _ctl_contract = load_control_stability_contract(repo_root)
            _ctl_caps = {}
            dflt = contract_defaults(_ctl_contract)
            for sub in ("vs","pf","cs","rwm"):
                v = dflt.get(sub) if isinstance(dflt, dict) else None
                if isinstance(v, dict):
                    _ctl_caps.update({k: float(vv) for k, vv in v.items() if isinstance(k, str)})
        except Exception:
            _ctl_contract = None
            _ctl_caps = {}
        cc = compute_control_contracts(out, inp, caps_override=_ctl_caps)

        out["gamma_VS_s_inv"] = cc.gamma_VS_s_inv
        out["tau_VS_s"] = cc.tau_VS_s
        out["vs_bandwidth_req_Hz"] = cc.vs_bandwidth_req_Hz
        out["vs_control_power_req_MW"] = cc.vs_control_power_req_MW
        out["vs_control_ok"] = cc.vs_control_ok
        out["vs_bandwidth_max_Hz"] = float(getattr(inp, "vs_bandwidth_max_Hz", float("nan")))
        out["vs_control_power_max_MW"] = float(getattr(inp, "vs_control_power_max_MW", float("nan")))

        out["pf_I_peak_MA"] = cc.pf_I_peak_MA
        out["pf_dIdt_peak_MA_s"] = cc.pf_dIdt_peak_MA_s
        out["pf_V_peak_V"] = cc.pf_V_peak_V
        out["pf_P_peak_MW"] = cc.pf_P_peak_MW
        out["pf_E_pulse_MJ"] = cc.pf_E_pulse_MJ
        out["pf_waveform_decimated"] = cc.pf_waveform_decimated
        out["pf_envelope_ok"] = cc.pf_envelope_ok

        out["pf_I_peak_max_MA"] = float(getattr(inp, "pf_I_peak_max_MA", float("nan")))
        out["pf_V_peak_max_V"] = float(getattr(inp, "pf_V_peak_max_V", float("nan")))
        out["pf_P_peak_max_MW"] = float(getattr(inp, "pf_P_peak_max_MW", float("nan")))
        out["pf_dIdt_max_MA_s"] = float(getattr(inp, "pf_dIdt_max_MA_s", float("nan")))
        out["pf_E_pulse_max_MJ"] = float(getattr(inp, "pf_E_pulse_max_MJ", float("nan")))

        out["f_rad_SOL_max"] = float(getattr(inp, "f_rad_SOL_max", float("nan")))
        out["sol_control_ok"] = cc.sol_control_ok
        out["control_contracts_authority"] = cc.control_contracts_authority
        out["control_contract_sha256"] = (_ctl_contract.sha256 if _ctl_contract is not None else "")
        out["control_budget_ledger"] = cc.control_budget_ledger
        out["control_contract_caps"] = cc.contract_caps
        out["control_contract_margins"] = cc.contract_margins
        out["vs_control_horizon_s"] = float(getattr(inp, "vs_control_horizon_s", 1.0))

        # RWM screening (v229.0)
        out["rwm_regime"] = cc.rwm_regime
        out["rwm_betaN_no_wall"] = cc.rwm_betaN_no_wall
        out["rwm_betaN_ideal_wall"] = cc.rwm_betaN_ideal_wall
        out["rwm_chi"] = cc.rwm_chi
        out["rwm_tau_w_s"] = cc.rwm_tau_w_s
        out["rwm_gamma_s_inv"] = cc.rwm_gamma_s_inv
        out["rwm_bandwidth_req_Hz"] = cc.rwm_bandwidth_req_Hz
        out["rwm_control_power_req_MW"] = cc.rwm_control_power_req_MW
        out["rwm_control_ok"] = cc.rwm_control_ok
        out["rwm_bandwidth_max_Hz"] = float(getattr(inp, "rwm_bandwidth_max_Hz", float(getattr(inp, "vs_bandwidth_max_Hz", float("nan")))))
        out["rwm_control_power_max_MW"] = float(getattr(inp, "rwm_control_power_max_MW", float(getattr(inp, "vs_control_power_max_MW", float("nan")))))
        out["rwm_tau_w_input_s"] = float(getattr(inp, "rwm_tau_w_s", float("nan")))
    except Exception:
        pass

    # Operational risk proxies (MHD/disruption, vertical stability margin)
    try:
        risk = compute_mhd_and_vs_risk(out, inp)
        out["mhd_risk_proxy"] = risk.mhd_risk_proxy
        out["vs_margin"] = risk.vs_margin
        out["mhd_risk_max"] = float(getattr(inp, "mhd_risk_max", float("nan")))
        out["vs_margin_min"] = float(getattr(inp, "vs_margin_min", float("nan")))
    except Exception:
        pass

    # ---------------------------------------------------------------------
    # v319.0 Stability & control risk tiering (screening)
    # ---------------------------------------------------------------------
    try:
        sr = evaluate_stability_risk(out)
        out["stability_risk_tier"] = str(sr.tier)
        out["stability_dominant_driver"] = str(sr.dominant_driver)
        out["stability_risk_index"] = float(sr.risk_index)
        out["stability_risk_components"] = dict(sr.components)
    except Exception:
        out["stability_risk_tier"] = "UNKNOWN"
        out["stability_dominant_driver"] = "unknown"
        out["stability_risk_index"] = float("nan")
        out["stability_risk_components"] = {}

    # v319.0 Unified operational tier (disruption + stability)
    try:
        _rank = {"LOW": 0, "MED": 1, "HIGH": 2, "UNKNOWN": -1}
        dt = str(out.get("disruption_risk_tier", "UNKNOWN") or "UNKNOWN")
        stt = str(out.get("stability_risk_tier", "UNKNOWN") or "UNKNOWN")
        r = max(_rank.get(dt, -1), _rank.get(stt, -1))
        inv = {0: "LOW", 1: "MED", 2: "HIGH"}
        out["operational_risk_tier"] = inv.get(r, "UNKNOWN")

        # Dominant driver: choose from the higher-ranked tier; break ties by larger index.
        di = float(out.get("disruption_risk_index", float("nan")))
        si = float(out.get("stability_risk_index", float("nan")))
        dd = str(out.get("disruption_dominant_driver", ""))
        sd = str(out.get("stability_dominant_driver", ""))
        if _rank.get(dt, -1) > _rank.get(stt, -1):
            out["operational_dominant_driver"] = dd
        elif _rank.get(stt, -1) > _rank.get(dt, -1):
            out["operational_dominant_driver"] = sd
        else:
            # same tier (or both unknown): prefer whichever index is larger (if both finite)
            if (si == si) and (di == di):
                out["operational_dominant_driver"] = sd if si >= di else dd
            else:
                out["operational_dominant_driver"] = sd or dd
    except Exception:
        out["operational_risk_tier"] = "UNKNOWN"
        out["operational_dominant_driver"] = ""

    # Tritium fuel-cycle closure proxies
    try:
        tri = compute_tritium_fuel_cycle(out, inp)
        out["T_burn_g_per_day"] = tri.T_burn_g_per_day
        out["T_inventory_proxy_g"] = tri.T_inventory_proxy_g
        out["T_processing_proxy_g_per_day"] = tri.T_processing_proxy_g_per_day
        out["TBR_proxy"] = tri.TBR_proxy
        out["TBR_min"] = float(getattr(inp, "TBR_min", float("nan")))
    except Exception:
        pass

    # Availability / maintenance model (annual energy realism)
    try:
        av = compute_availability(out, inp)
        out["availability_model"] = av.availability
        out["fw_replace_interval_y"] = av.fw_replace_interval_y
        out["div_replace_interval_y"] = av.div_replace_interval_y
        out["blanket_replace_interval_y"] = av.blanket_replace_interval_y
        out["downtime_scheduled_frac"] = av.downtime_scheduled_frac
        out["downtime_trips_frac"] = av.downtime_trips_frac
        out["availability_min"] = float(getattr(inp, "availability_min", float("nan")))
    except Exception:
        pass

    # -----------------------------------------------------------------
    # (v367.0) Materials lifetime closure: replacement cadence + cost-rate
    # -----------------------------------------------------------------
    try:
        ml = compute_materials_lifetime_closure_v367(out, inp)
        # Merge derived metadata (strictly post-processing; does not alter plasma truth)
        out.update(ml)
        # Override replacement intervals with the materials-authoritative cadence if available.
        # This ensures v359 ledger and constraints see the same cadence.
        if "fw_replace_interval_y_v367" in ml and ml["fw_replace_interval_y_v367"] == ml["fw_replace_interval_y_v367"]:
            out["fw_replace_interval_y"] = float(ml["fw_replace_interval_y_v367"])
        if "blanket_replace_interval_y_v367" in ml and ml["blanket_replace_interval_y_v367"] == ml["blanket_replace_interval_y_v367"]:
            out["blanket_replace_interval_y"] = float(ml["blanket_replace_interval_y_v367"])
    except Exception:
        pass

    # -----------------------------------------------------------------
    # (v384.0.0) Materials & lifetime tightening (divertor+magnet + downtime→CF + annualized replacement cost)
    # -----------------------------------------------------------------
    try:
        out["include_materials_lifetime_v384"] = bool(getattr(inp, "include_materials_lifetime_v384", False))
        out["fw_lifetime_min_yr_v384"] = float(getattr(inp, "fw_lifetime_min_yr_v384", float("nan")))
        out["blanket_lifetime_min_yr_v384"] = float(getattr(inp, "blanket_lifetime_min_yr_v384", float("nan")))
        out["divertor_lifetime_min_yr_v384"] = float(getattr(inp, "divertor_lifetime_min_yr_v384", float("nan")))
        out["magnet_lifetime_min_yr_v384"] = float(getattr(inp, "magnet_lifetime_min_yr_v384", float("nan")))
        out["replacement_cost_max_MUSD_per_y_v384"] = float(getattr(inp, "replacement_cost_max_MUSD_per_y_v384", float("nan")))
        out["capacity_factor_min_v384"] = float(getattr(inp, "capacity_factor_min_v384", float("nan")))

        ml384 = compute_materials_lifetime_tightening_v384(out, inp)
        if isinstance(ml384, dict):
            out.update(ml384)
    except Exception:
        pass

    # Availability-aware annual net generation (MWh/year)
    try:
        Pnet = float(out.get("P_e_net_MW", float('nan')))
        A = float(out.get("availability_model", out.get("availability", float('nan'))))
        if not (A == A):
            A = float(getattr(inp, "availability", 0.70))
        if Pnet == Pnet and A == A:
            out["annual_net_MWh"] = max(Pnet, 0.0) * 8760.0 * max(0.0, min(1.0, A))
        out["annual_net_MWh_min"] = float(getattr(inp, "annual_net_MWh_min", float('nan')))
    except Exception:
        pass

    # -----------------------------------------------------------------
    # (v359.0) Availability & replacement ledger authority (optional)
    # -----------------------------------------------------------------
    try:
        if bool(getattr(inp, "include_availability_replacement_v359", False)):
            av3 = compute_availability_replacement_v359(out, inp)
            out["availability_v359"] = av3.availability
            out["availability_planned_outage_frac_v359"] = av3.planned_outage_frac
            out["availability_forced_outage_frac_v359"] = av3.forced_outage_frac
            out["availability_replacement_downtime_frac_v359"] = av3.replacement_downtime_frac
            out["replacement_cost_MUSD_per_year_v359"] = av3.replacement_cost_MUSD_per_year
            out["major_rebuild_interval_years_v359"] = av3.major_rebuild_interval_years
            out["net_electric_MWh_per_year_v359"] = av3.net_electric_MWh_per_year
            out["LCOE_proxy_v359_USD_per_MWh"] = av3.LCOE_proxy_USD_per_MWh
            out["availability_replacement_contract_sha256"] = av3.contract_sha256
        else:
            # pass through caps for constraint visibility without activating anything
            out["availability_v359_min"] = float(getattr(inp, "availability_v359_min", float('nan')))
            out["LCOE_max_USD_per_MWh"] = float(getattr(inp, "LCOE_max_USD_per_MWh", float('nan')))
    except Exception:
        pass

    # -----------------------------------------------------------------
    # (v368.0) Maintenance Scheduling Authority 1.0 (optional)
    # -----------------------------------------------------------------
    try:
        if bool(getattr(inp, "include_maintenance_scheduling_v368", False)):
            ms = compute_maintenance_schedule_v368(out, inp)
            out["maintenance_schedule_schema_version"] = ms.schema_version
            out["maintenance_contract_sha256"] = ms.contract_sha256
            out["maintenance_planning_horizon_yr_v368"] = ms.planning_horizon_yr
            out["maintenance_bundle_policy_v368"] = ms.bundle_policy
            out["maintenance_bundle_overhead_days_v368"] = ms.bundle_overhead_days

            out["planned_outage_frac_v368"] = ms.planned_outage_frac
            out["forced_outage_frac_v368"] = ms.forced_outage_frac
            out["replacement_outage_frac_v368"] = ms.replacement_outage_frac
            out["outage_total_frac_v368"] = ms.outage_total_frac
            out["availability_v368"] = ms.availability
            out["net_electric_MWh_per_year_v368"] = ms.net_electric_MWh_per_year
            out["replacement_cost_MUSD_per_year_v368"] = ms.replacement_cost_MUSD_per_year
            out["maintenance_events_v368"] = list(ms.events)

            # Pass-through optional caps for constraints
            out["outage_fraction_v368_max"] = float(getattr(inp, "outage_fraction_v368_max", float("nan")))
            out["availability_v368_min"] = float(getattr(inp, "availability_v368_min", float("nan")))
        else:
            # Pass-through caps for visibility
            out["outage_fraction_v368_max"] = float(getattr(inp, "outage_fraction_v368_max", float("nan")))
            out["availability_v368_min"] = float(getattr(inp, "availability_v368_min", float("nan")))
    except Exception:
        pass

    # Pass-through optional caps (constraint-visible, deterministic)
    try:
        out["tritium_inventory_max_g"] = float(getattr(inp, "tritium_inventory_max_g", float('nan')))
        out["fw_dpa_max_per_year"] = float(getattr(inp, "fw_dpa_max_per_year", float('nan')))
        out["enforce_radial_build"] = 1.0 if bool(getattr(inp, "enforce_radial_build", False)) else 0.0
    except Exception:
        pass

    # Added: Economics / COE proxy
    # =========================================================================
    out["COE_max_USD_per_MWh"] = float(getattr(inp, "COE_max_USD_per_MWh", float("nan")))
    if bool(getattr(inp, "include_economics", False)):
        try:
            out.update(cost_proxies(inp, out))
        except Exception:
            pass


    # Added: PROCESS-inspired engineering/economics closures (transparent proxies)
    # =========================================================================
    try:
        mp = magnet_pack_proxy(out, inp)
        out["tf_Jop_MA_per_mm2"] = mp.Jop_MA_per_mm2
        out["tf_Jop_limit_MA_per_mm2"] = mp.Jop_limit_MA_per_mm2
        out["tf_Jop_margin_MA_per_mm2"] = mp.Jop_margin
        out["tf_stress_MPa"] = mp.stress_MPa
        out["tf_stress_allow_MPa"] = mp.stress_allow_MPa
        out["tf_stress_margin_MPa"] = mp.stress_margin
        out["tf_E_GPa"] = float(getattr(inp, "tf_E_GPa", 200.0) or 200.0)
        # Strain proxy: eps = sigma / E.
        sigma = float(out.get("tf_stress_MPa", float("nan")))
        E_GPa = float(out.get("tf_E_GPa", 200.0) or 200.0)
        out["tf_strain"] = (sigma / (max(E_GPa, 1e-9) * 1000.0)) if math.isfinite(sigma) else float("nan")
        out["tf_strain_allow"] = float(getattr(inp, "tf_strain_allow", float("nan")))
        eps_allow = float(out.get("tf_strain_allow", float("nan")))
        eps = float(out.get("tf_strain", float("nan")))
        out["tf_strain_margin"] = (eps_allow - eps) if (math.isfinite(eps_allow) and math.isfinite(eps)) else float("nan")
        out["cryo_power_MW"] = mp.cryo_power_MW

        # -----------------------------------------------------------------
        # (v288.0) Magnet authority 2.0 (diagnostic outputs + optional caps)
        # -----------------------------------------------------------------
        # Adds HTS critical-surface margin and peak-field margins. Does NOT
        # modify the operating point; only exposes transparent feasibility metrics.
        try:
            from engineering import tf_coil as tfc

            # Winding-pack area from the magnet pack proxy if present; otherwise build a conservative guess.
            wp_area_mm2 = float(out.get("tf_wp_area_mm2", float("nan")))
            wp_area_m2 = (wp_area_mm2 / 1e6) if math.isfinite(wp_area_mm2) else float(getattr(inp, "t_tf_wind_m", 0.20)) * float(getattr(inp, "tf_wp_height_factor", 2.4) or 2.4) * float(getattr(inp, "a_m", 1.0)) * float(getattr(inp, "kappa", 1.7))

            R0 = float(getattr(inp, "R0_m", float("nan")))
            Bt = float(getattr(inp, "Bt_T", float("nan")))
            R_inner = float(out.get("R_coil_inner_m", getattr(inp, "R_coil_inner_m", 0.5 * R0)))
            geom = tfc.TFCoilGeom(
                wp_width_m=float(getattr(inp, "tf_wp_width_m", 0.25) or 0.25),
                wp_height_m=float(out.get("tf_wp_height_m", float("nan"))) if math.isfinite(float(out.get("tf_wp_height_m", float("nan")))) else float(getattr(inp, "tf_wp_height_factor", 2.4) or 2.4) * float(getattr(inp, "a_m", 1.0)) * float(getattr(inp, "kappa", 1.7)),
                R_inner_leg_m=float(R_inner),
                Bpeak_factor=float(getattr(inp, "Bpeak_factor", 1.05) or 1.05),
            )
            Bpk = tfc.B_peak_T(Bt, R0, geom) if (math.isfinite(Bt) and math.isfinite(R0)) else float(out.get("B_peak_T", float("nan")))
            out["tf_Bpeak_T"] = float(Bpk)

            # Operating engineering J in A/m^2 from the same NI/A closure used by tf_coil.
            Jop_A_m2 = tfc.engineering_current_density_A_m2(Bt, R0, max(wp_area_m2, 1e-12)) if (math.isfinite(Bt) and math.isfinite(R0)) else float("nan")
            out["tf_Jop_A_m2"] = float(Jop_A_m2)

            # Peak-field cap (already present in inputs).
            Ballow = float(getattr(inp, "B_peak_allow_T", float("nan")))
            out["B_peak_allow_T"] = float(Ballow)
            out["tf_Bpeak_margin_T"] = (Ballow - Bpk) if (math.isfinite(Ballow) and math.isfinite(Bpk)) else float("nan")

            # HTS margin: Jc(B,T,ε) / Jop with multiplicative calibration.
            out["hts_margin_min"] = float(getattr(inp, "hts_margin_min", float("nan")))
            if bool(getattr(inp, "include_hts_critical_surface", False)) and math.isfinite(Bpk) and math.isfinite(Jop_A_m2) and (Jop_A_m2 > 0.0):
                surf = tfc.HTSCriticalSurface(Jc_ref_A_m2=float(tfc.HTSCriticalSurface().Jc_ref_A_m2) * float(getattr(inp, "hts_Jc_mult", 1.0) or 1.0))
                m = tfc.hts_margin(
                    Bpeak_T=float(Bpk),
                    Tcoil_K=float(getattr(inp, "Tcoil_K", 20.0) or 20.0),
                    Jop_A_m2=float(Jop_A_m2),
                    surface=surf,
                    strain=float(getattr(inp, "hts_strain", 0.0) or 0.0),
                    strain_crit=float(getattr(inp, "hts_strain_crit", 0.004) or 0.004),
                )
                out["tf_hts_margin"] = float(m)
            else:
                out["tf_hts_margin"] = float("nan")
        except Exception:
            # Never fail truth; just omit these diagnostics.
            out.setdefault("tf_Bpeak_T", float("nan"))
            out.setdefault("tf_hts_margin", float("nan"))
    except Exception:
        pass

    try:
        tbr = tbr_proxy(out, inp)
        out["TBR"] = tbr.TBR
        out["TBR_required"] = tbr.TBR_required
        out["TBR_margin"] = tbr.margin
        out["TBR_validity"] = tbr.validity
    except Exception:
        pass

    try:
        div = divertor_proxy(out, inp)
        out["Psep_MW"] = div.Psep_MW
        out["q_parallel_MW_per_m2"] = div.q_par_MW_per_m2
        out["q_parallel_limit_MW_per_m2"] = div.q_limit_MW_per_m2
        out["q_parallel_margin_MW_per_m2"] = div.margin
        out["divertor_tech_mode"] = div.mode
    except Exception:
        pass

    try:
        av2 = availability_proxy(out, inp)
        out["availability"] = av2.availability
        out["availability_planned_outage_frac"] = av2.planned_outage_fraction
        out["availability_forced_outage_frac"] = av2.forced_outage_fraction
        out["availability_min"] = float(getattr(inp, "availability_min", getattr(inp, "availability_min_frac", float("nan"))))
    except Exception:
        pass

    try:
        cc = component_cost_proxy(out, inp)
        out["capex_tf_coils_MUSD"] = cc.tf_coils_MUSD
        out["capex_pf_cs_MUSD"] = cc.pf_cs_MUSD
        out["capex_blanket_shield_MUSD"] = cc.blanket_shield_MUSD
        out["capex_cryoplant_MUSD"] = cc.cryoplant_MUSD
        out["capex_bop_MUSD"] = cc.bop_MUSD
        out["capex_buildings_MUSD"] = cc.buildings_MUSD
        out["capex_total_MUSD"] = cc.total_capex_MUSD
    except Exception:
        pass


    # ---------------------------------------------------------------------
    # Heating & current-drive closure (proxy, deterministic)
    # ---------------------------------------------------------------------
    try:
        from physics.heating_cd import estimate_current_drive
        # Populate minimal fields for the CD proxy (best-effort).
        out.setdefault("Ip_MA", float(getattr(inp, "Ip_MA", float("nan"))))
        out.setdefault("B0_T", float(getattr(inp, "B0_T", float("nan"))))
        out.setdefault("R0_m", float(getattr(inp, "R0_m", float("nan"))))
        cd = estimate_current_drive(out)
        if cd is not None:
            out["P_cd_MW"] = cd.P_cd_MW
            out["I_cd_MA"] = cd.I_cd_MA
            out["cd_eta_A_per_W"] = cd.eta_A_per_W
            out["cd_model"] = cd.model
            Ibs = float(out.get("I_bs_MA", out.get("I_bootstrap_MA", float("nan"))))
            Ip = float(out.get("Ip_MA", float("nan")))
            if Ip == Ip and Ip > 0 and Ibs == Ibs:
                out["f_NI"] = float((Ibs + cd.I_cd_MA) / Ip)
            out["f_NI_min"] = float(getattr(inp, "f_NI_min", float("nan")))
    except Exception:
        pass

        # ---------------------------------------------------------------------
    # (v285.0) Exhaust authority bundle (diagnostic outputs + optional caps)
    # ---------------------------------------------------------------------
    try:
        R0 = float(getattr(inp, "R0_m", float("nan")))
        ne20 = float(out.get("ne20", float("nan")))
        Psol = float(out.get("P_SOL_MW", out.get("P_SOL", float("nan"))))
        if (R0 == R0) and (ne20 == ne20) and (Psol == Psol) and (R0 > 0.0) and (ne20 > 0.0):
            out["detachment_index"] = float(Psol / (ne20 * ne20 * R0))
        out["detachment_index_min"] = float(getattr(inp, "detachment_index_min", float("nan")))
        out["detachment_index_max"] = float(getattr(inp, "detachment_index_max", float("nan")))
        f_core = float(out.get("f_rad_core", float(getattr(inp, "f_rad_core", 0.0))))
        f_div = float(out.get("f_rad_div", float(getattr(inp, "f_rad_div", 0.0))))
        f_tot = max(0.0, min(1.0, f_core + f_div))
        out["f_rad_total"] = float(f_tot)
        out["f_rad_total_max"] = float(getattr(inp, "f_rad_total_max", float("nan")))
        # Fuel ion fraction proxy (dilution + optional ash)
        f_fuel = float(getattr(inp, "dilution_fuel", 0.85))
        f_ash = float(getattr(inp, "f_He_ash", 0.0)) if str(getattr(inp, "ash_dilution_mode", "off")) != "off" else 0.0
        fuel_ion = max(0.0, min(1.0, f_fuel * max(0.0, 1.0 - f_ash)))
        out["fuel_ion_fraction"] = float(fuel_ion)
        out["fuel_ion_fraction_min"] = float(getattr(inp, "fuel_ion_fraction_min", float("nan")))
        Q = float(out.get("Q_DT_eqv", out.get("Q", float("nan"))))
        if Q == Q:
            out["Q_effective"] = float(Q * fuel_ion * fuel_ion)
        out["Q_effective_min"] = float(getattr(inp, "Q_effective_min", float("nan")))
    except Exception:
        pass

    # ---------------------------------------------------------------------
    # (v285.0) Magnet quench / protection authority (diagnostic outputs + optional caps)
    # ---------------------------------------------------------------------
    try:
        mu0 = 4.0e-7 * math.pi
        # Prefer tf_Bpeak_T (v288 authority) -> fallback B_peak_T.
        Bp = float(out.get("tf_Bpeak_T", out.get("B_peak_T", float("nan"))))
        R0 = float(getattr(inp, "R0_m", float("nan")))
        wp_area_mm2 = float(out.get("tf_wp_area_mm2", float("nan")))
        wp_area_m2 = (wp_area_mm2 / 1e6) if math.isfinite(wp_area_mm2) else float("nan")

        if all(math.isfinite(x) for x in [Bp, R0, wp_area_m2]) and (Bp > 0.0) and (R0 > 0.0) and (wp_area_m2 > 0.0):
            # Magnetic energy proxy in the TF winding-pack volume (transparent, conservative):
            #   V ~ 2πR0 * A_wp * f_volume
            fV = float(getattr(inp, "tf_energy_volume_factor", 1.0) or 1.0)
            Vmag = (2.0 * math.pi * R0) * wp_area_m2 * max(fV, 1e-6)
            ed_J_m3 = (Bp * Bp) / (2.0 * mu0)
            out["magnet_energy_density_MJ_m3"] = float(ed_J_m3 / 1e6)
            W_J = ed_J_m3 * Vmag
            out["magnet_W_mag_MJ"] = float(W_J * 1e-6)

            qmax = float(getattr(inp, "quench_energy_density_max_MJ_m3", float("nan")))
            if math.isfinite(qmax) and (qmax > 0.0):
                out["magnet_quench_risk_proxy"] = float(out["magnet_energy_density_MJ_m3"] / qmax)
            else:
                out["magnet_quench_risk_proxy"] = float("nan")
        else:
            out.setdefault("magnet_energy_density_MJ_m3", float("nan"))
            out.setdefault("magnet_W_mag_MJ", float("nan"))
            out.setdefault("magnet_quench_risk_proxy", float("nan"))
        out["magnet_quench_risk_max"] = float(getattr(inp, "magnet_quench_risk_max", float("nan")))
        out["quench_energy_density_max_MJ_m3"] = float(getattr(inp, "quench_energy_density_max_MJ_m3", float("nan")))
    except Exception:
        pass

# ---------------------------------------------------------------------
    # Disruption / radiative-limit risk screens (proxy, deterministic)
    # ---------------------------------------------------------------------
    try:
        from physics.risk_screens import evaluate_risk_proxies
        rr = evaluate_risk_proxies(out)
        if rr is not None:
            out["disruption_risk_proxy"] = rr.disruption_risk
            out["f_rad_core"] = rr.radiative_fraction_core
            out["f_rad_core_margin"] = rr.radiative_limit_margin
            out["risk_screen_model"] = rr.model
            out["disruption_risk_max"] = float(getattr(inp, "disruption_risk_max", float("nan")))
            out["f_rad_core_max"] = float(getattr(inp, "f_rad_core_max", float("nan")))
    except Exception:
        pass
    # Model cards (auditability / provenance) for direct hot_ion_point calls.
    # (Evaluator also injects these; ...)
    try:
        from provenance.model_cards import model_cards_index, check_model_card_validity
        out["model_cards"] = model_cards_index()
        out["model_cards_validity"] = check_model_card_validity(out.get("model_cards", {}), dict(getattr(inp, "__dict__", {})), out)
    except Exception:
        # Never gate physics on provenance tooling.
        out.setdefault("model_cards", {})
        out.setdefault("model_cards_validity", {})

    # ---------------------------------------------------------------------
    # Non-authoritative diagnostics (PROCESS/Toka_LITE-inspired sanity checks)
    # ---------------------------------------------------------------------
    # These are for benchmarking and expert interpretation only.
    # They MUST NOT affect constraints, solver behavior, or feasibility.
    try:
        from diagnostics.process_sanity import Shape, fq_PROCESS, Ip_from_q95_PROCESS

        # Only compute when the necessary fields are present and finite.
        R = float(getattr(inp, "R0_m", float("nan")))
        a = float(getattr(inp, "a_m", float("nan")))
        kappa = float(getattr(inp, "kappa", float("nan")))
        delta = float(getattr(inp, "delta", float("nan")))
        Bt = float(getattr(inp, "B0_T", float("nan")))
        Ip = float(getattr(inp, "Ip_MA", float("nan")))
        q95 = float(out.get("q95", out.get("q95_proxy", float("nan"))))
        if all(math.isfinite(x) for x in [R, a, kappa, delta, Bt, Ip, q95]) and (R > 0) and (a > 0) and (Bt > 0) and (q95 > 0):
            sh = Shape(R=R, a=a, kappa=kappa, delta=delta)
            fq = float(fq_PROCESS(sh))
            Ip_proc = float(Ip_from_q95_PROCESS(Bt=Bt, q95=q95, shape=sh))
            out["process_fq"] = fq
            out["Ip_from_q95_PROCESS_MA"] = Ip_proc
            out["Ip_vs_PROCESS_ratio"] = (Ip / Ip_proc) if (math.isfinite(Ip_proc) and abs(Ip_proc) > 1e-12) else float("nan")
            out["process_sanity_note"] = "Diagnostic only; does not affect feasibility. Uses Ip(MA)=5 a^2 Bt/(q95 R fq)."
    except Exception:
        pass
    # Policy contract (feasibility semantics): carried in outputs for downstream constraint evaluation.
    # This MUST NOT change physics outputs; it only allows explicit policy-tiering of certain constraints.
    try:
        out["_policy_contract"] = {
            "q95_enforcement": str(getattr(inp, "q95_enforcement", "hard")),
            "greenwald_enforcement": str(getattr(inp, "greenwald_enforcement", "hard")),
        }
    except Exception:
        out["_policy_contract"] = {"q95_enforcement": "hard", "greenwald_enforcement": "hard"}

    # Maturity/TRL contract (governance): recorded for evidence and constraint metadata.
    try:
        from contracts.tech_tiers import compute_maturity_contract  # type: ignore
        out["_maturity_contract"] = compute_maturity_contract(inp)
    except Exception:
        out["_maturity_contract"] = {"tier": str(getattr(inp, "tech_tier", "TRL7"))}

    # ---------------------------------------------------------------------
    # Plant power ledger overlay (non-authoritative) + optional fuel-cycle ledger
    # ---------------------------------------------------------------------
    try:
        from plant.power_ledger import compute_power_ledger  # type: ignore
        out.update(compute_power_ledger(out))
        # Additional plant bookkeeping components for optional constraint caps
        try:
            cop = float(getattr(inp, "cryo_COP", float('nan')))
            P20 = float(getattr(inp, "P_cryo_20K_MW", float('nan')))
            if cop == cop and cop > 0.0 and P20 == P20 and P20 >= 0.0:
                out["P_cryo_MW"] = P20 / cop
            else:
                out["P_cryo_MW"] = float('nan')
        except Exception:
            out.setdefault("P_cryo_MW", float('nan'))

        try:
            eta_aux = float(getattr(inp, "eta_aux_wallplug", float('nan')))
            if not (eta_aux == eta_aux) or eta_aux <= 0.0:
                eta_aux = 1.0
            Paux_el = float(getattr(inp, "Paux_MW", 0.0)) / eta_aux
            Pcd_launch = float(out.get("P_cd_launch_MW", 0.0))
            eta_cd = float(out.get("eta_cd_wallplug_used", getattr(inp, "eta_cd_wallplug", 0.33)))
            if not (eta_cd == eta_cd) or eta_cd <= 0.0:
                eta_cd = 1.0
            out["P_aux_total_el_MW"] = Paux_el + Pcd_launch / eta_cd
        except Exception:
            out.setdefault("P_aux_total_el_MW", float('nan'))
        # Carry caps through for the constraint ledger (NaN disables)
        out["f_recirc_max"] = float(getattr(inp, "f_recirc_max", float('nan')))
        out["P_pf_avg_max_MW"] = float(getattr(inp, "P_pf_avg_max_MW", float('nan')))
        out["P_aux_max_MW"] = float(getattr(inp, "P_aux_max_MW", float('nan')))
        out["P_cryo_max_MW"] = float(getattr(inp, "P_cryo_max_MW", float('nan')))
        # v361.0 Engineering Actuator Limits Authority: peak power supply draw proxy (optional cap)
        try:
            def _f(v):
                try:
                    x=float(v)
                    return x if x==x else float('nan')
                except Exception:
                    return float('nan')
            Paux_el=_f(out.get('P_aux_total_el_MW', float('nan')))
            Ppf_peak=_f(out.get('pf_P_peak_MW', float('nan')))
            Pvs=_f(out.get('vs_control_power_req_MW', float('nan')))
            Prwm=_f(out.get('rwm_control_power_req_MW', float('nan')))
            vals=[v for v in [Paux_el,Ppf_peak,Pvs,Prwm] if (v==v)]
            out['P_supply_peak_MW']=float(max(vals) if vals else float('nan'))
        except Exception:
            out.setdefault('P_supply_peak_MW', float('nan'))
        out['P_supply_peak_max_MW']=float(getattr(inp,'P_supply_peak_max_MW', float('nan')))
    except Exception:
        pass

    try:
        from fuel_cycle.tritium_authority import compute_tritium_authority  # type: ignore
        out.update(compute_tritium_authority(out, dict(getattr(inp, "__dict__", {}))))
    except Exception:
        pass

    # ---------------------------------------------------------------------
    # v336.0 Plasma Regime Authority (deterministic classifier + margins)
    # ---------------------------------------------------------------------
    try:
        _pl_contract = load_plasma_regime_contract(repo_root)
        pr = evaluate_plasma_regime(out, _pl_contract)
        out["plasma_regime"] = str(pr.plasma_regime)
        out["burn_regime"] = str(pr.burn_regime)
        out["plasma_fragility_class"] = str(pr.fragility_class)
        out["plasma_min_margin_frac"] = float(pr.min_margin_frac)
        out["plasma_contract_sha256"] = str(_pl_contract.sha256)
        # Individual margins (fractional, signed)
        for k, v in (pr.margins or {}).items():
            out[f"plasma_{k}"] = float(v)
    except Exception:
        # Never gate physics on governance tooling.
        out.setdefault("plasma_regime", "unknown")
        out.setdefault("burn_regime", str(out.get("burn_regime", "aux_dominated")))
        out.setdefault("plasma_fragility_class", "UNKNOWN")
        out.setdefault("plasma_min_margin_frac", float('nan'))
        out.setdefault("plasma_contract_sha256", "")


    # ---------------------------------------------------------------------
    # v337.0 Impurity Species & Radiation Partition Authority
    # ---------------------------------------------------------------------
    try:
        _imp_contract = load_impurity_radiation_contract(repo_root)
        ir = evaluate_impurity_radiation(out, _imp_contract)
        out["impurity_regime"] = str(ir.impurity_regime)
        out["impurity_species"] = str(ir.impurity_species)
        out["impurity_fragility_class"] = str(ir.fragility_class)
        out["impurity_min_margin_frac"] = float(ir.min_margin_frac)
        out["impurity_contract_sha256"] = str(_imp_contract.sha256)
        for k, v in (ir.margins or {}).items():
            out[f"impurity_{k}"] = float(v)
        for k, v in (ir.derived or {}).items():
            out[f"impurity_{k}"] = float(v)
    except Exception:
        out.setdefault("impurity_regime", "unknown")
        out.setdefault("impurity_species", str(out.get("impurity_species", "unknown")))
        out.setdefault("impurity_fragility_class", "UNKNOWN")
        out.setdefault("impurity_min_margin_frac", float("nan"))
        out.setdefault("impurity_contract_sha256", "")


    # -----------------------------------------------------------------------------
    # ---------------------------------------------------------------------
    # v345.0 Current Profile Proxy Authority (bootstrap / q-profile / CD)
    # ---------------------------------------------------------------------
    try:
        try:
            from ..contracts.current_profile_proxy_authority_contract import load_current_profile_proxy_contract  # type: ignore
            from ..analysis.current_profile_proxy import evaluate_current_profile_proxy  # type: ignore
        except Exception:
            from contracts.current_profile_proxy_authority_contract import load_current_profile_proxy_contract  # type: ignore
            from analysis.current_profile_proxy import evaluate_current_profile_proxy  # type: ignore

        _cp_contract, _cp_sha = load_current_profile_proxy_contract(repo_root)
        cp = evaluate_current_profile_proxy(out, _cp_contract)
        out["current_profile_regime"] = str(cp.regime)
        out["current_profile_fragility_class"] = str(cp.fragility_class)
        out["current_profile_min_margin_frac"] = float(cp.min_margin_frac)
        out["current_profile_top_limiter"] = str(cp.top_limiter)
        out["current_profile_contract_sha256"] = str(_cp_sha)
        for k, v in (cp.margins or {}).items():
            try:
                out[f"current_profile_{k}"] = float(v)
            except Exception:
                out[f"current_profile_{k}"] = float('nan')
        # Context snapshot (best-effort, for UI / reviewer packs)
        for k, v in (cp.context or {}).items():
            out[f"current_profile_ctx_{k}"] = v
    except Exception:
        out.setdefault("current_profile_regime", "unknown")
        out.setdefault("current_profile_fragility_class", "UNKNOWN")
        out.setdefault("current_profile_min_margin_frac", float('nan'))
        out.setdefault("current_profile_top_limiter", "UNKNOWN")
        out.setdefault("current_profile_contract_sha256", "")



    # ---------------------------------------------------------------------

    # ---------------------------------------------------------------------
    # v349.0 Bootstrap & Pressure Self-Consistency Authority
    # ---------------------------------------------------------------------
    try:
        if bool(getattr(inp, "include_bootstrap_pressure_selfconsistency", False)):
            from src.contracts.bootstrap_pressure_selfconsistency_authority_contract import (
                load_bootstrap_pressure_selfconsistency_contract,
            )
            from src.analysis.bootstrap_pressure_selfconsistency_authority import (
                evaluate_bootstrap_pressure_selfconsistency_authority,
            )
            out["bsp_abs_delta_max"] = float(getattr(inp, "f_bootstrap_consistency_abs_max", float("nan")))
            _c_bsp, _sha_bsp = load_bootstrap_pressure_selfconsistency_contract(repo_root)
            out["bsp_contract_sha256"] = str(_sha_bsp)
            _bsp = evaluate_bootstrap_pressure_selfconsistency_authority(out, _c_bsp)
            for k, v in _bsp.items():
                out[k] = v
        else:
            out.setdefault("bsp_regime", "disabled")
            out.setdefault("bsp_fragility_class", "UNKNOWN")
            out.setdefault("bsp_min_margin_frac", float("nan"))
            out.setdefault("bsp_top_limiter", "DISABLED")
            out.setdefault("bsp_contract_sha256", "")
    except Exception:
        out.setdefault("bsp_regime", "unknown")
        out.setdefault("bsp_fragility_class", "UNKNOWN")
        out.setdefault("bsp_min_margin_frac", float("nan"))
        out.setdefault("bsp_top_limiter", "UNKNOWN")
        out.setdefault("bsp_contract_sha256", "")

    # v346.0 Current Drive Technology Authority (CD tech regimes)
    # ---------------------------------------------------------------------
    try:
        try:
            from ..contracts.cd_tech_authority_contract import load_cd_tech_authority_contract  # type: ignore
            from ..analysis.cd_tech_authority import evaluate_cd_tech_authority  # type: ignore
        except Exception:
            from contracts.cd_tech_authority_contract import load_cd_tech_authority_contract  # type: ignore
            from analysis.cd_tech_authority import evaluate_cd_tech_authority  # type: ignore

        _cd_contract, _cd_sha = load_cd_tech_authority_contract(repo_root)
        cd = evaluate_cd_tech_authority(out, _cd_contract)

        out["cd_tech_regime"] = cd.cd_tech_regime
        out["cd_fragility_class"] = cd.cd_fragility_class
        out["cd_min_margin_frac"] = float(cd.cd_min_margin_frac) if cd.cd_min_margin_frac is not None else float('nan')
        out["cd_top_limiter"] = str(cd.cd_top_limiter)
        out["cd_contract_sha256"] = str(_cd_sha)

        for k, v in (cd.margins or {}).items():
            out[f"cd_{k}"] = float(v) if isinstance(v, (int, float)) else float('nan')
        for k, v in (cd.ctx or {}).items():
            out[f"cd_ctx_{k}"] = v
    except Exception:
        out.setdefault("cd_tech_regime", "unknown")
        out.setdefault("cd_fragility_class", "UNKNOWN")
        out.setdefault("cd_min_margin_frac", float('nan'))
        out.setdefault("cd_top_limiter", "UNKNOWN")
        out.setdefault("cd_contract_sha256", "")


    
    # ---------------------------------------------------------------------
    # v357.0 Current Drive Library Expansion Authority (channel caps)
    # ---------------------------------------------------------------------
    try:
        if bool(getattr(inp, "include_current_drive", False)) and bool(getattr(inp, "include_cd_library_v357", False)):
            try:
                from ..contracts.cd_library_v357_contract import load_cd_library_v357_contract  # type: ignore
                from ..analysis.cd_library_v357_authority import evaluate_cd_library_v357_authority  # type: ignore
            except Exception:
                from contracts.cd_library_v357_contract import load_cd_library_v357_contract  # type: ignore
                from analysis.cd_library_v357_authority import evaluate_cd_library_v357_authority  # type: ignore

            _c_cdl, _sha_cdl = load_cd_library_v357_contract(repo_root)
            cdl = evaluate_cd_library_v357_authority(out, _c_cdl)

            out["cdlib_channel"] = str(cdl.cd_channel)
            out["cdlib_fragility_class"] = str(cdl.fragility_class)
            out["cdlib_min_margin_frac"] = float(cdl.min_margin_frac) if cdl.min_margin_frac is not None else float('nan')
            out["cdlib_top_limiter"] = str(cdl.top_limiter)
            out["cdlib_contract_sha256"] = str(_sha_cdl)

            for k, v in (cdl.margins or {}).items():
                out[f"cdlib_{k}"] = float(v) if isinstance(v, (int, float)) else float('nan')
            for k, v in (cdl.ctx or {}).items():
                out[f"cdlib_ctx_{k}"] = v
        else:
            out.setdefault("cdlib_channel", "disabled")
            out.setdefault("cdlib_fragility_class", "UNKNOWN")
            out.setdefault("cdlib_min_margin_frac", float('nan'))
            out.setdefault("cdlib_top_limiter", "DISABLED")
            out.setdefault("cdlib_contract_sha256", "")
    except Exception:
        out.setdefault("cdlib_channel", "unknown")
        out.setdefault("cdlib_fragility_class", "UNKNOWN")
        out.setdefault("cdlib_min_margin_frac", float('nan'))
        out.setdefault("cdlib_top_limiter", "UNKNOWN")
        out.setdefault("cdlib_contract_sha256", "")

# Non-Inductive Closure Authority (v347)
    # -----------------------------------------------------------------------------
    try:
        from src.contracts.ni_closure_authority_contract import load_ni_closure_authority_contract
        from src.analysis.ni_closure_authority import evaluate_ni_closure_authority

        _c_ni, _sha_ni = load_ni_closure_authority_contract(repo_root)
        out["ni_closure_contract_sha256"] = _sha_ni
        _ni = evaluate_ni_closure_authority(out, _c_ni)
        for k, v in _ni.items():
            out[k] = v
    except Exception:
        out.setdefault("ni_closure_regime", "unknown")
        out.setdefault("ni_fragility_class", "UNKNOWN")
        out.setdefault("ni_min_margin_frac", float('nan'))
        out.setdefault("ni_top_limiter", "UNKNOWN")
        out.setdefault("ni_closure_contract_sha256", "")

    # Neutronics & Materials Authority (v338)
    # -----------------------------------------------------------------------------
    try:
        from src.contracts.neutronics_materials_authority_contract import load_neutronics_materials_contract
        from src.analysis.neutronics_materials import classify_neutronics_materials

        c = load_neutronics_materials_contract(repo_root)
        nm = classify_neutronics_materials(out, limits=c.limits, fragile_margin_frac=c.fragile_margin_frac)

        out["neutronics_materials_regime"] = str(nm.regime)
        out["neutronics_materials_fragility_class"] = str(nm.fragility_class)
        out["neutronics_materials_min_margin_frac"] = float(nm.min_margin_frac)
        out["neutronics_materials_contract_sha256"] = str(c.sha256)

        for k, v in (nm.margins or {}).items():
            out[f"neutronics_materials_{k}"] = float(v)
        for k, v in (nm.derived or {}).items():
            out[f"neutronics_materials_{k}"] = float(v)
    except Exception:
        out.setdefault("neutronics_materials_regime", "unknown")
        out.setdefault("neutronics_materials_fragility_class", "UNKNOWN")
        out.setdefault("neutronics_materials_min_margin_frac", float("nan"))
        out.setdefault("neutronics_materials_contract_sha256", "")

    # v371.0 transport contracts (governance-only diagnostics)
    try:
        if isinstance(transport_contract_v371, dict):
            for k, v in transport_contract_v371.items():
                # Do not overwrite canonical scalars except when identical-key duplication is benign.
                if k not in out:
                    out[k] = v
                else:
                    # Keep existing but allow filling NaNs
                    try:
                        if (out.get(k) != out.get(k)) and (v == v):
                            out[k] = v
                    except Exception:
                        pass
    except Exception:
        pass


    # v372.0 neutronics–materials coupling (governance-only diagnostics)
    try:
        if evaluate_neutronics_materials_coupling_v372 is None:
            raise RuntimeError("nm coupling module not importable")
        nm_cpl_v372 = evaluate_neutronics_materials_coupling_v372(out=out, inp=inp)
        if isinstance(nm_cpl_v372, dict):
            for k, v in nm_cpl_v372.items():
                if k not in out:
                    out[k] = v
                else:
                    try:
                        if (out.get(k) != out.get(k)) and (v == v):
                            out[k] = v
                    except Exception:
                        pass
    except Exception:
        out.setdefault('nm_coupling_v372_enabled', False)

    return out

    # -----------------------------------------------------------------------------
    # Cached wrapper (performance for scans/optimisation)
    # -----------------------------------------------------------------------------
import pickle
from functools import lru_cache

@lru_cache(maxsize=2048)
def _hot_ion_point_cached(inp: PointInputs, Paux_for_Q_MW: Optional[float]) -> bytes:
    # Cache a serialized dict to preserve nested outputs (e.g. profile_meta).
    out = _hot_ion_point_uncached(inp, Paux_for_Q_MW)
    return pickle.dumps(out, protocol=4)

def hot_ion_point(inp: PointInputs, Paux_for_Q_MW: Optional[float] = None) -> Dict[str, float]:
    """Public entrypoint.

    Uses an LRU cache when inputs.enable_point_cache is True (default) to accelerate scans/optimizers.
    """
    if bool(getattr(inp, "enable_point_cache", True)):
        blob = _hot_ion_point_cached(inp, Paux_for_Q_MW)
        return pickle.loads(blob)
    return _hot_ion_point_uncached(inp, Paux_for_Q_MW)
