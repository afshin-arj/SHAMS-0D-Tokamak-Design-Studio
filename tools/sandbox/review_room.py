from __future__ import annotations

"""Review-room instruments for Reactor Design Forge.

Design intent
-------------
This module produces *reviewer-grade*, non-prescriptive briefs for a selected
candidate.

Hard rules (epistemic)
----------------------
- Never rank, recommend, or claim a "best" design.
- Never modify physics or constraint truth.
- Always point to artifacts/evidence fields inside the candidate.
- PHYS-KPI-001: on INFEASIBLE, claim FoMs (Q / H98 / Pfus / P_net) are
  diagnostic residue in human-facing briefs — never design achievements.

The UI may export these briefs as Markdown/JSON. The Markdown is a narrative
rendering of the JSON and should be treated as derived.
"""

import json
from typing import Any, Dict, List, Optional

_DIAGNOSTIC = "— (diagnostic)"
_CLAIM_CLOSURE_KEYS = frozenset(
    {
        "P_e_net_MW",
        "P_net_e_MW",
        "Pe_net_MW",
        "net_electric_MW",
        "Q",
        "Q_DT_eqv",
        "H98",
        "P_fus_MW",
        "Pfus_MW",
        "Pfus_total_MW",
        "Pfus_DT_adj_MW",
    }
)
_CLOSURE_PICK = [
    "gross_electric_MW",
    "recirc_electric_MW",
    "net_electric_MW",
    "P_e_gross_MW",
    "P_recirc_MW",
    "P_e_net_MW",
    "eta_thermal",
    "eta_electric",
]


def _j(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, default=str)


