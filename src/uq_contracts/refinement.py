"""Interval narrowing / contract refinement suggestions (v296.0).

Given an uncertainty contract (intervals) and corner-evaluated outcomes, identify
which inputs dominate fragility and suggest tightened bounds required to reach
ROBUST classification.

This module is deterministic and explanatory-only.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any


@dataclass(frozen=True)
class RefinementSuggestion:
    var: str
    current_interval: Tuple[float, float]
    suggested_interval: Tuple[float, float]
    rationale: str


def suggest_interval_refinements(
    intervals: Dict[str, Tuple[float, float]],
    corner_results: List[Dict[str, Any]],
    max_suggestions: int = 6,
) -> List[RefinementSuggestion]:
    """Suggest tightened intervals based on failure frequency by corner.

    Args:
        intervals: mapping var->(lo,hi)
        corner_results: list of dicts containing at least:
            - 'corner' : dict var->value
            - 'verdict' : 'PASS'/'FAIL'
            - optional 'dominant_mechanism'

    Returns:
        Deterministic list of suggestions.
    """

    # Count failures per variable boundary usage
    fail = [cr for cr in corner_results if str(cr.get('verdict','')).upper() != 'PASS']
    if not fail:
        return []

    stats: Dict[str, Dict[str, int]] = {v: {'lo':0,'hi':0,'n':0} for v in intervals}

    for cr in fail:
        corner = cr.get('corner', {}) or {}
        for v,(lo,hi) in intervals.items():
            x = corner.get(v)
            if x is None:
                continue
            stats[v]['n'] += 1
            # boundary hit heuristic
            if abs(float(x) - float(lo)) <= 1e-12:
                stats[v]['lo'] += 1
            if abs(float(x) - float(hi)) <= 1e-12:
                stats[v]['hi'] += 1

    # score vars by boundary-hit frequency
    scored: List[Tuple[str, float]] = []
    for v,s in stats.items():
        n = max(1, s['n'])
        score = max(s['lo'], s['hi']) / n
        scored.append((v, score))

    scored.sort(key=lambda x: (x[1], x[0]), reverse=True)

    out: List[RefinementSuggestion] = []
    for v,score in scored[:max_suggestions]:
        lo,hi = intervals[v]
        span = float(hi) - float(lo)
        if span <= 0:
            continue
        tighten = 0.20  # 20% tightening heuristic
        new_lo = float(lo) + tighten*span
        new_hi = float(hi) - tighten*span
        out.append(
            RefinementSuggestion(
                var=v,
                current_interval=(float(lo), float(hi)),
                suggested_interval=(new_lo, new_hi),
                rationale=f"Failures concentrate at '{v}' interval boundary (score={score:.2f}); suggest tightening by {int(tighten*100)}%.",
            )
        )

    return out
