from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def _stable_sha256(obj: Any) -> str:
    """Stable SHA-256 for deterministic stamps."""
    try:
        s = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(s).hexdigest()
    except Exception:
        return ""


def _pick_worst_margin_frac_hard(ledger: Dict[str, Any]) -> Optional[float]:
    """Return the worst (most negative) hard margin_frac if present."""
    entries = ledger.get("entries") if isinstance(ledger, dict) else None
    if not isinstance(entries, list):
        return None
    worst: Optional[float] = None
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
        worst = mf_f if worst is None else min(worst, mf_f)
    return worst


def _top_blocker(ledger: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tb = ledger.get("top_blockers") if isinstance(ledger, dict) else None
    if isinstance(tb, list) and tb:
        if isinstance(tb[0], dict):
            return tb[0]
    # Fallback: choose by violation_score
    entries = ledger.get("entries") if isinstance(ledger, dict) else None
    if not isinstance(entries, list):
        return None
    viol = [e for e in entries if isinstance(e, dict) and (not bool(e.get("passed", True)))]
    if not viol:
        return None
    viol.sort(key=lambda x: float(x.get("violation_score", 0.0) or 0.0), reverse=True)
    return viol[0] if isinstance(viol[0], dict) else None


def _confidence_bucket(cls: str) -> str:
    c = str(cls or "").strip().upper()
    if c in ("A", "B", "C", "D"):
        return c
    return "UNKNOWN"


def _posture_from_state(*, feasible_hard: bool, worst_hard_mf: Optional[float], design_conf: str) -> str:
    """Deterministic decision posture policy (advisory only)."""
    dc = _confidence_bucket(design_conf)

    if not feasible_hard:
        return "HOLD_FOUNDATIONAL"

    # Feasible but uncertain/extrapolated: proceed only with targeted R&D.
    if dc in ("C", "D", "UNKNOWN"):
        return "PROCEED_TARGETED_RD"

    # Near-binding hard margins: proceed with targeted R&D.
    if worst_hard_mf is not None and worst_hard_mf <= 0.20:
        return "PROCEED_TARGETED_RD"

    return "PROCEED"


def _r_and_d_axis(*, primary_subsystem: str, design_conf: str, ac: Dict[str, Any]) -> str:
    """Pick a deterministic R&D axis label."""
    dc = _confidence_bucket(design_conf)

    if dc in ("C", "D", "UNKNOWN"):
        subs = ac.get("subsystems") if isinstance(ac, dict) else {}
        if isinstance(subs, dict) and subs:
            def _rank(v: Dict[str, Any]) -> Tuple[int, int]:
                mat = str(v.get("maturity", "")).strip().lower()
                conf = _confidence_bucket(v.get("confidence_class", "UNKNOWN"))
                mat_rank = 2
                if "specul" in mat or "unknown" in mat:
                    mat_rank = 0
                elif "extrap" in mat:
                    mat_rank = 1
                conf_rank = {"D": 0, "C": 1, "B": 2, "A": 3, "UNKNOWN": 0}.get(conf, 0)
                return (mat_rank, conf_rank)

            items = []
            for k, v in subs.items():
                if isinstance(v, dict) and bool(v.get("involved", False)):
                    items.append((str(k), v))
            if not items:
                items = [(str(k), v) for k, v in subs.items() if isinstance(v, dict)]
            items.sort(key=lambda kv: _rank(kv[1]))
            if items:
                return f"UNCERTAINTY_REDUCTION({items[0][0]})"
        return "UNCERTAINTY_REDUCTION(GLOBAL)"

    ps = str(primary_subsystem or "").strip()
    return f"ENGINEERING_LEVERAGE({ps})" if ps else "ENGINEERING_LEVERAGE(GENERAL)"


@dataclass(frozen=True)
class DecisionConsequences:
    schema_version: str
    decision_posture: str
    primary_risk_driver: str
    dominant_mechanism: str
    dominant_constraint: str
    worst_hard_margin_frac: Optional[float]
    leverage_knobs: List[str]
    uncertainty_reduction_axis: str
    narrative: str

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "decision_posture": self.decision_posture,
            "primary_risk_driver": self.primary_risk_driver,
            "dominant_mechanism": self.dominant_mechanism,
            "dominant_constraint": self.dominant_constraint,
            "worst_hard_margin_frac": self.worst_hard_margin_frac,
            "leverage_knobs": list(self.leverage_knobs),
            "uncertainty_reduction_axis": self.uncertainty_reduction_axis,
            "narrative": self.narrative,
        }
        d["stamp_sha256"] = _stable_sha256(d)
        return d


