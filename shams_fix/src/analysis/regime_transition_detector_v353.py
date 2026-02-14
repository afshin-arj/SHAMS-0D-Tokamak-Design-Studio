from __future__ import annotations

"""v353.0 — Regime Transition Detector (post-processing).

SHAMS law:
  - Must NOT modify frozen truth.
  - Deterministic, algebraic classification only.

This detector produces *labels* and *near-boundary flags* using existing
outputs from the frozen evaluator plus explicit authority overlays.
It never invokes solvers and never iterates.

The detector is intentionally defensive: if a required diagnostic key is
missing, that sub-detector reports UNKNOWN rather than guessing.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional
import math


def _f(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _b(x: Any) -> Optional[bool]:
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)) and math.isfinite(float(x)):
        return bool(int(x))
    if isinstance(x, str):
        s = x.strip().lower()
        if s in {"true", "t", "yes", "y", "1"}:
            return True
        if s in {"false", "f", "no", "n", "0"}:
            return False
    return None


@dataclass(frozen=True)
class RegimeTransitions:
    schema_version: str
    summary: str
    labels: Dict[str, str]
    near_boundaries: List[Dict[str, Any]]
    context: Dict[str, Any]


def evaluate_regime_transitions(
    *,
    inputs: Mapping[str, Any],
    outputs: Mapping[str, Any],
    tolerances: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    """Compute deterministic regime labels and proximity flags.

    Parameters
    ----------
    inputs/outputs:
        Frozen Point Designer inputs and evaluator outputs.
    tolerances:
        Optional per-boundary proximity windows.

    Returns
    -------
    Dict[str, Any]
        JSON-serializable regime transition report.
    """

    tol = {
        # proximity windows
        "greenwald_near": 0.05,  # |f_GW - 1| <= 0.05
        "greenwald_warn": 0.10,  # |f_GW - 1| <= 0.10
        "betaN_near": 0.10,  # within 10% of betaN limit proxy
    }
    if isinstance(tolerances, Mapping):
        for k, v in tolerances.items():
            try:
                tol[str(k)] = float(v)
            except Exception:
                pass

    labels: Dict[str, str] = {}
    near: List[Dict[str, Any]] = []
    ctx: Dict[str, Any] = {}

    # --- Confinement proxy (L/H) ---
    # Prefer explicit boolean if present.
    hmode = _b(outputs.get("is_H_mode", outputs.get("H_mode", outputs.get("h_mode"))))
    if hmode is None:
        # Fall back to H-factor proxy naming conventions.
        H98 = _f(outputs.get("H98"))
        if math.isfinite(H98):
            # Not a hard rule; used as a label only.
            labels["confinement_regime"] = "H-LIKE" if H98 >= 1.0 else "L-LIKE"
            ctx["H98"] = H98
            if 0.95 <= H98 <= 1.05:
                near.append({"boundary": "H98≈1", "metric": "H98", "value": H98, "window": 0.05, "note": "Confinement near H98=1 proxy boundary."})
        else:
            labels["confinement_regime"] = "UNKNOWN"
    else:
        labels["confinement_regime"] = "H" if hmode else "L"
        ctx["is_H_mode"] = bool(hmode)

    # --- Exhaust regime (attached/detached) ---
    det = _b(outputs.get("is_detached", outputs.get("detached", outputs.get("detachment_active"))))
    if det is None:
        # Fall back to heat-flux proxy if available.
        qdiv = _f(outputs.get("q_div_MW_m2", outputs.get("q_div_MW_m2_base")))
        if math.isfinite(qdiv):
            labels["exhaust_regime"] = "ATTACHED-LIKE" if qdiv > 5.0 else "DETACHED-LIKE"
            ctx["q_div_MW_m2_proxy"] = qdiv
            if 4.0 <= qdiv <= 6.0:
                near.append({"boundary": "q_div≈5 MW/m2", "metric": "q_div_MW_m2", "value": qdiv, "window": 1.0, "note": "Heuristic attached/detached proxy transition."})
        else:
            labels["exhaust_regime"] = "UNKNOWN"
    else:
        labels["exhaust_regime"] = "DETACHED" if det else "ATTACHED"
        ctx["is_detached"] = bool(det)

    # --- Magnet technology regime (LTS/HTS/Cu) ---
    mag = outputs.get("magnet_regime", outputs.get("magnet_tech_regime", inputs.get("magnet_regime")))
    if isinstance(mag, str) and mag.strip():
        labels["magnet_regime"] = mag.strip().upper()
    else:
        # Try boolean hints
        is_hts = _b(outputs.get("is_HTS", inputs.get("use_HTS")))
        if is_hts is not None:
            labels["magnet_regime"] = "HTS" if is_hts else "LTS"
        else:
            labels["magnet_regime"] = "UNKNOWN"

    # --- Density-limit proximity (Greenwald fraction) ---
    fgw = _f(outputs.get("f_GW", outputs.get("f_Gw", outputs.get("nbar_over_nGw", outputs.get("nGW")))) )
    # Note: some models use nGW as absolute; only treat as fraction if plausible.
    if math.isfinite(fgw):
        if fgw > 3.0:
            # Likely absolute density, not a fraction.
            labels["greenwald_state"] = "UNKNOWN"
        else:
            labels["greenwald_state"] = (
                "SAFE" if fgw < 0.7 else "APPROACH" if fgw < 0.9 else "NEAR_LIMIT" if fgw <= 1.0 else "VIOLATED"
            )
            ctx["f_GW"] = fgw
            if abs(fgw - 1.0) <= tol["greenwald_near"]:
                near.append({"boundary": "Greenwald", "metric": "f_GW", "value": fgw, "window": tol["greenwald_near"], "note": "Within near window of f_GW=1."})
            elif abs(fgw - 1.0) <= tol["greenwald_warn"]:
                near.append({"boundary": "Greenwald", "metric": "f_GW", "value": fgw, "window": tol["greenwald_warn"], "note": "Within warning window of f_GW=1."})
    else:
        labels["greenwald_state"] = "UNKNOWN"

    # --- Beta_N proximity to limit proxy (Troyon/contract) ---
    betaN = _f(outputs.get("beta_N"))
    betaN_lim = _f(outputs.get("betaN_limit", outputs.get("beta_N_limit")))
    if math.isfinite(betaN) and math.isfinite(betaN_lim) and betaN_lim > 0.0:
        frac = betaN / betaN_lim
        ctx["beta_N"] = betaN
        ctx["betaN_limit"] = betaN_lim
        labels["betaN_state"] = "SAFE" if frac < 0.9 else "NEAR_LIMIT" if frac <= 1.0 else "VIOLATED"
        if abs(frac - 1.0) <= tol["betaN_near"]:
            near.append({"boundary": "beta_N", "metric": "beta_N/betaN_limit", "value": frac, "window": tol["betaN_near"], "note": "Within 10% of beta_N limit proxy."})
    else:
        labels["betaN_state"] = labels.get("betaN_state", "UNKNOWN")

    # Summary string
    parts = []
    for k in ("confinement_regime", "exhaust_regime", "magnet_regime", "greenwald_state", "betaN_state"):
        if k in labels:
            parts.append(f"{k}={labels[k]}")
    summary = "; ".join(parts) if parts else "Regime transitions unavailable."

    rep = RegimeTransitions(
        schema_version="regime_transitions.v353",
        summary=summary,
        labels=labels,
        near_boundaries=near,
        context=ctx,
    )
    return {
        "schema_version": rep.schema_version,
        "regime_summary": rep.summary,
        "labels": rep.labels,
        "near_boundaries": rep.near_boundaries,
        "context": rep.context,
    }
