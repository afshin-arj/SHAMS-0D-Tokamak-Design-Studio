from __future__ import annotations
"""FC Advanced Toolkit (v134–v138)

Includes:
- v134 FC Atlas generator (figures + dominance tables)
- v136 bounded feasibility repair (auditable)
- v137 feasible set compression (top-K representatives)
- v138 handoff helpers (convert feasible completion -> run_artifact)

All are downstream/orchestration only.
"""

from typing import Any, Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
from io import BytesIO, StringIO
import json, time, hashlib, zipfile, csv, math, random

from tools.study_matrix import evaluate_point_inputs

def _created_utc() -> str:
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

# -----------------------
# v137 compression
# -----------------------
def compress_feasible_set(
    report: Dict[str, Any],
    k: int = 25,
    secondary: str = "Pnet_MW",
) -> Dict[str, Any]:
    evals = list(report.get("evaluations_all") or report.get("evaluations") or [])
    feas = [r for r in evals if r.get("feasible") is True]
    def keyfn(r):
        m = r.get("worst_hard_margin_frac")
        m = -1e9 if m is None else float(m)
        s = r.get(secondary)
        s = -1e9 if s is None else float(s)
        return (m, s)
    feas_sorted = sorted(feas, key=keyfn, reverse=True)
    reps = feas_sorted[:max(1,int(k))]
    out = {
        "kind":"shams_fc_compressed_set",
        "version":"v137",
        "created_utc": _created_utc(),
        "k": int(k),
        "secondary": secondary,
        "n_feasible": len(feas),
        "representatives": reps,
    }
    return out

# -----------------------
# v136 repair
# -----------------------
@dataclass
class RepairConfig:
    bounds: Dict[str, Tuple[float, float]]
    free: List[str]
    max_steps: int = 12
    step_frac: float = 0.15
    seed: int = 0

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def repair_to_feasibility(
    baseline_inputs: Dict[str, Any],
    start_inputs: Dict[str, Any],
    cfg: RepairConfig,
) -> Dict[str, Any]:
    """Bounded stochastic repair: hill-climb on worst_hard_margin_frac.
    Accept steps that increase margin (less negative) and stop if feasible.
    """
    rng = random.Random(int(cfg.seed))
    cur = dict(baseline_inputs or {})
    cur.update(start_inputs or {})
    trace=[]

    def eval_point(inp: Dict[str, Any]):
        art = evaluate_point_inputs(inputs_dict=inp, solver_meta={"label":"fc_repair_v136"})
        cs = art.get("constraints_summary", {}) if isinstance(art.get("constraints_summary"), dict) else {}
        return {
            "feasible": cs.get("feasible"),
            "worst_hard": cs.get("worst_hard"),
            "worst_hard_margin_frac": cs.get("worst_hard_margin_frac"),
            "artifact": art,
        }

    best = eval_point(cur)
    trace.append({"step":0, "inputs": {k: cur.get(k) for k in cfg.free}, **{k: best.get(k) for k in ["feasible","worst_hard","worst_hard_margin_frac"]}})

    for step in range(1, int(cfg.max_steps)+1):
        if best.get("feasible") is True:
            break
        cand = dict(cur)
        # random tweak one free var
        v = cfg.free[rng.randrange(len(cfg.free))]
        lo,hi = cfg.bounds[v]
        x0 = _safe_float(cand.get(v))
        if x0 is None:
            x0 = (lo+hi)/2.0
        span = (hi-lo)
        dx = (rng.uniform(-1,1)) * float(cfg.step_frac) * span
        cand[v] = _clamp(float(x0)+dx, lo, hi)

        res = eval_point(cand)
        mb = _safe_float(best.get("worst_hard_margin_frac"))
        mr = _safe_float(res.get("worst_hard_margin_frac"))
        # accept if improves margin or becomes feasible
        accept = False
        if res.get("feasible") is True and best.get("feasible") is not True:
            accept = True
        elif mr is not None and mb is not None and mr > mb:
            accept = True

        trace.append({"step": step, "tweak": v, "new": cand.get(v), "accepted": accept,
                      **{k: res.get(k) for k in ["feasible","worst_hard","worst_hard_margin_frac"]}})
        if accept:
            cur = cand
            best = res

    out = {
        "kind":"shams_fc_repair_trace",
        "version":"v136",
        "created_utc": _created_utc(),
        "config": {"free": list(cfg.free), "bounds": {k:[float(v[0]),float(v[1])] for k,v in cfg.bounds.items()},
                   "max_steps": int(cfg.max_steps), "step_frac": float(cfg.step_frac), "seed": int(cfg.seed)},
        "final": {k: best.get(k) for k in ["feasible","worst_hard","worst_hard_margin_frac"]},
        "final_inputs": {k: cur.get(k) for k in cfg.free},
        "trace": trace,
        "run_artifact": best.get("artifact"),
    }
    return out

