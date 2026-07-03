"""Unified constraint pipeline (PROPOSAL-020).

Single entry point builds governance and PROCESS ledger constraint lists and
reports parity between pipelines.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .constraints import GovernanceConstraint, evaluate_constraints
from .system import build_constraints_from_outputs

try:
    from schema.constraints import Constraint as LedgerConstraint  # type: ignore
except ImportError:
    from src.schema.constraints import Constraint as LedgerConstraint  # type: ignore


@dataclass
class ConstraintBundle:
    governance: List[GovernanceConstraint] = field(default_factory=list)
    ledger: List[LedgerConstraint] = field(default_factory=list)
    parity: Dict[str, Any] = field(default_factory=dict)

    @property
    def governance_feasible(self) -> bool:
        from .constraints import constraint_is_hard

        hard = [c for c in self.governance if constraint_is_hard(c)]
        return all(bool(getattr(c, "passed", True)) for c in hard)

    @property
    def ledger_feasible(self) -> bool:
        return all(c.ok for c in self.ledger if c.name != "Radial build closes" or c.value >= 0.5)


def _norm_name(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def diff_constraint_pipelines(
    governance: List[GovernanceConstraint],
    ledger: List[LedgerConstraint],
) -> Dict[str, Any]:
    """Compare governance vs ledger constraint sets (normalized name keys)."""
    gov_by: Dict[str, GovernanceConstraint] = {}
    for c in governance:
        gov_by[_norm_name(c.name)] = c

    led_by: Dict[str, LedgerConstraint] = {}
    for c in ledger:
        led_by[_norm_name(c.name)] = c

    gov_keys: Set[str] = set(gov_by)
    led_keys: Set[str] = set(led_by)
    only_gov = sorted(gov_keys - led_keys)
    only_led = sorted(led_keys - gov_keys)
    shared = sorted(gov_keys & led_keys)

    mismatched: List[Dict[str, Any]] = []
    for key in shared:
        g = gov_by[key]
        l = led_by[key]
        g_ok = bool(getattr(g, "passed", True))
        l_ok = bool(l.ok)
        if g_ok != l_ok:
            mismatched.append(
                {
                    "name": g.name,
                    "governance_passed": g_ok,
                    "ledger_ok": l_ok,
                }
            )

    return {
        "n_governance": len(governance),
        "n_ledger": len(ledger),
        "only_governance": only_gov,
        "only_ledger": only_led,
        "n_shared": len(shared),
        "n_pass_mismatch": len(mismatched),
        "pass_mismatches": mismatched,
        "pipelines_aligned": not only_gov and not only_led and not mismatched,
    }


def build_all_constraints(
    out: Dict[str, Any],
    *,
    design_intent: Optional[str] = None,
    **evaluate_kwargs: Any,
) -> ConstraintBundle:
    """Build governance + ledger constraints and parity report."""
    gov = evaluate_constraints(out, **evaluate_kwargs)
    led = build_constraints_from_outputs(out, design_intent=design_intent)
    parity = diff_constraint_pipelines(gov, led)
    return ConstraintBundle(governance=gov, ledger=led, parity=parity)


def dominant_failing_constraint(bundle: ConstraintBundle, *, use_governance: bool = True) -> Optional[str]:
    from .constraints import constraint_is_hard

    if use_governance:
        for c in bundle.governance:
            if constraint_is_hard(c) and not bool(getattr(c, "passed", True)):
                return str(c.name)
        return None
    for c in bundle.ledger:
        if not c.ok:
            return str(c.name)
    return None
