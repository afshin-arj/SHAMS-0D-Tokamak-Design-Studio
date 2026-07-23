"""Reactor Design Forge — Narrative Pack (v1)

Produces a review-ready narrative from already-audited artifacts.

Strict rule: this is summarization of truth + derived accounting only. No
recommendations, no ranking, no hidden intent.

PHYS-KPI-001: on INFEASIBLE candidates, net electric (and kin) are framed as
diagnostic residue — never as achieved plant performance.
"""

from __future__ import annotations

from typing import Any, Dict, List

_DIAGNOSTIC = "— (diagnostic)"


def _candidate_feasible(c: Dict[str, Any]) -> bool:
    if "feasible" in c:
        return bool(c.get("feasible"))
    state = str(c.get("feasibility_state") or "").strip().upper()
    return state == "FEASIBLE"


def build_narrative(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Return a structured narrative + markdown for a candidate."""

    c = candidate or {}
    cid = str(c.get("id") or c.get("candidate_id") or "")
    intent = str(c.get("design_intent") or c.get("intent") or "")
    feas = str(c.get("feasibility_state") or "")
    robust = str(c.get("robustness_class") or "")
    feasible = _candidate_feasible(c)

    closure = c.get("closure_bundle") or {}
    net_e = closure.get("net_electric_MW")
    recirc = closure.get("recirc_electric_MW")
    gross = closure.get("gross_electric_MW")

    gates = c.get("reality_gates") or {}
    gate_summary = []
    if isinstance(gates.get("results"), list):
        for g in gates["results"]:
            gate_summary.append(f"{g.get('gate')}: {g.get('status')}")

    mb = c.get("margin_budget") or {}
    tight = []
    if isinstance(mb.get("tight_constraints"), list):
        tight = [str(x) for x in mb["tight_constraints"]][:6]

    bullets: List[str] = []
    bullets.append(f"Candidate **{cid or '(unlabeled)'}** — intent: **{intent or 'unknown'}**")
    if feas:
        bullets.append(f"Feasibility ladder: **{feas}** (robustness: **{robust or 'n/a'}**) ")
    elif "feasible" in c:
        bullets.append(
            f"Feasibility ladder: **{'FEASIBLE' if feasible else 'INFEASIBLE'}** "
            f"(robustness: **{robust or 'n/a'}**)"
        )
    if not feasible:
        bullets.append(
            "PHYS-KPI-001: claim FoMs (Q / H98 / Pfus / P_net) are diagnostic residue "
            "on this INFEASIBLE candidate — not design claims."
        )
    if any(v is not None for v in [gross, recirc, net_e]):
        if feasible:
            bullets.append(
                f"Electric closure: gross **{gross} MW**, recirc **{recirc} MW**, "
                f"net **{net_e} MW**"
            )
        else:
            bullets.append(
                f"Electric closure (diagnostic): gross **{gross} MW**, recirc **{recirc} MW**, "
                f"net {_DIAGNOSTIC} (not a design claim)"
            )
    if tight:
        bullets.append("Tight constraints (small headroom): " + ", ".join(tight))
    if gate_summary:
        bullets.append("Reality gates: " + "; ".join(gate_summary[:6]))

    md = "\n".join(["### Reactor Design Forge — Design Narrative", ""] + [f"- {b}" for b in bullets])

    return {
        "schema": "shams.reactor_design_forge.narrative_pack.v1",
        "candidate_id": cid,
        "feasible": feasible,
        "bullets": bullets,
        "markdown": md,
        "note": "Narrative is derived from audited artifacts only; not a recommendation.",
    }
