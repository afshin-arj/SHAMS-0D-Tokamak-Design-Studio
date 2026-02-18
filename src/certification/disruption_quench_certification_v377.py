"""Disruption severity & quench proxy authority (v377.0.0).

Deterministic, governance-only certification derived from a Systems artifact.
No truth re-evaluation, no solvers, no iteration.

This authority complements the existing *screening* disruption tiering by adding
consequence-severity proxies:

1) Disruptive regime proximity index (dimensionless, 0..1)
   - built from beta-N proximity, q95 proximity, and Greenwald fraction.

2) Thermal quench severity proxy
   - uses stored thermal energy proxy W_MJ and first-wall area A_fw_m2:
       S_th = W_MJ / A_fw_m2  [MJ/m^2]

3) Halo-current / force proxy
   - uses plasma current Ip_MA and B0 (Bt_T) with an explicit halo fraction
     range. Reports proxy force scaling ~ I_halo * B.

The outputs are intended for reviewer-facing governance and design-space
triage, not prediction of real disruptions.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Tuple


def _f(d: Dict[str, Any], key: str, default: float = float("nan")) -> float:
    try:
        return float(d.get(key, default))
    except Exception:
        return float(default)


def _s(d: Dict[str, Any], key: str, default: str = "") -> str:
    try:
        v = d.get(key, default)
        return "" if v is None else str(v)
    except Exception:
        return str(default)


def _design_intent(inputs: Dict[str, Any]) -> str:
    v = _s(inputs, "design_intent", "").strip().lower()
    if not v:
        return "unknown"
    if "react" in v:
        return "reactor"
    if "research" in v:
        return "research"
    return v


@dataclass(frozen=True)
class ProxyPolicy:
    intent: str
    q95_warn: float
    q95_block: float
    fG_warn: float
    fG_block: float
    betaN_warn_frac: float
    betaN_block_frac: float
    halo_frac_nom: float
    halo_frac_hi: float
    Sth_warn_MJ_m2: float
    Sth_block_MJ_m2: float


def _policy(intent: str) -> ProxyPolicy:
    """Explicit conservative policy defaults.

    These are governance thresholds, not empirical predictors.
    Reactor intent is treated more conservatively.
    """
    intent = (intent or "unknown").strip().lower()
    if intent == "research":
        return ProxyPolicy(
            intent="research",
            q95_warn=3.0,
            q95_block=2.5,
            fG_warn=0.90,
            fG_block=1.00,
            betaN_warn_frac=0.85,
            betaN_block_frac=1.00,
            halo_frac_nom=0.20,
            halo_frac_hi=0.30,
            Sth_warn_MJ_m2=2.5,
            Sth_block_MJ_m2=4.0,
        )
    # reactor or unknown
    return ProxyPolicy(
        intent=("reactor" if intent == "reactor" else "unknown"),
        q95_warn=3.2,
        q95_block=2.7,
        fG_warn=0.85,
        fG_block=0.95,
        betaN_warn_frac=0.80,
        betaN_block_frac=0.95,
        halo_frac_nom=0.20,
        halo_frac_hi=0.30,
        Sth_warn_MJ_m2=2.0,
        Sth_block_MJ_m2=3.2,
    )


def _clip01(x: float) -> float:
    if not math.isfinite(x):
        return float("nan")
    return float(max(0.0, min(1.0, x)))


def _dominant_driver(components: Dict[str, float]) -> str:
    best = ("unknown", -1.0)
    for k, v in components.items():
        try:
            fv = float(v)
        except Exception:
            continue
        if math.isfinite(fv) and fv > best[1]:
            best = (k, fv)
    return best[0]


def certify_disruption_quench(
    *,
    outputs: Dict[str, Any],
    inputs: Dict[str, Any],
    run_id: Optional[str] = None,
    inputs_hash: Optional[str] = None,
) -> Dict[str, Any]:
    intent = _design_intent(inputs)
    pol = _policy(intent)

    betaN = _f(outputs, "betaN", float("nan"))
    betaN_max = _f(outputs, "betaN_max", _f(outputs, "betaN_limit", float("nan")))
    q95 = _f(outputs, "q95", _f(outputs, "q95_proxy", float("nan")))
    fG = _f(outputs, "fG", _f(inputs, "fG", float("nan")))

    # Severity-relevant stored energy proxy
    W_MJ = _f(outputs, "W_MJ", float("nan"))
    A_fw_m2 = _f(outputs, "A_fw_m2", float("nan"))
    Sth = float("nan")
    if math.isfinite(W_MJ) and math.isfinite(A_fw_m2) and A_fw_m2 > 0:
        Sth = float(W_MJ / A_fw_m2)  # MJ/m^2

    Ip_MA = _f(outputs, "Ip_MA", float("nan"))
    B0_T = _f(inputs, "Bt_T", _f(outputs, "B0_T", float("nan")))

    # Regime proximity components -> 0..1 risk-like contributions
    comps: Dict[str, float] = {}

    # betaN proximity to limit
    if math.isfinite(betaN) and math.isfinite(betaN_max) and betaN_max > 0:
        frac = betaN / betaN_max
        # 0 at warn_frac, 1 at block_frac (clip)
        comps["betaN"] = _clip01((frac - pol.betaN_warn_frac) / max(pol.betaN_block_frac - pol.betaN_warn_frac, 1e-9))
    else:
        comps["betaN"] = float("nan")

    # q95 proximity (low q worse)
    if math.isfinite(q95) and q95 > 0:
        # 0 at warn, 1 at block
        comps["q95"] = _clip01((pol.q95_warn - q95) / max(pol.q95_warn - pol.q95_block, 1e-9))
    else:
        comps["q95"] = float("nan")

    # Greenwald fraction (high density worse)
    if math.isfinite(fG) and fG >= 0:
        comps["fG"] = _clip01((fG - pol.fG_warn) / max(pol.fG_block - pol.fG_warn, 1e-9))
    else:
        comps["fG"] = float("nan")

    # Composite proximity index (explicit weights)
    weights = {"betaN": 0.45, "q95": 0.35, "fG": 0.20}
    num = 0.0
    den = 0.0
    for k, w in weights.items():
        v = float(comps.get(k, float("nan")))
        if math.isfinite(v):
            num += w * v
            den += w
    prox = float(num / den) if den > 0 else float("nan")

    if math.isfinite(prox):
        if prox < 0.33:
            tier = "LOW"
        elif prox < 0.66:
            tier = "MED"
        else:
            tier = "HIGH"
    else:
        tier = "UNKNOWN"

    # Thermal quench severity tier
    if math.isfinite(Sth):
        if Sth <= pol.Sth_warn_MJ_m2:
            sth_tier = "LOW"
        elif Sth <= pol.Sth_block_MJ_m2:
            sth_tier = "MED"
        else:
            sth_tier = "HIGH"
    else:
        sth_tier = "UNKNOWN"

    # Halo proxy
    halo = {
        "halo_frac_nom": float(pol.halo_frac_nom),
        "halo_frac_hi": float(pol.halo_frac_hi),
        "I_halo_nom_MA": float("nan"),
        "I_halo_hi_MA": float("nan"),
        "F_proxy_nom_MA_T": float("nan"),
        "F_proxy_hi_MA_T": float("nan"),
    }
    if math.isfinite(Ip_MA) and math.isfinite(B0_T):
        I_nom = pol.halo_frac_nom * Ip_MA
        I_hi = pol.halo_frac_hi * Ip_MA
        halo.update(
            {
                "I_halo_nom_MA": float(I_nom),
                "I_halo_hi_MA": float(I_hi),
                "F_proxy_nom_MA_T": float(I_nom * B0_T),
                "F_proxy_hi_MA_T": float(I_hi * B0_T),
            }
        )

    cert: Dict[str, Any] = {
        "authority": {
            "name": "Disruption Severity & Quench Proxy Authority",
            "version": "v377.0.0",
            "scope": "governance-only; no truth execution",
        },
        "provenance": {
            "run_id": (run_id or ""),
            "inputs_hash": (inputs_hash or ""),
        },
        "intent": intent,
        "policy": {
            "q95_warn": float(pol.q95_warn),
            "q95_block": float(pol.q95_block),
            "fG_warn": float(pol.fG_warn),
            "fG_block": float(pol.fG_block),
            "betaN_warn_frac": float(pol.betaN_warn_frac),
            "betaN_block_frac": float(pol.betaN_block_frac),
            "Sth_warn_MJ_m2": float(pol.Sth_warn_MJ_m2),
            "Sth_block_MJ_m2": float(pol.Sth_block_MJ_m2),
            "weights": dict(weights),
            "note": "Explicit conservative thresholds for governance triage; not a disruption predictor.",
        },
        "metrics": {
            "betaN": float(betaN),
            "betaN_max": float(betaN_max),
            "q95": float(q95),
            "fG": float(fG),
            "proximity_components": dict(comps),
            "disruption_proximity_index": float(prox),
            "disruption_proximity_tier": str(tier),
            "dominant_driver": _dominant_driver({k: float(v) for k, v in comps.items() if math.isfinite(float(v))}),
            "W_MJ": float(W_MJ),
            "A_fw_m2": float(A_fw_m2),
            "S_th_MJ_m2": float(Sth),
            "thermal_quench_tier": str(sth_tier),
            "Ip_MA": float(Ip_MA),
            "B0_T": float(B0_T),
            "halo_proxy": halo,
        },
    }
    return cert


def certification_table_rows(cert: Dict[str, Any]) -> Tuple[List[List[Any]], List[str]]:
    m = cert.get("metrics") if isinstance(cert.get("metrics"), dict) else {}
    halo = m.get("halo_proxy") if isinstance(m.get("halo_proxy"), dict) else {}
    rows: List[List[Any]] = []

    # Convenience ratio (safe)
    try:
        _bn = float(m.get("betaN", float("nan")))
        _bnm = float(m.get("betaN_max", float("nan")))
        bn_ratio = (_bn / _bnm) if (math.isfinite(_bn) and math.isfinite(_bnm) and _bnm > 0) else float("nan")
    except Exception:
        bn_ratio = float("nan")

    rows.append(["Intent", cert.get("intent", "")])
    rows.append(["Disruption proximity index", m.get("disruption_proximity_index", float("nan"))])
    rows.append(["Proximity tier", m.get("disruption_proximity_tier", "UNKNOWN")])
    rows.append(["Dominant driver", m.get("dominant_driver", "unknown")])
    rows.append(["βN / βN_max", bn_ratio])
    rows.append(["q95", m.get("q95", float("nan"))])
    rows.append(["fG", m.get("fG", float("nan"))])
    rows.append(["S_th = W/A [MJ/m²]", m.get("S_th_MJ_m2", float("nan"))])
    rows.append(["Thermal quench tier", m.get("thermal_quench_tier", "UNKNOWN")])
    rows.append(["I_halo_nom [MA]", halo.get("I_halo_nom_MA", float("nan"))])
    rows.append(["F_proxy_nom [MA·T]", halo.get("F_proxy_nom_MA_T", float("nan"))])

    return rows, ["Field", "Value"]
