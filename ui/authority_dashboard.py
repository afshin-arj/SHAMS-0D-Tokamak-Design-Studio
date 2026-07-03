"""Overlay authority toggle dashboard (UI Phase C)."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import streamlit as st

_OVERLAY_TOGGLES: List[Tuple[str, str, str]] = [
    ("include_transport_envelope_v396", "v396", "Transport envelope spread authority"),
    ("include_profile_contracts_v397", "v397", "Profile / q0 / bootstrap localization proxies"),
    ("include_control_stability_authority_v398", "v398", "VS budget, VDE headroom, RWM proximity"),
    ("include_impurity_v399", "v399", "Multi-species impurity radiation partition"),
    ("include_magnet_technology_authority_v400", "v400", "Magnet technology margin stack"),
    ("include_neutronics_materials_library_v403", "v403", "Neutronics materials library"),
    ("include_structural_life_authority_v404", "v404", "Structural life / fatigue envelopes"),
    ("include_nuclear_data_authority_v407", "v407", "Nuclear data multi-group attenuation"),
    ("include_authority_dominance_v402", "v402", "Authority dominance screening"),
]


def render_overlay_authority_dashboard(
    session_state: Any,
    *,
    widget_key_prefix: str = "auth_dash",
) -> Dict[str, bool]:
    """Render overlay toggles; returns {field_name: enabled}."""
    st.markdown("#### Authority overlays")
    st.caption("Governance overlays only — frozen truth equations unchanged.")
    state: Dict[str, bool] = {}
    cols = st.columns(3)
    for i, (field, tag, tip) in enumerate(_OVERLAY_TOGGLES):
        with cols[i % 3]:
            default = bool(session_state.get(field, field.endswith("_v400")))
            state[field] = st.checkbox(
                f"{tag}",
                value=default,
                key=f"{widget_key_prefix}_{field}",
                help=tip,
            )
    return state
