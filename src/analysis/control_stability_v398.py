from __future__ import annotations

"""Control & Stability Authority v398 (governance-only, deterministic).

Purpose
-------
Consolidate existing SHAMS control proxies (CS flux swing, VS/PF/RWM contracts)
into an explicit, audit-ready *ledger* with headroom indices and tiers.

This module is an overlay:
- It does NOT mutate truth.
- It adds derived, reviewer-visible diagnostics and (optionally) explicit caps.

Inputs
------
Uses `inp` plus selected `out_partial` keys that already exist in SHAMS truth outputs:
- cs_flux_required_Wb, cs_flux_available_Wb, cs_flux_margin
- vs_control_power_req_MW, vs_control_power_max_MW, vs_bandwidth_req_Hz, vs_bandwidth_max_Hz, vs_margin
- rwm_chi, rwm_control_power_req_MW, rwm_control_power_max_MW, rwm_bandwidth_req_Hz, rwm_bandwidth_max_Hz
- profile proxy fields from v397 if present: q0_proxy_v397, q95_proxy_v397, li_proxy_v397,
  profile_peaking_p_v397, bootstrap_localization_index_v397

Law compliance
--------------
Single-pass, algebraic, deterministic. No iteration, no smoothing, no hidden search.

Author
------
© 2026 Afshin Arjhangmehr
"""

import math
from typing import Any, Dict


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _b(x: Any) -> bool:
    try:
        return bool(x)
    except Exception:
        return False


def _clamp01(x: float) -> float:
    if not math.isfinite(x):
        return float("nan")
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _headroom(req: float, cap: float) -> float:
    """Return dimensionless headroom: (cap-req)/max(req,eps). NaN if insufficient inputs."""
    if not (math.isfinite(req) and math.isfinite(cap)):
        return float("nan")
    if req <= 0.0:
        return float("nan")
    return (cap - req) / max(req, 1e-12)


def _tier_from_index(idx01: float) -> str:
    if not math.isfinite(idx01):
        return "unknown"
    if idx01 <= 0.33:
        return "benign"
    if idx01 <= 0.66:
        return "watch"
    return "critical"


def evaluate_control_stability_v398(inp: Any, out_partial: Dict[str, Any]) -> Dict[str, Any]:
    enabled = _b(getattr(inp, "include_control_stability_authority_v398", False))
    if not enabled:
        return {"control_stability_v398_enabled": False}

    # Guard: v398 is an overlay of existing control contracts; if those are off, still compute flux ledger.
    include_contracts = _b(getattr(inp, "include_control_contracts", False))

    # --------------------------
    # Volt-second / CS flux ledger
    # --------------------------
    psi_req_Wb = _f(out_partial.get("cs_flux_required_Wb"))
    psi_av_Wb = _f(out_partial.get("cs_flux_available_Wb"))
    cs_margin = _f(out_partial.get("cs_flux_margin"))

    if math.isfinite(psi_req_Wb) and psi_req_Wb > 0.0 and math.isfinite(psi_av_Wb):
        vs_budget_margin = (psi_av_Wb - psi_req_Wb) / max(psi_req_Wb, 1e-12)
    else:
        vs_budget_margin = float("nan")

    # --------------------------
    # Vertical control headroom (power + bandwidth)
    # --------------------------
    vs_p_req = _f(out_partial.get("vs_control_power_req_MW"))
    vs_p_max = _f(out_partial.get("vs_control_power_max_MW"))
    vs_bw_req = _f(out_partial.get("vs_bandwidth_req_Hz"))
    vs_bw_max = _f(out_partial.get("vs_bandwidth_max_Hz"))
    vs_margin = _f(out_partial.get("vs_margin"))

    vde_power_headroom = _headroom(vs_p_req, vs_p_max) if include_contracts else float("nan")
    vde_bw_headroom = _headroom(vs_bw_req, vs_bw_max) if include_contracts else float("nan")

    # Map to a single headroom index (min of power/bw when both finite)
    if math.isfinite(vde_power_headroom) and math.isfinite(vde_bw_headroom):
        vde_headroom = min(vde_power_headroom, vde_bw_headroom)
    else:
        vde_headroom = vde_power_headroom if math.isfinite(vde_power_headroom) else vde_bw_headroom

    if not math.isfinite(vde_headroom):
        vde_tier = "unknown"
    elif vde_headroom >= 0.25:
        vde_tier = "comfortable"
    elif vde_headroom >= 0.0:
        vde_tier = "near_limit"
    else:
        vde_tier = "deficit"

    # --------------------------
    # RWM proximity index (proxy; profile-informed)
    # --------------------------
    rwm_chi = _f(out_partial.get("rwm_chi"))
    # base from chi: map [0.5, 1.0] -> [0,1]
    if math.isfinite(rwm_chi):
        base = (rwm_chi - 0.5) / 0.5
        base = _clamp01(base)
    else:
        base = float("nan")

    # penalties from v397 profile proxies (all optional)
    q0p = _f(out_partial.get("q0_proxy_v397"))
    ppk = _f(out_partial.get("profile_peaking_p_v397"))
    loc = _f(out_partial.get("bootstrap_localization_index_v397"))
    li = _f(out_partial.get("li_proxy_v397"))

    pen = 0.0
    # low q0 is destabilizing (proxy)
    if math.isfinite(q0p):
        pen += 0.20 * (1.0 - _clamp01((q0p - 0.8) / 0.7))  # q0<=0.8 => ~0.2 penalty
    # strong peaking increases proximity (proxy)
    if math.isfinite(ppk):
        pen += 0.20 * _clamp01((ppk - 1.8) / 1.2)  # ppk>=3.0 => full penalty
    # edge-localized bootstrap is destabilizing (proxy)
    if math.isfinite(loc):
        pen += 0.20 * _clamp01((loc - 0.5) / 0.5)
    # very high li increases kink proximity proxy
    if math.isfinite(li):
        pen += 0.10 * _clamp01((li - 1.2) / 0.8)

    if math.isfinite(base):
        rwm_index = _clamp01(base + pen)
    else:
        rwm_index = float("nan")

    rwm_tier = _tier_from_index(rwm_index)

    # Optional explicit caps (recorded so constraints ledger can enforce)
    vs_budget_margin_min = _f(getattr(inp, "vs_budget_margin_min_v398", float("nan")))
    vde_headroom_min = _f(getattr(inp, "vde_headroom_min_v398", float("nan")))
    rwm_index_max = _f(getattr(inp, "rwm_proximity_index_max_v398", float("nan")))

    return {
        "control_stability_v398_enabled": True,
        # Volt-second / CS flux ledger
        "psi_available_Vs_v398": psi_av_Wb,  # Wb == V*s
        "psi_required_Vs_v398": psi_req_Wb,
        "cs_flux_margin_v398": cs_margin,
        "vs_budget_margin_v398": float(vs_budget_margin),
        "vs_budget_margin_min_v398": float(vs_budget_margin_min),
        # Vertical control headroom
        "vde_headroom_v398": float(vde_headroom),
        "vde_headroom_tier_v398": vde_tier,
        "vde_headroom_min_v398": float(vde_headroom_min),
        "vs_margin_v398": float(vs_margin),
        "vde_power_headroom_v398": float(vde_power_headroom),
        "vde_bw_headroom_v398": float(vde_bw_headroom),
        # RWM proximity overlay
        "rwm_proximity_index_v398": float(rwm_index),
        "rwm_proximity_tier_v398": rwm_tier,
        "rwm_proximity_index_max_v398": float(rwm_index_max),
        # Provenance
        "control_stability_v398_authority": "ledger_overlay_profile_informed",
    }
