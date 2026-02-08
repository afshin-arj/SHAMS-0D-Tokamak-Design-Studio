from __future__ import annotations

"""Optimization Sandbox — Design Navigation (steering instrument).

This module converts local constraint-surface geometry (gradient normals from
`constraint_surface_map`) into *descriptive steering cues*:

- "Increasing X tends to improve signed margin" (for a chosen constraint)
- "Decreasing Y tends to improve signed margin"

Discipline:
- No recommendations, only geometry implied by evaluated archive data.
- No truth claims: gradients are local linear summaries.
"""

from typing import Any, Dict, List, Sequence


LEVER_FAMILIES = {
    "Geometry": ["R0_m", "a_m", "kappa", "delta", "q95", "A"],
    "Plasma": ["Ip_MA", "nbar_1e20_m3", "Ti_keV", "Te_keV", "fG"],
    "Power": ["Paux_MW", "Pfus_MW", "Pnet_MWe"],
    "Magnets": ["Bt_T", "B0_T", "Bmax_T"],
}


def _family_for_key(k: str) -> str:
    for fam, keys in LEVER_FAMILIES.items():
        if str(k) in keys:
            return fam
    return "Other"


def steering_cues_from_surface_map(surface_map: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Turn a surface map gradient into human-readable cues.

    The gradient is defined as pointing toward increasing signed margin (more feasible
    for that constraint), by construction in `constraint_surface_map`.
    """
    if not isinstance(surface_map, dict) or not surface_map.get("ok"):
        return []
    grad = surface_map.get("gradient_normal") or {}
    if not isinstance(grad, dict) or not grad:
        return []

    rows = []
    for k, v in grad.items():
        try:
            g = float(v)
        except Exception:
            continue
        if not (g == g):  # NaN
            continue
        direction = "increase" if g > 0 else "decrease"
        strength = abs(g)
        rows.append({
            "lever": str(k),
            "family": _family_for_key(str(k)),
            "cue": f"{direction} {k}",
            "signed": g,
            "strength": strength,
        })

    rows.sort(key=lambda r: float(r.get("strength", 0.0)), reverse=True)
    return rows


def filter_cues(rows: List[Dict[str, Any]], family: str | None = None, top_n: int = 12) -> List[Dict[str, Any]]:
    if family and family != "All":
        rows = [r for r in rows if r.get("family") == family]
    return rows[: int(top_n)]
