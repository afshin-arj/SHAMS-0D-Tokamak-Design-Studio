from __future__ import annotations

"""Control & stability authority proxies.

Design intent
-------------
Provide deterministic, conservative proxies for:
- Vertical stability margin and required control bandwidth/power.
- PF envelope requirements (peak current, voltage, power, dI/dt) over a quasi-static phase.

SHAMS law compliance
-------------------
- Single-pass, algebraic; no hidden iteration.
- Outputs are auditable intermediate values.
- The constraints ledger decides enforcement (hard/diagnostic/ignored) via optional caps.
"""

from dataclasses import dataclass
import math
from typing import Any, Dict


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _get(inp: Any, k: str, default: Any) -> Any:
    try:
        return getattr(inp, k)
    except Exception:
        return default


@dataclass(frozen=True)
class VerticalStabilityProxy:
    vs_margin: float
    vs_bandwidth_req_Hz: float
    vs_control_power_req_MW: float
    authority: Dict[str, str]


def compute_vertical_stability(out: Dict[str, Any], inp: Any) -> VerticalStabilityProxy:
    """Compute a vertical stability margin proxy and control requirements.

    Margin proxy (dimensionless)
    ---------------------------
    We use a conservative geometric screen: high elongation at low aspect ratio is harder.

        vs_margin = 1 - (kappa / kappa_lim(A, delta))

    where kappa_lim is a *screening* limit. Positive margin is better.

    Control requirements
    --------------------
    If include_control_contracts is True, map margin to a growth rate proxy and then
    to required closed-loop bandwidth and power over a short horizon.
    """

    R0 = _f(out.get("R0_m"), _f(_get(inp, "R0_m", float("nan"))))
    a = _f(out.get("a_m"), _f(_get(inp, "a_m", float("nan"))))
    kappa = _f(out.get("kappa"), _f(_get(inp, "kappa", float("nan"))))
    delta = _f(out.get("delta"), _f(_get(inp, "delta", 0.0)))

    # aspect ratio A
    A = float("nan")
    if math.isfinite(R0) and math.isfinite(a) and a > 0:
        A = R0 / a

    # Screening kappa limit proxy: intentionally modest.
    # Larger A (thinner) allows slightly more kappa; delta helps slightly.
    if math.isfinite(A):
        kappa_lim = 1.7 + 0.15 * max(0.0, min(A - 2.0, 3.0)) + 0.10 * max(0.0, min(delta, 0.6))
    else:
        kappa_lim = 1.85

    if math.isfinite(kappa) and kappa_lim > 0:
        vs_margin = 1.0 - (kappa / kappa_lim)
    else:
        vs_margin = float("nan")

    # Default: no requirements unless control contracts enabled
    if not bool(_get(inp, "include_control_contracts", False)):
        return VerticalStabilityProxy(
            vs_margin=float(vs_margin),
            vs_bandwidth_req_Hz=float("nan"),
            vs_control_power_req_MW=float("nan"),
            authority={"vs": "proxy_geometry_only"},
        )

    # Map margin -> growth rate proxy.
    tau_nom = max(_f(_get(inp, "vs_tau_nominal_s", 0.30)), 1e-3)
    # If margin <=0, assume near-immediate growth (very conservative).
    if not math.isfinite(vs_margin):
        gamma = 1.0 / tau_nom
    else:
        gamma = (1.0 / tau_nom) * (1.0 / max(vs_margin, 0.05))

    bw_factor = max(_f(_get(inp, "vs_bw_factor", 3.0)), 1.0)
    f_req = bw_factor * gamma / (2.0 * math.pi)

    # Power proxy: scale with plasma thermal energy and required bandwidth.
    # Use W_th if available, else fall back to Pfus-scale.
    Wth_MJ = _f(out.get("W_th_MJ"), float("nan"))
    Pfus_MW = _f(out.get("P_fus_total_MW"), _f(out.get("Pfus_total_MW"), float("nan")))
    if not math.isfinite(Wth_MJ) and math.isfinite(Pfus_MW):
        Wth_MJ = 3.0 * max(Pfus_MW, 0.0)  # coarse scaling

    horizon = max(_f(_get(inp, "vs_control_horizon_s", 1.0)), 0.05)
    margin_factor = max(_f(_get(inp, "vs_control_margin_factor", 1.30)), 1.0)

    if math.isfinite(Wth_MJ) and math.isfinite(f_req):
        # Energy to control ~ margin_factor * Wth * (f_req * horizon)
        E_ctrl_MJ = margin_factor * Wth_MJ * (f_req * horizon)
        P_req_MW = E_ctrl_MJ / horizon
    else:
        P_req_MW = float("nan")

    return VerticalStabilityProxy(
        vs_margin=float(vs_margin),
        vs_bandwidth_req_Hz=float(f_req),
        vs_control_power_req_MW=float(P_req_MW),
        authority={"vs": "proxy_geometry+contracts"},
    )


