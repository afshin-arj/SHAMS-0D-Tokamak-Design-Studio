from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Tuple

@dataclass(frozen=True)
class AnalyticProfiles:
    """Lightweight analytic profile set.

    We keep SHAMS Windows-native by using analytic forms. Profiles are used to:
      - generate *consistent* volume averages
      - provide gradient proxies for bootstrap sensitivity
      - support documentation / diagnostics

    By default, SHAMS remains 0-D. When enabled, profiles are *diagnostic* and do not
    change legacy inputs unless the caller explicitly opts into profile closures.
    """
    r_grid: Tuple[float, ...]   # normalized radius 0..1
    T_keV: Tuple[float, ...]
    n20: Tuple[float, ...]
    meta: Dict[str, float]

def _parabolic(shape_alpha: float, r: float) -> float:
    # f(r) = (1 - r^2)^alpha, clipped at 0
    x = 1.0 - r*r
    return (x if x > 0.0 else 0.0) ** shape_alpha

def volume_average_parabolic(f0: float, alpha: float) -> float:
    """Volume average of f(r)=f0*(1-r^2)^alpha in a circular cross-section.

    <f> = 2 ∫_0^1 f(r) r dr  = f0 * 2 ∫_0^1 (1-r^2)^alpha r dr = f0/(alpha+1)
    (exact for this functional form).
    """
    return f0 / (alpha + 1.0)

def central_from_volume_avg_parabolic(fbar: float, alpha: float) -> float:
    return fbar * (alpha + 1.0)

def build_profiles_from_volume_avgs(
    Tbar_keV: float,
    nbar20: float,
    alpha_T: float,
    alpha_n: float,
    ngrid: int = 101,
    pedestal_enabled: bool = False,
    ped_width_a: float = 0.05,
    ped_top_T_frac: float = 0.6,
    ped_top_n_frac: float = 0.8,
    pedestal_model: str = 'tanh',
    pedestal_edge_T_frac: float = 0.2,
    pedestal_edge_n_frac: float = 0.2,
) -> AnalyticProfiles:
    """Construct analytic profiles consistent with provided volume averages.

    Pedestal model (optional): a smooth tanh transition applied near the edge that
    limits the edge value to a fraction of the core central value. This is used as a
    diagnostic profile only.
    """
    r = [i/(ngrid-1) for i in range(ngrid)]
    # Determine central values such that the *core* parabolic profile has the requested volume average.
    T0 = central_from_volume_avg_parabolic(Tbar_keV, alpha_T)
    n0 = central_from_volume_avg_parabolic(nbar20, alpha_n)

    def pedestal_factor(rr: float, top_frac: float, edge_frac: float) -> float:
        if not pedestal_enabled:
            return 1.0
        model = (pedestal_model or "tanh").strip().lower()
        # pedestal location in normalized radius
        r_ped = max(0.0, 1.0 - float(ped_width_a))
        # Core value factor is 1.0 in the core; this function returns a multiplicative
        # factor applied to the *core parabolic* value.
        if model == "two_zone":
            # Piecewise: core factor ~1 up to r_ped, then linearly ramps from top_frac to edge_frac.
            if rr <= r_ped:
                return 1.0
            # The pedestal "top" is enforced by clamping to top_frac (relative to central) later,
            # so here we return the ramp factor only.
            t = (rr - r_ped) / max(1e-6, 1.0 - r_ped)
            return max(edge_frac, top_frac + (edge_frac - top_frac) * t)
        # Default: smooth tanh transition from 1.0 in the core to top_frac at the edge.
        k = 12.0 / max(1e-6, float(ped_width_a))
        s = 0.5*(1.0 - math.tanh(k*(rr - r_ped)))
        # s≈1 in core (rr<<r_ped), s≈0 at edge
        return max(edge_frac, top_frac + (1.0 - top_frac)*s)

    T = []
    n = []
    model = (pedestal_model or "tanh").strip().lower()
    r_ped = max(0.0, 1.0 - float(ped_width_a))
    # Two-zone pedestal: core parabolic until r_ped, then a linear pedestal from top->edge
    # specified as fractions of central values. This is deterministic and deliberately simple.
    T_ped_top = float(ped_top_T_frac) * T0
    n_ped_top = float(ped_top_n_frac) * n0
    T_edge = float(pedestal_edge_T_frac) * T0
    n_edge = float(pedestal_edge_n_frac) * n0

    for rr in r:
        if pedestal_enabled and model == "two_zone" and rr >= r_ped:
            t = (rr - r_ped) / max(1e-6, 1.0 - r_ped)
            T_val = T_ped_top + (T_edge - T_ped_top) * t
            n_val = n_ped_top + (n_edge - n_ped_top) * t
        else:
            T_val = T0 * _parabolic(alpha_T, rr) * pedestal_factor(rr, ped_top_T_frac, pedestal_edge_T_frac)
            n_val = n0 * _parabolic(alpha_n, rr) * pedestal_factor(rr, ped_top_n_frac, pedestal_edge_n_frac)
        T.append(T_val)
        n.append(n_val)

    meta = {
        "T0_keV": T0,
        "n0_1e20_m3": n0,
        "alpha_T": alpha_T,
        "alpha_n": alpha_n,
        "pedestal_enabled": float(pedestal_enabled),
        "ped_width_a": ped_width_a,
        "ped_top_T_frac": ped_top_T_frac,
        "ped_top_n_frac": ped_top_n_frac,
        "pedestal_model": str(pedestal_model),
        "pedestal_edge_T_frac": pedestal_edge_T_frac,
        "pedestal_edge_n_frac": pedestal_edge_n_frac,
    }
    return AnalyticProfiles(tuple(r), tuple(T), tuple(n), meta)

def gradient_proxy_at_pedestal(profiles: AnalyticProfiles) -> Dict[str, float]:
    """Return simple gradient proxies near the pedestal top.

    Used for bootstrap sensitivity. We compute |d ln p / d r| at r ~ 0.9.
    """
    r = profiles.r_grid
    # pick index closest to 0.9
    target = 0.9
    i = min(range(len(r)), key=lambda j: abs(r[j]-target))
    # finite difference
    i0 = max(1, min(len(r)-2, i))
    dr = r[i0+1]-r[i0-1]
    T = profiles.T_keV
    n = profiles.n20
    p = [n[k]*T[k] for k in range(len(r))]
    def safe_ln(x): 
        return math.log(max(1e-30, x))
    dlnp_dr = (safe_ln(p[i0+1]) - safe_ln(p[i0-1]))/dr
    return {"abs_dlnp_dr@r~0.9": abs(dlnp_dr)}