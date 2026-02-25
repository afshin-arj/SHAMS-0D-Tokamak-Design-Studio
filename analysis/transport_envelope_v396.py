from __future__ import annotations

"""Transport Envelope 2.0 Authority (v396.0).

Deterministic, algebraic, post-processing-only transport credibility envelope.

Design intent
------------
- Compute an envelope over multiple τE scalings (min/max) and the spread ratio.
- Provide a deterministic credibility tier based on spread.
- Optionally expose a feasibility constraint on spread via a user-provided cap.
- MUST NOT modify the frozen-truth operating point.

© 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import math

from phase1_models import (
    tauE_ipb98y2,
    tauE_iter89p,
)

# ----------------------------
# User scaling (optional)
# ----------------------------

def tauE_user_powerlaw_s(
    *,
    C: float,
    Ip_MA: float,
    Bt_T: float,
    ne20: float,
    Ploss_MW: float,
    R_m: float,
    a_m: float,
    kappa: float,
    M_amu: float,
    exp_Ip: float,
    exp_Bt: float,
    exp_ne: float,
    exp_Ploss: float,
    exp_R: float,
    exp_eps: float,
    exp_kappa: float,
    exp_M: float,
) -> float:
    """Generic power-law confinement time [s].

    τE = C * Ip^a * Bt^b * ne^c * Ploss^d * R^e * (a/R)^f * kappa^g * M^h

    Units are consistent with the standard global scalings used in SHAMS.
    """
    eps = float(a_m) / max(float(R_m), 1e-12)
    return float(C) * (float(Ip_MA) ** float(exp_Ip)) * (float(Bt_T) ** float(exp_Bt)) * (float(ne20) ** float(exp_ne)) * (
        float(Ploss_MW) ** float(exp_Ploss)
    ) * (float(R_m) ** float(exp_R)) * (eps ** float(exp_eps)) * (float(kappa) ** float(exp_kappa)) * (float(M_amu) ** float(exp_M))


def _credibility_tier_from_spread(spread_ratio: float) -> str:
    """Deterministic spread-tier mapping (no smoothing)."""
    s = float(spread_ratio)
    if not math.isfinite(s) or s <= 0.0:
        return "unknown"
    if s <= 1.5:
        return "tight"
    if s <= 2.5:
        return "moderate"
    if s <= 4.0:
        return "weak"
    return "fragile"


def evaluate_transport_envelope_v396(
    *,
    inp: Any,
    out_partial: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute Transport Envelope 2.0 results (v396).

    Inputs (consumed from inp / out_partial):
      - Geometry / operation: R0_m, a_m, kappa, Bt_T, Ip_MA
      - ne20, Pin_MW or Ploss surrogate
      - M_amu (optional; default 2.5)

    Returns keys are prefixed with v396 tags to avoid collisions.
    """
    enabled = bool(getattr(inp, "include_transport_envelope_v396", True))

    if not enabled:
        return {
            "transport_envelope_v396_enabled": False,
        }

    # Pull required parameters deterministically
    Ip_MA = float(getattr(inp, "Ip_MA", float("nan")))
    Bt_T = float(getattr(inp, "Bt_T", float("nan")))
    R_m = float(getattr(inp, "R0_m", float("nan")))
    a_m = float(getattr(inp, "a_m", float("nan")))
    kappa = float(getattr(inp, "kappa", float("nan")))
    M_amu = float(getattr(inp, "M_amu", 2.5) or 2.5)

    ne20 = float(out_partial.get("ne20", float("nan")))
    # Use Pin_MW or Ploss proxy if provided
    Ploss_MW = float(out_partial.get("Pin_MW", out_partial.get("P_SOL_MW", float("nan"))))

    scalings: List[Tuple[str, float]] = []

    def add(name: str, val: float) -> None:
        if math.isfinite(val) and val > 0.0:
            scalings.append((name, float(val)))

    # Baseline library scalings
    add("IPB98(y,2)", tauE_ipb98y2(Ip_MA, Bt_T, ne20, Ploss_MW, R_m, a_m, kappa, M_amu))
    add("ITER89-P", tauE_iter89p(Ip_MA, Bt_T, ne20, Ploss_MW, R_m, a_m, kappa, M_amu))

    # Optional user scaling vector
    include_user = bool(getattr(inp, "include_tauE_user_scaling_v396", False))
    if include_user:
        C = float(getattr(inp, "tauE_user_C_v396", float("nan")))
        exps = {
            "exp_Ip": float(getattr(inp, "tauE_user_exp_Ip_v396", float("nan"))),
            "exp_Bt": float(getattr(inp, "tauE_user_exp_Bt_v396", float("nan"))),
            "exp_ne": float(getattr(inp, "tauE_user_exp_ne_v396", float("nan"))),
            "exp_Ploss": float(getattr(inp, "tauE_user_exp_Ploss_v396", float("nan"))),
            "exp_R": float(getattr(inp, "tauE_user_exp_R_v396", float("nan"))),
            "exp_eps": float(getattr(inp, "tauE_user_exp_eps_v396", float("nan"))),
            "exp_kappa": float(getattr(inp, "tauE_user_exp_kappa_v396", float("nan"))),
            "exp_M": float(getattr(inp, "tauE_user_exp_M_v396", float("nan"))),
        }
        if math.isfinite(C) and all(math.isfinite(v) for v in exps.values()):
            add(
                "USER(v396)",
                tauE_user_powerlaw_s(
                    C=C,
                    Ip_MA=Ip_MA,
                    Bt_T=Bt_T,
                    ne20=ne20,
                    Ploss_MW=Ploss_MW,
                    R_m=R_m,
                    a_m=a_m,
                    kappa=kappa,
                    M_amu=M_amu,
                    **exps,
                ),
            )

    if not scalings:
        return {
            "transport_envelope_v396_enabled": False,
            "transport_envelope_v396_error": "No valid τE scalings available (non-finite inputs).",
        }

    vals = [v for _, v in scalings]
    tau_min = float(min(vals))
    tau_max = float(max(vals))
    spread = float(tau_max / max(tau_min, 1e-12))
    tier = _credibility_tier_from_spread(spread)

    # Expose optional feasibility cap (default NaN => disabled)
    spread_cap = float(getattr(inp, "transport_spread_max_v396", float("nan")))
    spread_cap_enabled = bool(math.isfinite(spread_cap) and spread_cap > 0.0)

    return {
        "transport_envelope_v396_enabled": True,
        "tauE_envelope_min_s_v396": tau_min,
        "tauE_envelope_max_s_v396": tau_max,
        "transport_spread_ratio_v396": spread,
        "transport_credibility_tier_v396": tier,
        "transport_spread_cap_enabled_v396": spread_cap_enabled,
        "transport_spread_max_v396": spread_cap,
        "tauE_scalings_v396": {k: float(v) for k, v in scalings},
    }
