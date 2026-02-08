"""
phase1_models.py (drop-in refactor)

This module provides reusable physics models for a Phase-1 0-D tokamak scan.

"Best available" *0-D* models included:
- IPB98(y,2) energy confinement time scaling (ITER H-mode database).
- Martin-2008 L-H transition power threshold scaling (ITPA).
- Bosch–Hale thermal fusion reactivity (<σv>) for DT and DD branches.
- Optional Eich λq scaling (SOL width) as a *risk metric*.

Also included:
- Simple geometric formulas (volume, first-wall area proxy, surface area).
- Explicit *proxies* for q95, βN, bootstrap fraction for screening.

Important limitations:
- 0-D, volume-averaged, steady-state.
- No transport/profile solver.
- No equilibrium solver; q95 and bootstrap are proxies.
- Divertor physics is not solved; λq is only a metric.

All functions document units and assumptions.
"""

from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Literal, Tuple

MU0 = 4e-7 * math.pi
E_CHARGE = 1.602176634e-19
KEV_TO_J = 1e3 * E_CHARGE
MW_TO_W = 1e6


# -----------------------------
# Bosch–Hale fusion reactivity
# -----------------------------
Reaction = Literal["DT", "DD_Tp", "DD_He3n"]


@dataclass(frozen=True)
class BoschHaleCoeffs:
    BG: float
    MRC2: float
    C1: float
    C2: float
    C3: float
    C4: float
    C5: float
    C6: float
    C7: float


BH_COEFFS = {
    "DT": BoschHaleCoeffs(
        BG=34.3827, MRC2=1124656,
        C1=1.17302e-9, C2=1.51361e-2, C3=7.51886e-2,
        C4=4.60643e-3, C5=1.35000e-2, C6=-1.06750e-4, C7=1.36600e-5
    ),
    "DD_Tp": BoschHaleCoeffs(
        BG=31.3970, MRC2=937814,
        C1=5.65718e-12, C2=3.41267e-3, C3=1.99167e-3,
        C4=0.0, C5=1.05060e-5, C6=0.0, C7=0.0
    ),
    "DD_He3n": BoschHaleCoeffs(
        BG=31.3970, MRC2=937814,
        C1=5.43360e-12, C2=5.85778e-3, C3=7.68222e-3,
        C4=0.0, C5=-2.96400e-6, C6=0.0, C7=0.0
    ),
}


def bosch_hale_sigmav(Ti_keV: float, reaction: Reaction) -> float:
    """
    Thermal Maxwellian reactivity <σv> [m^3/s] using Bosch–Hale parameterization.

    Inputs:
      Ti_keV : ion temperature [keV]
      reaction : "DT", "DD_Tp", "DD_He3n"

    Output:
      <σv> in m^3/s
    """
    if Ti_keV <= 0.0:
        return 0.0
    c = BH_COEFFS[reaction]

    denom = 1.0 + Ti_keV * (c.C3 + Ti_keV * (c.C5 + Ti_keV * c.C7))
    numer = Ti_keV * (c.C2 + Ti_keV * (c.C4 + Ti_keV * c.C6))
    theta = Ti_keV / (1.0 - numer / denom)
    xi = ((c.BG * c.BG) / (4.0 * theta)) ** (1.0 / 3.0)

    sigmav = (
        c.C1 * theta
        * math.sqrt(xi / (c.MRC2 * Ti_keV**3))
        * math.exp(-3.0 * xi)
        * 1e-6
    )
    return max(sigmav, 0.0)


# -----------------------------
# IPB98(y,2) confinement scaling
# -----------------------------

def tauE_iter89p(
    Ip_MA: float,
    Bt_T: float,
    ne20: float,
    Ploss_MW: float,
    R_m: float,
    a_m: float,
    kappa: float,
    M_amu: float = 2.5,
) -> float:
    """ITER89-P L-mode global confinement time τE [s] (engineering scaling).

    This is provided as an *alternative* to IPB98(y2) for sensitivity studies.
    Formula (common form):
      τE = 0.048 * Ip^0.85 * Bt^0.2 * ne^0.1 * Ploss^-0.5 * R^1.2 * a^0.3 * κ^0.5 * M^0.5

    Units: Ip [MA], Bt [T], ne20 [1e20 m^-3], Ploss [MW], R/a [m].
    """
    if Ploss_MW <= 0.0:
        return float("inf")
    return (
        0.048
        * (Ip_MA ** 0.85)
        * (Bt_T ** 0.20)
        * (max(ne20, 1e-12) ** 0.10)
        * (Ploss_MW ** -0.50)
        * (R_m ** 1.20)
        * (a_m ** 0.30)
        * (kappa ** 0.50)
        * (M_amu ** 0.50)
    )

