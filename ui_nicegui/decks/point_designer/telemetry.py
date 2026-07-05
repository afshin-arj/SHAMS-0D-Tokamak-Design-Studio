"""Telemetry tab — full Streamlit parity views (Phase 19/21)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.decks.point_designer.chronicle_export import render_chronicle_export
from ui_nicegui.decks.point_designer.control_contracts import render_control_contracts
from ui_nicegui.decks.point_designer.dominance_closure import render_dominance_closure
from ui_nicegui.decks.point_designer.ledgers import render_ledgers
from ui_nicegui.decks.point_designer.mission_snapshot import render_mission_snapshot
from ui_nicegui.decks.point_designer.plot_deck import render_plot_deck
from ui_nicegui.decks.point_designer.sensitivity_lab import render_sensitivity_lab
from ui_nicegui.lib.pd_panel_labels import TELEMETRY_VIEWS, normalize_telemetry_view
from ui_nicegui.lib.pd_parity_helpers import tau_peaking_panel_data
from ui_nicegui.session import DesignSession


def render_tau_peaking_panel(out: dict) -> None:
    """Optional v397 τE peaking hook (mirrors ui/authority_dashboard.render_profile_tau_peaking_panel)."""
    data = tau_peaking_panel_data(out)
    if not data:
        return
    if not data.get("enabled", True):
        ui.label(str(data.get("message", ""))).classes("text-caption")
        return
    with ui.expansion("Energy confinement time profile peaking", icon="timeline").classes("w-full q-mb-sm"):
        ui.label(f"τE profile peaking factor: {data.get('factor_label', 'n/a')}").classes("text-body1")
        cap = data.get("tauE_s_caption")
        if cap:
            ui.label(str(cap)).classes("text-caption")


def render_telemetry(session: DesignSession) -> None:
    out = session.pd_last_outputs or session.last_eval
    if not out:
        empty_state(
            "No Point Designer results yet. Open **Configure** and click **Evaluate Point**.",
            kind="info",
        )
        return

    session.pd_telemetry_view = normalize_telemetry_view(session.pd_telemetry_view)
    if session.pd_telemetry_view not in TELEMETRY_VIEWS:
        session.pd_telemetry_view = TELEMETRY_VIEWS[0]

    ui.toggle(
        TELEMETRY_VIEWS,
        value=session.pd_telemetry_view,
        on_change=lambda e: (
            setattr(session, "pd_telemetry_view", str(e.value)),
            _body.refresh(),
        ),
    ).classes("q-mb-md")

    _body(session)


@ui.refreshable
def _body(session: DesignSession) -> None:
    view = session.pd_telemetry_view
    out = session.pd_last_outputs or session.last_eval or {}
    if view == "Verdict & KPIs":
        render_tau_peaking_panel(out if isinstance(out, dict) else {})
        render_mission_snapshot(session)
    elif view == "Power balance plots":
        render_plot_deck(session)
    elif view == "Authority dominance & closures":
        render_dominance_closure(session)
    elif view == "Control system contracts":
        render_control_contracts(session)
    elif view == "Plant & materials ledgers":
        render_ledgers(session)
    elif view == "Parameter sensitivity":
        render_sensitivity_lab(session)
    elif view == "Run history & export":
        render_chronicle_export(session)
