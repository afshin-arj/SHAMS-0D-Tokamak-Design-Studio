"""
SHAMS — Impurity Species & Radiation Partition Authority (v399.0)
Author: © 2026 Afshin Arjhangmehr

Deterministic, bounded, *proxy* impurity radiation model with:
- multi-species impurity mix,
- explicit Zeff computation from quasi-neutrality,
- radiation partition ledger (core/edge/SOL/divertor),
- audit-friendly per-species contributions.

Law compliance:
- No hidden iteration.
- No Monte Carlo.
- Pure algebraic evaluation with explicit validity flags.

Notes:
- Lz(T) proxy envelopes are conservative placeholders; NOT a CR-model.
- This authority is intended for feasibility screening and dominance attribution.

"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, Any
import math
import json

# ----------------------------
# Species definitions (proxy)
# ----------------------------

@dataclass(frozen=True)
class SpeciesDef:
    Z: int
    # Lz envelope params: (mu_logT, sigma, floor, peak) in W m^3
    lz_params: Tuple[float, float, float, float]


# Supported species set (expandable without breaking schema)
# mu is log(T_keV) at peak; sigma is log-space width
_SPECIES: Dict[str, SpeciesDef] = {
    # Light / medium-Z
    "C":  SpeciesDef(Z=6,  lz_params=(math.log(0.25), 0.50, 8e-35, 2.5e-33)),
    "N":  SpeciesDef(Z=7,  lz_params=(math.log(0.35), 0.52, 8e-35, 3.0e-33)),
    "Ne": SpeciesDef(Z=10, lz_params=(math.log(0.50), 0.55, 8e-35, 5.0e-33)),
    "Ar": SpeciesDef(Z=18, lz_params=(math.log(1.00), 0.60, 8e-35, 8.0e-33)),
    # Noble radiators (high-T envelopes; proxy)
    "Kr": SpeciesDef(Z=36, lz_params=(math.log(2.00), 0.70, 5e-35, 1.6e-32)),
    "Xe": SpeciesDef(Z=54, lz_params=(math.log(2.50), 0.75, 5e-35, 2.2e-32)),
    # Wall / high-Z
    "W":  SpeciesDef(Z=74, lz_params=(math.log(4.00), 0.85, 5e-35, 3.0e-32)),
    # Helium ash (weak radiator; treat as dilution-only with tiny Lz)
    "He": SpeciesDef(Z=2,  lz_params=(math.log(1.00), 0.80, 1e-35, 2e-34)),
}

_ALLOWED = tuple(sorted(_SPECIES.keys()))


def allowed_species() -> Tuple[str, ...]:
    return _ALLOWED


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def lz_envelope_Wm3(species: str, t_keV: float) -> float:
    """Smooth bounded proxy for Lz(T) in W m^3 (multi-species)."""
    sp = str(species).strip()
    if sp not in _SPECIES:
        # Unknown species: conservative fallback (low floor, low peak)
        sp = "Ne"
    t_keV = _clamp(float(t_keV), 0.05, 50.0)
    logt = math.log(t_keV)
    mu, sigma, floor, peak = _SPECIES[sp].lz_params
    bump = math.exp(-0.5 * ((logt - mu) / sigma) ** 2)
    return float(floor + (peak - floor) * bump)


# ----------------------------
# Contracts and results
# ----------------------------

@dataclass(frozen=True)
class ImpurityMixContractV399:
    """
    Multi-species impurity contract.

    Fractions are defined as f_z = n_z / n_e (dimensionless).
    Partitions are global fractions applied to all impurity radiation.
    """
    species_fz: Dict[str, float]
    f_core: float = 0.50
    f_edge: float = 0.20
    f_sol: float = 0.20
    f_divertor: float = 0.10

    @staticmethod
    def from_json(s: str) -> "ImpurityMixContractV399":
        obj = json.loads(s) if (isinstance(s, str) and s.strip()) else {}
        species_fz = obj.get("species_fz", obj.get("species", {}))
        if not isinstance(species_fz, dict):
            species_fz = {}
        # sanitize numeric
        sf: Dict[str, float] = {}
        for k, v in species_fz.items():
            try:
                fk = str(k).strip()
                fv = float(v)
            except Exception:
                continue
            if fk:
                sf[fk] = fv
        return ImpurityMixContractV399(
            species_fz=sf,
            f_core=float(obj.get("f_core", 0.50)),
            f_edge=float(obj.get("f_edge", 0.20)),
            f_sol=float(obj.get("f_sol", 0.20)),
            f_divertor=float(obj.get("f_divertor", 0.10)),
        )


@dataclass(frozen=True)
class RadiationPartitionV399:
    prad_total_MW: float
    prad_core_MW: float
    prad_edge_MW: float
    prad_sol_MW: float
    prad_div_MW: float
    zeff: float
    fuel_ion_fraction: float
    by_species_MW: Dict[str, float]
    validity: Dict[str, Any]


def _sanitize_partitions(f_core: float, f_edge: float, f_sol: float, f_div: float) -> Tuple[float, float, float, float, Dict[str, Any]]:
    v: Dict[str, Any] = {}
    # basic numeric
    fc = float(f_core); fe = float(f_edge); fs = float(f_sol); fd = float(f_div)
    if not (math.isfinite(fc) and math.isfinite(fe) and math.isfinite(fs) and math.isfinite(fd)):
        return 0.5, 0.2, 0.2, 0.1, {"partitions": "nonfinite_defaulted"}
    # clamp to [0,1]
    fc = _clamp(fc, 0.0, 1.0); fe = _clamp(fe, 0.0, 1.0); fs = _clamp(fs, 0.0, 1.0); fd = _clamp(fd, 0.0, 1.0)
    s = fc + fe + fs + fd
    if s <= 0.0:
        return 0.5, 0.2, 0.2, 0.1, {"partitions": "sum_zero_defaulted"}
    if s > 1.0:
        # conservative: renormalize but record flag
        fc, fe, fs, fd = fc / s, fe / s, fs / s, fd / s
        v["partitions_renormalized"] = True
    v["partitions_sum"] = float(fc + fe + fs + fd)
    return fc, fe, fs, fd, v


def evaluate_impurity_radiation_partition_v399(
    contract: ImpurityMixContractV399,
    ne20: float,
    volume_m3: float,
    t_keV: float,
) -> RadiationPartitionV399:
    """
    Deterministic multi-species radiation partition.

    Power model (proxy):
      Pz = n_e * n_z * Lz(T) * V

    where n_z = f_z * n_e.

    Zeff under quasi-neutrality for main ions with Z=1:
      n_main = n_e * (1 - Σ f_z Z)
      Zeff = (n_main + Σ n_z Z^2)/n_e = 1 - Σ f_z Z + Σ f_z Z^2

    Fuel ion fraction (relative to electron density):
      f_fuel = n_main / n_e = 1 - Σ f_z Z

    Validity flags emitted for:
      - negative/too-large impurity charge fraction
      - unknown species
      - partition renormalization

    """
    validity: Dict[str, Any] = {}
    ne20 = float(ne20)
    V = float(volume_m3)
    t_keV = float(t_keV)

    if not (math.isfinite(ne20) and ne20 > 0.0 and math.isfinite(V) and V > 0.0 and math.isfinite(t_keV) and t_keV > 0.0):
        return RadiationPartitionV399(
            prad_total_MW=float("nan"),
            prad_core_MW=float("nan"),
            prad_edge_MW=float("nan"),
            prad_sol_MW=float("nan"),
            prad_div_MW=float("nan"),
            zeff=float("nan"),
            fuel_ion_fraction=float("nan"),
            by_species_MW={},
            validity={"inputs": "nonfinite_or_nonpositive"},
        )

    ne = ne20 * 1e20  # m^-3
    fc, fe, fs, fd, pv = _sanitize_partitions(contract.f_core, contract.f_edge, contract.f_sol, contract.f_divertor)
    validity.update(pv)

    sum_fzZ = 0.0
    sum_fzZ2 = 0.0

    by_species_W: Dict[str, float] = {}
    unknown: Dict[str, float] = {}

    for sp_raw, fz_raw in (contract.species_fz or {}).items():
        try:
            sp = str(sp_raw).strip()
            fz = float(fz_raw)
        except Exception:
            continue
        if not (math.isfinite(fz) and fz > 0.0):
            continue
        if sp not in _SPECIES:
            unknown[sp] = fz
            sp = "Ne"  # conservative mapping
        Z = _SPECIES[sp].Z
        sum_fzZ += fz * float(Z)
        sum_fzZ2 += fz * float(Z * Z)

        nz = fz * ne
        Lz = lz_envelope_Wm3(sp, t_keV)
        Pz_W = ne * nz * Lz * V
        by_species_W[sp] = by_species_W.get(sp, 0.0) + float(Pz_W)

    if unknown:
        validity["unknown_species_mapped_to"] = "Ne"
        validity["unknown_species"] = dict(unknown)

    fuel_frac = 1.0 - sum_fzZ
    if fuel_frac < 0.0:
        validity["charge_neutrality_violation"] = True
        # still compute with floor at zero for reporting
        fuel_frac = 0.0

    zeff = 1.0 - sum_fzZ + sum_fzZ2
    if zeff < 1.0:
        zeff = 1.0
        validity["zeff_clamped_min1"] = True

    prad_total_W = float(sum(by_species_W.values()))
    prad_total_MW = prad_total_W * 1e-6

    prad_core_MW = prad_total_MW * fc
    prad_edge_MW = prad_total_MW * fe
    prad_sol_MW  = prad_total_MW * fs
    prad_div_MW  = prad_total_MW * fd

    by_species_MW = {k: v * 1e-6 for k, v in sorted(by_species_W.items())}
    validity["sum_fzZ"] = float(sum_fzZ)
    validity["sum_fzZ2"] = float(sum_fzZ2)

    return RadiationPartitionV399(
        prad_total_MW=float(prad_total_MW),
        prad_core_MW=float(prad_core_MW),
        prad_edge_MW=float(prad_edge_MW),
        prad_sol_MW=float(prad_sol_MW),
        prad_div_MW=float(prad_div_MW),
        zeff=float(zeff),
        fuel_ion_fraction=float(fuel_frac),
        by_species_MW=by_species_MW,
        validity=validity,
    )
