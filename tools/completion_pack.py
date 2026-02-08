from __future__ import annotations
"""Completion Pack (v163)

Turns feasibility completion outputs into an actionable, publishable "recipe".

Inputs accepted (any subset):
- v159: shams_feasibility_completion_evidence
- v161: shams_completion_frontier
- v162: shams_directed_local_search

Output:
- kind: shams_completion_pack, version: v163
- includes a selected recommended witness (priority: v162 feasible final > v161 minimal-change feasible > v159 best_witness)
- includes next-knobs ranking derived from:
    - v159 bottleneck dominance ranking (if present)
    - v158 constraint dominance summary (optional; not required)
- includes bounds recommendations: tighten/shift bounds around successful witness (heuristic)

Safety:
- Purely downstream reporting. No physics or solver logic changes.
"""

from typing import Any, Dict, List, Optional, Tuple
import json, time, hashlib, copy, math

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _canon_json(o: Any) -> bytes:
    return json.dumps(o, indent=2, sort_keys=True, default=str).encode("utf-8")

def _sha_bytes(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def _sha_obj(o: Any) -> str:
    return _sha_bytes(_canon_json(o))

def _pick_witness(v159: Optional[Dict[str,Any]], v161: Optional[Dict[str,Any]], v162: Optional[Dict[str,Any]]) -> Tuple[Optional[Dict[str,Any]], str]:
    # Returns (witness_inputs, provenance)
    # Preferred order: v162 feasible final -> v161 minimal-change feasible -> v159 best_witness
    if isinstance(v162, dict):
        res=((v162.get("payload") or {}).get("result") or {})
        fin=(res.get("final") or {})
        if (fin.get("status")=="feasible") and isinstance(((v162.get("payload") or {}).get("query") or {}).get("baseline"), dict):
            base=((v162.get("payload") or {}).get("query") or {}).get("baseline") or {}
            x_dec=fin.get("x_decision") or {}
            if isinstance(x_dec, dict):
                w=dict(base); w.update(x_dec)
                return (w, "v162.final.feasible")
    if isinstance(v161, dict):
        res=((v161.get("payload") or {}).get("result") or {})
        mc=res.get("minimal_change_feasible")
        if isinstance(mc, dict) and mc.get("status")=="feasible":
            base=((v161.get("payload") or {}).get("query") or {}).get("baseline") or {}
            x_dec=mc.get("x_decision") or {}
            if isinstance(base, dict) and isinstance(x_dec, dict):
                w=dict(base); w.update(x_dec)
                return (w, "v161.minimal_change_feasible")
    if isinstance(v159, dict):
        res=((v159.get("payload") or {}).get("result") or {})
        bw=res.get("best_witness") or {}
        if isinstance(bw, dict) and isinstance(bw.get("x"), dict):
            return (bw.get("x"), "v159.best_witness")
    return (None, "none")

def _rank_knobs(v159: Optional[Dict[str,Any]]) -> List[Dict[str,Any]]:
    # Use v159 bottleneck dominance ranking when available
    ranked=[]
    if not isinstance(v159, dict):
        return ranked
    bot=(((v159.get("payload") or {}).get("result") or {}).get("bottleneck") or {})
    dom=(bot.get("dominance_ranked") or [])
    if isinstance(dom, list):
        for r in dom[:15]:
            if not isinstance(r, dict):
                continue
            nm=str(r.get("name") or "")
            if not nm:
                continue
            ranked.append({
                "constraint": nm,
                "signal": "dominance_frequency",
                "count": int(r.get("count") or 0),
                "near_count": int(r.get("near_count") or 0),
                "recommendation": "Adjust variables that affect this constraint first; use v162 directed search with bounds.",
            })
    return ranked

def _bounds_recommendation(vars_spec: Optional[List[Dict[str,Any]]], witness: Optional[Dict[str,Any]], tighten: float=0.25) -> List[Dict[str,Any]]:
    # Heuristic: for each decision variable bounds [lo,hi], propose new bounds centered at witness with +/- tighten*(hi-lo)
    out=[]
    if not (isinstance(vars_spec, list) and isinstance(witness, dict)):
        return out
    for v in vars_spec:
        if not isinstance(v, dict):
            continue
        nm=str(v.get("name") or "")
        b=v.get("bounds")
        if not (nm and isinstance(b,(list,tuple)) and len(b)==2):
            continue
        try:
            lo=float(b[0]); hi=float(b[1])
        except Exception:
            continue
        if hi<lo: lo,hi=hi,lo
        span=hi-lo
        if span<=0:
            continue
        try:
            w=float(witness.get(nm))
        except Exception:
            continue
        delta=tighten*span
        nlo=max(lo, w-delta)
        nhi=min(hi, w+delta)
        out.append({
            "name": nm,
            "old_bounds": [lo,hi],
            "new_bounds": [float(nlo), float(nhi)],
            "center": float(w),
            "note": f"Heuristic tighten={tighten} of span around witness.",
        })
    return out[:50]

def build_completion_pack(
    *,
    v159: Optional[Dict[str,Any]] = None,
    v161: Optional[Dict[str,Any]] = None,
    v162: Optional[Dict[str,Any]] = None,
    policy: Optional[Dict[str,Any]] = None,
) -> Dict[str,Any]:
    policy = policy if isinstance(policy, dict) else {}
    witness, wprov = _pick_witness(v159, v161, v162)
    knobs = _rank_knobs(v159)
    vars_spec=None
    if isinstance(v161, dict):
        vars_spec=((v161.get("payload") or {}).get("query") or {}).get("decision_vars")
    elif isinstance(v162, dict):
        vars_spec=((v162.get("payload") or {}).get("query") or {}).get("decision_vars")
    bounds_rec=_bounds_recommendation(vars_spec, witness, tighten=float(policy.get("tighten",0.25)))

    refs=[]
    def add_ref(obj, tag):
        if isinstance(obj, dict):
            refs.append({"tag":tag, "kind": obj.get("kind"), "version": obj.get("version"), "sha256": ((obj.get("integrity") or {}).get("object_sha256") or "")})
    add_ref(v159,"v159")
    add_ref(v161,"v161")
    add_ref(v162,"v162")

    out={
        "kind":"shams_completion_pack",
        "version":"v163",
        "issued_utc": _utc(),
        "provenance": {"generator": policy.get("generator","ui"), "refs": refs},
        "integrity": {"object_sha256": ""},
        "payload": {
            "recommended_witness": witness,
            "witness_provenance": wprov,
            "next_knobs": knobs,
            "bounds_recommendations": bounds_rec,
            "notes": [
                "Witness priority: v162 feasible final > v161 minimal-change feasible > v159 best witness.",
                "Bounds recommendations are heuristic tighten-around-witness; always validate with v156/v162 before publication.",
            ],
        },
    }
    tmp=copy.deepcopy(out); tmp["integrity"]={"object_sha256": ""}
    out["integrity"]["object_sha256"]=_sha_obj(tmp)
    return out

def render_completion_pack_markdown(pack: Dict[str,Any]) -> str:
    p=(pack.get("payload") or {}) if isinstance(pack, dict) else {}
    w=p.get("recommended_witness") or {}
    knobs=p.get("next_knobs") or []
    bnds=p.get("bounds_recommendations") or []
    lines=[]
    lines.append("# SHAMS Completion Pack (v163)")
    lines.append("")
    lines.append(f"- Issued: {pack.get('issued_utc','')}")
    lines.append(f"- Witness provenance: {p.get('witness_provenance','')}")
    lines.append("")
    lines.append("## Recommended witness (inputs)")
    lines.append("```json")
    lines.append(json.dumps(w, indent=2, sort_keys=True, default=str))
    lines.append("```")
    lines.append("")
    lines.append("## Next knobs (ranked)")
    for k in knobs[:12]:
        if not isinstance(k, dict): 
            continue
        lines.append(f"- **{k.get('constraint','')}** (count={k.get('count',0)}, near={k.get('near_count',0)}) — {k.get('recommendation','')}")
    lines.append("")
    lines.append("## Bounds recommendations")
    for b in bnds[:20]:
        if not isinstance(b, dict): 
            continue
        lines.append(f"- `{b.get('name','')}`: {b.get('old_bounds')} → {b.get('new_bounds')} (center={b.get('center')})")
    lines.append("")
    return "\n".join(lines)
