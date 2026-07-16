"""PointInputs factory helpers (no Streamlit dependency)."""
from __future__ import annotations

from dataclasses import fields
from typing import Any, Dict, Tuple

try:
    from schema.inputs import PointInputs
except ImportError:
    from src.schema.inputs import PointInputs

_POINTINPUTS_FIELDS = {f.name for f in fields(PointInputs)}

# Overlay / authority keys often duplicated between preset dicts and explicit kwargs.
_POINT_INPUT_KNOB_DEDUP_KEYS: Tuple[str, ...] = (
    "include_transport_envelope_v396",
    "include_profile_contracts_v397",
    "include_control_stability_authority_v398",
    "include_impurity_v399",
    "include_magnet_technology_authority_v400",
    "include_magnet_sc_system_authority_v410",
    "include_neutronics_materials_library_v403",
    "include_structural_life_authority_v404",
    "include_nuclear_data_authority_v407",
    "include_authority_dominance_v402",
    "include_elm_transient_heat_v409",
    "cd_mix_enable",
    "include_tritium_tight_closure",
    "vs_budget_margin_min_v398",
    "vde_headroom_min_v398",
    "rwm_proximity_index_max_v398",
    "magnet_margin_min_v400",
    "b_margin_min_v400",
    "j_margin_min_v400",
    "stress_margin_min_v400",
    "sc_margin_min_v400",
    "t_margin_min_v400",
    "p_tf_ohmic_margin_min_v400",
    "magnet_system_margin_min_v410",
    "tf_family_margin_min_v410",
    "pf_family_margin_min_v410",
    "cs_family_margin_min_v410",
    "transport_spread_ref_v402",
    "profile_peaking_p_ref_v402",
    "zeff_ref_max_v402",
    "include_control_contracts",
)


def strip_point_input_knob_dupes(knobs: Dict[str, Any] | None, *also_strip: str) -> Dict[str, Any]:
    """Return a copy of UI knob dict with keys removed that are passed explicitly elsewhere."""
    out = dict(knobs or {})
    for k in _POINT_INPUT_KNOB_DEDUP_KEYS:
        out.pop(k, None)
    for k in also_strip:
        out.pop(k, None)
    return out


def make_point_inputs(extras: dict | None = None, /, **kwargs) -> PointInputs:
    """Create PointInputs; merge ``extras`` with explicit kwargs (kwargs win)."""
    merged: dict = dict(extras or {})
    merged.update(kwargs)
    filtered = {k: v for k, v in merged.items() if k in _POINTINPUTS_FIELDS}
    return PointInputs(**filtered)


make_point_inputs_from = make_point_inputs
_make_point_inputs_safe = make_point_inputs
