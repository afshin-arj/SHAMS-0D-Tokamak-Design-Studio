"""Control Room — Diagnostics section."""
from __future__ import annotations

from nicegui import ui
from nicegui import run

from ui_nicegui.decks.control_room import validation_envelopes
from ui_nicegui.lib.control_room_helpers import (
    DIAG_TABS,
    hygiene_scan,
    interop_check,
    read_version,
    report_to_json_bytes,
    run_contract_validator,
    session_snapshot,
)
from ui_nicegui.lib.cr_governance_helpers import nonfeasibility_certificate_view, pick_session_artifact
from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def render_diagnostics(session: DesignSession) -> None:
    if session.cr_diag_tab not in DIAG_TABS:
        session.cr_diag_tab = DIAG_TABS[0]

    ui.toggle(
        DIAG_TABS,
        value=session.cr_diag_tab,
        on_change=lambda e: (
            setattr(session, "cr_diag_tab", str(e.value)),
            _panel.refresh(),
        ),
    ).classes("q-mb-md")

    _panel(session)


@ui.refreshable
def _panel(session: DesignSession) -> None:
    tab = session.cr_diag_tab
    if tab == "Gatechecks":
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
        if scan.get("packaging_ok"):
            ui.label("No packaging hygiene violations detected.").classes("text-positive")
        else:
            ui.label("Packaging hygiene violations detected (remove before release).").classes(
                "text-negative"
            )
        dev_hits = scan.get("dev_cache_hits") or []
        if dev_hits:
            ui.label(
                f"Dev cache artifacts present ({len(dev_hits)} paths) — advisory only, not a release blocker."
            ).classes("text-caption text-grey")
        if not scan.get("packaging_ok"):
            with ui.expansion("Show packaging paths").classes("w-full"):
                for h in scan.get("hits") or []:
                    if h not in dev_hits:
                        ui.label(h).classes("text-caption")
        elif dev_hits:
            with ui.expansion("Show dev cache paths").classes("w-full"):
                for h in dev_hits:
                    ui.label(h).classes("text-caption")

    elif tab == "Interoperability":
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
                render_json_blob(ir)

        cr = session.cr_contract_report
        if isinstance(cr, dict):
            nicegui_ok = cr.get("nicegui_ok", cr.get("ok"))
            ui.label(
                "Contract validator (NiceGUI scope): OK"
                if nicegui_ok
                else "Contract validator: issues detected"
            ).classes("text-body2 q-mt-sm")
            sp = cr.get("streamlit_parity") or {}
            parts = []
            if sp.get("uncontracted_panels"):
                parts.append(f"{sp['uncontracted_panels']} uncontracted panels")
            if sp.get("missing_functions"):
                parts.append(f"{sp['missing_functions']} missing contract targets")
            if sp.get("empty_requires"):
                parts.append(f"{sp['empty_requires']} empty requires")
            if parts:
                ui.label(
                    "Streamlit parity note: " + ", ".join(parts) + " (informational)."
                ).classes("text-caption text-grey")
            with ui.expansion("Contract validator report").classes("w-full"):
                render_json_blob(cr)
            ui.download_button(
                "Download contract report JSON",
                report_to_json_bytes(cr),
                "shams_contract_validator.json",
            ).props("flat")

    elif tab == "Validation Envelopes":
        validation_envelopes.render_validation_envelopes(session)

    elif tab == "Session":
        ui.label("Session debug").classes("text-subtitle2")
        ui.label(f"Version: {read_version()}").classes("text-caption")
        snap = session_snapshot(session)
        with ui.expansion("Session keys", value=True).classes("w-full"):
            for k, v in snap.items():
                ui.label(f"{k}: {v}").classes("text-caption")

    elif tab == "Non-Feasibility Guide":
        _non_feasibility_guide(session)


