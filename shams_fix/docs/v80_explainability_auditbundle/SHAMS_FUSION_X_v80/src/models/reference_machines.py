from __future__ import annotations
"""Reference machine presets for qualitative validation (PROCESS-inspired).

These are NOT intended to be exact reproductions of any public design; they
provide plausible envelopes and starting points for regression and trend checks.
"""

from typing import Dict, Any

REFERENCE_MACHINES: Dict[str, Dict[str, Any]] = {
    "SPARC-class (compact HTS)": {
        "R0_m": 1.85, "a_m": 0.57, "kappa": 1.8,
        "Bt_T": 12.2, "Ip_MA": 8.0, "Ti_keV": 15.0,
        "fG": 0.80, "Paux_MW": 20.0,
        "t_shield_m": 0.25,
    },
    "HH170 (Energy Singularity, public slide values)": {
        # From Energy Singularity CEO deck (page 10): R0=1.5 m, B0≈9 T, Ip≈6.3 MA; device diameter ~6 m.
        # Minor radius is not specified publicly; we choose a ~0.47 m as a compact, SPARC-scaled starting point.
        "R0_m": 1.50, "a_m": 0.47, "kappa": 1.85,
        "Bt_T": 9.0, "Ip_MA": 6.3, "Ti_keV": 12.0,
        "fG": 0.80, "Paux_MW": 20.0,
        "t_shield_m": 0.35,
    },
    "ARC-class (reactor HTS)": {
        "R0_m": 3.3, "a_m": 1.1, "kappa": 1.9,
        "Bt_T": 9.2, "Ip_MA": 12.0, "Ti_keV": 18.0,
        "fG": 0.85, "Paux_MW": 30.0,
        "t_shield_m": 0.70,
    },
    "ITER-inspired (large LTS)": {
        "R0_m": 6.2, "a_m": 2.0, "kappa": 1.7,
        "Bt_T": 5.3, "Ip_MA": 15.0, "Ti_keV": 10.0,
        "fG": 0.85, "Paux_MW": 50.0,
        "t_shield_m": 1.00,
    },
}

def reference_presets():
    """Return reference presets as PointInputs objects."""
    from models.inputs import PointInputs
    presets = {}
    for name, d in REFERENCE_MACHINES.items():
        presets[name.split(' (')[0]] = PointInputs(**d)
    return presets