@dataclass(frozen=True)
class PFEnvelopeProxy:
    pf_I_peak_MA: float
    pf_V_peak_V: float
    pf_P_peak_MW: float
    pf_dIdt_MA_s: float
    authority: Dict[str, str]


def compute_pf_envelope(out: Dict[str, Any], inp: Any) -> PFEnvelopeProxy:
    """Compute a PF envelope proxy.

    This is a bookkeeping envelope for ramp/flat requirements and simple LR limits.
    It is not a PF circuit solve.

    The proxy uses either pf_L_eff_H if provided, or a conservative inferred value.
    """

    if not bool(_get(inp, "include_control_contracts", False)):
        return PFEnvelopeProxy(float("nan"), float("nan"), float("nan"), float("nan"), {"pf": "disabled"})

    # Required plasma flux swing (very coarse): use CS requirement if available.
    Phi_req_Wb = _f(out.get("Phi_CS_req_Wb"), float("nan"))
    if not math.isfinite(Phi_req_Wb):
        # fallback: scale with Ip and geometry
        Ip_MA = _f(out.get("Ip_MA"), _f(_get(inp, "Ip_MA", float("nan"))))
        R0 = _f(out.get("R0_m"), _f(_get(inp, "R0_m", float("nan"))))
        Phi_req_Wb = 30.0 * max(Ip_MA, 0.0) * max(R0, 1.0) / 6.0

    ramp_s = _f(_get(inp, "pf_ramp_s", float("nan")))
    if not math.isfinite(ramp_s):
        ramp_s = _f(_get(inp, "pulse_ramp_s", 300.0))
    ramp_s = max(ramp_s, 1.0)

    # Effective PF inductance and resistance
    L = _f(_get(inp, "pf_L_eff_H", float("nan")))
    if not math.isfinite(L):
        # infer from flux requirement assuming I ~ Phi/L with I~10 MA scale
        L = max(Phi_req_Wb / (10e6), 1e-6)
    R = max(_f(_get(inp, "pf_R_eff_Ohm", 1.0e-4)), 1e-8)

    # Peak current proxy
    I_peak_A = max(Phi_req_Wb / max(L, 1e-9), 0.0)
    dIdt_A_s = I_peak_A / ramp_s

    # Peak voltage from L dI/dt + R I
    V_peak = L * dIdt_A_s + R * I_peak_A
    P_peak_W = V_peak * I_peak_A

    return PFEnvelopeProxy(
        pf_I_peak_MA=float(I_peak_A / 1e6),
        pf_V_peak_V=float(V_peak),
        pf_P_peak_MW=float(P_peak_W / 1e6),
        pf_dIdt_MA_s=float(dIdt_A_s / 1e6),
        authority={"pf": "proxy_LR_envelope" if math.isfinite(L) else "proxy_inferred"},
    )
