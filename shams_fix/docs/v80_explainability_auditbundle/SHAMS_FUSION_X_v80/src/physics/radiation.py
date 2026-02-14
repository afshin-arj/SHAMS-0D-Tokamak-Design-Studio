from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

# NOTE:
# These models are intentionally lightweight and Windows-friendly.
# They aim to provide PROCESS-like *structure* (composition + profile-aware hooks)
# rather than a drop-in numerical replica of PROCESS/Fortran radiation.

@dataclass(frozen=True)
class ImpurityMix:
    """Very small impurity/composition container.

    Provide either:
      - Zeff directly (zeff), or
      - an impurity species + fraction (species, frac) for a rough estimate.

    For serious design work, you should replace/augment the default Lz models with
    validated tables and experiment-informed mixes.
    """
    zeff: float = 2.0
    species: str = "C"
    frac: float = 0.0  # number fraction (rough knob)
    # Optional multi-impurity mix as number fractions, e.g. {"C":0.01,"Ne":0.002}
    species_fracs: Optional[Dict[str, float]] = None


_Z_BY_SPECIES = {
    # Light elements
    "H": 1,
    "D": 1,
    "T": 1,
    "HE": 2,
    "LI": 3,
    "BE": 4,
    "B": 5,
    "C": 6,
    "N": 7,
    "O": 8,
    "NE": 10,
    "AR": 18,
    # Heavy
    "W": 74,
}


def impurity_Z(species: str) -> int:
    sp = (species or "C").strip().upper()
    # Normalize a few common names
    if sp in ("CARBON",):
        sp = "C"
    if sp in ("NEON",):
        sp = "NE"
    if sp in ("ARGON",):
        sp = "AR"
    if sp in ("TUNGSTEN",):
        sp = "W"
    return int(_Z_BY_SPECIES.get(sp, 6))


def estimate_zeff_from_single_impurity(impurity_species: str, impurity_frac: float) -> float:
    """Estimate Zeff from a single impurity number fraction.

    We use a simple two-ion mixture model:
      n_main = 1, Z_main = 1
      n_imp  = f, Z_imp  = Z
      n_e = n_main*Z_main + n_imp*Z_imp
      Zeff = (n_main*Z_main^2 + n_imp*Z_imp^2) / n_e

    This is a rough knob intended for Windows-friendly scoping.
    """
    f = max(float(impurity_frac), 0.0)
    Z = float(impurity_Z(impurity_species))
    ne = 1.0 + f * Z
    return (1.0 + f * Z * Z) / max(ne, 1e-12)


def estimate_zeff_from_mix(species_fracs: Dict[str, float]) -> float:
    """Estimate Zeff from a (species -> number fraction) impurity mix.

    Main ions are assumed Z=1 with unit normalized density. Each impurity i has
    number fraction f_i and nuclear charge Z_i. Then:
      n_e = 1 + Σ f_i Z_i
      Zeff = (1 + Σ f_i Z_i^2) / n_e

    This is a transparent 0-D proxy used for scoping and auditability.
    """
    if not isinstance(species_fracs, dict) or len(species_fracs) == 0:
        return 1.0
    sum_fZ = 0.0
    sum_fZ2 = 0.0
    for sp, f in species_fracs.items():
        try:
            fi = max(float(f), 0.0)
        except Exception:
            continue
        Zi = float(impurity_Z(str(sp)))
        sum_fZ += fi * Zi
        sum_fZ2 += fi * Zi * Zi
    ne = 1.0 + sum_fZ
    return (1.0 + sum_fZ2) / max(ne, 1e-12)


# Lightweight Lz(Te) tables (order-of-magnitude) for a few common impurities.
# These are NOT a numerical replica of PROCESS; they provide PROCESS-like coupling
# (impurity + Te sensitivity) without external dependencies.
_LZ_TABLES = {
    "C": {
        "Te_keV": [0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0],
        "Lz_W_m3": [3e-34, 1.5e-34, 6e-35, 2e-35, 8e-36, 3e-36, 1e-36, 5e-37],
    },
    "NE": {
        "Te_keV": [0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0],
        "Lz_W_m3": [6e-34, 3e-34, 1.2e-34, 4e-35, 1.6e-35, 6e-36, 2e-36, 8e-37],
    },
    "AR": {
        "Te_keV": [0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0],
        "Lz_W_m3": [1.2e-33, 6e-34, 2.4e-34, 8e-35, 3.2e-35, 1.2e-35, 4e-36, 1.5e-36],
    },
    "W": {
        "Te_keV": [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0],
        "Lz_W_m3": [2e-33, 1.2e-33, 6e-34, 3.5e-34, 2.0e-34, 9e-35, 4.5e-35, 2.5e-35],
    },
}


