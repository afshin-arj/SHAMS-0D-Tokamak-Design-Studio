"""Point Designer handoff session normalization."""
from __future__ import annotations

from ui_nicegui.session import DesignSession


def prepare_point_designer_handoff(session: DesignSession) -> None:
    """Ensure promoted inputs are visible on Truth Console → Configure."""
    session.pd_subdeck = "Truth Console"
    session.pd_workflow_tab = "1 · Configure"


def invalidate_point_designer_after_seed(session: DesignSession) -> None:
    """Clear PD KPI caches after an external seed mutates inputs (no auto-eval).

    Prevents STALE-with-wrong-machine heroes when Compare / Pareto / Trade /
    Scan / Atlas / recovery promote a different design into ``session.inputs``.
    Paths that immediately re-evaluate (e.g. Systems Apply) should not call this.
    """
    from ui_nicegui.lib.session_store import clear_point_designer

    clear_point_designer(session)


def navigate_to_point_designer(session: DesignSession) -> None:
    """Promote path: show Truth Console and remount Point Designer."""
    prepare_point_designer_handoff(session)
    from ui_nicegui.lib.navigation import switch_deck

    switch_deck("Point Designer", force=True)
