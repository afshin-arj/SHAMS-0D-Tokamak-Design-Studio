from __future__ import annotations
"""Sensitivity Maps (v140)

Goal:
For a feasible baseline run, estimate how much each selected variable can vary
(+/-) before hard feasibility breaks. Uses auditable finite perturbations only.

Safety:
- Downstream orchestration only (no physics/solver changes)
- Deterministic given config
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from io import BytesIO, StringIO
from pathlib import Path
import json, time, hashlib, zipfile, csv, math

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

@dataclass
class SensitivityConfig:
    baseline_inputs: Dict[str, Any]
    fixed_overrides: Dict[str, Any]
    vars: List[str]
    bounds: Dict[str, Tuple[float, float]]  # optional clamps
    max_rel: float = 0.40   # max relative change to search
    max_abs: float = 0.0    # if >0, also cap absolute change
    n_expand: int = 8       # expansion steps
    n_bisect: int = 10      # bisection steps
    require_baseline_feasible: bool = True

def _eval(inp: Dict[str, Any]) -> Dict[str, Any]:
    art = evaluate_point_inputs(inputs_dict=inp, solver_meta={"label":"sens_v140"})
    cs = art.get("constraints_summary", {}) if isinstance(art.get("constraints_summary"), dict) else {}
    return {
        "artifact": art,
        "feasible": cs.get("feasible"),
        "worst_hard": cs.get("worst_hard"),
        "worst_hard_margin_frac": cs.get("worst_hard_margin_frac"),
    }

def _clamp(x: float, lo: Optional[float], hi: Optional[float]) -> float:
    if lo is not None: x = max(lo, x)
    if hi is not None: x = min(hi, x)
    return x

def _target_value(x0: float, direction: int, rel: float, abs_cap: float) -> float:
    # direction: +1 or -1
    dx = rel * abs(x0) if abs(x0) > 1e-12 else rel
    if abs_cap and abs_cap > 0:
        dx = min(dx, abs_cap)
    return x0 + direction * dx

def _find_boundary_1d(base_inputs: Dict[str, Any], var: str, x0: float, direction: int,
                      cfg: SensitivityConfig) -> Dict[str, Any]:
    lo_b, hi_b = None, None
    if var in cfg.bounds:
        lo_b, hi_b = cfg.bounds[var][0], cfg.bounds[var][1]

    # Expand: find first fail (or hit limits)
    last_ok = {"rel": 0.0, "x": x0, "res": _eval(base_inputs)}
    if last_ok["res"]["feasible"] is not True and cfg.require_baseline_feasible:
        return {"var": var, "direction": direction, "status": "baseline_infeasible", "baseline": last_ok["res"]}

    first_fail = None
    rels = [cfg.max_rel * (i+1)/cfg.n_expand for i in range(int(cfg.n_expand))]
    for r in rels:
        xt = _target_value(x0, direction, r, cfg.max_abs)
        xt = _clamp(xt, lo_b, hi_b)
        inp = dict(base_inputs); inp[var] = float(xt)
        res = _eval(inp)
        if res["feasible"] is True:
            last_ok = {"rel": r, "x": float(xt), "res": res}
        else:
            first_fail = {"rel": r, "x": float(xt), "res": res}
            break

    if first_fail is None:
        return {"var": var, "direction": direction, "status": "no_failure_within_budget",
                "last_ok": last_ok}

    # Bisect between last_ok and first_fail on rel parameter
    a = float(last_ok["rel"]); b = float(first_fail["rel"])
    ax = float(last_ok["x"]); bx = float(first_fail["x"])

    for _ in range(int(cfg.n_bisect)):
        m = 0.5*(a+b)
        xt = _target_value(x0, direction, m, cfg.max_abs)
        xt = _clamp(xt, lo_b, hi_b)
        inp = dict(base_inputs); inp[var]=float(xt)
        res = _eval(inp)
        if res["feasible"] is True:
            a = m; ax = float(xt); last_ok = {"rel": m, "x": float(xt), "res": res}
        else:
            b = m; bx = float(xt); first_fail = {"rel": m, "x": float(xt), "res": res}

    return {"var": var, "direction": direction, "status": "bounded",
            "last_ok": last_ok, "first_fail": first_fail,
            "boundary_rel": float(last_ok["rel"]), "boundary_x": float(last_ok["x"])}

def run_sensitivity(cfg: SensitivityConfig) -> Dict[str, Any]:
    created = _created_utc()
    base = dict(cfg.baseline_inputs or {})
    base.update(cfg.fixed_overrides or {})

    baseline_res = _eval(base)
    out = {
        "kind": "shams_sensitivity_report",
        "version": "v140",
        "created_utc": created,
        "baseline": {
            "feasible": baseline_res.get("feasible"),
            "worst_hard": baseline_res.get("worst_hard"),
            "worst_hard_margin_frac": baseline_res.get("worst_hard_margin_frac"),
        },
        "config": {
            "vars": list(cfg.vars),
            "bounds": {k:[float(v[0]), float(v[1])] for k,v in (cfg.bounds or {}).items()},
            "max_rel": float(cfg.max_rel),
            "max_abs": float(cfg.max_abs),
            "n_expand": int(cfg.n_expand),
            "n_bisect": int(cfg.n_bisect),
            "require_baseline_feasible": bool(cfg.require_baseline_feasible),
        },
        "results": [],
    }

    for v in cfg.vars:
        x0 = _safe_float(base.get(v))
        if x0 is None:
            out["results"].append({"var": v, "status": "non_numeric_or_missing"})
            continue
        neg = _find_boundary_1d(base, v, x0, -1, cfg)
        pos = _find_boundary_1d(base, v, x0, +1, cfg)

        def summarize(r):
            if r.get("status") == "bounded":
                return {
                    "status": "bounded",
                    "boundary_rel": r.get("boundary_rel"),
                    "boundary_x": r.get("boundary_x"),
                    "worst_hard_at_boundary": (r.get("last_ok", {}).get("res", {}) or {}).get("worst_hard"),
                    "margin_frac_at_boundary": (r.get("last_ok", {}).get("res", {}) or {}).get("worst_hard_margin_frac"),
                }
            if r.get("status") == "no_failure_within_budget":
                lk=r.get("last_ok", {})
                return {"status":"no_failure_within_budget", "last_ok_rel": lk.get("rel"), "last_ok_x": lk.get("x"),
                        "worst_hard": (lk.get("res", {}) or {}).get("worst_hard"),
                        "margin_frac": (lk.get("res", {}) or {}).get("worst_hard_margin_frac")}
            return {"status": r.get("status"), "baseline": r.get("baseline")}

        out["results"].append({
            "var": v,
            "x0": float(x0),
            "minus": summarize(neg),
            "plus": summarize(pos),
        })

    return out

def build_sensitivity_bundle(report: Dict[str, Any]) -> Dict[str, Any]:
    created = str(report.get("created_utc") or _created_utc())
    rep_bytes = json.dumps(report, indent=2, sort_keys=True, default=str).encode("utf-8")

    # CSV summary
    rows=[]
    for r in report.get("results") or []:
        if not isinstance(r, dict): continue
        v=r.get("var")
        x0=r.get("x0")
        m=r.get("minus", {}) if isinstance(r.get("minus"), dict) else {}
        p=r.get("plus", {}) if isinstance(r.get("plus"), dict) else {}
        rows.append({
            "var": v, "x0": x0,
            "minus_status": m.get("status"),
            "minus_boundary_rel": m.get("boundary_rel"),
            "minus_boundary_x": m.get("boundary_x"),
            "plus_status": p.get("status"),
            "plus_boundary_rel": p.get("boundary_rel"),
            "plus_boundary_x": p.get("boundary_x"),
        })

    fieldnames=["var","x0","minus_status","minus_boundary_rel","minus_boundary_x","plus_status","plus_boundary_rel","plus_boundary_x"]
    buf=StringIO()
    w=csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for rr in rows:
        w.writerow(rr)
    csv_bytes=buf.getvalue().encode("utf-8")

    # Simple bar plot of allowable rel ranges if bounded
    png_bytes=b""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        vars_=[r["var"] for r in rows]
        minus=[abs(float(r["minus_boundary_rel"])) if r["minus_boundary_rel"] is not None else 0.0 for r in rows]
        plus=[abs(float(r["plus_boundary_rel"])) if r["plus_boundary_rel"] is not None else 0.0 for r in rows]
        fig=plt.figure(figsize=(max(6, 0.4*len(vars_)), 3.2))
        ax=fig.add_subplot(111)
        xs=list(range(len(vars_)))
        ax.bar([x-0.2 for x in xs], minus, width=0.4, label="-")
        ax.bar([x+0.2 for x in xs], plus, width=0.4, label="+")
        ax.set_xticks(xs)
        ax.set_xticklabels(vars_, rotation=45, ha="right")
        ax.set_ylabel("Boundary rel change")
        ax.set_title("Sensitivity boundaries (v140)")
        ax.legend()
        out=BytesIO()
        fig.savefig(out, dpi=180, bbox_inches="tight")
        plt.close(fig)
        png_bytes=out.getvalue()
    except Exception:
        png_bytes=b""

    files={
        "sensitivity_report_v140.json": rep_bytes,
        "sensitivity_summary_v140.csv": csv_bytes,
    }
    if png_bytes:
        files["sensitivity_plot_v140.png"]=png_bytes

    manifest={
        "kind":"shams_sensitivity_bundle_manifest",
        "version":"v140",
        "created_utc": created,
        "files": {k: {"sha256": _sha256(v), "bytes": len(v)} for k,v in files.items()},
    }
    files["manifest_v140.json"]=json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")

    zbuf=BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for k,v in files.items():
            z.writestr(k,v)

    return {"kind":"shams_sensitivity_bundle","version":"v140","created_utc": created,"manifest": manifest,"zip_bytes": zbuf.getvalue()}
