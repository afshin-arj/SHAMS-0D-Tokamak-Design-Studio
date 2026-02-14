# SHAMS / Reactor Design Forge — Supremacy Instruments (v212+)
# Purely descriptive, posture-safe utilities. No ranking, no "best design".

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def epistemic_gap_map(context: Dict[str, Any]) -> Dict[str, List[str]]:
    """Return a reviewer-facing map of *where conclusions depend on model limits*.
    This is not UQ; it is explicit honesty signaling."""
    gaps: Dict[str, List[str]] = {
        "Scaling-dominated (empirical)": [],
        "Model-scope (0-D abstraction)": [],
        "Assumption-sensitive (inputs / bounds)": [],
        "Data-missing (unknown / not modeled)": [],
    }

    # Heuristic extraction from available ledgers / assumption notes
    notes = []
    for k in ("assumptions_ledger", "assumptions", "model_ledger", "notes"):
        v = context.get(k)
        if isinstance(v, str):
            notes.append(v)
        elif isinstance(v, list):
            notes.extend([str(x) for x in v])
        elif isinstance(v, dict):
            notes.extend([f"{kk}: {vv}" for kk, vv in v.items()])

    joined = "\n".join(notes).lower()

    # Always-true scope gaps for 0-D
    gaps["Model-scope (0-D abstraction)"].extend([
        "No 2-D/3-D edge/divertor detachment physics; q_div is a proxy gate.",
        "No time-dependent disruption/ELM dynamics; constraints are static gates.",
        "No full neutronics transport; TBR is a proxy model gate.",
    ])

    if "h98" in joined or "scaling" in joined:
        gaps["Scaling-dominated (empirical)"].append("Energy confinement relies on empirical scaling (e.g., H98-style factors).")
    if "bootstrap" in joined or "current" in joined:
        gaps["Scaling-dominated (empirical)"].append("Current drive / bootstrap fractions depend on simplified models.")
    if "cost" in joined or "lcoe" in joined:
        gaps["Assumption-sensitive (inputs / bounds)"].append("Economics proxies depend on assumed cost envelopes and learning factors.")
    if "availability" in joined:
        gaps["Assumption-sensitive (inputs / bounds)"].append("Net-electric outcomes depend on assumed availability / capacity factor.")

    # Keep lists non-empty and readable
    for k, v in gaps.items():
        if not v:
            gaps[k] = ["(No explicit entries detected in current artifacts; scope gaps above still apply.)"]
    return gaps


def constraint_personas() -> Dict[str, Dict[str, str]]:
    """A compact, memorable 'persona' profile for core constraints."""
    return {
        "q_div": {
            "Persona": "Edge Tyrant",
            "Behavior": "Punishes small wetted area and optimistic power exhaust.",
            "Typical fights": "vs. compactness, high P_fus, high beta",
            "Common trap": "Assuming geometry tweaks alone save the divertor.",
        },
        "sigma_vm": {
            "Persona": "Steel Prosecutor",
            "Behavior": "Scales brutally with stress concentration and field.",
            "Typical fights": "vs. high B_t, small R, thick blanket",
            "Common trap": "Ignoring structural knock-ons from magnet sizing.",
        },
        "HTS margin": {
            "Persona": "Cryo Realist",
            "Behavior": "Temperature-fragile, engineering-forgiving until it isn't.",
            "Typical fights": "vs. high B, high ripple, poor thermal design",
            "Common trap": "Treating HTS like 'infinite margin' superconductivity.",
        },
        "TBR": {
            "Persona": "Neutron Accountant",
            "Behavior": "Hates optimistic blanket coverage and thin breeding volume.",
            "Typical fights": "vs. compactness, thick shields, tight ports",
            "Common trap": "Counting theoretical blanket coverage as real coverage.",
        },
        "q95": {
            "Persona": "Topology Gatekeeper",
            "Behavior": "Enforces a minimum operational safety topology.",
            "Typical fights": "vs. aggressive shaping and small machines",
            "Common trap": "Treating it as a tunable preference instead of a gate.",
        },
    }


