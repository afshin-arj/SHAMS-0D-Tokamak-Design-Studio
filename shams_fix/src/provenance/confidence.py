from __future__ import annotations

"""Authority confidence model (v256.0).

Design goal
-----------
Expose *trust* alongside *feasibility* without modifying physics truth.

This module is strictly post-processing over:
  - authority contracts snapshot (tier/validity/equations)
  - constraint ledger entries (subsystem/authority_tier)

No iteration. Deterministic. Audit-ready.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json


# -----------------------------
# Confidence taxonomy
# -----------------------------

CONFIDENCE_ORDER = {"A": 0, "B": 1, "C": 2, "U": 3}  # U = unknown


def _stable_sha256(obj: Any) -> str:
    try:
        s = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(s).hexdigest()
    except Exception:
        return ""


def tier_to_confidence(tier: str) -> str:
    t = str(tier or "").strip().lower()
    if t in {"authoritative", "authority", "external"}:
        return "A"
    if t in {"semi-authoritative", "semi", "parametric"}:
        return "B"
    if t in {"proxy"}:
        return "C"
    return "U"


def default_maturity_for_tier(tier: str) -> str:
    t = str(tier or "").strip().lower()
    if t in {"authoritative", "authority", "external"}:
        return "established"
    if t in {"semi-authoritative", "semi", "parametric"}:
        return "established"
    if t in {"proxy"}:
        return "extrapolated"
    return "unknown"


# Optional manual overrides (conservative). Keys match authority subsystem keys.
MATURITY_OVERRIDES: Dict[str, str] = {
    "plasma.profiles": "extrapolated",
    "current.drive": "extrapolated",
    "neutronics.proxy": "extrapolated",
    "fuel_cycle.tritium": "extrapolated",
    "plant.availability": "extrapolated",
    "control.rwm": "extrapolated",
}


@dataclass(frozen=True)
class SubsystemConfidence:
    subsystem: str
    tier: str
    maturity: str
    confidence_class: str  # A/B/C/U
    involved: bool
    evidence: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["subsystem"] = str(d.get("subsystem", ""))
        d["tier"] = str(d.get("tier", ""))
        d["maturity"] = str(d.get("maturity", ""))
        d["confidence_class"] = str(d.get("confidence_class", ""))
        d["involved"] = bool(d.get("involved", False))
        d["evidence"] = str(d.get("evidence", ""))
        return d


def _pick_worst_class(classes: List[str]) -> str:
    if not classes:
        return "U"
    # Higher order value = worse
    worst = max(classes, key=lambda c: CONFIDENCE_ORDER.get(str(c), 9))
    return str(worst)


def _involved_subsystems_from_ledger(ledger: Dict[str, Any]) -> Tuple[List[str], Dict[str, int]]:
    """Identify involved subsystems based on constraint ledger.

    Rules (deterministic):
      - include top_blockers subsystems
      - include near-binding hard constraints subsystems (|margin_frac| <= 0.20)
    """
    involved: List[str] = []
    counts: Dict[str, int] = {}
    if not isinstance(ledger, dict):
        return involved, counts
    entries = ledger.get("entries") or []
    top = ledger.get("top_blockers") or []
    # Top blockers
    for e in top:
        if not isinstance(e, dict):
            continue
        s = str(e.get("subsystem", "") or "").strip()
        if not s:
            continue
        involved.append(s)
        counts[s] = counts.get(s, 0) + 2
    # Near-binding
    for e in entries:
        if not isinstance(e, dict):
            continue
        if str(e.get("severity", "hard")).lower() != "hard":
            continue
        mf = e.get("margin_frac", None)
        try:
            mf_f = float(mf) if mf is not None else None
        except Exception:
            mf_f = None
        if mf_f is None:
            continue
        if abs(mf_f) <= 0.20:
            s = str(e.get("subsystem", "") or "").strip()
            if not s:
                continue
            involved.append(s)
            counts[s] = counts.get(s, 0) + 1
    # stable
    involved = sorted(set(involved))
    return involved, counts


def build_authority_confidence_snapshot(
    *,
    authority_contracts: Optional[Dict[str, Any]] = None,
    constraint_ledger: Optional[Dict[str, Any]] = None,
    dominant_mechanism: str = "",
) -> Dict[str, Any]:
    """Build an authority confidence snapshot.

    Parameters
    ----------
    authority_contracts:
        Output of ``src.provenance.authority.authority_snapshot_from_outputs``.
    constraint_ledger:
        Output of ``src.decision.constraint_ledger.build_constraint_ledger``.
    dominant_mechanism:
        Optional mechanism stamp (informational only).
    """
    subs = (authority_contracts or {}).get("subsystems") if isinstance(authority_contracts, dict) else {}
    subs = subs if isinstance(subs, dict) else {}

    involved_subs, counts = _involved_subsystems_from_ledger(constraint_ledger or {})

    per: Dict[str, Dict[str, Any]] = {}
    involved_classes: List[str] = []
    all_classes: List[str] = []

    for key, c in subs.items():
        if not isinstance(c, dict):
            continue
        tier = str(c.get("tier", ""))
        conf = tier_to_confidence(tier)
        maturity = MATURITY_OVERRIDES.get(str(key), default_maturity_for_tier(tier))
        inv = (str(key) in involved_subs)
        evidence = ""
        if inv:
            evidence = f"involved_by_ledger(count={counts.get(str(key), 0)})"
        sc = SubsystemConfidence(
            subsystem=str(key),
            tier=tier,
            maturity=maturity,
            confidence_class=conf,
            involved=inv,
            evidence=evidence,
        )
        per[str(key)] = sc.to_dict()
        all_classes.append(conf)
        if inv:
            involved_classes.append(conf)

    design_conf = _pick_worst_class(involved_classes or all_classes)
    global_conf = _pick_worst_class(all_classes)

    payload = {
        "schema_version": "authority_confidence.v1",
        "design": {
            "design_confidence_class": design_conf,
            "global_confidence_class": global_conf,
            "dominant_mechanism": str(dominant_mechanism or ""),
            "involved_subsystems": involved_subs,
        },
        "subsystems": per,
        # legacy flat keys (backward compatibility)
        "design_confidence_class": design_conf,
        "global_confidence_class": global_conf,
        "dominant_mechanism": str(dominant_mechanism or ""),
        "involved_subsystems": involved_subs,
    }
    payload["stamp_sha256"] = _stable_sha256(payload)
    return payload


def authority_confidence_from_artifact(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Backward-compatible helper used by artifacts and benchmarks.

    Derives a confidence snapshot from a full run artifact (post-processing only).
    """
    art = artifact if isinstance(artifact, dict) else {}
    return build_authority_confidence_snapshot(
        authority_contracts=art.get("authority_contracts") if isinstance(art.get("authority_contracts"), dict) else {},
        constraint_ledger=art.get("constraint_ledger") if isinstance(art.get("constraint_ledger"), dict) else {},
        dominant_mechanism=str(art.get("dominant_mechanism","") or ""),
    )
