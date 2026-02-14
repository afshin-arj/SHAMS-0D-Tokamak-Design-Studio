from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class PFProxy:
    I_pf_MA: float
    stress_proxy: float
    ok: bool

def pf_system_proxy(R0_m: float, a_m: float, kappa: float, Ip_MA: float, ramp_rate_MA_s: float) -> PFProxy:
    """Lightweight PF system proxy.

    Computes a proxy PF coil current demand and a stress proxy.
    Intended for screening; not a detailed PF design.

    - PF current proxy increases with Ip, elongation, and compactness (low A).
    - Stress proxy scales with current density demand and ramp rate.

    Returns:
      ok flag is simply True (constraints applied elsewhere).
    """
    A = R0_m / max(a_m, 1e-6)
    I_pf = Ip_MA * (1.0 + 0.3*max(0.0, kappa-1.6)) * (1.0 + 0.4*max(0.0, 2.5-A))
    stress = (I_pf/ max(Ip_MA, 1e-6))**2 * (1.0 + 0.2*max(0.0, ramp_rate_MA_s - 0.01)/0.05)
    return PFProxy(I_pf_MA=float(I_pf), stress_proxy=float(stress), ok=True)
