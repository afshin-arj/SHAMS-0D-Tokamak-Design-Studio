"""Recovery search helpers — base-variable bounds, seeds, distance weights."""

from __future__ import annotations

import math
from dataclasses import fields
from typing import Any, Dict, List, Tuple

BASE_DESIGN_VARIABLES: List[Tuple[str, str]] = [
    ("R0_m", "Major radius R₀ [m]"),
    ("a_m", "Minor radius a [m]"),
    ("kappa", "Elongation κ"),
    ("delta", "Triangularity δ"),
    ("Bt_T", "Toroidal field B_t [T]"),
    ("Ti_keV", "Ion temperature T_i [keV]"),
    ("Ti_over_Te", "T_i / T_e"),
    ("t_shield_m", "Shield thickness [m]"),
]

BASE_LABELS = {k: lab for k, lab in BASE_DESIGN_VARIABLES}


def default_base_bounds(base: Any, key: str) -> tuple[float, float]:
    try:
        v0 = float(getattr(base, key))
    except Exception:
        return 0.0, 1.0
    if key == "delta" and abs(v0) < 1e-6:
        return 0.0, 0.5
    span = max(1e-9, abs(v0))
    lo = max(0.0, v0 - 0.20 * span)
    hi = v0 + 0.20 * span
    return float(lo), float(hi)


def merge_recovery_bounds(
    session: Any,
    base: Any,
    variables: Dict[str, Tuple[float, float, float]],
) -> Dict[str, Dict[str, float]]:
    bounds: Dict[str, Dict[str, float]] = {
        k: {"lo": float(lo), "hi": float(hi)} for k, (_, lo, hi) in variables.items()
    }
    if not getattr(session, "systems_recovery_basevars_enabled", False):
        return bounds
    selected = list(getattr(session, "systems_recovery_basevars", None) or [])
    stored = dict(getattr(session, "systems_recovery_base_bounds", None) or {})
    for key in selected:
        dlo, dhi = default_base_bounds(base, key)
        entry = stored.get(key) if isinstance(stored.get(key), dict) else {}
        lo = float(entry.get("lo", dlo))
        hi = float(entry.get("hi", dhi))
        bounds[key] = {"lo": min(lo, hi), "hi": max(lo, hi)}
    return bounds


def recovery_distance_weights(session: Any) -> Dict[str, float]:
    weights: Dict[str, float] = {}
    stored = dict(getattr(session, "systems_recovery_base_bounds", None) or {})
    for key, entry in stored.items():
        if isinstance(entry, dict) and bool(entry.get("pin")):
            weights[key] = 10.0
    return weights


def build_recovery_seed(
    session: Any,
    base: Any,
    bounds: Dict[str, Dict[str, float]],
    *,
    mode: str,
) -> Dict[str, float]:
    seed: Dict[str, float] = {}
    manual = dict(getattr(session, "systems_recovery_manual_seed", None) or {})

    for key, b in bounds.items():
        lo = float(b.get("lo", 0.0))
        hi = float(b.get("hi", 1.0))
        if mode == "midpoint":
            seed[key] = 0.5 * (lo + hi)
        elif mode == "manual" and key in manual:
            seed[key] = max(lo, min(hi, float(manual[key])))
        else:
            pd_out = getattr(session, "pd_last_outputs", None) or getattr(session, "last_eval", None)
            if isinstance(pd_out, dict) and key in pd_out and pd_out[key] is not None:
                try:
                    seed[key] = max(lo, min(hi, float(pd_out[key])))
                    continue
                except (TypeError, ValueError):
                    pass
            if hasattr(base, key):
                try:
                    seed[key] = max(lo, min(hi, float(getattr(base, key))))
                    continue
                except (TypeError, ValueError):
                    pass
            seed[key] = 0.5 * (lo + hi)
    return seed


def valid_point_fields(base: Any) -> set[str]:
    try:
        return {f.name for f in fields(base)}
    except Exception:
        return set()
