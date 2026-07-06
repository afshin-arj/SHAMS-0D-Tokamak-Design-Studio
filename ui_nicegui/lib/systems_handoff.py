"""External deck handoffs into Systems Mode."""

from __future__ import annotations

from typing import Any

from nicegui import ui


def consume_systems_mode_queue(session: Any) -> bool:
    """Apply queued Pareto / external handoff payloads to session inputs."""
    q = list(getattr(session, "systems_mode_queue", []) or [])
    if not q:
        return False
    item = q.pop(0)
    session.systems_mode_queue = q
    if not isinstance(item, dict):
        return False
    applied = 0
    for k, v in item.items():
        if k in getattr(session, "inputs", {}) and v is not None:
            try:
                session.inputs[k] = float(v)
                applied += 1
            except (TypeError, ValueError):
                pass
    if applied:
        session.systems_workflow_step = "1 · Targets"
        ui.notify(f"Pareto handoff applied ({applied} inputs) — review targets on tab 1.", type="positive")
        return True
    ui.notify("Handoff queue was empty or invalid.", type="warning")
    return False
