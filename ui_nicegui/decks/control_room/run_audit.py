"""Control Room — run audit overlays (authority, decision, dominance, epoch)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.cr_artifacts_helpers import load_json_bytes
from ui_nicegui.lib.cr_governance_helpers import (
    authority_confidence_rows,
    authority_dominance_summary,
    decision_consequences_summary,
    design_confidence_class,
    epoch_feasibility_summary,
    pick_session_artifact,
)
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def render_run_audit(session: DesignSession) -> None:
    ui.label("Run audit overlays").classes("text-subtitle1")
    ui.label(
        "Trust ledger, decision posture, authority dominance, and epoch feasibility — "
        "post-processing only; frozen truth unchanged."
    ).classes("text-caption text-grey q-mb-sm")

    art = pick_session_artifact(session)
    if isinstance(art, dict):
        session.cr_selected_artifact = art
        _audit_body(session, art)
    else:
        empty_state("Upload an artifact or evaluate in Point Designer / Systems Mode.", kind="info")
        from ui_nicegui.components.deck_gate import pd_prerequisite_gate

        pd_prerequisite_gate("Open Point Designer to evaluate a point, then return for run audit.")

    async def _upload(e) -> None:
        try:
            art_local = load_json_bytes(e.content.read())
            session.cr_selected_artifact = art_local
            ui.notify("Artifact loaded", type="positive")
            _audit_body.refresh(session, art_local)
        except Exception as exc:
            ui.notify(f"Load failed: {exc}", type="negative")

    ui.upload(on_upload=_upload).props('accept=".json" auto-upload label="Upload shams_run_artifact.json"')


@ui.refreshable
def _audit_body(session: DesignSession, art: dict) -> None:
    dc = design_confidence_class(art)
    dc_sum = decision_consequences_summary(art)
    kpi_row([
        ("Design confidence", dc),
        ("Decision posture", str(dc_sum.get("decision_posture") or "-")),
        ("Dominant constraint", str(dc_sum.get("dominant_constraint") or "-")),
        ("Primary risk", str(dc_sum.get("primary_risk_driver") or "-")),
    ])

    ui.markdown(
        "**Legend:** A = authoritative/external · B = parametric · C = proxy · D = speculative · UNKNOWN = missing metadata"
    ).classes("text-caption q-mb-sm")

    with ui.expansion("Authority & confidence", icon="verified_user", value=True).classes("w-full"):
        rows = authority_confidence_rows(art)
        if rows:
            cols = list(rows[0].keys())
            ui.table(
                columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in cols],
                rows=rows,
                row_key="subsystem",
            ).classes("w-full")
        else:
            ui.label("No authority_confidence block in artifact.").classes("text-grey")

    with ui.expansion("Decision consequences", icon="gavel").classes("w-full"):
        dc_sum = decision_consequences_summary(art)
        if dc_sum:
            for k, v in dc_sum.items():
                if v is not None:
                    ui.label(f"{k}: {v}").classes("text-body2")
        else:
            ui.label("No decision_consequences block.").classes("text-grey")

    with ui.expansion("Authority dominance", icon="leaderboard").classes("w-full"):
        dom = authority_dominance_summary(art)
        if dom:
            if dom.get("dominant_authority"):
                ui.label(f"Dominant authority: {dom['dominant_authority']}").classes("text-subtitle2")
            ranking = dom.get("ranking") or []
            if ranking:
                render_json_blob(ranking)
            top = dom.get("top_limiting") or []
            if top:
                ui.label("Top limiting").classes("text-caption")
                render_json_blob(top)
        else:
            ui.label("No authority_dominance block.").classes("text-grey")

    with ui.expansion("Epoch feasibility", icon="timeline").classes("w-full"):
        ef = epoch_feasibility_summary(art)
        if ef:
            if ef.get("overall"):
                ui.label(f"Overall: {ef['overall']}").classes("text-subtitle2")
            epochs = ef.get("epochs") or []
            if epochs:
                ui.table(
                    columns=[
                        {"name": "epoch", "label": "epoch", "field": "epoch", "align": "left"},
                        {"name": "verdict", "label": "verdict", "field": "verdict", "align": "left"},
                    ],
                    rows=epochs,
                    row_key="epoch",
                ).classes("w-full")
        else:
            ui.label("No epoch_feasibility block.").classes("text-grey")

    if session.cr_expert_view:
        for block, label in (
            ("fidelity_tiers", "Fidelity tiers"),
            ("regime_transitions", "Regime transitions"),
            ("coupling_narratives", "Coupling narratives"),
            ("nonfeasibility_certificate", "Non-feasibility certificate"),
            ("verification_checks", "Verification checks"),
        ):
            payload = art.get(block)
            if payload:
                with ui.expansion(label, icon="science").classes("w-full"):
                    render_json_blob(payload)
