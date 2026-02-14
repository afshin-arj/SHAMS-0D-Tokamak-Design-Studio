from __future__ import annotations
"""CLI: Constraint Dominance Topology (v158)

Example:
  python -m tools.cli_constraint_dominance --field feasibility_field_v156.json --outdir out_dom_v158
"""

import argparse, json
from pathlib import Path
from tools.constraint_dominance import build_constraint_dominance

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--field", required=True)
    ap.add_argument("--outdir", default="out_constraint_dominance_v158")
    ap.add_argument("--all_points", action="store_true", help="Include feasible points in map (default infeasible-only)")
    args=ap.parse_args()

    field=json.loads(Path(args.field).read_text(encoding="utf-8"))
    dom=build_constraint_dominance(field=field, only_infeasible=(not args.all_points))
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"constraint_dominance_v158.json").write_text(json.dumps(dom, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"constraint_dominance_v158.json")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
