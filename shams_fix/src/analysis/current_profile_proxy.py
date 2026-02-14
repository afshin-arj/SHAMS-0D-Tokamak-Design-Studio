"""
SHAMS — Current Profile Proxy Authority (v345)
Author: © 2026 Afshin Arjhangmehr

Deterministic post-processing authority to assess current-profile / non-inductive plausibility
using existing proxy outputs (q95, qmin proxy, bootstrap fraction proxy, CD proxy outputs).
No solvers. No iteration. No internal optimization. Pure margin evaluation + regime labeling.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import math


def _sf(x: Any) -> float:
    try:
        v = float(x)
        return v
    except Exception:
        return float("nan")


def _finite(x: float) -> bool:
    return isinstance(x, float) and math.isfinite(x)


def _margin_frac(value: float, limit: float, sense: str) -> float:
    """
    Signed fractional margin:
      - sense == 'min' : (value/limit - 1)
      - sense == 'max' : (1 - value/limit)
    Returns NaN if undefined.
    """
    if not (_finite(value) and _finite(limit)) or limit == 0.0:
        return float("nan")
    r = value / limit
    if sense == "min":
        return float(r - 1.0)
    if sense == "max":
        return float(1.0 - r)
    return float("nan")


def _select_first(out: Dict[str, Any], keys: list[str]) -> float:
    for k in keys:
        if k in out:
            v = _sf(out.get(k))
            if _finite(v):
                return v
    return float("nan")


def _regime_from_fni(fni: float) -> str:
    if not _finite(fni):
        return "unknown"
    if fni < 0.35:
        return "inductive"
    if fni < 0.75:
        return "hybrid"
    return "steady_state"


@dataclass(frozen=True)
class CurrentProfileProxyResult:
    regime: str
    fragility_class: str
    min_margin_frac: float
    top_limiter: str
    margins: Dict[str, float]
    context: Dict[str, Any]


def evaluate_current_profile_proxy(out: Dict[str, Any], contract: Any) -> CurrentProfileProxyResult:
    thr = getattr(contract, "regimes", {}) or {}
    fragile_thr = float(getattr(contract, "fragile_margin_frac", 0.05))
    ni_tol = float(getattr(contract, "ni_consistency_tol_frac", 0.08))

    # Pull key proxies / outputs
    q95 = _select_first(out, ["q95_proxy", "q95", "q95_proxy_v", "q95_val"])
    qmin = _select_first(out, ["profile_qmin_proxy", "qmin_proxy", "qmin"])
    fbs = _select_first(out, ["profile_f_bootstrap_proxy", "f_bs_proxy", "f_bs_proxy"])
    fni = _select_first(out, ["f_NI", "f_ni", "fNI"])
    Ip = _select_first(out, ["Ip_MA", "I_p_MA", "Ip"])
    Icd = _select_first(out, ["I_cd_MA", "Icd_MA"])
    Pcd = _select_first(out, ["P_cd_MW", "Pcd_MW"])
    eta = _select_first(out, ["cd_eta_A_per_W", "eta_cd_A_per_W", "cd_eta"])

    # Best-effort bootstrap current
    Ibs = _select_first(out, ["I_bs_MA", "I_bootstrap_MA", "Ibs_MA"])
    if (not _finite(Ibs)) and _finite(fbs) and _finite(Ip) and Ip > 0:
        Ibs = fbs * Ip

    # Regime classification
    regime = _regime_from_fni(fni)
    reg = dict(thr.get(regime, {}) or {})

    margins: Dict[str, float] = {}

    # q95 minimum
    q95_min = _sf(reg.get("q95_min", float("nan")))
    margins["CP_Q95_MIN"] = _margin_frac(q95, q95_min, "min")

    # qmin minimum
    qmin_min = _sf(reg.get("qmin_proxy_min", float("nan")))
    margins["CP_QMIN_MIN"] = _margin_frac(qmin, qmin_min, "min")

    # bootstrap min/max
    fbs_min = _sf(reg.get("f_bootstrap_proxy_min", float("nan")))
    fbs_max = _sf(reg.get("f_bootstrap_proxy_max", float("nan")))
    margins["CP_FBS_MIN"] = _margin_frac(fbs, fbs_min, "min")
    margins["CP_FBS_MAX"] = _margin_frac(fbs, fbs_max, "max")

    # NI fraction bounds (if available)
    fni_min = _sf(reg.get("f_NI_min", float("nan")))
    fni_max = _sf(reg.get("f_NI_max", float("nan")))
    margins["CP_FNI_MIN"] = _margin_frac(fni, fni_min, "min")
    margins["CP_FNI_MAX"] = _margin_frac(fni, fni_max, "max")

    # CD efficiency (optional; allow 0 min by default)
    eta_min = _sf(reg.get("cd_eta_min_A_per_W", float("nan")))
    margins["CP_ETA_CD_MIN"] = _margin_frac(eta, eta_min, "min")

    # CD power fraction max (relative to total heating input if available)
    P_in = _select_first(out, ["Pin_MW", "P_in_MW", "Paux_MW", "P_aux_MW"])
    pfrac = float("nan")
    if _finite(Pcd) and _finite(P_in) and P_in > 0:
        pfrac = Pcd / P_in
    pfrac_max = _sf(reg.get("P_cd_frac_max", float("nan")))
    margins["CP_PCD_FRAC_MAX"] = _margin_frac(pfrac, pfrac_max, "max")

    # NI consistency margin: compare Ip with Ibs+Icd (best-effort). If inductive: allow OH current.
    ni_cons = float("nan")
    if _finite(Ip) and Ip > 0 and _finite(Ibs) and _finite(Icd):
        if regime == "inductive":
            # allow remaining fraction as OH; consistency is only that non-inductive does not exceed Ip too much
            frac = (Ibs + Icd) / Ip
            # exceed margin: want frac <= 1 + ni_tol
            ni_cons = (1.0 + ni_tol) - frac
        else:
            # in non-inductive regimes, want Ip ≈ Ibs+Icd within tolerance
            frac_err = abs(Ip - (Ibs + Icd)) / Ip
            ni_cons = ni_tol - frac_err
    margins["CP_NI_CONSISTENCY"] = ni_cons

    # Determine min margin across finite ones
    finite_margins = {k: v for k, v in margins.items() if _finite(v)}
    if finite_margins:
        top_limiter = min(finite_margins, key=lambda k: finite_margins[k])
        min_margin = float(finite_margins[top_limiter])
        if min_margin < 0.0:
            cls = "INFEASIBLE"
        elif min_margin < fragile_thr:
            cls = "FRAGILE"
        else:
            cls = "FEASIBLE"
    else:
        top_limiter = "UNKNOWN"
        min_margin = float("nan")
        cls = "UNKNOWN"

    context = {
        "q95": q95,
        "qmin_proxy": qmin,
        "f_bootstrap_proxy": fbs,
        "f_NI": fni,
        "Ip_MA": Ip,
        "I_bs_MA": Ibs,
        "I_cd_MA": Icd,
        "P_cd_MW": Pcd,
        "cd_eta_A_per_W": eta,
        "P_in_MW": P_in,
        "P_cd_frac": pfrac,
    }

    return CurrentProfileProxyResult(
        regime=regime,
        fragility_class=cls,
        min_margin_frac=min_margin,
        top_limiter=top_limiter,
        margins=margins,
        context=context,
    )

