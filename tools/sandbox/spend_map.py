"""Reactor Design Forge — Constraint Spend Map (v1)

The Spend Map is a descriptive instrument: it visualizes how a candidate is
"buying" feasibility by spending margin on different constraints.

This module converts an archive (audited candidates) into 2D scatter inputs
for UI plotting. It intentionally does not set plot styles or colors.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional


def _get_margin(candidate: Dict[str, Any], constraint_key: str) -> Optional[float]:
    """Best-effort fetch of a specific constraint margin."""
    mb = candidate.get("margin_budget") or {}
    if isinstance(mb, dict):
        # v203 margin_budget structure: {"rows": [...]} or a flat mapping
        if isinstance(mb.get("rows"), list):
            for r in mb["rows"]:
                if str(r.get("constraint")) == str(constraint_key):
                    v = r.get("headroom")
                    try:
                        return float(v) if v is not None else None
                    except Exception:
                        return None
        if constraint_key in mb:
            try:
                return float(mb[constraint_key])
            except Exception:
                return None
    # fallback: records list
    recs = candidate.get("records") or []
    for r in recs:
        if str(r.get("name")) == str(constraint_key) or str(r.get("key")) == str(constraint_key):
            v = r.get("margin") or r.get("signed_margin")
            try:
                return float(v) if v is not None else None
            except Exception:
                return None
    return None


def build_spend_scatter(
    archive: List[Dict[str, Any]],
    x_key: str,
    y_key: str,
    color_by: str = "min_margin",
    constraint_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a minimal scatter payload for UI.

    Parameters
    ----------
    archive:
        List of candidate dicts.
    x_key, y_key:
        Keys in candidate['inputs'] to use as axes (e.g., 'Ip_MA').
    color_by:
        'min_margin' | 'feasibility_state' | 'constraint_margin'
    constraint_key:
        Only used when color_by='constraint_margin'.
    """

    xs, ys, cs, ids = [], [], [], []
    for c in archive or []:
        inp = c.get("inputs") or {}
        if x_key not in inp or y_key not in inp:
            continue
        try:
            x = float(inp[x_key])
            y = float(inp[y_key])
        except Exception:
            continue

        if color_by == "feasibility_state":
            col = c.get("feasibility_state") or ""
        elif color_by == "constraint_margin" and constraint_key:
            col = _get_margin(c, constraint_key)
        else:
            mm = c.get("min_signed_margin")
            try:
                col = float(mm) if mm is not None else None
            except Exception:
                col = None

        xs.append(x)
        ys.append(y)
        cs.append(col)
        ids.append(str(c.get("id") or c.get("candidate_id") or ""))

    return {
        "x": xs,
        "y": ys,
        "c": cs,
        "ids": ids,
        "meta": {
            "x_key": x_key,
            "y_key": y_key,
            "color_by": color_by,
            "constraint_key": constraint_key,
        },
    }
