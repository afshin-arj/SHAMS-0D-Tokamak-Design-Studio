"""Constraint pipeline diff dossier (PROPOSAL-027 core)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from constraints.authority_registry import evaluate_registry_governance, evaluate_registry_ledger
    from constraints.constraints import evaluate_constraints
    from constraints.system import build_constraints_from_outputs
    from constraints.unified import build_all_constraints
except ImportError:
    from src.constraints.authority_registry import evaluate_registry_governance, evaluate_registry_ledger
    from src.constraints.constraints import evaluate_constraints
    from src.constraints.system import build_constraints_from_outputs
    from src.constraints.unified import build_all_constraints


def _rows_governance(constraints: List[Any]) -> List[Dict[str, Any]]:
    rows = []
    for c in constraints:
        rows.append(
            {
                "name": str(getattr(c, "name", "")),
                "value": float(getattr(c, "value", float("nan"))),
                "limit": float(getattr(c, "limit", float("nan"))),
                "passed": bool(getattr(c, "passed", True)),
            }
        )
    rows.sort(key=lambda r: r["name"])
    return rows


def _rows_ledger(constraints: List[Any]) -> List[Dict[str, Any]]:
    rows = []
    for c in constraints:
        rows.append(
            {
                "name": str(c.name),
                "value": float(c.value),
                "ok": bool(c.ok),
                "lo": c.lo,
                "hi": c.hi,
            }
        )
    rows.sort(key=lambda r: r["name"])
    return rows


def build_pipeline_diff_dossier(
    out: Dict[str, Any],
    *,
    design_intent: Optional[str] = None,
) -> Dict[str, Any]:
    """Structured diff between registry, legacy governance, and ledger pipelines."""
    reg_gov = evaluate_registry_governance(out)
    reg_led = evaluate_registry_ledger(out)
    leg_gov = evaluate_constraints(out)
    leg_led = build_constraints_from_outputs(out, design_intent=design_intent)
    bundle = build_all_constraints(out, design_intent=design_intent)
    return {
        "registry_governance": _rows_governance(reg_gov),
        "legacy_governance": _rows_governance(leg_gov),
        "merged_governance": _rows_governance(bundle.governance),
        "registry_ledger": _rows_ledger(reg_led),
        "legacy_ledger": _rows_ledger(leg_led),
        "merged_ledger": _rows_ledger(bundle.ledger),
        "parity": bundle.parity,
    }
