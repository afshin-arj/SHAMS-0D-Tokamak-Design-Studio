from __future__ import annotations

"""Authority Dominance Engine (v330.0).

Deterministic, post-processing-only dominance classification over constraint margins.

Design intent
-------------
This module answers (without any solver/iteration):

  - What authority is the *dominant feasibility killer*?
  - What constraint is the top blocker?
  - What are the top-N secondary blockers (with margins)?

It is strictly additive: it consumes an already-evaluated run artifact
(constraints + ledger) and produces a dominance summary. It MUST NOT modify
physics truth.

Conventions
-----------
- Uses hard constraints only for dominance.
- Margin convention is the SHAMS canonical convention: margin_frac < 0 => violation.
- If hard-infeasible: dominance ranks the most negative (worst) margins.
- If hard-feasible: dominance ranks the smallest positive margins (tightest).
"""

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Dict, Iterable, List, Optional, Tuple


CANON_AUTHORITIES: Tuple[str, ...] = (
    "PLASMA",
    "EXHAUST",
    "MAGNET",
    "CONTROL",
    "ACTUATORS",
    "MAINTENANCE",
    "MATERIALS",
    "NEUTRONICS",
    "FUEL",
    "PLANT",
    "ECONOMICS",
    "GENERAL",
)


def _stable_hash_json(obj: Any) -> str:
    try:
        s = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(s).hexdigest()
    except Exception:
        return ""


def _as_float(x: Any) -> Optional[float]:
    try:
        f = float(x)
        # reject NaN
        if f != f:
            return None
        return f
    except Exception:
        return None


def _norm(s: Any) -> str:
    return str(s or "").strip()


def _infer_authority(*, group: str, mechanism_group: str, subsystem: str) -> str:
    """Map legacy fields to a canonical authority label.

    Priority:
      1) mechanism_group (if it already looks like an authority)
      2) group
      3) subsystem
      4) GENERAL
    """

    mg = _norm(mechanism_group).upper()
    g = _norm(group).lower()
    ss = _norm(subsystem).lower()

    # 1) direct mapping if already canonical-ish
    for a in CANON_AUTHORITIES:
        if mg == a:
            return a

    # 2) group heuristics
    if any(k in g for k in ("plasma", "core", "profile", "pedestal", "current_drive", "beta", "q", "greenwald")):
        return "PLASMA"
    if any(k in g for k in ("exhaust", "divertor", "sol", "edge", "radiat")):
        return "EXHAUST"
    # Keep TF magnets distinct from PF/CS control budgets
    if any(k in g for k in ("magnet", "tf", "coil")):
        return "MAGNET"
    if any(k in g for k in ("control", "vs", "rwm", "pf", "cs")):
        return "CONTROL"
    if any(k in g for k in ("actuator", "wallplug", "power_supply", "supply_peak")):
        return "ACTUATORS"
    if any(k in g for k in ("maintenance", "outage", "calendar", "schedule", "availability_v368")):
        return "MAINTENANCE"
    if any(k in g for k in ("materials", "lifetime", "dpa", "irradiat", "he_appm", "first-wall", "first wall")):
        return "MATERIALS"
    if any(k in g for k in ("neutronic", "blanket", "shield", "material")):
        return "NEUTRONICS"
    if any(k in g for k in ("fuel", "trit", "tbr", "breeding")):
        return "FUEL"
    if any(k in g for k in ("plant", "power", "balance", "ledger", "recirc")):
        return "PLANT"
    if any(k in g for k in ("econ", "cost", "lcoe")):
        return "ECONOMICS"

    # 3) subsystem heuristics
    if any(k in ss for k in ("magnet", "tf")):
        return "MAGNET"
    if any(k in ss for k in ("pf", "cs", "control")):
        return "CONTROL"
    if any(k in ss for k in ("divertor", "exhaust", "sol")):
        return "EXHAUST"
    if any(k in ss for k in ("maintenance", "availability", "outage", "schedule")):
        return "MAINTENANCE"
    if any(k in ss for k in ("materials", "lifetime", "damage")):
        return "MATERIALS"
    if any(k in ss for k in ("neutronic", "blanket", "shield")):
        return "NEUTRONICS"
    if any(k in ss for k in ("trit", "fuel")):
        return "FUEL"
    if any(k in ss for k in ("plant", "power")):
        return "PLANT"

    return "GENERAL"


@dataclass(frozen=True)
class DominanceConfig:
    top_k: int = 8
    fragility_threshold: float = 0.05  # margin_frac < thr (but >=0) => FRAGILE


