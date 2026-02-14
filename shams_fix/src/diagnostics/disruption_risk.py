"""Disruption and operational risk tiering (v296.0).

This is a conservative, deterministic *screening* tool.
It does not claim predictive disruption modeling.

Inputs are normalized margins (<=1 means at/over limit).
Outputs:
- tier: LOW/MED/HIGH
- dominant driver

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Dict

Tier = Literal["LOW", "MED", "HIGH"]


@dataclass(frozen=True)
class DisruptionRisk:
    tier: Tier
    dominant_driver: str
    risk_index: float
    components: Dict[str, float]


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def evaluate_disruption_risk(
    f_greenwald: float,
    beta_n_margin: float,
    qmin: float,
    prad_frac: float,
) -> DisruptionRisk:
    """Compute conservative disruption risk tier.

    Args:
        f_greenwald: n/nG (dimensionless).
        beta_n_margin: betaN / betaN_limit (dimensionless, >1 means exceeding).
        qmin: proxy qmin.
        prad_frac: Prad / Pin.

    Returns:
        DisruptionRisk.
    """

    # Normalize components into 0..2 range where 1~edge.
    c_den = _clamp(max(0.0, f_greenwald) / 1.0, 0.0, 2.0)
    c_beta = _clamp(max(0.0, beta_n_margin) / 1.0, 0.0, 2.0)
    c_q = _clamp(1.0 / max(0.2, qmin) * 2.0, 0.0, 2.0)  # qmin~2 =>1.0, qmin~1 =>2.0
    c_rad = _clamp(max(0.0, prad_frac) / 0.7, 0.0, 2.0)  # 70% radiative fraction is risky

    components = {
        "density": c_den,
        "beta": c_beta,
        "qmin": c_q,
        "radiation": c_rad,
    }

    # Conservative weighted max-like index
    risk_index = 0.35 * c_den + 0.30 * c_beta + 0.20 * c_q + 0.15 * c_rad
    risk_index = _clamp(risk_index, 0.0, 2.0)

    # Tier thresholds
    if risk_index >= 1.25 or max(components.values()) >= 1.6:
        tier: Tier = "HIGH"
    elif risk_index >= 0.85 or max(components.values()) >= 1.25:
        tier = "MED"
    else:
        tier = "LOW"

    dominant_driver = max(components.items(), key=lambda kv: kv[1])[0]

    return DisruptionRisk(
        tier=tier,
        dominant_driver=dominant_driver,
        risk_index=risk_index,
        components=components,
    )