def tauE_ipb98y2(
    Ip_MA: float,
    Bt_T: float,
    ne20: float,
    Ploss_MW: float,
    R_m: float,
    a_m: float,
    kappa: float,
    M_amu: float = 2.5,
) -> float:
    """
    IPB98(y,2) global energy confinement time τE [s].

    τE = 0.0562 * Ip^0.93 * Bt^0.15 * ne^0.41 * Ploss^-0.69
         * R^1.97 * ε^0.58 * κ^0.78 * M^0.19

    Units:
      Ip in MA, Bt in T, ne20 in 1e20 m^-3, Ploss in MW, R/a in m.
    """
    if Ploss_MW <= 0.0:
        return float("inf")
    eps = a_m / max(R_m, 1e-9)
    return (
        0.0562
        * (Ip_MA ** 0.93)
        * (Bt_T ** 0.15)
        * (ne20 ** 0.41)
        * (Ploss_MW ** -0.69)
        * (R_m ** 1.97)
        * (eps ** 0.58)
        * (kappa ** 0.78)
        * (M_amu ** 0.19)
    )



def tauE_iter89p(
    Ip_MA: float,
    Bt_T: float,
    ne20: float,
    Ploss_MW: float,
    R_m: float,
    a_m: float,
    kappa: float,
    M_amu: float = 2.5,
) -> float:
    """ITER89-P L-mode energy confinement time scaling [s].

    A lightweight implementation used for comparative studies / uncertainty envelopes.
    This is not intended to reproduce PROCESS numerically; it provides the correct *scaling structure*.
    """
    eps = a_m / R_m
    return (
        0.038
        * (Ip_MA ** 0.85)
        * (Bt_T ** 0.20)
        * (ne20 ** 0.10)
        * (Ploss_MW ** -0.50)
        * (R_m ** 1.50)
        * (a_m ** 0.30)
        * (kappa ** 0.50)
        * (M_amu ** 0.50)
        * (eps ** 0.00)
    )


# -----------------------------
# Additional confinement scalings (PROCESS-inspired comparators)
# -----------------------------
def tauE_kaye_goldston(
    Ip_MA: float,
    Bt_T: float,
    ne20_lineavg: float,
    Ploss_MW: float,
    R_m: float,
    a_m: float,
    kappa: float,
    M_amu: float = 2.5,
) -> float:
    """Kaye-Goldston L-mode scaling τE [s] (engineering comparator).

    Implemented in the same spirit as PROCESS's confinement_time.kaye_goldston_confinement_time.
    Units: Ip [MA], Bt [T], ne20 [1e20 m^-3], Ploss [MW], R/a [m].
    """
    if Ploss_MW <= 0.0:
        return float("inf")
    return (
        0.055
        * (kappa ** 0.28)
        * (Ip_MA ** 1.24)
        * (max(ne20_lineavg, 1e-12) ** 0.26)
        * (R_m ** 1.65)
        * math.sqrt(max(M_amu, 1e-12) / 1.5)
        / ( (Bt_T ** 0.09) * (a_m ** 0.49) * (Ploss_MW ** 0.58) )
    )

def tauE_neo_alcator(
    ne20_lineavg: float,
    R_m: float,
    a_m: float,
    qstar: float,
) -> float:
    """Neo-Alcator OH scaling τE [s] (comparator).

    PROCESS form: τE = 0.07 * ne20 * a * R^2 * q*
    Here we use a for rminor and R for rmajor, and a simple q* proxy.
    """
    return 0.07 * max(ne20_lineavg, 0.0) * max(a_m, 0.0) * (max(R_m, 0.0) ** 2) * max(qstar, 0.0)

def tauE_mirnov(
    a_m: float,
    kappa: float,
    Ip_MA: float,
) -> float:
    """Mirnov H-mode scaling τE [s] (very lightweight comparator)."""
    return 0.2 * max(a_m, 0.0) * math.sqrt(max(kappa, 0.0)) * max(Ip_MA, 0.0)

