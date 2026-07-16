"""Point Designer handoff session normalization."""
from __future__ import annotations

from ui_nicegui.session import DesignSession


def prepare_point_designer_handoff(session: DesignSession) -> None:
    """Ensure promoted inputs are visible on Truth Console → Configure."""
    session.pd_subdeck = "Truth Console"
    session.pd_workflow_tab = "1 · Configure"
