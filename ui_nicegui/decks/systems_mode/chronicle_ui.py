"""Negotiation chronicle and dominance switchboard."""

from __future__ import annotations

from nicegui import ui

from ui_nicegui.session import DesignSession

_LIMITER_GRAPH = {
    "q95": "Driven by I_p, B_t, geometry (R₀, a, κ) — safety factor proxy.",
    "q_div": "Driven by P_aux, confinement, exhaust geometry — divertor heat flux.",
    "TBR": "Driven by blanket, shield, size — tritium breeding.",
    "B_peak": "Driven by B_t, TF J_op, magnet technology.",
    "sigma_vm": "Driven by TF stress, size, field — structural envelope.",
}


def render_chronicle_panel(session: DesignSession) -> None:
    cards = list(session.systems_run_cards or [])
    ui.label("Negotiation chronicle").classes("text-subtitle2 q-mt-md")
    if not cards:
        ui.label("Run cards appear after precheck, solve, recovery, or search.").classes("text-caption")
    else:
        for card in reversed(cards[-15:]):
            kind = card.get("kind", "?")
            outcome = card.get("outcome") or {}
            settings = card.get("settings") or {}
            ui.markdown(f"- **{kind}**: {outcome} `{settings}`")

    ui.button(
        "Download transcript JSON",
        on_click=lambda: ui.download(
            __import__("json").dumps(cards, indent=2, sort_keys=True, default=str).encode("utf-8"),
            "systems_negotiation_transcript.json",
        ),
    ).props("flat q-mt-xs")

    with ui.expansion("Dominance switchboard (qualitative)", icon="hub").classes("w-full q-mt-sm"):
        ui.label("Curated map: what usually drives each constraint class.").classes("text-caption")
        for name, hint in _LIMITER_GRAPH.items():
            ui.markdown(f"- **{name}**: {hint}")
