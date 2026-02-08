from __future__ import annotations
"""PF/CS (poloidal field / central solenoid) flux swing proxy.

PROCESS includes a detailed PF/CS system model to ensure pulsed operation is feasible.
SHAMS remains lightweight, so we introduce a transparent *proxy* based on standard tokamak
inductance and a simple CS flux capacity estimate.

Definitions (all SI unless stated):

Plasma inductance proxy:
    Lp = μ0 R0 [ ln(8R0/a) - 2 + li/2 ]
where li is the internal inductance (dimensionless). We use li≈0.8 as a typical value.

Required flux swing proxy:
    Δψ_req ≈ Lp * Ip + V_loop_req * t_burn + V_loop_ramp * t_ramp

Here we choose:
    V_loop_req = 0  (by default) unless a max loop voltage is supplied by the caller,
and:
    V_loop_ramp ≈ (Lp * Ip) / t_ramp  (order-of-magnitude ramp voltage)
so the last term adds a conservative ramp contribution.

Available CS flux proxy:
    Δψ_avail ≈ cs_flux_mult * cs_fill_factor * (π r_cs^2) * B_cs,max
with r_cs = cs_radius_factor * R0.

This is *not* a replacement for PF coil design. It is intended to:
- flag obviously impossible pulse-length demands
- provide a tunable margin metric
- integrate into SHAMS constraints and artifacts

All assumptions are recorded in the run artifact.
"""
import math
from dataclasses import dataclass

MU0 = 4e-7 * math.pi

@dataclass(frozen=True)
class CSFluxResult:
    Lp_H: float
    flux_required_Wb: float
    flux_available_Wb: float
    V_loop_ramp_V: float
    margin: float  # (avail - req)/req


def plasma_inductance_H(R0_m: float, a_m: float, li: float = 0.8) -> float:
    R0 = max(R0_m, 1e-6)
    a = max(a_m, 1e-6)
    term = math.log(8.0 * R0 / a) - 2.0 + 0.5 * li
    return MU0 * R0 * max(term, 0.0)


def cs_flux_swing_proxy(
    *,
    R0_m: float,
    a_m: float,
    Ip_MA: float,
    t_burn_s: float,
    cs_Bmax_T: float,
    cs_fill_factor: float,
    cs_radius_factor: float,
    cs_flux_mult: float = 1.0,
    pulse_ramp_s: float = 300.0,
) -> CSFluxResult:
    Ip_A = max(Ip_MA, 0.0) * 1e6
    Lp = plasma_inductance_H(R0_m, a_m)
    # conservative: inductive flux for Ip plus ramp penalty
    flux_inductive = Lp * Ip_A
    t_ramp = max(pulse_ramp_s, 1e-3)
    V_ramp = flux_inductive / t_ramp
    flux_ramp = V_ramp * t_ramp  # equals flux_inductive; included for explicitness
    # burn requirement: treat additional resistive/loop as zero in proxy (can be extended later)
    flux_req = flux_inductive + flux_ramp * 0.25  # modest extra factor for burn/ramp overhead
    # CS available flux
    r_cs = max(cs_radius_factor, 0.0) * max(R0_m, 1e-6)
    area = math.pi * r_cs * r_cs
    flux_avail = max(cs_flux_mult, 0.0) * max(cs_fill_factor, 0.0) * area * max(cs_Bmax_T, 0.0)
    margin = (flux_avail - flux_req) / max(flux_req, 1e-12)
    return CSFluxResult(Lp_H=Lp, flux_required_Wb=flux_req, flux_available_Wb=flux_avail, V_loop_ramp_V=V_ramp, margin=margin)
