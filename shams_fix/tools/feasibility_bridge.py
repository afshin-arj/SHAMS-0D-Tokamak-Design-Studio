from __future__ import annotations
"""Feasibility Bridge (v146)

Purpose:
Given two points (A and B) that are feasible (or near-feasible), attempt to find an
audit-friendly continuation path between them in a low-dimensional subspace.

This does NOT change physics/solver logic. It repeatedly calls the existing point evaluator
at intermediate parameter values and records feasibility margins and dominant constraints.

Outputs:
- shams_feasibility_bridge_report (v146): full step log
- shams_feasibility_bridge_certificate (v146): concise citable summary, with hashes

Method (safe):
- linear interpolation in selected vars across N steps
- optional adaptive refinement: if a step is infeasible, bisect that segment up to max_depth
- declares "bridge exists" if a continuous sequence of feasible steps connects endpoints

This is a *topology witness* tool. It does not guarantee global connectivity; it provides
evidence under a declared protocol.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional
import time, uuid, json, hashlib

from tools.study_matrix import evaluate_point_inputs

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha(x: Any) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, default=str).encode("utf-8")).hexdigest()

def _extract_constraints(art: Dict[str, Any]) -> Dict[str, Any]:
    cs = art.get("constraints_summary", {}) if isinstance(art.get("constraints_summary"), dict) else {}
    cons = cs.get("constraints")
    if isinstance(cons, dict):
        return cons
    cons2 = art.get("constraints")
    return cons2 if isinstance(cons2, dict) else {}

def _constraint_pass_fail(cons: Dict[str, Any]) -> Tuple[Dict[str,bool], Dict[str, float]]:
    pmap={}
    mmap={}
    for k,v in (cons or {}).items():
        if not isinstance(v, dict):
            continue
        is_hard=True
        if "kind" in v and isinstance(v["kind"], str) and "soft" in v["kind"].lower():
            is_hard=False
        if "hard" in v and isinstance(v["hard"], bool):
            is_hard=bool(v["hard"])
        if not is_hard:
            continue
        mf=v.get("margin_frac")
        try:
            mf=float(mf) if mf is not None else None
        except Exception:
            mf=None
        mmap[k]=mf
        if "pass" in v and isinstance(v["pass"], bool):
            pmap[k]=bool(v["pass"])
        elif mf is not None:
            pmap[k]=(mf>=0.0)
        else:
            pmap[k]=False
    return pmap,mmap

def _worst_hard(cons: Dict[str, Any]) -> Tuple[Optional[str], Optional[float]]:
    _,mmap=_constraint_pass_fail(cons)
    worst_name=None
    worst_m=None
    for k,m in mmap.items():
        if m is None: 
            continue
        if worst_m is None or m < worst_m:
            worst_m=m
            worst_name=k
    return worst_name, worst_m

def _eval(inputs: Dict[str, Any], label: str) -> Dict[str, Any]:
    art = evaluate_point_inputs(inputs_dict=inputs, solver_meta={"label": label})
    cs = art.get("constraints_summary", {}) if isinstance(art.get("constraints_summary"), dict) else {}
    cons = _extract_constraints(art)
    feasible = cs.get("feasible")
    if feasible is None:
        pmap,_=_constraint_pass_fail(cons)
        feasible = all(pmap.values()) if pmap else False
    worst_name, worst_m = _worst_hard(cons)
    return {
        "feasible": bool(feasible is True),
        "worst_hard": cs.get("worst_hard") or worst_name,
        "worst_hard_margin_frac": cs.get("worst_hard_margin_frac") if cs.get("worst_hard_margin_frac") is not None else worst_m,
        "artifact": art,
    }

@dataclass
class BridgeConfig:
    inputs_A: Dict[str, Any]
    inputs_B: Dict[str, Any]
    vars: List[str]
    n_steps: int = 21
    max_bisect_depth: int = 6
    require_endpoints_feasible: bool = True
    label: str = "bridge_v146"

def _lerp(a: float, b: float, t: float) -> float:
    return (1.0-t)*a + t*b

def _interp_inputs(A: Dict[str, Any], B: Dict[str, Any], vars: List[str], t: float) -> Dict[str, Any]:
    out = dict(A)
    for v in vars:
        av=A.get(v); bv=B.get(v)
        out[v] = _lerp(float(av), float(bv), float(t))
    return out

def _segment_check(cfg: BridgeConfig, t0: float, t1: float, depth: int, log: List[Dict[str, Any]]):
    # midpoint check with bisection if needed
    tm = 0.5*(t0+t1)
    inp = _interp_inputs(cfg.inputs_A, cfg.inputs_B, cfg.vars, tm)
    r = _eval(inp, cfg.label)
    log.append({"t": tm, "inputs": {v: inp.get(v) for v in cfg.vars}, "feasible": r["feasible"], "worst_hard": r["worst_hard"], "margin": r["worst_hard_margin_frac"]})
    if r["feasible"]:
        return
    if depth >= cfg.max_bisect_depth:
        return
    _segment_check(cfg, t0, tm, depth+1, log)
    _segment_check(cfg, tm, t1, depth+1, log)

def run_bridge(cfg: BridgeConfig) -> Dict[str, Any]:
    created=_utc()
    # validate vars exist numeric
    for v in cfg.vars:
        if v not in cfg.inputs_A or v not in cfg.inputs_B:
            raise ValueError(f"Missing var {v} in A/B")
        float(cfg.inputs_A[v]); float(cfg.inputs_B[v])

    # endpoints
    endA=_eval(_interp_inputs(cfg.inputs_A,cfg.inputs_B,cfg.vars,0.0), cfg.label+"_A")
    endB=_eval(_interp_inputs(cfg.inputs_A,cfg.inputs_B,cfg.vars,1.0), cfg.label+"_B")
    if cfg.require_endpoints_feasible and (not endA["feasible"] or not endB["feasible"]):
        raise ValueError("Endpoints not feasible under require_endpoints_feasible")

    log=[]
    # coarse grid
    n=max(3,int(cfg.n_steps))
    for i in range(n):
        t=i/(n-1)
        if t in (0.0,1.0):
            r = endA if t==0.0 else endB
            log.append({"t": t, "inputs": {v: _interp_inputs(cfg.inputs_A,cfg.inputs_B,cfg.vars,t).get(v) for v in cfg.vars},
                        "feasible": r["feasible"], "worst_hard": r["worst_hard"], "margin": r["worst_hard_margin_frac"]})
        else:
            inp=_interp_inputs(cfg.inputs_A,cfg.inputs_B,cfg.vars,t)
            r=_eval(inp, cfg.label)
            log.append({"t": t, "inputs": {v: inp.get(v) for v in cfg.vars}, "feasible": r["feasible"], "worst_hard": r["worst_hard"], "margin": r["worst_hard_margin_frac"]})

    # refine any infeasible segments by bisection witnesses
    # sort by t
    log_sorted=sorted(log, key=lambda x: x["t"])
    refine=[]
    for i in range(len(log_sorted)-1):
        a=log_sorted[i]; b=log_sorted[i+1]
        if a["feasible"] and b["feasible"]:
            continue
        # if segment crosses infeasible, add refinement points
        _segment_check(cfg, float(a["t"]), float(b["t"]), 0, refine)

    full = sorted(log_sorted + refine, key=lambda x: x["t"])
    # Determine if a feasible chain exists: if all sampled points feasible => witness
    bridge_exists = all(p.get("feasible") is True for p in full)

    report={
        "kind":"shams_feasibility_bridge_report",
        "version":"v146",
        "created_utc": created,
        "config": {
            "vars": list(cfg.vars),
            "n_steps": int(cfg.n_steps),
            "max_bisect_depth": int(cfg.max_bisect_depth),
            "require_endpoints_feasible": bool(cfg.require_endpoints_feasible),
        },
        "endpoints": {
            "A": {"feasible": endA["feasible"], "worst_hard": endA["worst_hard"], "margin": endA["worst_hard_margin_frac"]},
            "B": {"feasible": endB["feasible"], "worst_hard": endB["worst_hard"], "margin": endB["worst_hard_margin_frac"]},
        },
        "bridge_exists": bool(bridge_exists),
        "path": full,
    }
    return report

def bridge_certificate(report: Dict[str, Any], baseline_inputs_sha256: str = "") -> Dict[str, Any]:
    if not (isinstance(report, dict) and report.get("kind") == "shams_feasibility_bridge_report"):
        raise ValueError("report kind mismatch")
    created=_utc()
    path=report.get("path") or []
    worst=None
    for p in path:
        m=p.get("margin")
        try:
            m=float(m) if m is not None else None
        except Exception:
            m=None
        if m is None:
            continue
        if worst is None or m < worst:
            worst=m
    cert={
        "kind":"shams_feasibility_bridge_certificate",
        "version":"v146",
        "certificate_id": str(uuid.uuid4()),
        "issued_utc": created,
        "references": {
            "baseline_inputs_sha256": baseline_inputs_sha256 or None,
            "bridge_report_sha256": _sha(report),
        },
        "summary": {
            "bridge_exists": bool(report.get("bridge_exists")),
            "vars": (report.get("config") or {}).get("vars"),
            "n_path_points": len(path),
            "worst_seen_margin_frac": worst,
        },
        "hashes": {
            "certificate_sha256": "",
        }
    }
    cert["hashes"]["certificate_sha256"]=_sha(cert)
    return cert