def tauE_shimomura(
    R_m: float,
    a_m: float,
    Bt_T: float,
    kappa: float,
    M_amu: float = 2.5,
) -> float:
    """Shimomura optimized H-mode scaling τE [s] (comparator)."""
    return 0.045 * max(R_m, 0.0) * max(a_m, 0.0) * max(Bt_T, 0.0) * math.sqrt(max(kappa, 0.0)) * math.sqrt(max(M_amu, 0.0))


# -----------------------------
# Martin-2008 L-H threshold
# -----------------------------
def p_LH_martin08(ne20_lineavg: float, Bt_T: float, S_m2: float, A_eff: float = 2.0) -> float:
    """
    Martin-2008 L-H transition threshold power P_LH [MW].

    P_LH = 0.0488 * ne20^0.717 * Bt^0.803 * S^0.941 * (2/A_eff)
    """
    if ne20_lineavg <= 0.0 or Bt_T <= 0.0 or S_m2 <= 0.0:
        return 0.0
    return 0.0488 * (ne20_lineavg ** 0.717) * (Bt_T ** 0.803) * (S_m2 ** 0.941) * (2.0 / A_eff)


# -----------------------------
# Optional SOL width metric (Eich)
# -----------------------------
def lambda_q_eich14_mm(Bpol_out_mid_T: float, factor: float = 1.0) -> float:
    """
    Eich λq scaling (risk metric):
      λq [mm] ≈ factor * 0.63 * Bpol^{-1.19}
    """
    if Bpol_out_mid_T <= 0.0:
        return float("inf")
    return factor * 0.63 * (Bpol_out_mid_T ** -1.19)


# -----------------------------
# Geometry helpers
# -----------------------------
def tokamak_volume(R_m: float, a_m: float, kappa: float) -> float:
    """V ≈ 2π^2 R a^2 κ"""
    return 2.0 * math.pi**2 * R_m * (a_m**2) * kappa


def tokamak_surface_area(R_m: float, a_m: float, kappa: float) -> float:
    """S ≈ 4π^2 R a κ (engineering approx; consistent use is what matters)."""
    return 4.0 * math.pi**2 * R_m * a_m * kappa


def S_plasma(R_m: float, a_m: float, kappa: float) -> float:
    """Backward-compatible alias for plasma surface area S [m^2]."""
    return tokamak_surface_area(R_m, a_m, kappa)


def first_wall_area_proxy(R_m: float, a_m: float, kappa: float) -> float:
    """
    Proxy for first-wall area A_fw [m^2] used for neutron wall loading metrics.

    We use the same order-of-unity expression as surface area to keep it consistent
    in Phase-1. Replace with a more accurate surface calculation if needed.
    """
    return tokamak_surface_area(R_m, a_m, kappa)


def greenwald_density_20(Ip_MA: float, a_m: float) -> float:
    """n_GW in 1e20 m^-3: n_GW = Ip/(π a^2)"""
    if a_m <= 0.0:
        return 0.0
    return Ip_MA / (math.pi * a_m**2)


def Bpol_outboard_midplane_T(Ip_MA: float, a_m: float) -> float:
    """Bpol ≈ μ0 Ip / (2π a)"""
    if a_m <= 0.0:
        return float("inf")
    return MU0 * (Ip_MA * 1e6) / (2.0 * math.pi * a_m)


def neutron_shield_capture(t_shield_m: float, lambda_m: float = 0.25) -> float:
    """
    Very simple neutron capture fraction model vs shield thickness.

    eps_n = 1 - exp(-t/lambda)

    This is a placeholder to preserve the original script's "captured neutron power"
    output fields. Replace with a validated neutronics fit for your shield stack.
    """
    if t_shield_m <= 0.0:
        return 0.0
    return 1.0 - math.exp(-t_shield_m / max(lambda_m, 1e-9))


# -----------------------------
# Screening proxies
# -----------------------------
def betaN_from_beta(beta: float, a_m: float, Bt_T: float, Ip_MA: float) -> float:
    """βN = β(%) * a * Bt / Ip  with β(%) = 100*β where β is fraction."""
    if Ip_MA <= 0.0:
        return float("inf")
    return (100.0 * beta) * a_m * Bt_T / Ip_MA


