from __future__ import annotations

"""Citation governance helpers (SHAMS authority discipline).

This module enforces a simple rule:

- If a clause/field is asserted as anything other than "unknown", it must include
  at least one citation record.

Citations are treated as *metadata*, never as physics. Missing citations are
reported as diagnostics and can be policy-gated by the caller.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Citation:
    """A minimal citation record."""

    kind: str  # doi/report/url/other
    ref: str
    note: str = ""


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def citations_present(citations: Any) -> bool:
    """Return True if at least one citation with a non-empty ref exists."""
    for c in _as_list(citations):
        if isinstance(c, dict):
            if str(c.get("ref", "")).strip():
                return True
        elif isinstance(c, Citation):
            if str(c.ref).strip():
                return True
        else:
            if str(c).strip():
                return True
    return False


def validate_clause_citations(
    clauses: Dict[str, Any],
    *,
    state_key: str = "state",
    citations_key: str = "citations",
    unknown_state: str = "unknown",
    path_prefix: str = "",
) -> List[str]:
    """Validate that asserted clauses have citations.

    Expected clause shape (flexible):
      clauses[name] = {"state": "hard|diagnostic|ignored|unknown", "citations": [...]}

    Returns list of human-readable issues.
    """
    issues: List[str] = []
    for name, rec in (clauses or {}).items():
        if not isinstance(rec, dict):
            continue
        state = str(rec.get(state_key, unknown_state)).strip().lower()
        if state == unknown_state:
            continue
        cits = rec.get(citations_key, [])
        if not citations_present(cits):
            p = f"{path_prefix}{name}" if path_prefix else str(name)
            issues.append(f"Missing citation for asserted clause: {p} (state={state})")
    return issues


def validate_authority_overrides(authority_overrides: Dict[str, Any]) -> List[str]:
    """Validate citation coverage for authority overrides.

    Expected minimal shape:
      {"neutronics": {"tier": "external", "source": "...", "sha256": "...", "citations": [...]}, ...}
    """
    issues: List[str] = []
    for k, v in (authority_overrides or {}).items():
        if not isinstance(v, dict):
            continue
        tier = str(v.get("tier", "unknown")).strip().lower()
        if tier == "unknown":
            continue
        if not citations_present(v.get("citations", [])):
            issues.append(f"Missing citation for authority override: {k} (tier={tier})")
    return issues


def summarize_citation_completeness(issues: List[str]) -> Dict[str, Any]:
    """Return a compact completeness summary."""
    return {
        "schema": "citation_completeness.v1",
        "ok": len(issues) == 0,
        "n_issues": int(len(issues)),
        "issues": list(issues),
    }
