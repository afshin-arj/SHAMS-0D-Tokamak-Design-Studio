from __future__ import annotations
import argparse, json, os, csv, time
from typing import Any, Dict, List
from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from constraints.system import build_constraints_from_outputs
from tools.process_compat.process_compat import constraints_to_records, active_constraints, feasibility_flag, failure_mode, constraint_set_hash, to_jsonable

def main():
    ap = argparse.ArgumentParser(description="Feasible Scan (additive): evaluates points and exports feasibility + margins.")
    ap.add_argument("--base", required=True, help="Base point JSON (dict compatible with PointInputs.sanitize)")
    ap.add_argument("--var", required=True, help="Variable name in PointInputs to scan")
    ap.add_argument("--lo", type=float, required=True)
    ap.add_argument("--hi", type=float, required=True)
    ap.add_argument("--n", type=int, default=21)
    ap.add_argument("--outdir", default="out_feasible_scan")
    ap.add_argument("--topk", type=int, default=5, help="Top-K limiting constraints to record")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    with open(args.base, "r", encoding="utf-8") as f:
        base = json.load(f)

    xs = [args.lo + (args.hi-args.lo) * i/(args.n-1) for i in range(args.n)] if args.n > 1 else [args.lo]
    rows: List[Dict[str, Any]] = []
    t0 = time.time()

    for x in xs:
        payload = dict(base)
        payload[args.var] = x
        inp = PointInputs(**PointInputs.sanitize(payload))
        out = hot_ion_point(inp)
        constraints = build_constraints_from_outputs(out)
        recs = constraints_to_records(constraints)

        feas = feasibility_flag(recs)
        act = active_constraints(recs, top_k=args.topk)
        rows.append({
            "var": args.var,
            "x": float(x),
            "feasible": bool(feas),
            "failure_mode": failure_mode(recs),
            "constraint_set_hash": constraint_set_hash(recs),
            "n_constraints": len(recs),
            "n_ok": sum(1 for r in recs if r.ok),
            "min_signed_margin": min((r.signed_margin for r in recs if r.name), default=float("nan")),
            "active_constraints": [a.name for a in act if a.name],
            "active_signed_margins": [a.signed_margin for a in act if a.name],
            "constraints": to_jsonable(recs),
            "inputs": payload,
            "outputs": out,
        })

    meta = {
        "kind": "feasible_scan",
        "var": args.var,
        "lo": args.lo,
        "hi": args.hi,
        "n": args.n,
        "wall_s": time.time() - t0,
    }

    out_json = os.path.join(args.outdir, "feasible_scan.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "points": rows}, f, indent=2, sort_keys=True)

    # CSV summary (lightweight)
    out_csv = os.path.join(args.outdir, "feasible_scan_summary.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "var","x","feasible","failure_mode","constraint_set_hash","n_constraints","n_ok","min_signed_margin","active_constraints","active_signed_margins"
        ])
        w.writeheader()
        for r in rows:
            w.writerow({
                **{k: r.get(k) for k in w.fieldnames if k not in ("active_constraints","active_signed_margins")},
                "active_constraints": ";".join(r.get("active_constraints", [])),
                "active_signed_margins": ";".join(str(v) for v in r.get("active_signed_margins", [])),
            })

    print(f"Wrote: {out_json}")
    print(f"Wrote: {out_csv}")

if __name__ == "__main__":
    main()
