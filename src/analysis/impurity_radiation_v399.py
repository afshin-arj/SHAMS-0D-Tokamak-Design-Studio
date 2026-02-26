"""
SHAMS — Impurity Species & Radiation Partition Authority (v399)
Author: © 2026 Afshin Arjhangmehr

Post-processing authority: uses TRUTH outputs (and v399 partition ledger outputs)
to compute explicit margins, tiers, and dominance-ready diagnostics.

No solvers. No iteration.

"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class ImpurityRadiationV399Result:
    tier: str
    min_margin_frac: float
    margins: Dict[str, float]
    derived: Dict[str, float]
    validity: Dict[str, Any]


def _sf(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return default


def evaluate_impurity_radiation_v399(out: Dict[str, Any], thresholds: Dict[str, float] | None = None) -> ImpurityRadiationV399Result:
    thr = thresholds or {}
    zeff_max = float(thr.get("Zeff_max", 2.5))
    f_core_rad_max = float(thr.get("f_core_rad_max", 0.75))
    f_total_rad_max = float(thr.get("f_total_rad_max", 0.85))
    # detachment margin: achieved/required - 1 (>=0 feasible)
    det_margin_min = float(thr.get("detachment_margin_min", 0.0))

    Pin = _sf(out.get("Pin_MW", out.get("P_in_MW", float("nan"))))
    Prad_core = _sf(out.get("impurity_v399_prad_core_MW", out.get("impurity_prad_core_MW", float("nan"))))
    Prad_tot = _sf(out.get("impurity_v399_prad_total_MW", out.get("impurity_prad_total_MW", float("nan"))))
    Zeff = _sf(out.get("impurity_v399_zeff", out.get("Zeff", out.get("impurity_zeff_proxy", float("nan")))))

    # radiation fractions (guarded)
    f_core = Prad_core / Pin if (Pin == Pin and Pin > 0 and Prad_core == Prad_core) else float("nan")
    f_tot = Prad_tot / Pin if (Pin == Pin and Pin > 0 and Prad_tot == Prad_tot) else float("nan")

    margins: Dict[str, float] = {}
    margins["zeff_margin"] = (zeff_max - Zeff) / zeff_max if (Zeff == Zeff and zeff_max > 0) else float("nan")
    margins["f_core_rad_margin"] = (f_core_rad_max - f_core) / f_core_rad_max if (f_core == f_core and f_core_rad_max > 0) else float("nan")
    margins["f_total_rad_margin"] = (f_total_rad_max - f_tot) / f_total_rad_max if (f_tot == f_tot and f_total_rad_max > 0) else float("nan")

    # detachment achieved vs required (from inverted detachment authority)
    prad_sol_div = _sf(out.get("impurity_v399_prad_sol_MW", float("nan"))) + _sf(out.get("impurity_v399_prad_div_MW", float("nan")))
    prad_req = _sf(out.get("detachment_prad_sol_div_required_MW", float("nan")))
    det_margin = (prad_sol_div / prad_req - 1.0) if (prad_sol_div == prad_sol_div and prad_req == prad_req and prad_req > 0.0) else float("nan")
    margins["detachment_margin"] = (det_margin - det_margin_min) / max(1e-9, abs(det_margin_min) + 1.0) if det_margin == det_margin else float("nan")

    # min margin
    mm = float("nan")
    for v in margins.values():
        if v == v:
            mm = v if (mm != mm or v < mm) else mm

    tier = "unknown"
    if mm == mm:
        if mm >= 0.10:
            tier = "comfortable"
        elif mm >= 0.0:
            tier = "near_limit"
        else:
            tier = "deficit"

    derived = {
        "f_core_rad": float(f_core) if f_core == f_core else float("nan"),
        "f_total_rad": float(f_tot) if f_tot == f_tot else float("nan"),
        "detachment_margin": float(det_margin) if det_margin == det_margin else float("nan"),
    }
    validity = dict(out.get("impurity_v399_validity", {})) if isinstance(out.get("impurity_v399_validity", {}), dict) else {}
    return ImpurityRadiationV399Result(
        tier=tier,
        min_margin_frac=float(mm),
        margins=margins,
        derived=derived,
        validity=validity,
    )
