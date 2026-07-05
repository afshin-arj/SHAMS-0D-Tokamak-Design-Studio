"""Control Room — Diagnostics section."""
from __future__ import annotations

from nicegui import ui
from nicegui import run

from ui_nicegui.lib.control_room_helpers import (
    DIAG_TABS,
    hygiene_scan,
    interop_check,
    read_version,
    report_to_json_bytes,
    run_contract_validator,
    session_snapshot,
)
from ui_nicegui.session import DesignSession


def render_diagnostics(session: DesignSession) -> None:
    with ui.tabs().classes("w-full") as tabs:
        tab_widgets = {name: ui.tab(name) for name in DIAG_TABS}

    with ui.tab_panels(tabs, value=tab_widgets[session.cr_diag_tab]).classes("w-full"):
        with ui.tab_panel(tab_widgets["Gatechecks"]):
            ui.label("Gatechecks").classes("text-subtitle2")
            ui.markdown(
                """
Run these from a terminal at the repo root:

- `python -m compileall -q .`
- `pytest -q`
- `python ui_nicegui/app.py`

This panel performs a lightweight hygiene scan of the working tree.
"""
            )
            scan = hygiene_scan()
            if scan.get("ok"):
                ui.label("No hygiene violations detected in this tree.").classes("text-positive")
            else:
                ui.label("Hygiene violations detected (should be removed before packaging).").classes(
                    "text-negative"
                )
                with ui.expansion("Show paths").classes("w-full"):
                    for h in scan.get("hits") or []:
                        ui.label(h).classes("text-caption")

        with ui.tab_panel(tab_widgets["Interoperability"]):
            ui.label("Interoperability & contract validator").classes("text-subtitle2")
            ui.label("Static + runtime wiring audit — no physics, no truth modifications.").classes(
                "text-caption q-mb-sm"
            )

            async def _run_interop() -> None:
                session.cr_interop_report = interop_check(session)
                ui.notify(
                    "Interoperability: OK" if session.cr_interop_report.get("ok") else "Issues detected",
                    type="positive" if session.cr_interop_report.get("ok") else "warning",
                )

            async def _run_contract() -> None:
                try:
                    session.cr_contract_report = await run.io_bound(run_contract_validator, session)
                    ui.notify(
                        "Contract validator: OK" if session.cr_contract_report.get("ok") else "Issues detected",
                        type="positive" if session.cr_contract_report.get("ok") else "warning",
                    )
                except Exception as exc:
                    ui.notify(f"Contract validator failed: {exc}", type="negative")

            with ui.row().classes("gap-2 q-mb-sm"):
                ui.button("Run interoperability check", on_click=_run_interop)
                ui.button("Run contract validator", on_click=_run_contract)

            ir = session.cr_interop_report
            if isinstance(ir, dict):
                ui.label(
                    "Interoperability check: OK" if ir.get("ok") else "Interoperability check: issues detected"
                ).classes("text-body2")
                with ui.expansion("Interoperability report").classes("w-full"):
                    ui.json(ir)

            cr = session.cr_contract_report
            if isinstance(cr, dict):
                ui.label(
                    "Contract validator: OK" if cr.get("ok") else "Contract validator: issues detected"
                ).classes("text-body2 q-mt-sm")
                with ui.expansion("Contract validator report").classes("w-full"):
                    ui.json(cr)
                ui.download_button(
                    "Download contract report JSON",
                    report_to_json_bytes(cr),
                    "shams_contract_validator.json",
                ).props("flat")

        with ui.tab_panel(tab_widgets["Session"]):
            ui.label("Session debug").classes("text-subtitle2")
            ui.label(f"Version: {read_version()}").classes("text-caption")
            snap = session_snapshot(session)
            with ui.expansion("Session keys", value=True).classes("w-full"):
                for k, v in snap.items():
                    ui.label(f"{k}: {v}").classes("text-caption")

        with ui.tab_panel(tab_widgets["Non-Feasibility Guide"]):
            ui.label("Non-Feasibility Guide").classes("text-subtitle2")
            ui.label(
                "Deterministic local forensics around the current Point Designer inputs — "
                "identifies which knobs most affect feasibility margins."
            ).classes("text-caption q-mb-sm")

            async def _forensics() -> None:
                try:
                    from ui_nicegui.lib.cr_chronicle_helpers import run_local_forensics

                    rep = await run.io_bound(
                        run_local_forensics,
                        session.build_point_inputs(),
                        design_intent="Reactor",
                    )
                    session.cr_forensics_last = rep
                    ui.notify("Forensics complete", type="positive")
                    _nf_view.refresh()
                except Exception as exc:
                    ui.notify(f"Forensics failed: {exc}", type="negative")

            ui.button("Run forensics on current point", on_click=_forensics).props("outline")
            _nf_view(session)


@ui.refreshable
def _nf_view(session: DesignSession) -> None:
    rep = session.cr_forensics_last
    if isinstance(rep, dict):
        with ui.expansion("Forensics JSON", icon="description").classes("w-full"):
            ui.json(rep)
