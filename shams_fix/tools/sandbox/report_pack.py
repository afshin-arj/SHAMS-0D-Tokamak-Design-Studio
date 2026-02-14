
"""SHAMS Reactor Design Forge — Report Pack

Generates a PROCESS-recognizable (but audit-clean) report bundle for a single
candidate.

Outputs are purely descriptive:
- JSON (machine + closure + constraints)
- Markdown (human summary)
- CSV (flattened key-value table)

No rankings, no recommendations, no hidden assumptions.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pathlib import Path

from tools.sandbox.closure_certificate import build_closure_certificate
from tools.sandbox.citation_blocks import build_citation_blocks
from tools.sandbox.history_repro import history_repro_bundle
from tools.sandbox.design_classes import classify_candidate

def _flatten(prefix: str, obj: Any, out: Dict[str, Any]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(f"{prefix}{k}.", v, out)
    elif isinstance(obj, list):
        if len(obj) <= 5 and all(not isinstance(x, (dict, list)) for x in obj):
            out[prefix.rstrip('.')] = ";".join(str(x) for x in obj)
        else:
            out[prefix.rstrip('.')] = f"list(len={len(obj)})"
    else:
        out[prefix.rstrip('.')] = obj

def build_report_pack(candidate: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
    """Return a report pack dict.

    Back-compat: older callers pass a full candidate dict.
    Newer callers (Forge) may pass intent/inputs/outputs/constraints/closure_bundle etc.
    """
    if candidate is None:
        candidate = {}
    if kwargs:
        # Merge kwargs into a candidate-like dict (without overriding explicit candidate fields)
        for k,v in kwargs.items():
            if k == "constraints":
                candidate.setdefault("constraints", v)
            else:
                candidate.setdefault(k, v)

    c = candidate or {}
    intent = str(c.get("intent") or "")
    feas = bool(c.get("feasible", False))
    fm = str(c.get("failure_mode") or "")

    closure = c.get("closure_bundle") if isinstance(c.get("closure_bundle"), dict) else {}
    mb = c.get("margin_budget") if isinstance(c.get("margin_budget"), dict) else {}
    rg = c.get("reality_gates") if isinstance(c.get("reality_gates"), dict) else {}
    constraints = c.get("constraints") or []

    # --- New (v216): Certificates + classes + citations + reference context ---
    base_dir = Path(__file__).resolve().parent.parent.parent
    citation = build_citation_blocks(base_dir)
    fcc = build_closure_certificate(c)
    # Attach for downstream UI
    c["closure_certificate"] = fcc
    design_class = classify_candidate(c)
    c["design_class"] = design_class
    hist = history_repro_bundle(c)

    pack_json = {
        "schema": "shams.reactor_design_forge.report_pack.v2",
        "intent": intent,
        "feasible": feas,
        "failure_mode": fm,
        "design_class": design_class,
        "closure_certificate": fcc,
        "inputs": c.get("inputs") or c.get("inp") or {},
        "key_outputs": c.get("outputs") or {},
        "closure_bundle": closure,
        "margin_budget": mb,
        "reality_gates": rg,
        "constraints": constraints,
        "citation_blocks": citation,
        "reference_context": hist,
        "guardrails": [
            "No ranking. No recommendation. 0-D proxies only.",
            "Claims must respect Model Scope Card; use Reviewer Packet for scope and crosswalk.",
        ],
    }

    md_lines: List[str] = []
    md_lines.append("# SHAMS Reactor Design Forge — Candidate Report")
    md_lines.append("")
    if design_class:
        md_lines.append(f"- design_class: **{design_class.get('code','')}** — {design_class.get('name','')}")
    md_lines.append(f"- intent: **{intent}**")
    md_lines.append(f"- feasible: **{feas}**")
    if fm:
        md_lines.append(f"- failure_mode: **{fm}**")
    if fcc:
        md_lines.append(f"- closure_certificate: **{fcc.get('verdict','')}**")
    md_lines.append("")
    md_lines.append("## Closure (summary)")
    if isinstance(closure, dict) and closure:
        for k in ["gross_electric_MW","recirc_electric_MW","net_electric_MW"]:
            if k in closure:
                md_lines.append(f"- {k}: {closure.get(k)}")
    else:
        md_lines.append("- (no closure bundle)")
    md_lines.append("")
    md_lines.append("## Reality Gates")
    if isinstance(rg, dict) and rg:
        for k,v in rg.items():
            md_lines.append(f"- {k}: {v}")
    else:
        md_lines.append("- (no reality gates)")
    md_lines.append("")
    md_lines.append("## Guardrails")
    for g in pack_json["guardrails"]:
        md_lines.append(f"- {g}")
    md_lines.append("")
    md_lines.append("## Methods (paste-ready)")
    md_lines.append(citation.get("methods_block") or "")
    md_lines.append("")
    md_lines.append("## Reference context")
    md_lines.append("Comparisons are anchors, not targets.")
    for ref in (hist.get("refs") or [])[:4]:
        rname = ref.get("ref")
        comp = ref.get("comparison") or {}
        q = comp.get("Q") or {}
        md_lines.append(f"- {rname}: ΔQ={q.get('delta')}")
    md_lines.append("")
    pack_md = "\n".join(md_lines).strip() + "\n"

    flat: Dict[str, Any] = {}
    _flatten("", pack_json, flat)
    csv_lines = ["key,value"]
    for k in sorted(flat.keys()):
        v = flat[k]
        csv_lines.append(f"{k},{str(v).replace(',', ';')}")
    pack_csv = "\n".join(csv_lines) + "\n"

    return {"json": pack_json, "markdown": pack_md, "csv": pack_csv}
