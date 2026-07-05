"""Design stories — save/load decision-grade Systems snapshots."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from nicegui import ui

from ui_nicegui.lib.systems_state_helpers import merge_base_overrides_into_session
from ui_nicegui.session import DesignSession


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def render_design_stories(session: DesignSession, *, on_change=None) -> None:
    ui.label("Design stories").classes("text-subtitle2 q-mt-md")
    ui.label("Save and reload Systems workflow state (base, bounds, overrides).").classes("text-caption q-mb-sm")

    stories = list(session.systems_design_stories or [])
    name = ui.input("Story name", value=f"Story {len(stories) + 1}").classes("w-full")
    notes = ui.textarea("Notes (optional)").classes("w-full")

    def _save() -> None:
        pre = session.last_precheck_report
        pre_d = None
        if pre is not None:
            try:
                pre_d = {k: getattr(pre, k) for k in ("ok", "reason", "n_samples") if hasattr(pre, k)}
            except Exception:
                pre_d = pre if isinstance(pre, dict) else None
        story = {
            "ts": _now_iso(),
            "name": str(name.value or f"Story {len(stories)+1}").strip(),
            "notes": str(notes.value or ""),
            "design_intent": session.design_intent,
            "base_overrides": dict(session.systems_base_overrides or {}),
            "bounds_overrides": dict(session.systems_bounds_overrides or {}),
            "inputs_overrides": dict(session.systems_inputs_overrides or {}),
            "targets_overrides": dict(session.systems_targets_overrides or {}),
            "last_precheck": pre_d,
            "last_recovery": dict(session.systems_recovery_last or {}),
            "last_feasible_search": dict(session.systems_feasible_search_last or {}),
            "last_run_card": (session.systems_run_cards or [])[-1] if session.systems_run_cards else None,
        }
        session.systems_design_stories = (stories + [story])[-50:]
        ui.notify("Story saved", type="positive")
        if on_change:
            on_change()

    ui.button("Save current story", icon="bookmark", on_click=_save).props("outline q-mb-sm")

    stories = list(session.systems_design_stories or [])
    if not stories:
        ui.label("No stories yet.").classes("text-grey")
        return

    labels = [f"{s.get('name', '(unnamed)')} ({s.get('ts', '')})" for s in stories]

    def _load(label: str) -> None:
        try:
            idx = labels.index(label)
        except ValueError:
            return
        s = stories[idx]
        bo = dict(s.get("base_overrides") or {})
        session.systems_base_overrides = bo
        merge_base_overrides_into_session(session, bo)
        session.systems_bounds_overrides = dict(s.get("bounds_overrides") or {})
        session.systems_inputs_overrides = dict(s.get("inputs_overrides") or {})
        session.systems_targets_overrides = dict(s.get("targets_overrides") or {})
        ui.notify("Story loaded — re-run precheck on tab 2", type="info")
        if on_change:
            on_change()

    ui.select(labels, label="Load story", on_change=lambda e: _load(str(e.value))).classes("w-full")

    ui.button(
        "Export all stories JSON",
        on_click=lambda: ui.download(
            json.dumps(stories, indent=2, sort_keys=True, default=str).encode("utf-8"),
            "shams_systems_design_stories.json",
        ),
    ).props("flat")
