"""
SHAMS v358.0 — Profile Family Library Authority
Author: © 2026 Afshin Arjhangmehr

Deterministic, audit-safe profile family tags and multiplicative shape factors.
No solvers. No iteration. No relaxation.

This module provides a small, certified library of profile "families" (shape narratives),
implemented as algebraic mappings from declared knobs to multipliers that can be
applied in the frozen truth evaluator.

All multipliers are conservatively clamped to prevent unbounded leverage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple
import math

# Conservative clamps (audit safety)
_CONFINEMENT_MULT_BOUNDS: Tuple[float, float] = (0.5, 1.8)
_BOOTSTRAP_MULT_BOUNDS: Tuple[float, float] = (0.5, 1.8)
_PEAKING_BOUNDS: Tuple[float, float] = (0.7, 2.0)
_SHEAR_BOUNDS: Tuple[float, float] = (0.0, 1.0)
_PED_FRAC_BOUNDS: Tuple[float, float] = (0.0, 0.4)

SUPPORTED_FAMILIES = (
    "CORE_FLAT",
    "CORE_PEAKED",
    "PEDESTAL_MODERATE",
    "PEDESTAL_STRONG",
    "HYBRID_CORE_PEAKED_PED",
)

@dataclass(frozen=True)
class ProfileFamilyFactorsV358:
    tag: str
    p_peaking: float
    j_peaking: float
    shear_shape: float
    pedestal_frac: float
    confinement_mult_eff: float
    bootstrap_mult_eff: float
    validity: Dict[str, object]


def _clamp(x: float, lo: float, hi: float) -> float:
    if not (x == x) or math.isinf(x):
        return float("nan")
    return max(lo, min(hi, x))


def compute_profile_family_factors_v358(
    family_raw: str,
    p_peaking: float,
    j_peaking: float,
    shear_shape: float,
    pedestal_frac: float,
    confinement_mult_user: float,
    bootstrap_mult_user: float,
) -> ProfileFamilyFactorsV358:
    """Return deterministic profile family factors.

    The "family" provides default shape narratives; user knobs fine-tune within
    bounded ranges. Multipliers are applied multiplicatively and then clamped.
    """
    family = (family_raw or "CORE_FLAT").upper().replace(" ", "_")
    if family not in SUPPORTED_FAMILIES:
        family = "CORE_FLAT"

    # Clamp user knobs
    ppk = _clamp(float(p_peaking), *_PEAKING_BOUNDS)
    jpk = _clamp(float(j_peaking), *_PEAKING_BOUNDS)
    shear = _clamp(float(shear_shape), *_SHEAR_BOUNDS)
    ped = _clamp(float(pedestal_frac), *_PED_FRAC_BOUNDS)

    cmu = float(confinement_mult_user)
    bmu = float(bootstrap_mult_user)
    cmu = _clamp(cmu, *_CONFINEMENT_MULT_BOUNDS)
    bmu = _clamp(bmu, *_BOOTSTRAP_MULT_BOUNDS)

    # Family base factors (narrative-level defaults)
    base_ppk = 1.0
    base_jpk = 1.0
    base_shear = 0.5
    base_ped = 0.0
    base_cm = 1.0
    base_bm = 1.0

    if family == "CORE_FLAT":
        base_ppk, base_jpk, base_shear, base_ped = 0.95, 0.95, 0.55, 0.0
        base_cm, base_bm = 0.95, 0.90
    elif family == "CORE_PEAKED":
        base_ppk, base_jpk, base_shear, base_ped = 1.25, 1.15, 0.45, 0.0
        base_cm, base_bm = 1.05, 1.10
    elif family == "PEDESTAL_MODERATE":
        base_ppk, base_jpk, base_shear, base_ped = 1.10, 1.05, 0.50, 0.12
        base_cm, base_bm = 1.10, 1.05
    elif family == "PEDESTAL_STRONG":
        base_ppk, base_jpk, base_shear, base_ped = 1.15, 1.05, 0.48, 0.22
        base_cm, base_bm = 1.20, 1.05
    elif family == "HYBRID_CORE_PEAKED_PED":
        base_ppk, base_jpk, base_shear, base_ped = 1.20, 1.10, 0.40, 0.16
        base_cm, base_bm = 1.15, 1.15

    # Combine family defaults with user knobs in a conservative manner:
    # - treat knobs as multipliers around 1.0, but bounded.
    # - pedestal fraction adds additional confinement leverage, bounded.
    ppk_eff = _clamp(base_ppk * ppk, *_PEAKING_BOUNDS)
    jpk_eff = _clamp(base_jpk * jpk, *_PEAKING_BOUNDS)
    shear_eff = _clamp(0.5 * (base_shear + shear), *_SHEAR_BOUNDS)
    ped_eff = _clamp(base_ped + ped, *_PED_FRAC_BOUNDS)

    # Confinement multiplier: pedestal gives a small extra boost, saturating.
    ped_boost = 1.0 + 0.6 * ped_eff  # <= 1.24
    cm_eff = _clamp(base_cm * cmu * ped_boost, *_CONFINEMENT_MULT_BOUNDS)

    # Bootstrap multiplier: peaked pressure tends to increase f_bs proxy; keep mild.
    peak_boost = 1.0 + 0.25 * max(0.0, ppk_eff - 1.0)  # <= 1.25
    bm_eff = _clamp(base_bm * bmu * peak_boost, *_BOOTSTRAP_MULT_BOUNDS)

    validity: Dict[str, object] = {
        "v358_profile_family": True,
        "family": family,
        "bounds": {
            "confinement_mult": _CONFINEMENT_MULT_BOUNDS,
            "bootstrap_mult": _BOOTSTRAP_MULT_BOUNDS,
            "peaking": _PEAKING_BOUNDS,
            "shear": _SHEAR_BOUNDS,
            "pedestal_frac": _PED_FRAC_BOUNDS,
        },
    }

    return ProfileFamilyFactorsV358(
        tag=family,
        p_peaking=ppk_eff,
        j_peaking=jpk_eff,
        shear_shape=shear_eff,
        pedestal_frac=ped_eff,
        confinement_mult_eff=cm_eff,
        bootstrap_mult_eff=bm_eff,
        validity=validity,
    )
