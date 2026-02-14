
"""
phase1_systems.py

Systems/engineering *proxies* for a "clean" HTS compact tokamak 0-D point design.

This module is intentionally explicit about assumptions and limitations.

Scope:
- Radial build feasibility (inboard stack closure).
- Toroidal-field (TF) coil peak field mapping and a hoop-stress proxy.
- HTS (REBCO-like) critical margin proxy vs (B,T) and a simple quench/dump voltage proxy.
- Divertor heat-flux constraint surrogate using λq + connection-length proxy + radiated-power fractions.
- Neutronics feasibility surrogates: TBR proxy and HTS fluence lifetime proxy.
- Recirculating power closure: auxiliaries + cryo + current-drive → net electric.

IMPORTANT LIMITATIONS (by design):
- These are *screening* models, not predictive design tools.
- No equilibrium; q95 and Bpol are proxies from phase1_models.
- No detailed magnet design (no winding pack layout, grading, joint physics, etc.).
- No divertor model; λq and q_div are only constraints/metrics.
- No real neutronics; TBR and attenuation are very coarse fits.

The goal is to make every assumption and knob explicit so you can
swap in validated models later (Phase-2+).

Units:
- SI unless otherwise stated.
- Power in MW where indicated.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Tuple

from phase1_models import MU0, MW_TO_W, E_CHARGE

# -----------------------------------------------------------------------------
# Radial build (inboard) and TF peak-field mapping
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class RadialBuild:
    """
    Inboard radial build stack from plasma edge inward to TF inner leg.

    Geometry convention:
      - Major radius R0 is plasma geometric center.
      - Minor radius a is plasma minor radius.
      - Inboard midplane distance from axis to plasma inboard edge is (R0 - a).

    We "spend" the inboard radial space on structural/blanket/shield/coil layers.

    The design is feasible only if:
      R0 - a >= sum(thicknesses)

    Note: real devices include triangularity, gaps, thermal shields, etc.
    Those are represented here as explicit thickness knobs.
    """
    t_fw_m: float = 0.02          # first wall (plasma-facing) [m]
    t_blanket_m: float = 0.50     # breeding blanket (inboard) [m]
    t_shield_m: float = 0.80      # neutron shield (inboard) [m]
    t_vv_m: float = 0.05          # vacuum vessel [m]
    t_gap_m: float = 0.03         # clearance/gap/thermal [m]
    t_tf_wind_m: float = 0.20     # TF winding pack radial thickness [m]
    t_tf_struct_m: float = 0.15   # TF structural case radial thickness [m]

    def total_inboard_m(self) -> float:
        return (
            self.t_fw_m
            + self.t_blanket_m
            + self.t_shield_m
            + self.t_vv_m
            + self.t_gap_m
            + self.t_tf_wind_m
            + self.t_tf_struct_m
        )


def inboard_build_ok(R0_m: float, a_m: float, rb: RadialBuild) -> Tuple[bool, float]:
    """
    Returns (ok, R_coil_inner_m) where R_coil_inner_m is the radius of the TF
    inner leg *inner* surface at the inboard midplane.

    R_coil_inner_m = (R0 - a) - (t_fw + t_blanket + t_shield + t_vv + t_gap)

    If this is <= 0, the inboard stack does not close.
    """
    R_inboard_edge = R0_m - a_m
    spent = rb.t_fw_m + rb.t_blanket_m + rb.t_shield_m + rb.t_vv_m + rb.t_gap_m
    R_coil_inner = R_inboard_edge - spent
    ok = R_coil_inner > 0.0
    return ok, R_coil_inner


def B_peak_T(B0_T: float, R0_m: float, R_coil_inner_m: float, peak_factor: float = 1.05) -> float:
    """
    Toroidal-field peak on TF inner leg from a simple 1/R mapping.

    Assumptions:
      - Toroidal field scales as B(R) ~ constant * (R0 / R) (vacuum field).
      - "peak_factor" accounts for local enhancements (coil shape, ripple, etc.)

    B_peak ≈ peak_factor * B0 * (R0 / R_coil_inner)

    This is a *proxy*. Real designs compute Bpeak from coil geometry and current distribution.
    """
    if R_coil_inner_m <= 0.0:
        return float("inf")
    return peak_factor * B0_T * (R0_m / R_coil_inner_m)


def hoop_stress_MPa(Bpeak_T: float, R_coil_inner_m: float, t_struct_m: float) -> float:
    """
    Very simple TF hoop-stress proxy.

    Magnetic pressure:
      p_mag = B^2 / (2*mu0)

    Hoop stress scaling (order-of-magnitude):
      sigma ~ p_mag * (R / t)

    Returns MPa.

    Notes:
      - Real stress depends on coil case design, winding pack, preload, etc.
      - This proxy is meant for screening only.
    """
    if t_struct_m <= 0.0:
        return float("inf")
    p_mag = (Bpeak_T**2) / (2.0 * MU0)  # Pa
    sigma = p_mag * (R_coil_inner_m / t_struct_m)  # Pa
    return sigma / 1e6  # MPa


# -----------------------------------------------------------------------------
# HTS critical margin proxy and quench/dump proxy
# -----------------------------------------------------------------------------

def rebco_Jc_norm(B_T: float, T_K: float,
                  Tc_K: float = 92.0,
                  B0_T: float = 30.0,
                  n_T: float = 1.5,
                  m_B: float = 1.7) -> float:
    """
    Normalized REBCO-like critical engineering current density Jc(B,T).

    This is a *toy* fit that captures qualitative behavior:
      - decreases with increasing B
      - decreases with increasing T (approaches 0 at Tc)

    Jc_norm = [(1 - T/Tc)^n] / [1 + (B/B0)^m]

    Returns a unitless number (1.0 at B→0, T→0).
    """
    if T_K >= Tc_K:
        return 0.0
    if T_K <= 0.0:
        T_K = 0.1
    temp = max(1.0 - T_K / Tc_K, 0.0) ** n_T
    field = 1.0 + (max(B_T, 0.0) / max(B0_T, 1e-9)) ** m_B
    return temp / field


def hts_operating_margin(Bpeak_T: float, Tcoil_K: float,
                         strain: float = 0.0,
                         strain_crit: float = 0.004,
                         B_ref_T: float = 20.0) -> float:
    """
    Convert Bpeak and coil temperature to a normalized operating margin.

    PROCESS-like intent: expose a *single margin number* that worsens with
    higher peak field, higher temperature, and (optionally) mechanical strain.

    We use a toy REBCO critical surface: Jc_norm(B,T) and apply a Gaussian
    strain degradation factor:
        f_strain = exp(-(strain/strain_crit)^2)

    Operating demand is taken as Jop_norm ~ Bpeak/B_ref (a legacy proxy).

    Margin = Jc_norm(B,T) * f_strain / Jop_norm

    If Margin > 1: comfortably below critical.
    If Margin ~ 1: at critical.
    If Margin < 1: infeasible.

    This remains a screening proxy; it is *not* a detailed conductor model.
    """
    Jc = rebco_Jc_norm(Bpeak_T, Tcoil_K)
    # Strain degradation (optional)
    try:
        eps = float(strain)
    except Exception:
        eps = 0.0
    if eps != 0.0 and strain_crit > 0.0:
        f_strain = math.exp(- (eps / strain_crit) ** 2)
    else:
        f_strain = 1.0

    Jop = max(Bpeak_T / max(B_ref_T, 1e-9), 1e-12)
    return (Jc * f_strain) / Jop


def tf_current_A(B_T: float, R_m: float, N_turns: int = 1) -> float:
    """
    Proxy for TF coil current per turn using a circular loop relation:
      B ~ mu0 * N * I / (2*pi*R)

    Rearranged:
      I ~ B * 2*pi*R / (mu0*N)

    This is *not* how a real TF coil is designed, but it provides a scaling
    for stored energy and dump voltage proxies.
    """
    N = max(int(N_turns), 1)
    return B_T * (2.0 * math.pi * R_m) / (MU0 * N)


def tf_stored_energy_J(B_T: float, volume_m3: float) -> float:
    """
    Stored magnetic energy proxy:
      E ~ (B^2/(2*mu0)) * Volume

    Here "volume" is an effective magnetic-field volume associated with the TF system.
    """
    return (B_T**2) / (2.0 * MU0) * volume_m3


def dump_voltage_kV(E_J: float, I_A: float, tau_dump_s: float) -> float:
    """
    Exponential dump voltage proxy.

    Using:
      E = 0.5 * L * I^2  =>  L = 2E / I^2
      V0 = L * I / tau   =>  V0 = (2E / I) / tau

    Returns kV.
    """
    if I_A <= 0.0 or tau_dump_s <= 0.0:
        return float("inf")
    V0 = (2.0 * E_J / I_A) / tau_dump_s
    return V0 / 1e3


# -----------------------------------------------------------------------------
# Divertor constraint surrogate
# -----------------------------------------------------------------------------

def connection_length_m(q95: float, R0_m: float, f_Lpar: float = 1.0) -> float:
    """
    Crude connection length proxy.

    A common scaling is L_parallel ~ pi * q95 * R.

    We include a multiplier f_Lpar to allow tuning for magnetic configuration.
    """
    return f_Lpar * math.pi * max(q95, 0.0) * max(R0_m, 0.0)


def divertor_wetted_area_m2(R0_m: float, lambda_q_m: float, flux_expansion: float = 5.0, n_strikes: int = 2) -> float:
    """
    Proxy for divertor wetted area:

      A_wet ~ n_strikes * (2*pi*R0) * (lambda_q) * (flux_expansion)

    - lambda_q is the midplane heat-flux width (SOL width proxy).
    - flux_expansion accounts for magnetic/geometry expansion at the target.
    - n_strikes allows single- vs double-null like scaling (default 2).

    This is a screening formula; real A_wet depends on divertor geometry and strike point spreading.
    """
    n = max(int(n_strikes), 1)
    return n * (2.0 * math.pi * R0_m) * max(lambda_q_m, 1e-9) * max(flux_expansion, 1e-9)


def divertor_q_MW_m2(P_SOL_MW: float, R0_m: float, lambda_q_mm: float,
                     flux_expansion: float,
                     f_rad_div: float,
                     n_strikes: int = 2) -> float:
    """
    Divertor target heat-flux proxy:

      q_div ~ (P_SOL * (1 - f_rad_div)) / A_wet

    Where:
      - P_SOL is the power crossing the separatrix (MW).
      - f_rad_div is the divertor radiated fraction (0..1), representing detachment/seeding.

    Returns MW/m^2.
    """
    lam_m = max(lambda_q_mm, 1e-9) * 1e-3
    A = divertor_wetted_area_m2(R0_m, lam_m, flux_expansion=flux_expansion, n_strikes=n_strikes)
    return max(P_SOL_MW, 0.0) * (1.0 - min(max(f_rad_div, 0.0), 1.0)) / max(A, 1e-12)


# -----------------------------------------------------------------------------
# Neutronics surrogates: TBR feasibility and HTS lifetime proxy
# -----------------------------------------------------------------------------

def TBR_proxy(t_blanket_m: float, coverage: float = 0.80, lambda_m: float = 0.30, multiplier: float = 1.10) -> float:
    """
    Very coarse tritium breeding ratio proxy.

    Motivation:
      - thicker blanket generally increases breeding, with diminishing returns.
      - incomplete coverage reduces total breeding.
      - "multiplier" captures material choices (Li6 enrichment, neutron multipliers, etc.)

    Model:
      TBR = coverage * multiplier * (1 - exp(-t_blanket/lambda))

    This is NOT a neutronics calculation; it's a feasibility screen.
    """
    cov = min(max(coverage, 0.0), 1.0)
    t = max(t_blanket_m, 0.0)
    return cov * multiplier * (1.0 - math.exp(-t / max(lambda_m, 1e-9)))


def neutron_flux_from_power(P_n_W: float) -> float:
    """
    Convert neutron power to neutron rate using 14.1 MeV per DT neutron.

    E_n = 14.1 MeV = 14.1e6 * e_charge J

    Returns neutrons/s.
    """
    E_n_J = 14.1e6 * E_CHARGE
    if E_n_J <= 0:
        return 0.0
    return max(P_n_W, 0.0) / E_n_J


def HTS_fluence_per_fpy_n_m2(S_n_W_m2: float,
                            attenuation_len_m: float,
                            shield_m: float,
                            f_geom: float = 0.05) -> float:
    """
    HTS fast-neutron fluence proxy at the TF coil per full-power-year.

    Inputs:
      - S_n_W_m2: neutron wall loading proxy at first wall [W/m^2] (from Phase-1).
      - attenuation_len_m: exponential attenuation length through shield/blanket [m]
      - shield_m: effective shielding thickness to TF [m]
      - f_geom: geometric factor mapping FW flux to TF location without shielding
               (accounts for distance, solid angle, etc.). This is *very* approximate.

    Steps:
      1) neutron flux at FW: phi_FW = (S_n / E_n)  [n/(m^2*s)]
      2) attenuation to coil: phi_TF = phi_FW * f_geom * exp(-shield/att_len)
      3) fluence per FPY: Phi = phi_TF * seconds_per_year

    Returns n/m^2 per FPY.
    """
    E_n_J = 14.1e6 * E_CHARGE
    phi_FW = max(S_n_W_m2, 0.0) / max(E_n_J, 1e-30)
    phi_TF = phi_FW * max(f_geom, 0.0) * math.exp(-max(shield_m, 0.0) / max(attenuation_len_m, 1e-9))
    seconds_per_year = 365.25 * 24.0 * 3600.0
    return phi_TF * seconds_per_year


# -----------------------------------------------------------------------------
# Recirculating power closure (gross electric -> net electric)
# -----------------------------------------------------------------------------

def cryoplant_electric_MW(Q_cold_W: float, W_elec_per_Wcold: float) -> float:
    """
    Convert cold heat lift to electric power using a simple multiplier.

    At ~20 K, a common rule of thumb is ~300 W_electric per 1 W_cold,
    but this depends strongly on temperature and plant efficiency.

    Returns MW electric.
    """
    return max(Q_cold_W, 0.0) * max(W_elec_per_Wcold, 0.0) / MW_TO_W


def joint_loss_W(I_A: float, R_joint_ohm: float, N_joints: int) -> float:
    """Resistive joint heating: P = N * I^2 * R_joint"""
    return max(int(N_joints), 0) * (max(I_A, 0.0) ** 2) * max(R_joint_ohm, 0.0)


def current_drive_power_MW(Ip_MA: float, f_bs: float, eta_cd_MA_per_MW: float) -> Tuple[float, float]:
    """
    Required external current drive and power for steady-state:

      I_CD = (1 - f_bs) * Ip
      P_CD = I_CD / eta_cd   where eta_cd is in MA per MW

    Returns (I_CD_MA, P_CD_MW).

    Note: This assumes bootstrap is the only non-inductive source.
    """
    Icd = max(0.0, (1.0 - min(max(f_bs, 0.0), 1.0)) * max(Ip_MA, 0.0))
    eta = max(eta_cd_MA_per_MW, 1e-9)
    Pcd = Icd / eta
    return Icd, Pcd


def net_electric_MW(Pfus_MW: float,
                    eta_elec: float,
                    Paux_MW: float,
                    eta_aux_wallplug: float,
                    Pcd_MW: float,
                    eta_cd_wallplug: float,
                    Pcryo_MW: float,
                    P_pumps_MW: float) -> Dict[str, float]:
    """
    Gross-to-net electric closure:

      P_gross = eta_elec * Pfus
      P_aux_wall = Paux / eta_aux_wallplug
      P_CD_wall  = Pcd  / eta_cd_wallplug
      P_recirc = P_aux_wall + P_CD_wall + Pcryo + P_pumps
      P_net = P_gross - P_recirc

    This intentionally ignores balance-of-plant subtleties (thermal cycle partial loads, etc.).
    """
    Pgross = max(eta_elec, 0.0) * max(Pfus_MW, 0.0)
    Paux_wall = max(Paux_MW, 0.0) / max(eta_aux_wallplug, 1e-9)
    Pcd_wall = max(Pcd_MW, 0.0) / max(eta_cd_wallplug, 1e-9)
    Precirc = Paux_wall + Pcd_wall + max(Pcryo_MW, 0.0) + max(P_pumps_MW, 0.0)
    return {
        "P_gross_e_MW": Pgross,
        "P_aux_wall_MW": Paux_wall,
        "P_CD_wall_MW": Pcd_wall,
        "P_cryo_e_MW": max(Pcryo_MW, 0.0),
        "P_pumps_MW": max(P_pumps_MW, 0.0),
        "P_recirc_MW": Precirc,
        "P_net_e_MW": Pgross - Precirc,
    }
