"""Fuel-cycle / tritium admissibility proxies (non-time-domain).

Deterministic algebraic bookkeeping; no dynamic simulation.
This module provides conservative, transparent proxies intended for
governance and trade studies.

Definitions:
- Tritium burn rate derived from fusion power assuming D-T only.
  17.6 MeV per reaction, consumes one tritium nucleus per reaction.

1 MW fusion -> ~1.54e-4 kg T / day.

All computations are NaN-safe.
"""

from __future__ import annotations

from typing import Any, Dict
import math

T_KG_PER_DAY_PER_MW_FUS = 1.54e-4  # kg/day per MW fusion (D-T)


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def compute_tritium_authority(out: Dict[str, Any], inp_dict: Dict[str, Any]) -> Dict[str, float]:
    """Compute fuel-cycle tritium ledger.

    Inputs (from inp_dict, defaults):
    - availability (0..1) used for annualization only
    - T_reserve_days (default 3)
    - T_processing_margin (default 1.25)
    - T_inventory_min_kg (optional cap, NaN disables)
    - T_processing_capacity_min_g_per_day (optional min, NaN disables)
    - TBR (from out) is compared to a computed required TBR for fuel-cycle
    """
    Pfus = _f(out.get("Pfus_total_MW", out.get("Pfus_MW", float("nan"))))
    if not math.isfinite(Pfus) or Pfus < 0.0:
        Pfus = 0.0

    T_burn_kg_per_day = Pfus * T_KG_PER_DAY_PER_MW_FUS

    reserve_days = _f(inp_dict.get("T_reserve_days", 3.0))
    if not math.isfinite(reserve_days) or reserve_days < 0.0:
        reserve_days = 3.0
    inventory_required_kg = T_burn_kg_per_day * reserve_days

    processing_margin = _f(inp_dict.get("T_processing_margin", 1.25))
    if not math.isfinite(processing_margin) or processing_margin <= 0.0:
        processing_margin = 1.25
    processing_required_g_per_day = T_burn_kg_per_day * 1000.0 * processing_margin

    # Required TBR proxy: baseline 1.05 plus reserve/processing stress
    # This is a *contract* proxy; users can override via TBR_required_override if desired.
    TBR_required = _f(inp_dict.get("TBR_required_override", float("nan")))
    if not math.isfinite(TBR_required):
        # 1.05 accounts for losses; add small term for reserve_days (very conservative proxy)
        TBR_required = 1.05 + 0.002 * reserve_days

    TBR = _f(out.get("TBR", float("nan")))
    TBR_margin = float("nan")

    cap_g_per_day = _f(inp_dict.get("T_processing_capacity_min_g_per_day", float("nan")))
    cap_margin = float("nan")
    if math.isfinite(cap_g_per_day):
        cap_margin = cap_g_per_day - processing_required_g_per_day

    if math.isfinite(TBR):
        TBR_margin = TBR - TBR_required

    return {
        "T_burn_kg_per_day": float(T_burn_kg_per_day),
        "T_inventory_required_kg": float(inventory_required_kg),
        "T_processing_required_g_per_day": float(processing_required_g_per_day),
        "TBR_required_fuelcycle": float(TBR_required),
        "TBR_margin_fuelcycle": float(TBR_margin),
        "T_inventory_min_kg": _f(inp_dict.get("T_inventory_min_kg", float("nan"))),
        "T_processing_capacity_min_g_per_day": _f(inp_dict.get("T_processing_capacity_min_g_per_day", float("nan"))),
        "T_processing_capacity_margin_g_per_day": float(cap_margin),
    }