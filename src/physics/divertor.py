from __future__ import annotations
"""Divertor / SOL heat exhaust proxies.

Lightweight models intended for systems studies:
- identify attached vs detached-like regimes from P_SOL/R overload
- estimate power to divertor targets and peak heat flux proxy

These are not numerical replicas of PROCESS; they provide PROCESS-like coupling structure.
"""
import math
from dataclasses import dataclass

@dataclass(frozen=True)
class DivertorResult:
    P_SOL_MW: float
    f_rad_div_eff: float
    P_div_MW: float
    regime: str
    q_div_MW_m2: float
    q_mid_MW_m2: float

def divertor_two_regime(
    P_SOL_MW: float,
    R0_m: float,
    A_fw_m2: float,
    q_div_proxy_MW_m2: float,
    P_SOL_over_R_max_MW_m: float,
    f_rad_div: float,
    detach_boost: float = 0.25,
    advanced_divertor_factor: float = 1.0,
) -> DivertorResult:
    """Two-regime divertor proxy.

    metric = P_SOL / R0 (MW/m). If above threshold, assume detachment assistance increases
    effective divertor radiation fraction.
    """
    P_SOL = float(P_SOL_MW)
    R0 = max(float(R0_m), 1e-9)
    metric = P_SOL / R0

    thr = max(float(P_SOL_over_R_max_MW_m), 1e-9)
    f_rad_div = float(f_rad_div)
    if metric <= thr:
        regime = "attached"
        f_eff = min(max(f_rad_div, 0.0), 0.95)
    else:
        regime = "detached"
        over = metric / thr - 1.0
        f_eff = min(0.98, max(f_rad_div, 0.0) + float(detach_boost) * (1.0 - math.exp(-over)))

    P_div = P_SOL * (1.0 - f_eff)
    scale = P_div / max(P_SOL, 1e-9)

    adv = max(float(advanced_divertor_factor), 1e-6)
    q_div = float(q_div_proxy_MW_m2) * scale * adv
    q_mid = (P_div * 1e6) * adv / max(float(A_fw_m2), 1e-6) / 1e6
    return DivertorResult(
        P_SOL_MW=P_SOL,
        f_rad_div_eff=f_eff,
        P_div_MW=P_div,
        regime=regime,
        q_div_MW_m2=q_div,
        q_mid_MW_m2=q_mid,
    )
