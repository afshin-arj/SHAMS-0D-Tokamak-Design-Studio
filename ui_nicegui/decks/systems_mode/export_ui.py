"""Systems Mode — Export bundle (Phase 12 + PDF parity)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional

from nicegui import run, ui

from ui_nicegui.lib.systems_artifact import fetch_systems_artifact
from ui_nicegui.lib.systems_ranking_helpers import rank_candidates
from ui_nicegui.lib.systems_workflow_helpers import collect_candidates, systems_export_bytes
from ui_nicegui.session import DesignSession


def _watermark_candidate_row(c: Any) -> Any:
    """PHYS-KPI-001: watermark headline/metrics on infeasible candidates."""
    if not isinstance(c, Mapping):
        return c
    from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_claim_kpi_map

    cc: Dict[str, Any] = dict(c)
    feas = bool(cc.get("feasible", cc.get("is_feasible", cc.get("hard_feasible", True))))
    if str(cc.get("verdict") or "").upper() in ("FAIL", "INFEASIBLE", "REJECTED"):
        feas = False
    if feas:
        return cc
    if isinstance(cc.get("headline"), Mapping):
        cc["headline"] = watermark_claim_kpi_map(cc["headline"], feasible=False)
    if isinstance(cc.get("metrics"), Mapping):
        cc["metrics"] = watermark_claim_kpi_map(cc["metrics"], feasible=False)
    return cc


def _watermark_candidates(cands: Optional[List[Any]]) -> List[Any]:
    return [_watermark_candidate_row(c) for c in (cands or [])]


def render_export_panel(session: DesignSession) -> None:
    ui.label("Export").classes("text-subtitle1")
    ui.label(
        "Download Systems workflow bundle, solve artifact, decision journal, and audit PDFs."
    ).classes("text-caption q-mb-sm")
    ui.label(
        "PHYS-KPI-001: claim KPIs on INFEASIBLE solve / candidates are — (diagnostic) in PDF/JSON exports."
    ).classes("text-caption text-grey q-mb-sm")

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
        from ui_nicegui.lib.cr_artifacts_helpers import watermark_run_artifact_export

        art = fetch_systems_artifact(session)
        if isinstance(art, dict):
            art = watermark_run_artifact_export(art)
        pd_art = session.pd_last_artifact
        if isinstance(pd_art, dict):
            pd_art = watermark_run_artifact_export(pd_art)
        cands = rank_candidates(collect_candidates(session), session.systems_ranking_profile)
        top = _watermark_candidates(rank_candidates(cands, session.systems_ranking_profile)[:10])

        def _build():
            return build_decision_report_pdf_bytes(
                systems_artifact=art if isinstance(art, dict) else None,
                point_artifact=pd_art if isinstance(pd_art, dict) else None,
                journal=list(session.systems_journal or []),
                top_candidates=top,
            )

        pdf = await run.io_bound(_build)
        ui.download(pdf, "shams_systems_decision_report.pdf")

    async def _exec_pdf() -> None:
        try:
            from tools.reports.executive_summary import build_executive_summary_pdf_bytes
        except ImportError:
            ui.notify("Executive summary module unavailable", type="negative")
            return
        from ui_nicegui.lib.cr_artifacts_helpers import watermark_run_artifact_export

        art = fetch_systems_artifact(session)
        if isinstance(art, dict):
            art = watermark_run_artifact_export(art)
        pd_art = session.pd_last_artifact
        if isinstance(pd_art, dict):
            pd_art = watermark_run_artifact_export(pd_art)
        ranked = rank_candidates(collect_candidates(session), session.systems_ranking_profile)
        top = _watermark_candidate_row(ranked[0]) if ranked else None

        def _build():
            return build_executive_summary_pdf_bytes(
                systems_artifact=art if isinstance(art, dict) else None,
                point_artifact=pd_art if isinstance(pd_art, dict) else None,
                top_candidate=top,
            )

        pdf = await run.io_bound(_build)
        ui.download(pdf, "shams_systems_executive_summary.pdf")

    with ui.row().classes("gap-2 q-mt-sm"):
        ui.button("Decision Report (PDF)", icon="picture_as_pdf", on_click=_decision_pdf).props("outline")
        ui.button("Executive Summary (PDF)", icon="picture_as_pdf", on_click=_exec_pdf).props("outline")
