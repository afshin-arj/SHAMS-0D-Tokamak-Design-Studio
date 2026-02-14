"""SHAMS Reactor Design Forge — Margin Budget

Produces an explicit constraint margin ledger for a candidate.

This is NOT a scalar score and NOT a recommendation. It is an engineering
accounting view: which constraints are tight, which are slack, and how close
we are to the boundary.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def margin_budget(constraint_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a margin budget table from constraint records.

    Expects records shaped like tools.process_compat.constraints_to_records
    outputs: contains keys like 'name', 'signed_margin', 'value', 'limit',
    'status', etc.

    Returns a dict suitable for archiving and reporting.
    """
    rows = []
    min_sm: Optional[float] = None
    for r in (constraint_records or []):
        name = str(r.get("name") or "")
        if not name:
            continue
        sm = r.get("signed_margin")
        try:
            smf = float(sm)
        except Exception:
            smf = None
        if smf is not None:
            if min_sm is None or smf < min_sm:
                min_sm = smf
        rows.append({
            "name": name,
            "signed_margin": smf,
            "status": r.get("status"),
            "value": r.get("value"),
            "limit": r.get("limit"),
            "units": r.get("units"),
        })

    # Sort tightest first (lowest signed margin)
    rows_sorted = sorted(rows, key=lambda x: (float("inf") if x.get("signed_margin") is None else x.get("signed_margin")))
    tight = [x for x in rows_sorted if (x.get("signed_margin") is not None and x.get("signed_margin") <= 0.05)]

    return {
        "schema": "shams.forge.margin_budget.v1",
        "n_constraints": int(len(rows_sorted)),
        "min_signed_margin": float(min_sm) if min_sm is not None else None,
        "tight_constraints": tight[:10],
        "table": rows_sorted,
        "notes": "Descriptive engineering ledger. Not a score, not a recommendation.",
    }
