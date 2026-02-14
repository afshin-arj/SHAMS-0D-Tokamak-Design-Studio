from __future__ import annotations

"""v356.0 — Cost Overlay Authority (diagnostic).

This module adds a PROCESS-organized component CAPEX breakdown as a
*transparent proxy*.

Design laws
-----------
- No solvers / no iteration.
- Deterministic algebraic mapping only.
- Optional: consumers may ignore these keys.

Units
-----
All outputs are in **MUSD** (million USD) and meant for *relative* comparisons.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict
import math


@dataclass(frozen=True)
class ComponentCostBreakdownV356:
    capex_tf_coils_MUSD: float
    capex_pf_cs_MUSD: float
    capex_blanket_shield_MUSD: float
    capex_cryoplant_MUSD: float
    capex_bop_MUSD: float
    capex_buildings_MUSD: float
    capex_heating_cd_MUSD: float
    capex_tritium_plant_MUSD: float
    CAPEX_component_proxy_MUSD: float


def component_cost_proxy_v356(*, inputs: Any, outputs: Dict[str, Any], legacy_costs: Dict[str, float]) -> Dict[str, float]:
    """Compute a PROCESS-like component CAPEX breakdown (MUSD).

    Parameters
    ----------
    inputs:
        PointInputs (or similar). Only a small set of fields are read.
    outputs:
        Frozen-truth evaluator outputs dict.
    legacy_costs:
        Must include the v355 proxy keys:
        - cost_magnet_MUSD, cost_blanket_MUSD, cost_bop_MUSD, cost_cryo_MUSD

    Returns
    -------
    Dict[str, float]
        Component CAPEX keys + total.
    """

    # --- Start from legacy component proxies (already deterministic) ---
    cost_magnet = float(legacy_costs.get("cost_magnet_MUSD", float("nan")))
    cost_blanket = float(legacy_costs.get("cost_blanket_MUSD", float("nan")))
    cost_bop = float(legacy_costs.get("cost_bop_MUSD", float("nan")))
    cost_cryo = float(legacy_costs.get("cost_cryo_MUSD", float("nan")))

    # Split magnet proxy into TF vs PF/CS using explicit *split knobs*.
    # These knobs were already present in inputs (v355), but unused.
    k_tf = float(getattr(inputs, "cost_k_tf", 120.0))
    k_pf = float(getattr(inputs, "cost_k_pf", 60.0))
    denom = max(k_tf + k_pf, 1e-9)
    tf_share = max(min(k_tf / denom, 1.0), 0.0)

    capex_tf = cost_magnet * tf_share if math.isfinite(cost_magnet) else float("nan")
    capex_pf = cost_magnet * (1.0 - tf_share) if math.isfinite(cost_magnet) else float("nan")

    # Blanket/shield — keep as-is; allow explicit scaling via cost_k_blanket (for future extension)
    capex_blanket = cost_blanket

    # Cryoplant and BOP — keep as-is
    capex_cryo = cost_cryo
    capex_bop = cost_bop

    # Buildings proxy: scale with torus area proxy (already used in cost.py)
    # Use explicit knob cost_k_buildings (v355) as MUSD per (1000 m^2) proxy.
    R0 = float(outputs.get("R0_m", float(getattr(inputs, "R0_m", float("nan")))))
    a = float(outputs.get("a_m", float(getattr(inputs, "a_m", float("nan")))))
    kappa = float(outputs.get("kappa", float(getattr(inputs, "kappa", 1.0))))
    area = 4.0 * math.pi**2 * max(R0 if math.isfinite(R0) else 0.1, 0.1) * max(a if math.isfinite(a) else 0.05, 0.05) * max(kappa if math.isfinite(kappa) else 1.0, 1.0)

    k_build = float(getattr(inputs, "cost_k_buildings", 80.0))
    capex_buildings = k_build * (area / 1000.0)

    # Heating/CD proxy: proportional to CD / aux launch power.
    # Preferred key: P_CD_launch_MW, fallback: Paux_MW.
    P_cd = outputs.get("P_CD_launch_MW", outputs.get("Paux_MW", outputs.get("P_aux_wall_MW", float("nan"))))
    try:
        P_cd = float(P_cd)
    except Exception:
        P_cd = float("nan")
    k_hcd = float(getattr(inputs, "cost_k_heating_cd", 25.0))
    capex_hcd = k_hcd * (max(P_cd, 0.0) if math.isfinite(P_cd) else 0.0)

    # Tritium plant proxy: proportional to tritium burn throughput (kg/day).
    T_burn = outputs.get("T_burn_kg_per_day", float("nan"))
    try:
        T_burn = float(T_burn)
    except Exception:
        T_burn = float("nan")
    k_tri = float(getattr(inputs, "cost_k_tritium_plant", 40.0))
    capex_tritium = k_tri * (max(T_burn, 0.0) if math.isfinite(T_burn) else 0.0)

    # Total
    total = 0.0
    for v in [capex_tf, capex_pf, capex_blanket, capex_cryo, capex_bop, capex_buildings, capex_hcd, capex_tritium]:
        if math.isfinite(v):
            total += float(v)

    br = ComponentCostBreakdownV356(
        capex_tf_coils_MUSD=float(capex_tf) if math.isfinite(capex_tf) else float("nan"),
        capex_pf_cs_MUSD=float(capex_pf) if math.isfinite(capex_pf) else float("nan"),
        capex_blanket_shield_MUSD=float(capex_blanket) if math.isfinite(capex_blanket) else float("nan"),
        capex_cryoplant_MUSD=float(capex_cryo) if math.isfinite(capex_cryo) else float("nan"),
        capex_bop_MUSD=float(capex_bop) if math.isfinite(capex_bop) else float("nan"),
        capex_buildings_MUSD=float(capex_buildings),
        capex_heating_cd_MUSD=float(capex_hcd),
        capex_tritium_plant_MUSD=float(capex_tritium),
        CAPEX_component_proxy_MUSD=float(total),
    )

    return {k: float(v) for k, v in asdict(br).items()}
