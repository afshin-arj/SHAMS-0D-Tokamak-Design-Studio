from __future__ import annotations
"""Feasible Space Topology (v104)

Builds a lightweight *feasibility topology graph* from feasible points produced by SHAMS
(Scan Lab feasible sets, Feasibility Boundary Atlas, sandbox logs).

No external dependencies. Additive only.
"""

from typing import Any, Dict, List, Tuple, Optional
import time
import math

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _l2_scaled(a: Dict[str, float], b: Dict[str, float], scales: Dict[str, float]) -> float:
    s = 0.0
    n = 0
    for k, sc in scales.items():
        if sc <= 0:
            continue
        if k not in a or k not in b:
            continue
        try:
            da = (float(a[k]) - float(b[k])) / float(sc)
        except Exception:
            continue
        s += da * da
        n += 1
    if n == 0:
        return float("inf")
    return math.sqrt(s / n)

def _connected_components(n: int, edges: List[Tuple[int,int]]) -> List[List[int]]:
    adj = [[] for _ in range(n)]
    for i,j in edges:
        adj[i].append(j)
        adj[j].append(i)
    seen = [False]*n
    comps: List[List[int]] = []
    for i in range(n):
        if seen[i]:
            continue
        stack=[i]
        seen[i]=True
        comp=[]
        while stack:
            u=stack.pop()
            comp.append(u)
            for v in adj[u]:
                if not seen[v]:
                    seen[v]=True
                    stack.append(v)
        comps.append(sorted(comp))
    comps.sort(key=len, reverse=True)
    return comps

def build_feasible_topology(
    points: List[Dict[str, Any]],
    *,
    lever_keys: Optional[List[str]] = None,
    lever_bounds: Optional[Dict[str, Tuple[float,float]]] = None,
    eps: float = 0.18,
    max_points: int = 600,
) -> Dict[str, Any]:
    """Build a simple graph + components from feasible points.

    Parameters
    ----------
    points:
        List of dicts containing lever values (e.g. R0_m, a_m, Bt_T, Ip_MA, fG).
    lever_keys:
        Explicit keys; otherwise inferred as intersection of numeric keys.
    lever_bounds:
        Optional bounds for scaling; otherwise uses min/max from points.
    eps:
        Edge threshold in scaled L2 distance.
    max_points:
        Safety cap (downsample deterministically by truncation).
    """
    pts = [p for p in (points or []) if isinstance(p, dict)]
    if len(pts) > max_points:
        pts = pts[:max_points]

    # infer lever keys (numeric) if not given
    if lever_keys is None:
        numeric_keys = None
        for p in pts:
            ks=set()
            for k,v in p.items():
                try:
                    float(v)
                    ks.add(k)
                except Exception:
                    pass
            numeric_keys = ks if numeric_keys is None else (numeric_keys & ks)
        lever_keys = sorted(list(numeric_keys or []))

    # compute scaling
    bounds: Dict[str, Tuple[float,float]] = {}
    if lever_bounds:
        for k,(lo,hi) in lever_bounds.items():
            try:
                bounds[k]=(float(lo), float(hi))
            except Exception:
                pass
    for k in lever_keys:
        if k in bounds:
            continue
        vals=[]
        for p in pts:
            try:
                vals.append(float(p.get(k)))
            except Exception:
                pass
        if len(vals) >= 2:
            bounds[k] = (min(vals), max(vals))
        elif len(vals) == 1:
            v=vals[0]
            bounds[k] = (v, v if v!=0 else 1.0)

    scales: Dict[str, float] = {}
    for k,(lo,hi) in bounds.items():
        sc = float(hi) - float(lo)
        if sc <= 0:
            sc = max(abs(float(hi)), 1.0)
        scales[k]=sc

    # compress points to lever-only numeric dicts
    lp: List[Dict[str, float]] = []
    for p in pts:
        d: Dict[str, float] = {}
        for k in lever_keys:
            if k in p:
                try:
                    d[k]=float(p[k])
                except Exception:
                    pass
        lp.append(d)

    n = len(lp)
    edges: List[Tuple[int,int]] = []
    # brute-force edge build (n capped)
    for i in range(n):
        for j in range(i+1, n):
            if _l2_scaled(lp[i], lp[j], scales) <= eps:
                edges.append((i,j))

    comps = _connected_components(n, edges) if n>0 else []
    topology = {
        "kind": "shams_feasible_topology",
        "created_utc": _created_utc(),
        "n_points": n,
        "n_edges": len(edges),
        "eps": float(eps),
        "lever_keys": lever_keys,
        "lever_bounds": {k: [float(lo), float(hi)] for k,(lo,hi) in bounds.items()},
        "components": comps,
        "points": lp,
    }
    return topology

def extract_feasible_points_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Best-effort extractor from common SHAMS payloads."""
    if not isinstance(payload, dict):
        return []
    kind = payload.get("kind")
    pts: List[Dict[str, Any]] = []

    # Scan Lab feasible set
    if kind == "shams_feasible_set":
        p = payload.get("points")
        if isinstance(p, list):
            pts += [x for x in p if isinstance(x, dict)]
        return pts

    # Feasibility Boundary Atlas
    if kind == "shams_feasibility_boundary_atlas":
        baseline = payload.get("baseline", {})
        if isinstance(baseline, dict):
            rep = baseline.get("report", {})
            if isinstance(rep, dict) and rep.get("best_ok") and isinstance(rep.get("best_levers"), dict):
                pts.append(rep["best_levers"])
        for r in payload.get("reports", []) if isinstance(payload.get("reports"), list) else []:
            if not isinstance(r, dict):
                continue
            rep = r.get("report", {})
            if isinstance(rep, dict) and rep.get("best_ok") and isinstance(rep.get("best_levers"), dict):
                pts.append(rep["best_levers"])
        return pts

    # Sandbox run (v103.1+)
    if kind in ("shams_optimizer_sandbox_run", "shams_optimizer_sandbox_run_plus", "shams_optimizer_sandbox_run_v103"):
        best = payload.get("best_inputs")
        if isinstance(best, dict):
            pts.append(best)
        return pts

    # Run artifact (point) - include if explicitly feasible
    if kind == "shams_run_artifact":
        ok = payload.get("constraints_summary", {}).get("ok") if isinstance(payload.get("constraints_summary"), dict) else None
        if ok is True and isinstance(payload.get("inputs"), dict):
            pts.append(payload["inputs"])
        return pts

    return []
