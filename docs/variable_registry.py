from __future__ import annotations

from dataclasses import fields
from typing import Dict, List

import pandas as pd

from models.inputs import PointInputs

# A lightweight, auditable variable registry (PROCESS-like).
# This is intended to be the single UI-facing source of truth for symbols, units, and meaning.
#
# NOTE: For derived outputs, the 'units' and 'meaning' are maintained here for user-facing clarity.
#       The implementation lives in src/physics/* and src/phase1_* modules.

_INPUT_UNITS: Dict[str, str] = {
    "R0_m": "m",
    "a_m": "m",
    "kappa": "–",
    "Bt_T": "T",
    "Ip_MA": "MA",
    "Ti_keV": "keV",
    "fG": "–",
    "Paux_MW": "MW",
    "t_shield_m": "m",
    "Ti_over_Te": "–",
}

_INPUT_MEANING: Dict[str, str] = {
    "R0_m": "Major radius",
    "a_m": "Minor radius",
    "kappa": "Elongation",
    "Bt_T": "On-axis toroidal field",
    "Ip_MA": "Plasma current",
    "Ti_keV": "Ion temperature (volume-average in 0-D mode)",
    "fG": "Greenwald fraction (line-average density / Greenwald)",
    "Paux_MW": "Auxiliary heating power launched into plasma",
    "t_shield_m": "Effective inboard shield thickness used in neutronics proxy",
    "Ti_over_Te": "Ion-to-electron temperature ratio (Ti/Te)",
}

_OUTPUTS: List[Dict[str, str]] = [
    {"name": "Pfus_MW", "units": "MW", "meaning": "Total fusion power (thermal)"},
    {"name": "Q_DT_eqv", "units": "–", "meaning": "Fusion gain (Pfus / Paux) using DT-equivalent convention"},
    {"name": "H98", "units": "–", "meaning": "Confinement multiplier relative to IPB98(y,2) scaling"},
    {"name": "P_e_net_MW", "units": "MW", "meaning": "Net electric power after recirculating loads"},
    {"name": "B_peak_T", "units": "T", "meaning": "Peak TF coil field proxy"},
    {"name": "q_div_MW_m2", "units": "MW/m^2", "meaning": "Peak divertor heat flux proxy"},
    {"name": "TBR_proxy", "units": "–", "meaning": "Tritium breeding ratio proxy"},
    {"name": "ne20", "units": "1e20 m^-3", "meaning": "Line-average electron density (10^20 m^-3)"},
]

def registry_dataframe() -> pd.DataFrame:
    rows: List[Dict[str, str]] = []
    for f in fields(PointInputs):
        nm = f.name
        rows.append({
            "variable": nm,
            "kind": "input",
            "units": _INPUT_UNITS.get(nm, ""),
            "meaning": _INPUT_MEANING.get(nm, ""),
            "default": "" if f.default is f.default_factory else str(f.default) if f.default is not None else "",
        })
    for o in _OUTPUTS:
        rows.append({
            "variable": o["name"],
            "kind": "output",
            "units": o["units"],
            "meaning": o["meaning"],
            "default": "",
        })
    df = pd.DataFrame(rows)
    return df.sort_values(["kind", "variable"]).reset_index(drop=True)
