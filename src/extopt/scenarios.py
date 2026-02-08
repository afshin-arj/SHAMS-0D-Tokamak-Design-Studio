from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple
import json, hashlib

@dataclass(frozen=True)
class Scenario:
    name: str
    overrides: Dict[str, Any]

def default_corner_scenarios() -> List[Scenario]:
    """Deterministic UQ-lite corner set. Conservative small set by design."""
    return [
        Scenario("BASE", {}),
        Scenario("LOW_H", {"H98y2": 0.9}),
        Scenario("HIGH_H", {"H98y2": 1.1}),
        Scenario("HIGH_ZEFF", {"Zeff": 2.2}),
        Scenario("LOW_ZEFF", {"Zeff": 1.6}),
    ]

def scenarios_hash(scenarios: List[Scenario]) -> str:
    payload = [{"name": s.name, "overrides": s.overrides} for s in scenarios]
    blob = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
