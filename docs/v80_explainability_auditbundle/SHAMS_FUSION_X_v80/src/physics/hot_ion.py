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
from typing import Dict, Optional

from models.inputs import PointInputs
from profiles.profiles import ParabolicProfile, PedestalProfile, PlasmaProfiles
from physics.radiation import bremsstrahlung_W, total_core_radiation_W, ImpurityMix, estimate_zeff_from_single_impurity, estimate_zeff_from_mix
from physics.plant import plant_power_closure, electric_efficiency
from economics.cost import cost_proxies
from analysis.mhd_risk import compute_mhd_and_vs_risk
from analysis.availability import compute_availability
from analysis.tritium import compute_tritium_cycle
from engineering.pf_system import pf_system_proxy
from physics.profiles import build_profiles_from_volume_avgs, gradient_proxy_at_pedestal
from physics.divertor import divertor_two_regime
from physics.neutronics import neutronics_proxies
from engineering.thermal_hydraulics import coolant_pumping_power_MW, coolant_dT_K
from analysis.time_evolution import pulsed_summary
from engineering.radial_stack import build_default_stack, neutron_attenuation_factor, nuclear_heating_MW
from engineering.tf_coil import TFCoilGeom, HTSCriticalSurface, engineering_current_density_A_m2, B_peak_T, hts_margin as hts_margin_cs_func, von_mises_stress_MPa
from engineering.pf_cs import cs_flux_swing_proxy
from engineering.coil_thermal import tf_coil_heat_proxy
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
    lambda_q_eich14_mm,
)
from phase1_systems import (
    RadialBuild,
    inboard_build_ok,
    B_peak_T,
    hoop_stress_MPa,
    hts_operating_margin,
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
)

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
            )
            Prad_core_MW = rad_breakdown["P_total_W"] / 1e6
        else:
            # Default behavior: explicit radiated fraction (legacy)
            f_core = min(max(inp.f_rad_core, 0.0), 0.95)
            Prad_core_MW = f_core * Pin_MW

    # Power crossing separatrix (steady-state, 0-D):
    # P_SOL = Pin - Prad_core
    P_SOL_MW = max(Pin_MW - Prad_core_MW, 1e-9)
    P_SOL_over_R_MW_m = P_SOL_MW / max(inp.R0_m, 1e-9)

    # For confinement scaling, use Ploss as the power *not* radiated in the core.
    Ploss_MW = P_SOL_MW

    # ---------------------------
    # Thermal stored energy and confinement
    # ---------------------------
    W_J = 3.0 * ne_m3 * ((Te + Ti) * KEV_TO_J) * V
    W_MJ = W_J / 1e6

    tauE_s = (W_MJ / max(Ploss_MW, 1e-9)) * max(getattr(inp, 'confinement_mult', 1.0), 0.0)

    tauIPB_s = tauE_ipb98y2(
        Ip_MA=inp.Ip_MA, Bt_T=inp.Bt_T, ne20=ne20,
        Ploss_MW=Ploss_MW, R_m=inp.R0_m, a_m=inp.a_m,
        kappa=inp.kappa, M_amu=inp.A_eff
    )
    # Optional confinement scaling comparison
    tauScaling_s = tauIPB_s
    scaling = (getattr(inp, "confinement_scaling", "IPB98y2") or "IPB98y2").upper().replace(" ", "")
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
        "f_G": inp.fG,
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
        "Prad_brem_MW": rad_breakdown.get("P_brem_W",0.0)/1e6,
        "Prad_sync_MW": rad_breakdown.get("P_sync_W",0.0)/1e6,
        "Prad_line_MW": rad_breakdown.get("P_line_W",0.0)/1e6,
        "radiation_model": (inp.radiation_model or "fractional"),
        "P_SOL_MW": P_SOL_MW,
        "P_SOL_over_R_MW_m": P_SOL_over_R_MW_m,
        "P_SOL_over_R_max_MW_m": inp.P_SOL_over_R_max_MW_m,
        "Ploss_MW": Ploss_MW,

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
            out["LH_ok"] = 1.0 if inp.Paux_MW >= margin * PLH else 0.0
        else:
            out["LH_ok"] = 1.0
    else:
        out["P_LH_MW"] = float("nan")
        out["LH_ok"] = float("nan")

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

    # Bootstrap/current fraction proxy selection
    if (inp.bootstrap_model or "proxy").lower() == "improved":
        eps = inp.a_m / max(inp.R0_m, 1e-9)
        beta_p = beta / max(eps, 1e-9)
        fbs = bootstrap_fraction_improved(beta_p, q95, eps)
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
            )
            gp = gradient_proxy_at_pedestal(prof)
            g = float(gp.get("abs_dlnp_dr@r~0.9", 0.0))
            # small, bounded boost to represent steeper edge gradients increasing bootstrap
            fbs *= min(1.25, 1.0 + 0.08 * g)
            out["profile_meta"] = prof.meta
            out["profile_grad_proxy"] = gp
        except Exception:
            # Profile diagnostics should never crash point evaluation
            pass
    out["beta_proxy"] = beta
    out["betaN_proxy"] = betaN
    out["q95_proxy"] = q95

    out["f_bs_proxy"] = fbs

    # =========================================================================
    # Added: (2b) Current drive closure (very lightweight, SPARC-style bookkeeping)
    # =========================================================================
    Ip_A = inp.Ip_MA * 1e6
    I_bs_A = float(fbs) * Ip_A
    P_CD_MW = float(getattr(inp, "P_CD_MW", 0.0))
    eta_CD_A_W = float(getattr(inp, "eta_CD_A_W", 0.04e-6))
    I_cd_A = max(0.0, eta_CD_A_W * (P_CD_MW * 1e6))
    f_NI = (I_bs_A + I_cd_A) / max(Ip_A, 1e-9)
    out["P_CD_MW"] = P_CD_MW
    out["eta_CD_A_W"] = eta_CD_A_W
    out["I_bs_MA"] = I_bs_A / 1e6
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
    # Added: (2) HTS (B,T) margin + dump voltage proxy
    # =========================================================================
    hts_margin = hts_operating_margin(Bpk, inp.Tcoil_K, strain=getattr(inp, "hts_strain", 0.0), strain_crit=getattr(inp, "hts_strain_crit", 0.004)) if math.isfinite(Bpk) else float("nan")
    out["Tcoil_K"] = inp.Tcoil_K
    out["hts_margin"] = hts_margin
    out["hts_margin_min"] = inp.hts_margin_min

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
    # Added: (3) Divertor heat flux constraint (λq + divertor radiation)
    # =========================================================================
    lam_mm = out.get("lambda_q_mm", float("nan"))
    # We use f_rad_div as a *separate* knob: fraction of P_SOL radiated before reaching target.
    f_div = min(max(inp.f_rad_div, 0.0), 0.99)

    qdiv = divertor_q_MW_m2(
        P_SOL_MW=P_SOL_MW,
        R0_m=inp.R0_m,
        lambda_q_mm=lam_mm,
        flux_expansion=inp.flux_expansion,
        f_rad_div=f_div,
        n_strikes=int(getattr(inp, "n_strike_points", 2)),
    )
    Lpar = connection_length_m(q95, inp.R0_m, f_Lpar=inp.f_Lpar)

    out["f_rad_div"] = f_div
    out["flux_expansion"] = inp.flux_expansion
    out["q_div_MW_m2"] = qdiv
    out["q_div_max_MW_m2"] = inp.q_div_max_MW_m2

    # Two-regime divertor proxy (attached vs detached) using P_SOL/R overload.
    div = divertor_two_regime(
        P_SOL_MW=float(P_SOL_MW),
        R0_m=inp.R0_m,
        A_fw_m2=float(A_fw),
        q_div_proxy_MW_m2=float(qdiv),
        P_SOL_over_R_max_MW_m=float(inp.P_SOL_over_R_max_MW_m),
        f_rad_div=float(f_div),
        advanced_divertor_factor=float(getattr(inp,'advanced_divertor_factor',1.0) or 1.0),
    )
    out["div_regime"] = div.regime
    out["f_rad_div_eff"] = div.f_rad_div_eff
    out["P_div_MW"] = div.P_div_MW
    out["q_div_MW_m2"] = div.q_div_MW_m2
    out["q_midplane_MW_m2"] = div.q_mid_MW_m2


    # Midplane/SOL proxy heat flux density (very rough):
    #   q_mp ~ P_SOL / (2πR0 * λq)
    lam_m = max(float(lam_mm) * 1e-3, 1e-6)
    q_mid = P_SOL_MW / (2.0 * math.pi * max(inp.R0_m, 1e-6) * lam_m)
    out["P_SOL_MW"] = P_SOL_MW
    out["P_SOL_over_R_MW_m"] = P_SOL_over_R_MW_m
    out["q_div_W_m2"] = float(out.get("q_div_MW_m2", float("nan"))) * 1e6
    out["q_div_max_W_m2"] = float(inp.q_div_max_MW_m2) * 1e6
    out["q_midplane_W_m2"] = float(q_mid) * 1e6
    out["q_midplane_max_MW_m2"] = float(getattr(inp, "q_midplane_max_MW_m2", float("nan")))
    out["P_SOL_over_R_limit_MW_m"] = float(getattr(inp, "P_SOL_over_R_limit_MW_m", float("nan")))
    out["q_midplane_MW_m2"] = q_mid
    out["n_strike_points"] = int(getattr(inp, "n_strike_points", 2))
    out["Lpar_m"] = Lpar

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
            gamma = float(getattr(inp, "gamma_cd_A_per_W", 0.05))  # A/W
            Pcd_max = float(getattr(inp, "Pcd_max_MW", 200.0))
            Ip_A = max(float(inp.Ip_MA) * 1e6, 1e-6)
            Icd_req_A = max((f_target - f_bs) * Ip_A, 0.0)
            Pcd_req_MW = (Icd_req_A / max(gamma, 1e-12)) / 1e6
            Pcd_launch = min(max(Pcd_req_MW, 0.0), max(Pcd_max, 0.0))
            Icd_A = Pcd_launch * 1e6 * max(gamma, 0.0)
            f_NI = f_bs + Icd_A / Ip_A
            out["P_cd_launch_MW"] = float(Pcd_launch)
            out["I_cd_MA"] = float(Icd_A / 1e6)
            out["f_noninductive"] = float(f_NI)
            out["f_noninductive_target"] = float(f_target)
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
        eta_cd_wallplug=getattr(inp, "eta_cd_wallplug", 0.33),
        P_balance_of_plant_MW=getattr(inp, "P_balance_of_plant_MW", 20.0),
        P_pumps_MW=P_pumps_use_MW,
        P_cryo_20K_MW=getattr(inp, "P_cryo_20K_MW", 0.0),
        cryo_COP=getattr(inp, "cryo_COP", 0.02),
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
        out["cs_flux_margin"] = cs.margin
        out["cs_flux_margin_min"] = float(getattr(inp, "cs_flux_margin_min", float("nan")))
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

    # Operational risk proxies (MHD/disruption, vertical stability margin)
    try:
        risk = compute_mhd_and_vs_risk(out, inp)
        out["mhd_risk_proxy"] = risk.mhd_risk_proxy
        out["vs_margin"] = risk.vs_margin
        out["mhd_risk_max"] = float(getattr(inp, "mhd_risk_max", float("nan")))
        out["vs_margin_min"] = float(getattr(inp, "vs_margin_min", float("nan")))
    except Exception:
        pass

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
