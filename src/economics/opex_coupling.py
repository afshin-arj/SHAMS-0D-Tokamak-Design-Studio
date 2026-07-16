from __future__ import annotations

"""Centralized availability-coupled annual OPEX components (PROXY tier).

Single source of the annual-OPEX component formulas used by the
``availability_opex_lcoe_authority_v420`` overlay, so the coupling
availability → operating hours → electricity/tritium OPEX is written
in exactly one place (no duplicated economics equations).

Historical note
---------------
The frozen v360 economics authority (``economics/cost.py``) computes similar
components, but its electricity terms use the *legacy* hours basis
(availability_model × duty) even when its annual energy prefers the
v368 / v359 ledgers — an inconsistency the v420 overlay exists to fix.
v360 stamped outputs are intentionally left untouched (frozen behavior);
this module is the go-forward centralized formulation.

All formulas are deterministic, algebraic, single-pass. Units are explicit
in every key name. This is a screening proxy — not a bankable plant cost.

Author: © 2026 Afshin Arjhangmehr
"""

import math
from typing import Any, Dict


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else float(default)
    except (TypeError, ValueError):
        return float(default)


def _finite(x: float) -> bool:
    return x == x and math.isfinite(x)


def annual_opex_components_MUSD(
    inp: Any,
    out: Dict[str, Any],
    *,
    hours_per_year: float,
    availability: float,
    duty_factor: float,
) -> Dict[str, Any]:
    """Availability-coupled annual OPEX components [MUSD/y].

    Parameters
    ----------
    inp : PointInputs-like (economics knobs read via getattr)
    out : L0 evaluator output dict (powers read; never mutated)
    hours_per_year : operating hours [h/y] = 8760 × availability × duty
    availability : selected availability A ∈ [0, 1] (dimensionless)
    duty_factor : pulse duty factor ∈ [0, 1] (dimensionless)

    Returns
    -------
    dict with component keys (all MUSD/y unless suffixed otherwise) plus
    the electric-load breakdown used [MW(e)] for traceability.

    Component formulas (PROXY tier)
    -------------------------------
    - electric_recirc  = price × P_recirc × hours / 1e6
      (L0 recirculating electric power buys grid electricity when not
      self-supplied; transparent screening convention shared with legacy COE)
    - electric_cryo    = price × (P_cryo_20K × cryo_wallplug_multiplier) × hours / 1e6
    - electric_cd      = price × (P_cd / η_cd_wallplug) × hours / 1e6
    - tritium          = T_processing[g/day] × 365 × A × duty × cost[USD/g] / 1e6
      (processing throughput accrues only while burning — availability-coupled,
      unlike the frozen v360 term which used a full 365-day year)
    - maintenance      = k_cost_maint × neutron_wall_load  (damage-rate proxy;
      replacement cadence ledgers already account availability upstream, so
      no additional A scaling here — avoids double-counting)
    - fixed            = inp.opex_fixed_MUSD_per_y
    """
    hours = max(_f(hours_per_year, 0.0), 0.0)
    A = min(max(_f(availability, 0.0), 0.0), 1.0)
    duty = min(max(_f(duty_factor, 1.0), 0.0), 1.0)

    elec_price = _f(getattr(inp, "electricity_price_USD_per_MWh", 60.0), 60.0)

    # --- Electric loads [MW(e)] -------------------------------------------
    P_recirc = _f(out.get("P_recirc_MW"))
    P_pump = _f(out.get("P_pump_MW"), 0.0)
    P_recirc_total = (P_recirc if _finite(P_recirc) else 0.0) + max(P_pump, 0.0)

    cryo_mult = _f(getattr(inp, "cryo_wallplug_multiplier", 250.0), 250.0)
    P_cryo_20K = _f(getattr(inp, "P_cryo_20K_MW", out.get("P_cryo_20K_MW", 0.0)), 0.0)
    P_cryo_wallplug = max(P_cryo_20K, 0.0) * max(cryo_mult, 0.0)

    P_cd = _f(out.get("P_cd_MW", out.get("Pcd_MW", out.get("P_CD_MW", 0.0))), 0.0)
    eta_cd = _f(out.get("eta_cd_wallplug", getattr(inp, "eta_cd_wallplug", 0.35)), 0.35)
    eta_cd = min(max(eta_cd, 1e-6), 1.0)
    P_cd_wallplug = max(P_cd, 0.0) / eta_cd

    # --- Components [MUSD/y] ----------------------------------------------
    opex_elec_recirc = elec_price * max(P_recirc_total, 0.0) * hours / 1e6
    opex_elec_cryo = elec_price * P_cryo_wallplug * hours / 1e6
    opex_elec_cd = elec_price * P_cd_wallplug * hours / 1e6

    T_proc_g_per_day = _f(out.get("T_processing_required_g_per_day"))
    if not _finite(T_proc_g_per_day):
        T_burn_kg_per_day = _f(out.get("T_burn_kg_per_day"))
        T_proc_g_per_day = (
            T_burn_kg_per_day * 1000.0 if _finite(T_burn_kg_per_day) else 0.0
        )
    T_cost_USD_per_g = _f(getattr(inp, "tritium_processing_cost_USD_per_g", 0.05), 0.05)
    opex_tritium = (
        max(T_proc_g_per_day, 0.0) * 365.0 * A * duty * max(T_cost_USD_per_g, 0.0)
    ) / 1e6

    nwl = _f(out.get("neutron_wall_load_MW_m2"), 0.0)
    k_maint = _f(getattr(inp, "k_cost_maint", 15.0), 15.0)
    opex_maint = k_maint * max(nwl, 0.0)

    opex_fixed = _f(getattr(inp, "opex_fixed_MUSD_per_y", 0.0), 0.0)
    if not _finite(opex_fixed):
        opex_fixed = 0.0

    total = (
        opex_fixed
        + opex_elec_recirc
        + opex_elec_cryo
        + opex_elec_cd
        + opex_tritium
        + opex_maint
    )

    return {
        "OPEX_fixed_MUSD_per_y": float(opex_fixed),
        "OPEX_electric_recirc_MUSD_per_y": float(opex_elec_recirc),
        "OPEX_electric_cryo_MUSD_per_y": float(opex_elec_cryo),
        "OPEX_electric_cd_MUSD_per_y": float(opex_elec_cd),
        "OPEX_tritium_MUSD_per_y": float(opex_tritium),
        "OPEX_maintenance_MUSD_per_y": float(opex_maint),
        "OPEX_total_MUSD_per_y": float(total),
        # Traceability: loads and prices actually used
        "P_recirc_el_used_MW": float(max(P_recirc_total, 0.0)),
        "P_cryo_wallplug_used_MW": float(P_cryo_wallplug),
        "P_cd_wallplug_used_MW": float(P_cd_wallplug),
        "electricity_price_used_USD_per_MWh": float(elec_price),
        "tritium_processing_used_g_per_day": float(max(T_proc_g_per_day, 0.0)),
        "hours_per_year_used_h": float(hours),
    }
