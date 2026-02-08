from __future__ import annotations

"""Resistive Wall Mode (RWM) screening proxy.

Design intent
-------------
This is a PROCESS-class *screening* module:

* deterministic, single-pass, no hidden iteration
* produces auditable intermediate quantities (beta limits, chi, growth-rate proxy)
* couples to Control Contracts via required bandwidth and power envelopes
* authority-tiered coefficients with conservative defaults

It is **not** a stability solver. It is an explicit feasibility screen intended
for design-space cartography and reviewer-safe constraint accounting.
"""

from dataclasses import dataclass
import math
from typing import Any, Dict


def _f(d: Dict[str, Any], k: str, default: float = float("nan")) -> float:
    try:
        return float(d.get(k, default))
    except Exception:
        return default


def _get(inp: Any, k: str, default: Any) -> Any:
    try:
        return getattr(inp, k, default)
    except Exception:
        return default


@dataclass(frozen=True)
class RWMScreening:
    regime: str  # NO_WALL_STABLE | RWM_ACTIVE | IDEAL_WALL_EXCEEDED | UNAVAILABLE
    betaN_NW: float
    betaN_IW: float
    chi: float
    tau_w_s: float
    gamma_rwm_s_inv: float
    f_req_Hz: float
    P_req_MW: float
    authority: Dict[str, str]
    meta: Dict[str, float]


