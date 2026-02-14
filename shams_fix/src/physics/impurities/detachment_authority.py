"""Impurity radiation & detachment authority (v320.0).

Purpose
-------
Provide a deterministic, algebraic inversion from a divertor heat-flux target
to a *required* SOL+divertor radiated power and an implied impurity seeding
fraction f_z.

This is not a time-domain detachment model.
It is an audit-safe, conservative *budget* layer:

  q_div_target  ->  P_rad(SOL+div) required  ->  f_z required (species envelope)

Law compliance
--------------
- No iteration / solvers.
- No Monte Carlo.
- Purely algebraic with explicit clamps and validity flags.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
import math

from .species_library import Species, _clamp, _lz_envelope_Wm3


@dataclass(frozen=True)
class DetachmentRequirement:
    q_div_no_rad_MW_m2: float
    q_div_target_MW_m2: float
    f_sol_div_required: float
    prad_sol_div_required_MW: float
    # Implied impurity seeding fraction (n_Z / n_e).
    f_z_required: float
    # Diagnostics
    lz_sol_Wm3: float
    validity: Dict[str, str]


def required_sol_div_radiation_fraction(
    q_div_no_rad_MW_m2: float,
    q_div_target_MW_m2: float,
) -> float:
    """Required radiated fraction in SOL+divertor to meet a heat-flux target.

    Assumption: q_div scales approximately linearly with power reaching the divertor.
    """

    q0 = float(q_div_no_rad_MW_m2)
    qt = float(q_div_target_MW_m2)
    if not (math.isfinite(q0) and math.isfinite(qt) and q0 > 0.0 and qt > 0.0):
        return float("nan")
    f = 1.0 - qt / q0
    return max(0.0, min(0.95, f))


def detachment_requirement_from_target(
    *,
    species: Species,
    ne20: float,
    volume_m3: float,
    P_SOL_MW: float,
    q_div_no_rad_MW_m2: float,
    q_div_target_MW_m2: float,
    # Representative SOL temperature for the cooling coefficient envelope.
    T_sol_keV: float = 0.08,
    # Effective radiating volume fraction for SOL+div (conservative).
    f_V_sol_div: float = 0.12,
) -> DetachmentRequirement:
    """Compute required SOL+div radiation and implied f_z.

    Model:
      P_rad_req = f_required * P_SOL
      P_rad_req ≈ n_e^2 * f_z * Lz(T_sol) * V_eff
    with V_eff = f_V_sol_div * V_plasma.

    Notes:
    - This inversion is only meaningful if P_SOL and q_div_no_rad are finite.
    - f_z is clamped to [0,1e-2] and flagged.
    """

    validity: Dict[str, str] = {}

    f_req = required_sol_div_radiation_fraction(q_div_no_rad_MW_m2, q_div_target_MW_m2)
    if not math.isfinite(f_req):
        return DetachmentRequirement(
            q_div_no_rad_MW_m2=float(q_div_no_rad_MW_m2),
            q_div_target_MW_m2=float(q_div_target_MW_m2),
            f_sol_div_required=float("nan"),
            prad_sol_div_required_MW=float("nan"),
            f_z_required=float("nan"),
            lz_sol_Wm3=float("nan"),
            validity={"input": "invalid"},
        )

    Psol = max(0.0, float(P_SOL_MW))
    prad_req = Psol * f_req

    ne = max(0.0, float(ne20)) * 1e20
    V = max(1e-6, float(volume_m3))
    fV = _clamp(float(f_V_sol_div), 1e-3, 0.5)
    if fV != f_V_sol_div:
        validity["f_V_sol_div"] = "clamped"

    Veff = V * fV
    Tsol = _clamp(float(T_sol_keV), 0.03, 1.0)
    if Tsol != T_sol_keV:
        validity["T_sol_keV"] = "clamped"

    lz = _lz_envelope_Wm3(species, Tsol)

    # Invert: prad_req [W] = ne^2 * fz * Lz * Veff
    prad_W = prad_req * 1e6
    denom = max(1e-60, (ne * ne) * lz * Veff)
    fz = prad_W / denom

    fz_clamped = _clamp(fz, 0.0, 1e-2)
    if fz_clamped != fz:
        validity["f_z_required"] = "clamped"

    return DetachmentRequirement(
        q_div_no_rad_MW_m2=float(q_div_no_rad_MW_m2),
        q_div_target_MW_m2=float(q_div_target_MW_m2),
        f_sol_div_required=float(f_req),
        prad_sol_div_required_MW=float(prad_req),
        f_z_required=float(fz_clamped),
        lz_sol_Wm3=float(lz),
        validity=validity,
    )
