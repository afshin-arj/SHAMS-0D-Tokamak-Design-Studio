from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Tuple

# Single maturity rubric for proxies and decisions.
# TRL: 1 (concept) .. 9 (commercial)
# Envelope: conservative/baseline/aggressive

VALID_ENVELOPES = ("conservative", "baseline", "aggressive")

@dataclass(frozen=True)
class MaturityRubric:
    trl_low_maturity_threshold: int = 4  # <4 considered low maturity for decision risk
    decision_grade_envelope: str = "conservative"

RUBRIC = MaturityRubric()

def is_low_maturity(maturity: Dict[str, Any] | None) -> bool:
    if not maturity:
        return False
    try:
        trl = int(maturity.get("trl", 9))
        return trl < RUBRIC.trl_low_maturity_threshold
    except Exception:
        return False

def decision_grade_check(feasible: bool, envelope: str | None) -> Tuple[bool, str]:
    env = (envelope or "").strip().lower() or "baseline"
    if env not in VALID_ENVELOPES:
        env = "baseline"
    if env != RUBRIC.decision_grade_envelope:
        return False, f"Decision-grade requires '{RUBRIC.decision_grade_envelope}' envelope (current={env})."
    if not feasible:
        return False, "Not feasible under decision-grade envelope."
    return True, "Passes decision-grade envelope check."
