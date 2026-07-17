"""verdict_banner — verdict-first posture strip."""
from __future__ import annotations

from nicegui import ui


def verdict_banner(posture: str, *, detail: str = "") -> None:
    p = str(posture or "UNKNOWN").upper()
    style = {
        "FEASIBLE": "bg-green-1 text-green-10",
        "FEASIBLE+DIAG": "bg-amber-1 text-orange-10",
        "PASS+DIAG": "bg-amber-1 text-orange-10",
        "INFEASIBLE": "bg-red-1 text-red-10",
        "NO-SOLUTION": "bg-orange-1 text-orange-10",
        "MIRAGE": "bg-purple-1 text-purple-10",
        "PASS": "bg-green-1 text-green-10",
        "FAIL": "bg-red-1 text-red-10",
        "MIXED": "bg-amber-1 text-orange-10",
        "READY": "bg-blue-1 text-blue-10",
        "SEMANTICS": "bg-blue-grey-1 text-blue-grey-10",
        "MISSING ARTIFACT": "bg-orange-1 text-orange-10",
        # Scan Lab cartography robustness proxies (not L0 constraint verdicts)
        "ROBUST": "bg-green-1 text-green-10",
        "BALANCED": "bg-blue-1 text-blue-10",
        "BRITTLE": "bg-amber-1 text-orange-10",
        "KNIFE-EDGE": "bg-red-1 text-red-10",
        "UNKNOWN": "bg-grey-2",
    }.get(p, "bg-grey-2")
    with ui.card().classes(f"w-full p-3 {style}"):
        ui.label(f"Verdict: {p}").classes("text-h6")
        if detail:
            ui.label(detail).classes("text-body2")
