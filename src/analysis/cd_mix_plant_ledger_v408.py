"""CD mix → plant electric ledger overlay (PHYS-006)."""
from __future__ import annotations

import math
from typing import Any, Dict


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else float("nan")
    except (TypeError, ValueError):
        return default


def evaluate_cd_mix_plant_ledger_v408(out: Dict[str, Any], inp: Any) -> Dict[str, Any]:
    """Break down CD channel electric draw for plant ledger constraints."""
    patch: Dict[str, Any] = {
        "cd_mix_enable": float(bool(getattr(inp, "cd_mix_enable", False))),
        "P_cd_eccd_max_MW": _f(getattr(inp, "P_cd_eccd_max_MW", float("nan"))),
        "P_cd_lhcd_max_MW": _f(getattr(inp, "P_cd_lhcd_max_MW", float("nan"))),
        "cd_mix_frac_sum_max": 1.001,
    }
    if not bool(getattr(inp, "cd_mix_enable", False)):
        patch["cd_mix_frac_sum"] = float("nan")
        return patch

    channels = ("ECCD", "LHCD", "NBI", "ICRF")
    frac_sum = 0.0
    for ch in channels:
        frac = _f(getattr(inp, f"cd_mix_frac_{ch.lower()}", 0.0 if ch != "ECCD" else 1.0))
        if frac > 0.0:
            frac_sum += frac
        p_mw = _f(out.get(f"P_cd_{ch}_MW", float("nan")))
        eta = _f(out.get(f"eta_cd_wallplug_{ch}", out.get("eta_cd_wallplug_used", 0.35)))
        if p_mw == p_mw and eta > 0.0:
            patch[f"P_cd_{ch.lower()}_el_MW"] = float(p_mw / eta)
        else:
            patch[f"P_cd_{ch.lower()}_el_MW"] = float("nan")

    patch["cd_mix_frac_sum"] = float(frac_sum)
    return patch
