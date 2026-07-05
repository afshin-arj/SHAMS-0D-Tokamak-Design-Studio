"""Scan Lab deck — NiceGUI Batch 4 + Phase 13 workbench.



Deterministic 2D cartography over the frozen Evaluator.

"""

from __future__ import annotations



from nicegui import ui



from ui_nicegui.components.empty_state import empty_state

from ui_nicegui.decks.scan_lab import cartography, results, verdict, workbench

from ui_nicegui.lib.artifact_access import get_point_artifact_triple

from ui_nicegui.session import DesignSession





def _refresh_after_scan() -> None:

    _render_verdict_section.refresh()

    _render_results_section.refresh()

    _render_workbench_section.refresh()





def render_scan_lab(session: DesignSession) -> None:

    ui.label("Scan Lab").classes("text-h5")

    ui.label(

        "Cartography over the frozen evaluator — map feasibility, emptiness, "

        "fragility, and dominant mechanisms. No optimizer."

    ).classes("text-caption text-grey q-mb-sm")



    with ui.expansion("About this mode", icon="info").classes("w-full q-mb-sm"):

        ui.markdown(

            "Scan Lab is **frozen**: deterministic cartography/interpretability only. "

            "A microscope, not an engine."

        )



    _, _, point_out = get_point_artifact_triple(session)

    if not isinstance(point_out, dict):

        empty_state(

            "Run **Point Designer** first — Scan Lab uses the last evaluated point as baseline.",

            kind="info",

        )

        return



    _render_verdict_section(session)

    ui.separator()

    cartography.render_cartography_controls(

        session,

        on_scan_complete=_refresh_after_scan,

    )

    _render_results_section(session)

    _render_workbench_section(session)





@ui.refreshable

def _render_verdict_section(session: DesignSession) -> None:

    verdict.render_scan_verdict(session.scan_cartography_report)





@ui.refreshable

def _render_results_section(session: DesignSession) -> None:

    rep = session.scan_cartography_report

    if not isinstance(rep, dict):

        return

    ui.separator()

    results.render_scan_results(session, rep)





@ui.refreshable

def _render_workbench_section(session: DesignSession) -> None:

    rep = session.scan_cartography_report

    if not isinstance(rep, dict):

        return

    ui.separator()

    workbench.render_workbench(

        session,

        rep,

        on_update=_render_workbench_section.refresh,

    )

