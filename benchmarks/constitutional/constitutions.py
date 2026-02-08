from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple

# Constitutional semantics used in SHAMS benchmarks.
# These are NOT physics. They are enforcement semantics / requirements.

# Allowed clause values:
#   - "required": feasibility-gating requirement
#   - "hard": hard constraint
#   - "diagnostic": evaluated but non-blocking
#   - "ignored": not evaluated / not enforced

RESEARCH_INTENT_CONSTITUTION: Dict[str, str] = {
    # Plasma limits remain hard in research by default
    "q95": "hard",
    "greenwald": "hard",
    "beta_n": "diagnostic",
    # Reactor closures are not required for research devices
    "net_electric": "ignored",
    "tritium_self_sufficiency": "ignored",
    "detachment": "diagnostic",
    "lifetime_margin": "diagnostic",
    "availability": "ignored",
}

REACTOR_INTENT_CONSTITUTION: Dict[str, str] = {
    # Plasma limits remain hard
    "q95": "hard",
    "greenwald": "hard",
    "beta_n": "hard",
    # Reactor closures required
    "net_electric": "required",
    "tritium_self_sufficiency": "required",
    "detachment": "required",
    "lifetime_margin": "required",
    "availability": "required",
}

def intent_to_constitution(intent: str) -> Dict[str, str]:
    key = intent.strip().lower()
    if key.startswith("research") or key.startswith("experimental"):
        return dict(RESEARCH_INTENT_CONSTITUTION)
    if key.startswith("reactor") or key.startswith("power"):
        return dict(REACTOR_INTENT_CONSTITUTION)
    # Default conservative: reactor
    return dict(REACTOR_INTENT_CONSTITUTION)

def constitution_diff(baseline: Dict[str, str], other: Dict[str, str]) -> List[Dict[str, str]]:
    diff: List[Dict[str, str]] = []
    keys = sorted(set(baseline.keys()) | set(other.keys()))
    for k in keys:
        a = baseline.get(k, "unset")
        b = other.get(k, "unset")
        if a != b:
            diff.append({"key": k, "from": a, "to": b})
    return diff

def pretty_clause(k: str) -> str:
    m = {
        "q95": "q95 enforcement",
        "greenwald": "Greenwald enforcement",
        "beta_n": "βN (Troyon) enforcement",
        "net_electric": "Net electric requirement",
        "tritium_self_sufficiency": "Tritium self-sufficiency",
        "detachment": "Detachment requirement",
        "lifetime_margin": "Lifetime margin requirement",
        "availability": "Availability requirement",
    }
    return m.get(k, k)
