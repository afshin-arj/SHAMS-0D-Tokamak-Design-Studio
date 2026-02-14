"""DSG Bindings — adopt DSG nodes into UI input widgets deterministically.

Exploration-layer only: mutates Streamlit session_state keys used by UI widgets.
Does not change frozen evaluator truth.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Stable Point Designer widget keys (must match ui/app.py PD_KEYS mapping)
_PD_KEYS: Dict[str, str] = {
    "R0_m": "pd_R0_m",
    "a_m": "pd_a_m",
    "kappa": "pd_kappa",
    "delta": "pd_delta",
    "Bt_T": "pd_Bt_T",
    "Ti_keV": "pd_Ti_keV",
    "Paux_MW": "pd_Paux_MW",
    "Ip_lo": "pd_Ip_lo",
    "Ip_hi": "pd_Ip_hi",
    "fG_lo": "pd_fG_lo",
    "fG_hi": "pd_fG_hi",
    "Ti_over_Te": "pd_Ti_over_Te",
    "Paux_for_Q": "pd_Paux_for_Q",
    "magnet_technology": "pd_magnet_technology",
    "Tcoil_K": "pd_Tcoil_K",
    "profile_mode": "pd_profile_mode",
    "profile_alpha_T": "pd_profile_alpha_T",
    "profile_alpha_n": "pd_profile_alpha_n",
    "profile_shear_shape": "pd_profile_shear_shape",
    "pedestal_enabled": "pd_pedestal_enabled",
    "pedestal_width_a": "pd_pedestal_width_a",
}


def adopt_active_node_into_point_designer(*, g: Any, node_id: Optional[str] = None) -> bool:
    """Adopt DSG node inputs into Point Designer widget keys + last_point_inp.

    Returns True if adoption succeeded.
    """
    if g is None:
        return False
    import streamlit as st
    node_id = str(node_id or st.session_state.get("dsg_selected_node_id") or getattr(g, "active_node_id", "") or "")
    if not node_id:
        return False

    # Convert to PointInputs if available
    try:
        from phase1_core import PointInputs
    except Exception:
        PointInputs = None

    base = None
    if PointInputs is not None:
        try:
            base = g.to_point_inputs(node_id, PointInputs)
        except Exception:
            base = None

    # Push last_point_inp (Systems baseline uses this)
    if base is not None:
        st.session_state["last_point_inp"] = base

    # Push to Point Designer widgets from decoded dict (works even if PointInputs missing)
    try:
        data = g.inputs_dict(node_id)
    except Exception:
        data = {}

    if not data:
        return False

    def _set(k: str, v: Any) -> None:
        if k:
            st.session_state[k] = v

    # Core geometric/plasma knobs
    for fld in ["R0_m", "a_m", "kappa", "Bt_T", "Ti_keV", "Paux_MW"]:
        if fld in data and fld in _PD_KEYS:
            try:
                _set(_PD_KEYS[fld], float(data[fld]))
            except Exception:
                pass

    # delta optional
    if "delta" in data:
        try:
            _set(_PD_KEYS["delta"], float(data["delta"]))
        except Exception:
            pass

    # Ip/fG are bounds in Point Designer (lo/hi)
    try:
        ip = float(data.get("Ip_MA", 0.0))
        if ip > 0:
            _set(_PD_KEYS["Ip_lo"], max(0.1, 0.80 * ip))
            _set(_PD_KEYS["Ip_hi"], max(0.2, 1.20 * ip))
    except Exception:
        pass

    try:
        fg = float(data.get("fG", 0.0))
        _set(_PD_KEYS["fG_lo"], max(0.0, fg - 0.20))
        _set(_PD_KEYS["fG_hi"], min(2.0, fg + 0.20))
    except Exception:
        pass

    # Aux/Q and Ti/Te
    try:
        _set(_PD_KEYS["Paux_for_Q"], float(data.get("Paux_MW", 0.0)))
    except Exception:
        pass
    try:
        _set(_PD_KEYS["Ti_over_Te"], float(data.get("Ti_over_Te", 1.0)))
    except Exception:
        pass

    # Magnet tech axis
    try:
        _set(_PD_KEYS["magnet_technology"], str(data.get("magnet_technology", "HTS_REBCO") or "HTS_REBCO"))
    except Exception:
        pass
    try:
        _set(_PD_KEYS["Tcoil_K"], float(data.get("Tcoil_K", 20.0)))
    except Exception:
        pass

    # Profile knobs (optional)
    for fld in ["profile_mode","profile_alpha_T","profile_alpha_n","profile_shear_shape","pedestal_enabled","pedestal_width_a"]:
        if fld in data and fld in _PD_KEYS:
            try:
                val = data[fld]
                if isinstance(val, bool):
                    _set(_PD_KEYS[fld], bool(val))
                else:
                    _set(_PD_KEYS[fld], float(val))
            except Exception:
                pass

    return True
