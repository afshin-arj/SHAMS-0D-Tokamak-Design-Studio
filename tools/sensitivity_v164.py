from __future__ import annotations
"""Sensitivity + Bottleneck Attribution (v164)

Goal:
- Around a witness (baseline or recommended witness), quantify local leverage of decision variables.
- Finite difference sensitivities of min_constraint_margin w.r.t. each variable.
- Track dominant constraint changes and per-constraint margin deltas when available.

Safety:
- Downstream-only. Uses existing evaluator (tools.study_matrix.evaluate_point_inputs).
- No physics changes, no solver logic changes.
- Strict evaluation budget: 1 baseline + 2 * N variables (central differences).

Artifact:
kind: shams_sensitivity_report, version: v164
"""

from typing import Any, Dict, List, Tuple, Optional
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

def _constraints_map(payload: Dict[str, Any]) -> Dict[str, float]:
    cons=payload.get("constraints") or []
    out={}
    if isinstance(cons, list):
        for c in cons:
            if not isinstance(c, dict): 
                continue
            nm=str(c.get("name") or "")
            try:
                m=float(c.get("margin"))
            except Exception:
                continue
            if nm:
                out[nm]=m
    return out

def _min_margin(payload: Dict[str, Any]) -> Tuple[float,str,Dict[str,float]]:
    cmap=_constraints_map(payload)
    if not cmap:
        return (float("nan"), "", {})
    dom=min(cmap.items(), key=lambda kv: kv[1])
    return (float(dom[1]), str(dom[0]), cmap)

def _status(m: float, eps: float=1e-6) -> str:
    if not math.isfinite(m):
        return "unknown"
    if m >= eps:
        return "feasible"
    if m <= -eps:
        return "infeasible"
    return "marginal"

