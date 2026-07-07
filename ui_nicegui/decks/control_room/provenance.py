"""Control Room Provenance — studies, protocol, repro lock, citation, regression."""
from __future__ import annotations

import json
from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.decks.control_room import case_deck_panel, run_audit, scenario_delta
from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.cr_provenance_helpers import (
    build_authority_pack_zip,
    build_citation_bundle,
    build_repro_lock,
    build_study_protocol,
    list_session_run_artifacts,
    regression_artifact_diff,
    replay_check,
    run_repo_regression,
    save_point_study,
    study_protocol_markdown,
)
from ui_nicegui.lib.control_room_helpers import report_to_json_bytes
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob

PROVENANCE_TABS = [
    "Studies & Protocol",
    "Repro Lock",
    "Authority & Citation",
    "Run Audit",
    "Case Deck Runner",
    "Scenario Delta",
    "Studies Manager",
    "Regression Viewer",
]


def render_provenance(session: DesignSession, *, on_update: Optional[Callable[[], None]] = None) -> None:
    ui.label("Provenance").classes("text-subtitle1")
    ui.label(
        "Study protocol, reproducibility lock, authority pack, citation bundle, and regression visibility."
    ).classes("text-caption text-grey q-mb-sm")

    if session.cr_provenance_tab not in PROVENANCE_TABS:
        session.cr_provenance_tab = PROVENANCE_TABS[0]

    ui.toggle(
        PROVENANCE_TABS,
        value=session.cr_provenance_tab,
        on_change=lambda e: (
            setattr(session, "cr_provenance_tab", str(e.value)),
            _render_panel.refresh(),
        ),
    ).classes("q-mb-md")

    _render_panel(session, on_update=on_update)


@ui.refreshable
def _render_panel(session: DesignSession, *, on_update: Optional[Callable[[], None]] = None) -> None:
    tab = session.cr_provenance_tab
    if tab == "Studies & Protocol":
        _render_study_protocol(session)
    elif tab == "Repro Lock":
        _render_repro_lock(session)
    elif tab == "Authority & Citation":
        _render_authority_citation(session)
    elif tab == "Run Audit":
        run_audit.render_run_audit(session)
    elif tab == "Case Deck Runner":
        case_deck_panel.render_case_deck_runner(session)
    elif tab == "Scenario Delta":
        scenario_delta.render_scenario_delta(session)
    elif tab == "Studies Manager":
        _render_studies_manager(session)
    else:
        _render_regression_viewer(session)


def _run_artifact_picker(session: DesignSession):
    runs = list_session_run_artifacts(session)
    if not runs:
        empty_state("Run **Point Designer** (Evaluate) first to create a run artifact.", kind="info")
        return None, None
    labels = [r["label"] for r in runs]
    if session.cr_selected_run_id not in [r["id"] for r in runs]:
        session.cr_selected_run_id = runs[-1]["id"]
    idx = next((i for i, r in enumerate(runs) if r["id"] == session.cr_selected_run_id), len(runs) - 1)
    sel = ui.select(labels, label="Run artifact", value=labels[idx]).classes("w-full")
    pick = runs[labels.index(sel.value) if sel.value in labels else idx]
    session.cr_selected_run_id = pick["id"]
    return pick["artifact"], pick


def _render_study_protocol(session: DesignSession) -> None:
    art, _ = _run_artifact_picker(session)
    if not isinstance(art, dict):
        return

    title = ui.input("Study title", value=session.cr_protocol_title or "SHAMS Design Study").classes("w-full")
    objective = ui.textarea(
        "Objective",
        value=session.cr_protocol_objective
        or "Feasibility characterization and completion under explicit constraints.",
    ).classes("w-full").props("rows=3")

    async def _generate() -> None:
        runs = list_session_run_artifacts(session)
        if not runs:
            ui.notify("No run artifact", type="warning")
            return
        art_local = next((r["artifact"] for r in runs if r["id"] == session.cr_selected_run_id), runs[-1]["artifact"])
        overrides = {
            "title": str(title.value or ""),
            "objective": str(objective.value or ""),
            "notes": [],
            "variables_varied": [],
            "artifacts_generated": ["study_protocol_v165.json", "study_protocol_v165.md"],
            "seed": int(session.cr_protocol_seed),
        }
        try:
            prot = await run.io_bound(build_study_protocol, art_local, overrides)
            session.cr_study_protocol_last = prot
            sha = ((prot.get("payload") or {}).get("integrity") or {}).get("protocol_sha256", "")
            ui.notify(f"Protocol generated — SHA {str(sha)[:12]}…", type="positive")
            _protocol_dl.refresh()
        except Exception as exc:
            ui.notify(f"Protocol failed: {exc}", type="negative")

    ui.button("Generate Study Protocol", icon="description", on_click=_generate).props("color=primary outline")
    _protocol_dl(session)


