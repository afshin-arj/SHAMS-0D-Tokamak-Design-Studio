"""
SHAMS — Neutronics & Materials Authority Tightening (v338)
Author: © 2026 Afshin Arjhangmehr

Deterministic classification using already-computed neutronics/materials proxies.
No solvers. No iteration. Pure post-processing of TRUTH outputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class NeutronicsMaterialsResult:
    regime: str
    fragility_class: str
    min_margin_frac: float
    margins: Dict[str, float]
    derived: Dict[str, Any]


def _nan() -> float:
    return float("nan")


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return _nan()


def _frac_margin(limit: float, value: float, sense: str) -> float:
    # sense: "le" means value <= limit; "ge" means value >= limit
    if limit != limit or value != value:
        return _nan()
    if sense == "le":
        # positive means headroom
        return (limit - value) / max(abs(limit), 1e-12)
    if sense == "ge":
        return (value - limit) / max(abs(limit), 1e-12)
    return _nan()


def classify_neutronics_materials(out: Dict[str, Any], limits: Dict[str, float], fragile_margin_frac: float = 0.10) -> NeutronicsMaterialsResult:
    nwl = _safe_float(out.get("neutron_wall_load_MW_m2"))
    dpa_y = _safe_float(out.get("fw_dpa_per_year"))
    hts_life = _safe_float(out.get("hts_lifetime_yr"))
    tbr = _safe_float(out.get("TBR"))

    m_nwl = _frac_margin(limits.get("neutron_wall_load_max_MW_m2", _nan()), nwl, "le")
    m_dpa = _frac_margin(limits.get("fw_dpa_per_year_max", _nan()), dpa_y, "le")
    m_hts = _frac_margin(limits.get("hts_lifetime_min_yr", _nan()), hts_life, "ge")
    m_tbr = _frac_margin(limits.get("TBR_min", _nan()), tbr, "ge")

    margins = {
        "neutron_wall_load_margin_frac": m_nwl,
        "fw_dpa_per_year_margin_frac": m_dpa,
        "hts_lifetime_margin_frac": m_hts,
        "TBR_margin_frac": m_tbr,
    }

    finite_margins = [v for v in margins.values() if v == v]
    min_m = min(finite_margins) if finite_margins else _nan()

    if finite_margins and min_m < 0.0:
        frag = "INFEASIBLE"
    elif finite_margins and min_m < float(fragile_margin_frac):
        frag = "FRAGILE"
    elif finite_margins:
        frag = "FEASIBLE"
    else:
        frag = "UNKNOWN"

    # Regime label (coarse)
    if frag == "INFEASIBLE":
        # categorize by worst offender if available
        worst = min(margins.items(), key=lambda kv: kv[1] if kv[1] == kv[1] else 1e9)[0] if finite_margins else "unknown"
        if "neutron_wall_load" in worst:
            regime = "neutron_wall_load_limited"
        elif "fw_dpa" in worst:
            regime = "dpa_limited"
        elif "hts_lifetime" in worst:
            regime = "coil_damage_limited"
        elif "TBR" in worst:
            regime = "tbr_limited"
        else:
            regime = "infeasible"
    else:
        regime = "admissible"

    derived = {
        "neutron_wall_load_MW_m2": nwl,
        "fw_dpa_per_year": dpa_y,
        "hts_lifetime_yr": hts_life,
        "TBR": tbr,
    }

    return NeutronicsMaterialsResult(
        regime=regime,
        fragility_class=frag,
        min_margin_frac=float(min_m) if min_m == min_m else _nan(),
        margins=margins,
        derived=derived,
    )
