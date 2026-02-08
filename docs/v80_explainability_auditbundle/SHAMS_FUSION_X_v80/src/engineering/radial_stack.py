from __future__ import annotations
"""Radial region stack (PROCESS-inspired multi-region build).

This provides a structured representation of the radial build and attaches
simple proxies for neutron attenuation and nuclear heating across regions.

It is intentionally lightweight: coefficients are placeholders and should be
refined with better neutronics proxies as they are introduced.
"""

from dataclasses import dataclass
from typing import List, Dict

@dataclass(frozen=True)
class Region:
    name: str
    thickness_m: float
    # simple neutron attenuation coefficient (1/m)
    mu_n_1_per_m: float = 0.0
    # nuclear heating fraction deposited in this region (dimensionless share)
    heat_frac: float = 0.0

def build_default_stack(inp: Dict[str, float]) -> List[Region]:
    # Coefficients are intentionally simple.
    return [
        Region("Vacuum vessel", float(inp.get("t_vv_m", 0.0)), mu_n_1_per_m=0.5, heat_frac=0.05),
        Region("Shield", float(inp.get("t_shield_m", 0.0)), mu_n_1_per_m=2.0, heat_frac=0.10),
        Region("Blanket", float(inp.get("t_blanket_m", 0.0)), mu_n_1_per_m=1.0, heat_frac=0.25),
        Region("First wall", float(inp.get("t_fw_m", 0.0)), mu_n_1_per_m=1.5, heat_frac=0.10),
        Region("TF winding pack", float(inp.get("t_tf_wind_m", 0.0)), mu_n_1_per_m=0.2, heat_frac=0.02),
        Region("TF structure", float(inp.get("t_tf_struct_m", 0.0)), mu_n_1_per_m=0.2, heat_frac=0.02),
    ]

def neutron_attenuation_factor(stack: List[Region]) -> float:
    """Attenuation factor exp(-∫mu dr)."""
    import math
    tau = sum(max(0.0, r.mu_n_1_per_m) * max(0.0, r.thickness_m) for r in stack)
    return float(math.exp(-tau))

def nuclear_heating_MW(P_fus_MW: float, stack: List[Region]) -> Dict[str, float]:
    """Allocate nuclear heating fractions across regions."""
    P = float(max(0.0, P_fus_MW))
    out: Dict[str, float] = {}
    for r in stack:
        if r.thickness_m <= 0:
            continue
        out[f"P_nuc_{r.name}_MW"] = P * float(max(0.0, r.heat_frac))
    out["P_nuc_total_MW"] = sum(out.values())
    return out
