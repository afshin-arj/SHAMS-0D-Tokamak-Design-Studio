from __future__ import annotations
"""Study Protocol Generator (v165)

Goal:
- Produce a journal-ready, audit-ready "Methods" protocol describing *exactly* what was run.
- Intended for Design Study Authority pillar.

Inputs:
- run_artifact: shams_run_artifact (preferred)
- optional: protocol_overrides (study title, objectives, variables varied, scan configs, seeds, solver modes)

Outputs:
- kind: shams_study_protocol, version: v165
- includes stable protocol_sha256 computed from canonical protocol body
- markdown summary suitable for paper methods section

Safety:
- Reporting-only. No physics changes, no solver logic changes.
"""

from typing import Any, Dict, List, Optional
import json, time, hashlib, copy

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _canon_json(o: Any) -> bytes:
    return json.dumps(o, indent=2, sort_keys=True, default=str).encode("utf-8")

def _sha_bytes(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def _sha_obj(o: Any) -> str:
    return _sha_bytes(_canon_json(o))

def build_study_protocol(
    *,
    run_artifact: Dict[str, Any],
    protocol_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not (isinstance(run_artifact, dict) and run_artifact.get("kind")=="shams_run_artifact"):
        raise ValueError("run_artifact must be a shams_run_artifact dict")

    protocol_overrides = protocol_overrides if isinstance(protocol_overrides, dict) else {}
    inputs = run_artifact.get("inputs") or run_artifact.get("_inputs") or {}
    constraints = run_artifact.get("constraints") or []
    metrics = run_artifact.get("metrics") or {}
    solver = run_artifact.get("solver") or run_artifact.get("solver_meta") or {}
    assumptions = run_artifact.get("assumptions") or {}

    body = {
        "study": {
            "title": str(protocol_overrides.get("title") or "SHAMS Design Study"),
            "study_id": str(protocol_overrides.get("study_id") or ""),
            "objective": protocol_overrides.get("objective") or "Feasibility characterization and completion under explicit constraints.",
            "notes": protocol_overrides.get("notes") or [],
        },
        "model": {
            "shams_version": str(protocol_overrides.get("shams_version") or run_artifact.get("shams_version") or ""),
            "mode": str(protocol_overrides.get("mode") or run_artifact.get("mode") or ""),
            "assumptions": assumptions,
        },
        "inputs": {
            "baseline": inputs,
            "fixed_overrides": protocol_overrides.get("fixed_overrides") or [],
            "variables_varied": protocol_overrides.get("variables_varied") or [],
        },
        "constraints": {
            "enforced": constraints,
            "margin_definition": protocol_overrides.get("margin_definition") or "margin >= 0 is feasible; min margin is feasibility score.",
        },
        "solver": {
            "backend": solver,
            "continuation": protocol_overrides.get("continuation") or {},
            "tolerances": protocol_overrides.get("tolerances") or {},
            "determinism": protocol_overrides.get("determinism") or {"seed": protocol_overrides.get("seed"), "note": "Set seed for sampling-based studies."},
        },
        "outputs": {
            "metrics": metrics,
            "artifacts_generated": protocol_overrides.get("artifacts_generated") or [],
        },
        "integrity": {
            "protocol_sha256": "",
        },
    }

    # Compute hash over body with empty protocol_sha256
    tmp = copy.deepcopy(body)
    tmp["integrity"]["protocol_sha256"] = ""
    body["integrity"]["protocol_sha256"] = _sha_obj(tmp)

    out = {
        "kind": "shams_study_protocol",
        "version": "v165",
        "issued_utc": _utc(),
        "integrity": {"object_sha256": ""},
        "payload": body,
    }
    tmp2=copy.deepcopy(out); tmp2["integrity"]={"object_sha256": ""}
    out["integrity"]["object_sha256"]=_sha_obj(tmp2)
    return out

def render_study_protocol_markdown(protocol: Dict[str, Any]) -> str:
    p=(protocol.get("payload") or {}) if isinstance(protocol, dict) else {}
    study=p.get("study") or {}
    model=p.get("model") or {}
    inp=p.get("inputs") or {}
    con=p.get("constraints") or {}
    sol=p.get("solver") or {}
    out=p.get("outputs") or {}
    sha=((p.get("integrity") or {}).get("protocol_sha256") or "")

    lines=[]
    lines.append("# SHAMS Study Protocol (v165)")
    lines.append("")
    lines.append(f"- Issued: {protocol.get('issued_utc','')}")
    lines.append(f"- Protocol SHA-256: `{sha}`")
    lines.append("")
    lines.append("## Study")
    lines.append(f"- Title: {study.get('title','')}")
    if study.get("study_id"):
        lines.append(f"- Study ID: {study.get('study_id')}")
    lines.append(f"- Objective: {study.get('objective','')}")
    for n in (study.get("notes") or [])[:10]:
        lines.append(f"- Note: {n}")
    lines.append("")
    lines.append("## Model & assumptions")
    lines.append(f"- SHAMS version: {model.get('shams_version','')}")
    if model.get("mode"):
        lines.append(f"- Mode: {model.get('mode')}")
    lines.append("")
    lines.append("### Assumptions (verbatim)")
    lines.append("```json")
    lines.append(json.dumps(model.get("assumptions") or {}, indent=2, sort_keys=True, default=str))
    lines.append("```")
    lines.append("")
    lines.append("## Inputs")
    lines.append("### Baseline inputs (verbatim)")
    lines.append("```json")
    lines.append(json.dumps(inp.get("baseline") or {}, indent=2, sort_keys=True, default=str))
    lines.append("```")
    if (inp.get("variables_varied") or []):
        lines.append("")
        lines.append("### Variables varied")
        lines.append("```json")
        lines.append(json.dumps(inp.get("variables_varied") or [], indent=2, sort_keys=True, default=str))
        lines.append("```")
    lines.append("")
    lines.append("## Constraints")
    lines.append(f"- Margin definition: {con.get('margin_definition','')}")
    lines.append("### Enforced constraints (verbatim)")
    lines.append("```json")
    lines.append(json.dumps(con.get("enforced") or [], indent=2, sort_keys=True, default=str))
    lines.append("```")
    lines.append("")
    lines.append("## Solver")
    lines.append("```json")
    lines.append(json.dumps(sol, indent=2, sort_keys=True, default=str))
    lines.append("```")
    lines.append("")
    lines.append("## Outputs")
    lines.append("```json")
    lines.append(json.dumps(out, indent=2, sort_keys=True, default=str))
    lines.append("```")
    lines.append("")
    lines.append("## Methods paragraph (paper-ready)")
    lines.append("This design study used SHAMS–FUSION-X in constraint-first mode with explicit feasibility margins. ")
    lines.append("We report baseline inputs, enforced constraints, solver backend configuration, and assumptions verbatim, ")
    lines.append("and we attach a protocol SHA-256 for reproducibility and audit.")
    lines.append("")
    return "\n".join(lines)
