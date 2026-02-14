"""External optimization interpretation layer (v331.0).

This module is **interpretation-only**:

- It never changes physics truth.
- It performs no optimization.
- It consumes optimizer traces / candidate artifacts and produces
  audit-friendly summaries: feasibility attrition, dominance histograms,
  and narrative explanations.

The layer is intentionally deterministic and replayable.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import json


def _as_str(x: Any) -> str:
    return "" if x is None else str(x)


def load_optimizer_registry(repo_root: Path) -> Dict[str, Any]:
    """Load the optimizer capability registry contract (metadata only)."""
    p = repo_root / "contracts" / "optimizer_capability_registry.json"
    if not p.exists():
        return {
            "schema_version": "shams.optimizer_capability_registry.v1",
            "optimizers": {},
        }
    return json.loads(p.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class AttritionSummary:
    n_total: int
    n_feasible: int
    n_infeasible: int
    by_dominant_authority: Dict[str, int]
    by_dominant_constraint: Dict[str, int]


def summarize_attrition_from_trace(trace: Mapping[str, Any]) -> AttritionSummary:
    """Compute feasibility attrition statistics from optimizer_trace.json.

    The reference trace schema includes (per candidate):
      - verdict
      - min_hard_margin
      - dominant_mechanism (or dominant_authority)
      - dominant_constraint
    """
    cands = trace.get("candidates")
    if not isinstance(cands, list):
        cands = []

    n_total = 0
    n_feas = 0
    by_auth: Dict[str, int] = {}
    by_con: Dict[str, int] = {}

    for c in cands:
        if not isinstance(c, Mapping):
            continue
        n_total += 1
        verdict = _as_str(c.get("verdict")).upper()
        is_feas = verdict in {"FEASIBLE", "OK", "PASS", "TRUE"}
        if is_feas:
            n_feas += 1

        auth = _as_str(c.get("dominant_authority") or c.get("dominant_mechanism") or "UNKNOWN")
        con = _as_str(c.get("dominant_constraint") or c.get("dominant_constraint_id") or "UNKNOWN")

        # Count dominant killers only among infeasible points to explain attrition.
        if not is_feas:
            by_auth[auth] = by_auth.get(auth, 0) + 1
            by_con[con] = by_con.get(con, 0) + 1

    return AttritionSummary(
        n_total=n_total,
        n_feasible=n_feas,
        n_infeasible=max(0, n_total - n_feasible),
        by_dominant_authority=dict(sorted(by_auth.items(), key=lambda kv: (-kv[1], kv[0]))),
        by_dominant_constraint=dict(sorted(by_con.items(), key=lambda kv: (-kv[1], kv[0]))),
    )


def build_narrative(trace: Mapping[str, Any], attr: AttritionSummary, *, top_k: int = 3) -> str:
    """Build a reviewer-friendly narrative explaining why an optimizer run succeeded or failed."""
    optimizer = _as_str(trace.get("optimizer") or "(unknown optimizer)")
    n = attr.n_total
    if n <= 0:
        return f"{optimizer}: no candidates present in trace."

    feas = attr.n_feasible
    infeas = attr.n_infeasible
    feas_frac = feas / n if n else 0.0

    lines: List[str] = []
    lines.append(f"Optimizer `{optimizer}` evaluated {n} candidates.")
    lines.append(f"Feasible: {feas} ({feas_frac*100:.1f}%). Infeasible: {infeas}.")

    if infeas <= 0:
        lines.append("No feasibility attrition observed. Interpretation focus: objective trade-offs among feasible set.")
        return "\n".join(lines)

    # Dominant-killer summary
    killers = list(attr.by_dominant_authority.items())[: max(1, int(top_k))]
    if killers:
        parts = [f"{k} ({v})" for k, v in killers if v > 0]
        if parts:
            lines.append("Dominant feasibility killers (count among infeasible): " + ", ".join(parts) + ".")

    cons = list(attr.by_dominant_constraint.items())[: max(1, int(top_k))]
    if cons:
        parts2 = [f"{k} ({v})" for k, v in cons if v > 0 and k != "UNKNOWN"]
        if parts2:
            lines.append("Most common limiting constraints: " + ", ".join(parts2) + ".")

    lines.append("SHAMS note: these explanations are observational; physics truth remains frozen.")
    return "\n".join(lines)


def interpret_optimizer_trace(trace: Mapping[str, Any]) -> Dict[str, Any]:
    """Main entrypoint: turn a trace into an interpretation report dict."""
    attr = summarize_attrition_from_trace(trace)
    narrative = build_narrative(trace, attr)
    return {
        "schema_version": "shams.extopt_interpretation_report.v1",
        "optimizer": _as_str(trace.get("optimizer")),
        "n_total": attr.n_total,
        "n_feasible": attr.n_feasible,
        "n_infeasible": attr.n_infeasible,
        "attrition_by_dominant_authority": attr.by_dominant_authority,
        "attrition_by_dominant_constraint": attr.by_dominant_constraint,
        "narrative": narrative,
    }
