"""Export evaluation bundle (JSON + SHA-256 + PDF) — includes forensics when present."""



from __future__ import annotations



import json



from nicegui import ui



from ui.export_bundle import build_export_bundle, bundle_json_bytes

from ui_nicegui.lib.pd_solver_helpers import build_summary_pdf_bytes

from ui_nicegui.session import DesignSession





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



    bundle = build_export_bundle(

        deck="Point Designer",

        outputs=out,

        inputs=art.get("inputs") if isinstance(art, dict) else session.inputs,

        constraints=art.get("constraints") if isinstance(art, dict) else None,

        extra=extra or None,

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

                json.dumps(art, indent=2, sort_keys=True, default=str).encode("utf-8"),

                "shams_run_artifact.json",

            ),

        ).props("flat q-mt-xs")



    pdf_bytes = session.pd_last_summary_pdf_bytes

    if not pdf_bytes and isinstance(art, dict) and art.get("outputs"):

        pdf_bytes = build_summary_pdf_bytes(art)

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