@ui.refreshable
def _protocol_dl(session: DesignSession) -> None:
    prot = session.cr_study_protocol_last
    if not isinstance(prot, dict):
        return
    ui.button(
        "Download study_protocol_v165.json",
        icon="download",
        on_click=lambda: ui.download(report_to_json_bytes(prot), "study_protocol_v165.json"),
    ).props("flat outline")
    try:
        md = study_protocol_markdown(prot)
        ui.button(
            "Download study_protocol_v165.md",
            icon="download",
            on_click=lambda m=md: ui.download(m.encode("utf-8"), "study_protocol_v165.md"),
        ).props("flat outline")
    except Exception:
        pass


def _render_repro_lock(session: DesignSession) -> None:
    art, _ = _run_artifact_picker(session)
    if not isinstance(art, dict):
        return

    tol_default = json.dumps(
        {
            "min_margin_abs": 1e-8,
            "constraint_margin_abs": 1e-6,
            "metric_rel": 1e-6,
            "metric_abs": 1e-9,
        },
        indent=2,
    )
    tol_area = ui.textarea("Tolerances JSON", value=session.cr_repro_tol_json or tol_default).classes("w-full").props(
        "rows=6"
    )

    async def _create_lock() -> None:
        runs = list_session_run_artifacts(session)
        art_local = next((r["artifact"] for r in runs if r["id"] == session.cr_selected_run_id), runs[-1]["artifact"])
        try:
            tol = json.loads(str(tol_area.value or "{}"))
        except json.JSONDecodeError as exc:
            ui.notify(f"Invalid tolerances JSON: {exc}", type="negative")
            return
        try:
            lock = await run.io_bound(
                build_repro_lock,
                art_local,
                {"tolerances": tol, "notes": []},
            )
            session.cr_repro_lock_last = lock
            sha = ((lock.get("payload") or {}).get("integrity") or {}).get("lock_sha256", "")
            ui.notify(f"Lock created — SHA {str(sha)[:12]}…", type="positive")
            _lock_dl.refresh()
        except Exception as exc:
            ui.notify(f"Lock failed: {exc}", type="negative")

    ui.button("Create repro lock", icon="lock", on_click=_create_lock).props("outline")

    async def _replay() -> None:
        lock = session.cr_repro_lock_last
        if not isinstance(lock, dict) or lock.get("kind") != "shams_repro_lock":
            ui.notify("Create or upload a lock first", type="warning")
            return
        try:
            rep = await run.io_bound(replay_check, lock, {})
            session.cr_replay_report_last = rep
            ok = (rep.get("payload") or {}).get("ok")
            ui.notify("Replay OK" if ok else "Replay NOT OK", type="positive" if ok else "warning")
            _replay_view.refresh()
        except Exception as exc:
            ui.notify(f"Replay failed: {exc}", type="negative")

    ui.button("Run replay check", icon="replay", on_click=_replay).props("outline flat")
    _lock_dl(session)
    _replay_view(session)


@ui.refreshable
def _lock_dl(session: DesignSession) -> None:
    lock = session.cr_repro_lock_last
    if isinstance(lock, dict):
        ui.button(
            "Download repro_lock_v166.json",
            icon="download",
            on_click=lambda: ui.download(report_to_json_bytes(lock), "repro_lock_v166.json"),
        ).props("flat outline q-mt-sm")


@ui.refreshable
def _replay_view(session: DesignSession) -> None:
    rep = session.cr_replay_report_last
    if isinstance(rep, dict):
        with ui.expansion("Replay report", icon="fact_check").classes("w-full"):
            render_json_blob((rep.get("payload") or {}).get("checks") or rep)


