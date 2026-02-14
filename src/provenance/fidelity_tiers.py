from __future__ import annotations

"""Multi-fidelity authority tiering (v366.0).

Design goal
-----------
Expose an explicit *fidelity tier* for SHAMS evaluations so that:
  - users can report the realism level (conceptual vs engineering vs industrial vs licensing-grade),
  - atlases/frontiers can be conditioned by fidelity class,
  - parity studies can be tier-aware,
  - reviewers can distinguish governance depth from physics-fidelity depth.

This module is strictly post-processing over:
  - authority contracts snapshot (tier/validity/equations)
  - (optional) constraint ledger involvement

No solvers. No iteration. Deterministic. Audit-ready.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json


FIDELITY_LABELS = {
    0: "T0 (Conceptual scaling)",
    1: "T1 (Engineering-constrained)",
    2: "T2 (Industrial-grade)",
    3: "T3 (Licensing-grade)",
}


def _stable_sha256(obj: Any) -> str:
    try:
        s = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(s).hexdigest()
    except Exception:
        return ""


def _tier_default_from_authority_tier(authority_tier: str) -> int:
    """Conservative default mapping (deterministic).

    Authority tier is a trust/authority classification; fidelity is a realism/TRL classification.
    Mapping is intentionally conservative:
      proxy -> T0
      semi-authoritative -> T1
      authoritative -> T2
    T3 is reserved for explicitly licensing-grade closures.
    """
    t = str(authority_tier or "").strip().lower()
    if t in {"authoritative", "authority", "external"}:
        return 2
    if t in {"semi-authoritative", "semi", "parametric"}:
        return 1
    if t in {"proxy"}:
        return 0
    return 0


# Manual overrides, aligned with SHAMS roadmap semantics.
# Keys must match authority subsystem keys.
FIDELITY_OVERRIDES: Dict[str, int] = {
    # Governance & certification layers can reach industrial/licensing grade even when using proxies.
    "scan.cartography": 2,
    # Tight closures (if present in evaluator outputs) are considered industrial-grade.
    "fuel_cycle.tritium": 2,
    "plant.availability": 2,
    # v367.0 materials replacement cadence closure: industrial-grade bookkeeping layer.
    "materials.lifetime_closure": 2,
    # Licensing evidence packs are export/governance; fidelity relates to evidence-grade.
    # Kept at T2 unless explicitly upgraded to T3 in future.
}


def _involved_subsystems_from_ledger(ledger: Dict[str, Any]) -> Tuple[List[str], Dict[str, int]]:
    """Deterministically identify involved subsystems based on constraint ledger."""
    involved: List[str] = []
    counts: Dict[str, int] = {}
    if not isinstance(ledger, dict):
        return involved, counts

    entries = ledger.get("entries") or []
    top = ledger.get("top_blockers") or []

    for e in top:
        if not isinstance(e, dict):
            continue
        s = str(e.get("subsystem", "") or "").strip()
        if not s:
            continue
        involved.append(s)
        counts[s] = counts.get(s, 0) + 2

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

    involved = sorted(set(involved))
    return involved, counts


@dataclass(frozen=True)
class SubsystemFidelity:
    subsystem: str
    authority_tier: str
    fidelity_tier: int
    fidelity_label: str
    involved: bool
    evidence: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["subsystem"] = str(d.get("subsystem", ""))
        d["authority_tier"] = str(d.get("authority_tier", ""))
        d["fidelity_tier"] = int(d.get("fidelity_tier", 0))
        d["fidelity_label"] = str(d.get("fidelity_label", ""))
        d["involved"] = bool(d.get("involved", False))
        d["evidence"] = str(d.get("evidence", ""))
        return d


def build_fidelity_tiers_snapshot(
    *,
    authority_contracts: Optional[Dict[str, Any]] = None,
    constraint_ledger: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a fidelity tier snapshot.

    Parameters
    ----------
    authority_contracts:
        Output of ``provenance.authority.authority_snapshot_from_outputs``.
    constraint_ledger:
        Output of ``decision.constraint_ledger.build_constraint_ledger``.
    """
    subs = (authority_contracts or {}).get("subsystems") if isinstance(authority_contracts, dict) else {}
    subs = subs if isinstance(subs, dict) else {}

    involved_subs, counts = _involved_subsystems_from_ledger(constraint_ledger or {})

    per: Dict[str, Dict[str, Any]] = {}
    all_tiers: List[int] = []
    involved_tiers: List[int] = []

    for key, c in subs.items():
        if not isinstance(c, dict):
            continue
        auth_tier = str(c.get("tier", ""))
        t0 = _tier_default_from_authority_tier(auth_tier)
        t = int(FIDELITY_OVERRIDES.get(str(key), t0))
        t = max(0, min(3, t))
        inv = (str(key) in involved_subs)
        ev = ""
        if inv:
            ev = f"involved_by_ledger(count={counts.get(str(key), 0)})"
        sf = SubsystemFidelity(
            subsystem=str(key),
            authority_tier=auth_tier,
            fidelity_tier=t,
            fidelity_label=FIDELITY_LABELS.get(t, f"T{t}"),
            involved=inv,
            evidence=ev,
        )
        per[str(key)] = sf.to_dict()
        all_tiers.append(t)
        if inv:
            involved_tiers.append(t)

    # Conservative: the *minimum* tier determines the certified tier.
    # If involved subsystems exist, use involved; otherwise use global.
    min_tier = min(involved_tiers or all_tiers) if (involved_tiers or all_tiers) else 0
    global_min_tier = min(all_tiers) if all_tiers else 0

    payload = {
        "schema_version": "fidelity_tiers.v366",
        "design": {
            "design_fidelity_min_tier": int(min_tier),
            "design_fidelity_label": FIDELITY_LABELS.get(int(min_tier), f"T{int(min_tier)}"),
            "global_fidelity_min_tier": int(global_min_tier),
            "global_fidelity_label": FIDELITY_LABELS.get(int(global_min_tier), f"T{int(global_min_tier)}"),
            "involved_subsystems": involved_subs,
        },
        "subsystems": per,
        # legacy flat keys
        "design_fidelity_min_tier": int(min_tier),
        "design_fidelity_label": FIDELITY_LABELS.get(int(min_tier), f"T{int(min_tier)}"),
        "global_fidelity_min_tier": int(global_min_tier),
        "global_fidelity_label": FIDELITY_LABELS.get(int(global_min_tier), f"T{int(global_min_tier)}"),
        "involved_subsystems": involved_subs,
    }
    payload["stamp_sha256"] = _stable_sha256(payload)
    return payload


def global_fidelity_from_registry(authority_contracts: Dict[str, Any]) -> str:
    """Convenience helper: return the global min fidelity label."""
    snap = build_fidelity_tiers_snapshot(authority_contracts=authority_contracts, constraint_ledger=None)
    return str((snap.get("design") or {}).get("global_fidelity_label", ""))