# -----------------------
# v138 handoff
# -----------------------
def completion_to_run_artifact(
    baseline_inputs: Dict[str, Any],
    completion_inputs: Dict[str, Any],
) -> Dict[str, Any]:
    inp = dict(baseline_inputs or {})
    inp.update(completion_inputs or {})
    art = evaluate_point_inputs(inputs_dict=inp, solver_meta={"label":"fc_handoff_v138"})
    return art

# -----------------------
# v134 atlas
# -----------------------
def _dominant_name(r: Dict[str, Any]) -> str:
    w = r.get("worst_hard")
    return "" if w is None else str(w)

def build_fc_atlas_bundle(
    report: Dict[str, Any],
    x_var: str,
    y_var: str,
) -> Dict[str, Any]:
    """Builds a simple 2D atlas using scatter and pivot tables.
    If (x_var,y_var) not present in evaluation inputs, raises.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    created = _created_utc()
    evals = list(report.get("evaluations_all") or report.get("evaluations") or [])
    pts=[]
    for r in evals:
        inp = r.get("inputs", {}) if isinstance(r.get("inputs"), dict) else {}
        x = _safe_float(inp.get(x_var))
        y = _safe_float(inp.get(y_var))
        if x is None or y is None:
            continue
        pts.append((x,y, bool(r.get("feasible") is True), _dominant_name(r), r.get("worst_hard_margin_frac")))

    if not pts:
        raise ValueError("No points for selected axes")

    # scatter feasible/infeasible (no explicit colors)
    xs_f=[p[0] for p in pts if p[2]]
    ys_f=[p[1] for p in pts if p[2]]
    xs_i=[p[0] for p in pts if not p[2]]
    ys_i=[p[1] for p in pts if not p[2]]

    fig1 = plt.figure()
    ax = fig1.add_subplot(111)
    if xs_i:
        ax.scatter(xs_i, ys_i, marker="x")
    if xs_f:
        ax.scatter(xs_f, ys_f, marker="o")
    ax.set_xlabel(x_var)
    ax.set_ylabel(y_var)
    ax.set_title("Feasibility map (v134)")
    buf1=BytesIO()
    fig1.savefig(buf1, dpi=180, bbox_inches="tight")
    plt.close(fig1)

    # dominance frequency table (csv)
    dom_counts={}
    for _,_,_,dom,_ in pts:
        if dom:
            dom_counts[dom]=dom_counts.get(dom,0)+1
    dom_rows=sorted(dom_counts.items(), key=lambda kv: kv[1], reverse=True)
    dom_csv = StringIO()
    w=csv.writer(dom_csv)
    w.writerow(["dominant_constraint","count"])
    for k,c in dom_rows:
        w.writerow([k,c])

    # points table
    pts_csv = StringIO()
    w=csv.writer(pts_csv)
    w.writerow([x_var,y_var,"feasible","dominant","worst_hard_margin_frac"])
    for x,y,fe,dom,m in pts:
        w.writerow([x,y,fe,dom,m])

    files={
        "atlas_scatter.png": buf1.getvalue(),
        "dominant_counts.csv": dom_csv.getvalue().encode("utf-8"),
        "atlas_points.csv": pts_csv.getvalue().encode("utf-8"),
        "atlas_meta.json": json.dumps({"kind":"shams_fc_atlas_meta","version":"v134","created_utc": created,"x_var":x_var,"y_var":y_var,"n_points":len(pts)}, indent=2, sort_keys=True).encode("utf-8"),
    }
    manifest={
        "kind":"shams_fc_atlas_manifest",
        "version":"v134",
        "created_utc": created,
        "files": {k: {"sha256": _sha256(v), "bytes": len(v)} for k,v in files.items()},
    }
    files["manifest_v134.json"]=json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")

    zbuf=BytesIO()
    with zipfile.ZipFile(zbuf,"w",zipfile.ZIP_DEFLATED) as z:
        for k,v in files.items():
            z.writestr(k,v)

    return {"kind":"shams_fc_atlas_bundle","version":"v134","created_utc": created,"manifest": manifest,"zip_bytes": zbuf.getvalue()}
