from __future__ import annotations
"""TF coil and HTS engineering proxies (SPARC-oriented).

This module is intentionally *0-D / parametric*:
- peak field estimate at the winding pack
- engineering current density in the winding pack
- REBCO-like critical surface proxy Jc(B,T) (+ optional strain degradation)
- stress proxies (magnetic pressure, thin-shell von Mises estimate)

Outputs feed constraints (Bpeak, stress, HTS margin). The model is designed to be improved iteratively
while staying Windows-native and fast.
"""
import math
from dataclasses import dataclass

MU0 = 4e-7 * math.pi

@dataclass(frozen=True)
class TFCoilGeom:
    # Winding-pack cross-section [m]
    wp_width_m: float
    wp_height_m: float
    # Inner-leg radius where Bpeak is evaluated [m]
    R_inner_leg_m: float
    # Enhancement factor from ideal 1/R vacuum field to conductor peak
    Bpeak_factor: float = 1.05

@dataclass(frozen=True)
class HTSCriticalSurface:
    """Lightweight REBCO-like critical surface fit.

    This is intentionally simple (Windows-friendly, no tables).
    It provides a monotonic Jc(B,T) that captures the main trends.

    Jc(B,T) = Jc_ref * (B_ref/B)^b * exp(-c*(T - T_ref))

    Units:
      - Jc in A/m^2 (engineering current density in winding pack)
    """
    Jc_ref_A_m2: float = 3.0e8   # ~300 A/mm^2 engineering at (B_ref,T_ref)
    B_ref_T: float = 20.0
    T_ref_K: float = 20.0
    b_B: float = 0.6
    c_T_per_K: float = 0.06

    def Jc_A_m2(self, B_T: float, T_K: float) -> float:
        B = max(B_T, 1e-6)
        return self.Jc_ref_A_m2 * (self.B_ref_T / B) ** self.b_B * math.exp(-self.c_T_per_K * max(T_K - self.T_ref_K, 0.0))


def required_ampere_turns_A(B0_T: float, R0_m: float) -> float:
    """Total ampere-turns required for toroidal field (vacuum approx)."""
    return B0_T * 2.0 * math.pi * R0_m / MU0


def engineering_current_density_A_m2(B0_T: float, R0_m: float, area_wp_m2: float) -> float:
    """Engineering current density in TF winding pack.

    Using NI/A = (B0*2πR0/μ0)/A.
    """
    A = max(area_wp_m2, 1e-12)
    return required_ampere_turns_A(B0_T, R0_m) / A


def B_peak_T(B0_T: float, R0_m: float, geom: TFCoilGeom) -> float:
    """Peak field on the inner leg using a 1/R mapping with enhancement."""
    R = max(geom.R_inner_leg_m, 1e-6)
    return geom.Bpeak_factor * B0_T * (R0_m / R)


def hts_strain_factor(strain: float, strain_crit: float) -> float:
    if strain <= 0.0:
        return 1.0
    sc = max(strain_crit, 1e-9)
    return math.exp(- (strain / sc) ** 2)


def hts_margin(Bpeak_T: float, Tcoil_K: float, Jop_A_m2: float,
               surface: HTSCriticalSurface,
               strain: float = 0.0, strain_crit: float = 0.004) -> float:
    Jc = surface.Jc_A_m2(Bpeak_T, Tcoil_K) * hts_strain_factor(strain, strain_crit)
    return Jc / max(Jop_A_m2, 1e-12)


def magnetic_pressure_Pa(B_T: float) -> float:
    """Magnetic pressure p = B^2/(2*mu0)."""
    return (B_T * B_T) / (2.0 * MU0)


def von_mises_stress_MPa(Bpeak_T: float, R_inner_m: float, t_struct_m: float) -> float:
    """Very simple TF inner-leg structural stress proxy.

    Uses thin-shell hoop stress: sigma ~ p * R / t, where p = B^2/(2μ0).
    Returns MPa.
    """
    t = max(t_struct_m, 1e-6)
    p = magnetic_pressure_Pa(Bpeak_T)
    sigma_Pa = p * R_inner_m / t
    return sigma_Pa / 1e6
