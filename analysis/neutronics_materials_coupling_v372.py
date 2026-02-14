from __future__ import annotations

"""Neutronics–Materials Coupling Authority (v372.0).

Governance-only, frozen-truth compliant.

This module *does not* modify the operating point. It consumes already-computed
neutronics scalars (e.g., neutron wall load) and explicit user-selected classes
(material class, spectrum class) to compute:

- effective DPA-rate proxy (material + spectrum conditioned)
- component-level damage proxies (first wall / blanket / structure)
- damage margin and lifetime proxy (if limits are provided)
- explicit pass/fail flags (for constraint ledger conversion)

No Monte Carlo. No iterative closure. Pure algebra + lookup tables.

All coefficients are screening-level and intentionally conservative. They are
stored as explicit tables here to keep auditability.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import math


@dataclass(frozen=True)
class MaterialClassParams:
    allowable_dpa: float         # [-] allowable cumulative damage (screening)
    T_min_C: float
    T_max_C: float
    sensitivity: float           # multiplier on DPA rate (material vulnerability proxy)


@dataclass(frozen=True)
class SpectrumClassParams:
    hardness: float              # multiplier on DPA rate (spectral hardness proxy)


# ---- Screening tables (explicit, deterministic) ---------------------------------
# Material classes are *governance labels*, not a substitute for detailed neutronics.
_MATERIALS: Dict[str, MaterialClassParams] = {
    # Reduced-activation ferritic/martensitic steel
    "RAFM": MaterialClassParams(allowable_dpa=50.0, T_min_C=250.0, T_max_C=550.0, sensitivity=1.00),
    # Tungsten facing components: higher brittleness / embrittlement risk -> lower allowable
    "W":    MaterialClassParams(allowable_dpa=20.0, T_min_C=600.0, T_max_C=1200.0, sensitivity=1.25),
    # SiC/SiC composites: high irradiation tolerance (screening), but windowed by temperature
    "SiC":  MaterialClassParams(allowable_dpa=80.0, T_min_C=400.0, T_max_C=1100.0, sensitivity=0.85),
    # ODS / advanced steels: improved tolerance (screening)
    "ODS":  MaterialClassParams(allowable_dpa=70.0, T_min_C=350.0, T_max_C=650.0, sensitivity=0.90),
}

_SPECTRA: Dict[str, SpectrumClassParams] = {
    "soft":    SpectrumClassParams(hardness=0.85),
    "nominal": SpectrumClassParams(hardness=1.00),
    "hard":    SpectrumClassParams(hardness=1.20),
}

# Component partition multipliers (proxy for flux attenuation away from FW)
_COMPONENT_FACTORS = {
    "fw": 1.00,
    "blanket": 0.45,
    "structure": 0.20,
}


def _norm_key(x: Any) -> str:
    return str(x).strip().upper().replace("-", "").replace("_", "")


def evaluate_neutronics_materials_coupling_v372(out: Dict[str, float], inp: Any) -> Dict[str, float]:
    """Evaluate the v372 coupling authority and return additional outputs.

    Required truth inputs (from `out`):
      - neutron_wall_load_MW_m2

    Optional:
      - neutronics_materials_fast_atten (if available from Neutronics & Materials Authority)
        used as a mild attenuation modifier for blanket/structure partitions.

    Governance inputs (from `inp`):
      - include_neutronics_materials_coupling_v372: bool
      - nm_material_class_v372: str (RAFM/W/SiC/ODS)
      - nm_spectrum_class_v372: str (soft/nominal/hard)
      - nm_T_oper_C_v372: float (NaN -> inferred/ignored)
      - dpa_rate_eff_max_v372: float (NaN disables explicit cap constraint)
      - damage_margin_min_v372: float (NaN disables explicit margin constraint)
    """

    enabled = bool(getattr(inp, "include_neutronics_materials_coupling_v372", False))
    if not enabled:
        return {"nm_coupling_v372_enabled": False}

    W = float(out.get("neutron_wall_load_MW_m2", float("nan")))
    # Convert MW/m^2 -> baseline DPA rate proxy [DPA/FPY]
    # Screening coefficient: 10 DPA/FPY per (MW/m^2)
    # (purely a monotonic proxy; actual mapping is spectrum/material dependent)
    base_dpa_rate = float("nan")
    if W == W and W >= 0.0:
        base_dpa_rate = 10.0 * W

    mat_key_raw = getattr(inp, "nm_material_class_v372", "RAFM")
    spec_key_raw = getattr(inp, "nm_spectrum_class_v372", "nominal")

    mat_key = _norm_key(mat_key_raw)
    spec_key = _norm_key(spec_key_raw)

    # Map normalized keys back to canonical table keys
    mat_map = {"RAFM": "RAFM", "W": "W", "SIC": "SiC", "ODS": "ODS"}
    spec_map = {"SOFT": "soft", "NOMINAL": "nominal", "HARD": "hard"}
    mat = _MATERIALS.get(mat_map.get(mat_key, "RAFM"), _MATERIALS["RAFM"])
    spec = _SPECTRA.get(spec_map.get(spec_key, "nominal"), _SPECTRA["nominal"])

    # Temperature handling: optional input; if NaN, we don't penalize (conservative neutrality).
    T = float(getattr(inp, "nm_T_oper_C_v372", float("nan")))
    in_window = float("nan")
    temp_penalty = 1.0
    if T == T:
        in_window = 1.0 if (mat.T_min_C <= T <= mat.T_max_C) else 0.0
        # If outside window, penalize allowable damage (reduce) conservatively
        if in_window < 0.5:
            temp_penalty = 0.5

    # Effective DPA rate
    dpa_rate_eff = float("nan")
    if base_dpa_rate == base_dpa_rate:
        dpa_rate_eff = base_dpa_rate * mat.sensitivity * spec.hardness

    # Optional attenuation modifier if an upstream fast attenuation exists.
    # For blanket/structure we scale down further when shielding is strong.
    fast_atten = float(out.get("neutronics_materials_fast_atten", float("nan")))
    atten_mod = 1.0
    if fast_atten == fast_atten and fast_atten > 0.0 and fast_atten <= 1.0:
        # Strong attenuation -> further reduce blanket/structure damage
        atten_mod = max(0.6, min(1.0, 0.6 + 0.4 * fast_atten))

    fw = float("nan")
    blanket = float("nan")
    structure = float("nan")
    if dpa_rate_eff == dpa_rate_eff:
        fw = dpa_rate_eff * _COMPONENT_FACTORS["fw"]
        blanket = dpa_rate_eff * _COMPONENT_FACTORS["blanket"] * atten_mod
        structure = dpa_rate_eff * _COMPONENT_FACTORS["structure"] * atten_mod

    allowable_dpa_eff = mat.allowable_dpa * temp_penalty
    lifetime_fpy = float("nan")
    if dpa_rate_eff == dpa_rate_eff and dpa_rate_eff > 0.0:
        lifetime_fpy = allowable_dpa_eff / dpa_rate_eff

    # Optional explicit constraints (NaN disables)
    dpa_max = float(getattr(inp, "dpa_rate_eff_max_v372", float("nan")))
    margin_min = float(getattr(inp, "damage_margin_min_v372", float("nan")))

    damage_margin = float("nan")
    pass_dpa = float("nan")
    pass_margin = float("nan")

    if dpa_rate_eff == dpa_rate_eff and dpa_max == dpa_max and dpa_max > 0.0:
        damage_margin = (dpa_max - dpa_rate_eff) / dpa_max
        pass_dpa = 1.0 if dpa_rate_eff <= dpa_max else 0.0
    if damage_margin == damage_margin and margin_min == margin_min:
        pass_margin = 1.0 if damage_margin >= margin_min else 0.0

    return {
        "nm_coupling_v372_enabled": True,
        "nm_material_class_v372": str(mat_map.get(mat_key, "RAFM")),
        "nm_spectrum_class_v372": str(spec_map.get(spec_key, "nominal")),
        "nm_T_oper_C_v372": float(T),
        "nm_temp_window_ok_v372": float(in_window),
        "dpa_rate_base_per_fpy_v372": float(base_dpa_rate),
        "dpa_rate_eff_per_fpy_v372": float(dpa_rate_eff),
        "fw_damage_proxy_v372": float(fw),
        "blanket_damage_proxy_v372": float(blanket),
        "structure_damage_proxy_v372": float(structure),
        "allowable_dpa_eff_v372": float(allowable_dpa_eff),
        "lifetime_fpy_v372": float(lifetime_fpy),
        "dpa_rate_eff_max_v372": float(dpa_max),
        "damage_margin_v372": float(damage_margin),
        "damage_margin_min_v372": float(margin_min),
        "nm_pass_dpa_cap_v372": float(pass_dpa),
        "nm_pass_margin_v372": float(pass_margin),
        "nm_coupling_contract_stamp_sha256": "b0e4dd3f3a8c0e8a2a5c7f1f0d5f02c9f0c4a9e6a8b0b14ed0cdbb0a9d4b7ad2",
    }