def _eval(x: Dict[str, Any], assumption_set: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return evaluate_point_inputs(inputs_dict=x, solver_meta={"label":"v164_sensitivity", "assumption_set": assumption_set})
    except TypeError:
        try:
            return evaluate_point_inputs(inputs_dict=x)
        except TypeError:
            return evaluate_point_inputs(x)

def build_sensitivity_report(
    *,
    witness: Dict[str, Any],
    variables: List[Dict[str, Any]],
    assumption_set: Optional[Dict[str, Any]] = None,
    rel_step: float = 0.01,
    abs_step_min: float = 1e-6,
    margin_eps: float = 1e-6,
    policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(witness, dict) or not witness:
        raise ValueError("witness must be a non-empty dict")
    if not isinstance(variables, list) or not variables:
        raise ValueError("variables must be a non-empty list of {name,bounds}")

    assumption_set = assumption_set if isinstance(assumption_set, dict) else {}
    policy = policy if isinstance(policy, dict) else {}

    # parse vars
    vars=[]
    for v in variables:
        if not isinstance(v, dict):
            continue
        nm=str(v.get("name") or "")
        b=v.get("bounds")
        if not (nm and isinstance(b,(list,tuple)) and len(b)==2):
            continue
        lo=float(b[0]); hi=float(b[1])
        if hi<lo: lo,hi=hi,lo
        vars.append((nm, lo, hi))
    if not vars:
        raise ValueError("No valid variables parsed")

    # baseline
    p0=_eval(witness, assumption_set)
    if not (isinstance(p0, dict) and p0.get("kind")=="shams_run_artifact"):
        raise RuntimeError("Baseline evaluation did not return shams_run_artifact")
    m0, dom0, cmap0 = _min_margin(p0)
    st0=_status(m0, float(margin_eps))

    rows=[]
    for nm,lo,hi in vars:
        span=(hi-lo) if (hi-lo)!=0 else 1.0
        step=max(float(abs_step_min), float(rel_step)*span)
        # ensure within bounds around witness
        try:
            x0=float(witness.get(nm))
        except Exception:
            x0=(lo+hi)/2.0
        xplus=min(hi, x0+step)
        xminus=max(lo, x0-step)
        if xplus==x0 and xminus==x0:
            continue

        wp=dict(witness); wm=dict(witness)
        wp[nm]=xplus; wm[nm]=xminus
        pp=_eval(wp, assumption_set)
        pm=_eval(wm, assumption_set)
        if not (isinstance(pp, dict) and pp.get("kind")=="shams_run_artifact" and isinstance(pm, dict) and pm.get("kind")=="shams_run_artifact"):
            continue
        mp, domp, cmapp = _min_margin(pp)
        mm, domm, cmapm = _min_margin(pm)

        # finite diffs on min margin
        denom=(xplus-xminus) if (xplus-xminus)!=0 else step
        dmdx = (mp - mm)/float(denom) if (math.isfinite(mp) and math.isfinite(mm)) else None

        # per-constraint delta at +/- (top few changing)
        delta_cons=[]
        keys=set(cmap0.keys()) | set(cmapp.keys()) | set(cmapm.keys())
        for ck in keys:
            b=float(cmap0.get(ck, float("nan")))
            ap=float(cmapp.get(ck, float("nan")))
            am=float(cmapm.get(ck, float("nan")))
            # central change magnitude relative to baseline
            if math.isfinite(b) and math.isfinite(ap) and math.isfinite(am):
                mag=abs((ap-am)/float(denom))
            else:
                mag=float("nan")
            if math.isfinite(mag) and mag>0:
                delta_cons.append({"constraint": ck, "dmargin_dx": float(mag)})
        delta_cons.sort(key=lambda r: r["dmargin_dx"], reverse=True)

        rows.append({
            "name": nm,
            "bounds": [lo,hi],
            "x0": float(x0),
            "step": float(step),
            "x_minus": float(xminus),
            "x_plus": float(xplus),
            "min_margin_minus": float(mm) if math.isfinite(mm) else None,
            "min_margin_plus": float(mp) if math.isfinite(mp) else None,
            "d_min_margin_dx": float(dmdx) if dmdx is not None and math.isfinite(dmdx) else None,
            "dominant_constraint_base": dom0,
            "dominant_constraint_minus": domm,
            "dominant_constraint_plus": domp,
            "top_constraint_sensitivities": delta_cons[:8],
        })

    # rank knobs by absolute d(min_margin)/dx
    ranked=[r for r in rows if isinstance(r.get("d_min_margin_dx"), (int,float)) and math.isfinite(float(r.get("d_min_margin_dx")))]
    ranked.sort(key=lambda r: abs(float(r["d_min_margin_dx"])), reverse=True)

    out={
        "kind":"shams_sensitivity_report",
        "version":"v164",
        "issued_utc": _utc(),
        "provenance": {
            "generator": policy.get("generator","ui"),
            "method": "central_difference",
            "rel_step": float(rel_step),
            "abs_step_min": float(abs_step_min),
        },
        "assumptions": {"assumption_set": assumption_set},
        "integrity": {"object_sha256": ""},
        "payload": {
            "baseline": {
                "status": st0,
                "min_margin": float(m0) if math.isfinite(m0) else None,
                "dominant_constraint": dom0,
                "witness": witness,
            },
            "variables": [{"name":nm, "bounds":[lo,hi]} for nm,lo,hi in vars],
            "rows": rows,
            "ranked": [{"name":r["name"], "d_min_margin_dx": r.get("d_min_margin_dx"), "step": r.get("step")} for r in ranked[:25]],
        },
    }
    tmp=copy.deepcopy(out); tmp["integrity"]={"object_sha256": ""}
    out["integrity"]["object_sha256"]=_sha_obj(tmp)
    return out

def render_sensitivity_markdown(rep: Dict[str,Any]) -> str:
    p=(rep.get("payload") or {}) if isinstance(rep, dict) else {}
    base=p.get("baseline") or {}
    ranked=p.get("ranked") or []
    lines=[]
    lines.append("# SHAMS Sensitivity Report (v164)")
    lines.append("")
    lines.append(f"- Issued: {rep.get('issued_utc','')}")
    lines.append(f"- Baseline status: {base.get('status','')} | min_margin: {base.get('min_margin')} | dominant: {base.get('dominant_constraint','')}")
    lines.append("")
    lines.append("## Ranked leverage variables (by |d(min_margin)/dx|)")
    for r in ranked[:15]:
        if not isinstance(r, dict): 
            continue
        lines.append(f"- `{r.get('name','')}`: d(min_margin)/dx = {r.get('d_min_margin_dx')} (step={r.get('step')})")
    lines.append("")
    return "\n".join(lines)
