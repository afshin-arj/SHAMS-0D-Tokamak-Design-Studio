"""Opt Lab champion warm-start — Certified Optimizer Phase 1.4.

One-click load of champion ``PointInputs`` as a **search seed** (propose-only).
Reuses Studio champion templates (`studio_entry.apply_champion_template` /
``studies.champion_cases``). Does **not** evaluate, certify, or run a search —
the user must still Evaluate / Certify / Run on the chosen path.

L0 risk: none. No ``vNNN`` labels; never claims a true optimum.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from ui_nicegui.lib.studio_entry import (
    apply_champion_template,
    champion_template_options,
)

WARM_START_TITLE = "Champion warm-start (search seed)"

WARM_START_TAGLINE = (
    "Load a champion PointInputs basis as the Opt Lab / Systems Mode / Pareto seed — "
    "propose-only; you still Evaluate, Certify, or Run search."
)

WARM_START_HONESTY = (
    "Warm-start proposes a seed only — not a Proposed — SHAMS-certified result and "
    "not an authoritative true minimum. Run certify/evaluate/search next."
)

# Session meta schema (UI-only; never L0).
WARM_START_META_SCHEMA = "opt_lab_warm_start.v1"

# Knobs used to prove the seed landed in session + search bounds.
_SEED_KNOB_KEYS = ("R0_m", "Bt_T", "Ip_MA", "Paux_MW", "fG", "Ti_keV")


def warm_start_user_facing_texts() -> List[str]:
    """All user-facing warm-start strings (honesty / version-tag locks)."""
    return [
        WARM_START_TITLE,
        WARM_START_TAGLINE,
        WARM_START_HONESTY,
        *[str(o.get("label") or "") for o in champion_template_options()],
    ]


def get_warm_start_meta(session: object) -> Optional[Mapping[str, Any]]:
    raw = getattr(session, "opt_lab_warm_start_meta", None)
    return dict(raw) if isinstance(raw, Mapping) else None


def get_warm_start_case_id(session: object) -> Optional[str]:
    meta = get_warm_start_meta(session)
    if meta and meta.get("case_id"):
        return str(meta["case_id"])
    raw = getattr(session, "opt_lab_warm_start_case_id", None)
    return str(raw) if raw else None


def warm_start_summary(session: object) -> str:
    """One-line status for Opt Lab / Systems / Pareto panels."""
    meta = get_warm_start_meta(session)
    if not meta:
        return "No champion search seed loaded yet."
    case_id = str(meta.get("case_id") or "?")
    label = str(meta.get("label") or case_id)
    n = int(meta.get("override_count") or 0)
    return (
        f"Search seed: {label} ({case_id}) — {n} champion inputs proposed; "
        "not yet certified."
    )


def _force_pd_solver_bounds_from_inputs(session: Any) -> None:
    """Reset Point Designer Ip/fG search bounds from the warm-start seed."""
    try:
        ip = float(session.inputs.get("Ip_MA", 8.0))
    except (TypeError, ValueError):
        ip = 8.0
    try:
        fg = float(session.inputs.get("fG", 0.8))
    except (TypeError, ValueError):
        fg = 0.8
    session.pd_ip_min = max(0.1, 0.80 * ip)
    session.pd_ip_max = max(session.pd_ip_min + 0.1, 1.20 * ip)
    session.pd_fg_min = max(0.0, fg - 0.20)
    session.pd_fg_max = min(2.0, max(session.pd_fg_min + 0.05, fg + 0.20))


def _refresh_search_bounds_from_seed(session: Any) -> Dict[str, Any]:
    """Clear stale Systems overrides; re-seed Pareto sampling box from baseline."""
    # Systems Mode: drop prior x0/lo/hi so resolve_* picks champion baseline.
    session.systems_bounds_overrides = {}
    session.systems_base_overrides = {}
    session.systems_inputs_overrides = {}
    session.systems_recovery_seed_mode = "Point Designer baseline"

    # Pareto Lab: force fresh defaults around the new seed (not sanitize-expand stale).
    bounds_snapshot: Dict[str, Any] = {}
    try:
        from ui_nicegui.lib.pareto_helpers import default_bounds

        base = session.build_point_inputs()
        fresh = default_bounds(base)
        session.pareto_bounds = dict(fresh)
        bounds_snapshot = {
            k: [float(lo), float(hi)] for k, (lo, hi) in fresh.items()
        }
    except Exception:
        session.pareto_bounds = None

    return bounds_snapshot


def _seed_knob_snapshot(session: Any) -> Dict[str, float]:
    out: Dict[str, float] = {}
    inp = getattr(session, "inputs", {}) or {}
    for key in _SEED_KNOB_KEYS:
        try:
            out[key] = float(inp[key])
        except (KeyError, TypeError, ValueError):
            continue
    return out


def apply_champion_warm_start(session: Any, case_id: str) -> Dict[str, Any]:
    """Load champion PointInputs as search seed (propose-only).

    Steps:
      1. ``apply_champion_template`` — deterministic session PointInputs + intent
      2. Force PD Ip/fG solver bounds from the seed
      3. Clear Systems Mode bound overrides; set recovery seed = PD baseline
      4. Refresh Pareto sampling bounds from the new baseline
      5. Stamp session meta (no evaluation, no CCFS, no SearchDriver)

    Returns a summary dict suitable for UI notify + lock tests.
    """
    options = {str(o["case_id"]): o for o in champion_template_options()}
    if str(case_id) not in options:
        raise KeyError(f"Unknown champion case for warm-start: {case_id!r}")

    overrides = apply_champion_template(session, str(case_id))
    _force_pd_solver_bounds_from_inputs(session)
    pareto_bounds = _refresh_search_bounds_from_seed(session)
    knobs = _seed_knob_snapshot(session)

    opt = options[str(case_id)]
    meta: Dict[str, Any] = {
        "schema": WARM_START_META_SCHEMA,
        "case_id": str(case_id),
        "label": str(opt.get("label") or case_id),
        "family": str(opt.get("family") or ""),
        "design_intent": str(opt.get("design_intent") or ""),
        "expect_hard_feasible": opt.get("expect_hard_feasible"),
        "override_count": int(len(overrides)),
        "seed_knobs": knobs,
        "pareto_bounds": pareto_bounds,
        "propose_only": True,
        "certified": False,
        "evaluated": False,
    }
    session.opt_lab_warm_start_case_id = str(case_id)
    session.opt_lab_warm_start_meta = dict(meta)
    return meta
