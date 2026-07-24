"""verdict_banner — verdict-first posture strip."""
from __future__ import annotations

from nicegui import ui

# Tokens that must never be painted as L0 "Verdict:" (cartography / UQ proxies).
_NON_L0_POSTURE_TOKENS = frozenset(
    {
        "ROBUST",
        "BALANCED",
        "BRITTLE",
        "KNIFE-EDGE",
        "DENSE SLICE",
        "MODERATE SLICE",
        "SPARSE SLICE",
        "NEAR-EMPTY SLICE",
        "ARCHIVE SCREENING",
        "BLOCKING-OK SCREENING",
    }
)


def verdict_banner(
    posture: str,
    *,
    detail: str = "",
    title_prefix: str | None = None,
) -> None:
    """Render a posture strip.

    Default title is ``Verdict:`` for L0 FEASIBLE / INFEASIBLE / NO-SOLUTION.
    Cartography robustness / slice-occupancy tokens auto-switch to
    ``Cartography posture:`` so they are not read as L0 feasibility.
    Pass ``title_prefix`` to override (e.g. ``"Pack screening posture"``).
    """
    p = str(posture or "UNKNOWN").upper()
    if title_prefix is None:
        if p in _NON_L0_POSTURE_TOKENS:
            title_prefix = "Cartography posture"
        else:
            title_prefix = "Verdict"
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
        # Systems Mode: PD seed / unverified — never green "Systems FEASIBLE"
        "PD BASELINE": "bg-amber-1 text-orange-10",
        "PD INFEASIBLE": "bg-orange-1 text-orange-10",
        "UNVERIFIED": "bg-blue-grey-1 text-blue-grey-10",
        # Scan Lab cartography slice occupancy / neighborhood proxies (not L0)
        "ROBUST": "bg-blue-1 text-blue-10",
        "BALANCED": "bg-blue-1 text-blue-10",
        "BRITTLE": "bg-amber-1 text-orange-10",
        "KNIFE-EDGE": "bg-amber-1 text-orange-10",
        "DENSE SLICE": "bg-blue-1 text-blue-10",
        "MODERATE SLICE": "bg-blue-1 text-blue-10",
        "SPARSE SLICE": "bg-amber-1 text-orange-10",
        "NEAR-EMPTY SLICE": "bg-amber-1 text-orange-10",
        "ARCHIVE SCREENING": "bg-blue-1 text-blue-10",
        "BLOCKING-OK SCREENING": "bg-blue-1 text-blue-10",
        "UNKNOWN": "bg-grey-2",
    }.get(p, "bg-grey-2")
    with ui.card().classes(f"w-full p-3 {style}"):
        ui.label(f"{title_prefix}: {p}").classes("text-h6")
        if detail:
            ui.label(detail).classes("text-body2")
