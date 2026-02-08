from __future__ import annotations
"""TF coil thermal margin proxies.

High-field compact machines are often limited by:
- HTS critical surface (Ic(B,T,ε))
- structural stress
- *and* thermal loads (nuclear heating, AC losses, cryogenic capacity)

SHAMS adds a transparent *thermal margin* proxy:
    P_heat_TF ≈ k_nuc * (neutron_wall_load_MW_m2)  +  k_ac * Bpeak^2
and compares it to a user-provided cooling capacity proxy.

This is intentionally lightweight; coefficients can be calibrated for a given design family.

All outputs are written into the run artifact and can be used as constraints.
"""
import math
from dataclasses import dataclass

@dataclass(frozen=True)
class CoilThermal:
    P_heat_MW: float
    P_nuclear_MW: float
    P_ac_MW: float
    cooling_capacity_MW: float
    margin: float  # (cap - heat)/heat


def tf_coil_heat_proxy(
    neutron_wall_load_MW_m2: float,
    Bpeak_T: float,
    *,
    k_nuclear_MW_per_MW_m2: float = 0.2,
    k_ac_MW_per_T2: float = 0.002,
    cooling_capacity_MW: float = 5.0,
) -> CoilThermal:
    P_nuc = max(k_nuclear_MW_per_MW_m2, 0.0) * max(neutron_wall_load_MW_m2, 0.0)
    P_ac = max(k_ac_MW_per_T2, 0.0) * (max(Bpeak_T, 0.0) ** 2)
    P_heat = P_nuc + P_ac
    cap = max(cooling_capacity_MW, 0.0)
    margin = (cap - P_heat) / max(P_heat, 1e-12)
    return CoilThermal(P_heat_MW=P_heat, P_nuclear_MW=P_nuc, P_ac_MW=P_ac, cooling_capacity_MW=cap, margin=margin)
