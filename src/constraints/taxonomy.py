from __future__ import annotations

"""Constraint taxonomy + deterministic metadata enrichment.

SHAMS Scan Lab uses dominant-constraint cartography with mechanism overlays.
This module provides a *single* place to map constraint records to:

- mechanism_group: {PLASMA, EXHAUST, MAGNETS, NEUTRONICS, COST, CONTROL, GENERAL}
- subsystem: authority-contract key used by provenance.authority
- authority_tier: proxy | semi-authoritative | authoritative
- validity_domain: short domain note (from authority contracts when available)

Design rules:
- Additive only: never change feasibility or numerical values.
- Conservative: return "GENERAL" / "unknown" if mapping is ambiguous.
- Deterministic + side-effect free.
"""

from typing import Any, Dict, Optional, Tuple


_MECHANISM_GROUPS = (
    "PLASMA",
    "EXHAUST",
    "MAGNETS",
    "NEUTRONICS",
    "COST",
    "CONTROL",
    "GENERAL",
)


def _norm(s: Any) -> str:
    try:
        return str(s).strip()
    except Exception:
        return ""


def infer_mechanism_group(name: str, group: Optional[str] = None) -> str:
    """Infer a mechanism group from constraint name (and optional coarse group).

    This is intentionally heuristic but stable.
    """
    n = _norm(name).lower()
    g = _norm(group).lower()

    # If a group is already one of the canonical groups, respect it.
    if g.upper() in _MECHANISM_GROUPS:
        return g.upper()

    # If group is provided as legacy semantic label.
    if g in ("plasma", "profiles", "burn", "stability", "current"):
        return "PLASMA"
    if g in ("exhaust", "sol", "divertor", "pfc"):
        return "EXHAUST"
    if g in ("magnets", "tf", "pf", "structure", "engineering"):
        return "MAGNETS"
    if g in ("neutronics", "blanket", "shield", "tbr"):
        return "NEUTRONICS"
    if g in ("cost", "economics"):
        return "COST"
    if g in ("control", "vs", "pf_control"):
        return "CONTROL"

    if g in ("actuators", "actuator", "power_supplies", "powersupply"):
        return "CONTROL"

    # Name-based fallbacks
    if any(k in n for k in ["q95", "beta", "greenwald", "f_g", "h_required", "lh", "ignition", "m_ign", "bootstrap", "f_bs"]):
        return "PLASMA"
    if any(k in n for k in ["sol", "divertor", "q_div", "lambda_q", "p_sol", "detac", "target"]):
        return "EXHAUST"
    if any(k in n for k in ["tf", "hts", "b_peak", "stress", "sigma", "coil", "v_dump", "j_eng", "jop", "strain", "quench"]):
        return "MAGNETS"
    if any(k in n for k in ["tbr", "nwl", "neutron", "blanket", "shield", "nuclear"]):
        return "NEUTRONICS"
    if any(k in n for k in ["capex", "lcoe", "$", "cost", "opex"]):
        return "COST"
    if any(k in n for k in ["rwm", "vs control", "vs_", "pf waveform", "pf_", "bandwidth", "control"]):
        return "CONTROL"

    return "GENERAL"


def infer_subsystem(name: str, mechanism_group: str) -> str:
    """Infer authority-contract subsystem key.

    Subsystems are those used in provenance.authority.AUTHORITY_CONTRACTS.
    """
    n = _norm(name).lower()
    mg = _norm(mechanism_group).upper()

    if mg == "PLASMA":
        if "bootstrap" in n or "f_bs" in n or "i_bs" in n:
            return "current.bootstrap"
        if "lh" in n:
            return "plasma.confinement"
        if "h_required" in n or "h98" in n or "tau" in n:
            return "plasma.confinement"
        return "plasma.confinement"

    if mg == "EXHAUST":
        return "exhaust.divertor"

    if mg == "MAGNETS":
        # PF-related screens are still engineering proxies.
        if n.startswith("pf ") or n.startswith("pf_"):
            return "engineering.magnets"
        return "engineering.magnets"

    if mg == "NEUTRONICS":
        return "neutronics.proxy"

    if mg == "COST":
        return "plant.availability"  # closest proxy contract; cost contracts are handled separately

    if mg == "CONTROL":
        if "rwm" in n:
            return "control.rwm"
        if any(k in n for k in ("aux", "cd", "pf_", "pf ", "cs_", "cs ", "supply", "wallplug")):
            return "control.actuators"
        return "engineering.magnets"  # actuator envelopes are engineering/control proxies

    return "scan.cartography" if "cartography" in n else "plasma.confinement"


def authority_metadata(subsystem: str) -> Tuple[str, str]:
    """Return (tier, validity_domain) from authority contracts (best-effort)."""
    try:
        from provenance.authority import AUTHORITY_CONTRACTS  # type: ignore

        c = AUTHORITY_CONTRACTS.get(str(subsystem))
        if c is None:
            return "unknown", ""
        cd = c.to_dict()
        return str(cd.get("tier", "unknown")), str(cd.get("validity_domain", ""))
    except Exception:
        return "unknown", ""


def enrich_constraint_meta(
    name: str,
    *,
    group: Optional[str] = None,
    mechanism_group: Optional[str] = None,
    subsystem: Optional[str] = None,
) -> Dict[str, str]:
    """Return a small metadata dict for constraint enrichment."""
    mg = _norm(mechanism_group).upper() if mechanism_group else infer_mechanism_group(name, group)
    if mg not in _MECHANISM_GROUPS:
        mg = "GENERAL"

    ss = _norm(subsystem) if subsystem else infer_subsystem(name, mg)
    tier, dom = authority_metadata(ss)

    return {
        "mechanism_group": mg,
        "subsystem": ss,
        "authority_tier": tier,
        "validity_domain": dom,
    }
