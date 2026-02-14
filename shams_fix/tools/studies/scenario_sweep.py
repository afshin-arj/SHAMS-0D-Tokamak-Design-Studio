from __future__ import annotations
import argparse, json, os, yaml
from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--scenarios", required=True, help="YAML file with list of scenario overrides")
    ap.add_argument("--outdir", default=os.path.join("artifacts","studies","scenario_sweep"))
    args=ap.parse_args()
    with open(args.base,"r",encoding="utf-8") as f:
        base=json.load(f)
    with open(args.scenarios,"r",encoding="utf-8") as f:
        scenarios=yaml.safe_load(f)
    os.makedirs(args.outdir, exist_ok=True)

    results=[]
    for sc in scenarios:
        name=sc.get("name","scenario")
        overrides=sc.get("overrides",{})
        d=dict(base); d.update(overrides)
        inp=PointInputs.sanitize(d)
        out=hot_ion_point(inp)
        results.append({
            "name": name,
            "overrides": overrides,
            "feasible": bool(out.get("all_constraints_ok", False)),
            "LCOE_proxy_USD_per_MWh": float(out.get("LCOE_proxy_USD_per_MWh", float("nan"))),
            "availability": float(out.get("availability", float("nan"))),
            "TBR": float(out.get("TBR", float("nan"))),
        })
    out_json=os.path.join(args.outdir,"scenario_sweep.json")
    with open(out_json,"w",encoding="utf-8") as f:
        json.dump(results,f,indent=2)
    print(f"Wrote {out_json}")

if __name__=="__main__":
    main()
