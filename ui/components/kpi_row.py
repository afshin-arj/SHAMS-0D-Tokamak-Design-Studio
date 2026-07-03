"""kpi_row -- compact horizontal KPI metric strip (UI redesign component).

Pure presentation: renders N equal-width columns with one st.metric per item.
No physics, no state mutation, no keys (caller owns any widget keys if needed).

Usage:
    kpi_row([("Gross electric (MW)", f"{pe:.2f}"), ("Recirc (MW)", f"{pr:.2f}")])
    kpi_row([("Label", value, "optional help")])
"""
from __future__ import annotations
from typing import Sequence
import streamlit as st


def kpi_row(items: Sequence[Sequence[object] | None]) -> None:
    """Render a row of metric KPIs.

    ``items`` is a sequence of tuples ``(label, value)`` or ``(label, value, help)``.
    ``None`` entries are skipped. If all entries are skipped, nothing is rendered.
    """
    cells = [it for it in items if it is not None]
    if not cells:
        return
    cols = st.columns(len(cells))
    for col, it in zip(cols, cells):
        label = it[0]
        value = it[1] if len(it) > 1 else ""
        help_text = it[2] if len(it) > 2 else None
        col.metric(str(label), value, help=help_text)
