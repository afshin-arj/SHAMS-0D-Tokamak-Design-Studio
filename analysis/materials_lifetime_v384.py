from __future__ import annotations

"""Materials & Lifetime Tightening closure (v384.0.0).

This module is deliberately placed under the repo-root `analysis/` namespace because
SHAMS runtime wiring imports `analysis.*` from repo root (see src/physics/hot_ion.py).

Purpose
-------
Provide deterministic, algebraic, post-processing-only proxies for:

  - divertor lifetime (q_div-based proxy)
  - magnet lifetime (margin-based proxy)
  - downtime-coupled capacity factor
  - annualized replacement cost-rate proxy (adds to v367 closure when available)

No solvers. No iteration. No hidden relaxation.

Author: © 2026 Afshin Arjhangmehr
"""

import math
from typing import Any, Dict, Mapping, Tuple


def _finite(x: float) -> bool:
    return (x == x) and (x != float("inf")) and (x != -float("inf"))


def _sf(outputs: Mapping[str, Any], key: str, default: float = float("nan")) -> float:
    try:
        return float(outputs.get(key, default))
    except Exception:
        return float(default)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _years_from_q_proxy(q: float, ref_yr: float, q_ref: float, exp: float) -> float:
    if not (_finite(q) and q > 0.0 and _finite(ref_yr) and _finite(q_ref) and q_ref > 0.0 and _finite(exp)):
        return float("nan")
    q_eff = max(q, 1e-6)
    return ref_yr * (q_ref / q_eff) ** exp


def _magnet_margin_fraction(outputs: Mapping[str, Any]) -> float:
    """Best-effort, deterministic margin fraction proxy.

    Preference order:
      1) HTS/LTS unified operating margin key `hts_margin` (ratio-like; convert to fractional headroom)
      2) stress margin fraction from tf_stress_margin_MPa / tf_stress_allow_MPa
    """
    m_sc = _sf(outputs, "hts_margin")
    m_sc_frac = float("nan")
    if _finite(m_sc):
        # Many SHAMS bundles treat margin as a multiplicative ratio where >=1 is acceptable.
        # Convert to a fractional headroom in [0,1): (m-1)/m, clamped.
        if m_sc > 0.0:
            m_sc_frac = _clamp((m_sc - 1.0) / max(m_sc, 1e-9), 0.0, 0.99)

    stress_margin = _sf(outputs, "tf_stress_margin_MPa")
    stress_allow = _sf(outputs, "tf_stress_allow_MPa")
    m_stress_frac = float("nan")
    if _finite(stress_margin) and _finite(stress_allow) and stress_allow > 0.0:
        m_stress_frac = _clamp(stress_margin / stress_allow, 0.0, 0.99)

    # Combine conservatively (minimum of finite proxies)
    cands = [v for v in [m_sc_frac, m_stress_frac] if _finite(v)]
    return min(cands) if cands else float("nan")


