"""2D slice diagnostics — off-plane projection stability and mitigation."""

from __future__ import annotations

from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.lib.scan_helpers import SCAN_VAR_KEYS, SCAN_VAR_LABELS
from ui_nicegui.lib.scan_insight_display import format_projection_stability
from ui_nicegui.lib.scan_insights_helpers import projection_stability
from ui_nicegui.session import DesignSession


def render_slice_diagnostics(
    session: DesignSession,
    rep: dict,
    *,
    on_update: Optional[Callable[[], None]] = None,
) -> None:
    ui.label("2D slice diagnostics").classes("text-subtitle1")
    ui.label(
        "Cartography is a plane slice. Perturb a third axis at the probed cell to see if dominance "
        "is stable off-plane — low stability means the 2D map may mislead."
    ).classes("text-caption q-mb-sm")

    x_key = str(rep.get("x_key") or "")
    y_key = str(rep.get("y_key") or "")
    z_opts = [k for k in SCAN_VAR_KEYS if k not in (x_key, y_key)]
    if not z_opts:
        ui.label("No third axis available for off-plane check.").classes("text-caption text-grey")
        return

    if getattr(session, "scan_slice_z_key", "") not in z_opts:
        session.scan_slice_z_key = z_opts[0]

    intents = list(rep.get("intents") or session.scan_cart_intents or ["Reactor"])
    with ui.row().classes("gap-4 flex-wrap w-full"):
        ui.select(
            intents,
            label="Intent",
            value=session.scan_wb_intent if session.scan_wb_intent in intents else intents[0],
            on_change=lambda e: setattr(session, "scan_wb_intent", str(e.value)),
        ).classes("w-36")
        ui.select(
            {k: SCAN_VAR_LABELS.get(k, k) for k in z_opts},
            label="Off-plane axis (z)",
            value=session.scan_slice_z_key,
            on_change=lambda e: setattr(session, "scan_slice_z_key", str(e.value)),
        ).classes("w-40")
        ui.number(
            "Relative step",
            value=float(getattr(session, "scan_slice_rel_step", 0.05)),
            min=0.01,
            max=0.2,
            step=0.01,
            on_change=lambda e: setattr(session, "scan_slice_rel_step", float(e.value)),
        ).classes("w-28")

    i, j = int(session.scan_wb_i), int(session.scan_wb_j)
    ui.label(f"Probed cell (i,j)=({i},{j})").classes("text-caption q-mb-sm")

    async def _run() -> None:
        ui.notify("Running projection stability…", type="info")
        try:
            out = await run.io_bound(
                projection_stability,
                session.build_point_inputs(),
                rep,
                str(session.scan_wb_intent),
                i,
                j,
                str(session.scan_slice_z_key),
                float(session.scan_slice_rel_step),
            )
            session.scan_slice_diag_last = out
            _panel.refresh()
            if on_update:
                on_update()
            ui.notify("Off-plane check complete.", type="positive")
        except Exception as exc:
            ui.notify(f"Diagnostics failed: {exc}", type="negative")

    ui.button("Run off-plane stability check", icon="layers", on_click=_run).props("outline q-mb-sm")
    _panel(session)


@ui.refreshable
def _panel(session: DesignSession) -> None:
    out = getattr(session, "scan_slice_diag_last", None)
    if not isinstance(out, dict):
        return
    plain = format_projection_stability(out)
    if plain:
        ui.markdown(plain).classes("text-body2")
    stab = out.get("dominant_stability")
    if isinstance(stab, (int, float)) and stab < 0.6:
        ui.label(
            "Low dominance stability off-plane — consider a different slice or a third cartography axis."
        ).classes("text-caption text-orange")
