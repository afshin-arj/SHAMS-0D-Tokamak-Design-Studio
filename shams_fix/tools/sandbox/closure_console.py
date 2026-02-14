"""SHAMS Reactor Design Forge — Closure Console

Explicit plant/accounting closure computed *from frozen truth outputs*.

Epistemic rules:
- Never modifies evaluator physics or constraints.
- Produces derived bookkeeping only.
- If required keys are missing, returns an explanatory bundle (no crashes).

This module is intentionally lightweight: it provides the bookkeeping that
users historically reach for PROCESS to obtain, but remains audit-clean.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ClosureEnvelope:
    name: str  # Optimistic / Nominal / Conservative
    scale_capex: float
    scale_opex: float


ENVELOPES = {
    "Optimistic": ClosureEnvelope("Optimistic", scale_capex=0.85, scale_opex=0.85),
    "Nominal": ClosureEnvelope("Nominal", scale_capex=1.00, scale_opex=1.00),
    "Conservative": ClosureEnvelope("Conservative", scale_capex=1.25, scale_opex=1.25),
}


def _get_num(d: Dict[str, Any], key: str) -> Optional[float]:
    v = d.get(key)
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def compute_closure_bundle(outputs: Dict[str, Any], cost_proxy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Compute an explicit closure bundle.

    Parameters
    ----------
    outputs:
        Frozen evaluator outputs (dict). We do not assume a fixed schema; we
        opportunistically read keys when available.
    cost_proxy:
        Optional cost proxy dict (e.g. from src.economics.cost.cost_proxies).

    Returns
    -------
    dict
        A closure bundle with gross/recirc/net electric where possible, and
        economics envelopes (O/N/C) based on cost proxies.
    """

    outputs = outputs or {}
    cost_proxy = cost_proxy or {}

    # Try several common keys for power numbers.
    p_gross = (
        _get_num(outputs, "P_e_gross_MW")
        or _get_num(outputs, "P_e_gross")
        or _get_num(outputs, "P_gross_e_MW")
    )
    p_recirc = (
        _get_num(outputs, "P_recirc_MW")
        or _get_num(outputs, "P_e_recirc_MW")
        or _get_num(outputs, "P_recirc_e_MW")
    )
    p_net = (
        _get_num(outputs, "P_e_net_MW")
        or _get_num(outputs, "P_net_e_MW")
        or _get_num(outputs, "P_net_MW")
    )

    # If net isn't provided, compute if possible.
    if p_net is None and p_gross is not None and p_recirc is not None:
        p_net = p_gross - p_recirc

    # Recirculation breakdown (best-effort).
    recirc_breakdown = {
        "cryo_MW": _get_num(outputs, "P_cryo_e_MW") or _get_num(outputs, "P_cryo_MW"),
        "current_drive_MW": _get_num(outputs, "P_cd_e_MW") or _get_num(outputs, "P_cd_MW"),
        "aux_MW": _get_num(outputs, "P_aux_e_MW") or _get_num(outputs, "P_aux_MW"),
        "balance_of_plant_MW": _get_num(outputs, "P_bop_e_MW") or _get_num(outputs, "P_bop_MW"),
    }
    recirc_breakdown = {k: v for k, v in recirc_breakdown.items() if v is not None}

    # Economics: use cost proxies if present.
    capex = _get_num(cost_proxy, "CAPEX_proxy")
    opex = _get_num(cost_proxy, "OPEX_proxy")
    lcoe = _get_num(cost_proxy, "LCOE_proxy") or _get_num(cost_proxy, "COE_proxy")

    envelopes = {}
    for nm, env in ENVELOPES.items():
        envelopes[nm] = {
            "CAPEX_proxy": float(capex) * env.scale_capex if capex is not None else None,
            "OPEX_proxy": float(opex) * env.scale_opex if opex is not None else None,
            "LCOE_proxy": float(lcoe) * (0.5 * (env.scale_capex + env.scale_opex)) if lcoe is not None else None,
            "assumptions": {
                "scale_capex": env.scale_capex,
                "scale_opex": env.scale_opex,
                "note": "Envelope scaling applies only to proxies; it does not modify truth outputs.",
            },
        }

    ok = any(v is not None for v in [p_gross, p_recirc, p_net])
    reason = None
    if not ok:
        reason = "Missing power keys in evaluator outputs (expected one of P_e_gross_MW/P_recirc_MW/P_e_net_MW)."

    return {
        "schema": "shams.reactor_design_forge.closure_bundle.v1",
        "ok": bool(ok),
        "reason": reason,
        "gross_electric_MW": p_gross,
        "recirc_electric_MW": p_recirc,
        "net_electric_MW": p_net,
        "recirc_breakdown_MW": recirc_breakdown,
        "economics_envelopes": envelopes,
        "raw_cost_proxy": cost_proxy,
    }


# --- Backward/compat import surface ---
def closure_console(outputs: Dict[str, Any], cost_proxy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Compatibility wrapper.

    Some UI builds import `closure_console` as a callable. The authoritative
    implementation is :func:`compute_closure_bundle`.
    """

    return compute_closure_bundle(outputs=outputs, cost_proxy=cost_proxy)
