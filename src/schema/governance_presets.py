"""Governance presets for reactor-grade defaults (PHYS-010)."""
from __future__ import annotations

import math
from typing import Any, Dict, Mapping, MutableMapping


def is_reactor_intent(design_intent: str) -> bool:
    s = str(design_intent or "").strip().lower()
    if s.startswith("experimental") or s.startswith("research") or "research" in s:
        return False
    return True


def tritium_tight_closure_default(design_intent: str) -> bool:
    """Reactor intent enables tight tritium closure by default (PHYS-010)."""
    return is_reactor_intent(design_intent)


def apply_governance_preset(
    fields: MutableMapping[str, Any],
    *,
    design_intent: str,
    preset: str = "auto",
) -> MutableMapping[str, Any]:
    """Apply intent-aware governance defaults without mutating frozen truth."""
    if preset == "off" or not is_reactor_intent(design_intent):
        return fields
    fields["include_tritium_tight_closure"] = True
    if not math.isfinite(float(fields.get("T_in_vessel_max_kg", float("nan")))):
        fields.setdefault("T_in_vessel_max_kg", 4.0)
    if not math.isfinite(float(fields.get("T_total_inventory_max_kg", float("nan")))):
        fields.setdefault("T_total_inventory_max_kg", 12.0)
    if not math.isfinite(float(fields.get("TBR_self_sufficiency_margin", float("nan")))):
        fields.setdefault("TBR_self_sufficiency_margin", 0.05)
    return fields


def preset_overlay_defaults(design_intent: str) -> Dict[str, bool]:
    """Suggested overlay toggles for authority dashboard."""
    reactor = is_reactor_intent(design_intent)
    return {
        "include_tritium_tight_closure": reactor,
        "include_elm_transient_heat_v409": reactor,
        "cd_mix_enable": False,
    }
