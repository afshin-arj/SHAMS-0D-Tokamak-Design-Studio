"""Streamlit Opt Lab entry — cheap parity with NiceGUI Phase 1.1.

Shows the same three-step certified-search contract and honesty copy.
Full interactive routes live on NiceGUI; Streamlit does not duplicate those decks.
"""
from __future__ import annotations

from typing import Any


def render_opt_lab(st_module: Any) -> None:
    """Render Opt Lab entry on Streamlit (contract + pointer to NiceGUI)."""
    st = st_module
    from ui_nicegui.lib.opt_lab_entry import (
        OPT_LAB_HONESTY_LINE,
        OPT_LAB_PITCH,
        OPT_LAB_ROUTES,
        OPT_LAB_STANCE_DOC,
        OPT_LAB_STEPS,
        OPT_LAB_TAGLINE,
        OPT_LAB_TITLE,
    )

    st.header(OPT_LAB_TITLE)
    st.caption(OPT_LAB_TAGLINE)
    st.info(OPT_LAB_PITCH)
    st.warning(OPT_LAB_HONESTY_LINE)

    st.subheader("Three steps to a certified search")
    for idx, step in enumerate(OPT_LAB_STEPS, start=1):
        st.markdown(f"{idx}. {step}")

    st.subheader("Certified paths (NiceGUI)")
    st.markdown(
        "Opt Lab unifies entry — open **NiceGUI** (`run_ui_nicegui.cmd`) for interactive "
        "routes into existing surfaces:"
    )
    for label, deck, _hook in OPT_LAB_ROUTES:
        st.markdown(f"- **{label}** → deck `{deck}`")

    st.markdown(
        f"Stance: `{OPT_LAB_STANCE_DOC[1]}` — propose→CCFS; "
        "**Proposed — SHAMS-certified**, not an authoritative optimum."
    )
    st.info(
        "Full Opt Lab navigation is on NiceGUI. Streamlit keeps this honesty contract "
        "visible without duplicating Systems Mode / Pareto Lab."
    )
