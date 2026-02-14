from __future__ import annotations
"""Feasibility Boundary Atlas v2 (v110)

Adds explicit boundary extraction between feasible and infeasible samples for lever-pair slices,
and labels boundary segments with dominant failure mode (when available).

This is additive only: it operates on SHAMS artifacts/payloads and produces a report + plots.
No physics, no solver changes.

Core idea:
- Collect feasible and infeasible points with lever values.
- For each lever pair, compute boundary points by connecting each infeasible point to nearest feasible
  neighbor and taking midpoints (filtered by proximity). This is robust, cheap, and audit-friendly.
- Cluster boundary points into polylines by simple nearest-neighbor chaining.
- Label boundary points by nearest failure record (mode) if provided.
"""

from typing import Any, Dict, List, Optional, Tuple
import time
import math

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _is_num(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False

def _get_feasible_flag(artifact: Dict[str, Any]) -> Optional[bool]:
    cs = artifact.get("constraints_summary")
    if isinstance(cs, dict) and "feasible" in cs:
        return bool(cs.get("feasible"))
    # fallback: constraints list
    cons = artifact.get("constraints")
    if isinstance(cons, list):
        any_fail = any(isinstance(c, dict) and c.get("passed") is False for c in cons)
        return not any_fail
    return None

def extract_points_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract point dicts with at least: inputs, feasible flag."""
    pts: List[Dict[str, Any]] = []
    if not isinstance(payload, dict):
        return pts
    kind = payload.get("kind")
    if kind == "shams_run_artifact":
        inp = payload.get("inputs", {})
        if isinstance(inp, dict):
            pts.append({"inputs": inp, "feasible": _get_feasible_flag(payload), "artifact": payload})
        return pts

    # Atlas / sandbox payloads are different kinds but contain lists
    # We'll scan for embedded run artifacts or point records with inputs/constraints_summary
    # Conservative approach: recursively look for dicts that look like run artifacts.
    stack = [payload]
    seen = 0
    while stack and seen < 50000:
        seen += 1
        obj = stack.pop()
        if isinstance(obj, dict):
            if obj.get("kind") == "shams_run_artifact":
                inp = obj.get("inputs", {})
                if isinstance(inp, dict):
                    pts.append({"inputs": inp, "feasible": _get_feasible_flag(obj), "artifact": obj})
            else:
                for v in obj.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
        elif isinstance(obj, list):
            for v in obj:
                if isinstance(v, (dict, list)):
                    stack.append(v)
    return pts

def _collect_lever_keys(points: List[Dict[str, Any]], lever_keys: Optional[List[str]]) -> List[str]:
    if lever_keys:
        return [k for k in lever_keys if isinstance(k, str)]
    keys = None
    for p in points:
        inp = p.get("inputs")
        if not isinstance(inp, dict):
            continue
        ks = {k for k,v in inp.items() if isinstance(k, str) and _is_num(v)}
        keys = ks if keys is None else (keys & ks)
    return sorted(list(keys or []))

def _bounds(points: List[Dict[str, Any]], keys: List[str]) -> Dict[str, List[float]]:
    out: Dict[str, List[float]] = {}
    for k in keys:
        vals = []
        for p in points:
            inp = p.get("inputs", {})
            if isinstance(inp, dict) and k in inp and _is_num(inp[k]):
                vals.append(float(inp[k]))
        if vals:
            lo = min(vals); hi = max(vals)
            if hi - lo < 1e-12:
                hi = lo + 1e-12
            out[k] = [lo, hi]
    return out

def _scaled_dist(a: Dict[str, Any], b: Dict[str, Any], keys: List[str], scales: Dict[str, float]) -> float:
    s = 0.0; n = 0
    for k in keys:
        if k not in scales:
            continue
        if (k in a) and (k in b) and _is_num(a[k]) and _is_num(b[k]):
            dx = (float(a[k]) - float(b[k])) / scales[k]
            s += dx*dx; n += 1
    return math.sqrt(s / max(n, 1))

def _nearest(point: Dict[str, Any], pool: List[Dict[str, Any]], keys: List[str], scales: Dict[str, float]) -> Tuple[Optional[int], float]:
    best_i = None
    best_d = 1e99
    for i, q in enumerate(pool):
        d = _scaled_dist(point, q, keys, scales)
        if d < best_d:
            best_d = d
            best_i = i
    return best_i, best_d

def _midpoint(a: Dict[str, Any], b: Dict[str, Any], kx: str, ky: str) -> Optional[Dict[str, Any]]:
    if not (_is_num(a.get(kx)) and _is_num(a.get(ky)) and _is_num(b.get(kx)) and _is_num(b.get(ky))):
        return None
    return {kx: 0.5*(float(a[kx]) + float(b[kx])), ky: 0.5*(float(a[ky]) + float(b[ky]))}

def _chain_points(points: List[Dict[str, Any]], kx: str, ky: str, max_step: float) -> List[List[Dict[str, Any]]]:
    """Simple chaining: repeatedly grow a polyline by nearest neighbor within max_step."""
    remaining = points[:]
    polylines: List[List[Dict[str, Any]]] = []
    def dist(p,q):
        return math.hypot(float(p[kx]) - float(q[kx]), float(p[ky]) - float(q[ky]))
    while remaining:
        line = [remaining.pop()]
        grown = True
        while grown and remaining:
            grown = False
            # extend front
            best_j = None; best_d = None
            for j, q in enumerate(remaining):
                d = dist(line[0], q)
                if (best_d is None or d < best_d) and d <= max_step:
                    best_d = d; best_j = j
            if best_j is not None:
                line.insert(0, remaining.pop(best_j))
                grown = True
            # extend back
            best_j = None; best_d = None
            for j, q in enumerate(remaining):
                d = dist(line[-1], q)
                if (best_d is None or d < best_d) and d <= max_step:
                    best_d = d; best_j = j
            if best_j is not None:
                line.append(remaining.pop(best_j))
                grown = True
        # sort line by x then y for determinism
        line.sort(key=lambda p: (float(p[kx]), float(p[ky])))
        polylines.append(line)
    polylines.sort(key=lambda L: -len(L))
    return polylines

def build_boundary_atlas_v2(
    payloads: List[Dict[str, Any]],
    *,
    lever_pairs: Optional[List[Tuple[str, str]]] = None,
    failure_taxonomy: Optional[Dict[str, Any]] = None,
    max_pairs: int = 6,
    max_points_per_pair: int = 1500,
    proximity_quantile: float = 0.25,
) -> Dict[str, Any]:
    points_raw: List[Dict[str, Any]] = []
    for p in payloads or []:
        points_raw.extend(extract_points_from_payload(p))

    # flatten to dicts of lever numeric values
    lever_keys = _collect_lever_keys(points_raw, None)
    if not lever_keys:
        return {
            "kind": "shams_boundary_atlas_v2",
            "created_utc": _created_utc(),
            "n_points": 0,
            "error": "No numeric lever keys found in payloads.",
            "slices": [],
        }

    # default lever pairs
    if lever_pairs is None:
        candidates = []
        # common SHAMS levers first if present
        preferred = ["R0_m", "a_m", "Bt_T", "Ip_MA", "fG", "Ti_keV", "Paux_MW", "kappa"]
        pref = [k for k in preferred if k in lever_keys]
        for i in range(len(pref)):
            for j in range(i+1, len(pref)):
                candidates.append((pref[i], pref[j]))
        # add any remaining combos
        for i in range(min(6, len(lever_keys))):
            for j in range(i+1, min(8, len(lever_keys))):
                candidates.append((lever_keys[i], lever_keys[j]))
        # unique keep order
        seen=set(); lp=[]
        for a,b in candidates:
            if a==b: continue
            key=(a,b)
            if key in seen: continue
            seen.add(key)
            lp.append((a,b))
        lever_pairs = lp[:max_pairs]
    else:
        lever_pairs = lever_pairs[:max_pairs]

    # prepare failure records for labeling
    failure_records = []
    if isinstance(failure_taxonomy, dict):
        recs = failure_taxonomy.get("records", [])
        if isinstance(recs, list):
            for r in recs:
                if isinstance(r, dict) and isinstance(r.get("inputs"), dict) and isinstance(r.get("mode"), str):
                    failure_records.append(r)

    # build atlas slices
    slices = []
    # prebuild feasible/infeasible pools for each pair
    for (kx, ky) in lever_pairs:
        feas = []
        infeas = []
        for pr in points_raw:
            inp = pr.get("inputs", {})
            if not isinstance(inp, dict):
                continue
            if not (_is_num(inp.get(kx)) and _is_num(inp.get(ky))):
                continue
            item = {kx: float(inp[kx]), ky: float(inp[ky]), "id": (pr.get("artifact") or {}).get("id")}
            feas_flag = pr.get("feasible")
            if feas_flag is True:
                feas.append(item)
            elif feas_flag is False:
                infeas.append(item)
        if len(feas) < 8 or len(infeas) < 8:
            continue

        bounds = _bounds([{"inputs": {kx: f[kx], ky: f[ky]}} for f in (feas+infeas)], [kx,ky])
        scales = {kx: max(bounds.get(kx, [0.0,1.0])[1] - bounds.get(kx, [0.0,1.0])[0], 1e-12),
                  ky: max(bounds.get(ky, [0.0,1.0])[1] - bounds.get(ky, [0.0,1.0])[0], 1e-12)}

        # For each infeasible, find nearest feasible; create boundary midpoint with distance
        mids = []
        dists = []
        for q in infeas:
            idx, d = _nearest(q, feas, [kx,ky], scales)
            if idx is None:
                continue
            m = _midpoint(q, feas[idx], kx, ky)
            if m is None:
                continue
            m["d_scaled"] = float(d)
            mids.append(m)
            dists.append(float(d))

        if not mids:
            continue
        dists_sorted = sorted(dists)
        thr = dists_sorted[int(max(0, min(len(dists_sorted)-1, int(proximity_quantile*(len(dists_sorted)-1)))))]
        # keep close boundary points
        mids = [m for m in mids if float(m.get("d_scaled", 1e9)) <= float(thr)]
        # cap
        mids = mids[:max_points_per_pair]

        # chain into polylines (in raw coordinate space) with max_step based on span
        span = max(scales[kx], scales[ky])
        max_step = 0.08 * span  # deterministic heuristic
        polylines = _chain_points(mids, kx, ky, max_step=max_step)

        # label points with nearest failure record mode (using inputs in this 2D plane)
        def nearest_failure_mode(pt):
            if not failure_records:
                return None
            best = None
            best_d = None
            for r in failure_records:
                inp = r.get("inputs", {})
                if not isinstance(inp, dict):
                    continue
                if not (_is_num(inp.get(kx)) and _is_num(inp.get(ky))):
                    continue
                dx = (float(pt[kx]) - float(inp[kx])) / scales[kx]
                dy = (float(pt[ky]) - float(inp[ky])) / scales[ky]
                d = math.sqrt(dx*dx + dy*dy)
                if best_d is None or d < best_d:
                    best_d = d
                    best = r.get("mode")
            return best

        labeled_lines = []
        for line in polylines[:12]:
            out_line = []
            for pt in line:
                out_pt = {kx: pt[kx], ky: pt[ky]}
                mode = nearest_failure_mode(pt)
                if isinstance(mode, str):
                    out_pt["mode"] = mode
                out_line.append(out_pt)
            labeled_lines.append(out_line)

        slices.append({
            "lever_x": kx,
            "lever_y": ky,
            "n_feasible": len(feas),
            "n_infeasible": len(infeas),
            "boundary_quantile": float(proximity_quantile),
            "boundary_threshold_scaled": float(thr),
            "boundary_polylines": labeled_lines,
            "bounds": bounds,
        })

    return {
        "kind": "shams_boundary_atlas_v2",
        "created_utc": _created_utc(),
        "n_payloads": len(payloads or []),
        "n_points_raw": len(points_raw),
        "lever_pairs": [{"x": a, "y": b} for (a,b) in (lever_pairs or [])],
        "slices": slices,
    }
