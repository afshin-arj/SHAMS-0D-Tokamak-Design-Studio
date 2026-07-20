"""Scan Lab verdict-first banner."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.lib.scan_helpers import summarize_scan_report
from ui_nicegui.lib.scan_labels import ROBUSTNESS_GLOSSARY


def render_scan_verdict(rep: dict | None) -> None:
    if not isinstance(rep, dict):
        empty_state(
            "No cartography scan results yet. Run a scan on **Setup & Run** "
            "(requires a **Point Designer** baseline).",
            kind="info",
        )
        ui.button(
            "Open Point Designer",
            icon="design_services",
            on_click=lambda: switch_deck("Point Designer"),
        ).props("outline color=primary").classes("q-mt-sm")
        return
    summary = summarize_scan_report(rep)
    if not summary.get("loaded"):
        empty_state("Scan report could not be summarized.", kind="warn")
        return
    from ui_nicegui.components.verdict_banner import verdict_banner

    rob = str(summary.get("robustness") or "UNKNOWN")
    verdict_banner(
        rob,
        detail=(
            f"Dominant: {summary['dominant']} · "
            f"Feasible ({summary['intent']}): {summary['feasible_pct']} · "
            f"Cliffiness proxy: {summary['cliffiness']:.2f} "
            "(screening proxy — not UQ robustness)"
        ),
    )
    kpi_row([
        ("Dominant constraint", summary["dominant"]),
        (f"Feasible fraction ({summary['intent']})", summary["feasible_pct"]),
        ("2-D slice occupancy", summary["robustness"]),
        ("Cliffiness proxy", f"{summary['cliffiness']:.2f}"),
    ])
    rs = rep.get("run_seconds")
    if isinstance(rs, (int, float)):
        ui.label(
            f"Scan: {summary['x_key']} vs {summary['y_key']} · "
            f"{summary['n_points']} points · {float(rs):.1f} s"
        ).classes("text-caption text-grey q-mb-xs")
    with ui.expansion("Robustness terminology", icon="help_outline").classes("w-full q-mb-sm"):
        ui.markdown(ROBUSTNESS_GLOSSARY).classes("text-caption")