def _loglog_interp(x: float, xs: list[float], ys: list[float]) -> float:
    """Log-log interpolation with clamping."""
    x = max(float(x), 1e-12)
    # clamp
    if x <= xs[0]:
        return float(ys[0])
    if x >= xs[-1]:
        return float(ys[-1])
    # find interval
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            x0, x1 = float(xs[i]), float(xs[i + 1])
            y0, y1 = float(ys[i]), float(ys[i + 1])
            lx = math.log(x)
            t = (lx - math.log(x0)) / max(math.log(x1) - math.log(x0), 1e-12)
            ly = math.log(max(y0, 1e-300)) * (1 - t) + math.log(max(y1, 1e-300)) * t
            return float(math.exp(ly))
    return float(ys[-1])

def bremsstrahlung_W(ne_m3: float, Te_keV: float, zeff: float, volume_m3: float) -> float:
    """Bremsstrahlung power [W] (simple engineering form)."""
    if ne_m3 <= 0.0 or Te_keV <= 0.0 or volume_m3 <= 0.0:
        return 0.0
    C = 5.35e-37
    return C * zeff * (ne_m3**2) * math.sqrt(Te_keV) * volume_m3

def synchrotron_W(ne_m3: float, Te_keV: float, B_T: float, R0_m: float, a_m: float, volume_m3: float) -> float:
    """Very rough synchrotron radiation estimate [W].

    This is a *placeholder* engineering model meant to introduce the right coupling
    (depends on ne, Te, B, geometry). It is NOT a validated replacement for PROCESS's
    synchrotron model.

    Scales ~ ne * Te * B^2 * V with weak geometric dependence.
    """
    if ne_m3 <= 0.0 or Te_keV <= 0.0 or B_T <= 0.0 or volume_m3 <= 0.0:
        return 0.0
    # weak geometry factor
    eps = a_m / max(R0_m, 1e-9)
    g = (1.0 + 2.0*eps)
    # coefficient tuned to keep magnitudes reasonable for typical tokamak parameters
    C = 1.0e-37
    return C * ne_m3 * (Te_keV*1e3) * (B_T**2) * volume_m3 * g

def Lz_W_m3(Te_keV: float, species: str) -> float:
    """Impurity cooling coefficient Lz(Te) [W m^3] using built-in lightweight tables."""
    sp = (species or "C").strip().upper()
    if sp in ("CARBON",):
        sp = "C"
    if sp in ("NEON",):
        sp = "NE"
    if sp in ("ARGON",):
        sp = "AR"
    if sp in ("TUNGSTEN",):
        sp = "W"

    tbl = _LZ_TABLES.get(sp)
    if tbl is None:
        tbl = _LZ_TABLES["C"]
    return _loglog_interp(float(Te_keV), tbl["Te_keV"], tbl["Lz_W_m3"])

def line_radiation_W(ne_m3: float, Te_keV: float, volume_m3: float, mix: ImpurityMix) -> float:
    """Impurity line radiation [W] using Lz(Te) and a simple impurity fraction knob."""
    if ne_m3 <= 0.0 or Te_keV <= 0.0 or volume_m3 <= 0.0:
        return 0.0
    # Support either a single impurity knob (species, frac) or a multi-impurity mix.
    if isinstance(getattr(mix, 'species_fracs', None), dict) and len(mix.species_fracs) > 0:
        P = 0.0
        for sp, f_sp in mix.species_fracs.items():
            try:
                f_imp = max(float(f_sp), 0.0)
            except Exception:
                continue
            Lz = Lz_W_m3(Te_keV, str(sp))
            P += f_imp * (ne_m3**2) * Lz * volume_m3
        return P

    Lz = Lz_W_m3(Te_keV, mix.species)
    # crude: Prad ~ (f_imp) * ne^2 * Lz * V
    f_imp = max(mix.frac, 0.0)
    return f_imp * (ne_m3**2) * Lz * volume_m3

def total_core_radiation_W(
    ne_m3: float,
    Te_keV: float,
    B_T: float,
    R0_m: float,
    a_m: float,
    volume_m3: float,
    mix: Optional[ImpurityMix] = None,
    include_synchrotron: bool = True,
    include_line: bool = True,
) -> Dict[str, float]:
    """Return radiation channel breakdown in Watts."""
    mix = mix or ImpurityMix()
    out: Dict[str, float] = {}
    out["P_brem_W"] = bremsstrahlung_W(ne_m3, Te_keV, mix.zeff, volume_m3)
    out["P_sync_W"] = synchrotron_W(ne_m3, Te_keV, B_T, R0_m, a_m, volume_m3) if include_synchrotron else 0.0
    out["P_line_W"] = line_radiation_W(ne_m3, Te_keV, volume_m3, mix) if include_line else 0.0
    out["P_total_W"] = out["P_brem_W"] + out["P_sync_W"] + out["P_line_W"]
    return out