def compute_materials_lifetime_tightening_v384(outputs: Mapping[str, Any], inp: Any) -> Dict[str, Any]:
    """Compute v384 post-processing outputs.

    Required upstream keys (best-effort; NaN allowed):
      - q_div_MW_m2 or q_par_MW_m2
      - CAPEX_structured_MUSD or CAPEX_proxy_MUSD (optional; for replacement cost proxy)
      - v367 closure outputs (optional): replacement_cost_MUSD_per_year_total

    Returns a dict of v384 keys used by certification + economics preference.
    """
    enabled = bool(getattr(inp, "include_materials_lifetime_v384", False))
    if not enabled:
        return {"include_materials_lifetime_v384": False}

    # --- Divertor lifetime proxy ---
    q_div = _sf(outputs, "q_div_MW_m2")
    if not _finite(q_div):
        q_div = _sf(outputs, "q_par_MW_m2")
    div_ref_yr = float(getattr(inp, "divertor_life_ref_yr", 3.0))
    div_q_ref = float(getattr(inp, "divertor_q_ref_MW_m2", 10.0))
    div_exp = float(getattr(inp, "divertor_q_exp", 2.0))
    div_life = _years_from_q_proxy(q_div, div_ref_yr, div_q_ref, div_exp)

    # --- Magnet lifetime proxy ---
    m_frac = _magnet_margin_fraction(outputs)
    mag_ref_yr = float(getattr(inp, "magnet_life_ref_yr", 30.0))
    mag_m_ref = float(getattr(inp, "magnet_margin_ref", 0.10))
    mag_exp = float(getattr(inp, "magnet_margin_exp", 1.5))
    mag_life = float("nan")
    if _finite(m_frac) and _finite(mag_ref_yr) and _finite(mag_m_ref) and mag_m_ref > 0.0 and _finite(mag_exp):
        mag_life = mag_ref_yr * (max(m_frac, 1e-9) / mag_m_ref) ** mag_exp

    # --- Intervals from v367 (FW/blanket) if present ---
    fw_int = _sf(outputs, "fw_replace_interval_y_v367")
    bl_int = _sf(outputs, "blanket_replace_interval_y_v367")
    # If not available, use lifetimes directly when present
    if not _finite(fw_int):
        fw_int = _sf(outputs, "fw_lifetime_yr")
    if not _finite(bl_int):
        bl_int = _sf(outputs, "blanket_lifetime_yr")

    intervals: Dict[str, float] = {
        "fw": fw_int,
        "blanket": bl_int,
        "divertor": div_life,
        "magnet": mag_life,
    }
    finite_intervals = {k: v for k, v in intervals.items() if _finite(v) and v > 0.0}
    if finite_intervals:
        limiting_component, repl_interval = min(finite_intervals.items(), key=lambda kv: kv[1])
    else:
        limiting_component, repl_interval = "unknown", float("nan")

    # --- Downtime coupling ---
    base_cf = float(getattr(inp, "base_capacity_factor", 0.75))
    cf_max = float(getattr(inp, "capacity_factor_max", 0.95))
    base_cf = _clamp(base_cf, 0.0, 1.0) if _finite(base_cf) else 0.75
    cf_max = _clamp(cf_max, 0.0, 1.0) if _finite(cf_max) else 0.95

    dt_frac = 0.0
    # Sum downtime/interval across finite components
    for comp, interval_y in finite_intervals.items():
        days_key = f"{comp}_downtime_days"
        dt_days = float(getattr(inp, days_key, float("nan")))
        if _finite(dt_days) and dt_days > 0.0:
            dt_frac += dt_days / (interval_y * 365.0)

    dt_frac = _clamp(dt_frac, 0.0, 0.95) if _finite(dt_frac) else float("nan")
    cf_used = float("nan")
    if _finite(dt_frac):
        cf_used = _clamp(base_cf * (1.0 - dt_frac), 0.0, cf_max)

    # --- Replacement annualized cost proxy ---
    # Start with v367 replacement cost total if present; add divertor replacement contribution.
    rc_v367 = _sf(outputs, "replacement_cost_MUSD_per_year_total")
    total_capex = _sf(outputs, "CAPEX_structured_MUSD")
    if not _finite(total_capex):
        total_capex = _sf(outputs, "CAPEX_proxy_MUSD")
    install = float(getattr(inp, "replacement_installation_factor", 1.15))
    install = max(1.0, install) if _finite(install) else 1.15

    div_capex_frac = float(getattr(inp, "divertor_capex_fraction_of_total", 0.05))
    div_capex_frac = _clamp(div_capex_frac, 0.0, 1.0) if _finite(div_capex_frac) else 0.05

    div_cost = float("nan")
    if _finite(total_capex) and _finite(div_life) and div_life > 0.0:
        div_cost = (total_capex * div_capex_frac * install) / div_life

    rc_total = float("nan")
    parts = []
    if _finite(rc_v367):
        parts.append(rc_v367)
    if _finite(div_cost):
        parts.append(div_cost)
    if parts:
        rc_total = sum(parts)

    return {
        "include_materials_lifetime_v384": True,
        "limiting_component_v384": limiting_component,
        "replacement_interval_y_v384": repl_interval,
        "divertor_lifetime_yr_v384": div_life,
        "magnet_lifetime_yr_v384": mag_life,
        "replacement_downtime_fraction_v384": dt_frac,
        "capacity_factor_used_v384": cf_used,
        "replacement_cost_MUSD_per_year_v384": rc_total,
    }
