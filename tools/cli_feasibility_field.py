from __future__ import annotations
"""CLI: Feasibility Field (v156)

Example:
  python -m tools.cli_feasibility_field --baseline artifact.json --axis1 R0_m 2.5 4.0 40 --axis2 B0_T 8 15 40 --outdir out_field
"""

import argparse, json
from pathlib import Path
from tools.feasibility_field import build_feasibility_field

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, help="Path to shams_run_artifact.json (or artifact.json)")
    ap.add_argument("--axis1", nargs=5, required=True, metavar=("NAME","START","STOP","N","TYPE"))
    ap.add_argument("--axis2", nargs=5, required=True, metavar=("NAME","START","STOP","N","TYPE"))
    ap.add_argument("--fixed", default="")
    ap.add_argument("--assumptions", default="{}")
    ap.add_argument("--outdir", default="out_feasibility_field_v156")
    args=ap.parse_args()

    base=json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    # allow wrapper artifact.json with payload
    if isinstance(base, dict) and base.get("kind")=="shams_run_artifact":
        baseline_inputs = (base.get("inputs") or {})
    else:
        baseline_inputs = (base.get("inputs") or base.get("_inputs") or base.get("payload") or {})
        if isinstance(base, dict) and isinstance(base.get("payload"), dict) and base["payload"].get("kind")=="shams_run_artifact":
            baseline_inputs = base["payload"].get("inputs") or {}

    def parse_axis(a):
        name, start, stop, n, typ = a
        return {"name": name, "role":"axis", "grid":{"type":"linspace","start": float(start), "stop": float(stop), "n": int(n)}}
    axis1=parse_axis(args.axis1)
    axis2=parse_axis(args.axis2)

    fixed=[]
    if args.fixed.strip():
        for chunk in args.fixed.split(","):
            if "=" in chunk:
                k,v=chunk.split("=",1)
                try:
                    vv=float(v)
                except Exception:
                    vv=v
                fixed.append({"name":k.strip(),"value":vv})
    assumptions=json.loads(args.assumptions) if args.assumptions.strip() else {}

    out=build_feasibility_field(baseline_inputs=baseline_inputs, axis1=axis1, axis2=axis2, fixed=fixed, assumption_set=assumptions,
                                sampling={"generator":"cli","strategy":"grid"})
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"feasibility_field_v156.json").write_text(json.dumps(out["field"], indent=2, sort_keys=True, default=str), encoding="utf-8")
    (outp/"feasibility_atlas_bundle_v156.zip").write_bytes(out["zip_bytes"])
    print("Wrote", outp/"feasibility_atlas_bundle_v156.zip")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
