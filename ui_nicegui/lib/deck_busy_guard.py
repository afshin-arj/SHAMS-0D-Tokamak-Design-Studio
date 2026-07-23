"""Block Guided/Expert/tab remounts while a deck long-job is live.

Mirrors Scan Lab ``_refresh_tab_body_if_idle`` so progress / busy chrome
is not torn down mid-run (Helm+decks deep loop).
"""
from __future__ import annotations

from typing import Any, Callable, Iterable

from nicegui import ui


def refresh_tab_if_idle(
    session: Any,
    *,
    running_attrs: Iterable[str],
    refresh: Callable[[], None],
    job_label: str,
) -> None:
    """Call ``refresh`` only when none of ``running_attrs`` are True on session."""
    busy = [a for a in running_attrs if getattr(session, a, False)]
    if busy:
        ui.notify(
            f"{job_label} running — wait until it finishes before changing Guided / Expert / tabs.",
            type="warning",
        )
        return
    refresh()


SYSTEMS_RUNNING_ATTRS = (
    "systems_precheck_running",
    "systems_solve_running",
    "systems_recovery_running",
    "systems_fs_running",
    "systems_atlas_running",
)

PUB_RUNNING_ATTRS = (
    "pub_running",
    "pub_atlas_running",
    "pub_atlas_fragility_running",
    "pub_bench_running",
)

SUITE_RUNNING_ATTRS = ("suite_running",)

PD_RUNNING_ATTRS = (
    "evaluating",
    "phase_envelopes_running",
    "uq_contract_running",
    "pd_forensics_running",
)

FORGE_RUNNING_ATTRS = (
    "forge_mf_running",
    "forge_auditing",
    "forge_compiling",
    "forge_instrument_running",
)

PARETO_RUNNING_ATTRS = ("pareto_running",)

TRADE_RUNNING_ATTRS = ("trade_running",)

SCAN_RUNNING_ATTRS = ("scan_running", "scan_legacy_running")
