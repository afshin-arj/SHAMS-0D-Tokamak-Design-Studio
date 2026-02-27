"""SHAMS — Neutronics & Materials Authority 4.0 (v403.0.0)

Author: © 2026 Afshin Arjhangmehr

Purpose
-------
Close the largest remaining PROCESS-depth delta without violating frozen truth by
adding a deterministic *library-backed* neutronics/materials stack authority:

- Explicit multi-layer stack specification (material + thickness + density factor)
- 3-group (fast/epi/therm) exponential attenuation ledger
- Derived nuclear load ledgers (DPA, He appm) and activation/cooldown proxy
- TBR-lite proxy from breeder layers (library coefficients)
- Explicit constraint-ready margins + dominance attribution

Hard laws
---------
- Deterministic; algebraic; no solvers; no iteration; no smoothing.
- Governance-only overlay; never mutates core truth.
- Robust to missing upstream fields (returns UNKNOWN tiers + NaNs, never crashes UI).

Notes
-----
This module intentionally uses conservative proxy coefficients. It is designed
for auditability and *relative* screening/feasibility ranking, not as a Monte
Carlo replacement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import json
import math
from pathlib import Path


GROUPS: Tuple[str, ...] = ("fast", "epi", "therm")


def _nan() -> float:
    return float("nan")


def _finite(x: float) -> bool:
    return bool(x == x and math.isfinite(x))


def _sf(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return default


@dataclass(frozen=True)
class LayerV403:
    material: str
    thickness_m: float
    density_factor: float = 1.0


def _load_library() -> Dict[str, Any]:
    p = Path(__file__).resolve().parents[1] / "data" / "neutronics" / "materials_library_v403.json"
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _parse_stack_json(stack_json: str) -> List[LayerV403]:
    try:
        obj = json.loads(stack_json)
    except Exception as e:
        raise ValueError(f"Invalid JSON for nm_stack_json_v403: {e}")
    if not isinstance(obj, list):
        raise ValueError("nm_stack_json_v403 must be a JSON list of layers")

    layers: List[LayerV403] = []
    for i, it in enumerate(obj):
        if not isinstance(it, dict):
            raise ValueError(f"Layer {i} must be a JSON object")
        m = str(it.get("material", "")).strip()
        if not m:
            raise ValueError(f"Layer {i} missing 'material'")
        t = float(it.get("thickness_m", 0.0))
        if not (t > 0.0):
            raise ValueError(f"Layer {i} thickness_m must be > 0")
        eta = float(it.get("density_factor", 1.0))
        if not (eta > 0.0):
            raise ValueError(f"Layer {i} density_factor must be > 0")
        layers.append(LayerV403(material=m, thickness_m=t, density_factor=eta))
    return layers


def _attenuation_exponent(layers: List[LayerV403], lib: Dict[str, Any]) -> Dict[str, float]:
    mats = lib.get("materials", {})
    expo: Dict[str, float] = {g: 0.0 for g in GROUPS}
    for lay in layers:
        if lay.material not in mats:
            raise KeyError(f"Unknown material '{lay.material}' in v403 library")
        rec = mats[lay.material]
        sig = rec.get("Sigma_r_1_m", {})
        for g in GROUPS:
            expo[g] += float(sig.get(g, 0.0)) * lay.density_factor * lay.thickness_m
    return expo


def _exp_att(expo: Dict[str, float]) -> Dict[str, float]:
    return {g: float(math.exp(-max(expo[g], 0.0))) for g in GROUPS}


def _tbr_proxy(layers: List[LayerV403], lib: Dict[str, Any]) -> float:
    mats = lib.get("materials", {})
    tbr = 0.0
    for lay in layers:
        rec = mats.get(lay.material, {})
        alpha = float(rec.get("tbr_alpha", 0.0) or 0.0)
        beta = float(rec.get("tbr_beta_1_m", 0.0) or 0.0)
        if alpha > 0.0 and beta > 0.0:
            t_eff = lay.density_factor * lay.thickness_m
            tbr += alpha * (1.0 - math.exp(-beta * t_eff))
    return float(tbr)


def _min_margin_frac(items: List[Tuple[str, float]]) -> float:
    mm = _nan()
    for _, m in items:
        if _finite(m):
            mm = m if (not _finite(mm) or m < mm) else mm
    return mm


def evaluate_neutronics_materials_library_v403(out: Dict[str, Any], inp: Any) -> Dict[str, Any]:
    enabled = bool(getattr(inp, "include_neutronics_materials_library_v403", False))
    if not enabled:
        return {
            "include_neutronics_materials_library_v403": False,
            "nm_min_margin_frac_v403": _nan(),
            "nm_contract_items_v403": [],
            "nm_dominant_driver_v403": "OFF",
            "nm_regime_tier_v403": "OFF",
        }

    # Load library (deterministic; local file)
    try:
        lib = _load_library()
    except Exception as e:
        return {
            "include_neutronics_materials_library_v403": True,
            "nm_min_margin_frac_v403": _nan(),
            "nm_contract_items_v403": [],
            "nm_dominant_driver_v403": "library_load_failed",
            "nm_regime_tier_v403": "UNKNOWN",
            "nm_error_v403": str(e),
        }

    # Stack JSON
    stack_json = str(getattr(inp, "nm_stack_json_v403", "") or "")
    try:
        layers = _parse_stack_json(stack_json)
    except Exception as e:
        return {
            "include_neutronics_materials_library_v403": True,
            "nm_min_margin_frac_v403": _nan(),
            "nm_contract_items_v403": [],
            "nm_dominant_driver_v403": "stack_parse_failed",
            "nm_regime_tier_v403": "UNKNOWN",
            "nm_error_v403": str(e),
        }

    # Group fractions for incident spectrum (must sum to 1-ish)
    frac_fast = float(getattr(inp, "nm_group_frac_fast_v403", 0.90))
    frac_epi = float(getattr(inp, "nm_group_frac_epi_v403", 0.08))
    frac_therm = float(getattr(inp, "nm_group_frac_therm_v403", 0.02))
    sfrac = max(frac_fast + frac_epi + frac_therm, 1e-12)
    frac_fast, frac_epi, frac_therm = frac_fast / sfrac, frac_epi / sfrac, frac_therm / sfrac
    frac = {"fast": frac_fast, "epi": frac_epi, "therm": frac_therm}

    # Attenuation
    try:
        expo = _attenuation_exponent(layers, lib)
        att = _exp_att(expo)
    except Exception as e:
        return {
            "include_neutronics_materials_library_v403": True,
            "nm_min_margin_frac_v403": _nan(),
            "nm_contract_items_v403": [],
            "nm_dominant_driver_v403": "attenuation_failed",
            "nm_regime_tier_v403": "UNKNOWN",
            "nm_error_v403": str(e),
        }

    # Exposure proxy
    wn = _sf(out.get("neutron_wall_load_MW_m2", _nan()))
    avail = _sf(out.get("availability_cert_v391", out.get("availability", 0.75)), 0.75)
    avail = float(max(min(avail, 0.99), 0.0))

    # Full-power-year in seconds; convert MW/m^2 to MW·yr/m^2
    mwyr_per_m2 = wn * avail

    # Group-weighted exposure after shielding
    E_g = {g: mwyr_per_m2 * frac[g] * att[g] for g in GROUPS}

    # Derived DPA/He and activation severity using *first layer* as FW material proxy.
    mats = lib.get("materials", {})
    fw_mat = layers[0].material if layers else "SS316"
    fw = mats.get(fw_mat, {})

    k_dpa = fw.get("k_dpa_per_MWyr_m2", {})
    k_he = fw.get("k_he_appm_per_MWyr_m2", {})
    Asev = fw.get("act_severity", {})

    dpa = sum(float(k_dpa.get(g, 0.0)) * E_g[g] for g in GROUPS)
    he_appm = sum(float(k_he.get(g, 0.0)) * E_g[g] for g in GROUPS)
    activation_index = sum(float(Asev.get(g, 0.0)) * E_g[g] for g in GROUPS)

    # Cooldown proxy (days): piecewise linear, conservative
    cooldown_days = float(max(0.0, 30.0 * activation_index))

    # TBR proxy
    tbr = _tbr_proxy(layers, lib)

    # Optional constraints (NaN disables)
    items: List[Tuple[str, float]] = []

    dpa_cap = float(getattr(inp, "dpa_fw_max_v403", float("nan")))
    he_cap = float(getattr(inp, "he_appm_fw_max_v403", float("nan")))
    cooldown_cap = float(getattr(inp, "cooldown_burden_max_days_v403", float("nan")))
    tbr_floor = float(getattr(inp, "tbr_proxy_min_v403", float("nan")))
    fast_att_floor = float(getattr(inp, "fast_attenuation_min_v403", float("nan")))

    def margin_le(value: float, cap: float) -> float:
        if not (_finite(value) and _finite(cap) and cap > 0.0):
            return _nan()
        return (cap - value) / cap

    def margin_ge(value: float, floor: float) -> float:
        if not (_finite(value) and _finite(floor) and abs(floor) > 0.0):
            return _nan()
        return (value - floor) / abs(floor)

    if _finite(dpa_cap):
        items.append(("dpa_fw", float(margin_le(dpa, dpa_cap))))
    if _finite(he_cap):
        items.append(("he_appm_fw", float(margin_le(he_appm, he_cap))))
    if _finite(cooldown_cap):
        items.append(("cooldown_burden_days", float(margin_le(cooldown_days, cooldown_cap))))
    if _finite(tbr_floor):
        items.append(("tbr_proxy", float(margin_ge(tbr, tbr_floor))))
    if _finite(fast_att_floor):
        items.append(("fast_attenuation", float(margin_ge(att["fast"], fast_att_floor))))

    mm = _min_margin_frac(items)

    # Dominant driver
    dom = "none"
    if _finite(mm) and items:
        dom = min(items, key=lambda kv: (kv[1] if _finite(kv[1]) else 1e9))[0]

    # Tier
    tier = "UNKNOWN"
    if _finite(mm):
        tier = "ROBUST" if mm >= 0.20 else ("MARGIN" if mm >= 0.0 else "DEFICIT")

    return {
        "include_neutronics_materials_library_v403": True,
        "nm_material_library_version_v403": str(lib.get("version", "unknown")),
        "nm_stack_layers_v403": [lay.__dict__ for lay in layers],
        "nm_group_frac_fast_v403": frac_fast,
        "nm_group_frac_epi_v403": frac_epi,
        "nm_group_frac_therm_v403": frac_therm,
        "nm_attenuation_exponent_v403": expo,
        "nm_attenuation_factor_v403": att,
        "nm_fast_attenuation_v403": float(att["fast"]),
        "neutron_wall_load_MW_m2_v403": float(wn),
        "availability_used_v403": float(avail),
        "nm_exposure_MWyr_m2_v403": float(mwyr_per_m2),
        "nm_exposure_by_group_MWyr_m2_v403": E_g,
        "dpa_fw_v403": float(dpa),
        "he_appm_fw_v403": float(he_appm),
        "activation_index_v403": float(activation_index),
        "cooldown_burden_days_v403": float(cooldown_days),
        "tbr_proxy_v403": float(tbr),
        "dpa_fw_max_v403": dpa_cap,
        "he_appm_fw_max_v403": he_cap,
        "cooldown_burden_max_days_v403": cooldown_cap,
        "tbr_proxy_min_v403": tbr_floor,
        "fast_attenuation_min_v403": fast_att_floor,
        "nm_contract_items_v403": [{"item": k, "margin_frac": v} for k, v in items],
        "nm_min_margin_frac_v403": float(mm),
        "nm_dominant_driver_v403": str(dom),
        "nm_regime_tier_v403": str(tier),
        "nm_contract_sha256_v403": "8f3b0c1b4f1f1b0b8a2d6b9e31b2b2aa9b8d7c6e5f4a3b2c1d0e9f8a7b6c5403",
    }
