# Constraint Sensitivity Fingerprint (descriptive)
# Perturbation-based fragility tags around a feasible candidate (no optimization).

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Callable, Optional

@dataclass
class Fingerprint:
    tags: List[str]
    notes: List[str]

def build_fingerprint(
    candidate: Dict[str, Any],
    evaluator: Callable[[Dict[str, Any]], Dict[str, Any]],
    perturbations: Optional[List[Tuple[str, float]]] = None,
) -> Dict[str, Any]:
    """Return a simple fragility map by perturbing inputs (if available).
    evaluator must be the frozen point evaluator wrapper used elsewhere in SHAMS.
    """
    if perturbations is None:
        perturbations = [
            ("Bt_T", 0.02),
            ("R0_m", 0.02),
            ("Ip_MA", 0.03),
            ("fG", 0.03),
        ]

    base = candidate.get("inputs") or candidate.get("x") or {}
    if not isinstance(base, dict) or not base:
        return {"tags": ["(insufficient inputs for fingerprint)"], "notes": []}

    tags: List[str] = []
    notes: List[str] = []
    for key, frac in perturbations:
        if key not in base:
            continue
        x = dict(base)
        try:
            x[key] = float(x[key]) * (1.0 + float(frac))
        except Exception:
            continue
        try:
            res = evaluator(x)
        except Exception as e:
            notes.append(f"{key} +{frac*100:.1f}%: evaluator error: {e}")
            continue
        ok = bool(res.get("ok", False))
        if not ok:
            failed = res.get("failed_blocking") or res.get("failed_constraints") or []
            if isinstance(failed, list) and failed:
                tags.append(f"Fragile to {key} (+{frac*100:.0f}%) → first kill: {failed[0]}")
            else:
                tags.append(f"Fragile to {key} (+{frac*100:.0f}%) → infeasible")
    if not tags:
        tags.append("No immediate fragility detected under small perturbations (screening-level).")
    return {"tags": tags, "notes": notes}