def _pick(d: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k in keys:
        if k in d:
            out[k] = d[k]
    return out


def _candidate_feasible(c: Dict[str, Any]) -> bool:
    if "feasible" in c:
        return bool(c.get("feasible"))
    state = str(c.get("feasibility_state") or "").strip().upper()
    return state == "FEASIBLE"


def _watermark_closure(closure: Dict[str, Any], *, feasible: bool) -> Dict[str, Any]:
    if feasible or not closure:
        return dict(closure)
    out: Dict[str, Any] = {}
    for k, v in closure.items():
        out[k] = _DIAGNOSTIC if str(k) in _CLAIM_CLOSURE_KEYS else v
    return out


def build_review_trinity(
    *,
    candidate: Dict[str, Any],
    scan_grounding: Optional[Dict[str, Any]] = None,
    pareto_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the "Review Trinity": Existence Proof → Stress Story → Positioning.

    Returns a JSON dict with `markdown` as a convenience rendering.
    """
    c = candidate or {}
    inputs = c.get("inputs") or {}
    outputs = c.get("outputs") or {}
    cons = c.get("constraints") or []
    feasible = _candidate_feasible(c)

    existence = {
        "feasible": feasible,
        "first_failure": c.get("first_failure") or c.get("failure_mode"),
        "min_signed_margin": c.get("min_signed_margin"),
        "fingerprint": c.get("fingerprint") or c.get("_id"),
        "evidence": {
            "inputs_keys": sorted(list(inputs.keys()))[:40],
            "outputs_keys": sorted(list(outputs.keys()))[:40],
            "constraints_n": int(len(cons)) if isinstance(cons, list) else 0,
        },
    }

    closure_raw = c.get("closure_bundle") or {}
    if not isinstance(closure_raw, dict):
        closure_raw = {}
    # Prefer explicit closure_bundle; fall back to evaluator outputs for legacy keys.
    closure_src = dict(closure_raw)
    if isinstance(outputs, dict):
        for k in _CLOSURE_PICK:
            if k not in closure_src and k in outputs:
                closure_src[k] = outputs[k]
    closure_picked = _pick(closure_src, _CLOSURE_PICK)
    closure_display = _watermark_closure(closure_picked, feasible=feasible)

    stress = {
        "margins": {
            "min_signed_margin": c.get("min_signed_margin"),
            "dominant_constraint": c.get("first_failure") or c.get("failure_mode"),
        },
        "reality_gates": c.get("reality_gates") or {},
        "closure": closure_display,
        "confidence": c.get("confidence_sweep") or {},
    }

    positioning = {
        "design_intent": c.get("intent") or c.get("design_intent"),
        "lens": c.get("lens") or {},
        "what_it_is": c.get("dossier_tagline") or "(not declared)",
        "what_it_is_not": c.get("dossier_not") or "(not declared)",
        "who_should_not_build": c.get("dossier_who_not") or "(not declared)",
    }

    out: Dict[str, Any] = {
        "kind": "shams.review_room.trinity.v1",
        "existence_proof": existence,
        "stress_story": stress,
        "positioning": positioning,
        "scan_grounding": scan_grounding or {},
        "pareto_context": pareto_context or {},
    }
    if not feasible:
        out["phys_kpi_note"] = (
            "PHYS-KPI-001: claim FoMs in stress_story.closure are diagnostic on "
            "INFEASIBLE — not design claims."
        )

    md = []
    md.append("# SHAMS Review Trinity (v1)\n")
    md.append("**Non-prescriptive review brief. No rankings. No recommendations.**\n")
    if not feasible:
        md.append(
            "PHYS-KPI-001: claim FoMs (Q / H98 / Pfus / P_net) below are "
            "**diagnostic residue** on an INFEASIBLE candidate — not design claims.\n"
        )

    md.append("## 1) Existence Proof\n")
    md.append(f"- Feasible: `{feasible}`")
    md.append(f"- First failure (if any): `{existence.get('first_failure') or '—'}`")
    md.append(f"- Min signed margin: `{existence.get('min_signed_margin')}`")
    md.append(f"- Fingerprint: `{existence.get('fingerprint')}`\n")

    md.append("## 2) Stress Story\n")
    md.append(f"- Dominant resistance: `{stress['margins'].get('dominant_constraint') or '—'}`")
    md.append(f"- Min signed margin: `{stress['margins'].get('min_signed_margin')}`")
    if stress.get("closure"):
        label = "Closure (selected, diagnostic)" if not feasible else "Closure (selected)"
        md.append(f"- {label}:")
        for k, v in stress["closure"].items():
            md.append(f"  - `{k}`: `{v}`")
    if stress.get("reality_gates"):
        md.append("- Reality gates (as recorded):")
        for k, v in (stress["reality_gates"] or {}).items():
            md.append(f"  - `{k}`: `{v}`")
    md.append("")

    md.append("## 3) Positioning\n")
    md.append(f"- Design intent: `{positioning.get('design_intent')}`")
    md.append(f"- What it is: {positioning.get('what_it_is')}")
    md.append(f"- What it is not: {positioning.get('what_it_is_not')}")
    md.append(f"- Who should not build it: {positioning.get('who_should_not_build')}\n")

    if scan_grounding:
        md.append("## Scan ↔ Forge grounding (topology context)\n")
        md.append(_j(scan_grounding))
        md.append("")

    out["markdown"] = "\n".join(md).strip() + "\n"
    return out


ATTACKS_V1 = [
    {
        "id": "assumption_tuning",
        "claim": "You tuned assumptions to get feasibility.",
        "required_evidence": ["capsule", "settings", "evaluator_fingerprint"],
        "response_template": "Point to the run capsule + evaluator fingerprint. Show perturbation outcomes (Confidence Sweep) if present.",
    },
    {
        "id": "hidden_optimization",
        "claim": "This is over-optimized / penalty-driven.",
        "required_evidence": ["objective_contract", "feasible_first_policy"],
        "response_template": "Point to Objective Contract and feasibility-first archive construction. No penalty terms are used in feasibility labeling.",
    },
    {
        "id": "fake_margins",
        "claim": "Those margins are fake / undefined.",
        "required_evidence": ["constraint_records", "margin_definition"],
        "response_template": "Show constraint records (value/limit/sense/margin) from frozen evaluator outputs.",
    },
    {
        "id": "process_disagreement",
        "claim": "PROCESS would disagree with this machine.",
        "required_evidence": ["replay_capsule", "assumption_explicitness"],
        "response_template": "Provide the deterministic replay capsule. Differences are audited as assumption/physics deltas, not tuned penalties.",
    },
]


def build_attack_simulation(*, candidate: Dict[str, Any], run_capsule: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate a hostile-review "attack simulation" scaffold.

    This does not invent facts; it returns prompts + pointers to where evidence
    *should* be found in artifacts.
    """
    c = candidate or {}
    capsule = run_capsule or {}

    evidence = {
        "evaluator_fingerprint": c.get("fingerprint") or capsule.get("evaluator_hash"),
        "objective_contract": (capsule.get("settings") or {}).get("objectives") or c.get("objectives"),
        "constraint_records": c.get("constraints"),
        "confidence_sweep": c.get("confidence_sweep"),
        "capsule": bool(bool(capsule)),
    }

    items = []
    for a in ATTACKS_V1:
        items.append({
            "id": a["id"],
            "claim": a["claim"],
            "evidence_present": {k: (evidence.get(k) is not None and evidence.get(k) != {} and evidence.get(k) != []) for k in a["required_evidence"]},
            "response": a["response_template"],
        })

    md = [
        "# SHAMS Hostile Review Attack Simulation (v1)",
        "",
        "**Purpose:** rehearsal prompts for expert scrutiny. No invented answers.",
        "",
    ]
    for it in items:
        md.append(f"## {it['id']}")
        md.append(f"- Claim: {it['claim']}")
        md.append(f"- Evidence present: `{it['evidence_present']}`")
        md.append(f"- Response pattern: {it['response']}")
        md.append("")

    return {
        "kind": "shams.review_room.attack_simulation.v1",
        "evidence": evidence,
        "items": items,
        "markdown": "\n".join(md).strip() + "\n",
    }
