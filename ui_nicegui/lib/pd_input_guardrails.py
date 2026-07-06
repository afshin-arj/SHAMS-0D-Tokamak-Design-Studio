"""Non-blocking input guardrails for Point Designer (UI-only, no L0 changes)."""
from __future__ import annotations

from typing import Any, List


def unrealistic_point_input_warnings(pi: Any, *, context: str = "") -> List[str]:
    """Return warning strings for obviously unrealistic PointInputs."""
    if pi is None:
        return []
    checks = [
        ("R0_m", 0.5, 15.0, "Major radius R₀ [m] looks unusual"),
        ("a_m", 0.1, 5.0, "Minor radius a [m] looks unusual"),
        ("kappa", 1.0, 3.5, "Elongation κ looks unusual"),
        ("delta", -0.8, 0.8, "Triangularity δ looks unusual"),
        ("Bt_T", 0.5, 25.0, "Toroidal field B₀ [T] looks unusual"),
        ("Ip_MA", 0.1, 30.0, "Plasma current Ip [MA] looks unusual"),
        ("Ti_keV", 0.1, 40.0, "Ion temperature Ti [keV] looks unusual"),
        ("fG", 0.05, 1.5, "Greenwald fraction fG looks unusual"),
        ("Paux_MW", 0.0, 300.0, "Auxiliary power Paux [MW] looks unusual"),
        ("t_shield_m", 0.05, 2.0, "Shield thickness [m] looks unusual"),
    ]
    warns: List[str] = []
    prefix = f"{context}: " if context else ""
    for name, lo, hi, msg in checks:
        if not hasattr(pi, name):
            continue
        try:
            v = float(getattr(pi, name))
        except (TypeError, ValueError):
            continue
        if v < lo or v > hi:
            warns.append(f"{prefix}{msg} — {name}={v:g} (expected roughly {lo:g}–{hi:g})")
    try:
        paux = float(getattr(pi, "Paux_MW", 0.0))
        if paux < 1.0:
            warns.append(
                f"{prefix}Very low Paux ({paux:g} MW): Q_DT_eqv can look unrealistically large; "
                "check Paux for Q definition."
            )
    except (TypeError, ValueError):
        pass
    try:
        r0 = float(getattr(pi, "R0_m", 0.0))
        a = float(getattr(pi, "a_m", 0.0))
        if r0 > 0.0 and a > 0.0 and r0 <= a:
            warns.append(f"{prefix}Geometry R₀ must exceed a (aspect ratio > 1).")
    except (TypeError, ValueError):
        pass
    return warns
