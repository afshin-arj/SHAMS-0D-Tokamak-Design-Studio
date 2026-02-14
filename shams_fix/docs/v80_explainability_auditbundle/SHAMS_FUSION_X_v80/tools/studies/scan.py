from __future__ import annotations
import argparse, json, os
from typing import Dict, Any, List
from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from constraints.system import build_constraints_from_outputs, summarize_constraints

def load_base(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _scan_worker(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Worker-safe point evaluation for scan runs (pickleable)."""
    base = payload["base"]
    var = payload["var"]
    x = float(payload["x"])
    # Local imports for process isolation
    from models.inputs import PointInputs
    from physics.hot_ion import hot_ion_point
    from constraints.system import build_constraints_from_outputs, summarize_constraints

    inp = PointInputs(**PointInputs.sanitize({**base, var: x}))
    import time as _time
    _t0 = _time.perf_counter()
    out = hot_ion_point(inp)
    _eval_s = _time.perf_counter() - _t0
    cs = build_constraints_from_outputs(out)
    summary = summarize_constraints(cs)
    return {
        "i": int(payload["i"]),
        var: x,
        "feasible": bool(out.get("all_constraints_ok", summary.get("all_ok", False))),
        "objective": float(out.get("LCOE_proxy_USD_per_MWh", out.get("COE_USD_per_MWh", float("nan")))),
        "dominant_blocker": summary.get("dominant", {}).get("name", ""),
        "dominant_residual": summary.get("dominant", {}).get("residual", float("nan")),
        "eval_s": float(_eval_s),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="Base point JSON (dict compatible with PointInputs.sanitize)")
    ap.add_argument("--var", required=True, help="Variable name in PointInputs to scan")
    ap.add_argument("--lo", type=float, required=True)
    ap.add_argument("--hi", type=float, required=True)
    ap.add_argument("--n", type=int, default=21)
    ap.add_argument("--parallel", action="store_true", help="Parallelize point evaluations (order preserved)")
    ap.add_argument("--workers", type=int, default=0, help="Worker processes (0=auto)")
    ap.add_argument("--outdir", default=os.path.join("artifacts","studies","scan"))
    args = ap.parse_args()
    import time as _time
    t_wall0 = _time.perf_counter()

    base = load_base(args.base)
    os.makedirs(args.outdir, exist_ok=True)

    rows=[]
    xs = [args.lo + (args.hi-args.lo)*(i/(max(args.n-1,1))) for i in range(args.n)]
    if args.parallel:
        import concurrent.futures, os as _os
        n_workers = args.workers if args.workers and args.workers > 0 else None
        payloads = [{"i": idx, "base": base, "var": args.var, "x": x} for idx, x in enumerate(xs)]
        with concurrent.futures.ProcessPoolExecutor(max_workers=n_workers) as ex:
            futs = [ex.submit(_scan_worker, p) for p in payloads]
            for fut in concurrent.futures.as_completed(futs):
                rows.append(fut.result())
        # preserve ordering
        rows.sort(key=lambda r: int(r.get("i", 0)))
        for r in rows:
            r.pop("i", None)
    else:
        for idx, x in enumerate(xs):
            inp = PointInputs(**PointInputs.sanitize({**base, args.var: x}))
            out = hot_ion_point(inp)
            cs = build_constraints_from_outputs(out)
            summary = summarize_constraints(cs)
            rows.append({
                args.var: x,
                "feasible": bool(out.get("all_constraints_ok", summary.get("all_ok", False))),
                "objective": float(out.get("LCOE_proxy_USD_per_MWh", out.get("COE_USD_per_MWh", float("nan")))),
                "dominant_blocker": summary.get("dominant", {}).get("name", ""),
                "dominant_residual": summary.get("dominant", {}).get("residual", float("nan")),
        "eval_s": float(_eval_s),
            })
    out_json=os.path.join(args.outdir, f"scan_{args.var}.json")
    with open(out_json,"w",encoding="utf-8") as f:
        json.dump(rows,f,indent=2)
    print(f"Wrote {out_json}")

if __name__ == "__main__":
    main()
