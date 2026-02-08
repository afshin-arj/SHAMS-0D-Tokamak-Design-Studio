from __future__ import annotations
"""Neutronics proxies for early design screening.

Provides simple, geometry-based proxies:
- neutron wall loading ~ P_fus / A_fw
- fluence per full-power-year
- lifetime proxy against a fluence limit

These proxies are sufficient to couple fusion power to component lifetime constraints.
"""
import math
from dataclasses import dataclass

@dataclass(frozen=True)
class NeutronicsResult:
    neutron_wall_load_MW_m2: float
    fluence_n_m2_per_fpy: float
    lifetime_yr: float

def neutronics_proxies(Pfus_MW: float,
                       A_fw_m2: float,
                       hts_fluence_limit_n_m2: float,
                       atten_len_m: float,
                       t_shield_m: float,
                       f_geom_to_tf: float) -> NeutronicsResult:
    """Very simple neutronics/lifetime proxies.

    - Neutron wall load: assume 80% of fusion power is neutron power.
    - Fluence at TF: attenuated from FW with exp(-t/λ) and geometry factor.
    """
    Pfus = max(Pfus_MW, 0.0)
    Pn = 0.8 * Pfus
    wall = (Pn * 1e6) / max(A_fw_m2, 1e-6) / 1e6  # MW/m2
    # crude mapping MW/m2 -> n/m2/s: treat 1 MW/m2 ~ 3.5e19 n/m2/s at 14 MeV (rough)
    nflux_fw = wall * 3.5e19
    atten = math.exp(-max(t_shield_m,0.0)/max(atten_len_m,1e-9))
    nflux_tf = nflux_fw * atten * max(f_geom_to_tf, 0.0)
    fpy_s = 365.25*24*3600
    fluence = nflux_tf * fpy_s
    lifetime = hts_fluence_limit_n_m2 / max(fluence, 1e-12)
    return NeutronicsResult(neutron_wall_load_MW_m2=wall, fluence_n_m2_per_fpy=fluence, lifetime_yr=lifetime)
