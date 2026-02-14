from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List


def _stable_hash_json(obj: Any) -> str:
    try:
        s = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(s).hexdigest()
    except Exception:
        return ""


def build_constraint_ledger(constraints_json: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build an explicit margin-ledger view over constraints.

    This is intentionally additive: it does not replace the canonical constraints
    list, it just provides a decision-grade accounting view.
    """
    entries: List[Dict[str, Any]] = []
    violated: List[Dict[str, Any]] = []

    for c in constraints_json or []:
        if not isinstance(c, dict):
            continue
        passed = bool(c.get("passed", True))
        sev = str(c.get("severity", "hard"))
        mf = c.get("margin_frac", None)
        try:
            mf_f = float(mf) if mf is not None else 0.0
        except Exception:
            mf_f = 0.0

        # violation_score: higher = worse
        # - hard constraints dominate
        # - negative margin_frac is a natural severity measure
        if passed:
            score = 0.0
        else:
            base = max(0.0, -mf_f)
            score = (10.0 * base) if sev == "hard" else (1.0 * base)

        e = {
            "name": c.get("name"),
            "group": c.get("group", "general"),
            "severity": sev,
            "passed": passed,
            "value": c.get("value"),
            "limit": c.get("limit"),
            "sense": c.get("sense"),
            "margin": c.get("margin"),
            "margin_frac": c.get("margin_frac"),
            "units": c.get("units", ""),
            "meaning": c.get("meaning", c.get("note", "")),
            "best_knobs": c.get("best_knobs"),
            "dominant_inputs": c.get("dominant_inputs"),
            "violation_score": float(score),
        }
        entries.append(e)
        if not passed:
            violated.append(e)

    # Dominance rank for violated constraints
    violated_sorted = sorted(violated, key=lambda x: float(x.get("violation_score", 0.0)), reverse=True)
    name_to_rank = {str(v.get("name")): i + 1 for i, v in enumerate(violated_sorted)}
    for e in entries:
        if not bool(e.get("passed", True)):
            e["dominance_rank"] = int(name_to_rank.get(str(e.get("name")), 0) or 0)
        else:
            e["dominance_rank"] = None

    top_blockers = violated_sorted[:8]
    ledger = {
        "schema_version": "constraint_ledger.v1",
        "entries": entries,
        "top_blockers": top_blockers,
    }
    ledger["ledger_fingerprint_sha256"] = _stable_hash_json(
        [{
            "name": e.get("name"),
            "severity": e.get("severity"),
            "passed": e.get("passed"),
            "margin": e.get("margin"),
            "margin_frac": e.get("margin_frac"),
            "violation_score": e.get("violation_score"),
        } for e in entries]
    )
    return ledger
