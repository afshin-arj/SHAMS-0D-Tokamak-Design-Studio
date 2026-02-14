from __future__ import annotations
import argparse, json, os
from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from constraints.system import build_constraints_from_outputs, summarize_constraints

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--var", required=True)
    ap.add_argument("--lo", type=float, required=True)
    ap.add_argument("--hi", type=float, required=True)
    ap.add_argument("--n", type=int, default=21)
    ap.add_argument("--outdir", default=os.path.join("artifacts","studies","constraint_sweep"))
    args=ap.parse_args()
    with open(args.base,"r",encoding="utf-8") as f:
        base=json.load(f)
    os.makedirs(args.outdir, exist_ok=True)
    rows=[]
    for i in range(args.n):
        x=args.lo+(args.hi-args.lo)*i/(args.n-1 if args.n>1 else 1)
        d=dict(base); d[args.var]=x
        inp=PointInputs.sanitize(d)
        out=hot_ion_point(inp)
        cs=build_constraints_from_outputs(out)
        summ=summarize_constraints(cs)
        dom=summ.get("dominant",{})
        rows.append({args.var:x,
                     "all_ok": bool(summ.get("all_ok", False)),
                     "dominant": dom.get("name",""),
                     "residual": dom.get("residual", float("nan")),
                     "margin": dom.get("margin", float("nan"))})
    out_json=os.path.join(args.outdir, f"constraint_sweep_{args.var}.json")
    with open(out_json,"w",encoding="utf-8") as f:
        json.dump(rows,f,indent=2)
    print(f"Wrote {out_json}")

if __name__=="__main__":
    main()
