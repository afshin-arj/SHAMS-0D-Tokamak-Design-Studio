from __future__ import annotations
"""Analytic 1/2-D profile utilities (PROCESS-inspired).

PROCESS uses analytic radial profiles ("1/2-D") to compute consistent averages and sensitivities.
SHAMS implements a lightweight subset for Windows-native use:

- Parabolic profiles (single exponent/peaking control)
- Pedestal profiles (piecewise core + pedestal + edge)
- Numerical normalization so the profile matches a *requested volume average*
- Derived averages/peaking factors used by fusion/radiation diagnostics

Conventions:
- ``rho`` is normalized minor radius in [0, 1]
- ``value(rho)`` returns the local value at rho
- ``volume_average()`` uses a simple cylindrical weighting ~ rho (good enough for 0-D coupling)

These profiles are *optional*: SHAMS runs with profiles disabled by default.
"""

from dataclasses import dataclass
import math
from typing import Callable, Tuple

# NOTE:
# This module provides lightweight, PROCESS-inspired analytic ("1/2-D") profile
# scaffolding for SHAMS. Profiles are defined on normalized radius rho in [0, 1].
#
# Design goals:
# - Pure Python, Windows-friendly (no SciPy dependency).
# - Stable normalization: given a desired volume-average f_avg, the profile is
#   scaled so that <f>_V = f_avg under a simple circular cross-section proxy
#   weighting w(rho) ~ 2*rho.
# - Expose a few derived averages needed by downstream physics:
#     * center value (peaking)
#     * volume average (by construction)
#     * line average (simple chord proxy)
#     * <f^2>_V (for quadratic processes like fusion and radiation proxies)

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _vol_weight(rho: float) -> float:
    # Circular proxy: dV ~ 2*rho drho
    return 2.0 * rho

def _trapz(fn: Callable[[float], float], n: int = 400) -> float:
    # Simple trapezoid integral on [0,1]
    n = max(int(n), 50)
    h = 1.0 / n
    s = 0.5 * (fn(0.0) + fn(1.0))
    for i in range(1, n):
        s += fn(i * h)
    return s * h

@dataclass(frozen=True)
class ParabolicProfile:
    """Parabolic-like profile: f(rho) = f0 * (1 - rho^2)^alpha.

    Normalized such that volume average (proxy) equals f_avg.
    """
    f_avg: float
    alpha: float = 1.0

    def _shape(self, rho: float) -> float:
        rho = _clamp(float(rho), 0.0, 1.0)
        return max(1.0 - rho * rho, 0.0) ** max(self.alpha, 0.0)

    def _shape_vol_avg(self) -> float:
        # Analytic: ∫0^1 (1-rho^2)^a * 2*rho drho = 1/(a+1)
        return 1.0 / max(max(self.alpha, 0.0) + 1.0, 1e-30)

    def _scale(self) -> float:
        return float(self.f_avg) / max(self._shape_vol_avg(), 1e-30)

    def value(self, rho: float) -> float:
        return self._scale() * self._shape(rho)

    def center_value(self) -> float:
        return self.value(0.0)

    def volume_average(self) -> float:
        return float(self.f_avg)

    def line_average(self) -> float:
        # Very simple chord proxy: <f>_line ≈ ∫0^1 f(rho) d rho
        return _trapz(lambda r: self.value(r), n=400)

    def vol_average_square(self) -> float:
        # <f^2>_V ≈ ∫ f(rho)^2 * 2*rho drho
        return _trapz(lambda r: (self.value(r) ** 2) * _vol_weight(r), n=600)

