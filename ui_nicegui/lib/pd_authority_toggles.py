"""Authority overlay quick-toggle definitions (Streamlit dashboard parity)."""

from __future__ import annotations

from typing import List, Tuple

try:
    from schema.governance_presets import is_reactor_intent, preset_overlay_defaults
except ImportError:
    from src.schema.governance_presets import is_reactor_intent, preset_overlay_defaults

# (session.overlay key, short tag, tooltip)
AUTHORITY_OVERLAY_TOGGLES: List[Tuple[str, str, str]] = [
    ("include_transport_envelope_v396", "v396", "Transport envelope spread authority"),
    ("include_profile_contracts_v397", "v397", "Profile / q0 / bootstrap localization proxies"),
    ("include_control_stability_authority_v398", "v398", "VS budget, VDE headroom, RWM proximity"),
    ("include_impurity_v399", "v399", "Multi-species impurity radiation partition"),
    ("include_magnet_technology_authority_v400", "v400", "Magnet technology margin stack"),
    ("include_neutronics_materials_library_v403", "v403", "Neutronics materials library"),
    ("include_structural_life_authority_v404", "v404", "Structural life / fatigue envelopes"),
    ("include_nuclear_data_authority_v407", "v407", "Nuclear data multi-group attenuation"),
    ("include_authority_dominance_v402", "v402", "Authority dominance screening"),
    ("include_elm_transient_heat_v409", "v409", "ELM / transient heat-load screening"),
    ("cd_mix_enable", "v408", "CD mix plant electric ledger"),
    ("include_tritium_tight_closure", "v405", "Tritium tight-closure inventory caps"),
]

AUTHORITY_TOGGLE_KEYS = [t[0] for t in AUTHORITY_OVERLAY_TOGGLES]


def default_overlay_bool(overlay: dict, field: str, design_intent: str) -> bool:
    if field in overlay:
        return bool(overlay[field])
    presets = preset_overlay_defaults(design_intent)
    if field in presets:
        return bool(presets[field])
    if field.endswith("_v400"):
        return False
    if field == "include_authority_dominance_v402":
        return True
    return False


def count_enabled(overlay: dict) -> tuple[int, int]:
    enabled = sum(1 for k in AUTHORITY_TOGGLE_KEYS if bool(overlay.get(k, False)))
    return enabled, len(AUTHORITY_TOGGLE_KEYS)


def reactor_intent_hint(design_intent: str) -> str:
    if is_reactor_intent(design_intent):
        return "Reactor intent: tritium tight closure and ELM screening suggested ON (PHYS-010)."
    return ""
