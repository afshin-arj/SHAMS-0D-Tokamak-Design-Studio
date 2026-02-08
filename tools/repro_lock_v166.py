from __future__ import annotations
"""Reproducibility Lock + Replay Checker (v166)

Goal:
- Make design studies reproducible under constrained environments by freezing the *exact* run input + assumptions + solver meta,
  and verifying that a rerun matches within tolerances.
- Produces a lockfile with stable hash + a replay report.

Inputs:
- run_artifact: shams_run_artifact
- optional: lock_overrides {tolerances, compare_fields, notes}

Outputs:
- lock: kind shams_repro_lock, version v166
- replay: kind shams_replay_report, version v166

Safety:
- Evaluation-only. Uses existing evaluator (tools.study_matrix.evaluate_point_inputs).
- No physics/solver changes; it just calls the current evaluator and compares outputs.
"""

from typing import Any, Dict, Optional, List, Tuple
import json, time, hashlib, copy, math
from pathlib import Path

from tools.study_matrix import evaluate_point_inputs

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _canon_json(o: Any) -> bytes:
    return json.dumps(o, indent=2, sort_keys=True, default=str).encode("utf-8")

def _sha_bytes(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def _sha_obj(o: Any) -> str:
    return _sha_bytes(_canon_json(o))

def _num(v) -> Optional[float]:
    try:
        return float(v)
    except Exception:
        return None

def _constraints_map(run_artifact: Dict[str,Any]) -> Dict[str, float]:
    cons=run_artifact.get("constraints") or []
    out={}
    if isinstance(cons, list):
        for c in cons:
            if not isinstance(c, dict): 
                continue
            nm=str(c.get("name") or "")
            mv=_num(c.get("margin"))
            if nm and (mv is not None) and math.isfinite(mv):
                out[nm]=float(mv)
    return out

def build_repro_lock(
    *,
    run_artifact: Dict[str, Any],
    lock_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not (isinstance(run_artifact, dict) and run_artifact.get("kind")=="shams_run_artifact"):
        raise ValueError("run_artifact must be a shams_run_artifact dict")

    lock_overrides = lock_overrides if isinstance(lock_overrides, dict) else {}
    inputs = run_artifact.get("inputs") or run_artifact.get("_inputs") or {}
    assumptions = run_artifact.get("assumptions") or {}
    solver = run_artifact.get("solver") or run_artifact.get("solver_meta") or {}
    mode = run_artifact.get("mode") or ""

    tolerances = lock_overrides.get("tolerances") or {
        "min_margin_abs": 1e-8,
        "constraint_margin_abs": 1e-6,
        "metric_rel": 1e-6,
        "metric_abs": 1e-9,
    }
    compare_fields = lock_overrides.get("compare_fields") or {
        "metrics": ["*"],  # wildcard; implemented by comparing numeric leafs where names match
        "constraints": ["margin"],
        "min_margin": True,
        "dominant_constraint": True,
    }

    payload = {
        "lock": {
            "issued_utc": _utc(),
            "shams_version": str(run_artifact.get("shams_version") or ""),
            "mode": str(mode),
            "notes": lock_overrides.get("notes") or [],
        },
        "frozen": {
            "inputs": inputs,
            "assumptions": assumptions,
            "solver_meta": solver,
        },
        "expected": {
            "metrics": run_artifact.get("metrics") or {},
            "constraints": run_artifact.get("constraints") or [],
            "min_margin": _num(run_artifact.get("min_margin")),
            "dominant_constraint": str(run_artifact.get("dominant_constraint") or ""),
        },
        "comparison": {
            "tolerances": tolerances,
            "compare_fields": compare_fields,
        },
        "integrity": {"lock_sha256": ""},
    }

    tmp=copy.deepcopy(payload)
    tmp["integrity"]["lock_sha256"] = ""
    payload["integrity"]["lock_sha256"] = _sha_obj(tmp)

    out={
        "kind":"shams_repro_lock",
        "version":"v166",
        "issued_utc": _utc(),
        "integrity": {"object_sha256": ""},
        "payload": payload,
    }
    tmp2=copy.deepcopy(out); tmp2["integrity"]={"object_sha256": ""}
    out["integrity"]["object_sha256"]=_sha_obj(tmp2)
    return out

def _flatten_numeric(d: Any, prefix: str="") -> Dict[str,float]:
    out={}
    if isinstance(d, dict):
        for k,v in d.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            out.update(_flatten_numeric(v, p))
    elif isinstance(d, list):
        for i,v in enumerate(d):
            p=f"{prefix}[{i}]"
            out.update(_flatten_numeric(v, p))
    else:
        nv=_num(d)
        if nv is not None and math.isfinite(nv):
            out[prefix]=float(nv)
    return out

def _compare_numbers(a: float, b: float, abs_tol: float, rel_tol: float) -> bool:
    if not (math.isfinite(a) and math.isfinite(b)):
        return False
    if abs(a-b) <= abs_tol:
        return True
    denom=max(abs(a), abs(b), 1e-12)
    return abs(a-b)/denom <= rel_tol

def replay_check(
    *,
    lock: Dict[str, Any],
    assumption_set_override: Optional[Dict[str, Any]] = None,
    policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not (isinstance(lock, dict) and lock.get("kind")=="shams_repro_lock"):
        raise ValueError("lock must be a shams_repro_lock dict")
    policy = policy if isinstance(policy, dict) else {}

    p=(lock.get("payload") or {})
    frozen=(p.get("frozen") or {})
    inputs=frozen.get("inputs") or {}
    assumptions=frozen.get("assumptions") or {}
    if isinstance(assumption_set_override, dict):
        # allow override (e.g. to adapt to slightly different environment)
        assumptions = copy.deepcopy(assumptions)
        assumptions.update(assumption_set_override)

    tol=((p.get("comparison") or {}).get("tolerances") or {})
    abs_mm=float(tol.get("min_margin_abs", 1e-8))
    abs_cm=float(tol.get("constraint_margin_abs", 1e-6))
    rel_m=float(tol.get("metric_rel", 1e-6))
    abs_m=float(tol.get("metric_abs", 1e-9))

    expected=(p.get("expected") or {})
    exp_mm=_num(expected.get("min_margin"))
    exp_dom=str(expected.get("dominant_constraint") or "")
    exp_metrics=expected.get("metrics") or {}
    exp_cons_map=_constraints_map({"constraints": expected.get("constraints") or []})
    exp_metrics_flat=_flatten_numeric(exp_metrics)

    # run
    run_payload=None
    try:
        run_payload = evaluate_point_inputs(inputs_dict=inputs, solver_meta={"label":"v166_replay", "assumption_set": assumptions})
    except TypeError:
        try:
            run_payload = evaluate_point_inputs(inputs_dict=inputs)
        except TypeError:
            run_payload = evaluate_point_inputs(inputs)

    ok_payload = isinstance(run_payload, dict) and run_payload.get("kind")=="shams_run_artifact"
    if not ok_payload:
        rep={
            "kind":"shams_replay_report",
            "version":"v166",
            "issued_utc": _utc(),
            "integrity": {"object_sha256": ""},
            "payload": {
                "ok": False,
                "reason": "invalid_payload",
                "lock_sha256": (p.get("integrity") or {}).get("lock_sha256"),
                "run_payload_kind": run_payload.get("kind") if isinstance(run_payload, dict) else str(type(run_payload)),
                "notes": ["Replay did not produce shams_run_artifact."],
            },
        }
        tmp=copy.deepcopy(rep); tmp["integrity"]={"object_sha256": ""}
        rep["integrity"]["object_sha256"]=_sha_obj(tmp)
        return rep

    # compare min margin / dominant
    run_mm=_num(run_payload.get("min_margin"))
    run_dom=str(run_payload.get("dominant_constraint") or "")
    mm_ok = (exp_mm is None or run_mm is None) and (exp_mm==run_mm)
    if (exp_mm is not None) and (run_mm is not None):
        mm_ok = _compare_numbers(float(exp_mm), float(run_mm), abs_tol=abs_mm, rel_tol=0.0)
    dom_ok = (not exp_dom) or (exp_dom==run_dom)

    # compare constraint margins for matching names
    run_cons_map=_constraints_map(run_payload)
    cons_mism=[]
    cons_ok=True
    for nm, em in exp_cons_map.items():
        rm=run_cons_map.get(nm)
        if rm is None:
            cons_ok=False
            cons_mism.append({"constraint": nm, "expected": em, "got": None, "ok": False})
        else:
            ok=_compare_numbers(float(em), float(rm), abs_tol=abs_cm, rel_tol=0.0)
            if not ok:
                cons_ok=False
            cons_mism.append({"constraint": nm, "expected": em, "got": float(rm), "ok": bool(ok)})
    # metric compare by common flattened numeric keys
    run_metrics_flat=_flatten_numeric(run_payload.get("metrics") or {})
    metric_mism=[]
    metric_ok=True
    common=set(exp_metrics_flat.keys()) & set(run_metrics_flat.keys())
    for k in sorted(common)[:600]:
        ea=float(exp_metrics_flat[k])
        ra=float(run_metrics_flat[k])
        ok=_compare_numbers(ea, ra, abs_tol=abs_m, rel_tol=rel_m)
        if not ok:
            metric_ok=False
        metric_mism.append({"key": k, "expected": ea, "got": ra, "ok": bool(ok)})
    # If no common keys, do not fail; just warn.
    if not common:
        metric_ok=True

    ok_all = bool(mm_ok and dom_ok and cons_ok and metric_ok)

    rep={
        "kind":"shams_replay_report",
        "version":"v166",
        "issued_utc": _utc(),
        "integrity": {"object_sha256": ""},
        "payload": {
            "ok": ok_all,
            "lock_sha256": (p.get("integrity") or {}).get("lock_sha256"),
            "checks": {
                "min_margin_ok": bool(mm_ok),
                "dominant_constraint_ok": bool(dom_ok),
                "constraints_ok": bool(cons_ok),
                "metrics_ok": bool(metric_ok),
            },
            "details": {
                "min_margin": {"expected": exp_mm, "got": run_mm, "abs_tol": abs_mm},
                "dominant_constraint": {"expected": exp_dom, "got": run_dom},
                "constraints": {"abs_tol": abs_cm, "mismatches": cons_mism[:200]},
                "metrics": {"abs_tol": abs_m, "rel_tol": rel_m, "common_keys": len(common), "mismatches": [m for m in metric_mism if not m["ok"]][:200]},
            },
            "notes": [
                "Metric comparison uses common numeric keys only; absence of common keys does not fail replay.",
                "Constraint margin comparison matches by constraint name.",
            ],
            "run_artifact": run_payload,
        },
    }
    tmp=copy.deepcopy(rep); tmp["integrity"]={"object_sha256": ""}
    rep["integrity"]["object_sha256"]=_sha_obj(tmp)
    return rep
