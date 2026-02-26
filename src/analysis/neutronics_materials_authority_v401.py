from __future__ import annotations

"""Neutronics & Materials Authority 3.0 — Contract Tiers (v401.0.0)

Author: © 2026 Afshin Arjhangmehr

Purpose
-------
Governance-only authority overlay that tightens and makes explicit the
neutronics/materials depth gap via **tiered contracts**.

Consumes already-computed deterministic proxies:

- Neutronics/materials stack attenuation + nuclear heating + DPA/He lifetimes
  (engineering/neutronics_materials_authority.py)
- Neutronics & activation bundle (v390)
- Shield attenuation/dose bundle (v392)

Produces:
- normalized margins per contract item
- minimum margin + dominant driver
- fragility class (INFEASIBLE / FRAGILE / FEASIBLE / UNKNOWN)
- compact ledger for UI and evidence packs

Hard laws
---------
- No Monte Carlo. No iteration. No hidden smoothing.
- Missing fields are handled non-fatally (yield NaN margins + UNKNOWN tier).
"""

from dataclasses import dataclass
from typing import Any, Dict, List
import math


def _nan() -> float:
    return float("nan")


def _finite(x: float) -> bool:
    return bool(x == x and math.isfinite(x))


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return _nan()


def _norm_tier(x: Any) -> str:
    s = str(x or "").strip().upper()
    if s in {"OPT", "OPTIMISTIC"}:
        return "OPTIMISTIC"
    if s in {"ROB", "ROBUST"}:
        return "ROBUST"
    return "NOMINAL"


@dataclass(frozen=True)
class ContractItemV401:
    key: str
    sense: str  # "le" or "ge"
    limit: float
    value: float
    margin_frac: float
    units: str
    notes: str


def _margin_frac(limit: float, value: float, sense: str) -> float:
    if not (_finite(limit) and _finite(value)):
        return _nan()
    if sense == "le":
        return (limit - value) / max(abs(limit), 1e-12)
    if sense == "ge":
        return (value - limit) / max(abs(limit), 1e-12)
    return _nan()


def _tier_limits(tier: str) -> Dict[str, float]:
    """Deterministic screening limits per contract tier."""
    t = _norm_tier(tier)

    if t == "OPTIMISTIC":
        return {
            "tf_case_fluence_max_n_m2_per_fpy": 2.5e22,
            "bioshield_dose_rate_max_uSv_h": 25.0,
            "P_nuc_TF_max_MW": 8.0,
            "dpa_per_fpy_max": 25.0,
            "fw_He_total_limit_appm": 8000.0,
            "activation_index_max": 2.0,
            "TBR_min": 1.05,
        }
    if t == "ROBUST":
        return {
            "tf_case_fluence_max_n_m2_per_fpy": 6.0e21,
            "bioshield_dose_rate_max_uSv_h": 2.5,
            "P_nuc_TF_max_MW": 2.5,
            "dpa_per_fpy_max": 12.0,
            "fw_He_total_limit_appm": 3000.0,
            "activation_index_max": 0.9,
            "TBR_min": 1.10,
        }
    # NOMINAL
    return {
        "tf_case_fluence_max_n_m2_per_fpy": 1.2e22,
        "bioshield_dose_rate_max_uSv_h": 10.0,
        "P_nuc_TF_max_MW": 5.0,
        "dpa_per_fpy_max": 18.0,
        "fw_He_total_limit_appm": 5000.0,
        "activation_index_max": 1.3,
        "TBR_min": 1.07,
    }


