from __future__ import annotations

"""Operational risk screens (disruption & radiative limit) for system-code mode.

These are conservative, low-order proxies intended to provide:
- explicit, interpretable risk indicators
- optional feasibility gates (via constraint limits set in inputs)

They do not simulate disruption dynamics.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
import math
from typing import Dict, Optional


@dataclass(frozen=True)
class RiskResult:
    disruption_risk: float  # dimensionless (lower is better)
    radiative_fraction_core: float  # 0-1
    radiative_limit_margin: float  # positive good
    model: str


def _finite(x: float) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def evaluate_risk_proxies(out: Dict[str, float]) -> Optional[RiskResult]:
    """Compute conservative risk proxies from output dict.

    Expected keys (best effort): betaN_proxy or betaN, q95_proxy/q95, f_Gw, Zeff,
    Prad_core_MW, P_loss_MW.
    """
    try:
        betaN = float(out.get("betaN_proxy", out.get("betaN", float("nan"))))
        q95 = float(out.get("q95_proxy", out.get("q95", float("nan"))))
        fGw = float(out.get("f_Gw", out.get("n_over_nG", float("nan"))))
        Zeff = float(out.get("Zeff", float("nan")))
        Prad = float(out.get("Prad_core_MW", out.get("P_rad_core_MW", float("nan"))))
        Ploss = float(out.get("P_loss_MW", out.get("Ploss_MW", float("nan"))))

        # Disruption risk proxy: increases with betaN, fGw, Zeff, decreases with q95.
        if not all(_finite(x) for x in [betaN, q95, fGw]):
            return None
        Zeff_eff = Zeff if _finite(Zeff) and Zeff > 0 else 2.0
        risk = (betaN ** 1.2) * (max(0.2, fGw) ** 1.0) * (Zeff_eff ** 0.3) / (max(1.0, q95) ** 1.0)
        # Normalize to a convenient scale ~ O(1)
        risk = float(min(10.0, max(0.0, risk / 3.0)))

        # Core radiative fraction and a conservative limit margin
        if _finite(Prad) and _finite(Ploss) and Ploss > 0:
            f_rad = float(max(0.0, min(2.0, Prad / Ploss)))
        else:
            f_rad = float("nan")

        # Radiative limit: require f_rad_core <= f_rad_core_max if provided
        fmax = float(out.get("f_rad_core_max", float("nan")))
        if _finite(f_rad) and _finite(fmax) and fmax > 0:
            margin = fmax - f_rad
        else:
            margin = float("nan")

        return RiskResult(
            disruption_risk=risk,
            radiative_fraction_core=f_rad,
            radiative_limit_margin=margin,
            model="proxy:v1",
        )
    except Exception:
        return None
