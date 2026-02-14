from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


def default_phases_for_point(inp: Any) -> list["PhaseSpec"]:
    """Return a conservative default quasi-static phase sequence.

    This helper is used by UI and CCFS verification when the user has not
    provided an explicit phase library.

    Phases are intentionally mild and algebraic: they do not attempt to model
    dynamics, only to probe a few reviewer-relevant operating slices.
    """
    try:
        Paux = float(getattr(inp, "Paux_MW", 0.0))
    except Exception:
        Paux = 0.0
    try:
        fG = float(getattr(inp, "fG", 0.8))
    except Exception:
        fG = 0.8

    # Ramp: slightly higher auxiliary demand and lower density margin.
    ramp = PhaseSpec(
        name="ramp",
        input_overrides={
            "Paux_MW": max(Paux, 0.0) * 1.15,
            "fG": max(min(fG * 0.85, 1.2), 0.1),
        },
        notes="Quasi-static ramp proxy: modestly higher Paux, modestly reduced density margin.",
    )
    flat = PhaseSpec(name="flat_top", input_overrides={}, notes="Nominal operating point.")
    eop = PhaseSpec(
        name="end_of_pulse",
        input_overrides={
            "Paux_MW": max(Paux, 0.0) * 0.90,
            "fG": max(min(fG * 0.95, 1.2), 0.1),
        },
        notes="Quasi-static end-of-pulse proxy: slightly reduced heating.",
    )
    return [ramp, flat, eop]


@dataclass(frozen=True)
class PhaseSpec:
    """Quasi-static operating phase specification.

    Phase evaluation is *outer-loop only*:
      - applies deterministic input overrides to a baseline PointInputs
      - calls frozen truth (physics + constraints)
      - applies an optional policy overlay (constraint tier semantics)
    No ODEs, no PF solvers, no dynamics.

    Notes
    -----
    - input_overrides: maps PointInputs attribute -> value
    - policy_overrides: merged into the baseline policy contract dict passed to constraints
    """
    name: str
    input_overrides: Optional[Dict[str, Any]] = None
    policy_overrides: Optional[Dict[str, Any]] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "phase_spec.v1",
            "name": str(self.name),
            "input_overrides": dict(self.input_overrides or {}),
            "policy_overrides": dict(self.policy_overrides or {}),
            "notes": str(self.notes or ""),
        }
