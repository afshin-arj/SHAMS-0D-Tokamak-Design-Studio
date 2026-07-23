"""Expert study workflow — phase map, deck actions, and next-step guidance."""
from __future__ import annotations

from typing import Any, Optional

from ui_nicegui.decks.labels import DECK_LABELS
from ui_nicegui.lib.deck_workflow import DECK_WORKFLOW_CAPTIONS, DECK_WORKFLOW_STEP
from ui_nicegui.lib.helm_labels import HELM_NAV_GROUPS

# Phase index 1–5 matching HELM_NAV_GROUPS order.
WORKFLOW_PHASES: list[tuple[str, str]] = [
    ("Anchor", "Define one operating point; get a feasibility verdict."),
    ("Map & close", "Cartography, then integrated plant/systems closure."),
    ("Compare & trade", "Diff artifacts, Pareto fronts, certified trade studies."),
    ("Concepts", "Compile intent; explore machine families and archives."),
    ("Evidence & audit", "Benchmarks, batch campaigns, provenance, export."),
]

DECK_TO_PHASE: dict[str, int] = {}
for phase_idx, (_, _, decks) in enumerate(HELM_NAV_GROUPS, start=1):
    for deck in decks:
        DECK_TO_PHASE[deck] = phase_idx

# What to do *now* on each deck (fusion-expert verbs, 2–3 lines max).
DECK_NOW_ACTIONS: dict[str, list[str]] = {
    "Point Designer": [
        "Configure geometry, plasma, and plant inputs.",
        "Evaluate — read verdict, dominant constraint, and margins.",
        "Use Constraints atlas before advancing.",
    ],
    "Scan Lab": [
        "Pick two scan axes and run a feasibility cartography.",
        "Inspect first-failure topology on the map.",
        "Export Scan Atlas capsule for replay.",
    ],
    "Systems Mode": [
        "Set targets and iteration variables, then precheck / solve.",
        "Review candidates and recovery posture on the constraint ledger.",
        "Apply only a feasible candidate to Point Designer (or an explicit diagnostic seed).",
    ],
    "Opt Lab": [
        "Follow the three-step certified-search path (propose→CCFS).",
        "Open Systems Mode, Pareto Lab, or Control Room Certified Search.",
        "Read Proposed — SHAMS-certified results; never claim a true minimum.",
    ],
    "Compare": [
        "Load baseline and scenario artifacts (A & B).",
        "Review performance, constraint, and structural diffs.",
        "Export comparison bundle for reviewers.",
    ],
    "Pareto Lab": [
        "Define objectives on the feasible set only.",
        "Separate optimistic vs robust lanes; filter mirages.",
        "Export publication pack from the frontier.",
    ],
    "Trade Study Studio": [
        "Set up certified trade study parameters.",
        "Run frontier atlas and robust certification.",
        "Hand off to external optimizer kits if needed.",
    ],
    "Reactor Design Forge": [
        "Compile design intent and machine-finder criteria.",
        "Run staged exploration; archive candidates to casebook.",
        "Open machine dossier for review-room narrative.",
    ],
    "Publication Benchmarks": [
        "Evaluate a reference preset on the Constitutional Atlas (Tab 1).",
        "Generate publication CSV/ZIP pack and inspect blocking pass/fail (Tab 2).",
        "Compare cross-code semantics or open System Suite for numeric PROCESS parity (Tab 3).",
        "Export reviewer/licensing packs or session evidence (Tabs 4–5).",
    ],
    "System Suite": [
        "Review plant closure and net-electric ledger (Tab 1).",
        "Check ops/thermal traces and lifetime/TBR budgets (Tabs 2–3).",
        "Run envelope tools or export campaign/parity packs (Tabs 4–5).",
    ],
    "Control Room": [
        "Generate study protocol and repro lock from artifact.",
        "Inspect run audit overlays and scenario delta.",
        "Export evidence bundle for audit trail.",
    ],
}

DECK_SHORT_VERBS: dict[str, str] = {
    "Point Designer": "Evaluate point",
    "Scan Lab": "Map design space",
    "Systems Mode": "Close systems",
    "Opt Lab": "Certified search",
    "Compare": "Diff A vs B",
    "Pareto Lab": "Build frontier",
    "Trade Study Studio": "Certify trade study",
    "Reactor Design Forge": "Explore concepts",
    "Publication Benchmarks": "Benchmark constitution",
    "System Suite": "Review system overlays",
    "Control Room": "Seal & export",
}


def deck_phase(deck: str) -> int:
    return DECK_TO_PHASE.get(deck, 1)


def phase_title(phase: int) -> str:
    if 1 <= phase <= len(WORKFLOW_PHASES):
        return WORKFLOW_PHASES[phase - 1][0]
    return "Study"


def has_point_evaluation(session: Any) -> bool:
    """True only for a current (non-STALE) Point Designer evaluation."""
    out = getattr(session, "pd_last_outputs", None)
    if not isinstance(out, dict):
        return False
    try:
        from ui_nicegui.lib.pd_solver_helpers import inputs_stale

        if bool(getattr(session, "pd_last_run_ts", None) and inputs_stale(session)):
            return False
    except Exception:
        pass
    return True


def has_compare_slots(session: Any) -> bool:
    """True only when both Compare slots A and B are loaded."""
    a = getattr(session, "cmp_slot_a", None)
    b = getattr(session, "cmp_slot_b", None)
    use_a = bool(getattr(session, "cmp_use_slot_a", True))
    use_b = bool(getattr(session, "cmp_use_slot_b", True))
    return (isinstance(a, dict) and use_a) and (isinstance(b, dict) and use_b)


