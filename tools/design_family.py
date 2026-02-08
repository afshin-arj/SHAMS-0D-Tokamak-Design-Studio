from __future__ import annotations
"""Design Family Explorer (v111)

Purpose:
- Explore *within* a feasible topology island (component) using safe, bounded local perturbations.
- No optimization. No solver changes. No physics changes.
- Produces a report that is publishable + audit-ready.

Inputs:
- topology (from v104)
- baseline_inputs (a full PointInputs dict; we only modify lever keys that exist there)
- component_index
- radius_frac: perturbation radius as fraction of (hi-lo) per lever
- n_samples

Outputs:
- report dict with:
  - summary stats (feasible fraction, worst constraints distribution)
  - per-sample rows (inputs + feasible + worst hard constraint)
"""

from typing import Any, Dict, List, Optional, Tuple
import time
import random
import math

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _is_num(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False

def _topo_component_points(topology: Dict[str, Any], component_index: int) -> List[Dict[str, Any]]:
    pts = topology.get("points")
    comps = topology.get("components")
    if not (isinstance(pts, list) and isinstance(comps, list)):
        return []
    if component_index < 0 or component_index >= len(comps):
        return []
    idxs = comps[component_index]
    if not isinstance(idxs, list):
        return []
    out = []
    for i in idxs:
        if isinstance(i, int) and 0 <= i < len(pts) and isinstance(pts[i], dict):
            out.append(pts[i])
    return out

def _lever_keys(topology: Dict[str, Any], baseline_inputs: Dict[str, Any]) -> List[str]:
    lk = topology.get("lever_keys")
    if isinstance(lk, list):
        keys = [k for k in lk if isinstance(k, str) and k in baseline_inputs]
        if keys:
            return keys
    # fallback: numeric keys shared across points and baseline
    pts = topology.get("points", [])
    keys = []
    if isinstance(pts, list):
        for p in pts[:40]:
            if isinstance(p, dict):
                for k, v in p.items():
                    if isinstance(k, str) and k in baseline_inputs and _is_num(v) and k not in keys:
                        keys.append(k)
    return keys

def _lever_bounds(topology: Dict[str, Any], keys: List[str], points: List[Dict[str, Any]], baseline_inputs: Dict[str, Any]) -> Dict[str, Tuple[float, float]]:
    bounds: Dict[str, Tuple[float, float]] = {}
    tb = topology.get("lever_bounds")
    if isinstance(tb, dict):
        for k in keys:
            b = tb.get(k)
            if isinstance(b, list) and len(b) == 2 and _is_num(b[0]) and _is_num(b[1]):
                lo = float(b[0]); hi = float(b[1])
                if hi - lo < 1e-12:
                    hi = lo + 1e-12
                bounds[k] = (lo, hi)
    # fill missing from observed points
    for k in keys:
        if k in bounds:
            continue
        vals = []
        for p in points:
            if isinstance(p, dict) and k in p and _is_num(p[k]):
                vals.append(float(p[k]))
        if vals:
            lo = min(vals); hi = max(vals)
            if hi - lo < 1e-12:
                hi = lo + 1e-12
            bounds[k] = (lo, hi)
        elif _is_num(baseline_inputs.get(k)):
            v = float(baseline_inputs[k])
            bounds[k] = (v - 1e-6, v + 1e-6)
    return bounds

def _constraint_summary(artifact: Dict[str, Any]) -> Dict[str, Any]:
    cs = artifact.get("constraints_summary")
    if isinstance(cs, dict):
        return cs
    # derive from constraints list
    cons = artifact.get("constraints", [])
    worst_name = None
    worst_mf = None
    feasible = True
    if isinstance(cons, list):
        for c in cons:
            if not isinstance(c, dict):
                continue
            if c.get("passed") is False:
                feasible = False
            mf = c.get("margin_frac")
            if _is_num(mf):
                mf = float(mf)
                if (worst_mf is None) or (mf < worst_mf):
                    worst_mf = mf
                    worst_name = c.get("name")
    return {"feasible": feasible, "worst_hard": worst_name, "worst_hard_margin_frac": worst_mf}

def build_design_family_report(
    *,
    topology: Dict[str, Any],
    component_index: int,
    baseline_inputs: Dict[str, Any],
    n_samples: int = 120,
    radius_frac: float = 0.08,
    seed: int = 0,
) -> Dict[str, Any]:
    created = _created_utc()
    rng = random.Random(int(seed))

    points = _topo_component_points(topology, int(component_index))
    if not points:
        return {
            "kind": "shams_design_family_report",
            "created_utc": created,
            "error": f"No points found for component_index={component_index}",
        }

    base = dict(baseline_inputs) if isinstance(baseline_inputs, dict) else {}
    keys = _lever_keys(topology, base)
    bounds = _lever_bounds(topology, keys, points, base)

    # imports locally (keeps module pure)
    from models.inputs import PointInputs
    from physics.hot_ion import hot_ion_point
    from constraints.constraints import evaluate_constraints
    from shams_io.run_artifact import build_run_artifact

    rows: List[Dict[str, Any]] = []
    worst_counts: Dict[str, int] = {}
    feasible_n = 0

    # pick centers from the island points; if point lacks a key, fallback to baseline
    for i in range(int(max(1, n_samples))):
        center = points[rng.randrange(len(points))]
        inp = dict(base)
        for k in keys:
            lo, hi = bounds.get(k, (None, None))
            if lo is None or hi is None:
                continue
            # center value from topology point if present else baseline
            cv = center.get(k, inp.get(k))
            if not _is_num(cv):
                continue
            span = max(hi - lo, 1e-12)
            rad = float(radius_frac) * span
            v = float(cv) + rng.uniform(-rad, rad)
            # clamp
            v = max(lo, min(hi, v))
            inp[k] = v

        # build PointInputs from intersection of valid keys (dataclass will validate)
        try:
            pi = PointInputs(**inp)
        except TypeError:
            # drop unknown keys
            allowed = set(PointInputs.__annotations__.keys())
            inp2 = {k: v for k, v in inp.items() if k in allowed}
            pi = PointInputs(**inp2)

        out = hot_ion_point(pi)
        cons = evaluate_constraints(out)
        art = build_run_artifact(inputs=pi.to_dict(), outputs=out, constraints=cons, meta={"mode":"design_family", "component_index": int(component_index), "sample_index": i})
        cs = _constraint_summary(art)
        feas = bool(cs.get("feasible")) if "feasible" in cs else None
        if feas is True:
            feasible_n += 1
        w = cs.get("worst_hard") or "unknown"
        if isinstance(w, str):
            worst_counts[w] = worst_counts.get(w, 0) + 1

        rows.append({
            "sample_index": i,
            "feasible": feas,
            "worst_hard": cs.get("worst_hard"),
            "worst_hard_margin_frac": cs.get("worst_hard_margin_frac"),
            "inputs": pi.to_dict(),
        })

    n = len(rows)
    worst_ranked = [{"name": k, "count": v, "share": (v / max(1, n))} for k, v in sorted(worst_counts.items(), key=lambda kv: kv[1], reverse=True)]

    return {
        "kind": "shams_design_family_report",
        "created_utc": created,
        "component_index": int(component_index),
        "n_component_points": len(points),
        "lever_keys": keys,
        "lever_bounds": {k: [float(bounds[k][0]), float(bounds[k][1])] for k in bounds},
        "n_samples": n,
        "feasible_fraction": feasible_n / max(1, n),
        "worst_hard_ranked": worst_ranked[:20],
        "rows": rows,
    }
