from __future__ import annotations
"""Feasibility Boundary Extractor (v157)

Safe, downstream-only boundary extraction from a v156 feasibility field.
No physics or solver changes.

Method (v157):
- Assumes the v156 field was generated on a regular linspace x (axis1) × y (axis2) grid.
- Uses the scalar min_constraint_margin (positive=feasible, negative=infeasible).
- For each axis1 slice, finds the first sign change in axis2 and linearly interpolates the zero-crossing.
- Emits a boundary curve samples[] in (axis1 -> axis2) form.
- Confidence band is half the axis2 grid spacing around the interpolated crossing.
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import json, time, hashlib, math, copy

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _canon_json(o: Any) -> bytes:
    return json.dumps(o, indent=2, sort_keys=True, default=str).encode("utf-8")

def _sha_bytes(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def _sha_obj(o: Any) -> str:
    return _sha_bytes(_canon_json(o))

def _grid_from_domain(field: Dict[str, Any]) -> Tuple[str, List[float], str, List[float]]:
    dom=(field.get("payload") or {}).get("domain") or {}
    params=dom.get("parameters") or []
    if not (isinstance(params, list) and len(params)==2):
        raise ValueError("field domain parameters must have 2 axes")
    a1=params[0]; a2=params[1]
    def grid(ax):
        g=(ax.get("grid") or {})
        if str(g.get("type") or "") != "linspace":
            raise ValueError("v157 requires linspace grids")
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

def build_feasibility_boundary(
    *,
    field: Dict[str, Any],
    transition: Tuple[str, str] = ("infeasible","feasible"),
    method: str = "slice_interpolate",
    prefer_lowest_axis2: bool = True,
) -> Dict[str, Any]:
    if not (isinstance(field, dict) and field.get("kind")=="shams_feasibility_field" and field.get("version")=="v156"):
        raise ValueError("Expected v156 feasibility field")
    a1_name, a1_grid, a2_name, a2_grid = _grid_from_domain(field)

    pts = (((field.get("payload") or {}).get("field") or {}).get("points") or [])
    if not isinstance(pts, list):
        pts=[]
    # Index points by (a1,a2)
    idx={}
    for p in pts:
        if not isinstance(p, dict): 
            continue
        x=p.get("x") or {}
        try:
            k=(float(x.get(a1_name)), float(x.get(a2_name)))
        except Exception:
            continue
        idx[k]=p

    # For each a1, build margin vector over a2 in order
    samples=[]
    step2 = (a2_grid[1]-a2_grid[0]) if len(a2_grid)>1 else 0.0
    half_band = abs(step2)/2.0 if step2 else 0.0
    for v1 in a1_grid:
        arr=[]
        for v2 in a2_grid:
            p=idx.get((float(v1), float(v2)))
            m=_margin(p) if p else float("nan")
            arr.append((v2, m, p))
        # Find sign changes (m<=0 then m>=0) or opposite depending on transition
        # Using margin sign as feasibility indicator.
        crossings=[]
        for i in range(len(arr)-1):
            y0,m0,_=arr[i]
            y1,m1,_=arr[i+1]
            if not (math.isfinite(m0) and math.isfinite(m1)):
                continue
            # We treat boundary at m==0
            if (m0<=0 and m1>=0) or (m0>=0 and m1<=0):
                # interpolate crossing
                if m1==m0:
                    ystar = (y0+y1)/2.0
                else:
                    t = (0.0 - m0)/(m1-m0)
                    t = max(0.0, min(1.0, t))
                    ystar = y0 + t*(y1-y0)
                # dominant constraint at nearer point
                dom=""
                dom0=((arr[i][2] or {}).get("margin") or {}).get("dominant_constraint") if arr[i][2] else ""
                dom1=((arr[i+1][2] or {}).get("margin") or {}).get("dominant_constraint") if arr[i+1][2] else ""
                dom = str(dom0 or dom1 or "")
                crossings.append((ystar, dom, i))
        if crossings:
            # choose lowest axis2 crossing by default
            crossings.sort(key=lambda c: c[0])
            ystar, dom, i = crossings[0] if prefer_lowest_axis2 else crossings[-1]
            # estimate normal direction based on local gradients (finite diff)
            # approximate dm/dy at segment, dm/dx using neighbor a1 if available
            y0,m0,_=arr[i]; y1,m1,_=arr[i+1]
            dmdy = (m1-m0)/(y1-y0) if (y1!=y0) else 0.0
            # dm/dx using nearest neighbor v1 step
            dmdx=0.0
            if len(a1_grid)>1:
                # choose next a1 if exists
                j=a1_grid.index(v1)
                if j+1 < len(a1_grid):
                    v1b=a1_grid[j+1]
                    pb0=idx.get((float(v1b), float(y0)))
                    pb1=idx.get((float(v1b), float(y1)))
                    if pb0 and pb1:
                        mb0=_margin(pb0); mb1=_margin(pb1)
                        dm_here=(m1+m0)/2.0
                        dm_next=(mb1+mb0)/2.0
                        dx = v1b - v1
                        if dx!=0 and math.isfinite(dm_next) and math.isfinite(dm_here):
                            dmdx = (dm_next-dm_here)/dx
            # normal vector for boundary: grad(m)
            norm={"%s"%a1_name: float(dmdx), "%s"%a2_name: float(dmdy)}
            # condition number placeholder (future): use |grad|
            cond=float(abs(dmdx)+abs(dmdy))
            samples.append({
                "u": {a1_name: float(v1)},
                "x_boundary": {a2_name: float(ystar)},
                "local": {
                    "dominant_constraint": dom,
                    "normal_vector": norm,
                    "condition_number": cond,
                },
                "confidence": {
                    "band": {f"{a2_name}_pm": float(half_band)},
                    "quality": "medium" if half_band>0 else "low",
                    "reason": "grid_interpolation",
                },
            })

    boundary={
        "kind":"shams_feasibility_boundary",
        "version":"v157",
        "issued_utc": _utc(),
        "shams_version": str((Path(__file__).resolve().parents[1]/"VERSION").read_text(encoding="utf-8").strip().splitlines()[0]),
        "study_id": str(field.get("study_id") or ""),
        "provenance": {
            "generator":"ui",
            "method": method,
        },
        "assumptions": field.get("assumptions") or {},
        "integrity": {"object_sha256": ""},
        "payload": {
            "boundary_definition": {
                "status_transition": [transition[0], transition[1]],
                "criterion": "min_constraint_margin == 0",
            },
            "parametrization": {
                "free_axes": [a1_name],
                "solved_axes": [a2_name],
                "fixed": (field.get("payload") or {}).get("domain", {}).get("fixed") or [],
            },
            "boundary": {"samples": samples},
            "traceability": {
                "source_field_ref": {"kind":"shams_feasibility_field","sha256": str((field.get("integrity") or {}).get("object_sha256") or "")},
                "method": method,
            },
        },
    }
    tmp=copy.deepcopy(boundary)
    tmp["integrity"]={"object_sha256": ""}
    boundary["integrity"]["object_sha256"]=_sha_obj(tmp)
    return boundary
