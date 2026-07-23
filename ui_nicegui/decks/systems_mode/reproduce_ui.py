"""Reproduce, diff, and regression guardrails for Systems run history."""

from __future__ import annotations

import json

from nicegui import ui

from ui_nicegui.lib.systems_reproduce import json_structural_diff, regression_json_from_run, systems_run_records
from ui_nicegui.session import DesignSession


def _restore_ui_state(session: DesignSession, payload: dict, *, run_id: str = "") -> None:
    ui_state = payload.get("ui_state") if isinstance(payload.get("ui_state"), dict) else {}
    for k, v in ui_state.items():
        if hasattr(session, k):
            setattr(session, k, v)
    if isinstance(payload, dict) and payload:
        art = dict(payload)
        # Restored history is not a fresh Newton solve (provenance honesty).
        prev_src = str(art.get("source") or "").strip()
        if prev_src:
            art["restored_source"] = prev_src
        art["source"] = "systems_restored"
        if run_id:
            art["restored_from_run_id"] = run_id
        session.systems_last_solve_artifact = art
        session.systems_last_solve_result = None


def render_reproduce_panel(session: DesignSession, *, on_change=None) -> None:
    with ui.expansion("Reproduce, diff & regression", icon="compare").classes("w-full q-mt-sm"):
        ui.label(
            "Freeze-grade audit: restore a recorded run, compare two artifacts, or export a minimal regression case."
        ).classes("text-caption q-mb-sm")

        runs = systems_run_records(session)
        if not runs:
            ui.label("No recorded Systems runs yet — run precheck, solve, or recovery first.").classes("text-grey")
            return

        ids = [r["id"] for r in runs]
        labels = {r["id"]: f"{r['id']} — {r['ts']} — {r['kind']}" for r in runs}

        if session.systems_repro_pick not in ids:
            session.systems_repro_pick = ids[0]
        if session.systems_diff_a not in ids:
            session.systems_diff_a = ids[0]
        if session.systems_diff_b not in ids:
            session.systems_diff_b = ids[min(1, len(ids) - 1)]

        pick = ui.select(
            ids,
            label="Recorded run",
            value=session.systems_repro_pick,
            on_change=lambda e: setattr(session, "systems_repro_pick", str(e.value)),
        ).classes("w-full")

        def _reproduce() -> None:
            rid = str(pick.value or session.systems_repro_pick)
            run = next((r for r in runs if r["id"] == rid), None)
            if not run:
                ui.notify("Run not found", type="warning")
                return
            payload = run.get("payload") if isinstance(run.get("payload"), dict) else {}
            if not payload:
                ui.notify("Run has no stored artifact payload", type="warning")
                return
            _restore_ui_state(session, payload, run_id=rid)
            ui.notify(f"Restored run {rid} as systems_restored (re-certify via Precheck/Solve).", type="positive")
            if on_change:
                on_change()

        def _download_run() -> None:
            from ui_nicegui.lib.cr_artifacts_helpers import watermark_run_artifact_export

            rid = str(pick.value or session.systems_repro_pick)
            run = next((r for r in runs if r["id"] == rid), None)
            payload = (run or {}).get("payload") or {}
            if isinstance(payload, dict):
                payload = watermark_run_artifact_export(payload)
            ui.download(
                json.dumps(payload, indent=2, sort_keys=True, default=str).encode("utf-8"),
                f"{rid}.json",
            )

        with ui.row().classes("gap-2 q-mb-md"):
            ui.button("Restore this run", icon="history", on_click=_reproduce).props("outline")
            ui.button("Download run JSON", icon="download", on_click=_download_run).props("flat")

        ui.label("Structural diff (JSON paths)").classes("text-subtitle2 q-mt-sm")
        rid_a = ui.select(
            ids,
            label="Run A",
            value=session.systems_diff_a,
            on_change=lambda e: setattr(session, "systems_diff_a", str(e.value)),
        ).classes("w-full")
        rid_b = ui.select(
            ids,
            label="Run B",
            value=session.systems_diff_b,
            on_change=lambda e: setattr(session, "systems_diff_b", str(e.value)),
        ).classes("w-full")

        def _show_diff() -> None:
            a = next((r for r in runs if r["id"] == str(rid_a.value)), None)
            b = next((r for r in runs if r["id"] == str(rid_b.value)), None)
            pa = (a or {}).get("payload") or {}
            pb = (b or {}).get("payload") or {}
            diffs = json_structural_diff(pa, pb)
            diff_view.clear()
            with diff_view:
                ui.label(f"Changed fields: {len(diffs)}").classes("text-caption")
                for line in diffs[:200]:
                    ui.label(line).classes("text-caption font-mono")
                if len(diffs) > 200:
                    ui.label(f"… and {len(diffs) - 200} more").classes("text-caption text-grey")

        diff_view = ui.column().classes("w-full")
        ui.button("Compare runs", on_click=_show_diff).props("flat dense q-mb-sm")

        ui.label("Regression test case (from Run A)").classes("text-subtitle2 q-mt-sm")

        def _download_regression() -> None:
            run = next((r for r in runs if r["id"] == str(rid_a.value)), None)
            if not run:
                return
            ui.download(
                regression_json_from_run(run).encode("utf-8"),
                f"regression_{run['id']}.json",
            )

        ui.button("Download regression JSON", icon="save", on_click=_download_regression).props("flat dense")
