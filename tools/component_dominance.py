from __future__ import annotations
"""Component-local dominance & boundary-near failures (v109)

Adds per-topology-component causality:
- assigns feasible run artifacts to feasible islands (components)
- computes dominance ranking per component (subset of run artifacts)
- maps failure taxonomy records to nearest component and aggregates per component

Additive only.
"""

from typing import Any, Dict, List, Optional
import time
import math

from tools.constraint_dominance import build_constraint_dominance_report

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _is_num(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False

def _scales_from_bounds(bounds: Dict[str, Any], lever_keys: List[str]) -> Dict[str, float]:
    scales: Dict[str, float] = {}
    if not isinstance(bounds, dict):
        return scales
    for k in lever_keys:
        ab = bounds.get(k)
        if isinstance(ab, list) and len(ab) == 2 and _is_num(ab[0]) and _is_num(ab[1]):
            scales[k] = max(float(ab[1]) - float(ab[0]), 1e-12)
    return scales

def _nearest_component_index(topology: Dict[str, Any], point: Dict[str, Any]) -> Optional[int]:
    pts = topology.get("points")
    comps = topology.get("components")
    lever_keys = topology.get("lever_keys")
    bounds = topology.get("lever_bounds")
    if not (isinstance(pts, list) and isinstance(comps, list) and isinstance(lever_keys, list) and isinstance(bounds, dict)):
        return None
    lever_keys = [k for k in lever_keys if isinstance(k, str) and k and k != "..."]
    scales = _scales_from_bounds(bounds, lever_keys)
    if not scales:
        # fall back to using common numeric keys across topology points
        keys = []
        for p in pts[:50]:
            if isinstance(p, dict):
                for k,v in p.items():
                    if isinstance(k,str) and _is_num(v) and k not in keys and k != "...":
                        keys.append(k)
        lever_keys = keys[:24]
        scales = {k: 1.0 for k in lever_keys}

    best_i = None
    best_d = None
    for i, p in enumerate(pts):
        if not isinstance(p, dict):
            continue
        s = 0.0
        n = 0
        for k in lever_keys:
            if k not in scales:
                continue
            if k not in p or k not in point:
                continue
            if not (_is_num(p[k]) and _is_num(point[k])):
                continue
            dx = (float(point[k]) - float(p[k])) / float(scales[k])
            s += dx*dx
            n += 1
        if n == 0:
            continue
        d = math.sqrt(s / n)
        if best_d is None or d < best_d:
            best_d = d
            best_i = i
    if best_i is None:
        return None
    for ci, comp in enumerate(comps):
        if isinstance(comp, list) and best_i in comp:
            return ci
    return None

def build_component_dominance_report(
    *,
    topology: Dict[str, Any],
    run_artifacts: List[Dict[str, Any]],
    failure_taxonomy: Optional[Dict[str, Any]] = None,
    near_threshold: float = 0.05,
    fail_weight: float = 4.0,
    max_components: int = 200,
) -> Dict[str, Any]:
    created = _created_utc()

    comps = topology.get("components", [])
    if not isinstance(comps, list):
        comps = []
    n_components = min(len(comps), int(max_components))

    # assign feasible run artifacts to components
    by_comp: Dict[int, List[Dict[str, Any]]] = {}
    for a in run_artifacts or []:
        if not (isinstance(a, dict) and a.get("kind") == "shams_run_artifact"):
            continue
        cs = a.get("constraints_summary")
        feasible = bool(cs.get("feasible")) if isinstance(cs, dict) and "feasible" in cs else None
        # Only feasible artifacts define islands; skip infeasible for dominance-inside-island
        if feasible is not True:
            continue
        inp = a.get("inputs", {})
        if not isinstance(inp, dict):
            continue
        ci = _nearest_component_index(topology, inp)
        if ci is None or ci >= n_components:
            continue
        by_comp.setdefault(ci, []).append(a)

    # per-component dominance
    comp_entries: List[Dict[str, Any]] = []
    for ci in range(n_components):
        payloads = by_comp.get(ci, [])
        dom = build_constraint_dominance_report(payloads, near_threshold=float(near_threshold), fail_weight=float(fail_weight))
        ranked = dom.get("constraints_ranked", [])
        top_constraints = []
        if isinstance(ranked, list):
            for r in ranked[:8]:
                if isinstance(r, dict):
                    top_constraints.append({
                        "name": r.get("name"),
                        "score": r.get("dominance_score"),
                        "fail_rate": r.get("fail_rate"),
                        "near_rate": r.get("near_boundary_rate"),
                    })
        comp_entries.append({
            "component_index": ci,
            "component_size_points": len(comps[ci]) if (ci < len(comps) and isinstance(comps[ci], list)) else None,
            "n_feasible_runs_assigned": len(payloads),
            "dominance_top_constraints": top_constraints,
        })

    # per-component failures near boundary (using failure taxonomy record inputs)
    if isinstance(failure_taxonomy, dict):
        records = failure_taxonomy.get("records", [])
        if isinstance(records, list):
            mode_counts_by_comp: Dict[int, Dict[str, int]] = {}
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                pt = rec.get("inputs", {})
                if not isinstance(pt, dict):
                    continue
                ci = _nearest_component_index(topology, pt)
                if ci is None or ci >= n_components:
                    continue
                mode = rec.get("mode")
                if not isinstance(mode, str):
                    continue
                mode_counts_by_comp.setdefault(ci, {}).setdefault(mode, 0)
                mode_counts_by_comp[ci][mode] += 1

            for e in comp_entries:
                ci = int(e["component_index"])
                mcounts = mode_counts_by_comp.get(ci, {})
                topm = []
                if isinstance(mcounts, dict) and mcounts:
                    for m, v in sorted(mcounts.items(), key=lambda kv: kv[1], reverse=True)[:6]:
                        topm.append({"mode": m, "count": v})
                e["top_failure_modes_near_component"] = topm

    # sort components by size (points) then by assigned runs
    comp_entries.sort(key=lambda e: (e.get("component_size_points") or 0, e.get("n_feasible_runs_assigned") or 0), reverse=True)

    report = {
        "kind": "shams_component_dominance_report",
        "created_utc": created,
        "near_threshold": float(near_threshold),
        "fail_weight": float(fail_weight),
        "n_run_artifacts": len(run_artifacts or []),
        "n_components": n_components,
        "components": comp_entries,
    }
    return report
