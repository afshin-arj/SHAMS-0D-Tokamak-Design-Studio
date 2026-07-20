"""Scan Lab export & archive — artifacts, atlases, families, restore, freeze QA."""
from __future__ import annotations

import json
from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.lib.scan_archive_helpers import (
    append_scan_library_entry,
    artifact_json_bytes,
    boundaries_json_bytes,
    build_signature_atlas,
    build_summary_pdf,
    compute_repo_fingerprints,
    field_cube_json_bytes,
    restore_scan_artifact,
    run_replay_determinism_audit,
)
from ui_nicegui.lib.scan_helpers import report_to_json_bytes
from ui_nicegui.lib.scan_workbench_helpers import (
    build_atlas_pdf_bytes,
    build_design_families,
    certify_design_families,
    design_family_table_rows,
    dominance_map_png_bytes,
    families_json_bytes,
)
from ui_nicegui.session import DesignSession


def render_export_tab(
    session: DesignSession,
    rep: Optional[dict],
    *,
    on_restore: Optional[Callable[[], None]] = None,
) -> None:
    ui.label("Trust & provenance").classes("text-subtitle1")
    fps = compute_repo_fingerprints()
    if fps:
        ui.label(f"Repo fingerprint: {fps.get('fingerprint', 'n/a')}").classes("text-caption")
    else:
        ui.label("Fingerprints unavailable.").classes("text-caption text-grey")

    ui.separator().classes("q-my-sm")
    _render_restore(session, on_restore)
    ui.separator().classes("q-my-sm")

    if not isinstance(rep, dict):
        ui.label("Run a cartography scan to unlock export bundles.").classes("text-caption text-grey")
        return

    intents = list(rep.get("intents") or session.scan_cart_intents or ["Reactor"])
    _render_downloads(session, rep, intents)
    ui.separator().classes("q-my-sm")
    _render_atlases(session, rep, intents)
    ui.separator().classes("q-my-sm")
    _render_design_families(session, rep, intents)
    ui.separator().classes("q-my-sm")
    _render_library_save(session, rep)
    ui.separator().classes("q-my-sm")
    _render_freeze_qa(session)


def _render_restore(session: DesignSession, on_restore: Optional[Callable[[], None]]) -> None:
    with ui.expansion("Restore scan artifact (JSON)", icon="upload_file", value=False).classes("w-full"):
        ui.label("Upload a previously exported scan artifact to restore scan state.").classes(
            "text-caption q-mb-sm"
        )

        async def _handle_upload(e) -> None:
            try:
                raw = e.content.read() if hasattr(e.content, "read") else e.content
                payload = json.loads(raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw)
                updates = await run.io_bound(restore_scan_artifact, payload)
                for k, v in updates.items():
                    setattr(session, k, v)
                ui.notify("Restored Scan Lab state from artifact.", type="positive")
                if on_restore:
                    on_restore()
            except Exception as exc:
                ui.notify(f"Restore failed: {exc}", type="negative")

        ui.upload(on_upload=_handle_upload, auto_upload=True).props("accept=.json").classes("w-full")


def _render_downloads(session: DesignSession, rep: dict, intents: list) -> None:
    ui.label("JSON exports").classes("text-subtitle2")
    ui.markdown(
        f"- n_points: **{rep.get('n_points')}**\n"
        f"- run_seconds: **{rep.get('run_seconds', '-')}**\n"
        f"- report_id: **{rep.get('id', '-')}**\n"
        f"- shams_version: **{rep.get('shams_version', '-')}**"
    ).classes("text-body2 q-mb-sm")
    with ui.row().classes("gap-2 flex-wrap"):
        ui.button(
            "Cartography report (JSON)",
            icon="download",
            on_click=lambda: ui.download(report_to_json_bytes(rep), "shams_cartography_report.json"),
        ).props("outline")
        art = session.scan_cartography_artifact
        if isinstance(art, dict):
            ui.button(
                "Scan artifact v1 (JSON)",
                icon="download",
                on_click=lambda a=art: ui.download(artifact_json_bytes(a), "shams_scan_artifact_v1.json"),
            ).props("outline")
        bnd = boundaries_json_bytes(rep)
        if bnd:
            ui.button(
                "Boundaries segments (JSON)",
                icon="download",
                on_click=lambda b=bnd: ui.download(b, "shams_scan_boundaries_segments.json"),
            ).props("outline")
        fc = field_cube_json_bytes(rep)
        if fc:
            ui.button(
                "Field cube (JSON)",
                icon="download",
                on_click=lambda f=fc: ui.download(f, "shams_scan_field_cube_v1.json"),
            ).props("outline")
        for it in intents:
            ui.button(
                f"Summary PDF — {it}",
                icon="picture_as_pdf",
                on_click=lambda r=rep, intent=it: _dl_summary(r, intent),
            ).props("flat outline")


