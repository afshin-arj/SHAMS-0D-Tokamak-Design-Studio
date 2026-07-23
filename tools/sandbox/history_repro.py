"""Historical Reproduction Mode (lightweight)

Compares a candidate to built-in reference presets (ITER/ARC/SPARC/HH170) and
reports deltas for review-room context.

No new physics; uses existing model outputs stored in the candidate plus
reference preset evaluations (hot_ion_point).

PHYS-KPI-001: on INFEASIBLE candidates, claim FoMs (Q / Pfus / P_net) and their
deltas vs anchors are diagnostic residue — not design claims.

Schema: shams.forge.history_repro.v1
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from models.reference_machines import reference_presets
from physics.hot_ion import hot_ion_point

_DIAGNOSTIC = "— (diagnostic)"
_CLAIM_METRICS = frozenset({"Q", "Pfus_MW", "Pnet_MW"})


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


def _candidate_feasible(c: Dict[str, Any]) -> bool:
    if "feasible" in c:
        return bool(c.get("feasible"))
    state = str(c.get("feasibility_state") or "").strip().upper()
    return state == "FEASIBLE"


def _jsonable_inputs(ref_inp: Any) -> Any:
    if ref_inp is None:
        return None
    if isinstance(ref_inp, dict):
        return dict(ref_inp)
    if hasattr(ref_inp, "__dict__"):
        try:
            return {k: getattr(ref_inp, k) for k in vars(ref_inp) if not k.startswith("_")}
        except Exception:
            return str(ref_inp)
    try:
        # dataclasses / pydantic-like
        from dataclasses import asdict, is_dataclass

        if is_dataclass(ref_inp):
            return asdict(ref_inp)
    except Exception:
        pass
    return str(ref_inp)


def compare_to_reference(
    candidate_outputs: Dict[str, Any],
    ref_name: str,
    *,
    feasible: bool = True,
) -> Dict[str, Any]:
    presets = reference_presets()
    if ref_name not in presets:
        return {"ref": ref_name, "error": "missing_reference"}
    ref_inp = presets[ref_name]
    ref_out = hot_ion_point(ref_inp)

    keys = {
        "Q": (["Q", "Q_DT_eqv"], ["Q", "Q_DT_eqv"]),
        "Pfus_MW": (["Pfus_total_MW", "Pfus_MW"], ["Pfus_total_MW", "Pfus_MW"]),
        "Pnet_MW": (["P_e_net_MW", "Pe_net_MW"], ["P_e_net_MW", "Pe_net_MW"]),
        "betaN": (["betaN", "betaN_proxy", "beta_N"], ["betaN", "betaN_proxy", "beta_N"]),
        "q95": (["q95", "q95_proxy"], ["q95", "q95_proxy"]),
    }

    rows = {}
    for name, (cand_keys, ref_keys) in keys.items():
        cv = _get(candidate_outputs, cand_keys)
        rv = _get(ref_out, ref_keys)
        if (not feasible) and (name in _CLAIM_METRICS):
            rows[name] = {"candidate": _DIAGNOSTIC, "reference": rv, "delta": _DIAGNOSTIC}
        else:
            rows[name] = {
                "candidate": cv,
                "reference": rv,
                "delta": (cv - rv) if (cv is not None and rv is not None) else None,
            }

    return {
        "ref": ref_name,
        "ref_inputs": _jsonable_inputs(ref_inp),
        "ref_outputs": {k: _get(ref_out, v[1]) for k, v in keys.items()},
        "comparison": rows,
    }


def history_repro_bundle(candidate: Dict[str, Any]) -> Dict[str, Any]:
    c = candidate or {}
    outs = c.get("outputs") if isinstance(c.get("outputs"), dict) else {}
    feasible = _candidate_feasible(c)
    refs = ["REF|REACTOR|ITER", "REF|REACTOR|SPARC", "REF|REACTOR|ARC", "REF|REACTOR|HH170"]
    note = "Reference comparisons are contextual anchors, not targets."
    out: Dict[str, Any] = {
        "schema": "shams.forge.history_repro.v1",
        "feasible": feasible,
        "refs": [compare_to_reference(outs, r, feasible=feasible) for r in refs],
        "note": note,
    }
    if not feasible:
        out["phys_kpi_note"] = (
            "PHYS-KPI-001: Q / Pfus / P_net deltas vs historical anchors are "
            "diagnostic on INFEASIBLE — not design claims."
        )
        out["note"] = note + " " + out["phys_kpi_note"]
    return out
