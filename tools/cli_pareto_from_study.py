from __future__ import annotations
"""CLI: Pareto from Study (v129)

Example:
  python -m tools.cli_pareto_from_study --study study_matrix_v127.zip --objectives Q:max Pnet_MW:max R0_m:min --outdir out_pareto
"""

import argparse, json
from pathlib import Path
from tools.pareto_from_study import build_pareto, pareto_bundle_zip

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", required=True)
    ap.add_argument("--outdir", default="out_pareto_v129")
    ap.add_argument("--objectives", nargs="+", required=True, help="Format: COL:sense (sense=max|min)")
    ap.add_argument("--feasible_only", action="store_true", default=True)
    ap.add_argument("--mission", default=None)
    args = ap.parse_args()

    objs=[]
    for s in args.objectives:
        if ":" not in s:
            raise SystemExit("objective must be COL:sense")
        k,sen = s.split(":",1)
        objs.append({"k": k, "sense": sen})
    rep = build_pareto(study_path=args.study, objectives=objs, feasible_only=bool(args.feasible_only), mission=args.mission, version="v129")
    bun = pareto_bundle_zip(rep)

    outp = Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"pareto_bundle_v129.zip").write_bytes(bun["zip_bytes"])
    (outp/"pareto_report_v129.json").write_text(json.dumps(rep, indent=2, sort_keys=True), encoding="utf-8")
    print("Wrote", outp/"pareto_bundle_v129.zip")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
