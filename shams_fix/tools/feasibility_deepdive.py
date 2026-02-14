from __future__ import annotations
"""Feasibility Deep Dive (v142–v144)

v142 — Feasible Topology Maps
- Sample a bounded design subspace, evaluate feasibility, build a kNN graph among feasible points,
  compute connected components ("islands"), and export artifacts.

v143 — Constraint Interaction Graphs
- From the same evaluated dataset, compute hard-constraint dominance and co-failure matrices,
  and export CSV/PNG.

v144 — Interval Feasibility Certificates
- Certify a hyper-rectangle conservatively by checking corners and random interior probes.
  Outputs a certificate JSON suitable for publication/audit.

All functions are downstream orchestration only: they call evaluate_point_inputs() and analyze outputs.
No physics/solver behavior is changed.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional
from pathlib import Path
from io import BytesIO, StringIO
import json, time, hashlib, zipfile, csv, math, random

from tools.study_matrix import evaluate_point_inputs

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def _safe_float(x):
    try:
        if x is None: return None
        if isinstance(x, bool): return None
        return float(x)
    except Exception:
        return None

def _extract_constraints(art: Dict[str, Any]) -> Dict[str, Any]:
    cs = art.get("constraints_summary", {}) if isinstance(art.get("constraints_summary"), dict) else {}
    # Preferred: cs["constraints"] as mapping name -> details
    cons = cs.get("constraints")
    if isinstance(cons, dict):
        return cons
    # fallback: maybe art["constraints"] already
    cons2 = art.get("constraints")
    return cons2 if isinstance(cons2, dict) else {}

def _constraint_pass_fail(cons: Dict[str, Any]) -> Tuple[Dict[str,bool], Dict[str, float]]:
    """Return (pass_map, margin_frac_map) for hard constraints, best-effort.
    If no explicit 'pass' field exists, infer from margin_frac >= 0.
    """
    pmap={}
    mmap={}
    for k,v in (cons or {}).items():
        if not isinstance(v, dict):
            continue
        # attempt to detect hard constraints only; if tag exists, honor it, else treat as hard
        is_hard = True
        if "kind" in v and isinstance(v["kind"], str):
            # if kind indicates soft, skip
            if "soft" in v["kind"].lower():
                is_hard = False
        if "hard" in v and isinstance(v["hard"], bool):
            is_hard = bool(v["hard"])
        if not is_hard:
            continue
        mf = _safe_float(v.get("margin_frac"))
        if mf is None:
            mf = _safe_float(v.get("margin_fractional"))
        if mf is None:
            mf = _safe_float(v.get("margin_frac_hard"))
        mmap[k] = mf
        if "pass" in v and isinstance(v["pass"], bool):
            pmap[k] = bool(v["pass"])
        elif mf is not None:
            pmap[k] = (mf >= 0.0)
        else:
            # last resort: assume pass unknown -> False
            pmap[k] = False
    return pmap, mmap

def _worst_hard(cons: Dict[str, Any]) -> Tuple[Optional[str], Optional[float]]:
    pmap, mmap = _constraint_pass_fail(cons)
    worst_name=None
    worst_m=None
    for k,m in mmap.items():
        if m is None:
            continue
        if worst_m is None or m < worst_m:
            worst_m = m
            worst_name = k
    return worst_name, worst_m

def _eval_point(inputs: Dict[str, Any], label: str) -> Dict[str, Any]:
    art = evaluate_point_inputs(inputs_dict=inputs, solver_meta={"label": label})
    cs = art.get("constraints_summary", {}) if isinstance(art.get("constraints_summary"), dict) else {}
    cons = _extract_constraints(art)
    feasible = cs.get("feasible")
    if feasible is None:
        # infer from pass_map
        pmap,_ = _constraint_pass_fail(cons)
        feasible = all(pmap.values()) if pmap else False
    worst_name, worst_m = _worst_hard(cons)
    return {
        "inputs": inputs,
        "feasible": bool(feasible is True),
        "worst_hard": cs.get("worst_hard") or worst_name,
        "worst_hard_margin_frac": cs.get("worst_hard_margin_frac") if cs.get("worst_hard_margin_frac") is not None else worst_m,
        "constraints": cons,
        "artifact": art,
    }

# ---------------- v142 data sampling & topology ----------------
@dataclass
class SampleConfig:
    baseline_inputs: Dict[str, Any]
    vars: List[str]
    bounds: Dict[str, Tuple[float, float]]
    n_samples: int = 300
    seed: int = 0
    label: str = "deepdive_v142"

def _sample_inputs(cfg: SampleConfig) -> List[Dict[str, Any]]:
    rng = random.Random(int(cfg.seed))
    pts=[]
    for _ in range(int(cfg.n_samples)):
        inp = dict(cfg.baseline_inputs or {})
        for v in cfg.vars:
            lo,hi = cfg.bounds[v]
            inp[v] = rng.uniform(float(lo), float(hi))
        pts.append(inp)
    return pts

def sample_and_evaluate(cfg: SampleConfig) -> Dict[str, Any]:
    created=_utc()
    pts=_sample_inputs(cfg)
    evals=[]
    for inp in pts:
        r=_eval_point(inp, cfg.label)
        # store only light fields + dominance/fails
        cons=r.get("constraints", {})
        pmap,_=_constraint_pass_fail(cons)
        fails=[k for k,ok in pmap.items() if ok is False]
        evals.append({
            "inputs": {k: r["inputs"].get(k) for k in (cfg.vars or [])},
            "feasible": r["feasible"],
            "worst_hard": r.get("worst_hard"),
            "worst_hard_margin_frac": r.get("worst_hard_margin_frac"),
            "fails": fails,
        })
    return {
        "kind":"shams_deepdive_dataset",
        "version":"v142",
        "created_utc": created,
        "config": {
            "vars": list(cfg.vars),
            "bounds": {k:[float(v[0]), float(v[1])] for k,v in cfg.bounds.items()},
            "n_samples": int(cfg.n_samples),
            "seed": int(cfg.seed),
        },
        "evaluations": evals,
    }

def _euclid(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((ai-bi)**2 for ai,bi in zip(a,b)))

def topology_from_dataset(ds: Dict[str, Any], k: int = 6, eps: float = 0.0) -> Dict[str, Any]:
    """kNN graph among feasible points; eps can limit edges by distance (0 = no limit)."""
    created=_utc()
    vars_ = list((ds.get("config", {}) or {}).get("vars") or [])
    feas=[e for e in (ds.get("evaluations") or []) if isinstance(e, dict) and e.get("feasible") is True]
    X=[]
    for e in feas:
        inp = e.get("inputs", {})
        vec=[_safe_float(inp.get(v)) for v in vars_]
        if any(vv is None for vv in vec):
            continue
        X.append((e, vec))
    n=len(X)
    # adjacency list
    adj=[set() for _ in range(n)]
    for i in range(n):
        di=[]
        for j in range(n):
            if i==j: continue
            d=_euclid(X[i][1], X[j][1])
            if eps and eps>0 and d>eps:
                continue
            di.append((d,j))
        di.sort(key=lambda t: t[0])
        for _,j in di[:max(1,int(k))]:
            adj[i].add(j); adj[j].add(i)
    # components
    comp=[-1]*n
    cid=0
    for i in range(n):
        if comp[i]!=-1: continue
        stack=[i]; comp[i]=cid
        while stack:
            u=stack.pop()
            for v in adj[u]:
                if comp[v]==-1:
                    comp[v]=cid; stack.append(v)
        cid+=1
    # component sizes
    sizes={}
    for c in comp:
        sizes[c]=sizes.get(c,0)+1
    # attach island id to points (aligned to X list)
    points=[]
    for idx,(e,vec) in enumerate(X):
        points.append({"island": comp[idx], "inputs": e.get("inputs", {}), "worst_hard": e.get("worst_hard"), "margin": e.get("worst_hard_margin_frac")})
    islands=[{"island": i, "size": sizes.get(i,0)} for i in sorted(sizes, key=lambda x: sizes[x], reverse=True)]
    return {
        "kind":"shams_feasible_topology",
        "version":"v142",
        "created_utc": created,
        "vars": vars_,
        "n_feasible_points": n,
        "k": int(k),
        "eps": float(eps),
        "islands": islands,
        "points": points,
    }

def bundle_topology(ds: Dict[str, Any], topo: Dict[str, Any]) -> Dict[str, Any]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    created=str(topo.get("created_utc") or _utc())
    ds_b=json.dumps(ds, indent=2, sort_keys=True, default=str).encode("utf-8")
    topo_b=json.dumps(topo, indent=2, sort_keys=True, default=str).encode("utf-8")

    # points csv
    vars_ = topo.get("vars") or []
    buf=StringIO()
    w=csv.writer(buf)
    w.writerow(["island", *vars_, "worst_hard", "margin"])
    for p in (topo.get("points") or []):
        row=[p.get("island")]
        inp=p.get("inputs", {})
        for v in vars_:
            row.append(inp.get(v))
        row += [p.get("worst_hard"), p.get("margin")]
        w.writerow(row)
    pts_csv=buf.getvalue().encode("utf-8")

    # plot: if 2 vars, scatter; else bar of island sizes
    png=b""
    try:
        if len(vars_)==2 and topo.get("points"):
            xs=[]; ys=[]; cs=[]
            for p in topo["points"]:
                xs.append(_safe_float((p.get("inputs") or {}).get(vars_[0])))
                ys.append(_safe_float((p.get("inputs") or {}).get(vars_[1])))
                cs.append(int(p.get("island") or 0))
            fig=plt.figure()
            ax=fig.add_subplot(111)
            ax.scatter(xs, ys, c=cs)
            ax.set_xlabel(vars_[0]); ax.set_ylabel(vars_[1])
            ax.set_title("Feasible islands (v142)")
        else:
            fig=plt.figure()
            ax=fig.add_subplot(111)
            islands=topo.get("islands") or []
            ax.bar(list(range(len(islands))), [i.get("size") for i in islands])
            ax.set_xlabel("island id (ranked)")
            ax.set_ylabel("size")
            ax.set_title("Feasible island sizes (v142)")
        out=BytesIO()
        fig.savefig(out, dpi=180, bbox_inches="tight")
        plt.close(fig)
        png=out.getvalue()
    except Exception:
        png=b""

    files={
        "deepdive_dataset_v142.json": ds_b,
        "feasible_topology_v142.json": topo_b,
        "feasible_points_v142.csv": pts_csv,
    }
    if png:
        files["feasible_topology_v142.png"]=png

    manifest={
        "kind":"shams_feasibility_topology_bundle_manifest",
        "version":"v142",
        "created_utc": created,
        "files": {k: {"sha256": _sha256(v), "bytes": len(v)} for k,v in files.items()},
    }
    files["manifest_v142.json"]=json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")

    zbuf=BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for k,v in files.items():
            z.writestr(k,v)
    return {"kind":"shams_topology_bundle","version":"v142","created_utc": created,"manifest": manifest,"zip_bytes": zbuf.getvalue()}

# ---------------- v143 interactions ----------------
def interactions_from_dataset(ds: Dict[str, Any], top_n: int = 20) -> Dict[str, Any]:
    created=_utc()
    evals=[e for e in (ds.get("evaluations") or []) if isinstance(e, dict)]
    # dominance counts by worst_hard among infeasible and feasible
    dom={}
    fail_counts={}
    for e in evals:
        w=e.get("worst_hard")
        if w:
            dom[w]=dom.get(w,0)+1
        for f in (e.get("fails") or []):
            fail_counts[f]=fail_counts.get(f,0)+1

    # co-failure matrix (top constraints)
    top=sorted(fail_counts.items(), key=lambda kv: kv[1], reverse=True)[:max(1,int(top_n))]
    names=[k for k,_ in top]
    idx={k:i for i,k in enumerate(names)}
    m=[[0 for _ in names] for __ in names]
    for e in evals:
        fs=[f for f in (e.get("fails") or []) if f in idx]
        for i in range(len(fs)):
            for j in range(i, len(fs)):
                a=idx[fs[i]]; b=idx[fs[j]]
                m[a][b]+=1
                if a!=b: m[b][a]+=1

    return {
        "kind":"shams_constraint_interactions",
        "version":"v143",
        "created_utc": created,
        "top_constraints": names,
        "failure_counts": fail_counts,
        "dominance_counts": dom,
        "cofailure_matrix": m,
    }

def bundle_interactions(inter: Dict[str, Any]) -> Dict[str, Any]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    created=str(inter.get("created_utc") or _utc())
    b=json.dumps(inter, indent=2, sort_keys=True, default=str).encode("utf-8")

    # counts csv
    buf=StringIO()
    w=csv.writer(buf)
    w.writerow(["constraint","fail_count"])
    for k,c in sorted((inter.get("failure_counts") or {}).items(), key=lambda kv: kv[1], reverse=True):
        w.writerow([k,c])
    counts_csv=buf.getvalue().encode("utf-8")

    # cofailure csv
    names=inter.get("top_constraints") or []
    mat=inter.get("cofailure_matrix") or []
    buf2=StringIO()
    w=csv.writer(buf2)
    w.writerow([""]+names)
    for i,n in enumerate(names):
        row=[n]+[mat[i][j] if i < len(mat) and j < len(mat[i]) else 0 for j in range(len(names))]
        w.writerow(row)
    co_csv=buf2.getvalue().encode("utf-8")

    png=b""
    try:
        fig=plt.figure(figsize=(max(6, 0.35*len(names)), max(4, 0.35*len(names))))
        ax=fig.add_subplot(111)
        ax.imshow(mat)
        ax.set_xticks(list(range(len(names))))
        ax.set_yticks(list(range(len(names))))
        ax.set_xticklabels(names, rotation=90)
        ax.set_yticklabels(names)
        ax.set_title("Co-failure heatmap (v143)")
        out=BytesIO()
        fig.savefig(out, dpi=180, bbox_inches="tight")
        plt.close(fig)
        png=out.getvalue()
    except Exception:
        png=b""

    files={
        "constraint_interactions_v143.json": b,
        "constraint_failures_v143.csv": counts_csv,
        "constraint_cofailure_v143.csv": co_csv,
    }
    if png:
        files["constraint_cofailure_v143.png"]=png

    manifest={
        "kind":"shams_constraint_interactions_bundle_manifest",
        "version":"v143",
        "created_utc": created,
        "files": {k: {"sha256": _sha256(v), "bytes": len(v)} for k,v in files.items()},
    }
    files["manifest_v143.json"]=json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")

    zbuf=BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for k,v in files.items():
            z.writestr(k,v)
    return {"kind":"shams_interactions_bundle","version":"v143","created_utc": created,"manifest": manifest,"zip_bytes": zbuf.getvalue()}

# ---------------- v144 interval certificate ----------------
@dataclass
class IntervalConfig:
    baseline_inputs: Dict[str, Any]
    bounds: Dict[str, Tuple[float, float]]  # hyper-rectangle
    n_random: int = 60
    seed: int = 0
    label: str = "interval_v144"

def _corners(bounds: Dict[str, Tuple[float, float]]) -> List[Dict[str, float]]:
    keys=list(bounds.keys())
    if len(keys) == 0:
        return []
    corners=[{}]
    for k in keys:
        lo,hi=bounds[k]
        new=[]
        for c in corners:
            c1=dict(c); c1[k]=float(lo)
            c2=dict(c); c2[k]=float(hi)
            new.extend([c1,c2])
        corners=new
    return corners

def interval_certificate(cfg: IntervalConfig) -> Dict[str, Any]:
    created=_utc()
    rng=random.Random(int(cfg.seed))
    base=dict(cfg.baseline_inputs or {})
    # Evaluate corners
    corners=_corners(cfg.bounds)
    corner_results=[]
    ok=True
    worst_seen=None
    worst_margin=None
    dominant_fail={}
    for c in corners:
        inp=dict(base); inp.update(c)
        r=_eval_point(inp, cfg.label+"_corner")
        corner_results.append({"corner": c, "feasible": r["feasible"], "worst_hard": r.get("worst_hard"), "margin": r.get("worst_hard_margin_frac")})
        if r["feasible"] is not True:
            ok=False
            dominant_fail[r.get("worst_hard") or ""] = dominant_fail.get(r.get("worst_hard") or "", 0)+1
        m=_safe_float(r.get("worst_hard_margin_frac"))
        if m is not None and (worst_margin is None or m < worst_margin):
            worst_margin=m; worst_seen=r.get("worst_hard")

    # Random interior probes (if corners pass, still probe for conservatism)
    rand_results=[]
    for _ in range(int(cfg.n_random)):
        c={k: rng.uniform(float(v[0]), float(v[1])) for k,v in cfg.bounds.items()}
        inp=dict(base); inp.update(c)
        r=_eval_point(inp, cfg.label+"_rand")
        rand_results.append({"sample": c, "feasible": r["feasible"], "worst_hard": r.get("worst_hard"), "margin": r.get("worst_hard_margin_frac")})
        if r["feasible"] is not True:
            ok=False
            dominant_fail[r.get("worst_hard") or ""] = dominant_fail.get(r.get("worst_hard") or "", 0)+1
        m=_safe_float(r.get("worst_hard_margin_frac"))
        if m is not None and (worst_margin is None or m < worst_margin):
            worst_margin=m; worst_seen=r.get("worst_hard")

    cert={
        "kind":"shams_interval_feasibility_certificate",
        "version":"v144",
        "issued_utc": created,
        "bounds": {k:[float(v[0]), float(v[1])] for k,v in cfg.bounds.items()},
        "n_corners": len(corners),
        "n_random": int(cfg.n_random),
        "verdict": {
            "interval_certified": bool(ok),
            "worst_seen_constraint": worst_seen,
            "worst_seen_margin_frac": worst_margin,
            "dominant_failures": dominant_fail,
        },
        "evidence": {
            "corners": corner_results[:64],  # cap to keep size bounded
            "random_samples": rand_results[:120],
        },
        "hashes": {},
    }
    cert["hashes"]["certificate_sha256"]=_sha256(json.dumps(cert, sort_keys=True, default=str).encode("utf-8"))
    return cert

def bundle_interval_certificate(cert: Dict[str, Any]) -> Dict[str, Any]:
    created=str(cert.get("issued_utc") or _utc())
    b=json.dumps(cert, indent=2, sort_keys=True, default=str).encode("utf-8")
    files={"interval_certificate_v144.json": b}
    manifest={
        "kind":"shams_interval_certificate_bundle_manifest",
        "version":"v144",
        "created_utc": created,
        "files": {k: {"sha256": _sha256(v), "bytes": len(v)} for k,v in files.items()},
    }
    files["manifest_v144.json"]=json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    zbuf=BytesIO()
    with zipfile.ZipFile(zbuf,"w",zipfile.ZIP_DEFLATED) as z:
        for k,v in files.items():
            z.writestr(k,v)
    return {"kind":"shams_interval_bundle","version":"v144","created_utc": created,"manifest": manifest,"zip_bytes": zbuf.getvalue()}