def decision_consequences_from_artifact(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Compute a deterministic Decision Consequences snapshot.

    Governance/protocol layer: MUST NOT modify physics truth.
    """
    art = artifact if isinstance(artifact, dict) else {}

    kpis = art.get("kpis") if isinstance(art.get("kpis"), dict) else {}
    feasible_hard = bool(kpis.get("feasible_hard", True))

    dom_mech = str(art.get("dominant_mechanism", "") or "")
    dom_con = str(art.get("dominant_constraint", "") or "")

    ledger = art.get("constraint_ledger") if isinstance(art.get("constraint_ledger"), dict) else {}
    worst_hard_mf = _pick_worst_margin_frac_hard(ledger)

    tb = _top_blocker(ledger) or {}
    primary_sub = str(tb.get("subsystem", "") or "")
    if not primary_sub:
        primary_sub = str(tb.get("mechanism_group", "") or "")
    if not primary_sub:
        primary_sub = str(dom_mech or "GENERAL")

    # ------------------------------------------------------------------
    # v319.0: Operational risk tiers (disruption + stability) are *advisory*
    # governance overlays. They MUST NOT modify truth, but they SHOULD steer
    # "what next" guidance when the design is otherwise hard-feasible.
    # ------------------------------------------------------------------
    try:
        out = art.get("outputs") if isinstance(art.get("outputs"), dict) else {}
        op_tier = str(out.get("operational_risk_tier", "") or "")
        op_driver = str(out.get("operational_dominant_driver", "") or "")

        def _map_driver_to_subsystem(d: str) -> str:
            d = (d or "").strip().lower()
            if d in {"vertical_stability", "rwm", "control_budget"}:
                return "CONTROL"
            if d in {"mhd", "density", "beta", "qmin", "radiation"}:
                return "PLASMA"
            return ""

        if feasible_hard and op_tier in {"MED", "HIGH"}:
            mapped = _map_driver_to_subsystem(op_driver)
            if mapped:
                primary_sub = mapped
            elif op_driver:
                primary_sub = f"OPERATIONAL:{op_driver.upper()}"
    except Exception:
        pass

    knobs: List[str] = []
    knobs_raw = tb.get("best_knobs")
    if isinstance(knobs_raw, list):
        for k in knobs_raw:
            if isinstance(k, str) and k.strip():
                knobs.append(k.strip())

    ac = art.get("authority_confidence") if isinstance(art.get("authority_confidence"), dict) else {}
    design_conf = str(ac.get("design_confidence_class", "") or "") if isinstance(ac, dict) else ""

    posture = _posture_from_state(feasible_hard=feasible_hard, worst_hard_mf=worst_hard_mf, design_conf=design_conf)
    axis = _r_and_d_axis(primary_subsystem=primary_sub, design_conf=design_conf, ac=ac if isinstance(ac, dict) else {})

    if posture == "PROCEED":
        narrative = "Feasible under hard constraints with adequate authority. Proceed to compare/export; monitor margin drift."
    elif posture == "PROCEED_TARGETED_RD":
        narrative = "Feasible but near-binding or authority-limited. Proceed only with targeted R&D and robustness checks."
    else:
        narrative = "Hard-infeasible. Hold; address dominant limiter(s) before further exploration."

    dc = DecisionConsequences(
        schema_version="decision_consequences.v1",
        decision_posture=posture,
        primary_risk_driver=primary_sub,
        dominant_mechanism=dom_mech,
        dominant_constraint=dom_con,
        worst_hard_margin_frac=worst_hard_mf,
        leverage_knobs=knobs,
        uncertainty_reduction_axis=axis,
        narrative=narrative,
    )
    return dc.to_dict()
