"""Control Room Artifacts section — Phase 18."""
from __future__ import annotations

from pathlib import Path

from nicegui import run, ui

from ui_nicegui.decks.control_room import benchmarks_reference
from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.control_room_helpers import ARTIFACT_TABS, report_to_json_bytes
from ui_nicegui.lib.cr_artifacts_helpers import (
    artifact_summary,
    collect_session_artifacts,
    export_artifact_bundle,
    ledger_rows,
    list_run_json_files,
    list_ui_run_dirs,
    load_json_bytes,
    load_json_path,
)
from ui_nicegui.session import DesignSession


def render_artifacts(session: DesignSession) -> None:
    if session.cr_artifacts_tab not in ARTIFACT_TABS:
        session.cr_artifacts_tab = ARTIFACT_TABS[0]

    ui.toggle(
        ARTIFACT_TABS,
        value=session.cr_artifacts_tab,
        on_change=lambda e: (
            setattr(session, "cr_artifacts_tab", str(e.value)),
            _panel.refresh(),
        ),
    ).classes("q-mb-md")

    _panel(session)


@ui.refreshable
def _panel(session: DesignSession) -> None:
    tab = session.cr_artifacts_tab
    if tab == "Artifacts Explorer":
        _explorer(session)
    elif tab == "Run Library":
        _run_library(session)
    elif tab == "Export & Share":
        _export_share(session)
    else:
        benchmarks_reference.render_benchmark_reference(session)


def _explorer(session: DesignSession) -> None:
    ui.label("Artifacts Explorer").classes("text-subtitle1")
    ui.label("Load a SHAMS run artifact and inspect ledger, model set, and tables.").classes("text-caption")

    arts = collect_session_artifacts(session)
    if arts:
        labels = [a["label"] for a in arts]
        if session.cr_selected_artifact_id not in [a["id"] for a in arts]:
            session.cr_selected_artifact_id = arts[-1]["id"]
        sel = ui.select(labels, label="Session artifact", value=labels[-1]).classes("w-full")
        pick = next(a for a in arts if a["label"] == sel.value)
        session.cr_selected_artifact = pick["artifact"]
        session.cr_selected_artifact_id = pick["id"]
        _artifact_view(session.cr_selected_artifact)
    else:
        ui.label("No session artifacts yet — evaluate in Point Designer first.").classes("text-caption q-mb-sm")

    async def _upload(e) -> None:
        try:
            art = load_json_bytes(e.content.read())
            session.cr_selected_artifact = art
            session.cr_selected_artifact_id = "upload"
            ui.notify("Artifact loaded", type="positive")
            _upload_view.refresh()
        except Exception as exc:
            ui.notify(f"Load failed: {exc}", type="negative")

    ui.upload(on_upload=_upload).props('accept=".json" auto-upload label="Upload shams_run_artifact.json"')
    _upload_view(session)


@ui.refreshable
def _upload_view(session: DesignSession) -> None:
    if isinstance(session.cr_selected_artifact, dict):
        _artifact_view(session.cr_selected_artifact)


@ui.refreshable
def _artifact_view(art: dict) -> None:
    summary = artifact_summary(art)
    kpi_row([
        ("Schema", str(summary.get("schema") or "-")),
        ("Label", str(summary.get("label") or "-")),
        ("Ledger entries", str(summary.get("ledger_entries", "-"))),
        ("Model set", "yes" if summary.get("has_model_set") else "no"),
    ])
    rows = ledger_rows(art)[:50]
    if rows:
        cols = [c for c in ("name", "margin", "failed", "severity") if any(c in r for r in rows)]
        if not cols:
            cols = list(rows[0].keys())[:6]
        ui.table(
            columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in cols],
            rows=[{c: r.get(c) for c in cols} for r in rows],
            row_key=cols[0],
        ).classes("w-full")
    with ui.expansion("Full artifact JSON", icon="data_object").classes("w-full"):
        ui.json(art)


def _run_library(session: DesignSession) -> None:
    ui.label("Run Library").classes("text-subtitle1")
    runs = list_ui_run_dirs()
    if not runs:
        empty_state("No folders under `ui_runs/` yet.", kind="info")
        return
    names = [p.name for p in runs]
    sel = ui.select(names, label="Run folder", value=names[0]).classes("w-full")
    run_dir = next(p for p in runs if p.name == sel.value)
    files = list_run_json_files(run_dir)
    ui.label(f"{len(files)} JSON file(s) in {run_dir.name}").classes("text-caption")

    def _load_file(name: str) -> None:
        try:
            session.cr_selected_artifact = load_json_path(run_dir / name)
            session.cr_selected_artifact_id = f"ui_runs/{run_dir.name}/{name}"
            ui.notify(f"Loaded {name}", type="positive")
            _artifact_view.refresh()
        except Exception as exc:
            ui.notify(f"Load failed: {exc}", type="negative")

    for f in files[:20]:
        ui.button(f.name, on_click=lambda n=f.name: _load_file(n)).props("flat outline dense")


def _export_share(session: DesignSession) -> None:
    ui.label("Export & Share").classes("text-subtitle1")
    art = session.cr_selected_artifact
    if not isinstance(art, dict):
        if isinstance(session.pd_last_artifact, dict):
            art = session.pd_last_artifact
        else:
            empty_state("Select or upload an artifact in **Artifacts Explorer** first.", kind="info")
            return

    ui.button(
        "Download artifact JSON",
        icon="download",
        on_click=lambda: ui.download(report_to_json_bytes(art), "shams_run_artifact.json"),
    ).props("outline")
    ui.button(
        "Download artifact bundle ZIP",
        icon="folder_zip",
        on_click=lambda: ui.download(export_artifact_bundle(art), "shams_artifact_bundle.zip"),
    ).props("outline q-mt-sm")
