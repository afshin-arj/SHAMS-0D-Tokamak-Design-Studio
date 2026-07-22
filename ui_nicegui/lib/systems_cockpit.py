"""Compact Systems cockpit summary — copy-ready markdown for experts."""

from __future__ import annotations

from typing import Any, Optional

from ui_nicegui.lib.systems_artifact import fmt
from ui_nicegui.lib.verdict_core import verdict_summary


def _pick(art: dict, paths: list[list[str]]) -> Any:
    for path in paths:
        cur: Any = art
        ok = True
        for key in path:
            if not isinstance(cur, dict) or key not in cur:
                ok = False
                break
            cur = cur[key]
        if ok:
            return cur
    return None


def compact_next_action(*, verdict: str, dominant: str, step: str) -> str:
    v = str(verdict or "").upper()
    stp = str(step or "")
    dom = str(dominant or "unknown")
    # "FEAS" matches INFEASIBLE — require exact FEASIBLE / PASS.
    if v in ("FEASIBLE", "PASS"):
        if "Explore" in stp or "trade" in stp.lower():
            return "Explore feasible neighborhood (search or scan), then apply the best candidate."
        return "Apply to Point Designer, re-check, and export audit bundle."
    if v in ("INFEASIBLE", "FAIL", "NO-SOLUTION", "NOSOLUTION"):
        if "Recover" in stp:
            return "Run seeded recovery — increase evaluation budget if the seed remains infeasible."
        if "Diagnose" in stp:
            return f"Inspect dominant limiter: {dom}"
        return f"Address dominant limiter ({dom}), then re-run precheck / solve."
    if "Recover" in stp:
        return "Run seeded recovery — increase evaluation budget if the seed remains infeasible."
    if "Diagnose" in stp:
        return f"Inspect dominant limiter: {dom}"
    return "Run precheck, then recovery or target solve as needed."


def build_compact_cockpit_markdown(session: Any, art: Optional[dict]) -> str:
    if not isinstance(art, dict):
        return "# Systems cockpit\n\nNo solve artifact yet — run precheck and target solve first.\n"

    out = art.get("outputs") if isinstance(art.get("outputs"), dict) else {}
    vs = verdict_summary(out) if out else {}
    verdict = vs.get("verdict") or art.get("verdict") or "UNKNOWN"
    dom = (
        art.get("dominant_constraint")
        or _pick(art, [["summary", "dominant_constraint"], ["ledger", "dominant_hard"]])
        or vs.get("dominant")
        or "-"
    )
    mech = art.get("dominant_mechanism") or _pick(art, [["summary", "dominant_mechanism"]]) or "-"
    step = getattr(session, "systems_decision_state", None) or art.get("workflow_step") or "Diagnose infeasibility"

    ac = art.get("authority_confidence") if isinstance(art.get("authority_confidence"), dict) else {}
    dc = str((ac.get("design") or {}).get("design_confidence_class", "UNKNOWN"))
    dec = art.get("decision_consequences") if isinstance(art.get("decision_consequences"), dict) else {}
    posture = str(dec.get("decision_posture", "UNKNOWN"))
    risk = str(dec.get("primary_risk_driver", "") or "-")
    ef = art.get("epoch_feasibility") if isinstance(art.get("epoch_feasibility"), dict) else {}
    epoch = str(ef.get("overall", "UNKNOWN"))

    feas = bool(vs.get("feasible")) if vs else str(verdict).upper() in ("FEASIBLE", "PASS", "PASS+DIAG")
    diag = "— (diagnostic)"
    pfus = diag if not feas else fmt(out.get("Pfus_total_MW", out.get("P_fus_MW")))
    pnet = diag if not feas else fmt(out.get("P_e_net_MW", out.get("P_net_e_MW", out.get("Pnet_MWe"))))
    qval = diag if not feas else fmt(out.get("Q_DT_eqv", out.get("Q")))

    src = str(art.get("source") or "") or "unknown"
    lines = [
        "# Systems cockpit summary",
        "",
        f"- Artifact source: {src}",
    ]
    if src in ("point_designer_fallback", "point_designer_apply", "systems_apply_reeval"):
        lines.append(
            "- Note: Point Designer baseline / Apply re-eval — not a Systems Mode target solve."
        )
    lines.extend(
        [
            f"- Verdict: {verdict}",
            f"- Design confidence: {dc}",
            f"- Decision posture: {posture}",
            f"- Epoch feasibility (overall): {epoch}",
            f"- Primary risk driver: {risk}",
            f"- Current workflow focus: {step}",
            f"- Dominant constraint: {dom}",
            f"- Dominant mechanism: {mech}",
            "",
            "## Key KPIs",
        ]
    )
    if not feas:
        lines.append("- PHYS-KPI-001: Q / Pfus / P_net shown as diagnostic on INFEASIBLE — not design claims.")
    lines.extend(
        [
            f"- P_fus [MW]: {pfus}",
            f"- P_net [MW]: {pnet}",
            f"- Q_plasma: {qval}",
            f"- β_N: {fmt(out.get('beta_N', out.get('betaN_proxy', out.get('betaN'))))}",
            f"- q95 (cyl. proxy): {fmt(out.get('q95_proxy', out.get('q95')))}",
            f"- n/n_GW: {fmt(out.get('fG', out.get('n_over_nGW')))}",
            "",
            "## Suggested next action (diagnostic only)",
            f"- {compact_next_action(verdict=str(verdict), dominant=str(dom), step=str(step))}",
        ]
    )
    return "\n".join(lines)
