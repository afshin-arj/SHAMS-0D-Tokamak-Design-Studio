"""SHAMS — Current Drive Technology Authority (v346)
Author: © 2026 Afshin Arjhangmehr

Deterministic technology-regime authority for external current drive (CD).

Scope
-----
- Classify CD technology regime (ECCD/LHCD/NBI/ICRF) based on declared actuator.
- Enforce conservative, contract-governed envelopes on:
  * eta_CD_A_W proxy (A/W)
  * wall-plug efficiency proxy (dimensionless, if available)
  * plant power fraction for CD (P_CD / P_electric)
  * basic accessibility proxy (e.g., LHCD density ceiling), when data exist
- No solvers. No iteration. No internal optimization. Pure margin evaluation.

Notes
-----
This authority is intentionally conservative and trend-correct, designed to prevent
non-physical steady-state claims that rely on implicit or over-optimistic CD performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import math


def _safe_f(out: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        if k in out:
            try:
                v = float(out[k])
                if math.isfinite(v):
                    return v
            except Exception:
                pass
    return None


def _safe_s(out: Dict[str, Any], *keys: str) -> Optional[str]:
    for k in keys:
        if k in out:
            try:
                s = str(out[k])
                if s.strip():
                    return s
            except Exception:
                pass
    return None


@dataclass(frozen=True)
class CDTechAuthorityResult:
    cd_tech_regime: str
    cd_fragility_class: str
    cd_min_margin_frac: float
    cd_top_limiter: str
    margins: Dict[str, float]
    ctx: Dict[str, Any]


def _fragility_from_min_margin(min_margin: float, fragile_thr: float) -> str:
    if not math.isfinite(min_margin):
        return "UNKNOWN"
    if min_margin < 0.0:
        return "INFEASIBLE"
    if min_margin < fragile_thr:
        return "FRAGILE"
    return "FEASIBLE"


def evaluate_cd_tech_authority(out: Dict[str, Any], contract: Any) -> CDTechAuthorityResult:
    regimes = getattr(contract, "tech_regimes", {}) or {}
    fragile_thr = float(getattr(contract, "fragile_margin_frac", 0.05))

    # Determine actuator/tech regime: prefer explicit label from inputs propagated to outputs
    tech = (_safe_s(out, "cd_actuator", "CD_ACTUATOR", "cd_tech") or "ECCD").strip().upper()
    # Normalize common spellings
    if tech in ("EC", "ECRH", "ECCD", "ECH"):
        tech = "ECCD"
    elif tech in ("LH", "LHCD"):
        tech = "LHCD"
    elif tech in ("NB", "NBI"):
        tech = "NBI"
    elif tech in ("ICRF", "FWCD", "IC"):
        tech = "ICRF"

    thr = dict(regimes.get(tech, {}) or {})
    # Fallback to ECCD envelope if unknown
    if not thr and "ECCD" in regimes:
        thr = dict(regimes["ECCD"])
        tech = "ECCD"

    # Extract terms
    P_cd_MW = _safe_f(out, "P_CD_MW", "Pcd_MW", "P_cd_MW") or 0.0
    eta_cd_A_W = _safe_f(out, "eta_CD_A_W", "eta_cd_A_W", "eta_cd_A_per_W")  # A/W
    if eta_cd_A_W is None:
        # Some branches expose gamma_A_per_W
        eta_cd_A_W = _safe_f(out, "gamma_cd_A_per_W", "gamma_A_per_W")

    eta_wallplug = _safe_f(out, "eta_cd_wallplug", "eta_CD_wallplug", "eta_wallplug")
    P_electric_MW = _safe_f(out, "P_electric_MW", "P_elec_MW", "P_electric")  # plant electrical
    # if plant ledger names differ, accept net electric
    if P_electric_MW is None:
        P_electric_MW = _safe_f(out, "P_net_electric_MW", "P_net_MW", "P_grid_MW")

    # Density proxy for LHCD accessibility (very lightweight)
    nbar20 = _safe_f(out, "ne_bar_1e20_m3", "nbar20", "ne20", "ne_1e20_m3")

    margins: Dict[str, float] = {}

    # eta_CD_A_W envelope
    eta_min = float(thr.get("eta_CD_A_W_min", 0.0))
    if eta_cd_A_W is None:
        margins["eta_CD_A_W_margin_frac"] = float("nan")
    else:
        margins["eta_CD_A_W_margin_frac"] = (eta_cd_A_W - eta_min) / max(abs(eta_min), 1e-30)

    # wallplug envelope (if provided)
    eta_wp_min = float(thr.get("eta_wallplug_min", 0.0))
    if eta_wallplug is None:
        margins["eta_wallplug_margin_frac"] = float("nan")
    else:
        margins["eta_wallplug_margin_frac"] = (eta_wallplug - eta_wp_min) / max(abs(eta_wp_min), 1e-30)

    # power fraction envelope (if electric power known)
    P_frac_max = float(thr.get("P_cd_frac_max", 1.0))
    if P_electric_MW is None or P_electric_MW <= 0.0:
        margins["P_cd_frac_margin_frac"] = float("nan")
        P_frac = float("nan")
    else:
        P_frac = P_cd_MW / max(P_electric_MW, 1e-9)
        margins["P_cd_frac_margin_frac"] = (P_frac_max - P_frac) / max(abs(P_frac_max), 1e-30)

    # LHCD density ceiling proxy
    if tech == "LHCD" and "nbar20_max_proxy" in thr and nbar20 is not None:
        nmax = float(thr.get("nbar20_max_proxy", 1e9))
        margins["lhcd_density_margin_frac"] = (nmax - nbar20) / max(abs(nmax), 1e-30)
    else:
        margins["lhcd_density_margin_frac"] = float("nan")

    # Determine min margin across finite margins
    finite_margins = {k: v for k, v in margins.items() if isinstance(v, float) and math.isfinite(v)}
    if finite_margins:
        top_limiter, min_margin = min(finite_margins.items(), key=lambda kv: kv[1])
    else:
        top_limiter, min_margin = "UNKNOWN", float("nan")

    frag = _fragility_from_min_margin(min_margin, fragile_thr)

    ctx = {
        "cd_tech_regime": tech,
        "P_CD_MW": float(P_cd_MW),
        "eta_CD_A_W": float(eta_cd_A_W) if eta_cd_A_W is not None else float("nan"),
        "eta_wallplug": float(eta_wallplug) if eta_wallplug is not None else float("nan"),
        "P_electric_MW": float(P_electric_MW) if P_electric_MW is not None else float("nan"),
        "P_cd_frac": float(P_frac) if "P_frac" in locals() else float("nan"),
        "nbar20": float(nbar20) if nbar20 is not None else float("nan"),
    }

    return CDTechAuthorityResult(
        cd_tech_regime=tech,
        cd_fragility_class=frag,
        cd_min_margin_frac=min_margin,
        cd_top_limiter=top_limiter,
        margins=margins,
        ctx=ctx,
    )
