"""Candidate ranking and decision journal."""

from __future__ import annotations

import json
import time

from nicegui import ui

from ui_nicegui.lib.systems_ranking_helpers import rank_candidates
from ui_nicegui.lib.systems_state_helpers import append_journal
from ui_nicegui.lib.systems_workflow_helpers import collect_candidates
from ui_nicegui.session import DesignSession


def render_audit_panel(session: DesignSession) -> None:
    ui.label("Candidate ranking").classes("text-subtitle2")
    ui.select(
        ["Balanced", "Performance", "Margin"],
        label="Profile",
        value=session.systems_ranking_profile,
        on_change=lambda e: setattr(session, "systems_ranking_profile", str(e.value)),
    ).classes("w-48 q-mb-sm")

    cands = collect_candidates(session)
    ranked = rank_candidates(cands, session.systems_ranking_profile)
    ui.label(f"{len(cands)} candidate(s)").classes("text-caption")

    if ranked:
        rows = []
        for i, c in enumerate(ranked[:10]):
            h = c.get("headline") or {}
            rows.append({
                "rank": i + 1,
                "source": c.get("source"),
                "feasible": c.get("feasible"),
                "Q": h.get("Q"),
                "P_net": h.get("P_net"),
            })
        ui.table(
            columns=[
                {"name": "rank", "label": "#", "field": "rank"},
                {"name": "source", "label": "Source", "field": "source"},
                {"name": "feasible", "label": "OK", "field": "feasible"},
                {"name": "Q", "label": "Q", "field": "Q"},
                {"name": "P_net", "label": "P_net", "field": "P_net"},
            ],
            rows=rows,
            row_key="rank",
        ).classes("w-full q-mb-md")

    ui.label("Decision journal").classes("text-subtitle2 q-mt-md")
    j = list(session.systems_journal or [])
    if j:
        for e in reversed(j[-8:]):
            ts = time.strftime("%H:%M", time.localtime(float(e.get("ts_unix", 0))))
            ui.markdown(f"- `{ts}` **{e.get('kind', '?')}**")
        md = "# SHAMS Systems Decision Journal\n\n"
        for e in j:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(e.get("ts_unix", 0))))
            md += f"- **{ts}** [{e.get('kind', '')}]\n"
        with ui.row().classes("gap-2"):
            ui.button("Journal MD", on_click=lambda: ui.download(md.encode(), "systems_journal.md")).props("flat")
            ui.button(
                "Journal JSON",
                on_click=lambda: ui.download(
                    json.dumps(j, indent=2, default=str).encode(), "systems_journal.json"
                ),
            ).props("flat")
    else:
        ui.label("Journal fills as you run precheck, solve, recovery, and search.").classes("text-caption")

    ui.button("Log audit snapshot", on_click=lambda: (append_journal(session, "AuditSnapshot"), ui.notify("Logged"))).props(
        "flat q-mt-sm"
    )