def _render_authority_citation(session: DesignSession) -> None:
    art, _ = _run_artifact_picker(session)
    if not isinstance(art, dict):
        return

    async def _authority_zip() -> None:
        runs = list_session_run_artifacts(session)
        art_local = next((r["artifact"] for r in runs if r["id"] == session.cr_selected_run_id), runs[-1]["artifact"])
        try:
            data = await run.io_bound(
                build_authority_pack_zip,
                run_artifact=art_local,
                protocol=session.cr_study_protocol_last,
                lock=session.cr_repro_lock_last,
                replay=session.cr_replay_report_last,
            )
            session.cr_authority_pack_bytes = data
            ui.notify("Authority pack ZIP ready", type="positive")
            _auth_dl.refresh()
        except Exception as exc:
            ui.notify(f"Authority pack failed: {exc}", type="negative")

    ui.button("Build Authority Pack ZIP", icon="folder_zip", on_click=_authority_zip).props("outline")
    _auth_dl(session)

    ui.separator().classes("q-my-md")
    ui.label("Citation bundle (requires study protocol)").classes("text-subtitle2")

    async def _citation() -> None:
        prot = session.cr_study_protocol_last
        if not isinstance(prot, dict) or prot.get("kind") != "shams_study_protocol":
            ui.notify("Generate study protocol first", type="warning")
            return
        meta = {
            "title": session.cr_citation_title or None,
            "repository": session.cr_citation_repo or None,
            "doi": session.cr_citation_doi or None,
            "authors": [{"name": session.cr_citation_author or "SHAMS Contributors"}],
        }
        try:
            res = await run.io_bound(
                build_citation_bundle,
                prot,
                lock=session.cr_repro_lock_last,
                metadata=meta,
            )
            session.cr_citation_last = res
            ui.notify("Citation bundle generated", type="positive")
            _cite_dl.refresh()
        except Exception as exc:
            ui.notify(f"Citation failed: {exc}", type="negative")

    ui.button("Generate Citation Bundle", icon="menu_book", on_click=_citation).props("outline")
    _cite_dl(session)


@ui.refreshable
def _auth_dl(session: DesignSession) -> None:
    data = session.cr_authority_pack_bytes
    if isinstance(data, (bytes, bytearray)) and len(data) > 100:
        ui.button(
            "Download authority_pack_v167.zip",
            icon="download",
            on_click=lambda: ui.download(bytes(data), "authority_pack_v167.zip"),
        ).props("flat outline q-mt-sm")


@ui.refreshable
def _cite_dl(session: DesignSession) -> None:
    res = session.cr_citation_last
    if not isinstance(res, dict):
        return
    payload = res.get("payload") or {}
    ui.button(
        "Download citation_bundle_v168.json",
        icon="download",
        on_click=lambda: ui.download(report_to_json_bytes(res), "citation_bundle_v168.json"),
    ).props("flat outline")
    cff = payload.get("citation_cff_text", "")
    if cff:
        ui.button(
            "Download CITATION.cff",
            icon="download",
            on_click=lambda: ui.download(str(cff).encode("utf-8"), "CITATION.cff"),
        ).props("flat outline")
    bib = payload.get("bibtex_text", "")
    if bib:
        ui.button(
            "Download study_citation.bib",
            icon="download",
            on_click=lambda: ui.download(str(bib).encode("utf-8"), "study_citation_v168.bib"),
        ).props("flat outline")


def _render_studies_manager(session: DesignSession) -> None:
    ui.label("Save and organize point-design studies as JSON.").classes("text-caption")

    def _save() -> None:
        save_point_study(session)
        ui.notify("Saved current Point Designer inputs as study", type="positive")
        _studies_table.refresh()

    ui.button("Save current PointInputs as study", icon="save", on_click=_save).props("outline")

    async def _import_studies(e) -> None:
        try:
            imported = json.loads(e.content.read().decode("utf-8"))
            studies = list(session.cr_studies or [])
            if isinstance(imported, list):
                studies.extend(imported)
            elif isinstance(imported, dict):
                studies.append(imported)
            session.cr_studies = studies
            ui.notify("Studies imported", type="positive")
            _studies_table.refresh()
        except Exception as exc:
            ui.notify(f"Import failed: {exc}", type="negative")

    ui.upload(on_upload=_import_studies).props('accept=".json" auto-upload label="Import studies JSON"')

    data = report_to_json_bytes(list(session.cr_studies or []))
    ui.button(
        "Download studies JSON",
        icon="download",
        on_click=lambda: ui.download(data, "shams_studies.json"),
    ).props("flat outline")

    _studies_table(session)


