from __future__ import annotations

"""PROCESS ↔ SHAMS intent mapping (v364.0).

SHAMS is not a PROCESS clone; this module provides a transparent, auditable
*interpretation* layer for parity studies.

The mapping is intentionally conservative:
- Only maps parameters with clear semantic correspondence
- Emits an explicit assumption registry for every mapping decision
- Never modifies truth; it only creates comparable input dictionaries

© 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class MappingAssumption:
    key: str
    description: str
    severity: str  # "info" | "warn" | "critical"

    def to_dict(self) -> Dict[str, str]:
        return {"key": self.key, "description": self.description, "severity": self.severity}


@dataclass(frozen=True)
class ProcessMapResult:
    schema: str
    process_like_inputs: Dict[str, Any]
    shams_inputs: Dict[str, Any]
    assumptions: List[MappingAssumption]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "process_like_inputs": self.process_like_inputs,
            "shams_inputs": self.shams_inputs,
            "assumptions": [a.to_dict() for a in self.assumptions],
        }


def map_process_to_shams(process_like: Dict[str, Any]) -> ProcessMapResult:
    """Map a minimal PROCESS-style dict into SHAMS PointInputs kwargs.

    Expected PROCESS-like keys (optional):
        - R0, a, kappa, delta
        - Bt0, Ip
        - q95 (or q_95)
        - ne_bar (line-avg electron density)
        - Te0, Ti0 (core temps)

    Anything not mapped is left to SHAMS defaults.
    """

    p = dict(process_like)
    a: List[MappingAssumption] = []
    s: Dict[str, Any] = {}

    def _pick(*keys: str) -> Optional[Any]:
        for k in keys:
            if k in p:
                return p.get(k)
        return None

    for k in ["R0", "a", "kappa", "delta", "Bt0", "Ip", "ne_bar", "Te0", "Ti0"]:
        v = _pick(k)
        if v is not None:
            s[k] = v

    q = _pick("q95", "q_95", "q_95_edge")
    if q is not None:
        s["q95"] = q
    elif any(k in p for k in ["qstar", "q_star"]):
        a.append(
            MappingAssumption(
                key="q", 
                description="PROCESS q* provided; mapped to SHAMS q95 is undefined. Provide q95 explicitly for parity.",
                severity="warn",
            )
        )

    a.append(
        MappingAssumption(
            key="defaults",
            description="Unspecified PROCESS-like inputs rely on SHAMS deterministic defaults; parity requires declaring these explicitly.",
            severity="info",
        )
    )

    return ProcessMapResult(
        schema="shams_process_map.v1",
        process_like_inputs=p,
        shams_inputs=s,
        assumptions=a,
    )


def map_shams_to_process_like(shams_inputs: Dict[str, Any]) -> ProcessMapResult:
    """Create a minimal PROCESS-like view from SHAMS inputs.

    This is not a full PROCESS input deck. It exists to support parity discussion and
    to build reviewer-facing traceability artifacts.
    """

    s = dict(shams_inputs)
    p: Dict[str, Any] = {}
    a: List[MappingAssumption] = []

    for k in ["R0", "a", "kappa", "delta", "Bt0", "Ip", "q95", "ne_bar", "Te0", "Ti0"]:
        if k in s:
            p[k] = s.get(k)

    a.append(
        MappingAssumption(
            key="non_equivalence",
            description="PROCESS input decks contain many engineering/physics knobs not represented in this minimal view.",
            severity="info",
        )
    )

    return ProcessMapResult(
        schema="shams_process_map.v1",
        process_like_inputs=p,
        shams_inputs=s,
        assumptions=a,
    )