@dataclass(frozen=True)
class PedestalProfile:
    """Simple piecewise pedestal profile, scaled to match volume average f_avg.

    Parameters:
      - alpha_core: core peaking exponent (higher -> more peaked).
      - rho_ped: normalized radius of the pedestal top (0<rho_ped<1).
      - f_edge_frac: edge value relative to pedestal-top value (0..1).

    Shape:
      - Core region rho<=rho_ped:
          g(rho) = g_ped + (1-g_ped)*(1-(rho/rho_ped)^2)^alpha_core
      - Pedestal/edge region rho>rho_ped:
          linear drop from g_ped at rho_ped to g_edge=g_ped*f_edge_frac at rho=1.

    We choose g_ped as a mild function of alpha_core to avoid an extra knob:
        g_ped = clamp( 1/(1+0.5*alpha_core), 0.15, 0.85 )

    Then scale factor s is chosen so that <s*g>_V = f_avg.
    """
    f_avg: float
    alpha_core: float = 1.0
    rho_ped: float = 0.9
    f_edge_frac: float = 0.2

    def _g_ped(self) -> float:
        a = max(float(self.alpha_core), 0.0)
        return _clamp(1.0 / (1.0 + 0.5 * a), 0.15, 0.85)

    def _shape(self, rho: float) -> float:
        rho = _clamp(float(rho), 0.0, 1.0)
        rp = _clamp(float(self.rho_ped), 0.2, 0.98)
        gped = self._g_ped()
        if rho <= rp:
            x = rho / max(rp, 1e-9)
            core = max(1.0 - x * x, 0.0) ** max(float(self.alpha_core), 0.0)
            return gped + (1.0 - gped) * core
        # edge region
        gedge = gped * _clamp(float(self.f_edge_frac), 0.0, 1.0)
        t = (rho - rp) / max(1.0 - rp, 1e-9)
        return (1.0 - t) * gped + t * gedge

    def _shape_vol_avg(self) -> float:
        return _trapz(lambda r: self._shape(r) * _vol_weight(r), n=800)

    def _scale(self) -> float:
        return float(self.f_avg) / max(self._shape_vol_avg(), 1e-30)

    def value(self, rho: float) -> float:
        return self._scale() * self._shape(rho)

    def center_value(self) -> float:
        return self.value(0.0)

    def volume_average(self) -> float:
        return float(self.f_avg)

    def line_average(self) -> float:
        return _trapz(lambda r: self.value(r), n=500)

    def vol_average_square(self) -> float:
        return _trapz(lambda r: (self.value(r) ** 2) * _vol_weight(r), n=900)

@dataclass(frozen=True)
class PlasmaProfiles:
    """Container for ne, Ti, Te profile objects."""
    ne: object
    Ti: object
    Te: object

    def peaking_factors(self) -> Tuple[float, float, float]:
        def peak(profile) -> float:
            f0 = float(profile.value(0.0))
            favg = float(getattr(profile, "f_avg", float("nan")))
            return f0 / max(favg, 1e-30)
        return peak(self.ne), peak(self.Ti), peak(self.Te)

    def derived_averages(self) -> dict:
        # A few useful derived quantities for diagnostics and PROCESS-like workflows
        ne0 = float(self.ne.value(0.0))
        Ti0 = float(self.Ti.value(0.0))
        Te0 = float(self.Te.value(0.0))
        ne_line = float(getattr(self.ne, "line_average")())
        Ti_line = float(getattr(self.Ti, "line_average")())
        Te_line = float(getattr(self.Te, "line_average")())
        ne2_vol = float(getattr(self.ne, "vol_average_square")())
        ne_avg = float(getattr(self.ne, "f_avg", float("nan")))
        return {
            "ne0_over_neV": ne0 / max(ne_avg, 1e-30),
            "Ti0_over_TiV": Ti0 / max(float(getattr(self.Ti, "f_avg", float("nan"))), 1e-30),
            "Te0_over_TeV": Te0 / max(float(getattr(self.Te, "f_avg", float("nan"))), 1e-30),
            "ne_line_over_neV": ne_line / max(ne_avg, 1e-30),
            "Ti_line_over_TiV": Ti_line / max(float(getattr(self.Ti, "f_avg", float("nan"))), 1e-30),
            "Te_line_over_TeV": Te_line / max(float(getattr(self.Te, "f_avg", float("nan"))), 1e-30),
            "ne2_over_neV2": ne2_vol / max(ne_avg * ne_avg, 1e-30),
        }
