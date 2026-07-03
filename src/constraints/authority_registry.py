"""Single-source authority constraint registry (PROPOSAL-025)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from schema.constraints import Constraint as LedgerConstraint  # type: ignore
except ImportError:
    from src.schema.constraints import Constraint as LedgerConstraint  # type: ignore

from .constraints import GovernanceConstraint


@dataclass(frozen=True)
class AuthorityCapSpec:
    name: str
    value_key: str
    sense: str
    limit_hi_key: Optional[str] = None
    limit_lo_key: Optional[str] = None
    group: str = "general"
    authority: str = ""
    note: str = ""
    enabled_key: Optional[str] = None
    fraction: Optional[Dict[str, str]] = None


def _safe(out: Dict[str, Any], k: str) -> float:
    try:
        v = float(out.get(k, float("nan")))
        return v if v == v else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def _registry_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "authority_caps.json"


def load_authority_specs() -> List[AuthorityCapSpec]:
    """Load specs from codegen module (PROPOSAL-026) with JSON fallback."""
    try:
        from .data.authority_specs_codegen import REGISTRY_SPECS  # type: ignore

        raw = list(REGISTRY_SPECS)
    except Exception:
        raw = json.loads(_registry_path().read_text(encoding="utf-8"))
    specs: List[AuthorityCapSpec] = []
    for row in raw:
        specs.append(
            AuthorityCapSpec(
                name=str(row["name"]),
                value_key=str(row["value_key"]),
                sense=str(row.get("sense", "<=")),
                limit_hi_key=row.get("limit_hi_key"),
                limit_lo_key=row.get("limit_lo_key"),
                group=str(row.get("group", "general")),
                authority=str(row.get("authority", "")),
                note=str(row.get("note", "")),
                enabled_key=row.get("enabled_key"),
                fraction=row.get("fraction"),
            )
        )
    return specs


def _enabled(out: Dict[str, Any], spec: AuthorityCapSpec) -> bool:
    if not spec.enabled_key:
        return True
    return float(_safe(out, spec.enabled_key)) > 0.5


def _resolve_value(out: Dict[str, Any], spec: AuthorityCapSpec) -> float:
    if spec.fraction:
        num_k = spec.fraction.get("numerator_key", "")
        den_k = spec.fraction.get("denominator_key", "Pin_MW")
        num = _safe(out, num_k)
        den = _safe(out, den_k)
        if den == den and den > 0.0 and num == num:
            return float(num / den)
        return float("nan")
    return _safe(out, spec.value_key)


def _resolve_limit(out: Dict[str, Any], spec: AuthorityCapSpec) -> float:
    if spec.sense == "<=":
        return _safe(out, spec.limit_hi_key or "")
    return _safe(out, spec.limit_lo_key or "")


def evaluate_registry_governance(out: Dict[str, Any]) -> List[GovernanceConstraint]:
    items: List[GovernanceConstraint] = []
    for spec in load_authority_specs():
        if not _enabled(out, spec):
            continue
        val = _resolve_value(out, spec)
        lim = _resolve_limit(out, spec)
        if val != val or lim != lim:
            continue
        if spec.sense == "<=":
            passed = val <= lim + 1e-12
        else:
            passed = val >= lim - 1e-12
        items.append(
            GovernanceConstraint(
                name=spec.name,
                value=float(val),
                limit=float(lim),
                sense=spec.sense,
                passed=bool(passed),
                units="-",
                note=spec.note or f"authority={spec.authority}",
                group=spec.group,
            )
        )
    return items


def evaluate_registry_ledger(out: Dict[str, Any]) -> List[LedgerConstraint]:
    items: List[LedgerConstraint] = []
    for spec in load_authority_specs():
        if not _enabled(out, spec):
            continue
        val = _resolve_value(out, spec)
        lim = _resolve_limit(out, spec)
        if val != val or lim != lim:
            continue
        if spec.sense == "<=":
            items.append(
                LedgerConstraint(
                    name=spec.name,
                    value=float(val),
                    lo=None,
                    hi=float(lim),
                    units="-",
                    description=spec.note or spec.authority,
                )
            )
        else:
            items.append(
                LedgerConstraint(
                    name=spec.name,
                    value=float(val),
                    lo=float(lim),
                    hi=None,
                    units="-",
                    description=spec.note or spec.authority,
                )
            )
    return items


def registry_spec_names() -> List[str]:
    return [s.name for s in load_authority_specs()]