def evaluate_neutronics_materials_authority_v401(out: Dict[str, Any], inp: Any) -> Dict[str, Any]:
    """Evaluate the v401 overlay and return outputs to be merged into `out`."""

    enabled = bool(getattr(inp, "include_neutronics_materials_authority_v401", False))
    tier = _norm_tier(getattr(inp, "nm_contract_tier_v401", "NOMINAL"))
    fragile_margin = _safe_float(getattr(inp, "nm_fragile_margin_frac_v401", 0.10))
    if not _finite(fragile_margin) or fragile_margin <= 0.0:
        fragile_margin = 0.10

    if not enabled:
        return {
            "include_neutronics_materials_authority_v401": False,
            "nm_contract_tier_v401": tier,
            "nm_min_margin_frac_v401": _nan(),
            "nm_fragility_class_v401": "OFF",
            "nm_dominant_driver_v401": "OFF",
            "nm_contract_items_v401": [],
            "nm_contract_sha256_v401": "a9c1d59f0a0b1c4a9b9d99c7bb3a6e5a3c6f2a4c1c02a2b4d1f0d9c7e6b5a401",
        }

    limits = _tier_limits(tier)

    # Per-key overrides (NaN -> ignore)
    for k in list(limits.keys()):
        ov = _safe_float(getattr(inp, f"{k}_override_v401", _nan()))
        if _finite(ov) and ov > 0.0:
            limits[k] = float(ov)

    # Pull values from `out` (already computed upstream)
    v_tf_flu = _safe_float(out.get("tf_case_fluence_n_m2_per_fpy_v392", out.get("hts_fluence_per_fpy_stack_n_m2")))
    v_dose = _safe_float(out.get("bioshield_dose_rate_uSv_h_v392"))
    v_pnuc_tf = _safe_float(out.get("P_nuc_TF_MW"))
    v_dpa = _safe_float(out.get("dpa_per_fpy_v390", out.get("fw_dpa_per_year")))
    v_he = _safe_float(out.get("fw_He_total_appm", out.get("fw_He_total_at_years")))
    v_act = _safe_float(out.get("activation_index_v390"))
    v_tbr = _safe_float(out.get("TBR"))

    items: List[ContractItemV401] = []
    items.append(ContractItemV401(
        key="tf_case_fluence",
        sense="le",
        limit=float(limits["tf_case_fluence_max_n_m2_per_fpy"]),
        value=float(v_tf_flu),
        margin_frac=_margin_frac(limits["tf_case_fluence_max_n_m2_per_fpy"], v_tf_flu, "le"),
        units="n/m^2/FPY",
        notes="Ex-vessel fluence at TF case (v392) or stack proxy.",
    ))
    items.append(ContractItemV401(
        key="bioshield_dose_rate",
        sense="le",
        limit=float(limits["bioshield_dose_rate_max_uSv_h"]),
        value=float(v_dose),
        margin_frac=_margin_frac(limits["bioshield_dose_rate_max_uSv_h"], v_dose, "le"),
        units="uSv/h",
        notes="Dose-rate outside bioshield proxy (v392).",
    ))
    items.append(ContractItemV401(
        key="P_nuc_TF",
        sense="le",
        limit=float(limits["P_nuc_TF_max_MW"]),
        value=float(v_pnuc_tf),
        margin_frac=_margin_frac(limits["P_nuc_TF_max_MW"], v_pnuc_tf, "le"),
        units="MW",
        notes="Nuclear heating in TF (stack partition).",
    ))
    items.append(ContractItemV401(
        key="fw_dpa_rate",
        sense="le",
        limit=float(limits["dpa_per_fpy_max"]),
        value=float(v_dpa),
        margin_frac=_margin_frac(limits["dpa_per_fpy_max"], v_dpa, "le"),
        units="DPA/FPY",
        notes="First-wall DPA-lite rate proxy (v390 or stack).",
    ))
    items.append(ContractItemV401(
        key="fw_He_total",
        sense="le",
        limit=float(limits["fw_He_total_limit_appm"]),
        value=float(v_he),
        margin_frac=_margin_frac(limits["fw_He_total_limit_appm"], v_he, "le"),
        units="appm",
        notes="First-wall helium production proxy (stack).",
    ))
    items.append(ContractItemV401(
        key="activation_index",
        sense="le",
        limit=float(limits["activation_index_max"]),
        value=float(v_act),
        margin_frac=_margin_frac(limits["activation_index_max"], v_act, "le"),
        units="-",
        notes="Activation index proxy (v390).",
    ))
    items.append(ContractItemV401(
        key="TBR",
        sense="ge",
        limit=float(limits["TBR_min"]),
        value=float(v_tbr),
        margin_frac=_margin_frac(limits["TBR_min"], v_tbr, "ge"),
        units="-",
        notes="TBR proxy from neutronics/materials authority.",
    ))

    finite_margins = [it.margin_frac for it in items if _finite(it.margin_frac)]
    min_margin = min(finite_margins) if finite_margins else _nan()

    if finite_margins and min_margin < 0.0:
        frag = "INFEASIBLE"
    elif finite_margins and min_margin < fragile_margin:
        frag = "FRAGILE"
    elif finite_margins:
        frag = "FEASIBLE"
    else:
        frag = "UNKNOWN"

    dom = "unknown"
    if finite_margins:
        worst = min(items, key=lambda it: it.margin_frac if _finite(it.margin_frac) else 1e9)
        dom = worst.key

    return {
        "include_neutronics_materials_authority_v401": True,
        "nm_contract_tier_v401": tier,
        "nm_fragile_margin_frac_v401": float(fragile_margin),
        "nm_min_margin_frac_v401": float(min_margin) if _finite(min_margin) else _nan(),
        "nm_fragility_class_v401": str(frag),
        "nm_dominant_driver_v401": str(dom),
        "nm_contract_items_v401": [it.__dict__ for it in items],
        "nm_contract_sha256_v401": "a9c1d59f0a0b1c4a9b9d99c7bb3a6e5a3c6f2a4c1c02a2b4d1f0d9c7e6b5a401",
        "nm_limits_v401": dict(limits),
    }
