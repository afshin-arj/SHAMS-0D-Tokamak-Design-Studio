from __future__ import annotations
"""CLI: Feasibility Boundary (v157)

Example:
  python -m tools.cli_feasibility_boundary --field feasibility_field_v156.json --outdir out_boundary_v157
"""

import argparse, json
from pathlib import Path
from tools.feasibility_boundary import build_feasibility_boundary

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--field", required=True)
    ap.add_argument("--outdir", default="out_feasibility_boundary_v157")
    args=ap.parse_args()

    field=json.loads(Path(args.field).read_text(encoding="utf-8"))
    b=build_feasibility_boundary(field=field)
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"feasibility_boundary_v157.json").write_text(json.dumps(b, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"feasibility_boundary_v157.json")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
