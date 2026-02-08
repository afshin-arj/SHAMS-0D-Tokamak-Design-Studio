
"""Official SHAMS Design Classes (v1)

Classifies a candidate descriptively for communication and review.
No ranking, no recommendation.

Schema: shams.forge.design_class.v1
"""

from __future__ import annotations
from typing import Any, Dict

def classify_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    c = candidate or {}
    intent = str(c.get("intent") or "")
    feasible = bool(c.get("feasible", False))
    fm = str(c.get("failure_mode") or "")
    cert = c.get("closure_certificate") if isinstance(c.get("closure_certificate"), dict) else {}

    verdict = str(cert.get("verdict") or ("PASS" if feasible else "FAIL"))
    # Descriptive class codes
    if feasible and verdict == "PASS":
        code = "FCR-0D" if ("REACT" in intent.upper()) else "FCE-0D"
        name = "Feasibility-Closed Reactor" if code == "FCR-0D" else "Feasibility-Closed Experiment"
    elif feasible and verdict == "CONDITIONAL":
        code = "FCCR-0D" if ("REACT" in intent.upper()) else "FCCE-0D"
        name = "Feasibility-Closed (Conditional)" 
    else:
        # Failure-typed descriptive classes
        key = (fm or "").lower()
        if "div" in key or "q_div" in key:
            code = "HFL-0D"; name = "Heat-Flux-Limited Candidate"
        elif "sigma" in key or "stress" in key:
            code = "STL-0D"; name = "Stress-Limited Candidate"
        elif "tbr" in key or "breed" in key:
            code = "BCL-0D"; name = "Breeding-Constrained Candidate"
        elif "recirc" in key or "net" in key:
            code = "PCL-0D"; name = "Power-Closure-Limited Candidate"
        else:
            code = "NFC-0D"; name = "Non-Feasible Candidate"

    return {
        "schema": "shams.forge.design_class.v1",
        "code": code,
        "name": name,
        "intent": intent,
        "feasible": feasible,
        "closure_verdict": verdict,
        "dominant_failure_mode": fm or None,
        "notes": [
            "Design classes are descriptive labels for communication; they are not rankings.",
        ],
    }
