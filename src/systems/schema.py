"""Systems Mode artifact schema utilities.

Freeze contract:
- All Systems artifacts (systems_state, traces, candidates, run cards) use schema_version=1.
- This module provides a tiny upgrader for back-compat with pre-freeze artifacts.
"""

from __future__ import annotations
from typing import Any, Dict, List

SCHEMA_VERSION = 1

# Keep this list intentionally small + stable. Unknown strings should be normalized
# to "unknown" rather than becoming de-facto new schema values.
REASON_CODES_V1 = {
    # generic
    "ok",
    "unknown",
    "exception",
    "invalid_input",
    # precheck
    "precheck_ok",
    "precheck_infeasible",
    "precheck_inconclusive",
    # recovery
    "seed_feasible",
    "no_feasible_found",
    # feasible search
    "multi_seed_feasible",
    "multi_seed_best_compromise",
    # solve
    "solve_ok",
    "solve_fail",
    # export
    "export_ok",
    "export_fail",
}

def normalize_reason_code(code: Any) -> str:
    """Normalize a reason string into the frozen v1 reason code vocabulary."""
    s = "" if code is None else str(code).strip()
    if s in REASON_CODES_V1:
        return s
    # Common legacy reason strings
    legacy_map = {
        "precheck_infeasible": "precheck_infeasible",
        "ok": "ok",
        "seed_feasible": "seed_feasible",
        "no_feasible_found": "no_feasible_found",
        "multi_seed_best_compromise": "multi_seed_best_compromise",
        "multi_seed_feasible": "multi_seed_feasible",
    }
    if s in legacy_map:
        return legacy_map[s]
    if s.startswith("precheck"):
        return "precheck_infeasible" if "infeas" in s else "precheck_inconclusive"
    if "exception" in s.lower():
        return "exception"
    return "unknown"

def freeze_contract() -> Dict[str, Any]:
    """Machine-readable Systems Mode freeze contract embedded in artifacts."""
    return {
        "schema_version": SCHEMA_VERSION,
        "reason_codes": sorted(REASON_CODES_V1),
        "notes": [
            "Systems Mode artifacts use schema_version=1.",
            "reason_code is normalized to a fixed vocabulary.",
            "UI state embedding is best-effort + sanitized; it must not affect physics.",
        ],
    }

def _upgrade_run_card(card: Any) -> Any:
    if not isinstance(card, dict):
        return card
    card.setdefault("schema_version", SCHEMA_VERSION)
    # Back-compat: older cards used 'reason' instead of 'reason_code'
    if "reason_code" not in card and "reason" in card:
        card["reason_code"] = str(card.get("reason") or "")
    # Freeze normalization
    card["reason_code"] = normalize_reason_code(card.get("reason_code"))
    return card

def validate_systems_artifact(obj: Any) -> List[str]:
    """Return a list of human-readable schema issues (empty = OK)."""
    issues: List[str] = []
    if not isinstance(obj, dict):
        return ["artifact is not a dict"]
    v = obj.get("schema_version")
    try:
        v_int = int(v)
    except Exception:
        v_int = None
    if v_int != SCHEMA_VERSION:
        issues.append(f"schema_version must be {SCHEMA_VERSION} (got {v!r})")

    cards = obj.get("run_cards")
    if cards is None:
        # tolerate older key names, but warn
        if any(k in obj for k in ("systems_run_cards", "history_cards")):
            issues.append("run_cards key missing (legacy key present)")
    elif not isinstance(cards, list):
        issues.append("run_cards must be a list")
    else:
        for i, c in enumerate(cards[:200]):
            if not isinstance(c, dict):
                issues.append(f"run_cards[{i}] is not a dict")
                continue
            rc = normalize_reason_code(c.get("reason_code"))
            if rc == "unknown" and c.get("reason_code") not in (None, "", "unknown"):
                issues.append(f"run_cards[{i}].reason_code not in frozen vocabulary: {c.get('reason_code')!r}")

    # Ensure freeze contract is present (non-fatal)
    if "freeze_contract" not in obj:
        issues.append("freeze_contract missing")
    return issues

def upgrade_systems_artifact(obj: Any) -> Any:
    """Upgrade a Systems artifact dict to the current schema.

    Safe to call on already-upgraded artifacts (idempotent).
    """
    if not isinstance(obj, dict):
        return obj

    v = obj.get("schema_version")
    # Accept any missing/legacy schema and normalize to v1
    if v is None or (isinstance(v, str) and v.strip() == ""):
        obj["schema_version"] = SCHEMA_VERSION
    else:
        try:
            obj["schema_version"] = int(v)
        except Exception:
            obj["schema_version"] = SCHEMA_VERSION

    # Upgrade run cards
    cards = obj.get("run_cards") or obj.get("systems_run_cards") or obj.get("history_cards")
    if isinstance(cards, list):
        obj["run_cards"] = [_upgrade_run_card(c) for c in cards]

    # Upgrade candidates
    cands = obj.get("candidates")
    if isinstance(cands, list):
        for c in cands:
            if isinstance(c, dict):
                c.setdefault("schema_version", SCHEMA_VERSION)

    # Upgrade traces
    traces = obj.get("traces")
    if isinstance(traces, dict):
        traces.setdefault("schema_version", SCHEMA_VERSION)
        # Common nested trace containers
        for k in ("precheck_trace", "recovery_trace", "search_trace", "trace"):
            if isinstance(traces.get(k), dict):
                traces[k].setdefault("schema_version", SCHEMA_VERSION)

    return obj
