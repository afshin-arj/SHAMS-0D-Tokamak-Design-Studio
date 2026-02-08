
"""Constraint Provenance Graph (CPG)

A lightweight, audit-friendly provenance scaffold for constraints and gates.
This does NOT change physics. It turns existing constraint objects/records into
a traceable 'where did this come from' explanation tree.

Schema: shams.forge.cpg.v1
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

def _node(id: str, label: str, kind: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"id": id, "label": label, "kind": kind, "meta": meta or {}}

def build_cpg_for_constraint(constraint_name: str, *, intent: str = "", assumption_notes: Optional[List[str]] = None) -> Dict[str, Any]:
    """Return a small provenance graph for a known constraint name.

    This is intentionally conservative: it documents *provenance structure*,
    not unverified numeric derivations.
    """
    c = (constraint_name or "").strip()
    intent = intent or ""
    notes = assumption_notes or []

    # Minimal, controlled vocabulary for typical tokamak 0-D constraints.
    templates = {
        "q_div": [
            ("assumptions", "Assumptions (SOL/divertor proxy)", "assumption"),
            ("proxy", "Divertor heat-flux proxy", "proxy"),
            ("inputs", "P_SOL, geometry, λ_q (declared)", "input"),
            ("constraint", "q_div limit", "constraint"),
        ],
        "sigma_vm": [
            ("assumptions", "Assumptions (structural screening)", "assumption"),
            ("proxy", "TF stress proxy", "proxy"),
            ("inputs", "B_peak, coil geometry", "input"),
            ("constraint", "σ_vm allowable", "constraint"),
        ],
        "HTS margin": [
            ("assumptions", "Assumptions (HTS critical surface)", "assumption"),
            ("proxy", "HTS margin proxy", "proxy"),
            ("inputs", "B_peak, T_op, J/Jc model", "input"),
            ("constraint", "HTS operating margin min", "constraint"),
        ],
        "TBR": [
            ("assumptions", "Assumptions (blanket coverage + thickness proxy)", "assumption"),
            ("proxy", "TBR screening proxy", "proxy"),
            ("inputs", "radial build + coverage", "input"),
            ("constraint", "TBR minimum", "constraint"),
        ],
        "net_electric": [
            ("assumptions", "Assumptions (plant closure)", "assumption"),
            ("proxy", "Power balance + recirc proxies", "proxy"),
            ("inputs", "P_fus, η_th, P_recirc", "input"),
            ("constraint", "P_net ≥ target", "constraint"),
        ],
    }

    chain = templates.get(c, [
        ("assumptions", "Assumptions (declared)", "assumption"),
        ("proxy", "Model proxy/relationship", "proxy"),
        ("inputs", "Inputs and derived intermediates", "input"),
        ("constraint", f"{c} constraint", "constraint"),
    ])

    nodes = []
    edges = []
    prev = None
    for i, (nid, label, kind) in enumerate(chain):
        full_id = f"{c}:{nid}:{i}"
        meta = {}
        if kind == "assumption":
            meta["intent"] = intent
            if notes:
                meta["notes"] = notes[:8]
        nodes.append(_node(full_id, label, kind, meta=meta))
        if prev is not None:
            edges.append({"src": prev, "dst": full_id, "why": "depends_on"})
        prev = full_id

    return {
        "schema": "shams.forge.cpg.v1",
        "constraint": c,
        "intent": intent,
        "nodes": nodes,
        "edges": edges,
    }