def genealogy_markdown(candidates: List[Dict[str, Any]]) -> str:
    """Render a lightweight genealogy view based on lineage fields if present."""
    # Build parent->children mapping if lineage exists
    by_id = {str(c.get("id", i)): c for i, c in enumerate(candidates)}
    children: Dict[str, List[str]] = {}
    roots: List[str] = []
    for i, c in enumerate(candidates):
        cid = str(c.get("id", i))
        parent = c.get("parent_id") or c.get("lineage_parent") or c.get("origin_id")
        if parent is None:
            roots.append(cid)
        else:
            pid = str(parent)
            children.setdefault(pid, []).append(cid)

    if not roots:
        roots = list(by_id.keys())[:10]

    def label(cid: str) -> str:
        c = by_id.get(cid, {})
        reg = c.get("regime_tag") or c.get("regime") or c.get("dominant_constraint") or "unknown"
        return f"{cid} — {reg}"

    lines = ["## Design Genealogy (descriptive)"]
    seen=set()

    def walk(cid: str, depth: int=0):
        if cid in seen:
            return
        seen.add(cid)
        lines.append("  "*depth + f"- {label(cid)}")
        for ch in children.get(cid, [])[:20]:
            walk(ch, depth+1)

    for r in roots[:20]:
        walk(r, 0)

    lines.append("\n*(Genealogy is derived from lineage metadata when available; absence of links is not an error.)*")
    return "\n".join(lines)


def do_not_build_brief(candidate: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate 'Reasons not to build this machine' — trust-building, not advocacy."""
    reasons: List[str] = []
    margins = context.get("margin_ledger") or candidate.get("margin_ledger") or {}
    if isinstance(margins, dict):
        minm = margins.get("min_signed_margin")
        if minm is not None:
            reasons.append(f"Thin headroom: minimum signed margin ≈ {minm}.")
    conflicts = context.get("conflicts") or candidate.get("conflicts") or []
    if conflicts:
        reasons.append("Constraint conflicts present: design lives on trade boundaries.")
    first_kill = context.get("first_kill_under_uncertainty") or candidate.get("first_kill_under_uncertainty")
    if first_kill:
        reasons.append(f"Under uncertainty, first-kill gate is: {first_kill}.")
    if not reasons:
        reasons.append("No explicit weak points detected in current artifacts; treat this as 'insufficient evidence', not confidence.")

    return {
        "title": "Do‑Not‑Build Brief (descriptive)",
        "candidate_id": candidate.get("id"),
        "reasons": reasons,
        "posture": "SHAMS does not recommend designs; this brief exists to prevent self-deception.",
    }


def elimination_narrative(context: Dict[str, Any]) -> str:
    """Narrative: why most reactors cannot exist, in constraint-elimination terms."""
    killers = context.get("dominant_killers") or context.get("first_failure_histogram") or {}
    lines = ["## Process of Elimination (constraint narrative)",
             "Most candidate machines fail for a small number of recurring physical gates.",
             "This narrative is descriptive: it explains elimination pressure, not optimality.",
             ""]
    if isinstance(killers, dict) and killers:
        lines.append("### Dominant eliminators observed")
        for k, v in list(killers.items())[:10]:
            lines.append(f"- **{k}** — {v}")
    else:
        lines.append("- No scan/atlas histogram found in current session; build a Scan Atlas to populate eliminators.")
    lines.append("")
    lines.append("### Interpretation")
    lines.append("- When an eliminator dominates, it defines the local 'physics ceiling'.")
    lines.append("- Surviving classes are existence proofs inside those ceilings, not winners.")
    return "\n".join(lines)


def paper_ready_signals(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Stable figure/table list template for paper-grade exports."""
    cid = candidate.get("id", "candidate")
    return {
        "paper_ready_signals": [
            {"id": "Fig-1", "title": "Margin Ledger (spent vs remaining)", "ref": f"{cid}:margin_ledger"},
            {"id": "Fig-2", "title": "Constraint Conflict Map (top pairs)", "ref": f"{cid}:conflict_map"},
            {"id": "Fig-3", "title": "Trade-off Slice (non-dominated feasible set)", "ref": f"{cid}:trade_slice"},
            {"id": "Tbl-1", "title": "Design Contract (intent + policy + gates)", "ref": f"{cid}:design_contract"},
            {"id": "Tbl-2", "title": "Do-Not-Build Brief (trust ledger)", "ref": f"{cid}:do_not_build"},
        ],
        "posture": "Figure IDs are stable across deterministic replay capsules.",
    }
