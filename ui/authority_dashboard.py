"""Overlay authority toggle dashboard (UI Phase C + v418 extensions)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

try:
    from schema.governance_presets import is_reactor_intent, preset_overlay_defaults
except ImportError:
    from src.schema.governance_presets import is_reactor_intent, preset_overlay_defaults

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
    ("include_elm_transient_heat_v409", "v409", "ELM / transient heat-load screening"),
    ("cd_mix_enable", "v408", "CD mix plant electric ledger"),
    ("include_tritium_tight_closure", "v405", "Tritium tight-closure inventory caps"),
]

_OVERLAY_TOGGLES_FIELDS = [t[0] for t in _OVERLAY_TOGGLES]

try:
    from ui.point_inputs_factory import strip_point_input_knob_dupes
except ImportError:
    from point_inputs_factory import strip_point_input_knob_dupes


def merge_overlay_session_into_inputs(inp: Any, session_state: Any) -> Any:
    """Apply authority-dashboard session toggles to PointInputs before evaluate."""
    try:
        from dataclasses import asdict, fields
        from schema.inputs import PointInputs
    except ImportError:
        from dataclasses import asdict, fields
        from src.schema.inputs import PointInputs
    names = {f.name for f in fields(PointInputs)}
    overrides = {k: session_state[k] for k in _OVERLAY_TOGGLES_FIELDS if k in names and k in session_state}
    for k in ("transport_spread_ref_v402", "profile_peaking_p_ref_v402", "zeff_ref_max_v402"):
        if k in names and k in session_state:
            overrides[k] = session_state[k]
    if not overrides:
        return inp
    data = asdict(inp) if hasattr(inp, "__dataclass_fields__") else dict(inp)
    data.update(overrides)
    return PointInputs(**{k: v for k, v in data.items() if k in names})


def _default_bool(session_state: Any, field: str, design_intent: str) -> bool:
    if field in session_state:
        return bool(session_state[field])
    presets = preset_overlay_defaults(design_intent)
    if field in presets:
        return bool(presets[field])
    if field.endswith("_v400"):
        return False
    if field == "include_authority_dominance_v402":
        return True
    return False


def apply_overlay_dashboard_state(session_state: Any, state: Dict[str, bool]) -> None:
    """Write overlay toggle state back to session for PointInputs merge."""
    for field, enabled in state.items():
        session_state[field] = bool(enabled)


def render_v402_threshold_panel(
    session_state: Any,
    *,
    widget_key_prefix: str = "auth_dash",
) -> Dict[str, float]:
    """PHYS-003: v402 reference thresholds in authority dashboard."""
    st.markdown("##### Dominance reference thresholds")
    c1, c2, c3 = st.columns(3)
    with c1:
        transport_spread_ref_v402 = st.number_input(
            "Transport spread ref",
            min_value=1.1,
            value=float(session_state.get("transport_spread_ref_v402", 3.0) or 3.0),
            step=0.1,
            key=f"{widget_key_prefix}_transport_spread_ref_v402",
        )
    with c2:
        profile_peaking_p_ref_v402 = st.number_input(
            "Profile p-peaking ref",
            min_value=1.1,
            value=float(session_state.get("profile_peaking_p_ref_v402", 3.0) or 3.0),
            step=0.1,
            key=f"{widget_key_prefix}_profile_peaking_p_ref_v402",
        )
    with c3:
        zeff_ref_max_v402 = st.number_input(
            "Zeff ref max",
            min_value=1.1,
            value=float(session_state.get("zeff_ref_max_v402", 2.5) or 2.5),
            step=0.1,
            key=f"{widget_key_prefix}_zeff_ref_max_v402",
        )
    refs = {
        "transport_spread_ref_v402": float(transport_spread_ref_v402),
        "profile_peaking_p_ref_v402": float(profile_peaking_p_ref_v402),
        "zeff_ref_max_v402": float(zeff_ref_max_v402),
    }
    for k, v in refs.items():
        session_state[k] = v
    return refs


def render_profile_tau_peaking_panel(out: Dict[str, Any]) -> None:
    """Display τE peaking factor from v397 profile proxy (PHYS-002 UI)."""
    if not isinstance(out, dict) or not out:
        return
    factor = out.get("tau_e_profile_factor_v397", out.get("tau_e_density_peaking_factor_v397"))
    if factor in (None, float("nan")):
        if not float(out.get("include_profile_proxy_v397", out.get("profile_proxy_v397_enabled", 0)) or 0) > 0.5:
            st.caption("Profile transport proxy disabled — τE peaking factor not computed.")
        return
    try:
        f = float(factor)
        if f != f:
            return
        st.metric("τE profile peaking factor", f"{f:.3f}", help="PHYS-002: density/pressure peaking degrades volume-averaged τE proxy.")
        tau0 = out.get("tauE_s")
        if tau0 is not None:
            try:
                t0 = float(tau0)
                if t0 == t0 and f > 0:
                    st.caption(f"Baseline τE_s ≈ {t0:.3f} s (after peaking coupling when enabled).")
            except (TypeError, ValueError):
                pass
    except (TypeError, ValueError):
        pass


def render_overlay_authority_dashboard(
    session_state: Any,
    *,
    widget_key_prefix: str = "auth_dash",
    design_intent: Optional[str] = None,
) -> Dict[str, bool]:
    """Render overlay toggles; returns {field_name: enabled} and writes session."""
    intent = design_intent or str(session_state.get("design_intent", "Power Reactor (net-electric)"))
    st.markdown("#### Authority overlays")
    st.caption("Governance overlays only — frozen truth equations unchanged.")
    if is_reactor_intent(intent):
        st.caption("Reactor intent: tritium tight closure and ELM screening suggested ON (PHYS-010).")
    state: Dict[str, bool] = {}
    cols = st.columns(3)
    for i, (field, tag, tip) in enumerate(_OVERLAY_TOGGLES):
        with cols[i % 3]:
            default = _default_bool(session_state, field, intent)
            state[field] = st.checkbox(
                f"{tag}",
                value=default,
                key=f"{widget_key_prefix}_{field}",
                help=tip,
            )
    apply_overlay_dashboard_state(session_state, state)
    if state.get("include_authority_dominance_v402", False):
        render_v402_threshold_panel(session_state, widget_key_prefix=widget_key_prefix)
    return state
