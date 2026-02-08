"""Impurity species library and radiation partitions (v320.0).

This module provides deterministic, conservative proxies for impurity radiation.
It is NOT a substitute for collisional-radiative modeling; it exists to:
- make impurity strategy explicit,
- expose dilution and radiation partitions,
- support robust feasibility screening.

Law compliance:
- No hidden iteration.
- No Monte Carlo.
- Bounded outputs with explicit validity flags.

Radiative efficiency proxy:
- We ship smooth envelope functions Lz(T) [W m^3] for a few species.
- These are *not* fitted to a specific database in this release. They are
  conservative placeholders with clear bounds, suitable for relative screening.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Tuple
import math

Species = Literal["C", "N", "Ne", "Ar", "W"]


@dataclass(frozen=True)
class ImpurityContract:
    species: Species = "Ne"
    # Seeding fraction relative to electron density (dimensionless, <=1e-2 typical).
    f_z: float = 3e-4
    # Partition fractions (must sum <=1; remainder treated as unmodelled -> conservative core).
    # Partitions are intentionally coarse: core / edge / SOL / divertor.
    f_core: float = 0.50
    f_edge: float = 0.20
    f_sol: float = 0.20
    f_divertor: float = 0.10


@dataclass(frozen=True)
class RadiationPartition:
    prad_total_MW: float
    prad_core_MW: float
    prad_edge_MW: float
    prad_sol_MW: float
    prad_div_MW: float
    zeff_proxy: float
    fuel_ion_fraction: float
    validity: Dict[str, str]


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _lz_envelope_Wm3(species: Species, t_keV: float) -> float:
    """Smooth bounded proxy for Lz(T) in W m^3.

    We use broad log-normal bumps with species-dependent peaks.
    The intent is conservative order-of-magnitude screening.
    """

    t_keV = max(0.05, min(50.0, t_keV))
    logt = math.log(t_keV)

    # Species peak parameters (log-space)
    params = {
        # Light impurities peak at lower temperatures.
        "C":  (math.log(0.25), 0.50, 8e-35, 2.5e-33),
        "N":  (math.log(0.35), 0.52, 8e-35, 3.0e-33),
        "Ne": (math.log(0.50), 0.55, 8e-35, 5.0e-33),
        "Ar": (math.log(1.00), 0.60, 8e-35, 8.0e-33),
        # Tungsten: very high-Z; use a broad high-T envelope (proxy).
        "W":  (math.log(4.00), 0.85, 5e-35, 3.0e-32),
    }
    mu, sigma, floor, peak = params[str(species)]
    bump = math.exp(-0.5 * ((logt - mu) / sigma) ** 2)
    lz = floor + (peak - floor) * bump
    return lz


def evaluate_impurity_radiation_partition(
    contract: ImpurityContract,
    ne20: float,
    volume_m3: float,
    t_keV: float,
) -> RadiationPartition:
    """Compute radiation partition and dilution proxies.

    Args:
        contract: impurity contract knobs.
        ne20: volume-averaged electron density in 1e20 m^-3.
        volume_m3: plasma volume.
        t_keV: representative core temperature.

    Returns:
        RadiationPartition with conservative totals and validity flags.
    """

    validity: Dict[str, str] = {}

    fz = _clamp(contract.f_z, 0.0, 1e-2)
    if fz != contract.f_z:
        validity["f_z"] = "clamped"

    f_core = _clamp(contract.f_core, 0.0, 1.0)
    f_edge = _clamp(contract.f_edge, 0.0, 1.0)
    f_sol = _clamp(getattr(contract, "f_sol", 0.0), 0.0, 1.0)
    f_div = _clamp(getattr(contract, "f_divertor", 0.0), 0.0, 1.0)

    s = f_core + f_edge + f_sol + f_div
    if s > 1.0:
        # renormalize to sum=1 but mark; conservative: push remainder to core later.
        f_core, f_edge, f_sol, f_div = f_core / s, f_edge / s, f_sol / s, f_div / s
        validity["partition"] = "renormalized"

    ne = max(0.0, ne20) * 1e20
    vol = max(1e-6, volume_m3)

    # nZ proxy: fz * ne. Radiated power ~ n_e * n_Z * Lz(T) * V.
    nz = fz * ne
    lz = _lz_envelope_Wm3(contract.species, t_keV)

    prad_W = ne * nz * lz * vol
    prad_MW = prad_W * 1e-6

    # Partition. If sum <1, remainder is unmodelled; conservatively assign to core.
    rem = max(0.0, 1.0 - (f_core + f_edge + f_sol + f_div))
    prad_core = prad_MW * (f_core + rem)
    prad_edge = prad_MW * f_edge
    prad_sol = prad_MW * f_sol
    prad_div = prad_MW * f_div

    # Zeff proxy: 1 + C_Z * fz * Zbar. Use representative Zbar.
    zbar = {
        "C":  6.0,
        "N":  7.0,
        "Ne": 10.0,
        "Ar": 18.0,
        "W":  30.0,  # effective charge state in core (proxy)
    }[str(contract.species)]
    zeff = 1.0 + 0.9 * fz * zbar
    zeff = _clamp(zeff, 1.0, 6.0)

    # Fuel ion fraction proxy decreases with Zeff.
    f_fuel = _clamp(1.0 / (1.0 + 0.25 * (zeff - 1.0)), 0.55, 1.0)

    return RadiationPartition(
        prad_total_MW=prad_MW,
        prad_core_MW=prad_core,
        prad_edge_MW=prad_edge,
        prad_sol_MW=prad_sol,
        prad_div_MW=prad_div,
        zeff_proxy=zeff,
        fuel_ion_fraction=f_fuel,
        validity=validity,
    )


def default_impurity_contract() -> ImpurityContract:
    return ImpurityContract()
