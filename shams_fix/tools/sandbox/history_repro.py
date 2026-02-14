
"""Historical Reproduction Mode (lightweight)

Compares a candidate to built-in reference presets (ITER/ARC/SPARC/HH170) and
reports deltas for review-room context.

No new physics; uses existing model outputs stored in the candidate plus
reference preset evaluations (hot_ion_point).

Schema: shams.forge.history_repro.v1
"""

from __future__ import annotations
from typing import Any, Dict, Optional
from models.reference_machines import reference_presets
from physics.hot_ion import hot_ion_point

def _get(out: Dict[str, Any], keys) -> Optional[float]:
    for k in keys:
        v = out.get(k)
        if v is None:
            continue
        try:
            return float(v)
        except Exception:
            continue
    return None

def compare_to_reference(candidate_outputs: Dict[str, Any], ref_name: str) -> Dict[str, Any]:
    presets = reference_presets()
    if ref_name not in presets:
        return {"ref": ref_name, "error": "missing_reference"}
    ref_inp = presets[ref_name]
    ref_out = hot_ion_point(ref_inp)

    keys = {
        "Q": ( ["Q", "Q_DT_eqv"], ["Q", "Q_DT_eqv"] ),
        "Pfus_MW": ( ["Pfus_total_MW", "Pfus_MW"], ["Pfus_total_MW", "Pfus_MW"] ),
        "Pnet_MW": ( ["P_e_net_MW", "Pe_net_MW"], ["P_e_net_MW", "Pe_net_MW"] ),
        "betaN": ( ["betaN", "betaN_proxy"], ["betaN", "betaN_proxy"] ),
        "q95": ( ["q95", "q95_proxy"], ["q95", "q95_proxy"] ),
    }

    rows = {}
    for name,(cand_keys, ref_keys) in keys.items():
        cv = _get(candidate_outputs, cand_keys)
        rv = _get(ref_out, ref_keys)
        rows[name] = {"candidate": cv, "reference": rv, "delta": (cv - rv) if (cv is not None and rv is not None) else None}

    return {
        "ref": ref_name,
        "ref_inputs": ref_inp,
        "ref_outputs": {k: _get(ref_out, v[1]) for k,v in keys.items()},
        "comparison": rows,
    }

def history_repro_bundle(candidate: Dict[str, Any]) -> Dict[str, Any]:
    c = candidate or {}
    outs = c.get("outputs") if isinstance(c.get("outputs"), dict) else {}
    refs = ["REF|REACTOR|ITER", "REF|REACTOR|SPARC", "REF|REACTOR|ARC", "REF|REACTOR|HH170"]
    return {
        "schema": "shams.forge.history_repro.v1",
        "refs": [compare_to_reference(outs, r) for r in refs],
        "note": "Reference comparisons are contextual anchors, not targets.",
    }
