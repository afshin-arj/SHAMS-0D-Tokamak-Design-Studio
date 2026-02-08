"""Repair suggestion generator (v296.0)

Explanatory-only: proposes candidate tweaks based on constraint residuals
and optional sensitivity information.

All candidates must be re-verified with frozen truth.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class RepairCandidate:
    deltas: Dict[str, float]
    rationale: str
    priority: float


def propose_repairs(
    base_inputs: Dict[str, Any],
    eval_out: Dict[str, Any],
    sensitivities: Dict[str, Dict[str, float]] | None = None,
    max_candidates: int = 6,
) -> List[RepairCandidate]:
    """Generate bounded repair candidates.

    Strategy (deterministic):
    - Identify worst constraint residual (if present)
    - Propose canonical knobs depending on mechanism tag

    This does *not* attempt to solve; it proposes.
    """

    # Identify worst residual constraint
    worst = None
    if isinstance(eval_out.get("constraints"), list):
        for c in eval_out["constraints"]:
            try:
                r = float(c.get("residual", 0.0))
            except Exception:
                continue
            if worst is None or r < worst[0]:
                worst = (r, c)

    mech = "UNKNOWN"
    if worst is not None:
        mech = str(worst[1].get("mechanism", worst[1].get("domain", "UNKNOWN"))).upper()

    cands: List[RepairCandidate] = []

    def add(delta: Dict[str, float], rationale: str, prio: float):
        cands.append(RepairCandidate(deltas=delta, rationale=rationale, priority=float(prio)))

    # Canonical knob proposals
    if mech in {"EXHAUST", "HEAT_FLUX", "DETACHMENT"}:
        add({"flux_expansion": float(base_inputs.get("flux_expansion", 6.0)) * 1.15}, "Increase flux expansion (reduce q⊥)", 0.9)
        add({"Paux_MW": float(base_inputs.get("Paux_MW", 0.0)) * 0.9}, "Reduce auxiliary power to lower P_sep", 0.7)
    elif mech in {"MAGNET", "STRESS", "QUENCH"}:
        add({"B0_T": float(base_inputs.get("B0_T", 5.0)) * 0.95}, "Reduce B0 to improve magnet margin", 0.85)
        add({"R0_m": float(base_inputs.get("R0_m", 3.0)) * 1.05}, "Increase major radius to reduce stress/field", 0.75)
    elif mech in {"PLASMA", "BETA", "Q", "CONFINEMENT"}:
        add({"H98": float(base_inputs.get("H98", 1.0)) * 1.05}, "Increase confinement factor (scenario improvement)", 0.6)
        add({"Ti_keV": float(base_inputs.get("Ti_keV", 10.0)) * 1.05}, "Increase Ti to raise fusion reactivity", 0.5)
    else:
        add({"R0_m": float(base_inputs.get("R0_m", 3.0)) * 1.03}, "Slightly increase size to widen margins", 0.4)

    # Sensitivity-guided candidate (if available)
    if isinstance(sensitivities, dict) and len(sensitivities) > 0:
        # Pick input with largest absolute sensitivity on feasibility proxy, if present
        # We look for a key 'feasible_score' in sensitivities; otherwise skip.
        fs = sensitivities.get("feasible_score")
        if isinstance(fs, dict) and fs:
            k = max(fs, key=lambda kk: abs(float(fs.get(kk, 0.0))))
            sgn = 1.0 if float(fs.get(k, 0.0)) > 0 else -1.0
            add({k: float(base_inputs.get(k, 0.0)) + sgn * 0.05 * (abs(float(base_inputs.get(k, 1.0))) + 1.0)}, f"Sensitivity-guided tweak of {k}", 0.65)

    # Deterministic sort
    cands.sort(key=lambda c: (-c.priority, c.rationale))
    return cands[: max(1, int(max_candidates))]
