from __future__ import annotations
"""Constraint Dominance Topology (v158)

Downstream-only analysis of infeasibility causes over a v156 feasibility field.
- Computes dominance labels per point (dominant violated constraint) and margin.
- Computes connected components per constraint over the 2D grid using 4-neighborhood.
- Produces an auditable dominance + topology artifact.

Schema:
kind: shams_constraint_dominance, version: v158
"""

from typing import Any, Dict, List, Tuple, Optional
import json, time, hashlib, math, copy
from pathlib import Path
from collections import deque, defaultdict

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _canon_json(o: Any) -> bytes:
    return json.dumps(o, indent=2, sort_keys=True, default=str).encode("utf-8")

def _sha_bytes(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def _sha_obj(o: Any) -> str:
    return _sha_bytes(_canon_json(o))

def _grid_from_field(field: Dict[str, Any]) -> Tuple[str, List[float], str, List[float]]:
    dom=(field.get("payload") or {}).get("domain") or {}
    params=dom.get("parameters") or []
    if not (isinstance(params, list) and len(params)==2):
        raise ValueError("field domain parameters must have 2 axes")
    a1=params[0]; a2=params[1]
    def grid(ax):
        g=(ax.get("grid") or {})
        if str(g.get("type") or "") != "linspace":
            raise ValueError("v158 requires linspace grids")
        start=float(g.get("start"))
        stop=float(g.get("stop"))
        n=int(g.get("n"))
        if n<2:
            return [start]
        step=(stop-start)/(n-1)
        return [start+i*step for i in range(n)]
    return str(a1.get("name")), grid(a1), str(a2.get("name")), grid(a2)

def _margin(p: Dict[str, Any]) -> float:
    try:
        return float(((p.get("margin") or {}).get("min_constraint_margin")))
    except Exception:
        return float("nan")

def _dom(p: Dict[str, Any]) -> str:
    try:
        return str(((p.get("margin") or {}).get("dominant_constraint")) or "")
    except Exception:
        return ""

def build_constraint_dominance(
    *,
    field: Dict[str, Any],
    only_infeasible: bool = True,
) -> Dict[str, Any]:
    if not (isinstance(field, dict) and field.get("kind")=="shams_feasibility_field" and field.get("version")=="v156"):
        raise ValueError("Expected v156 feasibility field")
    a1_name, a1_grid, a2_name, a2_grid = _grid_from_field(field)

    pts = (((field.get("payload") or {}).get("field") or {}).get("points") or [])
    if not isinstance(pts, list):
        pts=[]

    # index points
    idx = {}
    for p in pts:
        if not isinstance(p, dict): 
            continue
        x=p.get("x") or {}
        try:
            k=(float(x.get(a1_name)), float(x.get(a2_name)))
        except Exception:
            continue
        idx[k]=p

    # build label grid
    n1=len(a1_grid); n2=len(a2_grid)
    label=[["" for _ in range(n2)] for __ in range(n1)]
    margin=[[float("nan") for _ in range(n2)] for __ in range(n1)]
    status=[["" for _ in range(n2)] for __ in range(n1)]

    dom_counts=defaultdict(int)
    infeas_count=0
    feas_count=0

    for i,v1 in enumerate(a1_grid):
        for j,v2 in enumerate(a2_grid):
            p=idx.get((float(v1), float(v2)))
            if not p:
                continue
            st=str(p.get("status") or "")
            status[i][j]=st
            m=_margin(p); margin[i][j]=m
            d=_dom(p)
            if only_infeasible and st!="infeasible":
                if st=="feasible": feas_count += 1
                continue
            if st=="feasible": feas_count += 1
            if st=="infeasible": infeas_count += 1
            label[i][j]=d
            if d:
                dom_counts[d]+=1

    # connected components for each constraint label over infeasible points
    visited=[[False for _ in range(n2)] for __ in range(n1)]
    regions_by_constraint=defaultdict(list)
    comps_total=0

    def neigh(ii,jj):
        for di,dj in ((1,0),(-1,0),(0,1),(0,-1)):
            ni=ii+di; nj=jj+dj
            if 0<=ni<n1 and 0<=nj<n2:
                yield ni,nj

    for i in range(n1):
        for j in range(n2):
            if visited[i][j]:
                continue
            if status[i][j]!="infeasible":
                visited[i][j]=True
                continue
            c=label[i][j]
            if not c:
                visited[i][j]=True
                continue
            # BFS component of same label
            q=deque([(i,j)])
            visited[i][j]=True
            cells=[]
            min_m=math.inf
            while q:
                ii,jj=q.popleft()
                cells.append((ii,jj))
                mm=margin[ii][jj]
                if math.isfinite(mm):
                    min_m=min(min_m, mm)
                for ni,nj in neigh(ii,jj):
                    if visited[ni][nj]:
                        continue
                    if status[ni][nj]!="infeasible":
                        visited[ni][nj]=True
                        continue
                    if label[ni][nj]!=c:
                        continue
                    visited[ni][nj]=True
                    q.append((ni,nj))
            comps_total += 1
            # area fraction on grid = cells / total points
            regions_by_constraint[c].append({
                "component_id": len(regions_by_constraint[c]) + 1,
                "topology": "connected",
                "n_cells": len(cells),
                "area_fraction": (len(cells)/float(n1*n2)) if (n1*n2) else 0.0,
                "min_margin": float(min_m) if min_m is not math.inf else float("nan"),
            })

    # map list (optional): keep lightweight by listing only infeasible points (or all if only_infeasible False)
    dom_map=[]
    for i,v1 in enumerate(a1_grid):
        for j,v2 in enumerate(a2_grid):
            st=status[i][j]
            if only_infeasible and st!="infeasible":
                continue
            c=label[i][j]
            if not c:
                continue
            dom_map.append({
                "x": {a1_name: float(v1), a2_name: float(v2)},
                "dominant_constraint": c,
                "margin": float(margin[i][j]) if math.isfinite(margin[i][j]) else None,
            })

    regions=[]
    for c, comps in regions_by_constraint.items():
        regions.append({
            "constraint": c,
            "components": comps,
        })
    # rank constraints by count
    ranked=[{"name":k, "count":int(v), "n_components": len(regions_by_constraint.get(k,[]))} for k,v in sorted(dom_counts.items(), key=lambda kv: kv[1], reverse=True)]
    summary={
        "n_points": int(n1*n2),
        "n_infeasible": int(infeas_count),
        "n_feasible": int(feas_count),
        "dominant_constraints_ranked": ranked[:20],
        "total_components": int(comps_total),
    }

    out={
        "kind":"shams_constraint_dominance",
        "version":"v158",
        "issued_utc": _utc(),
        "shams_version": str((Path(__file__).resolve().parents[1]/"VERSION").read_text(encoding="utf-8").strip().splitlines()[0]),
        "study_id": str(field.get("study_id") or ""),
        "provenance": {
            "generator":"ui",
            "methods":["v156_sampling","v158_constraint_dominance"],
        },
        "assumptions": field.get("assumptions") or {},
        "integrity": {"object_sha256": ""},
        "payload": {
            "domain_ref": {"kind":"shams_feasibility_field","sha256": str((field.get("integrity") or {}).get("object_sha256") or "")},
            "axes": {"axis1": a1_name, "axis2": a2_name},
            "dominance": {
                "map": dom_map,
                "regions": regions,
                "summary": summary,
            },
        },
    }
    tmp=copy.deepcopy(out)
    tmp["integrity"]={"object_sha256": ""}
    out["integrity"]["object_sha256"]=_sha_obj(tmp)
    return out



# ---------------------------------------------------------------------------
# v158 report helper (used by ui_self_test): payload-level dominance ranking
# ---------------------------------------------------------------------------
def build_constraint_dominance_report(
    payloads: List[Dict[str, Any]],
    near_threshold: float = 0.05,
    fail_weight: float = 4.0,
) -> Dict[str, Any]:
    """Build a lightweight dominance report over a list of shams_run_artifact payloads.

    This is NOT a replacement for the v156-field topology object.
    It's a quick ranking used by the UI self-test and for small ad-hoc collections.
    """
    def dominant_from_payload(art: Dict[str, Any]) -> Tuple[str, float]:
        cons = art.get("constraints") or []
        best=("", float("inf"))
        if isinstance(cons, list):
            for c in cons:
                if not isinstance(c, dict):
                    continue
                try:
                    m=float(c.get("margin"))
                except Exception:
                    continue
                if m < best[1]:
                    best=(str(c.get("name") or ""), m)
        if best[1] is float("inf"):
            return ("", float("nan"))
        return best

    counts={}
    near={}
    total=len(payloads)
    n_fail=0
    n_near=0
    rows=[]
    for art in payloads:
        if not isinstance(art, dict) or art.get("kind")!="shams_run_artifact":
            continue
        dom, m = dominant_from_payload(art)
        ok = (isinstance(m, float) and math.isfinite(m) and m>=0.0)
        if not ok:
            n_fail += 1
        if isinstance(m, float) and math.isfinite(m) and abs(m) <= float(near_threshold):
            n_near += 1
            if dom:
                near[dom]=near.get(dom,0)+1
        if dom:
            # weighted count: failures get higher weight to surface hard blockers
            w = float(fail_weight) if (not ok) else 1.0
            counts[dom]=counts.get(dom,0.0)+w
        rows.append({"run_id": str(art.get("id") or ""), "dominant_constraint": dom, "min_margin": m, "feasible": bool(ok)})

    ranked=[{"name":k, "score":float(v), "near_count": int(near.get(k,0))} for k,v in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)]
    return {
        "kind":"shams_constraint_dominance_report",
        "version":"v158",
        "issued_utc": _utc(),
        "summary": {
            "n_payloads": int(total),
            "n_fail": int(n_fail),
            "n_near": int(n_near),
            "near_threshold": float(near_threshold),
            "fail_weight": float(fail_weight),
        },
        "ranked": ranked[:20],
        "rows": rows[:500],  # cap
    }

# Backward-compatible alias name used elsewhere
def build_constraint_dominance_report_v158(*args, **kwargs) -> Dict[str, Any]:
    return build_constraint_dominance_report(*args, **kwargs)
