"""Candidate ranking for Systems Mode audit exports."""

from __future__ import annotations

from typing import Any, List


def _margin_score(c: dict) -> float:
    h = c.get("headline") or {}
    v = h.get("margin") or c.get("margin")
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("-inf")


def _perf_score(c: dict) -> float:
    h = c.get("headline") or {}
    q = h.get("Q")
    pnet = h.get("P_net")
    try:
        qf = float(q) if q is not None else 0.0
    except (TypeError, ValueError):
        qf = 0.0
    try:
        pn = float(pnet) if pnet is not None else 0.0
    except (TypeError, ValueError):
        pn = 0.0
    return qf + 0.01 * pn


def rank_candidates(cands: List[dict], profile: str = "Balanced") -> List[dict]:
    prof = str(profile or "Balanced").strip().lower()

    def key(c: dict):
        feas = 1 if c.get("feasible") else 0
        if prof == "performance":
            return (feas, _perf_score(c))
        if prof == "margin":
            return (feas, _margin_score(c))
        return (feas, _perf_score(c), _margin_score(c))

    return sorted(list(cands), key=key, reverse=True)
