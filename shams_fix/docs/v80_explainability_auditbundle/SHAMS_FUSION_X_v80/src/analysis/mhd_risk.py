from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Dict, Any

@dataclass(frozen=True)
class RiskResult:
    mhd_risk_proxy: float
    vs_margin: float

def compute_mhd_and_vs_risk(out: Dict[str, Any], inp: Any) -> RiskResult:
    """Compute lightweight operational risk proxies.

    These are intentionally transparent, bounded proxies designed for systems-level trade studies.
    They are NOT a disruption predictor.

    MHD/disruption risk proxy:
      - increases as beta margin shrinks, q95 shrinks, Greenwald fraction rises, and divertor load rises.
      - bounded in [0, ~3] for typical regimes; smaller is better.

    Vertical stability margin proxy:
      - decreases with high elongation and low aspect ratio (compactness).
      - bounded roughly [0,1], larger is better.
    """
    # Gather key quantities safely
    def f(key: str, default: float = float('nan')) -> float:
        try:
            v = float(out.get(key, default))
        except Exception:
            v = default
        return v

    betaN = f("betaN", float('nan'))
    betaN_max = f("betaN_max", float('nan'))
    q95 = f("q95", f("q95_proxy", float('nan')))
    fG = f("fG", getattr(inp, "fG", float('nan')))
    q_div = f("q_div_MW_m2", f("q_div_peak_MW_m2", float('nan')))
    q_div_max = f("q_div_max_MW_m2", float('nan'))

    # Normalize margins (dimensionless), clip to avoid weirdness
    def margin(value: float, limit: float) -> float:
        if not (value == value) or not (limit == limit) or limit <= 0:
            return float('nan')
        return (limit - value) / limit

    m_beta = margin(betaN, betaN_max)
    m_qdiv = margin(q_div, q_div_max)

    # risk components (bounded, monotonic)
    r_beta = 0.0 if not (m_beta == m_beta) else max(0.0, 1.0 - max(min(m_beta, 1.0), -1.0))
    r_fG = 0.0 if not (fG == fG) else max(0.0, min(fG, 2.0) - 0.8) / 1.2  # starts rising above 0.8
    r_q95 = 0.0 if not (q95 == q95) else max(0.0, (3.0 - min(max(q95, 0.5), 6.0)) / 2.5)  # high below ~3
    r_qdiv = 0.0 if not (m_qdiv == m_qdiv) else max(0.0, 1.0 - max(min(m_qdiv, 1.0), -1.0))

    # Combine (simple weighted sum)
    mhd_risk = 0.9*r_beta + 0.6*r_q95 + 0.5*r_fG + 0.4*r_qdiv

    # Vertical stability margin proxy (very lightweight):
    # Higher kappa and lower aspect ratio increases vertical instability demands.
    try:
        kappa = float(getattr(inp, "kappa", float('nan')))
        R0 = float(getattr(inp, "R0_m", float('nan')))
        a = float(getattr(inp, "a_m", float('nan')))
    except Exception:
        kappa = R0 = a = float('nan')

    if (kappa == kappa) and (R0 == R0) and (a == a) and a > 0 and R0 > 0:
        A = R0 / a
        # heuristic stability capacity: more margin at higher A, lower kappa
        demand = max(0.0, (kappa - 1.6)) / 0.6 + max(0.0, (2.5 - A)) / 1.0
        vs_margin = max(0.0, 1.0 - 0.5*demand)
    else:
        vs_margin = float('nan')

    return RiskResult(mhd_risk_proxy=float(mhd_risk), vs_margin=float(vs_margin))
