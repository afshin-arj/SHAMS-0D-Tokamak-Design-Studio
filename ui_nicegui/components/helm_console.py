"""Helm Console — Streamlit sidebar parity, expert-friendly layout, dark-drawer theme."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.bootstrap import repo_root
from ui_nicegui.components.dsg_sidebar import render_dsg_sidebar
from ui_nicegui.components.helm_theme import helm_dark_props
from ui_nicegui.lib.control_room_helpers import read_version
from ui_nicegui.lib.helm_helpers import (
    apply_legacy_reference_machine_to_session,
    apply_reference_preset_to_session,
    force_clear_stuck_runs,
    health_snapshot_rows,
    log_ui_event,
    on_design_intent_changed,
    on_policy_contract_changed,
    on_tech_tier_changed,
    run_verification_capture,
    verification_needs_run,
    verification_report_paths,
)
from ui_nicegui.components.helm_workflow_panel import render_deck_navigation, render_workflow_compass
from ui_nicegui.lib.expert_mode import apply_expert_mode
from ui_nicegui.lib.teaching_mode import apply_guided_mode
from ui_nicegui.lib.helm_labels import (
    DESIGN_INTENT_OPTIONS,
    HELM_NAV_GROUPS,
    helm_section_label,
)
from ui_nicegui.lib.deck_dsg_hooks import normalize_edge_kind
from ui_nicegui.lib.pd_intent_policy import constraint_policy_snapshot, policy_caption
from ui_nicegui.lib.run_lock import status as runlock_status, global_status as runlock_global_status
from ui_nicegui.session import DesignSession

_TRL_TIERS = ["TRL3", "TRL5", "TRL7", "TRL9"]
_POLICY_ENFORCEMENT = ["hard", "diagnostic"]
_RUN_START: dict[str, float] = {}
_PROGRESS_SNAP: dict[str, tuple[float, str]] = {}
# Point Designer / short evals: offer orphan recovery after this age.
_STUCK_RUN_THRESHOLD_S = 90
# Cartography / Pareto / Forge / Systems / Pub: longer before offering force-clear.
_STUCK_RUN_THRESHOLD_LONG_S = 300
_LONG_TASK_MARKERS = (
    "cartograph",
    "scan lab",
    "pareto",
    "trade",
    "forge",
    "machine finder",
    "systems mode",
    "publication",
    "benchmark",
    "atlas",
)


def _stuck_threshold_s(task: Optional[str]) -> int:
    t = (task or "").lower()
    if any(m in t for m in _LONG_TASK_MARKERS):
        return _STUCK_RUN_THRESHOLD_LONG_S
    return _STUCK_RUN_THRESHOLD_S


def _activity_logger(session: DesignSession):
    from tools.activity_log import ActivityLogger

    lg = getattr(session, "_activity_logger", None)
    if lg is None:
        lg = ActivityLogger(repo_root=Path(repo_root()), tz_name="Asia/Tehran")
        session._activity_logger = lg
    return lg


def _read_log_tail(session: DesignSession) -> str:
    try:
        lg = _activity_logger(session)
        n = int(session.activity_log_tail)
        if lg.path.exists():
            text = lg.path.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            if n > 0 and lines:
                return "\n".join(lines[-n:])
            return text
        return lg.get_text(last_n=n)
    except Exception:
        return ""


def _on_expert_mode(session: DesignSession, enabled: bool) -> None:
    apply_expert_mode(session, enabled)
    from ui_nicegui.lib.deck_busy_guard import FORGE_RUNNING_ATTRS, SCAN_RUNNING_ATTRS
    from ui_nicegui.lib.navigation import refresh_active_deck, refresh_helm, refresh_status

    # Deck bodies that hide expert panels need a remount/refresh to pick up the flag.
    # Do not tear down Scan Lab / Forge progress chrome mid-job.
    if session.active_deck == "Scan Lab" and any(
        getattr(session, a, False) for a in SCAN_RUNNING_ATTRS
    ):
        ui.notify(
            "Scan Lab job running — Expert mode saved; deck remount deferred until idle.",
            type="warning",
        )
        refresh_helm()
        refresh_status()
        return
    if session.active_deck == "Reactor Design Forge" and any(
        getattr(session, a, False) for a in FORGE_RUNNING_ATTRS
    ):
        ui.notify(
            "Forge job running — Expert mode saved; deck remount deferred until idle.",
            type="warning",
        )
        refresh_helm()
        refresh_status()
        return
    refresh_active_deck()
    refresh_helm()
    refresh_status()


def _on_guided_mode(session: DesignSession, enabled: bool) -> None:
    apply_guided_mode(session, enabled)
    from ui_nicegui.lib.deck_busy_guard import FORGE_RUNNING_ATTRS, SCAN_RUNNING_ATTRS
    from ui_nicegui.lib.navigation import refresh_active_deck, refresh_helm, refresh_status

    if session.active_deck == "Scan Lab" and any(
        getattr(session, a, False) for a in SCAN_RUNNING_ATTRS
    ):
        ui.notify(
            "Scan Lab job running — Guided mode saved; deck remount deferred until idle.",
            type="warning",
        )
        refresh_helm()
        refresh_status()
        return
    if session.active_deck == "Reactor Design Forge" and any(
        getattr(session, a, False) for a in FORGE_RUNNING_ATTRS
    ):
        ui.notify(
            "Forge job running — Guided mode saved; deck remount deferred until idle.",
            type="warning",
        )
        refresh_helm()
        refresh_status()
        return
    refresh_active_deck()
    refresh_helm()
    refresh_status()


def render_helm_console(
    session: DesignSession,
    *,
    on_deck_change: Callable[[str], None],
) -> None:
    _helm_nav_section(session, on_deck_change=on_deck_change)
    _helm_settings_section(session, on_deck_change=on_deck_change)


def refresh_helm_navigation() -> None:
    """Refresh workflow compass + deck nav only (fast path for deck switches)."""
    _helm_nav_section.refresh()


def refresh_helm_settings_panel() -> None:
    """Refresh session setup, DSG, and chronicle panels."""
    _helm_settings_section.refresh()


@ui.refreshable
def _helm_nav_section(session: DesignSession, *, on_deck_change: Callable[[str], None]) -> None:
    ui.label(helm_section_label("Helm Console - Expert Navigation")).classes(
        "text-h6 text-weight-bold q-mb-xs"
    )
    ui.label("Follow the numbered study workflow — evaluate, map, compare, seal.").classes(
        "text-caption q-mb-xs"
    )
    ui.label("Drag the right edge to resize · header ☰ to close or reopen.").classes(
        "text-caption text-grey q-mb-sm"
    )

    _render_run_lock_banner(session)
    _render_posture(session)
    if getattr(session, "dsg_edge_kind_auto", True):
        ek = normalize_edge_kind(session.dsg_context_edge_kind)
        ui.label(f"DSG edge kind (auto): {ek}").classes("text-caption text-grey-7 q-mb-xs")

    ui.separator().classes("q-my-sm")
    render_workflow_compass(session, on_deck_change=on_deck_change)
    render_deck_navigation(session, groups=HELM_NAV_GROUPS, on_deck_change=on_deck_change)


@ui.refreshable
def _helm_settings_section(session: DesignSession, *, on_deck_change: Callable[[str], None]) -> None:
    render_dsg_sidebar(session)

    with ui.expansion("Session setup", icon="settings").classes("w-full overflow-hidden").props("default-closed"):
        ui.label("Design contract").classes("text-caption text-weight-bold q-mt-xs")
        _render_mission_policy(session)
        ui.separator().classes("q-my-sm")
        ui.label("Integrity gate").classes("text-caption text-weight-bold")
        _render_integrity_gate(session)
        ui.separator().classes("q-my-sm")
        ui.label("Model authority & closures").classes("text-caption text-weight-bold")
        _render_fidelity(session)
        ui.separator().classes("q-my-sm")
        ui.label("Reference calibration").classes("text-caption text-weight-bold")
        _render_calibration(session)
        ui.separator().classes("q-my-sm")
        ui.label("Benchmark vault").classes("text-caption text-weight-bold")
        _render_benchmark_vault(session)

    ui.switch(
        helm_section_label("Explain mode (show equations & reasons)"),
        value=session.explain_mode,
        on_change=lambda e: setattr(session, "explain_mode", bool(e.value)),
    ).props(helm_dark_props())
    ui.label("Binding reasons in Constraints and forensics.").classes("text-caption q-mb-sm")

    with ui.expansion(helm_section_label("Advanced controls"), icon="tune").classes("w-full overflow-hidden"):
        ui.switch(
            "Guided mode (teaching banners)",
            value=bool(getattr(session, "guided_mode", True)),
            on_change=lambda e: _on_guided_mode(session, bool(e.value)),
        ).props(helm_dark_props())
        ui.label(
            "Carries teaching banners across Systems / Scan / Pareto / Trade / Forge / Suite / Compare / Pub / CR / PD."
        ).classes("text-caption q-mb-sm")
        ui.switch(
            "Expert solver controls",
            value=session.expert_mode,
            on_change=lambda e: _on_expert_mode(session, bool(e.value)),
        ).props(helm_dark_props("disable" if session.forge_review_mode else ""))
        ui.label(
            "Expose solver tolerances and optimizer internals in exploration decks "
            "(carries across Systems / Scan / Pareto / Trade / Forge / Suite / Compare / Pub / CR / PD)."
        ).classes("text-caption")
        if session.forge_review_mode:
            ui.label("Disabled in Review Mode (Reactor Design Forge).").classes("text-caption text-orange")

    with ui.expansion(helm_section_label("Black-Box Chronicle"), icon="history").classes("w-full overflow-hidden"):
        _render_chronicle(session)

    ui.separator().classes("q-my-md")
    _ver = read_version()
    ui.label(f"SHAMS {_ver}" if _ver.startswith("v") else f"SHAMS v{_ver}").classes("text-caption")


def _session_or_lock_busy(session: DesignSession) -> tuple[bool, str | None, str | None]:
    """Return (busy, task_label, lock_holder) for Helm banners / status / exit."""
    locked, task, holder = runlock_global_status()
    busy = bool(
        session.evaluating
        or session.scan_running
        or getattr(session, "scan_legacy_running", False)
        or session.pareto_running
        or session.trade_running
        or session.systems_precheck_running
        or getattr(session, "systems_solve_running", False)
        or getattr(session, "systems_recovery_running", False)
        or getattr(session, "systems_fs_running", False)
        or getattr(session, "systems_atlas_running", False)
        or getattr(session, "phase_envelopes_running", False)
        or getattr(session, "uq_contract_running", False)
        or session.forge_mf_running
        or getattr(session, "forge_compiling", False)
        or getattr(session, "forge_auditing", False)
        or getattr(session, "forge_instrument_running", False)
        or session.suite_running
        or session.pub_running
        or session.pub_atlas_running
        or session.pub_atlas_fragility_running
        or session.pub_bench_running
        or getattr(session, "helm_verify_running", False)
        or getattr(session, "pd_forensics_running", False)
        or getattr(session, "cmp_handoff_running", False)
        or locked
    )
    if task:
        return busy, task, holder
    if getattr(session, "helm_verify_running", False):
        return busy, "Helm: Gatecheck / verification", holder
    if getattr(session, "pd_forensics_running", False):
        return busy, "Point Designer: Forensics", holder
    if getattr(session, "cmp_handoff_running", False):
        return busy, "Compare: slot handoff evaluate", holder
    if session.scan_running:
        return busy, "Scan Lab cartography", holder
    if getattr(session, "scan_legacy_running", False):
        return busy, "Scan Lab: Legacy nested", holder
    if session.pareto_running:
        return busy, "Pareto Lab study", holder
    if session.trade_running:
        return busy, "Trade Study", holder
    if session.systems_precheck_running:
        return busy, "Systems Mode: Precheck", holder
    if getattr(session, "systems_solve_running", False):
        return busy, "Systems Mode: Target solve", holder
    if getattr(session, "systems_fs_running", False):
        return busy, "Systems Mode: Feasible search", holder
    if getattr(session, "systems_atlas_running", False):
        return busy, "Systems Mode: Micro-atlas screening", holder
    if getattr(session, "systems_recovery_running", False):
        return busy, "Systems Mode: Recovery", holder
    if getattr(session, "phase_envelopes_running", False):
        return busy, "Point Designer: Phase envelopes", holder
    if getattr(session, "uq_contract_running", False):
        return busy, "Point Designer: Uncertainty contract", holder
    if session.forge_mf_running:
        return busy, "Reactor Design Forge: Machine Finder", holder
    if getattr(session, "forge_instrument_running", False):
        return busy, "Reactor Design Forge: Instruments", holder
    if getattr(session, "forge_compiling", False):
        return busy, "Reactor Design Forge: Compile", holder
    if getattr(session, "forge_auditing", False):
        return busy, "Reactor Design Forge: Audit", holder
    if session.suite_running:
        return busy, "System Suite campaign", holder
    if (
        session.pub_running
        or session.pub_atlas_running
        or session.pub_atlas_fragility_running
        or session.pub_bench_running
    ):
        return busy, "Publication Benchmarks", holder
    if session.evaluating:
        return busy, "Point Designer: Evaluate", holder
    return busy, task, holder


def _scan_progress_still_advancing(session: DesignSession) -> bool:
    """True when Scan Lab progress text/value changed recently — not an orphan."""
    if not getattr(session, "scan_running", False):
        return False
    key = "scan"
    now = time.time()
    snap = f"{getattr(session, 'scan_progress', 0)!s}|{getattr(session, 'scan_progress_text', '')!s}"
    prev = _PROGRESS_SNAP.get(key)
    _PROGRESS_SNAP[key] = (now, snap)
    if prev is None:
        return True
    prev_t, prev_snap = prev
    if snap != prev_snap:
        return True
    # Unchanged for <15s still counts as possibly live (coarse grid steps).
    return (now - prev_t) < 15.0


def _render_run_lock_banner(session: DesignSession) -> None:
    busy, task, holder = _session_or_lock_busy(session)
    if not busy:
        # Idle — drop age timers so a later job with the same label does not look "stuck".
        _RUN_START.clear()
        _PROGRESS_SNAP.clear()
        return
    if task and task not in _RUN_START:
        _RUN_START[task] = time.time()
    for k in list(_RUN_START):
        if k != task:
            del _RUN_START[k]
    age = 0
    if task and task in _RUN_START:
        age = int(time.time() - _RUN_START[task])
    is_owner = False
    if holder:
        _, _, is_owner = runlock_status(holder)
    badge = "Running sequence" if is_owner else "Shot in progress"
    owner_hint = f" [{holder}]" if holder else ""
    ui.html(
        f'<div class="helm-info-banner"><strong>{badge}</strong>: {task or "evaluation"}{owner_hint} · t+{age}s</div>'
    ).classes("w-full q-mb-sm")

    thr = _stuck_threshold_s(task)
    if age >= thr:
        def _open_force_clear_dialog() -> None:
            if _scan_progress_still_advancing(session):
                ui.notify(
                    "Scan Lab progress is still advancing — not treating this as an orphaned lock. "
                    "Wait for the scan to finish, or leave the tab open.",
                    type="warning",
                )
                return
            with ui.dialog() as dialog, ui.card().classes("w-full").style("min-width: 28rem"):
                ui.label("Force-clear stuck run?").classes("text-h6")
                ui.markdown(
                    "Force-clear resets UI busy flags and the global run lock, and invalidates "
                    "the worker write-fence. A finishing zombie **discards** results and will not "
                    "unlock a newer job. It still does **not** cancel the OS thread mid-flight."
                ).classes("text-body2 q-mb-sm")
                confirm = ui.checkbox(
                    "I confirm this is an orphaned lock (no live worker is running).",
                    value=False,
                )

                def _do_clear() -> None:
                    if not bool(confirm.value):
                        ui.notify(
                            "Check the orphan confirmation box before force-clearing.",
                            type="warning",
                        )
                        return
                    cleared = force_clear_stuck_runs(session)
                    _RUN_START.clear()
                    _PROGRESS_SNAP.clear()
                    ui.notify(
                        f"Cleared {len(cleared)} stuck flag(s): {', '.join(cleared) or '(none)'}",
                        type="warning",
                    )
                    dialog.close()
                    from ui_nicegui.lib.navigation import refresh_current_deck

                    refresh_current_deck()

                with ui.row().classes("w-full justify-end gap-2 q-mt-sm"):
                    ui.button("Cancel", on_click=dialog.close).props("flat")
                    ui.button(
                        "Force-clear",
                        icon="lock_open",
                        on_click=_do_clear,
                    ).props("outline color=negative")
            dialog.open()

        with ui.row().classes("w-full items-center gap-2 q-mb-sm"):
            ui.label(
                f"Busy for {age}s (orphan CTA after {thr}s for this job class). "
                "Force-clear requires orphan confirmation — it does **not** cancel a live worker."
            ).classes("text-caption text-orange")
            ui.button(
                "Force-clear stuck run…",
                icon="lock_open",
                on_click=_open_force_clear_dialog,
            ).props("outline dense color=negative")


def _refresh_after_truth_contract_change() -> None:
    """Remount active deck + Helm posture after intent/enforcement/TRL invalidation.

    Cache clear alone left Captain's Ledger and deck hero showing a stale Point
    verdict until the next manual deck switch.
    """
    from ui_nicegui.lib.navigation import refresh_current_deck

    refresh_current_deck()


def _render_posture(session: DesignSession) -> None:
    ui.label(helm_section_label("Captain's Ledger")).classes("text-caption text-weight-bold")
    posture = "Review Mode (locked)" if session.forge_review_mode else "Explore Mode"
    ui.badge(posture, color="orange" if session.forge_review_mode else "green").props("outline").classes(
        "q-mb-xs"
    )

    # Mission + policy visible without opening Session setup (fusion-researcher path).
    ui.label(f"Mission: {session.design_intent}").classes("text-caption q-mt-xs")
    ui.label(policy_caption(session.design_intent)).classes("text-caption text-grey q-mb-xs")

    busy, task, holder = _session_or_lock_busy(session)
    # Busy detail lives in the run-lock banner above (single source of truth + force-clear).
    if not busy:
        ui.label("Run status: Ready — frozen evaluator armed.").classes("text-caption")
    else:
        ui.label("Run status: see banner above (force-clear available after orphan confirm).").classes(
            "text-caption text-grey"
        )
    out = session.pd_last_outputs or session.last_eval
    if isinstance(out, dict) and out:
        from ui_nicegui.lib.pd_hero_kpis import hero_kpi_cells
        from ui_nicegui.lib.pd_solver_helpers import inputs_stale
        from ui_nicegui.lib.session_store import get_cached_no_solution_atlas, get_cached_verdict_summary

        stale = bool(session.pd_last_run_ts and inputs_stale(session))
        summary = get_cached_verdict_summary(session, out)
        # PHYS-KPI-001: suppress Q/H98/Pfus claims on INFEASIBLE (PD hero parity).
        cells = hero_kpi_cells(
            out,
            summary,
            design_intent=str(session.design_intent or ""),
            fuel_mode=str((session.inputs or {}).get("fuel_mode", "DT")),
        )
        by_label = {c.label: c for c in cells}
        q_cell = by_label.get("Performance")
        h98_cell = by_label.get("H98(y,2)")
        pfus_cell = by_label.get("Pfus")
        # PHYS-KPI-001: never fall back to raw verdict_core q_label on INFEASIBLE.
        if q_cell is not None:
            q_bit = q_cell.display
        elif not summary.get("feasible"):
            q_bit = "— (diagnostic)"
        else:
            q_bit = summary.get("q_label", "-")
        detail = f"{summary.get('verdict', '-')} · {q_bit} · Dom {summary.get('dominant', '-')}"
        if stale:
            detail = "STALE · " + detail
        if bool(out.get("mirage_flag_v402")):
            detail += " · MIRAGE"
        if not summary.get("feasible"):
            atlas = get_cached_no_solution_atlas(session, out)
            detail += (
                f" · {atlas.get('dominant_mechanism', '-')} / "
                f"{atlas.get('dominant_constraint', '-')}"
            )
        tone = (
            "text-negative"
            if stale
            else ("text-orange" if (not summary.get("feasible") or out.get("mirage_flag_v402")) else "text-caption")
        )
        ui.label(f"Point: {detail}").classes(f"text-caption q-mt-xs {tone}")
        if stale:
            ui.label("Re-evaluate in Point Designer — KPIs no longer match current inputs.").classes(
                "text-caption text-negative"
            )
        if bool(out.get("mirage_flag_v402")):
            ui.badge("MIRAGE", color="orange").props("outline dense").classes("q-mt-xs")
        if h98_cell is not None and h98_cell.display not in ("n/a", ""):
            prefix = "H98(y,2)" if h98_cell.suppressed else "H98(y,2) ≈"
            ui.label(f"{prefix} {h98_cell.display}").classes("text-caption text-grey")
        if pfus_cell is not None and pfus_cell.suppressed:
            ui.label(f"Pfus {pfus_cell.display}").classes("text-caption text-grey")
    else:
        ui.label("Point: No evaluation yet — Evaluate in Point Designer.").classes(
            "text-caption text-grey q-mt-xs"
        )

    ui.markdown(
        "- **Authority:** Frozen evaluator\n"
        "- **Workspace:** Non-authoritative (proposals only)"
    ).classes("text-caption")


def _render_mission_policy(session: DesignSession) -> None:
    inp = session.inputs
    inp.setdefault("q95_enforcement", "hard")
    inp.setdefault("greenwald_enforcement", "hard")
    inp.setdefault("tech_tier", "TRL7")

    intent_val = session.design_intent if session.design_intent in DESIGN_INTENT_OPTIONS else DESIGN_INTENT_OPTIONS[0]

    def _set_intent(e) -> None:
        prev = str(session.design_intent)
        new = str(e.value)
        if prev != new:
            on_design_intent_changed(session, prev, new)
            _helm_settings_section.refresh()
            _refresh_after_truth_contract_change()

    ui.select(
        DESIGN_INTENT_OPTIONS,
        label="Mission profile (design intent)",
        value=intent_val,
        on_change=_set_intent,
    ).props(helm_dark_props()).classes("w-full")
    ui.label(
        "Reactor / Pilot / High-field missions enforce plant limits (TBR, stress, exhaust). "
        "Research missions keep q95 blocking; engineering limits become diagnostic; TBR ignored."
    ).classes("text-caption q-mb-sm")

    pol = constraint_policy_snapshot(session.design_intent)
    ui.label(policy_caption(session.design_intent)).classes("text-caption text-weight-bold")
    ui.markdown(
        f"- **Blocking:** {', '.join(pol.get('hard_blocking') or []) or '(none)'}\n"
        f"- **Diagnostic:** {', '.join(pol.get('diagnostic_only') or []) or '(none)'}\n"
        f"- **Ignored:** {', '.join(pol.get('ignored') or []) or '(none)'}"
    ).classes("text-caption q-mb-sm")

    ui.label("Per-limit enforcement (does not change physics outputs)").classes("text-caption text-weight-bold")
    q_prev = str(inp.get("q95_enforcement", "hard"))
    fg_prev = str(inp.get("greenwald_enforcement", "hard"))

    def _set_q95(e) -> None:
        inp["q95_enforcement"] = str(e.value)
        on_policy_contract_changed(session)
        _refresh_after_truth_contract_change()

    def _set_fg(e) -> None:
        inp["greenwald_enforcement"] = str(e.value)
        on_policy_contract_changed(session)
        _refresh_after_truth_contract_change()

    def _set_tier(e) -> None:
        inp["tech_tier"] = str(e.value)
        on_tech_tier_changed(session)
        _refresh_after_truth_contract_change()

    with ui.grid(columns=2).classes("w-full gap-2"):
        ui.select(
            _POLICY_ENFORCEMENT,
            label="q95 (cyl. proxy) limit",
            value=q_prev if q_prev in _POLICY_ENFORCEMENT else "hard",
            on_change=_set_q95,
        ).props(helm_dark_props())
        ui.select(
            _POLICY_ENFORCEMENT,
            label="Greenwald fG",
            value=fg_prev if fg_prev in _POLICY_ENFORCEMENT else "hard",
            on_change=_set_fg,
        ).props(helm_dark_props())

    tier = str(inp.get("tech_tier", "TRL7")).upper().strip()
    if tier not in _TRL_TIERS:
        tier = "TRL7"

    ui.select(
        _TRL_TIERS,
        label="Technology readiness (TRL)",
        value=tier,
        on_change=_set_tier,
    ).props(helm_dark_props()).classes("w-full q-mt-sm")

    ui.markdown(
        "**Contract:** enforcement tiering is recorded in artifacts; physics truth is unchanged."
    ).classes("text-caption q-mt-sm")

    try:
        from contracts.tech_tiers import suggested_defaults  # type: ignore

        sug = dict(suggested_defaults(str(inp.get("tech_tier", "TRL7"))))
    except Exception:
        sug = {}
    if sug:
        with ui.expansion("Suggested TRL caps (optional)", icon="info").classes("w-full"):
            ui.code(json.dumps(sug, indent=2, default=str), language="json")
            ui.label("Suggestions only — apply explicitly in Point Designer if desired.").classes("text-caption")


def _render_fidelity(session: DesignSession) -> None:
    ui.label("Declared model fidelity — recorded in artifacts; does not alter L0 physics.").classes(
        "text-caption q-mb-xs"
    )
    ui.label(
        "Artifact metadata only — choosing “enriched” does **not** switch overlays or unlock denser equations."
    ).classes("text-caption text-orange q-mb-sm")
    fid = dict(session.fidelity_config or {})

    def _set(key: str, val: str) -> None:
        session.fidelity_config[key] = val

    with ui.grid(columns=2).classes("w-full gap-2"):
        ui.select(["0D", "1/2D"], label="Plasma", value=fid.get("plasma", "0D"),
                  on_change=lambda e: _set("plasma", str(e.value))).props(helm_dark_props())
        ui.select(["limits", "stress"], label="Magnets", value=fid.get("magnets", "limits"),
                  on_change=lambda e: _set("magnets", str(e.value))).props(helm_dark_props())
        ui.select(["proxy", "enriched"], label="Exhaust", value=fid.get("exhaust", "proxy"),
                  on_change=lambda e: _set("exhaust", str(e.value))).props(helm_dark_props())
        ui.select(["proxy", "enriched"], label="Neutronics", value=fid.get("neutronics", "proxy"),
                  on_change=lambda e: _set("neutronics", str(e.value))).props(helm_dark_props())
        ui.select(["off", "analytic"], label="Profiles", value=fid.get("profiles", "off"),
                  on_change=lambda e: _set("profiles", str(e.value))).props(helm_dark_props())
        ui.select(["proxy", "enriched"], label="Economics", value=fid.get("economics", "proxy"),
                  on_change=lambda e: _set("economics", str(e.value))).props(helm_dark_props())


def _render_calibration(session: DesignSession) -> None:
    ui.label(
        "Transparent multipliers (default 1.0) for reference calibration — not hidden tuning."
    ).classes("text-caption q-mb-sm")
    with ui.row().classes("w-full gap-2"):
        ui.button(
            "Reset to 1.0",
            on_click=lambda: (
                setattr(session, "calib_confinement", 1.0),
                setattr(session, "calib_divertor", 1.0),
                setattr(session, "calib_bootstrap", 1.0),
                _helm_settings_section.refresh(),
            ),
        ).props("outline dense")
        ui.label("τE · divertor · bootstrap").classes("text-caption")

    for attr, title, hint in (
        (
            "calib_confinement",
            "Confinement (τE multiplier)",
            "Multiplies τE for reference calibration — not a claimed H98.",
        ),
        (
            "calib_divertor",
            "Divertor / exhaust proxy",
            "Scales divertor/exhaust proxy screening — not a SOLPS design margin.",
        ),
        (
            "calib_bootstrap",
            "Bootstrap current I_bs",
            "Scales bootstrap current for calibration against references.",
        ),
    ):
        ui.slider(
            min=0.5, max=1.5, step=0.01,
            value=float(getattr(session, attr)),
            on_change=lambda e, a=attr: (
                setattr(session, a, float(e.value)),
                ui.notify("Reference calibration changed — re-evaluate Point Designer.", type="info"),
            ),
        ).props('label color="primary"').classes("w-full")
        ui.label(title).classes("text-caption")
        ui.label(hint).classes("text-caption text-grey q-mb-sm")


def _render_benchmark_vault(session: DesignSession) -> None:
    try:
        from models.reference_machines import REFERENCE_MACHINES, reference_catalog
    except ImportError:
        from src.models.reference_machines import REFERENCE_MACHINES, reference_catalog  # type: ignore

    try:
        ref_catalog = reference_catalog()
        ref_keys = sorted(ref_catalog.keys())
    except Exception:
        ref_catalog = {}
        ref_keys = []

    legacy_names = list(REFERENCE_MACHINES.keys())
    choices = ref_keys if ref_keys else legacy_names

    with ui.tabs().classes("w-full") as tabs:
        t_presets = ui.tab("Reference presets")
        t_packs = ui.tab("Benchmark packs")

    with ui.tab_panels(tabs, value=t_presets).classes("w-full"):
        with ui.tab_panel(t_presets):
            ui.label(
                "Load frozen reference machines into workspace inputs. Does not modify physics — sets inputs only."
            ).classes("text-caption q-mb-sm")
            if not choices:
                ui.label("No reference presets found.").classes("text-caption")
            else:
                sel = ui.select(choices, label="Preset", value=choices[0]).props(helm_dark_props()).classes(
                    "w-full"
                )
                if sel.value and str(sel.value) in ref_catalog:
                    ent = ref_catalog[str(sel.value)]
                    suite = str(ent.get("suite", "n/a"))
                    cls = str(ent.get("class", "n/a"))
                    with ui.expansion(f"Metadata · suite {suite} · class {cls}", icon="info").classes("w-full"):
                        ui.code(json.dumps(ent, indent=2, default=str), language="json")
                elif sel.value and str(sel.value) in REFERENCE_MACHINES:
                    ui.label("Legacy preset (inline table).").classes("text-caption text-weight-bold")

                async def _load() -> None:
                    key = str(sel.value or "")
                    if not key:
                        ui.notify("Select a preset first.", type="warning")
                        return
                    try:
                        if key in ref_catalog:
                            apply_reference_preset_to_session(session, key)
                        else:
                            apply_legacy_reference_machine_to_session(session, key)
                        from ui_nicegui.lib.navigation import refresh_current_deck, refresh_helm, refresh_status
                        from ui_nicegui.lib.pd_handoff import prepare_point_designer_handoff
                        from ui_nicegui.lib.session_store import clear_point_designer

                        # Inputs replaced — drop prior eval so Captain's Ledger cannot look current.
                        clear_point_designer(session)
                        prepare_point_designer_handoff(session)
                        log_ui_event(session, "UI", "ReferencePresetLoaded", {"preset": key})
                        ui.notify(
                            f"Loaded preset: {key} — prior Point Designer KPIs cleared; Evaluate Point before trusting posture.",
                            type="warning",
                        )
                        _helm_settings_section.refresh()
                        refresh_status()
                        refresh_helm()
                        if session.active_deck == "Point Designer":
                            refresh_current_deck()
                    except Exception as exc:
                        ui.notify(f"Preset load failed: {exc}", type="negative")

                ui.button("Load preset", on_click=_load).classes("w-full q-mt-sm")

        with ui.tab_panel(t_packs):
            ui.label(
                "Benchmark packs are deterministic evidence generators. "
                "Use Publication Benchmarks deck for full CSV+JSON+hashes."
            ).classes("text-caption q-mb-sm")
            ui.label("Quick actions").classes("text-caption text-weight-bold")
            outdir = session.pub_bench_last_outdir
            if outdir:
                ui.code(str(outdir), language="text").classes("w-full")
            else:
                ui.label("No benchmark pack recorded this session yet.").classes("text-caption")

            with ui.row().classes("w-full gap-2 q-mt-sm"):
                def _go_pub() -> None:
                    from ui_nicegui.lib.navigation import switch_deck

                    switch_deck("Publication Benchmarks")

                ui.button("Open Publication Benchmarks", on_click=_go_pub).props("outline dense").classes("flex-1")
                ui.label(
                    "Tip: Generate Pack in that deck for reviewer-safe artifacts."
                ).classes("text-caption flex-1")


def _render_integrity_gate(session: DesignSession) -> None:
    rep_path, _, _, _ = verification_report_paths()
    report_exists = os.path.exists(rep_path)
    needs = verification_needs_run()
    if report_exists and not needs:
        status_line = "Evidence report: up-to-date"
    elif report_exists:
        status_line = "Evidence report: needs update"
    else:
        status_line = "Evidence report: missing"

    ui.label("Explicit compliance check only — nothing runs automatically.").classes("text-caption")
    ui.label(status_line).classes("text-body2 q-mb-sm")

    with ui.expansion("Instant health snapshot", icon="monitor_heart").classes("w-full"):
        for row in health_snapshot_rows():
            ui.label(f"{row['Check']}: {row['Status']}").classes("text-caption")

    async def _run_gatecheck() -> None:
        from ui_nicegui.lib.run_lock import (
            acquire as runlock_acquire,
            release as runlock_release,
            status as runlock_status,
            current_lease,
            lease_valid,
        )

        if session.helm_verify_running:
            ui.notify("Gatecheck already running", type="warning")
            return
        locked, task, is_owner = runlock_status("HelmIntegrity")
        if locked:
            ui.notify(
                f"Busy: {task} — wait or force-clear from Helm."
                if not is_owner
                else "Gatecheck already holds the run lock.",
                type="warning",
            )
            return
        if not runlock_acquire("Helm: Gatecheck / verification", "HelmIntegrity"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        lease = current_lease()
        session.helm_verify_running = True
        _helm_settings_section.refresh()
        try:
            ok, out, err, dt = await run.io_bound(run_verification_capture)
            if not lease_valid(lease):
                ui.notify("Run was force-cleared — discarding results.", type="warning")
                return
            session.helm_verify_ok = ok
            session.helm_verify_out = out
            session.helm_verify_err = err
            session.helm_verify_dt = dt
            log_ui_event(session, "UI", "GatecheckRun", {"ok": ok, "seconds": dt})
            ui.notify(f"Gatecheck {'PASS' if ok else 'FAIL'} ({dt:.1f}s)", type="positive" if ok else "negative")
        finally:
            if lease_valid(lease):
                session.helm_verify_running = False
                runlock_release("HelmIntegrity", lease)
                _helm_settings_section.refresh()

    with ui.row().classes("w-full gap-2"):
        gate_btn = ui.button("Run gatecheck", on_click=_run_gatecheck).classes("flex-1")
        if session.helm_verify_running:
            gate_btn.props("loading disable")
        ui.switch(
            "Show logs",
            value=session.verify_show_logs,
            on_change=lambda e: setattr(session, "verify_show_logs", bool(e.value)),
        ).props(helm_dark_props())

    if report_exists:
        try:
            rep_bytes = Path(rep_path).read_bytes()
            ui.button(
                "Download evidence report (JSON)",
                on_click=lambda b=rep_bytes: ui.download(b, "shams_verification_report.json"),
            ).classes("w-full q-mt-sm")
        except Exception:
            ui.label("Evidence report download unavailable.").classes("text-caption")

    if session.helm_verify_dt is not None:
        ok = bool(session.helm_verify_ok)
        ui.label(
            f"Last gatecheck: {'PASS' if ok else 'FAIL'} ({session.helm_verify_dt:.2f}s)"
        ).classes("text-caption " + ("text-green" if ok else "text-red"))

    if session.verify_show_logs:
        ui.textarea(label="stdout", value=session.helm_verify_out or "").props(
            "readonly outlined dense rows=4"
        ).classes("w-full")
        ui.textarea(label="stderr", value=session.helm_verify_err or "").props(
            "readonly outlined dense rows=4"
        ).classes("w-full")


def _render_chronicle(session: DesignSession) -> None:
    ui.switch(
        "Auto-log (recommended)",
        value=session.activity_log_auto,
        on_change=lambda e: setattr(session, "activity_log_auto", bool(e.value)),
    ).props(helm_dark_props())
    ui.number(
        "Show last N lines",
        value=session.activity_log_tail,
        min=50,
        max=2000,
        step=50,
        on_change=lambda e: (
            setattr(session, "activity_log_tail", int(e.value or 200)),
            _render_chronicle_tail.refresh(),
        ),
    ).props(helm_dark_props()).classes("w-full")
    _render_chronicle_tail(session)

    tail = _read_log_tail(session)
    log_bytes = ((tail + "\n") if tail else "").encode("utf-8")
    ui.button(
        "Download log",
        on_click=lambda b=log_bytes: ui.download(b, "activity.log"),
    ).classes("w-full q-mt-sm")

    def _clear() -> None:
        if not bool(getattr(session, "shams_clear_log_confirm", False)):
            ui.notify("Check Confirm clear log first.", type="warning")
            return
        try:
            log_ui_event(session, "UI", "ClearLog", {})
            _activity_logger(session).clear()
        except Exception:
            pass
        session.shams_clear_log_confirm = False
        _render_chronicle_tail.refresh()
        _helm_settings_section.refresh()
        ui.notify("Activity log cleared.", type="info")

    ui.checkbox(
        "Confirm clear log",
        value=bool(getattr(session, "shams_clear_log_confirm", False)),
        on_change=lambda e: setattr(session, "shams_clear_log_confirm", bool(e.value)),
    )
    ui.button("Clear log", on_click=_clear).props("outline").classes("w-full q-mt-xs")
    ui.separator().classes("q-my-sm")
    ui.label("Session shutdown").classes("text-caption text-weight-bold")
    ui.checkbox(
        "Confirm exit",
        value=session.shams_exit_confirm,
        on_change=lambda e: (
            setattr(session, "shams_exit_confirm", bool(e.value)),
            _helm_settings_section.refresh(),
        ),
    )

    def _exit() -> None:
        if not session.shams_exit_confirm:
            ui.notify("Check Confirm exit first.", type="warning")
            return
        busy, task, _holder = _session_or_lock_busy(session)
        if busy and not bool(getattr(session, "shams_exit_force_busy", False)):
            ui.notify(
                f"A run is still active ({task or 'evaluation'}). "
                "Check 'Force exit while busy' to kill the process anyway.",
                type="warning",
            )
            return
        log_ui_event(session, "UI", "ExitRequested", {})
        os._exit(0)

    ui.checkbox(
        "Force exit while busy (kills in-flight runs)",
        value=bool(getattr(session, "shams_exit_force_busy", False)),
        on_change=lambda e: setattr(session, "shams_exit_force_busy", bool(e.value)),
    )
    ui.button(
        "Exit SHAMS",
        on_click=_exit,
    ).props("color=negative" + ("" if session.shams_exit_confirm else " disable")).classes("w-full q-mt-xs")


@ui.refreshable
def _render_chronicle_tail(session: DesignSession) -> None:
    tail = _read_log_tail(session)
    ui.textarea(value=tail or "(empty)").props("readonly outlined dense rows=6").classes("w-full").style(
        "font-family: monospace; font-size: 11px;"
    )


def helm_status_caption(session: DesignSession) -> str:
    deck = str(getattr(session, "active_deck", "") or "Point Designer")
    busy, task, holder = _session_or_lock_busy(session)
    if busy:
        who = f" [{holder}]" if holder else ""
        return f"{deck} · Running: {task or 'evaluation'}{who} · solver actions locked"
    return f"{deck} · Ready · frozen evaluator armed"
