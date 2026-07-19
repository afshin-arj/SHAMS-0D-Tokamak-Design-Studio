"""Streamlit Opt Lab entry — cheap parity with NiceGUI Phase 1.1–1.4.

Shows the same three-step certified-search contract, honesty copy, and
champion warm-start catalogue. Full interactive seed load lives on NiceGUI.
"""
from __future__ import annotations

from typing import Any


def render_opt_lab(st_module: Any) -> None:
    """Render Opt Lab entry on Streamlit (contract + warm-start catalogue)."""
    st = st_module
    from ui_nicegui.lib.opt_lab_entry import (
        OPT_LAB_HONESTY_LINE,
        OPT_LAB_NSGA2_HOOK_NOTE,
        OPT_LAB_PITCH,
        OPT_LAB_ROUTES,
        OPT_LAB_SLSQP_HOOK_NOTE,
        OPT_LAB_STANCE_DOC,
        OPT_LAB_STEPS,
        OPT_LAB_TAGLINE,
        OPT_LAB_TITLE,
    )
    from ui_nicegui.lib.opt_lab_warm_start import (
        WARM_START_HONESTY,
        WARM_START_TAGLINE,
        WARM_START_TITLE,
    )
    from ui_nicegui.lib.studio_entry import champion_template_options

    st.header(OPT_LAB_TITLE)
    st.caption(OPT_LAB_TAGLINE)
    st.info(OPT_LAB_PITCH)
    st.warning(OPT_LAB_HONESTY_LINE)
    st.caption(
        "Run stamps (opt_run_stamp.v1) attach on CCFS verify — "
        "VERSION + ObjectiveContract hash + VERIFIED/REJECTED counts."
    )

    st.subheader(WARM_START_TITLE)
    st.caption(WARM_START_TAGLINE)
    st.warning(WARM_START_HONESTY)
    st.markdown(
        "Champion catalogue (propose-only search seeds). "
        "Interactive **Load as search seed** is on NiceGUI Opt Lab / Systems Mode / Pareto Lab:"
    )
    for opt in champion_template_options():
        feas = opt.get("expect_hard_feasible")
        tag = "feasible expected" if feas is True else ("NO-SOLUTION story" if feas is False else "")
        st.markdown(
            f"- **{opt['label']}** (`{opt['case_id']}`)"
            + (f" — {tag}" if tag else "")
        )

    st.subheader("Three steps to a certified search")
    for idx, step in enumerate(OPT_LAB_STEPS, start=1):
        st.markdown(f"{idx}. {step}")

    st.caption(OPT_LAB_SLSQP_HOOK_NOTE)
    st.caption(OPT_LAB_NSGA2_HOOK_NOTE)

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
        "Full Opt Lab navigation and champion warm-start load are on NiceGUI. "
        "Streamlit keeps this honesty contract visible without duplicating decks."
    )