def _dl_summary(rep: dict, intent: str) -> None:
    pdf = build_summary_pdf(rep, intent)
    if pdf:
        ui.download(pdf, f"shams_scan_summary_{intent}.pdf")
    else:
        ui.notify("Summary PDF unavailable.", type="warning")


def _render_atlases(session: DesignSession, rep: dict, intents: list) -> None:
    ui.label("Atlas exports (PDF)").classes("text-subtitle2")
    ui.input(
        "Reference atlas title",
        value=session.scan_atlas_title,
        on_change=lambda e: setattr(session, "scan_atlas_title", str(e.value or "")),
    ).classes("w-full")
    ui.input(
        "Signature atlas title",
        value=session.scan_signature_atlas_title,
        on_change=lambda e: setattr(session, "scan_signature_atlas_title", str(e.value or "")),
    ).classes("w-full")

    async def _ref_atlas() -> None:
        ui.notify("Building reference atlas…", type="info")
        try:
            pdf = await run.io_bound(
                build_atlas_pdf_bytes,
                rep,
                intents,
                title=session.scan_atlas_title or "SHAMS — Scan Lab Atlas",
            )
            session.scan_atlas_pdf_bytes = pdf
            _atlas_dl.refresh()
            ui.notify("Reference atlas ready.", type="positive")
        except Exception as exc:
            ui.notify(str(exc), type="negative")

    async def _sig_atlas() -> None:
        ui.notify("Building signature atlas (10 pages)…", type="info")
        try:
            maps = {str(it): dominance_map_png_bytes(rep, str(it)) for it in intents}
            split_png = None
            try:
                from ui_nicegui.lib.scan_deep_viz_helpers import intent_split_png_bytes

                split_png = intent_split_png_bytes(rep)
            except Exception:
                pass
            pdf = await run.io_bound(
                build_signature_atlas,
                rep,
                title=session.scan_signature_atlas_title,
                map_png_by_intent=maps,
                intent_split_png=split_png,
                claim=session.scan_claim_last,
            )
            session.scan_signature_atlas_pdf_bytes = pdf
            _atlas_dl.refresh()
            ui.notify("Signature atlas ready.", type="positive")
        except Exception as exc:
            ui.notify(str(exc), type="negative")

    with ui.row().classes("gap-2"):
        ui.button("Build reference atlas", icon="picture_as_pdf", on_click=_ref_atlas).props("outline")
        ui.button("Build signature atlas (10 pp)", icon="collections", on_click=_sig_atlas).props("outline")
    _atlas_dl(session)


@ui.refreshable
def _atlas_dl(session: DesignSession) -> None:
    ref = session.scan_atlas_pdf_bytes
    sig = session.scan_signature_atlas_pdf_bytes
    with ui.row().classes("gap-2 q-mt-sm"):
        if isinstance(ref, (bytes, bytearray)) and len(ref) > 100:
            ui.button(
                "Download reference atlas",
                icon="download",
                on_click=lambda: ui.download(bytes(ref), "shams_scan_atlas.pdf"),
            ).props("flat")
        if isinstance(sig, (bytes, bytearray)) and len(sig) > 100:
            ui.button(
                "Download signature atlas",
                icon="download",
                on_click=lambda: ui.download(bytes(sig), "shams_scan_signature_atlas.pdf"),
            ).props("flat color=primary")


def _render_design_families(session: DesignSession, rep: dict, intents: list) -> None:
    ui.label("Design family clustering").classes("text-subtitle2")
    ui.label(
        "Deterministic families from cartography (regime-signature labeling + connected components)."
    ).classes("text-caption q-mb-sm")
    it_sel = session.scan_df_intent if session.scan_df_intent in intents else str(intents[0])
    ui.select(
        intents,
        label="Intent lens",
        value=it_sel,
        on_change=lambda e: setattr(session, "scan_df_intent", str(e.value)),
    ).props("dense").classes("w-full")
    ui.slider(
        min=4,
        max=80,
        step=1,
        value=session.scan_df_min_points,
        on_change=lambda e: setattr(session, "scan_df_min_points", int(e.value)),
    ).props("label").classes("w-full")
    ui.label(f"Minimum points per family: {session.scan_df_min_points}").classes("text-caption")

    async def _build() -> None:
        ui.notify("Building design families…", type="info")
        try:
            art = await run.io_bound(
                build_design_families,
                rep,
                intent=str(session.scan_df_intent or it_sel),
                min_points=int(session.scan_df_min_points),
            )
            session.scan_design_families_v394 = art
            session.scan_design_families_v394_cert = certify_design_families(art)
            _fam_table.refresh()
            ui.notify(f"Built {len(art.get('families') or [])} families.", type="positive")
        except Exception as exc:
            ui.notify(f"Family build failed: {exc}", type="negative")

    with ui.row().classes("gap-2"):
        ui.button("Build families", icon="hub", on_click=_build).props("outline")
        ui.button(
            "Clear",
            on_click=lambda: (
                setattr(session, "scan_design_families_v394", None),
                setattr(session, "scan_design_families_v394_cert", None),
                _fam_table.refresh(),
            ),
        ).props("flat")

    _fam_table(session)


