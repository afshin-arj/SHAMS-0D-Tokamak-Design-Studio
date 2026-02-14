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

    Deterministic algebraic bookkeeping; no dynamic simulation.

    Inputs (from inp_dict, defaults):
    - availability (0..1) used for annualization only
    - T_reserve_days (default 3)
    - T_processing_margin (default 1.25)
    - T_inventory_min_kg (optional minimum inventory contract, NaN disables)
    - T_processing_capacity_min_g_per_day (optional minimum processing capacity, NaN disables)

    v350.0 tight closure (optional; off by default):
    - include_tritium_tight_closure
    - T_processing_delay_days
    - T_in_vessel_max_kg
    - T_total_inventory_max_kg
    - T_startup_inventory_kg
    - T_loss_fraction (applied to TBR_eff)
    - TBR_self_sufficiency_margin (requires TBR_eff >= 1 + margin)

    Limits for constraints are returned in the output dictionary so
    ``evaluate_constraints(outputs=...)`` can enforce them without
    referencing mutable input state.
    """

    Pfus = _f(out.get("Pfus_total_MW", out.get("Pfus_MW", float("nan"))))
    if not math.isfinite(Pfus) or Pfus < 0.0:
        Pfus = 0.0

    # Burn throughput
    T_burn_kg_per_day = Pfus * T_KG_PER_DAY_PER_MW_FUS

    # Reserve inventory
    reserve_days = _f(inp_dict.get("T_reserve_days", 3.0))
    if not math.isfinite(reserve_days) or reserve_days < 0.0:
        reserve_days = 3.0
    if reserve_days > 365.0:
        reserve_days = 365.0
    T_inventory_reserve_kg = T_burn_kg_per_day * reserve_days

    # Processing requirement (throughput)
    processing_margin = _f(inp_dict.get("T_processing_margin", 1.25))
    if not math.isfinite(processing_margin) or processing_margin <= 0.0:
        processing_margin = 1.25
    processing_required_g_per_day = T_burn_kg_per_day * 1000.0 * processing_margin

    # Required TBR proxy (legacy): baseline 1.05 plus small reserve-days stress.
    TBR_required_legacy = _f(inp_dict.get("TBR_required_override", float("nan")))
    if not math.isfinite(TBR_required_legacy):
        TBR_required_legacy = 1.05 + 0.002 * reserve_days

    # v350.0: tight closure optional knobs
    include_tight = bool(inp_dict.get("include_tritium_tight_closure", False))

    delay_days = _f(inp_dict.get("T_processing_delay_days", 1.0))
    if not math.isfinite(delay_days) or delay_days < 0.0:
        delay_days = 0.0
    if delay_days > 30.0:
        delay_days = 30.0

    startup_inv = _f(inp_dict.get("T_startup_inventory_kg", float("nan")))
    if not math.isfinite(startup_inv) or startup_inv < 0.0:
        startup_inv = 0.0

    T_in_vessel_required_kg = T_burn_kg_per_day * delay_days
    T_total_inventory_required_kg = T_inventory_reserve_kg + T_in_vessel_required_kg + startup_inv

    # Effective TBR with optional loss tightening
    loss = _f(inp_dict.get("T_loss_fraction", float("nan")))
    validity: Dict[str, str] = {}
    if math.isfinite(loss):
        loss2 = min(max(loss, 0.0), 0.20)
        if loss2 != loss:
            validity["T_loss_fraction"] = "clamped"
        loss = loss2
    else:
        loss = float("nan")

    TBR = _f(out.get("TBR", float("nan")))
    TBR_eff = float("nan")
    if math.isfinite(TBR):
        if math.isfinite(loss):
            TBR_eff = TBR * (1.0 - loss)
        else:
            TBR_eff = TBR

    # Self-sufficiency tightening: require TBR_eff >= 1 + margin
    ss_margin = _f(inp_dict.get("TBR_self_sufficiency_margin", float("nan")))
    if math.isfinite(ss_margin):
        ss2 = min(max(ss_margin, 0.0), 0.50)
        if ss2 != ss_margin:
            validity["TBR_self_sufficiency_margin"] = "clamped"
        ss_margin = ss2
    else:
        ss_margin = float("nan")

    TBR_ss_required = float("nan")
    TBR_ss_margin_out = float("nan")
    if math.isfinite(ss_margin):
        TBR_ss_required = 1.0 + ss_margin
        if math.isfinite(TBR_eff):
            TBR_ss_margin_out = TBR_eff - TBR_ss_required

    # Tight required TBR: ensure both legacy contract and self-sufficiency are met.
    TBR_required = TBR_required_legacy
    if include_tight:
        if math.isfinite(TBR_ss_required):
            TBR_required = max(TBR_required, TBR_ss_required)
        # If losses are declared, raise required raw TBR so that TBR_eff meets required.
        if math.isfinite(loss):
            denom = max(1.0 - loss, 1e-12)
            TBR_required = TBR_required / denom

    TBR_margin = float("nan")
    if math.isfinite(TBR):
        TBR_margin = TBR - TBR_required

    cap_g_per_day = _f(inp_dict.get("T_processing_capacity_min_g_per_day", float("nan")))
    cap_margin = float("nan")
    if math.isfinite(cap_g_per_day):
        cap_margin = cap_g_per_day - processing_required_g_per_day

    # v350.0 caps (returned as outputs so constraints can act on them)
    T_in_vessel_max_kg = _f(inp_dict.get("T_in_vessel_max_kg", float("nan")))
    T_total_inventory_max_kg = _f(inp_dict.get("T_total_inventory_max_kg", float("nan")))

    # Contract fingerprint (if available)
    contract_sha = ""
    try:
        from contracts.tritium_fuelcycle_tight_closure_contract import CONTRACT_SHA256  # type: ignore
        contract_sha = str(CONTRACT_SHA256)
    except Exception:
        contract_sha = ""

    return {
        # Throughputs
        "T_burn_kg_per_day": float(T_burn_kg_per_day),
        "T_processing_required_g_per_day": float(processing_required_g_per_day),
        # Inventories
        "T_inventory_reserve_kg": float(T_inventory_reserve_kg),
        "T_inventory_required_kg": float(T_inventory_reserve_kg),  # backward compatible key
        "T_in_vessel_required_kg": float(T_in_vessel_required_kg),
        "T_startup_inventory_kg": float(startup_inv),
        "T_total_inventory_required_kg": float(T_total_inventory_required_kg),
        # TBR bookkeeping
        "TBR_required_fuelcycle": float(TBR_required),
        "TBR_margin_fuelcycle": float(TBR_margin),
        "TBR_eff_fuelcycle": float(TBR_eff),
        "TBR_self_sufficiency_required": float(TBR_ss_required),
        "TBR_self_sufficiency_margin": float(TBR_ss_margin_out),
        # Inputs / contracts (for constraint evaluation)
        "T_inventory_min_kg": _f(inp_dict.get("T_inventory_min_kg", float("nan"))),
        "T_processing_capacity_min_g_per_day": _f(inp_dict.get("T_processing_capacity_min_g_per_day", float("nan"))),
        "T_processing_capacity_margin_g_per_day": float(cap_margin),
        "include_tritium_tight_closure": float(1.0 if include_tight else 0.0),
        "T_processing_delay_days": float(delay_days),
        "T_in_vessel_max_kg": float(T_in_vessel_max_kg),
        "T_total_inventory_max_kg": float(T_total_inventory_max_kg),
        "T_loss_fraction": float(loss),
        "tritium_fuelcycle_contract_sha256": contract_sha,
        "tritium_fuelcycle_validity": str(validity) if validity else "",
    }
