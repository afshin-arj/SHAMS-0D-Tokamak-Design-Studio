from __future__ import annotations

"""Heating & current-drive reduced models (system-code level).

SHAMS law compliance:
- No iterative solve inside truth. These are explicit closures.
- Models are conservative proxies intended for feasibility screening and
  evidence packs.

The main deliverable is a consistent set of outputs that can be used by the
constraint ledger:
- I_cd_MA: externally driven current (sum of enabled systems)
- f_NI: non-inductive fraction (I_bs + I_cd)/Ip
- P_cd_MW: electrical power allocated to current drive (subset of Paux)

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
import math
from typing import Dict, Optional


@dataclass(frozen=True)
class CDResult:
    P_cd_MW: float
    I_cd_MA: float
    eta_A_per_W: float
    model: str


def _finite(x: float) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def cd_efficiency_proxy_A_per_W(
    *,
    ne20: float,
    Te_keV: float,
    Bt_T: float,
    R_m: float,
    method: str,
) -> float:
    """Very lightweight proxy for CD efficiency (A/W).

    Notes:
    - This is intentionally conservative and smooth.
    - Units: ne20 = n_e / 1e20 m^-3, Te_keV in keV.

    Typical order of magnitude: 0.03–0.3 A/W depending on method and regime.
    """
    ne20 = max(1e-6, float(ne20))
    Te_keV = max(1e-3, float(Te_keV))
    Bt_T = max(1e-3, float(Bt_T))
    R_m = max(0.1, float(R_m))

    m = method.lower().strip()

    # Base scaling: higher Te helps, higher density hurts. Stronger field and larger R modestly help.
    base = 0.08 * (Te_keV ** 0.6) * (Bt_T ** 0.3) * (R_m ** 0.2) / (ne20 ** 0.8)

    # Method modifiers (very rough):
    if m in {"nb", "nbi", "neutral_beam"}:
        mod = 0.8
    elif m in {"ec", "ech", "electron_cyclotron"}:
        mod = 0.6
    elif m in {"lh", "lhcd", "lower_hybrid"}:
        mod = 1.2
    else:
        mod = 0.7

    eta = base * mod

    # Conservative caps/floors
    eta = max(0.01, min(0.35, eta))
    return float(eta)


def estimate_current_drive(
    out: Dict[str, float],
    *,
    Paux_MW_key: str = "Paux_MW",
    Ip_MA_key: str = "Ip_MA",
    Ibs_MA_key: str = "I_bs_MA",
    enable_key: str = "cd_enable",
    fraction_key: str = "cd_fraction_of_Paux",
    method_key: str = "cd_method",
) -> Optional[CDResult]:
    """Estimate current drive given existing out dict.

    Returns None if required quantities are missing.
    """
    try:
        if not bool(out.get(enable_key, False)):
            return None
        Paux = float(out.get(Paux_MW_key, float("nan")))
        Ip = float(out.get(Ip_MA_key, float("nan")))
        ne20 = float(out.get("ne_1e20", out.get("ne20", float("nan"))))
        Te_keV = float(out.get("Te0_keV", out.get("Te_keV", float("nan"))))
        Bt = float(out.get("B0_T", out.get("Bt_T", float("nan"))))
        R = float(out.get("R0_m", out.get("R_m", float("nan"))))
        if not all(_finite(x) for x in [Paux, Ip, ne20, Te_keV, Bt, R]) or Paux <= 0 or Ip <= 0:
            return None
        frac = float(out.get(fraction_key, 0.5))
        frac = max(0.0, min(1.0, frac))
        P_cd = frac * Paux
        method = str(out.get(method_key, "NBI"))
        eta = cd_efficiency_proxy_A_per_W(ne20=ne20, Te_keV=Te_keV, Bt_T=Bt, R_m=R, method=method)
        I_cd_A = eta * (P_cd * 1e6)
        I_cd_MA = I_cd_A * 1e-6
        return CDResult(P_cd_MW=P_cd, I_cd_MA=I_cd_MA, eta_A_per_W=eta, model=f"proxy:{method}")
    except Exception:
        return None
