
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

@dataclass
class ComponentCostBreakdown:
    tf_coils_MUSD: float
    pf_cs_MUSD: float
    blanket_shield_MUSD: float
    cryoplant_MUSD: float
    bop_MUSD: float
    buildings_MUSD: float
    total_capex_MUSD: float

def component_cost_proxy(out: Dict[str, float], inp: object) -> ComponentCostBreakdown:
    """Component-based CAPEX proxy, inspired by PROCESS organization but not values.

    Costs scale with size, field and power. All coefficients are adjustable via inputs.
    """
    R0 = float(out.get("R0_m", getattr(inp, "R0_m", 6.2)))
    Bt = float(out.get("Bt_T", getattr(inp, "Bt_T", 5.0)))
    Pnet = float(out.get("Pnet_MW", out.get("P_net_MW", 0.0)))
    cryo = float(out.get("cryo_power_MW", 0.0))

    k_tf = float(getattr(inp, "cost_k_tf", 120.0))
    k_pf = float(getattr(inp, "cost_k_pf", 60.0))
    k_bl = float(getattr(inp, "cost_k_blanket", 90.0))
    k_cr = float(getattr(inp, "cost_k_cryo", 30.0))
    k_bop = float(getattr(inp, "cost_k_bop", 55.0))
    k_bld = float(getattr(inp, "cost_k_buildings", 80.0))

    tf = k_tf * (R0/6.2)**2 * (Bt/5.0)**1.6
    pf = k_pf * (R0/6.2)**2
    bl = k_bl * (R0/6.2)**2 * (float(out.get("t_blanket_m", getattr(inp,"t_blanket_m",0.8)))/0.8)
    cr = k_cr * (cryo/1.0 + 0.2)
    bop = k_bop * (max(Pnet, 10.0)/500.0)**0.8
    bld = k_bld * (R0/6.2)**2

    total = tf+pf+bl+cr+bop+bld
    return ComponentCostBreakdown(tf, pf, bl, cr, bop, bld, total)
