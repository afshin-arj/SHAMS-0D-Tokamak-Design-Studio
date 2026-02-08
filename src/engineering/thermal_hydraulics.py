from __future__ import annotations
"""Thermal-hydraulic consistency proxies (simple, transparent).

This is intentionally lightweight: it does not attempt CFD. Instead it provides
order-of-magnitude pumping power and temperature rise estimates suitable for
systems-level screening and economics closure.

All relations are documented as proxies; adjust coefficients as better models
are introduced.
"""

from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class Coolant:
    name: str
    # effective heat capacity (MJ/m^3-K) for a representative operating window
    cp_eff_MJ_m3K: float
    # pumping power fraction proxy coefficient (dimensionless)
    pump_frac_coeff: float

COOLANTS: Dict[str, Coolant] = {
    "Helium": Coolant("Helium", cp_eff_MJ_m3K=5e-3, pump_frac_coeff=0.030),
    "Water": Coolant("Water", cp_eff_MJ_m3K=4.2, pump_frac_coeff=0.010),
    "FLiBe": Coolant("FLiBe", cp_eff_MJ_m3K=3.0, pump_frac_coeff=0.015),
}

def coolant_pumping_power_MW(P_th_MW: float, coolant: str = "Helium") -> float:
    """Proxy pumping power proportional to thermal power."""
    c = COOLANTS.get(coolant, COOLANTS["Helium"])
    return float(max(0.0, c.pump_frac_coeff * max(0.0, P_th_MW)))

def coolant_dT_K(P_th_MW: float, flow_m3_s: float, coolant: str = "Helium") -> float:
    """Proxy coolant temperature rise ΔT = P / (ρcp * flow).

    We use cp_eff_MJ/m^3-K as a coarse stand-in for (ρ*cp). This is not meant for
    detailed design; it helps keep pumping/ΔT consistent in scoping studies.
    """
    c = COOLANTS.get(coolant, COOLANTS["Helium"])
    denom_MW_per_K = max(1e-9, c.cp_eff_MJ_m3K * 1e3 * max(flow_m3_s, 1e-9))  # MJ->kJ, kJ/s = kW
    return float(max(0.0, P_th_MW) / denom_MW_per_K)