@ui.refreshable
def _fam_table(session: DesignSession) -> None:
    art = session.scan_design_families_v394
    if not isinstance(art, dict) or art.get("families") is None:
        ui.label("No family artifact yet.").classes("text-caption text-grey q-mt-sm")
        return
    cert = session.scan_design_families_v394_cert
    if isinstance(cert, dict):
        ui.label(f"Certification: {cert.get('verdict', 'UNKNOWN')}").classes("text-caption")
    rows = design_family_table_rows(art)
    if rows:
        ui.table(
            columns=[
                {"name": "family_id", "label": "ID", "field": "family_id"},
                {"name": "label", "label": "Label", "field": "label", "align": "left"},
                {"name": "n_points", "label": "n", "field": "n_points"},
                {"name": "feasible_frac", "label": "Feasible frac", "field": "feasible_frac"},
            ],
            rows=rows,
            row_key="family_id",
        ).classes("w-full q-mt-sm")
    ui.button(
        "Download families JSON",
        icon="download",
        on_click=lambda: ui.download(families_json_bytes(art), "shams_scan_design_families.json"),
    ).props("outline flat q-mt-sm")


def _render_library_save(session: DesignSession, rep: dict) -> None:
    with ui.expansion("Curated scan library (local)", icon="bookmark").classes("w-full"):
        ui.input(
            "Tag",
            value=session.scan_lib_tag,
            on_change=lambda e: setattr(session, "scan_lib_tag", str(e.value or "")),
        ).classes("w-full")
        ui.textarea(
            "Why this scan mattered",
            value=session.scan_lib_note,
            on_change=lambda e: setattr(session, "scan_lib_note", str(e.value or "")),
        ).classes("w-full")

        def _save() -> None:
            try:
                path = append_scan_library_entry(
                    rep, tag=session.scan_lib_tag, note=session.scan_lib_note
                )
                ui.notify(f"Saved to {path}", type="positive")
            except Exception as exc:
                ui.notify(f"Save failed: {exc}", type="negative")

        ui.button("Save scan to library", icon="save", on_click=_save).props("outline")


def _render_freeze_qa(session: DesignSession) -> None:
    with ui.expansion("Freeze readiness (determinism replay)", icon="verified").classes("w-full"):
        ui.label("Validates determinism on a small neighborhood — does not change physics.").classes(
            "text-caption q-mb-sm"
        )

        async def _audit() -> None:
            from ui_nicegui.lib.navigation import refresh_helm, refresh_status
            from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status

            if session.scan_running:
                ui.notify("Scan Lab already running.", type="warning")
                return
            locked, task, is_owner = runlock_status("ScanLab")
            if locked and not is_owner:
                ui.notify(f"Run lock busy: {task or 'another task'}", type="warning")
                return
            if not runlock_acquire("Scan Lab: Replay audit", "ScanLab"):
                ui.notify("Run lock busy (another deck is evaluating).", type="warning")
                return
            session.scan_running = True
            refresh_status()
            refresh_helm()
            ui.notify("Running replay audit…", type="info")
            try:
                result = await run.io_bound(
                    run_replay_determinism_audit,
                    session.build_point_inputs(),
                    x_key=session.scan_cart_x_key,
                    y_key=session.scan_cart_y_key,
                    intents=list(session.scan_cart_intents or ["Reactor"]),
                )
                if result.get("pass"):
                    ui.notify("Replay determinism audit: PASS", type="positive")
                else:
                    ui.notify("Replay determinism audit: FAIL", type="negative")
                ui.code(json.dumps(result, indent=2), language="json").classes("w-full q-mt-sm")
            except Exception as exc:
                ui.notify(str(exc), type="negative")
            finally:
                session.scan_running = False
                runlock_release("ScanLab")
                refresh_status()
                refresh_helm()

        ui.button("Run quick replay audit", icon="replay", on_click=_audit).props("outline")
        ui.label("Full gate: python scripts/run_scanlab_freeze_qa.py").classes("text-caption text-grey q-mt-sm")
