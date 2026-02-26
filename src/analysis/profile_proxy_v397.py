"""SHAMS v397.0 — 1.5D Profile Proxy Authority (governance-only).

Frozen-truth compliance:
  - Deterministic, non-iterative.
  - Does not modify the operating point.
  - Emits explicit proxy metrics and optional feasibility caps.

This module intentionally uses:
  - Analytic profile families: s(ρ) = (1-ρ^α)^β
  - Fixed-grid deterministic quadrature for coupled moments.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import asdict
from math import isfinite
from typing import Any, Dict, Tuple

import numpy as np


def _shape(rho: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    """Return s(ρ) = (1-ρ^α)^β with s(0)=1 and s(1)=0 (for α,β>0)."""
    a = float(alpha)
    b = float(beta)
    if not (isfinite(a) and isfinite(b) and a > 0.0 and b > 0.0):
        return np.full_like(rho, np.nan, dtype=float)
    x = np.clip(rho, 0.0, 1.0) ** a
    return np.clip(1.0 - x, 0.0, 1.0) ** b


def _area_average(shape_vals: np.ndarray, rho: np.ndarray) -> float:
    """Area average over a circular cross-section proxy: <s> = 2∫ s ρ dρ."""
    # Deterministic trapezoid on a fixed grid
    integrand = shape_vals * rho
    return float(2.0 * np.trapz(integrand, rho))


def _peaking_factor(shape_vals: np.ndarray, rho: np.ndarray) -> float:
    """Central-to-average peaking f = s(0)/<s> = 1/<s> if s(0)=1."""
    avg = _area_average(shape_vals, rho)
    if not (isfinite(avg) and avg > 0.0):
        return float("nan")
    return float(1.0 / avg)


def _bootstrap_localization_index(p_shape: np.ndarray, rho: np.ndarray, rho_edge: float = 0.8) -> float:
    """Edge-localization proxy based on |dp/dρ| fraction in outer region.

    localization = ∫_{ρ>=ρ_edge} |dp/dρ| ρ dρ  / ∫_{0..1} |dp/dρ| ρ dρ
    """
    if p_shape.size != rho.size:
        return float("nan")
    dpdr = np.gradient(p_shape, rho)
    w = np.abs(dpdr) * rho
    denom = float(np.trapz(w, rho))
    if not (isfinite(denom) and denom > 0.0):
        return float("nan")
    mask = rho >= float(rho_edge)
    num = float(np.trapz(w[mask], rho[mask]))
    return float(num / denom)


def _q0_li_proxies(q95: float, f_j0: float, shear_shape: float) -> Tuple[float, float]:
    """Deterministic q0 and li proxies based on current peaking.

    This is explicitly labeled as proxy authority (NOT Grad–Shafranov).

    Heuristics:
      - More peaked current (higher f_j0) reduces q0.
      - Higher shear_shape in [0,1] increases q0 modestly.
      - li_proxy increases with peaking.
    """
    if not (isfinite(q95) and q95 > 0.0 and isfinite(f_j0) and f_j0 > 0.0):
        return float("nan"), float("nan")
    s = float(np.clip(shear_shape, 0.0, 1.0))
    # Baseline mapping: q0 decreases ~ linearly with (f_j0-1)
    q0_base = q95 / (1.0 + 0.8 * max(0.0, (f_j0 - 1.0)))
    # Shear-shape recovery (bounded): up to +20% of q0_base
    q0 = q0_base * (1.0 + 0.2 * s)
    # li proxy: 0.7 .. 2.0 typical
    li = float(np.clip(0.7 + 0.9 * max(0.0, (f_j0 - 1.0)), 0.6, 2.2))
    return float(q0), float(li)


def evaluate_profile_proxy_v397(inp: Any, out_partial: Dict[str, Any]) -> Dict[str, Any]:
    """Compute v397 profile-proxy metrics and (optionally) expose explicit caps.

    Parameters
    ----------
    inp:
      PointInputs-like object.
    out_partial:
      Must include q95 if available.
    """
    enabled = bool(getattr(inp, "include_profile_proxy_v397", False))
    if not enabled:
        return {
            "profile_proxy_v397_enabled": False,
        }

    # Fixed deterministic grid for diagnostics (audit-safe)
    rho = np.linspace(0.0, 1.0, 41)

    aT = float(getattr(inp, "profile_alpha_T_v397", 1.5))
    bT = float(getattr(inp, "profile_beta_T_v397", 1.0))
    an = float(getattr(inp, "profile_alpha_n_v397", 1.0))
    bn = float(getattr(inp, "profile_beta_n_v397", 1.0))
    aj = float(getattr(inp, "profile_alpha_j_v397", 1.5))
    bj = float(getattr(inp, "profile_beta_j_v397", 1.0))
    shear = float(getattr(inp, "profile_shear_shape_v397", 0.5))

    sT = _shape(rho, aT, bT)
    sn = _shape(rho, an, bn)
    sj = _shape(rho, aj, bj)

    fn0 = _peaking_factor(sn, rho)
    fT0 = _peaking_factor(sT, rho)

    # Pressure peaking uses coupled moment; compute via fixed-grid area average
    p_shape = sn * sT
    fp0 = _peaking_factor(p_shape, rho)

    # Bootstrap localization index (edge gradient proxy)
    boot_loc = _bootstrap_localization_index(p_shape, rho, rho_edge=0.8)

    # q0/li proxies
    q95 = float(out_partial.get("q95", out_partial.get("q95_proxy", float("nan"))))
    fj0 = _peaking_factor(sj, rho)
    q0_proxy, li_proxy = _q0_li_proxies(q95=q95, f_j0=fj0, shear_shape=shear)

    # Echo caps into output so the constraint ledger can consume them without
    # depending on UI state.
    caps = {
        "profile_peaking_p_max_v397": float(getattr(inp, "profile_peaking_p_max_v397", float("nan"))),
        "q95_proxy_min_v397": float(getattr(inp, "q95_proxy_min_v397", float("nan"))),
        "q0_proxy_min_v397": float(getattr(inp, "q0_proxy_min_v397", float("nan"))),
        "bootstrap_localization_max_v397": float(getattr(inp, "bootstrap_localization_max_v397", float("nan"))),
    }

    # Provide a compact sampled table for UI/pack export
    sample = {
        "rho": rho.tolist(),
        "s_n": sn.tolist(),
        "s_T": sT.tolist(),
        "s_p": p_shape.tolist(),
        "s_j": sj.tolist(),
    }

    return {
        "profile_proxy_v397_enabled": True,
        "profile_proxy_v397_params": {
            "alpha_T": aT,
            "beta_T": bT,
            "alpha_n": an,
            "beta_n": bn,
            "alpha_j": aj,
            "beta_j": bj,
            "shear_shape": float(np.clip(shear, 0.0, 1.0)),
        },
        "profile_peaking_n_v397": fn0,
        "profile_peaking_T_v397": fT0,
        "profile_peaking_p_v397": fp0,
        "profile_peaking_j_v397": fj0,
        "bootstrap_localization_index_v397": boot_loc,
        "q95_proxy_v397": q95,
        "q0_proxy_v397": q0_proxy,
        "li_proxy_v397": li_proxy,
        "profile_proxy_v397_sample": sample,
        **caps,
    }
