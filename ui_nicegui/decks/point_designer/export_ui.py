"""Export evaluation bundle (JSON + SHA-256 + PDF) — includes forensics when present."""

from __future__ import annotations

import json

from nicegui import ui

from ui.export_bundle import build_export_bundle, bundle_json_bytes
from ui_nicegui.lib.cr_artifacts_helpers import watermark_run_artifact_export
from ui_nicegui.lib.pd_solver_helpers import build_summary_pdf_bytes
from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_claim_kpi_map
from ui_nicegui.lib.verdict_core import verdict_summary
from ui_nicegui.session import DesignSession


def _download_cite_shams_pack(art: dict) -> None:
    """Build and download the Cite-SHAMS handoff ZIP (Independence 4.2)."""
    try:
        try:
            from reports.cite_shams_handoff_pack import build_cite_shams_handoff_pack
        except ImportError:
            from src.reports.cite_shams_handoff_pack import build_cite_shams_handoff_pack
        pack = build_cite_shams_handoff_pack(watermark_run_artifact_export(art))
        ui.download(pack["zip_bytes"], pack.get("suggested_filename") or "shams_cite_handoff.zip")
        ui.notify("Cite-SHAMS handoff pack ready", type="positive")
    except Exception as exc:
        ui.notify(f"Cite-SHAMS pack failed: {exc}", type="negative")


def render_export(session: DesignSession) -> None:
    out = session.pd_last_outputs or session.last_eval
    if not out:
        return

    art = session.pd_last_artifact or {}
    extra: dict = {}
    studies: dict = {}
    if isinstance(art.get("studies"), dict):
        studies.update(art["studies"])
    ff = session.pd_last_forensics
    if isinstance(ff, dict) and ff and ff.get("status") != "error":
        studies.setdefault("feasibility_forensics", ff)
    if session.phase_envelopes_last:
        studies["phase_envelope"] = session.phase_envelopes_last
    if session.uq_contract_last:
        studies["uncertainty_contract"] = session.uq_contract_last
    if session.pd_solver_trace:
        studies["solver_trace"] = session.pd_solver_trace
    if studies:
        extra["studies"] = studies

    vs = verdict_summary(out if isinstance(out, dict) else {})
    feasible = bool(vs.get("feasible")) if vs.get("loaded") else True
    export_out = out
    if isinstance(out, dict) and not feasible:
        export_out = watermark_claim_kpi_map(out, feasible=False, point_out=out)
        extra = dict(extra)
        extra["phys_kpi_note"] = (
            "PHYS-KPI-001: claim KPIs on INFEASIBLE exports are — (diagnostic) — not design claims."
        )

    bundle = build_export_bundle(
        deck="Point Designer",
        outputs=export_out,
        inputs=art.get("inputs") if isinstance(art, dict) else session.inputs,
        constraints=art.get("constraints") if isinstance(art, dict) else None,
        extra=extra or None,
        design_intent=str(getattr(session, "design_intent", "") or "") or None,
        no_solution_atlas=art.get("no_solution_atlas") if isinstance(art, dict) else None,
    )

    ui.download(
        bundle_json_bytes(bundle),
        "shams_point_export.json",
        "Download evaluation bundle (JSON + SHA-256)",
    ).classes("q-mt-md")

    if isinstance(art, dict) and art.get("schema_version"):
        ui.button(
            "Download full run artifact JSON",
            icon="download",
            on_click=lambda: ui.download(
                json.dumps(watermark_run_artifact_export(art), indent=2, sort_keys=True, default=str).encode(
                    "utf-8"
                ),
                "shams_run_artifact.json",
            ),
        ).props("flat q-mt-xs")

        ui.button(
            "Download cite-SHAMS handoff pack",
            icon="folder_zip",
            on_click=lambda a=art: _download_cite_shams_pack(a),
        ).props("outline color=primary q-mt-sm")
        ui.label(
            "Bundles VERSION, PointInputs, artifact SHA-256, citation snippet, "
            "CONDITIONAL release gate, and NO-SOLUTION atlas when infeasible. "
            "PROCESS import optional — cite SHAMS alone for new studies."
        ).classes("text-caption text-grey-7 q-mt-xs")

    pdf_bytes = session.pd_last_summary_pdf_bytes
    if not pdf_bytes and isinstance(art, dict) and art.get("outputs"):
        pdf_src = watermark_run_artifact_export(art) if not feasible else art
        pdf_bytes = build_summary_pdf_bytes(pdf_src)
        if pdf_bytes:
            session.pd_last_summary_pdf_bytes = pdf_bytes

    if pdf_bytes:
        ui.download(
            pdf_bytes,
            "shams_summary.pdf",
            "Download summary PDF",
        ).classes("q-mt-sm")
    else:
        ui.label("PDF summary export unavailable for this point.").classes("text-caption q-mt-sm")
