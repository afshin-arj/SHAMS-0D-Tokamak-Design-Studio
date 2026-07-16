"""Authority overlay quick-toggle definitions (Streamlit dashboard parity)."""

from __future__ import annotations

from typing import List, Tuple

from ui_nicegui.lib.pd_panel_labels import overlay_caption, overlay_display_label

try:
    from schema.governance_presets import is_reactor_intent, preset_overlay_defaults
except ImportError:
    from src.schema.governance_presets import is_reactor_intent, preset_overlay_defaults

# (session.overlay key, display label, tooltip)
_AUTHORITY_FIELDS: List[Tuple[str, str]] = [
    ("include_transport_envelope_v396", "Min/max τE spread across multiple confinement scaling laws."),
    ("include_profile_contracts_v397", "Profile shape, q0/q95 proxies, and bootstrap localization bounds."),
    ("include_control_stability_authority_v398", "VS budget, VDE headroom, and RWM proximity."),
    ("include_impurity_v399", "Multi-species impurity radiation partition."),
    ("include_magnet_technology_authority_v400", "Field, current density, and stress margins vs coil limits."),
    ("include_neutronics_materials_library_v403", "Activation inventories, dose rates, and replacement catalogs."),
    ("include_structural_life_authority_v404", "Component lifetime under cyclic thermal and mechanical loads."),
    ("include_nuclear_data_authority_v407", "Cross-section and decay-data provenance for neutronics."),
    ("include_authority_dominance_v402", "Ranks which constraint family binds the point design."),
    ("include_elm_transient_heat_v409", "Transient heat-flux envelope from ELM energy dumps."),
    ("cd_mix_enable", "Split launched CD power across ECCD/LHCD/NBI/ICRF channels."),
    ("include_magnet_sc_system_authority_v410", "TF/PF/CS superconducting system margins beyond v400 (proxy overlay)."),
    ("include_machine_build_authority_v412", "Radial / machine-build closure: layer stack, clearances, outboard envelope (proxy)."),
    ("include_tritium_tight_closure", "Strict tritium balance without breeding slack."),
]

AUTHORITY_OVERLAY_TOGGLES: List[Tuple[str, str, str]] = [
    (field, overlay_display_label(field), overlay_caption(field) or tip)
    for field, tip in _AUTHORITY_FIELDS
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
        return "Reactor intent: tritium tight closure and ELM screening suggested ON."
    return ""
