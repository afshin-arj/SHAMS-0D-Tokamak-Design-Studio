from __future__ import annotations
"""Explainability Layer (v122)

Generates a human-readable narrative of:
- why a design is feasible or infeasible
- what constraint is limiting and how margins behave
- if tolerance envelope is available, summarize fragility and most common failure mode

No physics/solver/constraint behavior changes. Post-processing only.
"""

from typing import Any, Dict, List, Optional
import time

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _safe_get(d: Dict[str, Any], k: str, default=None):
    v = d.get(k, default) if isinstance(d, dict) else default
    return v

def _fmt(x: Any, unit: str = "") -> str:
    try:
        if x is None:
            return "N/A"
        if isinstance(x, bool):
            return "true" if x else "false"
        xf = float(x)
        if abs(xf) >= 1000:
            s = f"{xf:.0f}"
        elif abs(xf) >= 100:
            s = f"{xf:.1f}"
        elif abs(xf) >= 10:
            s = f"{xf:.2f}"
        else:
            s = f"{xf:.3f}"
        return s + (f" {unit}" if unit else "")
    except Exception:
        return str(x)

def build_explainability_report(
    *,
    run_artifact: Dict[str, Any],
    tolerance_envelope_report: Optional[Dict[str, Any]] = None,
    mission_report: Optional[Dict[str, Any]] = None,
    version: str = "v122",
) -> Dict[str, Any]:
    if not (isinstance(run_artifact, dict) and run_artifact.get("kind") == "shams_run_artifact"):
        raise ValueError("expected shams_run_artifact")

    outputs = _safe_get(run_artifact, "outputs", {})
    cs = _safe_get(run_artifact, "constraints_summary", {})
    feas = _safe_get(cs, "feasible")
    worst = _safe_get(cs, "worst_hard")
    wmargin = _safe_get(cs, "worst_hard_margin_frac")
    soft = _safe_get(cs, "worst_soft")
    smargin = _safe_get(cs, "worst_soft_margin_frac")

    # Key metrics (best-effort)
    pn = None
    q = None
    for k in ("Pn_MW","Pnet_MW","P_net_MW"):
        if k in outputs:
            pn = outputs.get(k); break
    for k in ("Q","Qfus","Q_plasma"):
        if k in outputs:
            q = outputs.get(k); break

    # Envelope summary (if provided)
    env_summary = None
    if isinstance(tolerance_envelope_report, dict) and tolerance_envelope_report.get("kind") == "shams_tolerance_envelope_report":
        env_summary = tolerance_envelope_report.get("summary", {}) if isinstance(tolerance_envelope_report.get("summary"), dict) else {}

    # Mission summary (if provided)
    mission_name = None
    mission_gaps_n = None
    if isinstance(mission_report, dict) and mission_report.get("kind") == "shams_mission_report":
        mission_name = mission_report.get("mission_name")
        gaps = mission_report.get("gaps", [])
        mission_gaps_n = len(gaps) if isinstance(gaps, list) else None

    # Causality: simple ranked blockers (hard then soft)
    causality = []
    if worst:
        causality.append({"rank": 1, "constraint": worst, "class": "hard", "margin_frac": wmargin})
    if soft and soft != worst:
        causality.append({"rank": 2, "constraint": soft, "class": "soft", "margin_frac": smargin})

    recs = []
    if feas is False and worst:
        recs.append({
            "kind":"recommendation",
            "type":"feasibility",
            "message": f"Primary blocker is hard constraint '{worst}'. Adjust inputs to increase its margin.",
        })
    if env_summary and isinstance(env_summary, dict):
        ff = env_summary.get("feasible_fraction")
        if ff is not None:
            try:
                ff = float(ff)
                if ff < 0.75:
                    recs.append({"kind":"recommendation","type":"robustness","message":"Tolerance envelope shows low feasible fraction; design is fragile. Consider increasing margins on limiting constraints or reducing targets."})
            except Exception:
                pass

    # Narrative
    lines = []
    lines.append("SHAMS Explainability Report (v122)")
    lines.append("")
    lines.append(f"Feasibility: {_fmt(feas)}")
    lines.append(f"Net power (Pn): {_fmt(pn, 'MW')} | Q: {_fmt(q)}")
    lines.append(f"Limiting hard constraint: {worst or 'N/A'} (margin frac: {_fmt(wmargin)})")
    lines.append(f"Limiting soft constraint: {soft or 'N/A'} (margin frac: {_fmt(smargin)})")

    if env_summary:
        lines.append("")
        lines.append("Robustness (Tolerance Envelope):")
        lines.append(f"- Feasible fraction: {_fmt(env_summary.get('feasible_fraction'))}")
        lines.append(f"- Worst margin over envelope: {_fmt(env_summary.get('worst_margin_over_envelope'))} (constraint: {env_summary.get('worst_margin_constraint')})")

    if mission_name:
        lines.append("")
        lines.append(f"Mission context: {mission_name} (gaps: {_fmt(mission_gaps_n)})")
        if isinstance(mission_report, dict):
            gaps = mission_report.get("gaps", [])
            if isinstance(gaps, list) and gaps:
                g0 = gaps[0]
                if isinstance(g0, dict):
                    lines.append(f"- Top mission gap: {g0.get('metric')} status={g0.get('status')} target={g0.get('target')} value={g0.get('value')}")

    if recs:
        lines.append("")
        lines.append("Recommendations (advisory):")
        for r in recs[:6]:
            lines.append(f"- {r.get('message')}")

    narrative = "\n".join(lines) + "\n"

    summary = {
        "feasible": feas,
        "Pn_MW": pn,
        "Q": q,
        "worst_hard": worst,
        "worst_hard_margin_frac": wmargin,
        "has_tolerance_envelope": bool(env_summary),
        "mission_name": mission_name,
        "mission_gaps_n": mission_gaps_n,
    }

    return {
        "kind":"shams_explainability_report",
        "version": version,
        "created_utc": _created_utc(),
        "source_artifact_id": run_artifact.get("id"),
        "summary": summary,
        "constraint_causality": causality,
        "recommendations": recs,
        "narrative": narrative,
        "notes":[
            "Explainability is post-processing only; no physics/constraints were modified.",
            "Causality is derived from constraint summaries and optional envelope/mission reports.",
        ],
    }
