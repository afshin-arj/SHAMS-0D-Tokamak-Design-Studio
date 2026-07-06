"""Feasible search objectives and helpers — Streamlit parity."""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

FS_OBJECTIVE_OPTIONS: List[Tuple[str, str]] = [
    ("q_div_MW_m2", "Minimize divertor q_div"),
    ("P_SOL_over_R_MW_m", "Minimize P_SOL/R"),
    ("neutron_wall_load_MW_m2", "Minimize NWL"),
    ("sigma_vm_MPa", "Minimize stress sigma_vm"),
    ("B_peak_T", "Minimize B_peak"),
    ("-TBR", "Maximize TBR"),
    ("-hts_margin", "Maximize HTS margin"),
    ("Q_DT_eqv", "Maximize Q_DT_eqv (negated for min)"),
]

FS_METRIC_KEYS = [
    "q_div_MW_m2",
    "P_SOL_over_R_MW_m",
    "neutron_wall_load_MW_m2",
    "sigma_vm_MPa",
    "B_peak_T",
    "TBR",
    "hts_margin",
    "H98",
    "Q_DT_eqv",
    "Pfus_DT_adj_MW",
    "P_e_net_MW",
]

FS_START_SOURCES = [
    "Manual (midpoint of bounds)",
    "Last target solve",
    "Last seeded recovery",
]


def fs_objective_value(out: dict, objective_key: str) -> float:
    key = str(objective_key or "Q_DT_eqv")
    try:
        if key.startswith("-"):
            v = float(out.get(key[1:], float("nan")))
            return -v if math.isfinite(v) else float("inf")
        if key == "Q_DT_eqv":
            v = float(out.get("Q_DT_eqv", out.get("Q", float("nan"))))
            return -v if math.isfinite(v) else float("inf")
        v = float(out.get(key, float("nan")))
        return v if math.isfinite(v) else float("inf")
    except (TypeError, ValueError):
        return float("inf")


def fs_objective_label(key: str) -> str:
    for k, lbl in FS_OBJECTIVE_OPTIONS:
        if k == key:
            return lbl
    return str(key)
