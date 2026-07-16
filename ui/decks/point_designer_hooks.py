"""Point Designer deck hooks (UI Phase B)."""
from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

from ui.verdict_ui import render_verdict_hero_strip
from ui.constraint_trace import render_infeasibility_trace
from ui.export_bundle import build_export_bundle, bundle_json_bytes
from ui.session_api import get_point_outputs, get_point_artifact
from ui.constraint_pipeline_diff import render_constraint_pipeline_diff
from ui.no_solution_atlas_ui import render_no_solution_atlas_panel
from ui.authority_dashboard import render_profile_tau_peaking_panel


def render_point_designer_hero(session_state: Any) -> None:
    out = get_point_outputs(session_state)
    art = get_point_artifact(session_state) or {}
    rs = art.get("run_summary") if isinstance(art, dict) else None
    render_verdict_hero_strip(out or {}, run_summary=rs, key_prefix="pd_hero")


def render_point_designer_trace(session_state: Any) -> None:
    out = get_point_outputs(session_state)
    if out:
        render_infeasibility_trace(out)
        render_profile_tau_peaking_panel(out)


def render_point_designer_constraint_diff(session_state: Any) -> None:
    out = get_point_outputs(session_state)
    intent = str(session_state.get("design_intent", ""))
    if out:
        render_constraint_pipeline_diff(out, design_intent=intent, key_prefix="pd_cpdiff")


def render_point_designer_no_solution_atlas(session_state: Any) -> None:
    out = get_point_outputs(session_state)
    intent = str(session_state.get("design_intent", ""))
    if out:
        render_no_solution_atlas_panel(out, design_intent=intent, key_prefix="pd_nsatlas")


def render_point_designer_export(session_state: Any, *, deck: str = "Point Designer") -> None:
    out = get_point_outputs(session_state)
    art = get_point_artifact(session_state) or {}
    if not out:
        st.caption("Evaluate a point before exporting.")
        return
    intent = str(session_state.get("design_intent", "") or "")
    prebuilt = art.get("no_solution_atlas") if isinstance(art, dict) else None
    bundle = build_export_bundle(
        deck=deck,
        outputs=out,
        inputs=art.get("inputs") if isinstance(art, dict) else None,
        design_intent=intent or None,
        no_solution_atlas=prebuilt if isinstance(prebuilt, dict) else None,
    )
    st.download_button(
        "Download evaluation bundle (JSON + SHA-256)",
        data=bundle_json_bytes(bundle),
        file_name="shams_point_export.json",
        mime="application/json",
        key="pd_export_bundle",
    )
