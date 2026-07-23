"""Certified-front viewer — Opt Lab ↔ Pareto Lab unify (Phase 3.3).

One shared summary + session handoff so Opt Lab and Pareto Lab show the same
VERIFIED / REJECTED + atlas story without duplicating entire decks.

Honesty: Proposed — SHAMS-certified; never true minimum; no user-facing ``vNNN``.
L0 risk: none — display / session meta only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ui_nicegui.lib.certified_opt_honesty import (
    ATLAS_REJECT_NOTE,
    FORBIDDEN_POSITIVE_CLAIMS,
    PROPOSED_CERTIFIED,
    VERIFIED_REJECTED_ATLAS_LINE,
    format_verified_rejected_counts,
)

CERTIFIED_FRONT_SCHEMA = "certified_front_viewer.v1"

CERTIFIED_FRONT_TITLE = "Certified front viewer"

CERTIFIED_FRONT_TAGLINE = (
    f"{PROPOSED_CERTIFIED} front shared by Opt Lab and Pareto Lab — "
    "search proposes outside L0; every claim re-evaluates through frozen truth."
)

CERTIFIED_FRONT_HONESTY = (
    f"{PROPOSED_CERTIFIED}: this viewer summarizes VERIFIED vs REJECTED candidates "
    "with NO-SOLUTION atlas on rejects. Not an authoritative true minimum or "
    "global optimum."
)

CERTIFIED_FRONT_EMPTY = (
    "No certified-front handoff yet — run Pareto Lab, Certified Search / CCFS, "
    "or an Opt Lab SearchDriver shortlist, then return here."
)

HANDOFF_TO_PARETO_LABEL = "Open Pareto Lab on certified front"
HANDOFF_TO_OPT_LAB_LABEL = "Open Opt Lab certified-front viewer"

# Session attribute holding the shared viewer payload.
SESSION_ATTR = "certified_front_handoff"

REQUIRED_PHRASES: List[str] = [
    PROPOSED_CERTIFIED,
    "VERIFIED",
    "REJECTED",
    "atlas",
]

FORBIDDEN_PHRASES: List[str] = list(FORBIDDEN_POSITIVE_CLAIMS)


def certified_front_user_facing_texts() -> List[str]:
    return [
        CERTIFIED_FRONT_TITLE,
        CERTIFIED_FRONT_TAGLINE,
        CERTIFIED_FRONT_HONESTY,
        CERTIFIED_FRONT_EMPTY,
        HANDOFF_TO_PARETO_LABEL,
        HANDOFF_TO_OPT_LAB_LABEL,
        VERIFIED_REJECTED_ATLAS_LINE,
        ATLAS_REJECT_NOTE,
    ]


def _int_or(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def build_certified_front_summary(
    *,
    source: str,
    n_verified: int,
    n_rejected: int,
    n_candidates: Optional[int] = None,
    n_front: Optional[int] = None,
    objective_contract_hash: str = "",
    opt_run_stamp: Optional[Mapping[str, Any]] = None,
    contract_schema: str = "",
    notes: str = "",
    extopt_bridge_note: str = "",
) -> Dict[str, Any]:
    """Build a stable ``certified_front_viewer.v1`` payload for session handoff."""
    total = (
        int(n_candidates)
        if n_candidates is not None
        else (int(n_verified) + int(n_rejected))
    )
    stamp = dict(opt_run_stamp) if isinstance(opt_run_stamp, Mapping) else None
    hash_hex = str(objective_contract_hash or "").strip()
    if not hash_hex and stamp:
        hash_hex = str(stamp.get("objective_contract_hash") or "").strip()
    payload: Dict[str, Any] = {
        "schema": CERTIFIED_FRONT_SCHEMA,
        "source": str(source or "unknown").strip() or "unknown",
        "n_verified": int(n_verified),
        "n_rejected": int(n_rejected),
        "n_candidates": int(total),
        "n_front": int(n_front) if n_front is not None else int(n_verified),
        "objective_contract_hash": hash_hex,
        "contract_schema": str(contract_schema or "").strip(),
        "counts_line": format_verified_rejected_counts(
            n_verified=int(n_verified),
            n_rejected=int(n_rejected),
            n_candidates=int(total),
        ),
        "honesty": CERTIFIED_FRONT_HONESTY,
        "atlas_note": ATLAS_REJECT_NOTE,
        "notes": str(notes or ""),
        "extopt_bridge_note": str(extopt_bridge_note or ""),
        "proposed_certified": True,
        "authoritative_optimum": False,
    }
    if stamp is not None:
        payload["opt_run_stamp"] = stamp
    return payload


def summary_from_ccfs_bundle(
    bundle: Mapping[str, Any],
    *,
    source: str = "ccfs",
) -> Dict[str, Any]:
    """Derive viewer summary from a ``ccfs_verified.v1`` (or similar) bundle."""
    stamp = bundle.get("opt_run_stamp")
    stamp_m = stamp if isinstance(stamp, Mapping) else None
    n_ver = _int_or(bundle.get("n_status_verified"), 0)
    n_rej = _int_or(bundle.get("n_status_rejected"), 0)
    n_cand = _int_or(bundle.get("n_candidates"), n_ver + n_rej)
    rows = bundle.get("verified")
    if isinstance(rows, list) and n_ver == 0 and n_rej == 0:
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            if str(row.get("status") or "").upper() == "VERIFIED":
                n_ver += 1
            else:
                n_rej += 1
        n_cand = len(rows)
    hash_hex = ""
    contract_schema = ""
    if stamp_m:
        hash_hex = str(stamp_m.get("objective_contract_hash") or "")
        raw_c = stamp_m.get("objective_contract")
        if isinstance(raw_c, Mapping):
            contract_schema = str(raw_c.get("schema") or "")
    return build_certified_front_summary(
        source=source,
        n_verified=n_ver,
        n_rejected=n_rej,
        n_candidates=n_cand,
        n_front=n_ver,
        objective_contract_hash=hash_hex,
        opt_run_stamp=stamp_m,
        contract_schema=contract_schema,
        notes="CCFS-certified shortlist (propose-only search upstream).",
    )


def summary_from_pareto_last(
    pareto_last: Mapping[str, Any],
    *,
    source: str = "pareto_lab",
) -> Dict[str, Any]:
    """Derive viewer summary from Pareto Lab ``pareto_last`` artifact."""
    summary = pareto_last.get("summary")
    if not isinstance(summary, Mapping):
        summary = {}
    feasible = pareto_last.get("feasible") or []
    front = pareto_last.get("pareto") or []
    n_samples = _int_or(pareto_last.get("n_samples") or summary.get("n_samples"), 0)
    n_feasible = (
        _int_or(summary.get("n_feasible"), 0)
        if summary
        else (len(feasible) if isinstance(feasible, list) else 0)
    )
    if isinstance(feasible, list) and n_feasible == 0:
        n_feasible = len(feasible)
    n_front = len(front) if isinstance(front, list) else _int_or(summary.get("n_pareto"), 0)
    # Rejected ≈ samples that did not land on the feasible set (when sample count known).
    n_rejected = max(0, int(n_samples) - int(n_feasible)) if n_samples else 0
    n_candidates = int(n_samples) if n_samples else (int(n_feasible) + int(n_rejected))
    objs = pareto_last.get("objectives")
    contract_schema = ""
    hash_hex = str(pareto_last.get("objective_contract_hash") or "").strip()
    if isinstance(objs, Mapping) and objs:
        contract_schema = "pareto_objectives_map"
    stamp = pareto_last.get("opt_run_stamp")
    stamp_m = stamp if isinstance(stamp, Mapping) else None
    if stamp_m and not hash_hex:
        hash_hex = str(stamp_m.get("objective_contract_hash") or "").strip()
    return build_certified_front_summary(
        source=source,
        n_verified=int(n_feasible),
        n_rejected=int(n_rejected),
        n_candidates=int(n_candidates),
        n_front=int(n_front),
        objective_contract_hash=hash_hex,
        opt_run_stamp=stamp_m,
        contract_schema=contract_schema,
        notes=(
            "Pareto Lab feasible set / nondominated front — Proposed — SHAMS-certified "
            "points only; not an authoritative optimum."
        ),
    )


def summary_from_opt_run_stamp(
    stamp: Mapping[str, Any],
    *,
    source: str = "opt_lab",
) -> Dict[str, Any]:
    """Viewer summary from an ``opt_run_stamp.v1`` dict alone."""
    n_ver = _int_or(stamp.get("n_verified") or stamp.get("n_status_verified"), 0)
    n_rej = _int_or(stamp.get("n_rejected") or stamp.get("n_status_rejected"), 0)
    n_cand = _int_or(stamp.get("n_candidates"), n_ver + n_rej)
    raw_c = stamp.get("objective_contract")
    contract_schema = ""
    if isinstance(raw_c, Mapping):
        contract_schema = str(raw_c.get("schema") or "")
    return build_certified_front_summary(
        source=source,
        n_verified=n_ver,
        n_rejected=n_rej,
        n_candidates=n_cand,
        n_front=n_ver,
        objective_contract_hash=str(stamp.get("objective_contract_hash") or ""),
        opt_run_stamp=stamp,
        contract_schema=contract_schema,
        notes="Opt Lab last-run stamp (CCFS-attached).",
    )


def store_certified_front(session: object, summary: Mapping[str, Any]) -> None:
    """Persist shared certified-front handoff on the UI session."""
    if not isinstance(summary, Mapping) or str(summary.get("schema")) != CERTIFIED_FRONT_SCHEMA:
        raise ValueError(f"expected {CERTIFIED_FRONT_SCHEMA} payload")
    setattr(session, SESSION_ATTR, dict(summary))


def get_certified_front(session: object) -> Optional[Dict[str, Any]]:
    raw = getattr(session, SESSION_ATTR, None)
    if isinstance(raw, Mapping) and str(raw.get("schema")) == CERTIFIED_FRONT_SCHEMA:
        return dict(raw)
    return None


def sync_certified_front_from_session(session: object) -> Optional[Dict[str, Any]]:
    """Refresh handoff from Pareto last-run or Opt Lab stamp when present.

    Prefer an already-stored handoff if newer sources are absent; otherwise
    rebuild from ``pareto_last`` then ``opt_lab_last_run_stamp``.
    """
    pareto_last = getattr(session, "pareto_last", None)
    if isinstance(pareto_last, Mapping) and (
        pareto_last.get("feasible") is not None or pareto_last.get("pareto") is not None
        or pareto_last.get("summary") is not None
    ):
        summary = summary_from_pareto_last(pareto_last)
        store_certified_front(session, summary)
        return summary

    stamp = getattr(session, "opt_lab_last_run_stamp", None)
    if isinstance(stamp, Mapping) and stamp:
        summary = summary_from_opt_run_stamp(stamp)
        store_certified_front(session, summary)
        return summary

    return get_certified_front(session)


def apply_handoff_to_pareto(session: object) -> None:
    """Prime Pareto Lab to Interpret (front-reading) after Opt Lab handoff."""
    session.pareto_workflow_step = "3 · Interpret & Audit"  # type: ignore[attr-defined]
    # Keep decision language aligned with reading a front, not re-sampling.
    if hasattr(session, "pareto_decision_state"):
        session.pareto_decision_state = "Audit mechanisms & knees"  # type: ignore[attr-defined]


def apply_handoff_to_opt_lab(session: object) -> None:
    """Prime Opt Lab viewer focus (session flag for panel expansion)."""
    session.opt_lab_show_certified_front = True  # type: ignore[attr-defined]


def format_front_caption(summary: Optional[Mapping[str, Any]]) -> str:
    if not isinstance(summary, Mapping):
        return CERTIFIED_FRONT_EMPTY
    line = str(summary.get("counts_line") or "").strip()
    src = str(summary.get("source") or "").strip()
    hash_hex = str(summary.get("objective_contract_hash") or "").strip()
    short = (hash_hex[:12] + "…") if len(hash_hex) > 12 else hash_hex
    bits = [line or CERTIFIED_FRONT_EMPTY]
    if src:
        bits.append(f"source={src}")
    if short:
        bits.append(f"contract={short}")
    n_front = summary.get("n_front")
    if n_front is not None:
        bits.append(f"front_points={int(n_front)}")
    return " · ".join(bits)


def atlas_reject_hint(summary: Optional[Mapping[str, Any]]) -> str:
    if not isinstance(summary, Mapping):
        return ATLAS_REJECT_NOTE
    n_rej = _int_or(summary.get("n_rejected"), 0)
    if n_rej <= 0:
        return (
            f"No REJECTED rows in this handoff — still {PROPOSED_CERTIFIED}; "
            "not an authoritative optimum."
        )
    return ATLAS_REJECT_NOTE


def frontier_check_gates() -> Tuple[str, ...]:
    """Modules / tests that ``/pareto-frontier-check`` expects green."""
    return (
        "src.extopt.frontier_intake_v406",
        "tests.test_extopt_frontier_intake_v406",
    )
