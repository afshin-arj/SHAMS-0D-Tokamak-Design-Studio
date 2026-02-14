from __future__ import annotations

"""Availability & replacement-ledger overlay (v359.0).

Deterministic algebraic bookkeeping:
- planned outage baseline
- forced outage baseline
- replacement downtime from component replacement cadence
- optional annualized replacement cost rate from component CAPEX proxies

This is a governance-friendly proxy and is NOT a time-domain RAMI simulator.
"""

from dataclasses import dataclass
from typing import Any, Dict
import math
import hashlib
from pathlib import Path


@dataclass(frozen=True)
class AvailabilityReplacementV359:
    availability: float
    planned_outage_frac: float
    forced_outage_frac: float
    replacement_downtime_frac: float
    replacement_cost_MUSD_per_year: float
    major_rebuild_interval_years: float
    net_electric_MWh_per_year: float
    LCOE_proxy_USD_per_MWh: float
    contract_sha256: str


def _finite(x: float) -> bool:
    return (x == x) and math.isfinite(x)


def compute_availability_replacement_v359(out: Dict[str, Any], inp: Any) -> AvailabilityReplacementV359:
    # Load contract fingerprint (in-repo)
    contract_sha = ""
    try:
        here = Path(__file__).resolve()
        contract_path = here.parents[2] / "contracts" / "availability_replacement_v359_contract.json"
        if contract_path.exists():
            contract_sha = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    except Exception:
        contract_sha = ""

    # Baselines
    planned = float(getattr(inp, "planned_outage_base", 0.05) or 0.05)
    forced = float(getattr(inp, "forced_outage_base", 0.10) or 0.10)
    planned = max(0.0, min(0.50, planned))
    forced = max(0.0, min(0.50, forced))

    # Replacement cadence (years) + downtime per replacement (days)
    # Use existing computed intervals for FW/divertor/blanket if present.
    fw_int = float(out.get("fw_replace_interval_y", float('nan')))
    div_int = float(out.get("div_replace_interval_y", float('nan')))
    bl_int = float(out.get("blanket_replace_interval_y", float('nan')))
    fw_days = float(getattr(inp, "fw_replace_time_days", 30.0) or 30.0)
    div_days = float(getattr(inp, "div_replace_time_days", 30.0) or 30.0)
    bl_days = float(getattr(inp, "blanket_replace_time_days", 90.0) or 90.0)

    # Extra components
    hcd_int = float(getattr(inp, "heating_cd_replace_interval_y", 8.0) or 8.0)
    hcd_days = float(getattr(inp, "heating_cd_replace_duration_days", 30.0) or 30.0)
    tplant_int = float(getattr(inp, "tritium_plant_replace_interval_y", 10.0) or 10.0)
    tplant_days = float(getattr(inp, "tritium_plant_replace_duration_days", 30.0) or 30.0)

    def _term(days: float, interval_y: float) -> float:
        if not _finite(interval_y) or interval_y <= 0.0:
            return 0.0
        return max(days, 0.0) / 365.0 / interval_y

    repl = 0.0
    repl += _term(fw_days, fw_int)
    repl += _term(div_days, div_int)
    repl += _term(bl_days, bl_int)
    repl += _term(hcd_days, hcd_int)
    repl += _term(tplant_days, tplant_int)
    repl = max(0.0, min(0.90, repl))

    # Availability
    A = 1.0 - planned - forced - repl
    A = max(0.0, min(1.0, A))

    # Replacement cost rate (MUSD/y): annualize component CAPEX proxies if present.
    cap_hcd = float(out.get("capex_heating_cd_MUSD", float('nan')))
    cap_tp = float(out.get("capex_tritium_plant_MUSD", float('nan')))
    # Use install factor similar to lifecycle (transparent constant)
    install = float(getattr(inp, "replacement_installation_factor", 1.15) or 1.15)

    cost_rate = 0.0
    if _finite(cap_hcd) and _finite(hcd_int) and hcd_int > 0:
        cost_rate += max(cap_hcd, 0.0) * install / hcd_int
    if _finite(cap_tp) and _finite(tplant_int) and tplant_int > 0:
        cost_rate += max(cap_tp, 0.0) * install / tplant_int

    # v367.0: if materials lifetime closure provided annualized component cost rates, include them.
    # (Deterministic bookkeeping; no double-counting assumed by contract.)
    fw_cost = float(out.get("fw_replacement_cost_MUSD_per_year", float('nan')))
    bl_cost = float(out.get("blanket_replacement_cost_MUSD_per_year", float('nan')))
    if _finite(fw_cost):
        cost_rate += max(fw_cost, 0.0)
    if _finite(bl_cost):
        cost_rate += max(bl_cost, 0.0)

    # Major rebuild interval proxy: min of key replacement intervals if finite
    ints = [x for x in [fw_int, div_int, bl_int, hcd_int, tplant_int] if _finite(x) and x > 0]
    major = min(ints) if ints else float('nan')

    # Net electric MWh/year using P_e_net_MW and A.
    Pnet = float(out.get("P_e_net_MW", float('nan')))
    duty = float(out.get("duty_factor", 1.0))
    if not _finite(duty):
        duty = 1.0
    duty = max(0.0, min(1.0, duty))
    if _finite(Pnet):
        E = max(Pnet, 0.0) * 8760.0 * A * duty
    else:
        E = float('nan')

    # Simple LCOE proxy based on existing CAPEX/OPEX proxies (does not replace v355/v356 LCOE).
    CAPEX = float(out.get("CAPEX_component_proxy_MUSD", out.get("CAPEX_proxy_MUSD", float('nan'))))
    OPEX = float(out.get("OPEX_proxy_MUSD_per_y", float('nan')))
    fcr = float(getattr(inp, "fixed_charge_rate", 0.10) or 0.10)
    if _finite(CAPEX) and _finite(OPEX) and _finite(E) and E > 0:
        lcoe = ((fcr * CAPEX) + OPEX + cost_rate) * 1e6 / E
    else:
        lcoe = float('nan')

    return AvailabilityReplacementV359(
        availability=float(A),
        planned_outage_frac=float(planned),
        forced_outage_frac=float(forced),
        replacement_downtime_frac=float(repl),
        replacement_cost_MUSD_per_year=float(cost_rate),
        major_rebuild_interval_years=float(major),
        net_electric_MWh_per_year=float(E),
        LCOE_proxy_USD_per_MWh=float(lcoe),
        contract_sha256=str(contract_sha),
    )