def _non_feasibility_guide(session: DesignSession) -> None:
    ui.label("Non-Feasibility Guide").classes("text-subtitle2")
    ui.label(
        "Certificate-first review from the loaded run artifact, then optional local forensics on current inputs."
    ).classes("text-caption q-mb-sm")

    art = pick_session_artifact(session)
    if not isinstance(art, dict):
        ui.label("No run artifact on session.").classes("text-warning q-mb-sm")
        ui.button("Open Point Designer", icon="open_in_new", on_click=lambda: switch_deck("Point Designer")).props(
            "flat outline"
        )
    else:
        cert = nonfeasibility_certificate_view(art)
        if cert.get("hard_feasible") is True:
            ui.label("This run is hard-feasible — guided non-feasibility mode is not needed.").classes(
                "text-positive q-mb-sm"
            )
        elif cert:
            blockers = cert.get("dominant_blockers") or []
            ui.label(f"Non-feasibility certificate — {len(blockers)} hard blocker(s)").classes("text-subtitle2")
            if blockers:
                cols = [c for c in ("name", "group", "margin", "limit", "value", "sense") if any(c in b for b in blockers)]
                ui.table(
                    columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in cols],
                    rows=[{c: b.get(c) for c in cols} for b in blockers],
                    row_key="name",
                ).classes("w-full q-mb-sm")
                rec = cert.get("recommendation")
                if rec:
                    ui.label(str(rec)).classes("text-caption")
            if session.cr_expert_view:
                with ui.expansion("Full certificate JSON", icon="data_object").classes("w-full"):
                    render_json_blob(cert)
        else:
            ui.label("No hard failures detected in artifact constraints.").classes("text-caption")

    ui.separator().classes("q-my-md")
    ui.label("Local forensics (current Point Designer inputs)").classes("text-subtitle2")

    async def _forensics() -> None:
        from ui_nicegui.lib.run_lock import (
            acquire as runlock_acquire,
            release as runlock_release,
            status as runlock_status,
            current_lease,
            lease_valid,
        )

        locked, task, is_owner = runlock_status("ControlRoom")
        if locked:
            ui.notify(
                f"Busy: {task} — wait or force-clear from Helm."
                if not is_owner
                else "Control Room already holds the run lock.",
                type="warning",
            )
            return
        if not runlock_acquire("Control Room: Diagnostics forensics", "ControlRoom"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        lease = current_lease()
        try:
            from ui_nicegui.lib.cr_chronicle_helpers import run_local_forensics

            rep = await run.io_bound(
                run_local_forensics,
                session.build_point_inputs(),
                design_intent="Reactor",
            )
            if not lease_valid(lease):
                ui.notify("Run was force-cleared — discarding results.", type="warning")
                return
            session.cr_forensics_last = rep
            ui.notify("Forensics complete", type="positive")
            _nf_view.refresh()
        except Exception as exc:
            ui.notify(f"Forensics failed: {exc}", type="negative")
        finally:
            if lease_valid(lease):
                runlock_release("ControlRoom", lease)

    ui.button("Run forensics on current point", on_click=_forensics).props("outline")
    _nf_view(session)


@ui.refreshable
def _nf_view(session: DesignSession) -> None:
    rep = session.cr_forensics_last
    if isinstance(rep, dict):
        ranked = rep.get("ranked_knobs") or rep.get("knobs") or rep.get("sensitivity")
        if isinstance(ranked, list) and ranked:
            ui.label("Top sensitivity knobs").classes("text-caption q-mt-sm")
            rows = []
            for i, r in enumerate(ranked[:10]):
                if isinstance(r, dict):
                    rows.append({"idx": i, **r})
                else:
                    rows.append({"idx": i, "knob": str(r)})
            ui.table(
                columns=[{"name": "knob", "label": "knob", "field": "knob", "align": "left"}],
                rows=rows,
                row_key="idx",
            ).classes("w-full")
        if session.cr_expert_view:
            with ui.expansion("Forensics JSON", icon="description").classes("w-full"):
                render_json_blob(rep)
