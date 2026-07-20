"""Plot Deck — quick-look matplotlib visuals."""
from __future__ import annotations

import base64

from nicegui import ui

from ui_nicegui.lib.pd_parity_helpers import PLOT_PHYSICAL_MEANING, v396_scaling_rows, v397_profile_summary
from ui_nicegui.lib.pd_plot_helpers import (
    plot_confinement,
    plot_engineering_severity,
    plot_geometry_build,
    plot_power_balance_bars,
    plot_power_stack,
    plot_regime_dials,
    plot_stability_limits,
    plot_tight_constraints,
)
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def _show_png(data: bytes | None, *, caption: str) -> None:
    if not data:
        ui.label(caption).classes("text-caption text-grey")
        return
    ui.image(f"data:image/png;base64,{base64.b64encode(data).decode('ascii')}").classes("w-full")


def render_plot_deck(session: DesignSession) -> None:
    out = session.pd_last_outputs or session.last_eval
    if not isinstance(out, dict):
        return

    art = session.pd_last_artifact or {}
    ui.label("Power balance plots — quick-look engineering visuals").classes("text-subtitle1")
    ui.label("Screening-level 0-D proxies; no ranking.").classes("text-caption q-mb-sm")
    from ui_nicegui.lib.verdict_core import verdict_summary

    if not bool(verdict_summary(out).get("feasible")):
        ui.label(
            "PHYS-KPI-001: plots below use INFEASIBLE-point outputs as diagnostic residue — not design achievements."
        ).classes("text-caption text-orange q-mb-sm")

    with ui.row().classes("w-full gap-2"):
        with ui.column().classes("flex-1"):
            _show_png(plot_power_stack(out), caption="Power stack unavailable.")
        with ui.column().classes("flex-1"):
            _show_png(
                plot_tight_constraints(art if isinstance(art, dict) else {}),
                caption="Constraint margin plot unavailable.",
            )

    with ui.row().classes("w-full gap-2 q-mt-sm"):
        with ui.column().classes("flex-1"):
            _show_png(plot_regime_dials(out), caption="Regime dials unavailable.")
        with ui.column().classes("flex-1"):
            _show_png(plot_engineering_severity(out), caption="Engineering severity unavailable.")

    ui.label("Plot dashboard").classes("text-subtitle2 q-mt-md")
    with ui.tabs().classes("w-full") as tabs:
        t1 = ui.tab("Power balance")
        t2 = ui.tab("Stability & limits")
        t3 = ui.tab("Geometry / build")
        t4 = ui.tab("Confinement")

    with ui.tab_panels(tabs, value=t1).classes("w-full"):
        with ui.tab_panel(t1):
            ui.label("Quick visual breakdown of where power is going in this 0-D point.").classes("text-caption")
            _show_png(plot_power_balance_bars(out), caption="Install matplotlib for plots.")
            with ui.expansion("Physical meaning (with literature)", icon="menu_book").classes("w-full"):
                ui.markdown(PLOT_PHYSICAL_MEANING["power_balance"])
        with ui.tab_panel(t2):
            ui.label("Screening metrics vs common operational guardrails.").classes("text-caption")
            _show_png(plot_stability_limits(out), caption="Stability plot unavailable.")
            with ui.expansion("Physical meaning (with literature)", icon="menu_book").classes("w-full"):
                ui.markdown(PLOT_PHYSICAL_MEANING["stability"])
        with ui.tab_panel(t3):
            ui.label("Geometry/build proxies that drive magnet and shield feasibility checks.").classes("text-caption")
            _show_png(plot_geometry_build(out), caption="Geometry plot unavailable.")
            with ui.expansion("Physical meaning (with literature)", icon="menu_book").classes("w-full"):
                ui.markdown(PLOT_PHYSICAL_MEANING["geometry"])
        with ui.tab_panel(t4):
            ui.label("Energy confinement and empirical H-factor comparators.").classes("text-caption")
            _show_png(plot_confinement(out), caption="Confinement plot unavailable.")
            with ui.expansion("Multi-scaling confinement envelope", icon="timeline").classes("w-full"):
                v396 = v396_scaling_rows(out)
                if v396:
                    ui.table(
                        columns=[
                            {"name": "scaling", "label": "Scaling", "field": "scaling", "align": "left"},
                            {"name": "tauE_s", "label": "τE (s)", "field": "tauE_s"},
                        ],
                        rows=v396,
                        row_key="scaling",
                    ).classes("w-full")
                else:
                    ui.label("No confinement scaling dictionary (module disabled or invalid inputs).").classes("text-caption")
            with ui.expansion("Kinetic profile peaking proxy", icon="show_chart").classes("w-full"):
                v397 = v397_profile_summary(out)
                if v397:
                    ui.label("Deterministic 1.5D proxy diagnostics (no solvers).").classes("text-caption")
                    render_json_blob({k: v for k, v in v397.items() if k != "sample"})
                    samp = v397.get("sample")
                    if isinstance(samp, dict) and samp:
                        if isinstance(next(iter(samp.values()), None), list):
                            cols = [{"name": c, "label": c, "field": c} for c in samp.keys()]
                            n = len(next(iter(samp.values())))
                            rows = [{c: samp[c][i] for c in samp} for i in range(min(n, 80))]
                            ui.table(columns=cols, rows=rows, row_key=cols[0]["field"]).classes("w-full")
                        else:
                            render_json_blob(samp)
                else:
                    ui.label("Profile peaking proxy disabled (enable in Configure).").classes("text-caption")
            with ui.expansion("Notes", icon="info").classes("w-full"):
                ui.markdown(PLOT_PHYSICAL_MEANING["confinement"])
