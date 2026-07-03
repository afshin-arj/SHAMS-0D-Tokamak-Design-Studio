"""System Suite deck hooks (UI Phase B)."""
from __future__ import annotations

from typing import Any

from ui.verdict_ui import render_feasibility_strip, render_overlay_failure_panel
from ui.session_api import get_point_outputs


def render_system_suite_header(session_state: Any) -> None:
    out = get_point_outputs(session_state)
    if not out:
        return
    render_feasibility_strip(out, key_prefix="suite_feas")
    render_overlay_failure_panel(out, key_prefix="suite_ovl")
