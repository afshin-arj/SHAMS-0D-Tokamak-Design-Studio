from __future__ import annotations
from typing import List

# Heuristic knob suggestions for constraint classes.
# Keep transparent and editable; later versions can replace with computed explainability outputs.
_KNOBS_BY_PREFIX = {
    "q_div": ["Increase R0 (more area)", "Increase divertor capability mode", "Reduce P_fus target / increase radiation fraction"],
    "sigma_hoop": ["Increase TF structure thickness", "Reduce B0 / increase R0", "Reduce peak current density Jop"],
    "TBR": ["Increase blanket thickness", "Increase Li6 enrichment / breeder coverage", "Reduce shield thickness (if allowed)"],
    "q95": ["Increase plasma current (Ip)", "Increase B0", "Increase aspect ratio / shaping"],
}

def default_best_knobs(constraint_name: str) -> List[str]:
    for pref, knobs in _KNOBS_BY_PREFIX.items():
        if constraint_name.startswith(pref):
            return list(knobs)
    return []
