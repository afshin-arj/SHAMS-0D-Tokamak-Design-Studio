"""
SHAMS — Impurity Species & Radiation Partition Authority (v337)
Author: © 2026 Afshin Arjhangmehr

Deterministic classifier using already-computed power balance and radiation breakdown.
No solvers. No iteration. Pure post-processing of TRUTH outputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class ImpurityRadiationResult:
    impurity_regime: str
    impurity_species: str
    fragility_class: str
    min_margin_frac: float
    margins: Dict[str, float]
    derived: Dict[str, float]


def _safe_float(x: Any, default: float = float("nan")) -> float:
    try:
        v = float(x)
        return v
    except Exception:
        return default


def evaluate_impurity_radiation(out: Dict[str, Any], contract: Any) -> ImpurityRadiationResult:
    """
    Evaluate impurity/radiation margins from TRUTH outputs.
    Expects (when available):
      - Zeff
      - Pin_MW, Prad_core_MW, Prad_SOL_MW, P_SOL_MW
      - rad_breakdown: P_brem_W, P_sync_W, P_line_W, P_total_W (optional)
      - impurity_species (optional)
    """
    thr = getattr(contract, "thresholds", {}) if contract is not None else {}
    Zeff_max = float(thr.get("Zeff_max", 2.5))
    f_core_rad_max = float(thr.get("f_core_rad_max", 0.75))
    f_total_rad_max = float(thr.get("f_total_rad_max", 0.85))
    f_SOL_rad_max = float(thr.get("f_SOL_rad_max", 0.95))
    core_line_frac_max = float(thr.get("core_line_frac_max", 0.60))
    fragile_margin = float(getattr(contract, "fragility", {}).get("fragile_margin_frac", 0.05)) if contract is not None else 0.05

    Zeff = _safe_float(out.get("Zeff", float("nan")))
    Pin = _safe_float(out.get("Pin_MW", out.get("P_in_MW", float("nan"))))
    Prad_core = _safe_float(out.get("Prad_core_MW", float("nan")))
    Prad_SOL = _safe_float(out.get("Prad_SOL_MW", float("nan")))
    P_SOL = _safe_float(out.get("P_SOL_MW", float("nan")))

    # fractions (guarded)
    f_core = Prad_core / Pin if (Pin == Pin and Pin > 0 and Prad_core == Prad_core) else float("nan")
    f_tot = (Prad_core + Prad_SOL) / Pin if (Pin == Pin and Pin > 0 and Prad_core == Prad_core and Prad_SOL == Prad_SOL) else float("nan")
    f_sol = Prad_SOL / P_SOL if (P_SOL == P_SOL and P_SOL > 0 and Prad_SOL == Prad_SOL) else float("nan")

    rb = out.get("rad_breakdown", {}) if isinstance(out.get("rad_breakdown", {}), dict) else {}
    Ptot_W = _safe_float(rb.get("P_total_W", float("nan")))
    Pline_W = _safe_float(rb.get("P_line_W", float("nan")))
    core_line_frac = Pline_W / Ptot_W if (Ptot_W == Ptot_W and Ptot_W > 0 and Pline_W == Pline_W) else float("nan")

    # margins (signed; >=0 feasible)
    margins = {}
    margins["Zeff_margin"] = (Zeff_max - Zeff) / Zeff_max if (Zeff == Zeff and Zeff_max > 0) else float("nan")
    margins["f_core_rad_margin"] = (f_core_rad_max - f_core) / f_core_rad_max if (f_core == f_core and f_core_rad_max > 0) else float("nan")
    margins["f_total_rad_margin"] = (f_total_rad_max - f_tot) / f_total_rad_max if (f_tot == f_tot and f_total_rad_max > 0) else float("nan")
    margins["f_SOL_rad_margin"] = (f_SOL_rad_max - f_sol) / f_SOL_rad_max if (f_sol == f_sol and f_SOL_rad_max > 0) else float("nan")
    margins["core_line_frac_margin"] = (core_line_frac_max - core_line_frac) / core_line_frac_max if (core_line_frac == core_line_frac and core_line_frac_max > 0) else float("nan")

    # min margin over defined numeric margins
    mm = float("nan")
    for v in margins.values():
        if v == v:
            mm = v if (mm != mm or v < mm) else mm

    # classify regime (coarse)
    impurity_species = str(out.get("impurity_species", out.get("impurity_mix_species", "unknown")) or "unknown")
    impurity_regime = "unknown"
    if mm == mm:
        if mm < 0:
            # pick dominant
            worst = min((kv for kv in margins.items() if kv[1] == kv[1]), key=lambda kv: kv[1])[0]
            if worst == "Zeff_margin":
                impurity_regime = "high_Zeff"
            elif worst in ("f_core_rad_margin", "core_line_frac_margin"):
                impurity_regime = "core_radiation_dominated"
            elif worst == "f_SOL_rad_margin":
                impurity_regime = "sol_radiation_excess"
            elif worst == "f_total_rad_margin":
                impurity_regime = "radiation_dominated"
            else:
                impurity_regime = "radiation_limited"
        else:
            impurity_regime = "clean" if mm > 0.20 else "moderate"

    # fragility class
    frag = "UNKNOWN"
    if mm == mm:
        frag = "INFEASIBLE" if mm < 0 else ("FRAGILE" if mm < fragile_margin else "FEASIBLE")

    derived = {
        "Zeff": Zeff,
        "Pin_MW": Pin,
        "Prad_core_MW": Prad_core,
        "Prad_SOL_MW": Prad_SOL,
        "P_SOL_MW": P_SOL,
        "f_core_rad": f_core,
        "f_total_rad": f_tot,
        "f_SOL_rad": f_sol,
        "core_line_frac": core_line_frac,
    }
    return ImpurityRadiationResult(
        impurity_regime=impurity_regime,
        impurity_species=impurity_species,
        fragility_class=frag,
        min_margin_frac=float(mm) if mm == mm else float("nan"),
        margins={k: float(v) for k, v in margins.items()},
        derived={k: float(v) for k, v in derived.items()},
    )
