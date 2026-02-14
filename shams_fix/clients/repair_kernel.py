from __future__ import annotations
from typing import Dict, Any

def repair_candidate(overrides: Dict[str, Any], artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic, bounded repair kernel driven by dominant mechanism/constraint."""
    dom = str(artifact.get("dominant_constraint") or artifact.get("dominant_mechanism") or "").lower()
    x = dict(overrides)

    if "greenwald" in dom or "density" in dom or "gw" in dom:
        if "f_G" in x:
            x["f_G"] = max(0.2, float(x["f_G"]) * 0.95)
    if "beta" in dom:
        if "Bt" in x:
            x["Bt"] = float(x["Bt"]) * 1.02
        if "Ip" in x:
            x["Ip"] = float(x["Ip"]) * 1.01
    if "coil" in dom or "stress" in dom:
        if "Bt" in x:
            x["Bt"] = float(x["Bt"]) * 0.98
        if "R" in x:
            x["R"] = float(x["R"]) * 1.01
    if "power" in dom or "balance" in dom or "aux" in dom:
        if "Paux" in x:
            x["Paux"] = float(x["Paux"]) * 1.05

    return x
