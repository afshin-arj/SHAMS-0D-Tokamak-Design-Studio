"""Certified Optimizer UI honesty copy — Phase 1.3.

Shared, version-tag-free phrases for Opt Lab, Systems Mode, Pareto Lab, and
Control Room Certified Search. Pure strings (no NiceGUI/Streamlit imports) so
lock tests and both UIs can share one source of truth.

Stance: docs/CERTIFIED_OPTIMIZER.md — Proposed — SHAMS-certified; never claim
a true/global minimum as positive language; VERIFIED vs REJECTED + atlas on
rejects; no ``vNNN`` in user-facing labels.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Mapping, Sequence

# Canonical required label (stance-approved).
PROPOSED_CERTIFIED = "Proposed — SHAMS-certified"
PROPOSED_OPTIMUM_CERTIFIED = "Proposed optimum — SHAMS-certified"

# Shared banner used across certified-search surfaces.
HONESTY_BANNER = (
    f"{PROPOSED_CERTIFIED}: search proposes PointInputs outside L0; "
    "every claim is re-evaluated by frozen truth (CCFS / Evaluator). "
    "Not an authoritative true minimum or global optimum."
)

VERIFIED_REJECTED_ATLAS_LINE = (
    "Read VERIFIED vs REJECTED — rejects carry NO-SOLUTION atlas mechanism attribution."
)

PITCH_LINE = "PROCESS optimizes-and-believes; SHAMS searches-and-certifies."

# Deck-scoped one-liners (still share the required phrase).
SYSTEMS_MODE_HONESTY = (
    f"{PROPOSED_CERTIFIED} — Systems Mode proposes target-solve / recovery inputs only; "
    "L0 re-evaluates. " + VERIFIED_REJECTED_ATLAS_LINE
)

PARETO_LAB_HONESTY = (
    f"{PROPOSED_CERTIFIED} — Pareto Lab maps the feasible set / front; "
    "not an authoritative optimum. " + VERIFIED_REJECTED_ATLAS_LINE
)

CERTIFIED_SEARCH_HONESTY = (
    f"{PROPOSED_CERTIFIED} — Certified Search is budgeted multi-knob propose-only; "
    "each candidate is frozen-re-eval'd. " + VERIFIED_REJECTED_ATLAS_LINE
)

# Results panel labels (Certified Search).
BEST_PROPOSED_LABEL = f"Best {PROPOSED_CERTIFIED} candidate"
VERIFIED_KPI_LABEL = "VERIFIED"
REJECTED_KPI_LABEL = "REJECTED"
ATLAS_REJECT_NOTE = (
    "REJECTED / infeasible candidates: inspect NO-SOLUTION atlas mechanism attribution "
    "(do not treat FoM as overriding hard constraints)."
)

REQUIRED_PHRASES: List[str] = [
    PROPOSED_CERTIFIED,
    "VERIFIED",
    "REJECTED",
    "atlas",
]

# Forbidden as *positive* claims. Negated warnings ("never true minimum") are OK.
FORBIDDEN_POSITIVE_CLAIMS: List[str] = [
    "true minimum",
    "true global optimum",
    "true global minimum",
    "SHAMS found the true",
]

# Nearby ban markers that make a forbidden phrase a warning, not a claim.
BAN_MARKERS: tuple[str, ...] = (
    "never",
    "not an",
    "not a",
    "forbidden",
    "do not",
    "does not",
    "don't",
    "must not",
    "without claiming",
    "anti-pattern",
)

# Relative paths under SHAMS-0D scanned by honesty lock tests.
HONESTY_SCAN_RELPATHS: List[str] = [
    "ui_nicegui/lib/certified_opt_honesty.py",
    "ui_nicegui/lib/opt_lab_entry.py",
    "ui_nicegui/components/opt_lab_entry_panel.py",
    "ui_nicegui/components/certified_opt_honesty_banner.py",
    "ui_nicegui/decks/opt_lab/__init__.py",
    "ui_nicegui/decks/systems_mode/__init__.py",
    "ui_nicegui/lib/systems_labels.py",
    "ui_nicegui/decks/pareto_lab/__init__.py",
    "ui_nicegui/lib/pareto_labels.py",
    "ui_nicegui/decks/control_room/certified_search.py",
    "ui/decks/opt_lab.py",
    "ui/decks/systems_mode.py",
    "ui/decks/pareto_lab.py",
    "ui/decks/control_room.py",
]


def all_honesty_user_facing_texts() -> List[str]:
    """Canonical user-facing honesty strings (for version-tag + phrase locks)."""
    return [
        PROPOSED_CERTIFIED,
        PROPOSED_OPTIMUM_CERTIFIED,
        HONESTY_BANNER,
        VERIFIED_REJECTED_ATLAS_LINE,
        PITCH_LINE,
        SYSTEMS_MODE_HONESTY,
        PARETO_LAB_HONESTY,
        CERTIFIED_SEARCH_HONESTY,
        BEST_PROPOSED_LABEL,
        VERIFIED_KPI_LABEL,
        REJECTED_KPI_LABEL,
        ATLAS_REJECT_NOTE,
    ]


def honesty_banner_for(deck_key: str) -> str:
    """Return the honesty banner for a certified-search surface."""
    key = str(deck_key or "").strip().lower().replace(" ", "_")
    if key in ("systems_mode", "systems"):
        return SYSTEMS_MODE_HONESTY
    if key in ("pareto_lab", "pareto"):
        return PARETO_LAB_HONESTY
    if key in ("certified_search", "control_room_certified_search", "control_room"):
        return CERTIFIED_SEARCH_HONESTY
    return HONESTY_BANNER


def format_verified_rejected_counts(
    *,
    n_verified: int,
    n_rejected: int,
    n_candidates: int | None = None,
) -> str:
    """One-line VERIFIED / REJECTED summary (no version tags)."""
    total = n_candidates if n_candidates is not None else (n_verified + n_rejected)
    return (
        f"{VERIFIED_KPI_LABEL}={int(n_verified)} · "
        f"{REJECTED_KPI_LABEL}={int(n_rejected)} · "
        f"candidates={int(total)} — {PROPOSED_CERTIFIED}"
    )


def counts_from_pass_fail_rows(rows: Sequence[Mapping[str, object]]) -> tuple[int, int]:
    """Map legacy PASS/FAIL rows to VERIFIED/REJECTED counts."""
    n_ok = 0
    n_bad = 0
    for row in rows:
        verdict = str(row.get("verdict") or row.get("status") or "").upper()
        if verdict in ("PASS", "VERIFIED", "FEASIBLE", "OK"):
            n_ok += 1
        else:
            n_bad += 1
    return n_ok, n_bad


def scan_file_texts(repo_root: Path) -> List[tuple[str, str]]:
    """Load honesty-scan targets as (relpath, text) pairs."""
    out: List[tuple[str, str]] = []
    root = Path(repo_root)
    for rel in HONESTY_SCAN_RELPATHS:
        path = root / rel
        if path.is_file():
            out.append((rel, path.read_text(encoding="utf-8")))
    return out