def q95_proxy_cyl(R_m: float, a_m: float, Bt_T: float, Ip_MA: float, kappa: float = 1.0) -> float:
    """
    Very rough q95 proxy (monotonic trends only). Not an equilibrium.
    """
    if Ip_MA <= 0.0:
        return float("inf")
    Ip_A = Ip_MA * 1e6
    return (2.0 * math.pi * R_m * Bt_T / (MU0 * Ip_A)) * (a_m / max(R_m, 1e-9)) / max(kappa, 1e-6)



def bootstrap_fraction_improved(beta_p: float, q95: float, eps: float) -> float:
    """Improved (still simplified) bootstrap fraction proxy.

    Uses a smooth dependence on beta_p, aspect ratio and q95. This is *not*
    a full Sauter bootstrap model, but is more responsive than the constant proxy.
    """
    if beta_p <= 0.0 or q95 <= 0.0:
        return 0.0
    # heuristic: bootstrap rises with beta_p and inverse q; reduced at low eps
    f = 0.55 * (beta_p / (1.0 + beta_p)) * (1.0 / (0.5 + q95/5.0)) * (0.6 + 0.8*max(eps,0.0))
    return max(0.0, min(0.95, f))

def bootstrap_fraction_proxy(betaN: float, q95: float, C_bs: float = 0.15, clamp: Tuple[float, float] = (0.0, 0.95)) -> float:
    """
    Placeholder bootstrap fraction proxy:
      f_bs ≈ C_bs * betaN / q95

    C_bs is exposed as a knob to match your original driver's defaults.
    """
    if q95 <= 0.0:
        return clamp[1]
    f = C_bs * betaN / q95
    return min(max(f, clamp[0]), clamp[1])


def bootstrap_fraction_sauter_proxy(
    beta_p: float,
    q95: float,
    eps: float,
    grad_proxy: float = 0.0,
    clamp: Tuple[float, float] = (0.0, 0.99),
) -> float:
    """Sauter-inspired bootstrap fraction proxy.

    This is intentionally *not* a full Sauter (1999/2002) implementation with
    collisionality and geometry-dependent coefficients. Instead, it provides a
    deterministic, monotone, profile-sensitive closure that tracks key trends:
      - bootstrap increases with poloidal beta (beta_p)
      - decreases with increasing q95
      - increases with inverse aspect ratio (eps = a/R)
      - modestly increases with edge gradient proxy when analytic profiles are enabled

    Tagging:
      - authoritative: deterministic integration not required (proxy)
      - proxy: coefficients and q-profile/collisionality dependence are simplified
    """
    if beta_p <= 0.0 or q95 <= 0.0:
        return 0.0
    e = max(0.0, min(0.9, float(eps)))
    gp = max(0.0, min(5.0, float(grad_proxy)))
    # Base scaling: ~ O(beta_p/q) with aspect ratio shaping.
    base = 0.62 * (beta_p / (1.0 + beta_p)) * (1.0 / (0.6 + q95 / 4.0)) * (0.55 + 1.05 * e)
    # Profile sensitivity: bounded boost for steeper edge gradients.
    boost = 1.0 + 0.12 * gp
    f = base * boost
    return max(clamp[0], min(clamp[1], f))

# -----------------------------
# Backward-compatible aliases
# -----------------------------
def H98_from_tauE(tauE_s: float, tauE98_s: float) -> float:
    """H98(y,2) = tauE / tauE_IPB98(y,2)."""
    if tauE98_s <= 0.0:
        return 0.0
    return tauE_s / tauE98_s

def eich_lambda_q_mm(P_SOL_MW: float, Bt_T: float, q95: float, R_m: float, a_m: float, kappa: float) -> float:
    """Eich-style SOL power width proxy in mm.

    Backward-compatible helper:
    - In this codebase the core proxy is implemented as λq(mm) ≈ 0.63 * Bpol^{-1.19} (with an optional factor),
      where Bpol is evaluated at the outboard midplane.
    - Some callers pass the *engineering* set (P_SOL, Bt, q95, R, a, kappa). For that case, we estimate
      Bpol ≈ Bt * a / (q95 * R) (cylindrical approximation) and then apply the proxy.
    """
    # Cylindrical estimate of outboard-midplane poloidal field
    Bpol_est = (Bt_T * a_m) / max(q95 * R_m, 1e-12)
    return lambda_q_eich14_mm(Bpol_est, factor=1.0)