@ui.refreshable
def _studies_table(session: DesignSession) -> None:
    studies = session.cr_studies or []
    if not studies:
        ui.label("No studies saved yet.").classes("text-caption text-grey q-mt-sm")
        return
    rows = [
        {"i": i, "type": s.get("type", "?"), "created": s.get("created", ""), "notes": s.get("notes", "")}
        for i, s in enumerate(studies)
        if isinstance(s, dict)
    ]
    ui.table(
        columns=[
            {"name": "i", "label": "#", "field": "i"},
            {"name": "type", "label": "Type", "field": "type"},
            {"name": "created", "label": "Created", "field": "created", "align": "left"},
            {"name": "notes", "label": "Notes", "field": "notes", "align": "left"},
        ],
        rows=rows,
        row_key="i",
    ).classes("w-full q-mt-sm")


def _render_regression_viewer(session: DesignSession) -> None:
    ui.label("Compare two artifacts or run the repo regression suite.").classes("text-caption q-mb-sm")

    blob_a: dict = {}
    blob_b: dict = {}

    async def _up_a(e) -> None:
        blob_a.clear()
        blob_a.update(json.loads(e.content.read().decode("utf-8")))

    async def _up_b(e) -> None:
        blob_b.clear()
        blob_b.update(json.loads(e.content.read().decode("utf-8")))

    with ui.row().classes("w-full gap-4"):
        ui.upload(on_upload=_up_a).props('accept=".json" auto-upload label="Artifact A"').classes("flex-1")
        ui.upload(on_upload=_up_b).props('accept=".json" auto-upload label="Artifact B"').classes("flex-1")

    def _diff() -> None:
        if not blob_a or not blob_b:
            ui.notify("Upload both artifacts", type="warning")
            return
        session.cr_regression_diff = regression_artifact_diff(blob_a, blob_b)
        _reg_diff.refresh()

    ui.button("Compare artifacts", icon="compare", on_click=_diff).props("outline")

    async def _repo_regress() -> None:
        ui.notify("Running repo regression suite…", type="info")
        try:
            rep = await run.io_bound(run_repo_regression)
            session.cr_repo_regression_last = rep
            ui.notify("Regression suite complete", type="positive")
            _repo_reg.refresh()
        except Exception as exc:
            ui.notify(f"Regression suite failed: {exc}", type="negative")

    ui.button("Run repo regression suite", icon="science", on_click=_repo_regress).props("flat outline")
    _reg_diff(session)
    _repo_reg(session)


@ui.refreshable
def _reg_diff(session: DesignSession) -> None:
    d = session.cr_regression_diff
    if not isinstance(d, dict):
        return
    kpi_rows = d.get("kpi_rows") or []
    if kpi_rows:
        ui.label("KPI diff").classes("text-subtitle2")
        ui.table(
            columns=[
                {"name": "kpi", "label": "KPI", "field": "kpi", "align": "left"},
                {"name": "value_A", "label": "A", "field": "value_A"},
                {"name": "value_B", "label": "B", "field": "value_B"},
                {"name": "delta", "label": "Δ", "field": "delta"},
            ],
            rows=kpi_rows,
            row_key="kpi",
        ).classes("w-full")
    new_f = d.get("new_failures") or []
    if new_f:
        ui.label("New failures in B").classes("text-subtitle2 q-mt-sm")
        ui.table(
            columns=[
                {"name": "name", "label": "Constraint", "field": "name", "align": "left"},
                {"name": "margin_A", "label": "Margin A", "field": "margin_A"},
                {"name": "margin_B", "label": "Margin B", "field": "margin_B"},
            ],
            rows=new_f,
            row_key="name",
        ).classes("w-full")


@ui.refreshable
def _repo_reg(session: DesignSession) -> None:
    rep = session.cr_repo_regression_last
    if isinstance(rep, dict):
        with ui.expansion("Repo regression report", icon="bug_report").classes("w-full"):
            render_json_blob(rep)