def _systems_artifact_intent_feasible(art: dict) -> bool:
    """True when a Systems artifact represents an intent-feasible closure."""
    v = str(art.get("verdict") or "").upper()
    if v in ("FEASIBLE", "PASS", "PASS+DIAG", "OK", "VERIFIED"):
        return True
    if v in ("INFEASIBLE", "FAIL", "NO-SOLUTION", "NOSOLUTION", "REJECTED"):
        return False
    out = art.get("outputs")
    if isinstance(out, dict) and out:
        try:
            from ui_nicegui.lib.verdict_core import verdict_summary

            return bool(verdict_summary(out).get("feasible"))
        except Exception:
            return False
    return False


def has_systems_closure(session: Any) -> bool:
    """True when Systems Mode closed with an intent-feasible Systems result.

    PD fallback / Apply re-eval and INFEASIBLE recovery seeds do not close systems.
    A leftover Newton ``systems_last_solve_result`` must not count when the visible
    artifact is Point Designer Apply / fallback (Apply supersedes solve closure).
    """
    from ui_nicegui.lib.systems_artifact import is_systems_result_source, normalize_systems_artifact_source

    art = getattr(session, "systems_last_solve_artifact", None)
    if isinstance(art, dict) and art:
        if is_systems_result_source(normalize_systems_artifact_source(art)):
            return _systems_artifact_intent_feasible(art)
        # PD Apply / fallback / re-eval supersedes any leftover Newton result.
        return False
    rep = getattr(session, "systems_last_solve_result", None)
    if isinstance(rep, dict) and (
        rep.get("ok") or rep.get("intent_feasible") or rep.get("feasible")
    ):
        return True
    return False


def suggest_next_deck(session: Any, active_deck: str) -> tuple[Optional[str], str]:
    """Return (recommended deck or None, plain-language reason)."""
    if not has_point_evaluation(session):
        if active_deck != "Point Designer":
            return ("Point Designer", "No evaluation yet — anchor a point under frozen truth first.")
        return (None, "Evaluate the current point before moving to cartography.")

    try:
        idx = DECK_LABELS.index(active_deck)
    except ValueError:
        return (None, "")

    if active_deck == "Point Designer":
        # Prefer recovery/closure when the anchored point is already INFEASIBLE.
        cache = getattr(session, "pd_verdict_summary_cache", None)
        if isinstance(cache, dict) and cache.get("loaded") and not cache.get("feasible"):
            return (
                "Systems Mode",
                "Point is INFEASIBLE — close systems / recover before mapping the design space.",
            )
        out = getattr(session, "pd_last_outputs", None) or getattr(session, "last_eval", None)
        if isinstance(out, dict) and out and "outputs" not in out:
            try:
                from ui_nicegui.lib.verdict_core import verdict_summary

                summary = verdict_summary(out)
                if summary.get("loaded") and not summary.get("feasible"):
                    return (
                        "Systems Mode",
                        "Point is INFEASIBLE — close systems / recover before mapping the design space.",
                    )
            except Exception:
                pass
        return ("Scan Lab", "Point evaluated — map feasible regions before committing.")

    if active_deck == "Scan Lab" and not (
        isinstance(getattr(session, "scan_cartography_report", None), dict)
        or isinstance(getattr(session, "scan_cartography_artifact", None), dict)
    ):
        return (
            "Systems Mode",
            "Cartography optional — continue to Systems Mode to close plant/systems, or run a scan first.",
        )

    if active_deck == "Systems Mode":
        if not has_systems_closure(session):
            return (None, "Run precheck/solve to close systems, or continue when ready.")
        return (
            "Opt Lab",
            "Systems closed — open Opt Lab for certified-search entry (propose→CCFS).",
        )

    if active_deck == "Opt Lab":
        return (
            "Pareto Lab",
            "Continue to Pareto Lab for a feasible certified front, or Compare for diffs.",
        )

    if active_deck == "Compare" and not has_compare_slots(session):
        return (None, "Load both comparison artifacts, then review constraint diffs.")

    if idx < len(DECK_LABELS) - 1:
        nxt = DECK_LABELS[idx + 1]
        verb = DECK_SHORT_VERBS.get(nxt, nxt)
        return (nxt, f"Next in workflow: {verb}.")

    return (None, "Workflow complete — seal study in Control Room exports.")


def workflow_progress(session: Any) -> dict[str, bool]:
    """Milestone flags for phase strip styling."""
    evaluated = has_point_evaluation(session)
    scanned = isinstance(getattr(session, "scan_cartography_report", None), dict) or isinstance(
        getattr(session, "scan_cartography_artifact", None), dict
    )
    systems_closed = has_systems_closure(session)
    compared = has_compare_slots(session)
    # Real session fields (Machine Finder archive + exported capsule bytes).
    # Legacy names forge_mf_last_run / forge_last_capsule never existed on DesignSession.
    forged = isinstance(getattr(session, "forge_workbench_run", None), dict) or bool(
        getattr(session, "forge_capsule_zip_bytes", None)
    )
    sealed = isinstance(getattr(session, "cr_study_protocol_last", None), dict)
    return {
        "evaluated": evaluated,
        "scanned": scanned,
        "systems_closed": systems_closed,
        "compared": compared,
        "forged": forged,
        "sealed": sealed,
    }


def phase_completion(phase: int, progress: dict[str, bool]) -> bool:
    if phase == 1:
        return progress.get("evaluated", False)
    if phase == 2:
        # Map & close — cartography sufficient; systems solve completes the phase vividly.
        return progress.get("scanned", False) or progress.get("systems_closed", False)
    if phase == 3:
        return progress.get("compared", False)
    if phase == 4:
        return progress.get("forged", False)
    if phase == 5:
        return progress.get("sealed", False)
    return False