def authority_dominance_from_constraints_json(
    constraints_json: List[Dict[str, Any]],
    *,
    cfg: Optional[DominanceConfig] = None,
) -> Dict[str, Any]:
    """Compute authority dominance from canonical constraint JSON entries."""

    c = cfg or DominanceConfig()

    # Only hard constraints participate in dominance.
    hard: List[Dict[str, Any]] = []
    for e in constraints_json or []:
        if not isinstance(e, dict):
            continue
        sev = _norm(e.get("severity", "hard")).lower()
        if sev != "hard":
            continue
        mf = _as_float(e.get("margin_frac"))
        if mf is None:
            # fall back to margin (still dimensionless in SHAMS)
            mf = _as_float(e.get("margin"))
        if mf is None:
            continue
        passed = bool(e.get("passed", True))
        hard.append(
            {
                "name": _norm(e.get("name")),
                "group": _norm(e.get("group", "general")),
                "mechanism_group": _norm(e.get("mechanism_group", e.get("mechanism", "GENERAL"))),
                "subsystem": _norm(e.get("subsystem", "")),
                "authority_tier": _norm(e.get("authority_tier", "unknown")),
                "passed": passed,
                "margin_frac": float(mf),
            }
        )

    if not hard:
        return {
            "schema_version": "authority_dominance.v1",
            "dominance_verdict": "UNKNOWN",
            "dominant_authority": "",
            "dominant_constraint": "",
            "dominant_margin_frac": None,
            "dominance_topk": [],
            "authority_ranked": [],
            "stamp_sha256": "",
        }

    # Determine if any hard constraint failed.
    any_failed = any(not bool(e["passed"]) for e in hard)

    # Sort constraints by dominance: ascending margin (most negative first).
    # Works for both infeasible (negatives dominate) and feasible (tight positives first).
    hard_sorted = sorted(hard, key=lambda r: float(r.get("margin_frac", 0.0)))

    # Pick the dominant constraint:
    if any_failed:
        # first violated in sorted order
        dom = None
        for r in hard_sorted:
            if not bool(r.get("passed", True)):
                dom = r
                break
        dom = dom or hard_sorted[0]
        verdict = "INFEASIBLE"
    else:
        dom = hard_sorted[0]
        mf0 = float(dom.get("margin_frac", 0.0))
        verdict = "FRAGILE" if (mf0 >= 0.0 and mf0 < float(c.fragility_threshold)) else "FEASIBLE"

    dom_margin = float(dom.get("margin_frac", 0.0))
    dom_name = str(dom.get("name", ""))
    dom_auth = _infer_authority(
        group=str(dom.get("group", "")),
        mechanism_group=str(dom.get("mechanism_group", "")),
        subsystem=str(dom.get("subsystem", "")),
    )

    # Top-k constraints list
    topk: List[Dict[str, Any]] = []
    for r in hard_sorted[: int(c.top_k)]:
        auth = _infer_authority(
            group=str(r.get("group", "")),
            mechanism_group=str(r.get("mechanism_group", "")),
            subsystem=str(r.get("subsystem", "")),
        )
        topk.append(
            {
                "authority": auth,
                "constraint": str(r.get("name", "")),
                "margin_frac": float(r.get("margin_frac", 0.0)),
                "passed": bool(r.get("passed", True)),
                "authority_tier": str(r.get("authority_tier", "unknown")),
                "group": str(r.get("group", "")),
            }
        )

    # Aggregate per-authority min margin
    by_auth: Dict[str, Dict[str, Any]] = {}
    for r in hard:
        auth = _infer_authority(
            group=str(r.get("group", "")),
            mechanism_group=str(r.get("mechanism_group", "")),
            subsystem=str(r.get("subsystem", "")),
        )
        ent = by_auth.setdefault(
            auth,
            {
                "authority": auth,
                "n_hard": 0,
                "n_failed": 0,
                "min_margin_frac": None,
                "dominant_constraint": "",
            },
        )
        ent["n_hard"] = int(ent["n_hard"]) + 1
        if not bool(r.get("passed", True)):
            ent["n_failed"] = int(ent["n_failed"]) + 1
        mf = float(r.get("margin_frac", 0.0))
        cur = ent.get("min_margin_frac")
        if cur is None or mf < float(cur):
            ent["min_margin_frac"] = float(mf)
            ent["dominant_constraint"] = str(r.get("name", ""))

    authority_ranked = sorted(
        list(by_auth.values()),
        key=lambda e: float(e.get("min_margin_frac") if e.get("min_margin_frac") is not None else 0.0),
    )

    payload = {
        "schema_version": "authority_dominance.v1",
        "dominance_verdict": verdict,
        "dominant_authority": dom_auth,
        "dominant_constraint": dom_name,
        "dominant_margin_frac": float(dom_margin),
        "dominance_topk": topk,
        "authority_ranked": authority_ranked,
    }
    payload["stamp_sha256"] = _stable_hash_json(payload)
    return payload
