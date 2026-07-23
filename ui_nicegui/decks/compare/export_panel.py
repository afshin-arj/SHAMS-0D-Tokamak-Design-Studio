"""Compare deck — export markdown and JSON bundles + outbound handoffs."""
from __future__ import annotations

import json

from nicegui import ui

from ui_nicegui.lib.compare_helpers import (
    apply_artifact_inputs,
    comparison_json_bundle,
    comparison_markdown,
)
from ui_nicegui.lib.pd_handoff import navigate_to_point_designer
from ui_nicegui.session import DesignSession


def render_export_panel(session: DesignSession, art_a: dict, art_b: dict) -> None:
    ui.label("Export comparison").classes("text-subtitle2")
    ui.label(
        "Markdown for human review; JSON bundle for CI, Control Room, or archival replay."
    ).classes("text-caption text-grey q-mb-sm")

    md = comparison_markdown(art_a, art_b).encode("utf-8")
    bundle = json.dumps(comparison_json_bundle(art_a, art_b), indent=2, default=str).encode("utf-8")

    with ui.row().classes("gap-2"):
        ui.button(
            "Download markdown",
            icon="download",
            on_click=lambda: ui.download(md, "artifact_comparison.md"),
        ).props("outline")
        ui.button(
            "Download JSON bundle",
            icon="download",
            on_click=lambda: ui.download(bundle, "artifact_comparison.json"),
        ).props("outline color=primary")

    ui.separator().classes("q-my-sm")
    ui.label("Outbound handoffs").classes("text-subtitle2")
    ui.label(
        "Apply variant (B) or baseline (A) inputs to Point Designer for re-evaluation with frozen truth."
    ).classes("text-caption text-grey q-mb-sm")

    from ui_nicegui.lib.compare_helpers import normalize_compare_artifact
    from ui_nicegui.lib.verdict_core import verdict_summary

    feas_a = bool(
        verdict_summary(normalize_compare_artifact(art_a).get("outputs") or {}).get("feasible")
    )
    feas_b = bool(
        verdict_summary(normalize_compare_artifact(art_b).get("outputs") or {}).get("feasible")
    )
    if not feas_a or not feas_b:
        ui.label(
            "One or both slots are INFEASIBLE — Apply is a diagnostic seed handoff; "
            "prior KPIs are cleared; Evaluate Point to re-certify."
        ).classes("text-caption text-orange q-mb-xs")

    def _apply(slot_art: dict, label: str, *, feasible: bool) -> None:
        n = apply_artifact_inputs(session, slot_art)
        if n:
            try:
                from ui_nicegui.lib.navigation import refresh_helm, refresh_status

                refresh_helm()
                refresh_status()
            except Exception:
                pass
            navigate_to_point_designer(session)
            if feasible:
                ui.notify(
                    f"Applied {n} input fields from slot {label} — "
                    "prior KPIs cleared; Evaluate Point to re-certify.",
                    type="warning",
                )
            else:
                ui.notify(
                    f"Applied {n} diagnostic (INFEASIBLE) fields from slot {label} — "
                    "prior KPIs cleared; Evaluate Point to re-certify.",
                    type="warning",
                )
        else:
            ui.notify(f"No overlapping inputs copied from slot {label}.", type="warning")

    with ui.row().classes("gap-2 flex-wrap"):
        a_props = "outline" if feas_a else "outline color=orange"
        b_props = "outline color=primary" if feas_b else "outline color=orange"
        ui.button(
            "Apply slot A → Point Designer" + ("" if feas_a else " (diagnostic)"),
            icon="input",
            on_click=lambda: _apply(art_a, "A", feasible=feas_a),
        ).props(a_props)
        ui.button(
            "Apply slot B → Point Designer" + ("" if feas_b else " (diagnostic)"),
            icon="input",
            on_click=lambda: _apply(art_b, "B", feasible=feas_b),
        ).props(b_props)
