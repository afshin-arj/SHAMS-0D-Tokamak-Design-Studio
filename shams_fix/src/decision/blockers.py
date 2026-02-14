from __future__ import annotations
from typing import Any, Dict, List, Optional

def _violation_score(c: Dict[str, Any]) -> float:
    # Larger means worse. Hard constraints first.
    sev = c.get("severity","hard")
    margin_frac = float(c.get("margin_frac", 0.0))
    passed = bool(c.get("passed", True))
    # If passed: score 0; else use negative margin magnitude
    if passed:
        return 0.0
    base = max(0.0, -margin_frac)
    return base + (10.0 if sev == "hard" else 1.0)

def suggest_relief(constraint_name: str, group: str | None = None) -> str:
    n = (constraint_name or "").lower()
    g = (group or "").lower()
    if "stress" in n or "von" in n or "tf" in g:
        return "Reduce B0 / increase coil thickness / increase R0 to relieve TF stress."
    if "q_div" in n or "div" in g or "heat" in n:
        return "Reduce Psep / increase R0 / improve flux expansion / increase radiation fraction (within limits)."
    if "greenwald" in n or "fg" in n:
        return "Reduce density (fG) or increase Ip / a to reduce Greenwald fraction."
    if "beta" in n:
        return "Reduce pressure (lower fG/Paux) or increase B0/R0 to reduce beta."
    if "tbr" in n or "shield" in n or "dpa" in n or "neutron" in g:
        return "Increase shielding/blanket thickness or adjust blanket coverage/material multiplier."
    if "pnet" in n or "coe" in n or "econom" in g:
        return "Increase Q / improve wall-plug efficiency / reduce recirc power / adjust net-electric closure."
    if "vertical" in n or "kappa" in n or "elong" in n:
        return "Reduce elongation or increase stability margin (shape/Ip)."
    return "Adjust primary levers (R0, B0, Ip, fG, shielding, Paux) guided by sensitivities."

def rank_blockers(constraints: List[Dict[str, Any]], *, top_k: int = 8) -> List[Dict[str, Any]]:
    """Return the worst constraint violations with simple actionable hints."""
    scored = []
    for c in constraints or []:
        score = _violation_score(c)
        if score <= 0:
            continue
        out = dict(c)
        out["violation_score"] = float(score)
        out["suggestion"] = suggest_relief(out.get("name",""), out.get("group",""))
        scored.append(out)
    scored.sort(key=lambda x: float(x.get("violation_score",0.0)), reverse=True)
    return scored[:top_k]
