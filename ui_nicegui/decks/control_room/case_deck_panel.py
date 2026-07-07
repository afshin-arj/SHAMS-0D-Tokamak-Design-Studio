"""Control Room — case deck runner."""
from __future__ import annotations

from nicegui import run, ui

from ui_nicegui.lib.cr_governance_helpers import run_case_deck_file
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def render_case_deck_runner(session: DesignSession) -> None:
    ui.label("Case Deck Runner").classes("text-subtitle1")
    ui.label("Run a case_deck YAML/JSON deck and view resolved config + artifact outputs.").classes(
        "text-caption text-grey q-mb-sm"
    )

    out_name = ui.input("Output folder (under ui_runs/)", value="deck_run").classes("w-full")

    async def _upload(e) -> None:
        try:
            content = e.content.read()
            fname = getattr(e, "name", None) or "case_deck.yaml"
            result = await run.io_bound(
                run_case_deck_file,
                content,
                str(fname),
                str(out_name.value or "deck_run"),
            )
            session.cr_case_deck_last = result
            if result.get("returncode") == 0:
                ui.notify(f"Case deck finished — {result.get('out_dir')}", type="positive")
            else:
                ui.notify("Case deck run failed — see stderr", type="negative")
            _result.refresh(session)
        except Exception as exc:
            ui.notify(f"Run failed: {exc}", type="negative")

    ui.upload(on_upload=_upload).props('accept=".yaml,.yml,.json" auto-upload label="Upload case_deck.yaml / .json"')
    _result(session)


@ui.refreshable
def _result(session: DesignSession) -> None:
    result = session.cr_case_deck_last
    if not isinstance(result, dict):
        return
    ui.label(f"Exit code: {result.get('returncode')} · {result.get('out_dir', '')}").classes("text-caption")
    if result.get("stdout"):
        with ui.expansion("stdout", icon="terminal").classes("w-full"):
            ui.code(result["stdout"])
    if result.get("stderr"):
        with ui.expansion("stderr", icon="error").classes("w-full"):
            ui.code(result["stderr"])
    if isinstance(result.get("resolved_config"), dict):
        with ui.expansion("Resolved config", icon="settings").classes("w-full"):
            render_json_blob(result["resolved_config"])
    if isinstance(result.get("artifact"), dict):
        with ui.expansion("Run artifact preview", icon="data_object").classes("w-full"):
            render_json_blob(result["artifact"])
