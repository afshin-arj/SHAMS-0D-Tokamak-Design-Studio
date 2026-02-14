from __future__ import annotations
"""Evidence Graph + Traceability (v123)

Builds a provenance graph across SHAMS artifacts and a traceability table.
Post-processing only; no physics/solver modifications.
"""

from typing import Any, Dict, List, Optional, Tuple
import time, json, hashlib, csv, io

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def _node(kind: str, label: str, payload: Optional[Dict[str, Any]] = None, bytes_sha256: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": f"{kind}:{label}",
        "kind": kind,
        "label": label,
        "sha256": bytes_sha256,
        "payload_summary": payload if isinstance(payload, dict) else None,
    }

def build_evidence_graph(
    *,
    run_artifact: Dict[str, Any],
    tolerance_envelope_report: Optional[Dict[str, Any]] = None,
    mission_report: Optional[Dict[str, Any]] = None,
    explainability_report: Optional[Dict[str, Any]] = None,
    decision_pack_manifest: Optional[Dict[str, Any]] = None,
    downstream_bundle_manifest: Optional[Dict[str, Any]] = None,
    authority_pack_manifest: Optional[Dict[str, Any]] = None,
    version: str = "v123",
) -> Dict[str, Any]:
    if not (isinstance(run_artifact, dict) and run_artifact.get("kind") == "shams_run_artifact"):
        raise ValueError("expected shams_run_artifact")

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # Base node
    rid = run_artifact.get("id") or "run"
    n_run = _node("run_artifact", str(rid), {"feasible": (run_artifact.get("constraints_summary") or {}).get("feasible")})
    nodes.append(n_run)

    def add_rel(parent_id: str, child_node: Dict[str, Any], rel: str):
        nodes.append(child_node)
        edges.append({"from": parent_id, "to": child_node["id"], "rel": rel})

    if isinstance(tolerance_envelope_report, dict) and tolerance_envelope_report.get("kind") == "shams_tolerance_envelope_report":
        s = tolerance_envelope_report.get("summary", {})
        add_rel(n_run["id"], _node("tolerance_envelope", "v117", {"feasible_fraction": (s or {}).get("feasible_fraction")}), "robustness_of")

    if isinstance(mission_report, dict) and mission_report.get("kind") == "shams_mission_report":
        add_rel(n_run["id"], _node("mission_report", mission_report.get("mission_name") or "mission", {"gaps_n": len(mission_report.get("gaps", []) or [])}), "mission_overlay")

    if isinstance(explainability_report, dict) and explainability_report.get("kind") == "shams_explainability_report":
        add_rel(n_run["id"], _node("explainability", "v122", {"worst_hard": (explainability_report.get("summary") or {}).get("worst_hard")}), "explains")

    if isinstance(decision_pack_manifest, dict):
        add_rel(n_run["id"], _node("decision_pack", "v118", {"files": len((decision_pack_manifest.get("files") or {}))}), "candidate_pack")

    if isinstance(downstream_bundle_manifest, dict):
        add_rel(n_run["id"], _node("downstream_bundle", "v118", {"files": len((downstream_bundle_manifest.get("files") or {}))}), "downstream_of")

    if isinstance(authority_pack_manifest, dict):
        add_rel(n_run["id"], _node("authority_pack", "v119", {"files": len((authority_pack_manifest.get("files") or {}))}), "authority_bundle")

    return {
        "kind": "shams_evidence_graph",
        "version": version,
        "created_utc": _created_utc(),
        "nodes": nodes,
        "edges": edges,
        "notes": [
            "Graph captures provenance relationships across SHAMS artifacts (post-processing).",
        ],
    }

def _extract_constraints(run_artifact: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Best-effort: try explicit list, else use summaries
    cons = run_artifact.get("constraints")
    if isinstance(cons, list):
        out = []
        for c in cons:
            if isinstance(c, dict):
                out.append(c)
        return out
    if isinstance(cons, dict):
        out = []
        for k,v in cons.items():
            if isinstance(v, dict):
                d = dict(v); d.setdefault("name", k); out.append(d)
        return out
    return []

def build_traceability_table(
    *,
    run_artifact: Dict[str, Any],
    explainability_report: Optional[Dict[str, Any]] = None,
    tolerance_envelope_report: Optional[Dict[str, Any]] = None,
    mission_report: Optional[Dict[str, Any]] = None,
    version: str = "v123",
) -> Dict[str, Any]:
    if not (isinstance(run_artifact, dict) and run_artifact.get("kind") == "shams_run_artifact"):
        raise ValueError("expected shams_run_artifact")

    cs = run_artifact.get("constraints_summary", {}) if isinstance(run_artifact.get("constraints_summary"), dict) else {}
    worst_h = cs.get("worst_hard")
    worst_s = cs.get("worst_soft")
    wmh = cs.get("worst_hard_margin_frac")
    wms = cs.get("worst_soft_margin_frac")

    env = tolerance_envelope_report.get("summary", {}) if isinstance(tolerance_envelope_report, dict) else {}
    env_worst = env.get("worst_margin_constraint")
    env_worst_margin = env.get("worst_margin_over_envelope")
    env_ff = env.get("feasible_fraction")

    gaps = mission_report.get("gaps", []) if isinstance(mission_report, dict) else []
    gap_metrics = set()
    if isinstance(gaps, list):
        for g in gaps:
            if isinstance(g, dict) and g.get("metric"):
                gap_metrics.add(str(g["metric"]))

    expl_worst = None
    if isinstance(explainability_report, dict):
        expl_worst = ((explainability_report.get("summary") or {}).get("worst_hard"))

    # Create rows focusing on key blockers + mission gaps
    rows: List[Dict[str, Any]] = []
    def add_row(name: str, cls: str, margin: Any, tags: List[str]):
        rows.append({
            "constraint_or_metric": name,
            "class": cls,
            "margin_frac": margin,
            "in_explainability": bool(expl_worst and name == expl_worst),
            "in_envelope_worst": bool(env_worst and name == env_worst),
            "mission_gap": bool(name in gap_metrics),
            "tags": tags,
        })

    if worst_h:
        add_row(str(worst_h), "hard", wmh, ["worst_hard"])
    if worst_s and worst_s != worst_h:
        add_row(str(worst_s), "soft", wms, ["worst_soft"])
    if env_worst and env_worst not in {worst_h, worst_s}:
        add_row(str(env_worst), "envelope_worst", env_worst_margin, ["envelope"])
    # mission gaps as metrics rows
    for m in sorted(gap_metrics):
        if m in {str(worst_h), str(worst_s), str(env_worst)}:
            continue
        add_row(m, "mission_metric", None, ["mission_gap"])

    return {
        "kind":"shams_traceability_table",
        "version": version,
        "created_utc": _created_utc(),
        "rows": rows,
        "notes":[
            "Traceability is best-effort and focuses on key blockers + mission gaps.",
            f"envelope_feasible_fraction={env_ff!r}",
        ],
    }

def traceability_csv(table: Dict[str, Any]) -> bytes:
    rows = table.get("rows", [])
    if not isinstance(rows, list):
        rows = []
    buf = io.StringIO()
    cols = ["constraint_or_metric","class","margin_frac","in_explainability","in_envelope_worst","mission_gap","tags"]
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for r in rows:
        if not isinstance(r, dict):
            continue
        rr = {c: r.get(c) for c in cols}
        w.writerow(rr)
    return buf.getvalue().encode("utf-8")
