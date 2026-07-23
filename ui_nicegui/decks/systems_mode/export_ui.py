"""Systems Mode — Export bundle (Phase 12 + PDF parity)."""

from __future__ import annotations

import json

from nicegui import run, ui

from ui_nicegui.lib.systems_artifact import fetch_systems_artifact
from ui_nicegui.lib.systems_ranking_helpers import rank_candidates
from ui_nicegui.lib.systems_workflow_helpers import collect_candidates, systems_export_bytes
from ui_nicegui.session import DesignSession


def render_export_panel(session: DesignSession) -> None:
    ui.label("Export").classes("text-subtitle1")
    ui.label(
        "Download Systems workflow bundle, solve artifact, decision journal, and audit PDFs."
    ).classes("text-caption q-mb-sm")

    n_cards = len(session.systems_run_cards or [])
    ui.label(f"Run cards recorded: {n_cards}").classes("text-caption")

    ui.button(
        "Download Systems bundle (JSON)",
        icon="download",
        on_click=lambda: ui.download(systems_export_bytes(session), "shams_systems_bundle.json"),
    ).props("outline")

    if isinstance(session.systems_last_solve_artifact, dict):
        from ui_nicegui.lib.cr_artifacts_helpers import watermark_run_artifact_export

        ui.button(
            "Download last solve artifact JSON",
            icon="download",
            on_click=lambda: ui.download(
                json.dumps(
                    watermark_run_artifact_export(session.systems_last_solve_artifact),
                    indent=2,
                    sort_keys=True,
                    default=str,
                ).encode("utf-8"),
                "shams_systems_solve_artifact.json",
            ),
        ).props("flat q-mt-xs")

    async def _decision_pdf() -> None:
        try:
            from tools.reports.decision_report import build_decision_report_pdf_bytes
        except ImportError:
            ui.notify("Decision report module unavailable", type="negative")
            return
        art = fetch_systems_artifact(session)
        cands = rank_candidates(collect_candidates(session), session.systems_ranking_profile)

        def _build():
            return build_decision_report_pdf_bytes(
                systems_artifact=art if isinstance(art, dict) else None,
                point_artifact=session.pd_last_artifact,
                journal=list(session.systems_journal or []),
                top_candidates=rank_candidates(cands, session.systems_ranking_profile)[:10],
            )

        pdf = await run.io_bound(_build)
        ui.download(pdf, "shams_systems_decision_report.pdf")

    async def _exec_pdf() -> None:
        try:
            from tools.reports.executive_summary import build_executive_summary_pdf_bytes
        except ImportError:
            ui.notify("Executive summary module unavailable", type="negative")
            return
        art = fetch_systems_artifact(session)
        ranked = rank_candidates(collect_candidates(session), session.systems_ranking_profile)

        def _build():
            return build_executive_summary_pdf_bytes(
                systems_artifact=art if isinstance(art, dict) else None,
                point_artifact=session.pd_last_artifact,
                top_candidate=ranked[0] if ranked else None,
            )

        pdf = await run.io_bound(_build)
        ui.download(pdf, "shams_systems_executive_summary.pdf")

    with ui.row().classes("gap-2 q-mt-sm"):
        ui.button("Decision Report (PDF)", icon="picture_as_pdf", on_click=_decision_pdf).props("outline")
        ui.button("Executive Summary (PDF)", icon="picture_as_pdf", on_click=_exec_pdf).props("outline")
