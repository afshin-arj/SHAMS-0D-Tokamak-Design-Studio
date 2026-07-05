"""Design governance — v402 dominance refs; mission contract lives in Helm Console."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.helm_labels import DESIGN_INTENT_OPTIONS
from ui_nicegui.lib.pd_intent_policy import policy_caption
from ui_nicegui.session import DesignSession


def render_design_governance(session: DesignSession) -> None:
    """Dominance reference thresholds only — intent and enforcement tiering are in Helm Console."""
    inp = session.inputs
    inp.setdefault("q95_enforcement", "hard")
    inp.setdefault("greenwald_enforcement", "hard")
    inp.setdefault("tech_tier", "TRL7")
    session.knobs.setdefault("transport_spread_ref_v402", 3.0)
    session.knobs.setdefault("profile_peaking_p_ref_v402", 3.0)
    session.knobs.setdefault("zeff_ref_max_v402", 2.5)

    with ui.expansion("Design governance (dominance references)", icon="gavel").classes("w-full q-mb-sm"):
        ui.label(
            "**Mission profile, q95/Greenwald tiering, and TRL** are set in "
            "**Helm Console → Design contract**. This panel only adjusts global dominance ranking references."
        ).classes("text-caption q-mb-sm")

        ui.markdown(
            f"- **Intent:** {session.design_intent}\n"
            f"- **q95 / Greenwald:** {inp.get('q95_enforcement', 'hard')} / {inp.get('greenwald_enforcement', 'hard')}\n"
            f"- **TRL:** {inp.get('tech_tier', 'TRL7')}\n"
            f"- {policy_caption(session.design_intent)}"
        ).classes("text-caption q-mb-sm")

        if session.design_intent not in DESIGN_INTENT_OPTIONS:
            ui.label("Adjust mission profile in Helm Console for consistent policy.").classes(
                "text-caption text-orange q-mb-sm"
            )

        if bool(session.overlay.get("include_authority_dominance_v402", True)):
            ui.label("Global dominance reference thresholds").classes("text-subtitle2")
            ui.label(
                "Rank authority margins in dominance telemetry — does not change frozen physics."
            ).classes("text-caption q-mb-sm")
            with ui.grid(columns=3).classes("w-full gap-2"):
                ui.number(
                    "Transport spread reference",
                    value=float(session.knobs.get("transport_spread_ref_v402", 3.0)),
                    min=1.1, step=0.1,
                    on_change=lambda e: session.knobs.__setitem__("transport_spread_ref_v402", e.value),
                )
                ui.number(
                    "Pressure peaking reference",
                    value=float(session.knobs.get("profile_peaking_p_ref_v402", 3.0)),
                    min=1.1, step=0.1,
                    on_change=lambda e: session.knobs.__setitem__("profile_peaking_p_ref_v402", e.value),
                )
                ui.number(
                    "Zeff reference maximum",
                    value=float(session.knobs.get("zeff_ref_max_v402", 2.5)),
                    min=1.1, step=0.1,
                    on_change=lambda e: session.knobs.__setitem__("zeff_ref_max_v402", e.value),
                )
