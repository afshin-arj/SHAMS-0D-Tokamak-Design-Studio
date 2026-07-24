"""Reactor Design Forge verdict dashboard."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row


def render_forge_dashboard(summary: dict | None) -> None:
    ui.label("Forge Status").classes("text-subtitle1")
    if not isinstance(summary, dict) or not summary.get("loaded"):
        empty_state(
            "No compiled candidate yet. Use Intent Compiler to propose a candidate, then audit with frozen truth.",
            kind="info",
        )
        return
    from ui_nicegui.components.verdict_banner import verdict_banner

    # Machine Finder archive occupancy must never paint as L0 Verdict: FEASIBLE.
    if summary.get("workbench_loaded"):
        n_ok = summary.get("n_feasible_archive")
        n_all = summary.get("n_archive")
        frac = ""
        if isinstance(n_ok, (int, float)) and isinstance(n_all, (int, float)) and float(n_all) > 0:
            frac = f"{100.0 * float(n_ok) / float(n_all):.0f}% blocking-OK"
        posture = str(summary.get("screening_posture") or "ARCHIVE SCREENING")
        detail = (
            "Machine Finder archive occupancy — NOT Point Designer L0 FEASIBLE/INFEASIBLE. "
            f"{summary.get('audit_verdict', '-')} · "
            f"{frac + ' · ' if frac else ''}"
            f"Dominant: {summary.get('dominant', '-')}"
        )
        if "l0_audit_feasible" in summary:
            detail += (
                f" · Prior L0 Intent audit: "
                f"{'FEASIBLE' if summary.get('l0_audit_feasible') else 'INFEASIBLE'}"
            )
        verdict_banner(posture, detail=detail, title_prefix="Forge screening posture")
        kpi_row([
            ("Compiler", summary.get("compiler_status", "-")),
            ("Archive screening", summary.get("audit_verdict", "-")),
            (
                "Blocking-OK archive",
                f"{n_ok}/{n_all}" if n_ok is not None and n_all is not None else "-",
            ),
            ("Dominant", summary.get("dominant", "-")),
        ])
        return

    if "audit_feasible" in summary:
        posture = "FEASIBLE" if summary.get("audit_feasible") else "INFEASIBLE"
        verdict_banner(
            posture,
            detail=(
                f"L0 Intent-compiler audit · Compiler: {summary.get('compiler_status', '-')} · "
                f"Audit: {summary.get('audit_verdict', '-')} · "
                f"Dominant: {summary.get('dominant', '-')}"
            ),
            title_prefix="L0 audit",
        )
    else:
        posture = "READY" if summary.get("loaded") else "UNKNOWN"
        verdict_banner(
            posture,
            detail=(
                f"Compiler: {summary.get('compiler_status', '-')} · "
                f"Audit: {summary.get('audit_verdict', '-')} · "
                f"Dominant: {summary.get('dominant', '-')}"
            ),
        )
    kpi_row([
        ("Compiler", summary.get("compiler_status", "-")),
        ("Audit verdict", summary.get("audit_verdict", "-")),
        ("Feasible", "yes" if summary.get("audit_feasible") else ("no" if "audit_feasible" in summary else "-")),
        ("Dominant", summary.get("dominant", "-")),
    ])
