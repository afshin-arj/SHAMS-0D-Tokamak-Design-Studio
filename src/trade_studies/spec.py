from __future__ import annotations

"""Trade Study Studio specifications (v303.0).

This layer is *exploration governance* only. It does not change frozen truth.
All candidate evaluation is performed by the Evaluator or the physics point
function and constraints ledger.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple


Bounds = Dict[str, Tuple[float, float]]


@dataclass(frozen=True)
class KnobSet:
    """Named knob set with bounds in PointInputs field units."""

    name: str
    bounds: Bounds
    notes: str = ""


def default_knob_sets() -> List[KnobSet]:
    """Return a small canonical library of knob sets.

    Bounds are intentionally conservative and wide enough for early trade studies.
    Users can always override.
    """

    return [
        KnobSet(
            name="Geometry + Field (R0,a,kappa,delta,Bt)",
            bounds={
                "R0_m": (2.5, 9.0),
                "a_m": (0.8, 3.0),
                "kappa": (1.5, 2.4),
                "delta": (0.2, 0.6),
                "Bt_T": (3.0, 12.0),
            },
            notes="Geometry/field exploration: shifts all subsystem margins; good for family discovery.",
        ),
        KnobSet(
            name="Plasma + Heating (Ip,fG,Paux)",
            bounds={
                "Ip_MA": (5.0, 25.0),
                "fG": (0.3, 1.2),
                "Paux_MW": (0.0, 200.0),
            },
            notes="Plasma + heating knobs; useful for burn and confinement regime scans.",
        ),
        KnobSet(
            name="Exhaust + Radiation (lambda_q_mult, f_rad)",
            bounds={
                "lambda_q_mult": (0.6, 1.6),
                "f_rad": (0.1, 0.9),
            },
            notes="Exhaust / radiation levers for divertor constraints; multiplier is Eich λq factor.",
        ),
        KnobSet(
            name="Magnet + Build (R0,Bt,hts_Jc_mult)",
            bounds={
                "R0_m": (2.5, 9.0),
                "Bt_T": (3.0, 12.0),
                "hts_Jc_mult": (0.7, 1.4),
            },
            notes="Magnet realism / HTS margin exploration; pairs well with stress constraints.",
        ),
    ]
