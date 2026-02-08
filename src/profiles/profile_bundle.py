"""SHAMS 1.5D Algebraic Profile Bundle (v296.0)

Law compliance:
- Deterministic, algebraic, conservative.
- No hidden iteration.
- Intended as an *authority overlay* that produces diagnostics and margins.

This module provides parametric profile proxies for:
- pressure peaking factor
- current profile shaping proxies (li, qmin surrogate)
- bootstrap fraction proxy

All outputs are bounded and validity-tagged.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple
import math


@dataclass(frozen=True)
class ProfileSpec:
    """Parametric (dimensionless) profile spec.

    Parameters are interpreted as bounded knobs, not fitted physics.

    Args:
        p_peaking: pressure peaking factor proxy >=1.
        j_peaking: current density peaking factor proxy >=1.
        shear_shape: 0..1 proxy for shear enhancement.
    """

    p_peaking: float = 1.4
    j_peaking: float = 1.2
    shear_shape: float = 0.5


@dataclass(frozen=True)
class ProfileBundle:
    p_peaking: float
    j_peaking: float
    li_proxy: float
    qmin_proxy: float
    f_bootstrap: float
    validity: Dict[str, str]


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def evaluate_profile_bundle(
    spec: ProfileSpec,
    beta_n: float,
    q95: float,
    r_major_m: float,
    a_minor_m: float,
) -> ProfileBundle:
    """Compute conservative profile proxies.

    This intentionally avoids using detailed transport.

    Returns:
        ProfileBundle with bounded proxies and validity flags.
    """

    validity: Dict[str, str] = {}

    ppk = _clamp(spec.p_peaking, 1.0, 2.5)
    jpk = _clamp(spec.j_peaking, 1.0, 2.0)
    shear = _clamp(spec.shear_shape, 0.0, 1.0)

    if spec.p_peaking != ppk:
        validity["p_peaking"] = "clamped"
    if spec.j_peaking != jpk:
        validity["j_peaking"] = "clamped"
    if spec.shear_shape != shear:
        validity["shear_shape"] = "clamped"

    # li proxy: typical tokamak li ~ 0.6..1.2. Make it depend weakly on current peaking.
    li_proxy = _clamp(0.65 + 0.35 * (jpk - 1.0), 0.55, 1.25)

    # qmin proxy: conservative surrogate linking q95, li, shear.
    # lower qmin with higher beta_n and higher peaking; shear increases qmin.
    aspect = r_major_m / max(1e-9, a_minor_m)
    aspect = max(1.2, min(6.0, aspect))

    # Base relation: qmin ~ 0.6*q95 / (1 + c_beta*beta_n + c_pk*(ppk-1) + c_li*(li-0.8)) * (1+0.25*shear)
    denom = 1.0 + 0.18 * max(0.0, beta_n) + 0.22 * (ppk - 1.0) + 0.15 * (li_proxy - 0.8) + 0.05 * (aspect - 2.5)
    qmin_proxy = (0.6 * max(0.1, q95) / denom) * (1.0 + 0.25 * shear)
    qmin_proxy = _clamp(qmin_proxy, 0.7, max(0.9, 0.95 * q95))

    # Bootstrap fraction proxy: bounded 0..0.7, increases with beta_n and peaking, decreases with q95.
    f_boot = 0.10 + 0.08 * max(0.0, beta_n) + 0.05 * (ppk - 1.0) - 0.015 * (max(0.0, q95) - 3.0)
    f_boot = _clamp(f_boot, 0.0, 0.7)

    return ProfileBundle(
        p_peaking=ppk,
        j_peaking=jpk,
        li_proxy=li_proxy,
        qmin_proxy=qmin_proxy,
        f_bootstrap=f_boot,
        validity=validity,
    )


def default_profile_spec() -> ProfileSpec:
    return ProfileSpec()


def profile_assumption_tag(bundle: ProfileBundle) -> str:
    """Human-facing tag for governance overlays."""
    if bundle.p_peaking >= 1.8:
        return "PROFILE:peaked"
    if bundle.p_peaking <= 1.2:
        return "PROFILE:flat"
    return "PROFILE:moderate"
