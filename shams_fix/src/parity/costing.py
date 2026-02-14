from __future__ import annotations

"""PROCESS Parity Layer v1: costing block.

PROCESS-style studies often optimize for COE/LCOE. SHAMS keeps costing as an
explicit *optional layer*.

Implementation note
-------------------
SHAMS already includes a transparent cost proxy model in `src.economics.cost`.
This parity block simply exposes it in a stable shape for UI/reporting.
"""

from typing import Any, Dict

from economics.cost import cost_proxies


def parity_costing(inputs: Any, outputs: Dict[str, Any]) -> Dict[str, Any]:
    econ = cost_proxies(inputs, outputs)

    derived = {
        "CAPEX_MUSD": float(econ.get("CAPEX_proxy_MUSD", float("nan"))),
        "OPEX_MUSD_per_y": float(econ.get("OPEX_proxy_MUSD_per_y", float("nan"))),
        "COE_USD_per_MWh": float(econ.get("COE_proxy_USD_per_MWh", float("nan"))),
        "LCOE_USD_per_MWh": float(econ.get("LCOE_proxy_USD_per_MWh", float("nan"))),
        "NPV_cost_MUSD": float(econ.get("NPV_cost_proxy_MUSD", float("nan"))),
        "breakdown_MUSD": {
            # Prefer v356 component overlay when present; otherwise fall back to legacy 4-part split.
            "TF coils": float(econ.get("capex_tf_coils_MUSD", float("nan"))),
            "PF/CS": float(econ.get("capex_pf_cs_MUSD", float("nan"))),
            "Blanket+shield": float(econ.get("capex_blanket_shield_MUSD", float("nan"))),
            "Cryoplant": float(econ.get("capex_cryoplant_MUSD", float("nan"))),
            "BOP": float(econ.get("capex_bop_MUSD", float("nan"))),
            "Buildings": float(econ.get("capex_buildings_MUSD", float("nan"))),
            "Heating/CD": float(econ.get("capex_heating_cd_MUSD", float("nan"))),
            "Tritium plant": float(econ.get("capex_tritium_plant_MUSD", float("nan"))),
        },
    }

    # Clean NaNs; if overlay not available, fallback to legacy keys.
    bd = dict(derived.get("breakdown_MUSD", {}) or {})
    if not any((v == v) and abs(v) > 0 for v in bd.values()):
        derived["breakdown_MUSD"] = {
            "magnets": float(econ.get("cost_magnet_MUSD", 0.0)),
            "blanket": float(econ.get("cost_blanket_MUSD", 0.0)),
            "bop": float(econ.get("cost_bop_MUSD", 0.0)),
            "cryo": float(econ.get("cost_cryo_MUSD", 0.0)),
        }
    else:
        derived["breakdown_MUSD"] = {k: float(v) for k, v in bd.items() if (v == v)}

    assumptions = {
        "note": "Proxy economics for relative comparisons. See docs/cost_calibration_default.json and src/economics/cost.py for details.",
        "model": "SHAMS economics proxy (PROCESS-like objective layer)",
    }
    # keep full economics for artifact consumers
    return {"derived": derived, "assumptions": assumptions, "raw": econ}


def parity_costing_envelope(
    inputs: Any,
    outputs: Dict[str, Any],
    *,
    optimistic: Dict[str, float] | None = None,
    conservative: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    """Compute a simple optimistic/nominal/conservative envelope for economics proxies.

    This is a transparency feature (Phase-2): it does **not** change frozen truth.
    We avoid hidden complexity: we take the nominal cost proxy outputs and apply
    explicit multipliers to CAPEX/OPEX and capacity factor.

    Parameters
    ----------
    optimistic / conservative:
        Multipliers dict with optional keys:
        - capex_mult
        - opex_mult
        - cf_add  (additive delta to capacity factor / availability proxy)

    Returns
    -------
    Dict with:
        {"nominal": {...}, "optimistic": {...}, "conservative": {...}, "assumptions": {...}}
    """
    base = parity_costing(inputs, outputs)
    d = dict(base.get("derived", {}))
    raw = base.get("raw", {})
    econ = raw.get("_economics", {}) if isinstance(raw, dict) else {}
    a = dict((econ.get("assumptions") or {})) if isinstance(econ, dict) else {}

    # nominal
    capex = float(d.get("CAPEX_MUSD", float("nan")))
    opex = float(d.get("OPEX_MUSD_per_y", float("nan")))
    net_MWe = float((econ.get("net_electric_MWe") if isinstance(econ, dict) else float("nan")) or float("nan"))

    fcr = float(a.get("fixed_charge_rate", 0.10))
    cf = float(a.get("availability", 0.0) or 0.0)
    if cf <= 0:
        cf = float(a.get("capacity_factor", 0.75))

    def lcoe_usd_per_mwh(capex_musd: float, opex_musd_y: float, cf_val: float) -> float:
        if not (net_MWe > 0 and cf_val > 0):
            return float("nan")
        annual_MWh = net_MWe * 8760.0 * cf_val
        annual_cost_MUSD = fcr * capex_musd + opex_musd_y
        return (annual_cost_MUSD * 1e6) / annual_MWh

    nominal = {
        "CAPEX_MUSD": capex,
        "OPEX_MUSD_per_y": opex,
        "capacity_factor": cf,
        "LCOE_USD_per_MWh": lcoe_usd_per_mwh(capex, opex, cf),
    }

    optimistic = optimistic or {"capex_mult": 0.85, "opex_mult": 0.90, "cf_add": 0.05}
    conservative = conservative or {"capex_mult": 1.15, "opex_mult": 1.10, "cf_add": -0.05}

    def apply(mult: Dict[str, float]) -> Dict[str, float]:
        cap = capex * float(mult.get("capex_mult", 1.0))
        op = opex * float(mult.get("opex_mult", 1.0))
        cf2 = min(0.95, max(0.05, cf + float(mult.get("cf_add", 0.0))))
        return {
            "CAPEX_MUSD": cap,
            "OPEX_MUSD_per_y": op,
            "capacity_factor": cf2,
            "LCOE_USD_per_MWh": lcoe_usd_per_mwh(cap, op, cf2),
        }

    return {
        "nominal": nominal,
        "optimistic": apply(optimistic),
        "conservative": apply(conservative),
        "assumptions": {
            "note": "Explicit envelope on cost proxies (multipliers on CAPEX/OPEX and capacity factor).",
            "nominal_assumptions": a,
            "optimistic_multipliers": optimistic,
            "conservative_multipliers": conservative,
        },
    }
