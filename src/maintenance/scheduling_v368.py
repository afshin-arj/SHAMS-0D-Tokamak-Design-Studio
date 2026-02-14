from __future__ import annotations

"""Maintenance Scheduling Authority 1.0 (v368.0).

Deterministic, algebraic scheduling closure that converts component
replacement cadences + replacement durations into an **outage calendar proxy**.

Hard requirements:
- No solvers
- No iteration
- No hidden relaxation
- Bitwise reproducible arithmetic

This module is strictly post-processing: it must not modify plasma truth.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import math


def _finite(x: float) -> bool:
    return (x == x) and math.isfinite(x)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _sha256_file(p: Path) -> str:
    try:
        if p.exists():
            return hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception:
        pass
    return ""


@dataclass(frozen=True)
class MaintenanceScheduleV368:
    schema_version: str
    contract_sha256: str
    planning_horizon_yr: float
    bundle_policy: str
    bundle_overhead_days: float

    planned_outage_frac: float
    forced_outage_frac: float
    replacement_outage_frac: float
    outage_total_frac: float
    availability: float

    net_electric_MWh_per_year: float
    replacement_cost_MUSD_per_year: float

    events: Tuple[Dict[str, Any], ...]


def _component_specs(out: Dict[str, Any], inp: Any) -> List[Dict[str, Any]]:
    """Return canonical component specs used by the scheduling model.

    Cadences are expected to be provided by upstream authorities (v367 for FW/blanket).
    """

    # Replacement cadence (years) should already be in out (v367 override).
    fw_int = float(out.get("fw_replace_interval_y", float("nan")))
    div_int = float(out.get("div_replace_interval_y", float("nan")))
    bl_int = float(out.get("blanket_replace_interval_y", float("nan")))

    fw_days = float(getattr(inp, "fw_replace_time_days", 30.0) or 30.0)
    div_days = float(getattr(inp, "div_replace_time_days", 30.0) or 30.0)
    bl_days = float(getattr(inp, "blanket_replace_time_days", 90.0) or 90.0)

    hcd_int = float(getattr(inp, "heating_cd_replace_interval_y", 8.0) or 8.0)
    hcd_days = float(getattr(inp, "heating_cd_replace_duration_days", 30.0) or 30.0)

    tplant_int = float(getattr(inp, "tritium_plant_replace_interval_y", 10.0) or 10.0)
    tplant_days = float(getattr(inp, "tritium_plant_replace_duration_days", 30.0) or 30.0)

    return [
        {"key": "first_wall", "interval_y": fw_int, "duration_days": fw_days, "bundle_group": "in_vessel"},
        {"key": "divertor", "interval_y": div_int, "duration_days": div_days, "bundle_group": "in_vessel"},
        {"key": "blanket", "interval_y": bl_int, "duration_days": bl_days, "bundle_group": "in_vessel"},
        {"key": "heating_cd", "interval_y": hcd_int, "duration_days": hcd_days, "bundle_group": "balance"},
        {"key": "tritium_plant", "interval_y": tplant_int, "duration_days": tplant_days, "bundle_group": "balance"},
    ]


def _annualized_replacement_cost_rate(out: Dict[str, Any], inp: Any) -> float:
    """Annualized replacement cost rate (MUSD/y).

    Policy:
    - Prefer v367 material-authoritative annualized rates for FW/blanket.
    - Add any explicit CAPEX-based annualization for HCD / tritium plant.
    """

    install = float(getattr(inp, "replacement_installation_factor", 1.15) or 1.15)

    # v367 authoritative annualized component cost rates
    fw_cost = float(out.get("fw_replacement_cost_MUSD_per_year", float("nan")))
    bl_cost = float(out.get("blanket_replacement_cost_MUSD_per_year", float("nan")))

    cost_rate = 0.0
    if _finite(fw_cost):
        cost_rate += max(fw_cost, 0.0)
    if _finite(bl_cost):
        cost_rate += max(bl_cost, 0.0)

    # Additional components (transparent proxies)
    cap_hcd = float(out.get("capex_heating_cd_MUSD", float("nan")))
    hcd_int = float(getattr(inp, "heating_cd_replace_interval_y", 8.0) or 8.0)
    if _finite(cap_hcd) and _finite(hcd_int) and hcd_int > 0:
        cost_rate += max(cap_hcd, 0.0) * install / hcd_int

    cap_tp = float(out.get("capex_tritium_plant_MUSD", float("nan")))
    tplant_int = float(getattr(inp, "tritium_plant_replace_interval_y", 10.0) or 10.0)
    if _finite(cap_tp) and _finite(tplant_int) and tplant_int > 0:
        cost_rate += max(cap_tp, 0.0) * install / tplant_int

    return float(max(cost_rate, 0.0))


def _schedule_independent(components: List[Dict[str, Any]]) -> Tuple[float, List[Dict[str, Any]]]:
    """Independent replacement model.

    Outage fraction is the sum over components of duration/(365*interval).
    """

    events: List[Dict[str, Any]] = []
    repl = 0.0
    for c in components:
        itv = float(c.get("interval_y", float("nan")))
        dur = float(c.get("duration_days", 0.0))
        if not _finite(itv) or itv <= 0.0:
            continue
        term = max(dur, 0.0) / 365.0 / itv
        repl += term
        events.append(
            {
                "component": str(c.get("key")),
                "policy": "independent",
                "interval_y": float(itv),
                "duration_days": float(max(dur, 0.0)),
                "annual_events": float(1.0 / itv),
                "outage_frac": float(term),
            }
        )
    return float(repl), events


def _bundle_group_schedule(
    group: List[Dict[str, Any]],
    *,
    policy_label: str,
    overhead_days: float,
) -> Tuple[float, List[Dict[str, Any]]]:
    """Bundle a set of components into a single maintenance window.

    Deterministic proxy:
      - bundle interval = min(component intervals)
      - bundle duration = max(component durations) + overhead

    This avoids simulating calendars while preserving an upper-bound style
    outage coupling.
    """

    valid = [c for c in group if _finite(float(c.get("interval_y", float("nan")))) and float(c["interval_y"]) > 0.0]
    if not valid:
        return 0.0, []

    interval = min(float(c["interval_y"]) for c in valid)
    duration = max(float(c.get("duration_days", 0.0)) for c in valid) + max(overhead_days, 0.0)

    outage = max(duration, 0.0) / 365.0 / interval

    ev = {
        "component": "+".join(sorted(str(c.get("key")) for c in valid)),
        "policy": str(policy_label),
        "interval_y": float(interval),
        "duration_days": float(max(duration, 0.0)),
        "annual_events": float(1.0 / interval),
        "outage_frac": float(outage),
    }
    return float(outage), [ev]


def _schedule_bundled(
    components: List[Dict[str, Any]],
    *,
    bundle_policy: str,
    overhead_days: float,
) -> Tuple[float, List[Dict[str, Any]]]:
    """Bundled replacement models."""

    pol = (bundle_policy or "").strip().lower()
    overhead = float(overhead_days or 0.0)

    if pol in ("bundle_in_vessel", "bundle_in-vessel", "in_vessel"):
        inv = [c for c in components if str(c.get("bundle_group")) == "in_vessel"]
        other = [c for c in components if str(c.get("bundle_group")) != "in_vessel"]
        o1, e1 = _bundle_group_schedule(inv, policy_label="bundle_in_vessel", overhead_days=overhead)
        o2, e2 = _schedule_independent(other)
        return float(o1 + o2), [*e1, *e2]

    if pol in ("bundle_all", "all"):
        o, e = _bundle_group_schedule(components, policy_label="bundle_all", overhead_days=overhead)
        return float(o), e

    # Fallback: independent
    return _schedule_independent(components)


def compute_maintenance_schedule_v368(out: Dict[str, Any], inp: Any) -> MaintenanceScheduleV368:
    """Compute maintenance schedule metrics (v368.0)."""

    # Contract fingerprint
    contract_sha = ""
    try:
        here = Path(__file__).resolve()
        contract_path = here.parents[2] / "contracts" / "maintenance_scheduling_v368_contract.json"
        contract_sha = _sha256_file(contract_path)
    except Exception:
        contract_sha = ""

    # Horizon (years)
    horizon = float(getattr(inp, "maintenance_planning_horizon_yr", float("nan")))
    if not _finite(horizon) or horizon <= 0.0:
        # default to plant design lifetime if present
        horizon = float(getattr(inp, "plant_design_lifetime_yr", 30.0) or 30.0)
    horizon = _clamp(horizon, 1.0, 100.0)

    # Baselines
    planned = float(getattr(inp, "planned_outage_base", 0.05) or 0.05)
    planned = _clamp(planned, 0.0, 0.50)

    # Forced outage baseline or trip-based proxy
    forced_base = float(getattr(inp, "forced_outage_base", 0.10) or 0.10)
    forced_base = _clamp(forced_base, 0.0, 0.50)
    trips = float(getattr(inp, "trips_per_year", 0.0) or 0.0)
    trip_days = float(getattr(inp, "trip_duration_days", 0.0) or 0.0)
    trip_frac = _clamp(max(trips, 0.0) * max(trip_days, 0.0) / 365.0, 0.0, 0.50)

    forced_mode = str(getattr(inp, "forced_outage_mode_v368", "max"))
    fm = forced_mode.strip().lower()
    if fm == "baseline":
        forced = forced_base
    elif fm == "trips":
        forced = trip_frac
    else:
        # default: conservative max
        forced = max(forced_base, trip_frac)
    forced = _clamp(forced, 0.0, 0.50)

    # Replacement scheduling
    comps = _component_specs(out, inp)
    policy = str(getattr(inp, "maintenance_bundle_policy", "independent"))
    overhead = float(getattr(inp, "maintenance_bundle_overhead_days", 7.0) or 7.0)
    overhead = _clamp(overhead, 0.0, 90.0)

    pol = policy.strip().lower()
    if pol in ("independent", "none"):
        repl, events = _schedule_independent(comps)
        pol_used = "independent"
    else:
        repl, events = _schedule_bundled(comps, bundle_policy=policy, overhead_days=overhead)
        pol_used = pol

    repl = _clamp(repl, 0.0, 0.90)

    # Total outage and availability
    outage_total = _clamp(planned + forced + repl, 0.0, 0.95)
    avail = _clamp(1.0 - outage_total, 0.0, 1.0)

    # Net generation
    Pnet = float(out.get("P_e_net_MW", float("nan")))
    duty = float(out.get("duty_factor", 1.0))
    duty = _clamp(duty if _finite(duty) else 1.0, 0.0, 1.0)
    if _finite(Pnet):
        net_mwh = max(Pnet, 0.0) * 8760.0 * avail * duty
    else:
        net_mwh = float("nan")

    # Replacement cost rate
    repl_cost = _annualized_replacement_cost_rate(out, inp)

    return MaintenanceScheduleV368(
        schema_version="v368.0",
        contract_sha256=str(contract_sha),
        planning_horizon_yr=float(horizon),
        bundle_policy=str(pol_used),
        bundle_overhead_days=float(overhead),
        planned_outage_frac=float(planned),
        forced_outage_frac=float(forced),
        replacement_outage_frac=float(repl),
        outage_total_frac=float(outage_total),
        availability=float(avail),
        net_electric_MWh_per_year=float(net_mwh),
        replacement_cost_MUSD_per_year=float(repl_cost),
        events=tuple(events),
    )
