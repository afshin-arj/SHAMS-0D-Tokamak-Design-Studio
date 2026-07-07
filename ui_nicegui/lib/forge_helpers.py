"""Reactor Design Forge helpers."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

try:
    from src.models.inputs import PointInputs
    from tools.sandbox.intent_compiler import compile_intent_to_candidate
except ImportError:
    from models.inputs import PointInputs  # type: ignore
    from tools.sandbox.intent_compiler import compile_intent_to_candidate  # type: ignore

from ui_nicegui.evaluate import ui_evaluate
from ui_nicegui.lib.verdict_core import constraint_table_rows, verdict_summary

FORGE_DECKS = ["Intent Compiler", "Machine Finder", "Capsules"]
FORGE_RUNLOCK_OWNER = "ReactorDesignForge"


def compile_forge_candidate(
    base,
    *,
    pfus_target_mw: float,
    q_target: float,
    overrides: Optional[Dict[str, Any]] = None,
) -> dict:
    status, payload = compile_intent_to_candidate(
        base,
        Pfus_target_MW=float(pfus_target_mw),
        Q_target=float(q_target),
        overrides=overrides or {},
    )
    return {"status": status, **payload}


def audit_candidate_inputs(candidate: dict, *, origin: str = "NiceGUI:Forge audit") -> dict:
    pi = PointInputs(**dict(candidate))
    out = ui_evaluate(pi, origin=origin)
    summary = verdict_summary(out)
    rows = constraint_table_rows(out)
    dom = None
    for r in rows:
        if not r.get("passed"):
            dom = r.get("name")
            break
    return {
        "outputs": out,
        "verdict": summary,
        "dominant_constraint": dom or summary.get("dominant"),
        "feasible": bool(summary.get("feasible")),
        "constraint_rows": rows[:20],
    }


def summarize_forge_state(compiler_last: Optional[dict], audit: Optional[dict]) -> Dict[str, Any]:
    if not isinstance(compiler_last, dict):
        return {"loaded": False}
    status = str(compiler_last.get("status") or "?")
    out: Dict[str, Any] = {
        "loaded": True,
        "compiler_status": status,
        "has_candidate": isinstance(compiler_last.get("candidate_inputs"), dict),
    }
    if isinstance(audit, dict) and audit.get("verdict"):
        v = audit["verdict"]
        out["audit_verdict"] = v.get("verdict", "UNKNOWN")
        out["audit_feasible"] = bool(v.get("feasible"))
        out["dominant"] = audit.get("dominant_constraint") or v.get("dominant")
    elif status == "NO_SOLUTION":
        out["audit_verdict"] = "NO-SOLUTION"
        out["dominant"] = compiler_last.get("reason") or "(compile failed)"
    else:
        out["audit_verdict"] = "Not audited"
        out["dominant"] = "-"
    return out


def candidate_to_json_bytes(candidate: dict) -> bytes:
    return json.dumps(candidate, indent=2, sort_keys=True, default=str).encode("utf-8")


def merge_candidate_to_session_inputs(session_inputs: dict, candidate: dict) -> dict:
    merged = dict(session_inputs)
    merged.update(candidate)
    return merged
