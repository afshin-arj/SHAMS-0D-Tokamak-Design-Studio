"""Control Room governance verdict row."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.control_room_helpers import governance_summary
from ui_nicegui.session import DesignSession


def render_governance_verdict(summary: dict) -> None:
    ui.label("Governance posture").classes("text-subtitle1")
    fh = summary.get("feasible_hard")
    fh_label = "-" if fh is None else ("YES" if fh else "NO")
    kpi_row([
        ("Verdict", summary.get("point_verdict", "-")),
        ("Dominant", summary.get("dominant", "-")),
        ("Q / nτE", summary.get("q_label", "-")),
        ("Design class", summary.get("design_class", "-")),
        ("Hard feasible", fh_label),
        ("Version", summary.get("version", "-")),
    ])


@ui.refreshable
def render_governance_verdict_live(session: DesignSession) -> None:
    """Re-read PD artifact for header KPIs after explicit re-eval (Assumptions panel)."""
    render_governance_verdict(governance_summary(session))
