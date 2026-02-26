from __future__ import annotations

"""Magnet Technology Authority v400 (governance-only, deterministic).

Purpose
-------
Provide an explicit, audit-ready margin ledger for TF magnet feasibility across
technology regimes (LTS/HTS/Cu), leveraging existing TF coil proxies and the
magnet_tech_contract limits.

This module is an overlay:
- It does NOT mutate truth.
- It computes reviewer-visible margins and tiers (B-T-J-stress-quench).
- It optionally exposes explicit caps via input knobs handled by constraints.

Inputs (expected keys)
----------------------
From `inp`:
- magnet_technology (string)
- Tcoil_K
- optional v400 caps: magnet_margin_min_v400, b_margin_min_v400, j_margin_min_v400,
  stress_margin_min_v400, sc_margin_min_v400, t_margin_min_v400, p_tf_ohmic_margin_min_v400

From `out_partial` (truth outputs computed earlier):
- B_peak_T
- J_eng_A_mm2
- sigma_vm_MPa
- sigma_allow_MPa (from contract/inputs)
- B_peak_allow_T (from contract/inputs)
- J_eng_max_A_mm2 (from contract)
- hts_margin (unified SC margin proxy for LTS/HTS; NaN for copper)
- hts_margin_min (from contract)
- Tcoil_min_K, Tcoil_max_K (from contract)
- P_tf_ohmic_MW (copper only; NaN otherwise)
- P_tf_ohmic_max_MW (from contract; copper regime)

Law compliance
--------------
Single-pass, algebraic, deterministic. No iteration. No smoothing. No hidden search.

Author
------
© 2026 Afshin Arjhangmehr
"""

import math
from typing import Any, Dict


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        v = float(x)
        return v
    except Exception:
        return float(default)


def _finite(x: float) -> bool:
    return x == x and math.isfinite(x)


def _ratio_margin(allow: float, req: float) -> float:
    """Return (allow/req - 1). NaN if not computable."""
    a = _f(allow)
    r = _f(req)
    if not (_finite(a) and _finite(r)):
        return float("nan")
    if r <= 0.0:
        return float("nan")
    return a / r - 1.0


def _tier_from_margin(m: float, fragile: float = 0.05) -> str:
    if not _finite(m):
        return "unknown"
    if m < 0.0:
        return "deficit"
    if m < fragile:
        return "near_limit"
    return "comfortable"


def compute(inp: Any, out_partial: Dict[str, Any]) -> Dict[str, Any]:
    tech = str(getattr(inp, "magnet_technology", "" ) or "").strip().upper() or "UNKNOWN"

    Bpk = _f(out_partial.get("B_peak_T"))
    Ballow = _f(out_partial.get("B_peak_allow_T"))
    Jreq = _f(out_partial.get("J_eng_A_mm2"))
    Jallow = _f(out_partial.get("J_eng_max_A_mm2"))
    sig = _f(out_partial.get("sigma_vm_MPa"))
    sig_allow = _f(out_partial.get("sigma_allow_MPa"))
    sc_margin = _f(out_partial.get("hts_margin"))
    sc_margin_min = _f(out_partial.get("hts_margin_min"), 1.0)

    Tcoil = _f(out_partial.get("Tcoil_K"), _f(getattr(inp, "Tcoil_K", float("nan"))))
    Tmin = _f(out_partial.get("Tcoil_min_K"))
    Tmax = _f(out_partial.get("Tcoil_max_K"))

    # Margins
    b_margin = _ratio_margin(Ballow, Bpk)
    j_margin = _ratio_margin(Jallow, Jreq)
    stress_margin = _ratio_margin(sig_allow, sig)

    # Superconducting operating margin (already a ratio-like quantity)
    sc_oper_margin = float("nan")
    if _finite(sc_margin) and _finite(sc_margin_min) and sc_margin_min > 0.0:
        sc_oper_margin = sc_margin / sc_margin_min - 1.0

    # Temperature window margin: min distance to window edges, normalized by window span
    t_margin = float("nan")
    if _finite(Tcoil) and _finite(Tmin) and _finite(Tmax) and Tmax > Tmin:
        t_margin = min((Tcoil - Tmin) / (Tmax - Tmin), (Tmax - Tcoil) / (Tmax - Tmin))

    # Copper ohmic power margin (if applicable)
    P_ohmic = _f(out_partial.get("P_tf_ohmic_MW"))
    P_ohmic_max = _f(out_partial.get("P_tf_ohmic_max_MW"))
    p_tf_ohmic_margin = _ratio_margin(P_ohmic_max, P_ohmic)

    # Combined margin (min of available margins that are finite)
    margins = [b_margin, j_margin, stress_margin, sc_oper_margin, t_margin]
    if tech == "COPPER":
        margins.append(p_tf_ohmic_margin)
    finite_margins = [m for m in margins if _finite(m)]
    magnet_margin = min(finite_margins) if finite_margins else float("nan")

    # Tiers (use contract fragile margin if available)
    fragile = _f(out_partial.get("fragile_margin_frac"), 0.05)
    tier = _tier_from_margin(magnet_margin, fragile=fragile)

    out: Dict[str, Any] = {}
    out["magnet_v400_technology"] = tech
    out["magnet_v400_b_margin"] = float(b_margin)
    out["magnet_v400_j_margin"] = float(j_margin)
    out["magnet_v400_stress_margin"] = float(stress_margin)
    out["magnet_v400_sc_oper_margin"] = float(sc_oper_margin)
    out["magnet_v400_t_window_margin"] = float(t_margin)
    out["magnet_v400_p_tf_ohmic_margin"] = float(p_tf_ohmic_margin)
    out["magnet_v400_margin"] = float(magnet_margin)
    out["magnet_v400_tier"] = str(tier)

    # Per-aspect tiers for dominance explanation in UI
    out["magnet_v400_b_tier"] = _tier_from_margin(b_margin, fragile=fragile)
    out["magnet_v400_j_tier"] = _tier_from_margin(j_margin, fragile=fragile)
    out["magnet_v400_stress_tier"] = _tier_from_margin(stress_margin, fragile=fragile)
    out["magnet_v400_sc_tier"] = _tier_from_margin(sc_oper_margin, fragile=fragile)
    out["magnet_v400_t_window_tier"] = _tier_from_margin(t_margin, fragile=fragile)
    out["magnet_v400_p_tf_ohmic_tier"] = _tier_from_margin(p_tf_ohmic_margin, fragile=fragile)

    # Dominant limiter (min margin among finite)
    labels = [
        ("B_peak", b_margin),
        ("J_eng", j_margin),
        ("stress", stress_margin),
        ("sc_oper", sc_oper_margin),
        ("T_window", t_margin),
    ]
    if tech == "COPPER":
        labels.append(("P_tf_ohmic", p_tf_ohmic_margin))
    finite_labels = [(k, m) for (k, m) in labels if _finite(m)]
    if finite_labels:
        k_min, m_min = min(finite_labels, key=lambda km: km[1])
        out["magnet_v400_dominant_limiter"] = str(k_min)
        out["magnet_v400_dominant_margin"] = float(m_min)
    else:
        out["magnet_v400_dominant_limiter"] = "unknown"
        out["magnet_v400_dominant_margin"] = float("nan")

    return out


def evaluate_magnet_technology_authority_v400(inp: Any, out_partial: Dict[str, Any]) -> Dict[str, Any]:
    enabled = bool(getattr(inp, "include_magnet_technology_authority_v400", True))
    if not enabled:
        return {"magnet_v400_enabled": False}
    out = compute(inp, out_partial)
    out["magnet_v400_enabled"] = True
    return out
