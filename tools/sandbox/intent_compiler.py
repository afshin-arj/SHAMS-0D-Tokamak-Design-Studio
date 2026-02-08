from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Tuple

try:
    from src.models.inputs import PointInputs
except Exception:  # pragma: no cover
    from models.inputs import PointInputs  # type: ignore


def compile_intent_to_candidate(
    base: PointInputs,
    *,
    Pfus_target_MW: float,
    Q_target: float,
    overrides: Dict[str, Any] | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """Deterministic algebraic compilation from an intent contract to a candidate PointInputs dict.

    SHAMS law compliance:
      - No solver, no iteration.
      - Produces a *candidate* only; truth remains in evaluator.
      - Explicit NO_SOLUTION when contract is inconsistent.

    Minimal closure (v285.0):
      - Sets Paux = Pfus/Q (proxy for Q definition Pfus/Paux).
      - Applies optional direct overrides to existing PointInputs fields.

    Returns
    -------
    (status, payload)
      status: 'OK' or 'NO_SOLUTION'
      payload: dict with keys: candidate_inputs (dict), trace (list[str]), reason (optional)
    """
    trace: list[str] = []

    try:
        Pfus = float(Pfus_target_MW)
        Q = float(Q_target)
    except Exception:
        return 'NO_SOLUTION', {'reason': 'Pfus_target_MW and Q_target must be numeric', 'trace': trace}

    if not (Pfus >= 0.0):
        return 'NO_SOLUTION', {'reason': 'Pfus_target_MW must be >= 0', 'trace': trace}
    if not (Q > 0.0):
        return 'NO_SOLUTION', {'reason': 'Q_target must be > 0', 'trace': trace}

    d = asdict(base)
    d['Paux_MW'] = float(Pfus / Q)
    trace.append(f"Set Paux_MW = Pfus/Q = {Pfus:.3g}/{Q:.3g} = {d['Paux_MW']:.3g} MW")

    if overrides:
        for k, v in overrides.items():
            if k not in d:
                continue
            d[k] = v
            trace.append(f"Override {k} = {v}")

    # Minimal structural sanity
    if float(d.get('R0_m', 0.0)) <= 0.0 or float(d.get('a_m', 0.0)) <= 0.0:
        return 'NO_SOLUTION', {'reason': 'R0_m and a_m must be > 0', 'trace': trace, 'candidate_inputs': d}

    return 'OK', {'candidate_inputs': d, 'trace': trace}
