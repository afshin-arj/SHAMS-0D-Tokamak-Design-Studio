"""Stability & control risk tiering (v319.0).

Deterministic, conservative *screening* layer.

This module converts already-computed truth outputs (margins, proxies, and control-contract
status) into a small number of audit-friendly tiers.

It is NOT a predictive disruption model and MUST NOT be interpreted as one.

Inputs (from frozen truth outputs):
  - mhd_risk_proxy (dimensionless; smaller is better)
  - vs_margin (dimensionless; larger is better)
  - rwm_control_ok (bool)
  - control_contract_margins (dict[str,float]) where margin>0 means under cap

Outputs:
  - tier: LOW/MED/HIGH
  - dominant driver
  - risk index (0..2)

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

Tier = Literal["LOW", "MED", "HIGH"]


@dataclass(frozen=True)
class StabilityRisk:
    tier: Tier
    dominant_driver: str
    risk_index: float
    components: Dict[str, float]


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _f(out: Dict[str, Any], key: str, default: float = float("nan")) -> float:
    try:
        v = float(out.get(key, default))
    except Exception:
        v = default
    return v


def _bool(out: Dict[str, Any], key: str, default: bool = False) -> bool:
    v = out.get(key, default)
    return bool(v) if isinstance(v, (bool, int, float, str)) else bool(default)


def _min_margin(margins: Any) -> Optional[float]:
    if not isinstance(margins, dict):
        return None
    vals = []
    for v in margins.values():
        try:
            fv = float(v)
        except Exception:
            continue
        if fv == fv:
            vals.append(fv)
    return min(vals) if vals else None


def evaluate_stability_risk(out: Dict[str, Any]) -> StabilityRisk:
    """Compute stability/control risk tier from truth outputs.

    Args:
        out: Frozen truth outputs dict.

    Returns:
        StabilityRisk.
    """

    mhd = _f(out, "mhd_risk_proxy", float("nan"))
    vs = _f(out, "vs_margin", float("nan"))

    # --- Component normalizations to 0..2 (1 ~ 'edge')
    # MHD proxy: typical ~0..3; treat ~1.2 as edging into MED.
    c_mhd = 0.0 if not (mhd == mhd) else _clamp(mhd / 1.2, 0.0, 2.0)

    # Vertical stability margin: 1 is 'good', 0 is 'bad'. Risk rises as margin shrinks.
    # vs_margin ~0.5 -> c_vs ~1; vs_margin ~0.0 -> c_vs ->2.
    c_vs = 0.0 if not (vs == vs) else _clamp((1.0 - _clamp(vs, 0.0, 1.0)) / 0.5, 0.0, 2.0)

    # RWM control screening: if failed, force high component.
    rwm_ok = _bool(out, "rwm_control_ok", True)
    c_rwm = 0.0 if rwm_ok else 2.0
    try:
        chi = float(out.get("rwm_chi", float("nan")))
        if chi == chi and chi > 0:
            # chi~1 is 'hard'; scale such that chi>=1 -> component >=1
            c_rwm = max(c_rwm, _clamp(chi / 1.0, 0.0, 2.0))
    except Exception:
        pass

    # Control contract margins: take worst (minimum) margin. margin>0 is OK.
    min_m = _min_margin(out.get("control_contract_margins"))
    if min_m is None:
        c_ctrl = 0.0
    else:
        # margin 0 -> edge (1), negative margin -> >1
        c_ctrl = _clamp((0.0 - min_m) / 0.15 + 1.0, 0.0, 2.0)

    components = {
        "mhd": float(c_mhd),
        "vertical_stability": float(c_vs),
        "rwm": float(c_rwm),
        "control_budget": float(c_ctrl),
    }

    risk_index = 0.40 * c_mhd + 0.25 * c_vs + 0.20 * c_rwm + 0.15 * c_ctrl
    risk_index = _clamp(risk_index, 0.0, 2.0)

    if risk_index >= 1.25 or max(components.values()) >= 1.6:
        tier: Tier = "HIGH"
    elif risk_index >= 0.85 or max(components.values()) >= 1.25:
        tier = "MED"
    else:
        tier = "LOW"

    dominant_driver = max(components.items(), key=lambda kv: kv[1])[0]
    return StabilityRisk(
        tier=tier,
        dominant_driver=dominant_driver,
        risk_index=float(risk_index),
        components=components,
    )
