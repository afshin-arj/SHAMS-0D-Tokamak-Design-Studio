from __future__ import annotations

"""Proxy materials library for neutronics/materials authority.

This module defines deterministic coefficients used by SHAMS for early
screening proxies:
  - radial stack neutron attenuation coefficients (mu_n)
  - nuclear heating share placeholders (heat_frac)
  - irradiation damage limits (dpa_total_limit)

These are not Monte Carlo neutronics results and not a certified materials model.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class MaterialNeutronProps:
    name: str
    # Effective macroscopic attenuation coefficient for fast neutrons (1/m)
    mu_n_1_per_m: float
    # Fraction of fusion power deposited as nuclear heating in this region (0..1)
    heat_frac: float
    # Total irradiation damage limit used for lifetime proxy (dpa)
    dpa_total_limit: float


@dataclass(frozen=True)
class MaterialNeutronicsPropsV2:
    """Expanded proxy material properties for neutronics/materials authority.

    This is intentionally *not* a transport calculation, and it is not a
    certified materials qualification model. It provides deterministic,
    audit-friendly coefficients for early screening.

    Units
    -----
    - Sigma_R_*: macroscopic removal / attenuation coefficients [1/m]
    - k_dpa_per_MWm2: DPA rate coefficient [dpa/FPY] per [MW/m^2]
    - k_He_appm_per_MWm2: He production coefficient [appm/FPY] per [MW/m^2]
    - sigma0_allow_MPa: unirradiated allowable stress proxy [MPa]
    - T_*_C: temperature window [°C]

    Validity
    --------
    Coefficients are order-of-magnitude screening values.
    """

    name: str
    Sigma_R_14_1_per_m: float
    Sigma_R_gamma_1_per_m: float
    k_dpa_per_MWm2_fpy: float
    k_He_appm_per_MWm2_fpy: float
    dpa_total_limit: float
    He_total_limit_appm: float
    T_min_C: float
    T_max_C: float
    sigma0_allow_MPa: float
    # irradiation sensitivity scale (dpa) for allowable stress reduction
    dpa_ref_for_strength_drop: float = 50.0


# Notes:
# - mu_n_1_per_m and heat_frac are intentionally coarse.
# - dpa_total_limit are order-of-magnitude screening values.
#   They are *not* a substitute for material-specific irradiation qualification.

_MATERIALS: Dict[str, MaterialNeutronProps] = {
    # Structural steels
    "EUROFER": MaterialNeutronProps("EUROFER", mu_n_1_per_m=1.2, heat_frac=0.10, dpa_total_limit=80.0),
    "SS316": MaterialNeutronProps("SS316", mu_n_1_per_m=1.0, heat_frac=0.10, dpa_total_limit=60.0),

    # Tungsten-facing components (attenuation is weaker but robust surface)
    "W": MaterialNeutronProps("W", mu_n_1_per_m=0.6, heat_frac=0.06, dpa_total_limit=150.0),

    # Silicon carbide composites (advanced)
    "SiC": MaterialNeutronProps("SiC", mu_n_1_per_m=0.8, heat_frac=0.05, dpa_total_limit=200.0),

    # Shielding materials (very effective attenuation)
    "WC": MaterialNeutronProps("WC", mu_n_1_per_m=2.5, heat_frac=0.12, dpa_total_limit=200.0),
    "B4C": MaterialNeutronProps("B4C", mu_n_1_per_m=2.8, heat_frac=0.08, dpa_total_limit=200.0),

    # Blanket / breeder proxies (attenuation + heat)
    "LiPb": MaterialNeutronProps("LiPb", mu_n_1_per_m=1.1, heat_frac=0.25, dpa_total_limit=120.0),
    "FLiBe": MaterialNeutronProps("FLiBe", mu_n_1_per_m=0.9, heat_frac=0.22, dpa_total_limit=120.0),

    # Vacuum vessel / copper / coil pack (placeholders)
    "VV_STEEL": MaterialNeutronProps("VV_STEEL", mu_n_1_per_m=0.8, heat_frac=0.05, dpa_total_limit=60.0),
    "REBCO": MaterialNeutronProps("REBCO", mu_n_1_per_m=0.3, heat_frac=0.02, dpa_total_limit=30.0),
    "CU": MaterialNeutronProps("CU", mu_n_1_per_m=0.3, heat_frac=0.02, dpa_total_limit=20.0),
}


# Expanded V2 proxy library.
_MATERIALS_V2: Dict[str, MaterialNeutronicsPropsV2] = {
    # Structural steels
    "EUROFER": MaterialNeutronicsPropsV2(
        "EUROFER",
        Sigma_R_14_1_per_m=1.3,
        Sigma_R_gamma_1_per_m=0.9,
        k_dpa_per_MWm2_fpy=5.0,
        k_He_appm_per_MWm2_fpy=120.0,
        dpa_total_limit=80.0,
        He_total_limit_appm=10000.0,
        T_min_C=250.0,
        T_max_C=550.0,
        sigma0_allow_MPa=750.0,
        dpa_ref_for_strength_drop=60.0,
    ),
    "SS316": MaterialNeutronicsPropsV2(
        "SS316",
        Sigma_R_14_1_per_m=1.1,
        Sigma_R_gamma_1_per_m=0.8,
        k_dpa_per_MWm2_fpy=4.0,
        k_He_appm_per_MWm2_fpy=140.0,
        dpa_total_limit=60.0,
        He_total_limit_appm=8000.0,
        T_min_C=150.0,
        T_max_C=450.0,
        sigma0_allow_MPa=600.0,
        dpa_ref_for_strength_drop=50.0,
    ),

    # Tungsten
    "W": MaterialNeutronicsPropsV2(
        "W",
        Sigma_R_14_1_per_m=0.7,
        Sigma_R_gamma_1_per_m=0.4,
        k_dpa_per_MWm2_fpy=3.0,
        k_He_appm_per_MWm2_fpy=80.0,
        dpa_total_limit=150.0,
        He_total_limit_appm=20000.0,
        T_min_C=600.0,
        T_max_C=1400.0,
        sigma0_allow_MPa=900.0,
        dpa_ref_for_strength_drop=120.0,
    ),

    # Breeders / coolants (proxy): damage applies to structure, not liquid, but we keep coarse coefficients.
    "LiPb": MaterialNeutronicsPropsV2(
        "LiPb",
        Sigma_R_14_1_per_m=1.2,
        Sigma_R_gamma_1_per_m=0.7,
        k_dpa_per_MWm2_fpy=2.5,
        k_He_appm_per_MWm2_fpy=60.0,
        dpa_total_limit=120.0,
        He_total_limit_appm=15000.0,
        T_min_C=300.0,
        T_max_C=650.0,
        sigma0_allow_MPa=400.0,
        dpa_ref_for_strength_drop=100.0,
    ),
    "FLiBe": MaterialNeutronicsPropsV2(
        "FLiBe",
        Sigma_R_14_1_per_m=1.0,
        Sigma_R_gamma_1_per_m=0.6,
        k_dpa_per_MWm2_fpy=2.0,
        k_He_appm_per_MWm2_fpy=55.0,
        dpa_total_limit=120.0,
        He_total_limit_appm=15000.0,
        T_min_C=450.0,
        T_max_C=750.0,
        sigma0_allow_MPa=350.0,
        dpa_ref_for_strength_drop=100.0,
    ),

    # Shielding
    "WC": MaterialNeutronicsPropsV2(
        "WC",
        Sigma_R_14_1_per_m=2.6,
        Sigma_R_gamma_1_per_m=1.4,
        k_dpa_per_MWm2_fpy=1.0,
        k_He_appm_per_MWm2_fpy=30.0,
        dpa_total_limit=200.0,
        He_total_limit_appm=25000.0,
        T_min_C=100.0,
        T_max_C=800.0,
        sigma0_allow_MPa=900.0,
        dpa_ref_for_strength_drop=150.0,
    ),
    "B4C": MaterialNeutronicsPropsV2(
        "B4C",
        Sigma_R_14_1_per_m=2.9,
        Sigma_R_gamma_1_per_m=1.6,
        k_dpa_per_MWm2_fpy=0.8,
        k_He_appm_per_MWm2_fpy=25.0,
        dpa_total_limit=200.0,
        He_total_limit_appm=25000.0,
        T_min_C=100.0,
        T_max_C=900.0,
        sigma0_allow_MPa=700.0,
        dpa_ref_for_strength_drop=150.0,
    ),

    # Vacuum vessel & coil pack proxies
    "VV_STEEL": MaterialNeutronicsPropsV2(
        "VV_STEEL",
        Sigma_R_14_1_per_m=0.9,
        Sigma_R_gamma_1_per_m=0.6,
        k_dpa_per_MWm2_fpy=1.0,
        k_He_appm_per_MWm2_fpy=20.0,
        dpa_total_limit=60.0,
        He_total_limit_appm=5000.0,
        T_min_C=50.0,
        T_max_C=350.0,
        sigma0_allow_MPa=500.0,
        dpa_ref_for_strength_drop=40.0,
    ),
    "REBCO": MaterialNeutronicsPropsV2(
        "REBCO",
        Sigma_R_14_1_per_m=0.35,
        Sigma_R_gamma_1_per_m=0.25,
        k_dpa_per_MWm2_fpy=0.5,
        k_He_appm_per_MWm2_fpy=10.0,
        dpa_total_limit=30.0,
        He_total_limit_appm=2000.0,
        T_min_C=-50.0,
        T_max_C=100.0,
        sigma0_allow_MPa=250.0,
        dpa_ref_for_strength_drop=20.0,
    ),
    "CU": MaterialNeutronicsPropsV2(
        "CU",
        Sigma_R_14_1_per_m=0.35,
        Sigma_R_gamma_1_per_m=0.25,
        k_dpa_per_MWm2_fpy=0.8,
        k_He_appm_per_MWm2_fpy=15.0,
        dpa_total_limit=20.0,
        He_total_limit_appm=1500.0,
        T_min_C=-50.0,
        T_max_C=150.0,
        sigma0_allow_MPa=250.0,
        dpa_ref_for_strength_drop=20.0,
    ),
}


def get_material(name: str, fallback: MaterialNeutronProps) -> MaterialNeutronProps:
    """Return material properties for name; fallback is used if name is unknown."""
    key = str(name or "").strip()
    if not key:
        return fallback
    return _MATERIALS.get(key, fallback)


def get_material_v2(name: str, fallback: Optional[MaterialNeutronicsPropsV2] = None) -> MaterialNeutronicsPropsV2:
    """Return V2 proxy material properties.

    If name is unknown, returns fallback when provided, otherwise a conservative
    steel-like default.
    """
    key = str(name or "").strip()
    if key and key in _MATERIALS_V2:
        return _MATERIALS_V2[key]
    if fallback is not None:
        return fallback
    # conservative default
    return _MATERIALS_V2["VV_STEEL"]


def available_materials() -> Dict[str, MaterialNeutronProps]:
    """Return a copy of the material dictionary for UI / documentation."""
    return dict(_MATERIALS)


def available_materials_v2() -> Dict[str, MaterialNeutronicsPropsV2]:
    """Return a copy of the expanded V2 proxy material dictionary."""
    return dict(_MATERIALS_V2)
