"""Control Room Artifacts section — Phase 18."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.decks.control_room import benchmarks_reference
from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.compare_helpers import open_compare_deck, store_compare_slot
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
    watermark_run_artifact_export,
)
from ui_nicegui.lib.cr_governance_helpers import design_confidence_class, nonfeasibility_certificate_view
from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.lib.verdict_core import verdict_summary
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


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
        idx = next((i for i, a in enumerate(arts) if a["id"] == session.cr_selected_artifact_id), len(arts) - 1)

        def _on_pick(e) -> None:
            label = str(e.value)
            pick = next((a for a in arts if a["label"] == label), arts[idx])
            session.cr_selected_artifact = pick["artifact"]
            session.cr_selected_artifact_id = pick["id"]
            _artifact_view.refresh(pick["artifact"], session)

        sel = ui.select(labels, label="Session artifact", value=labels[idx], on_change=_on_pick).classes("w-full")
        pick = next(a for a in arts if a["label"] == sel.value)
        session.cr_selected_artifact = pick["artifact"]
        session.cr_selected_artifact_id = pick["id"]
        _artifact_view(pick["artifact"], session)
    else:
        empty_state("No session artifacts yet — evaluate in Point Designer first.", kind="info")
        ui.button("Open Point Designer", icon="open_in_new", on_click=lambda: switch_deck("Point Designer")).props(
            "flat outline q-mt-sm"
        )

    async def _upload(e) -> None:
        try:
            art = load_json_bytes(e.content.read())
            session.cr_selected_artifact = art
            session.cr_selected_artifact_id = "upload"
            ui.notify("Artifact loaded", type="positive")
            _upload_view.refresh(session)
        except Exception as exc:
            ui.notify(f"Load failed: {exc}", type="negative")

    ui.upload(on_upload=_upload).props('accept=".json" auto-upload label="Upload shams_run_artifact.json"')
    _upload_view(session)


@ui.refreshable
def _upload_view(session: DesignSession) -> None:
    if isinstance(session.cr_selected_artifact, dict):
        _artifact_view(session.cr_selected_artifact, session)


@ui.refreshable
def _artifact_view(art: dict, session: DesignSession) -> None:
    outs = art.get("outputs") if isinstance(art.get("outputs"), dict) else art
    vs = verdict_summary(outs if isinstance(outs, dict) else {})
    summary = artifact_summary(art)
    kpis = art.get("kpis") if isinstance(art.get("kpis"), dict) else {}
    fh = kpis.get("feasible_hard")
    kpi_row([
        ("Verdict", vs.get("verdict", "-") if vs.get("loaded") else "-"),
        ("Dominant", vs.get("dominant", "-") if vs.get("loaded") else "-"),
        ("Design class", design_confidence_class(art)),
        ("Hard feasible", "-" if fh is None else ("YES" if fh else "NO")),
        ("Ledger entries", str(summary.get("ledger_entries", "-"))),
    ])

    cert = nonfeasibility_certificate_view(art)
    blockers = cert.get("dominant_blockers") or []
    if blockers:
        ui.label(f"{len(blockers)} hard blocker(s) — worst: {blockers[0].get('name', '?')}").classes(
            "text-caption text-negative q-mb-xs"
        )

    with ui.row().classes("gap-2 flex-wrap q-mb-sm"):
        ui.button(
            "Send to Compare A",
            icon="compare",
            on_click=lambda: (
                store_compare_slot(
                    session, art, "A", label="Control Room explorer", refresh=False
                ),
                ui.notify("Loaded Compare slot A", type="positive"),
            ),
        ).props("flat outline dense")
        ui.button(
            "Send to Compare B",
            icon="compare",
            on_click=lambda: (
                store_compare_slot(
                    session, art, "B", label="Control Room explorer", refresh=False
                ),
                ui.notify("Loaded Compare slot B", type="positive"),
            ),
        ).props("flat outline dense")
        ui.button(
            "Open Compare deck",
            icon="open_in_new",
            on_click=lambda: (
                open_compare_deck(session),
                ui.notify("Opened Compare deck.", type="info"),
            ),
        ).props("flat outline dense")

    rows = ledger_rows(art)[:50]
    if rows:
        cols = [c for c in ("name", "margin", "failed", "severity", "authority_tier") if any(c in r for r in rows)]
        if not cols:
            cols = list(rows[0].keys())[:6]
        ui.table(
            columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in cols],
            rows=[{c: r.get(c) for c in cols} for r in rows],
            row_key=cols[0],
        ).classes("w-full")

    tables = art.get("tables") or {}
    if isinstance(tables, dict) and session.cr_expert_view:
        from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_claim_kpi_map

        feasible = bool(vs.get("feasible")) if vs.get("loaded") else False
        if not feasible:
            ui.label(
                "PHYS-KPI-001: plasma / power_balance claim KPIs below are diagnostic residue "
                "on an INFEASIBLE artifact — not design claims."
            ).classes("text-caption text-orange q-mb-xs")
        v1 = tables.get("v1") or tables
        if isinstance(v1, dict):
            for section in ("plasma", "power_balance", "tritium", "regimes"):
                block = v1.get(section)
                if isinstance(block, dict) and block:
                    display = (
                        watermark_claim_kpi_map(block, feasible=feasible, point_out=outs)
                        if section in ("plasma", "power_balance")
                        else block
                    )
                    with ui.expansion(f"Table: {section}", icon="table_chart").classes("w-full"):
                        render_json_blob(display)

    if session.cr_expert_view:
        with ui.expansion("Full artifact JSON", icon="data_object").classes("w-full"):
            from ui_nicegui.lib.cr_artifacts_helpers import watermark_run_artifact_export

            render_json_blob(
                watermark_run_artifact_export(art) if isinstance(art, dict) else art
            )


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
            _artifact_view.refresh(session.cr_selected_artifact, session)
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
        on_click=lambda: ui.download(
            report_to_json_bytes(watermark_run_artifact_export(art)),
            "shams_run_artifact.json",
        ),
    ).props("outline")
    ui.button(
        "Download artifact bundle ZIP",
        icon="folder_zip",
        on_click=lambda: ui.download(export_artifact_bundle(art), "shams_artifact_bundle.zip"),
    ).props("outline q-mt-sm")

    def _cite_pack() -> None:
        try:
            try:
                from reports.cite_shams_handoff_pack import build_cite_shams_handoff_pack
            except ImportError:
                from src.reports.cite_shams_handoff_pack import build_cite_shams_handoff_pack
            pack = build_cite_shams_handoff_pack(watermark_run_artifact_export(art))
            ui.download(
                pack["zip_bytes"],
                pack.get("suggested_filename") or "shams_cite_handoff.zip",
            )
            ui.notify("Cite-SHAMS handoff pack ready", type="positive")
        except Exception as exc:
            ui.notify(f"Cite-SHAMS pack failed: {exc}", type="negative")

    ui.button(
        "Download cite-SHAMS handoff pack",
        icon="inventory_2",
        on_click=_cite_pack,
    ).props("outline color=primary q-mt-sm")
    ui.label(
        "Cite VERSION + artifact SHA-256 — PROCESS import optional for new studies."
    ).classes("text-caption text-grey-7 q-mt-xs")
