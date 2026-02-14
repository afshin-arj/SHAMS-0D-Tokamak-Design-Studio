from __future__ import annotations
"""Radial region stack (PROCESS-inspired multi-region build).

This provides a structured representation of the radial build and attaches
simple proxies for neutron attenuation and nuclear heating across regions.

It is intentionally lightweight: coefficients are placeholders and should be
refined with better neutronics proxies as they are introduced.
"""

from dataclasses import dataclass
from typing import List, Dict

try:
    from .materials_library import get_material, MaterialNeutronProps
except Exception:  # pragma: no cover (back-compat when src not a package)
    from engineering.materials_library import get_material, MaterialNeutronProps  # type: ignore

@dataclass(frozen=True)
class Region:
    name: str
    thickness_m: float
    # simple neutron attenuation coefficient (1/m)
    mu_n_1_per_m: float = 0.0
    # nuclear heating fraction deposited in this region (dimensionless share)
    heat_frac: float = 0.0

def build_default_stack(inp: Dict[str, float]) -> List[Region]:
    # Coefficients are intentionally simple; may be overridden by materials.
    # Materials are provided as strings in inp (e.g. 'shield_material').

    vv_fb = MaterialNeutronProps("VV_STEEL", mu_n_1_per_m=0.5, heat_frac=0.05, dpa_total_limit=60.0)
    sh_fb = MaterialNeutronProps("WC", mu_n_1_per_m=2.0, heat_frac=0.10, dpa_total_limit=200.0)
    bl_fb = MaterialNeutronProps("LiPb", mu_n_1_per_m=1.0, heat_frac=0.25, dpa_total_limit=120.0)
    fw_fb = MaterialNeutronProps("EUROFER", mu_n_1_per_m=1.5, heat_frac=0.10, dpa_total_limit=80.0)
    tf_fb = MaterialNeutronProps("REBCO", mu_n_1_per_m=0.2, heat_frac=0.02, dpa_total_limit=30.0)

    vv = get_material(str(inp.get("vv_material", "VV_STEEL")), vv_fb)
    sh = get_material(str(inp.get("shield_material", "WC")), sh_fb)
    bl = get_material(str(inp.get("blanket_material", "LiPb")), bl_fb)
    fw = get_material(str(inp.get("fw_material", "EUROFER")), fw_fb)
    tf = get_material(str(inp.get("tf_material", "REBCO")), tf_fb)

    return [
        Region("Vacuum vessel", float(inp.get("t_vv_m", 0.0)), mu_n_1_per_m=vv.mu_n_1_per_m, heat_frac=vv.heat_frac),
        Region("Shield", float(inp.get("t_shield_m", 0.0)), mu_n_1_per_m=sh.mu_n_1_per_m, heat_frac=sh.heat_frac),
        Region("Blanket", float(inp.get("t_blanket_m", 0.0)), mu_n_1_per_m=bl.mu_n_1_per_m, heat_frac=bl.heat_frac),
        Region("First wall", float(inp.get("t_fw_m", 0.0)), mu_n_1_per_m=fw.mu_n_1_per_m, heat_frac=fw.heat_frac),
        Region("TF winding pack", float(inp.get("t_tf_wind_m", 0.0)), mu_n_1_per_m=tf.mu_n_1_per_m, heat_frac=tf.heat_frac),
        Region("TF structure", float(inp.get("t_tf_struct_m", 0.0)), mu_n_1_per_m=tf.mu_n_1_per_m, heat_frac=tf.heat_frac),
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
