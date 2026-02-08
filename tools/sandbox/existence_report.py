from __future__ import annotations

"""Optimization Sandbox — Machine Existence Report.

This is the complement to a Resistance Report.

Given one *evaluated* candidate (inputs + outputs + constraint records), produce a
readable explanation of why the point is feasible (or how close it is), without
recommending changes.

Discipline:
- Descriptive only.
- Uses signed margins already computed by frozen evaluator.
"""

from typing import Any, Dict, List, Optional


def _safe_float(x: Any) -> Optional[float]:
    try:
        v = float(x)
        return v
    except Exception:
        return None


def existence_report(
    candidate: Dict[str, Any],
    *,
    tight_abs_margin: float = 0.10,
    slack_abs_margin: float = 0.50,
    top_n: int = 8,
) -> Dict[str, Any]:
    """Build an existence report for a candidate."""

    cons = (candidate or {}).get("constraints") or []
    tight: List[Dict[str, Any]] = []
    slack: List[Dict[str, Any]] = []
    unknown: List[str] = []

    for c in cons:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name") or c.get("id") or "")
        sm = _safe_float(c.get("signed_margin"))
        if sm is None:
            unknown.append(name)
            continue
        row = {
            "name": name,
            "signed_margin": float(sm),
            "status": str(c.get("status") or ""),
        }
        if abs(sm) <= float(tight_abs_margin):
            tight.append(row)
        elif abs(sm) >= float(slack_abs_margin) and sm > 0:
            slack.append(row)

    tight.sort(key=lambda r: abs(float(r.get("signed_margin", 0.0))))
    slack.sort(key=lambda r: abs(float(r.get("signed_margin", 0.0))), reverse=True)

    feas = bool((candidate or {}).get("feasible", False))
    narrative = []
    if feas:
        narrative.append("This candidate is feasible under the frozen evaluator.")
        if tight:
            narrative.append("It exists near the boundary of these constraints (tight margins):")
        else:
            narrative.append("No constraints are particularly tight within the selected thresholds.")
    else:
        fm = (candidate or {}).get("failure_mode")
        narrative.append(f"This candidate is not feasible (failure_mode={fm}).")
        if tight:
            narrative.append("Closest-to-feasible constraints (near-boundary):")

    return {
        "schema": "shams.opt_sandbox.existence_report.v1",
        "feasible": feas,
        "failure_mode": (candidate or {}).get("failure_mode"),
        "tight": tight[: int(top_n)],
        "slack": slack[: int(top_n)],
        "unknown": unknown[: int(top_n)],
        "thresholds": {
            "tight_abs_margin": float(tight_abs_margin),
            "slack_abs_margin": float(slack_abs_margin),
        },
        "narrative": " ".join(narrative),
    }