def compute_rwm_screening(out: Dict[str, Any], inp: Any) -> RWMScreening:
    """Compute RWM screening outputs.

    Inputs
    ------
    Uses (when available): beta_N, betaN_proxy, q95_proxy, kappa, delta, li_proxy,
    and wall time constant tau_w_s or inferred tau_w_s.

    Control coupling
    ---------------
    Returns required closed-loop bandwidth f_req_Hz and control power P_req_MW.
    These are compared against caps by the constraints layer.
    """

    enabled = bool(_get(inp, "include_rwm_screening", False))
    if not enabled:
        return RWMScreening(
            regime="UNAVAILABLE",
            betaN_NW=float("nan"),
            betaN_IW=float("nan"),
            chi=float("nan"),
            tau_w_s=float("nan"),
            gamma_rwm_s_inv=float("nan"),
            f_req_Hz=float("nan"),
            P_req_MW=float("nan"),
            authority={"rwm": "disabled"},
            meta={},
        )

    # --- gather key state ---
    beta_N = _f(out, "beta_N", _f(out, "betaN_proxy", float("nan")))
    q95 = _f(out, "q95_proxy", float("nan"))
    kappa = _f(out, "kappa", float("nan"))
    delta = _f(out, "delta", float("nan"))
    li = _f(out, "li_proxy", float("nan"))
    if not math.isfinite(li):
        li = float(_get(inp, "li_proxy", float("nan")))

    # Wall time constant: prefer explicit input; else infer from geometry class.
    tau_w_in = float(_get(inp, "rwm_tau_w_s", float("nan")))
    tau_w = tau_w_in
    tau_authority = "proxy_input" if math.isfinite(tau_w_in) else "proxy_inferred"

    if not math.isfinite(tau_w):
        # Very conservative inference: thin-wall penetration time scales ~ R0 * t_wall / eta.
        # We use a bounded heuristic to avoid implying accuracy.
        R0 = _f(out, "R0_m", float(_get(inp, "R0_m", float("nan"))))
        a = _f(out, "a_m", float(_get(inp, "a_m", float("nan"))))
        # default wall thickness proxy (m)
        t_wall = float(_get(inp, "rwm_wall_thickness_m", 0.03))
        # resistivity class proxy (dimensionless)
        eta_class = float(_get(inp, "rwm_wall_resistivity_class", 1.0))
        eta_class = max(eta_class, 0.3)
        if math.isfinite(R0) and math.isfinite(a):
            tau_w = 0.03 * max(R0, 1.0) * max(t_wall, 0.01) / eta_class
        else:
            tau_w = 0.05
        tau_w = max(min(tau_w, 0.5), 0.005)

    # --- PROCESS-class beta limit proxies ---
    # Coefficients (conservative defaults; user-tunable with explicit authority tag)
    C_NW = float(_get(inp, "rwm_C_betaN_no_wall", 2.8))
    C_IW = float(_get(inp, "rwm_C_betaN_ideal_wall", 4.0))
    # shaping boost: modest for kappa, delta
    a_k = float(_get(inp, "rwm_a_kappa", 0.25))
    a_d = float(_get(inp, "rwm_a_delta", 0.15))
    # q dependence: weaker stability at low q
    q_ref = float(_get(inp, "rwm_q95_ref", 3.0))
    a_q = float(_get(inp, "rwm_a_q95", 0.30))
    # li dependence: weak
    li_ref = float(_get(inp, "rwm_li_ref", 0.8))
    a_li = float(_get(inp, "rwm_a_li", 0.10))

    def _shape_factor() -> float:
        f = 1.0
        if math.isfinite(kappa):
            f *= (1.0 + a_k * max(0.0, kappa - 1.0))
        if math.isfinite(delta):
            f *= (1.0 + a_d * max(0.0, delta))
        return max(f, 0.5)

    def _q_factor() -> float:
        if not math.isfinite(q95) or q95 <= 0.0:
            return 1.0
        # penalize low-q; cap effect
        return max(0.6, min(1.4, (q95 / q_ref) ** a_q))

    def _li_factor() -> float:
        if not math.isfinite(li) or li <= 0.0:
            return 1.0
        return max(0.8, min(1.2, (li / li_ref) ** (-a_li)))

    F = _shape_factor() * _q_factor() * _li_factor()
    betaN_NW = C_NW * F
    betaN_IW = C_IW * F
    # enforce ordering
    betaN_IW = max(betaN_IW, betaN_NW + 0.2)

    # --- regime classification ---
    if not math.isfinite(beta_N):
        return RWMScreening(
            regime="UNAVAILABLE",
            betaN_NW=float(betaN_NW),
            betaN_IW=float(betaN_IW),
            chi=float("nan"),
            tau_w_s=float(tau_w),
            gamma_rwm_s_inv=float("nan"),
            f_req_Hz=float("nan"),
            P_req_MW=float("nan"),
            authority={"rwm": "proxy_missing_beta"},
            meta={},
        )

    if beta_N <= betaN_NW:
        return RWMScreening(
            regime="NO_WALL_STABLE",
            betaN_NW=float(betaN_NW),
            betaN_IW=float(betaN_IW),
            chi=0.0,
            tau_w_s=float(tau_w),
            gamma_rwm_s_inv=0.0,
            f_req_Hz=0.0,
            P_req_MW=0.0,
            authority={"rwm": tau_authority},
            meta={"beta_N": float(beta_N)},
        )

    if beta_N >= betaN_IW:
        return RWMScreening(
            regime="IDEAL_WALL_EXCEEDED",
            betaN_NW=float(betaN_NW),
            betaN_IW=float(betaN_IW),
            chi=1.0,
            tau_w_s=float(tau_w),
            gamma_rwm_s_inv=float("inf"),
            f_req_Hz=float("inf"),
            P_req_MW=float("inf"),
            authority={"rwm": tau_authority},
            meta={"beta_N": float(beta_N)},
        )

    # --- RWM active regime: compute chi, growth, and requirements ---
    chi = (beta_N - betaN_NW) / max(betaN_IW - betaN_NW, 1e-6)
    chi = max(min(chi, 0.999), 1e-6)

    eps = float(_get(inp, "rwm_chi_eps", 0.05))
    eps = max(eps, 1e-4)
    phi = chi / max(1.0 - chi + eps, 1e-6)

    f_rot = float(_get(inp, "rwm_rotation_stabilization", 0.0))
    f_rot = max(min(f_rot, 1.0), 0.0)
    k_rot = float(_get(inp, "rwm_k_rot", 1.5))
    psi_rot = 1.0 / (1.0 + k_rot * f_rot)

    gamma = (phi * psi_rot) / max(tau_w, 1e-6)
    f_req = gamma / (2.0 * math.pi)

    # Control power: scale to PF magnetic energy proxy if available.
    W_pf_MJ = _f(out, "pf_magnetic_energy_proxy_MJ", float("nan"))
    if not math.isfinite(W_pf_MJ):
        # fallback: use control budget ledger PF energy if already computed elsewhere
        W_pf_MJ = _f(out, "pf_E_pulse_MJ", float("nan"))
    C_P = float(_get(inp, "rwm_C_P", 0.15))
    P_req = (C_P * W_pf_MJ * gamma) if math.isfinite(W_pf_MJ) else float("nan")

    return RWMScreening(
        regime="RWM_ACTIVE",
        betaN_NW=float(betaN_NW),
        betaN_IW=float(betaN_IW),
        chi=float(chi),
        tau_w_s=float(tau_w),
        gamma_rwm_s_inv=float(gamma),
        f_req_Hz=float(f_req),
        P_req_MW=float(P_req),
        authority={"rwm": tau_authority},
        meta={
            "beta_N": float(beta_N),
            "phi": float(phi),
            "psi_rot": float(psi_rot),
            "W_pf_MJ": float(W_pf_MJ) if math.isfinite(W_pf_MJ) else float("nan"),
        },
    )
