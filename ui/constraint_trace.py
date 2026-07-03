"""Infeasibility trace: constraint → output key → authority (UI Phase D)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from constraints.unified import build_all_constraints
    from constraints.constraints import constraint_is_hard
except ImportError:
    from src.constraints.unified import build_all_constraints
    from src.constraints.constraints import constraint_is_hard

_AUTHORITY_DOC = {
    "v396": "docs/patch_notes/PATCH_NOTES_v396.md",
    "v397": "docs/patch_notes/PATCH_NOTES_v397.md",
    "v398": "docs/patch_notes/PATCH_NOTES_v398.md",
    "v399": "docs/patch_notes/PATCH_NOTES_v399.md",
    "v400": "docs/patch_notes/PATCH_NOTES_v400.md",
    "v403": "docs/patch_notes/PATCH_NOTES_v403.md",
    "v407": "docs/patch_notes/PATCH_NOTES_v407.md",
}


def _guess_doc(name: str) -> str:
    low = str(name).lower()
    for tag, path in _AUTHORITY_DOC.items():
        if tag in low:
            return path
    return "GOVERNANCE.md"


def build_infeasibility_trace(out: Dict[str, Any]) -> List[Dict[str, Any]]:
    bundle = build_all_constraints(out)
    trace: List[Dict[str, Any]] = []
    for c in bundle.governance:
        if not constraint_is_hard(c):
            continue
        if bool(getattr(c, "passed", True)):
            continue
        key = str(getattr(c, "key", getattr(c, "name", "")))
        trace.append(
            {
                "constraint": str(c.name),
                "output_key": key,
                "value": float(getattr(c, "value", float("nan"))),
                "limit": float(getattr(c, "limit", float("nan"))),
                "sense": str(getattr(c, "sense", "")),
                "group": str(getattr(c, "group", "")),
                "authority_doc": _guess_doc(str(c.name)),
                "note": str(getattr(c, "note", "") or ""),
            }
        )
    trace.sort(key=lambda r: str(r["constraint"]))
    return trace


def render_infeasibility_trace(out: Dict[str, Any]) -> None:
    import streamlit as st

    trace = build_infeasibility_trace(out)
    if not trace:
        st.caption("No hard constraint violations in current evaluation.")
        return
    with st.expander("Why infeasible? (constraint trace)", expanded=True):
        for row in trace:
            st.markdown(
                f"**{row['constraint']}** — `{row['output_key']}` = {row['value']:.4g} "
                f"({row['sense']} {row['limit']:.4g}) · doc: `{row['authority_doc']}`"
            )
            if row.get("note"):
                st.caption(row["note"])
