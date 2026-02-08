from __future__ import annotations

"""Lifecycle costing (transparent proxy).

This module upgrades the earlier single-number COE proxy into a simple
discounted-cashflow (DCF) *proxy* with explicit replacement schedules.

Design goals:
- Transparent, parameterized, audit-friendly
- Cheap to compute (runs inside the evaluator)
- Backward-compatible with earlier economics keys
- No hard dependency on external costing packages
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List
import math


@dataclass(frozen=True)
class ReplacementItem:
    name: str
    interval_y: float
    part_cost_MUSD: float
    install_factor: float = 1.15  # multiplier on part cost


@dataclass(frozen=True)
class LifecycleAssumptions:
    plant_life_y: float = 30.0
    discount_rate: float = 0.07
    fixed_charge_rate: float = 0.10
    availability: float = 0.70
    capacity_factor: float = 0.75
    decom_fraction_of_capex: float = 0.10


def _npv_factor(discount_rate: float, year: float) -> float:
    return 1.0 / ((1.0 + max(discount_rate, 0.0)) ** max(year, 0.0))


def discounted_cashflow_proxy(
    *,
    capex_MUSD: float,
    opex_MUSD_per_y: float,
    net_electric_MWe: float,
    assumptions: LifecycleAssumptions,
    replacements: List[ReplacementItem],
) -> Dict[str, Any]:
    """Return lifecycle breakdown + LCOE-like proxy.

    LCOE_proxy_USD_per_MWh is computed from NPV(costs) / NPV(energy).
    This is still a proxy (not a bankable model), but it is consistent and auditable.
    """
    life = max(float(assumptions.plant_life_y), 1.0)
    r = float(assumptions.discount_rate)

    capex = float(max(capex_MUSD, 0.0))
    opex = float(max(opex_MUSD_per_y, 0.0))
    Pnet = float(max(net_electric_MWe, 0.0))
    avail = float(max(min(assumptions.availability, 1.0), 0.0))
    capfac = float(max(min(assumptions.capacity_factor, 1.0), 0.0))

    # NPV of CAPEX at year 0
    npv_cost_MUSD = capex

    # OPEX annual (years 1..life)
    npv_opex = 0.0
    npv_energy_MWh = 0.0

    # Use mid-year discounting for annual flows to avoid edge artifacts
    for y in range(1, int(math.ceil(life)) + 1):
        t = min(float(y) - 0.5, life)
        df = _npv_factor(r, t)
        npv_opex += opex * df
        # energy per year
        npv_energy_MWh += (Pnet * 8760.0 * avail * capfac) * df

    npv_cost_MUSD += npv_opex

    # replacements (scheduled)
    repl_events: List[Dict[str, Any]] = []
    npv_repl = 0.0
    for item in replacements:
        if item.interval_y <= 0:
            continue
        k = 1
        while True:
            t = float(item.interval_y) * k
            if t > life:
                break
            df = _npv_factor(r, t)
            cost = float(max(item.part_cost_MUSD, 0.0)) * float(max(item.install_factor, 1.0))
            npv_repl += cost * df
            repl_events.append({
                "name": item.name,
                "year": t,
                "part_cost_MUSD": float(item.part_cost_MUSD),
                "install_factor": float(item.install_factor),
                "event_cost_MUSD": float(cost),
                "discount_factor": float(df),
                "npv_event_MUSD": float(cost * df),
            })
            k += 1

    npv_cost_MUSD += npv_repl

    # decommissioning at end of life
    decom = float(max(assumptions.decom_fraction_of_capex, 0.0)) * capex
    npv_decom = decom * _npv_factor(r, life)
    npv_cost_MUSD += npv_decom

    # LCOE proxy (USD/MWh). 1 MUSD = 1e6 USD
    LCOE = float("inf")
    if npv_energy_MWh > 0:
        LCOE = (npv_cost_MUSD * 1.0e6) / npv_energy_MWh

    return {
        "assumptions": asdict(assumptions),
        "capex_MUSD": capex,
        "opex_MUSD_per_y": opex,
        "net_electric_MWe": Pnet,
        "npv_cost_MUSD": float(npv_cost_MUSD),
        "npv_opex_MUSD": float(npv_opex),
        "npv_replacements_MUSD": float(npv_repl),
        "npv_decom_MUSD": float(npv_decom),
        "npv_energy_MWh": float(npv_energy_MWh),
        "replacement_events": repl_events,
        "LCOE_proxy_USD_per_MWh": float(LCOE),
    }
