from __future__ import annotations
"""CLI: Feasibility Atlas (v124)

Usage:
  python -m tools.cli_feasibility_atlas --baseline baseline_run_artifact.json --x R0_m --y B0_T --xlo 2.5 --xhi 3.5 --ylo 8 --yhi 12 --nx 25 --ny 25 --outdir out_atlas

Outputs:
- outdir/feasibility_atlas_v124.json
- outdir/boundary_atlas_v2.json
- outdir/feasibility_points.csv
- outdir/*.png (maps) and boundary_plots/*.png (if available)
"""

import argparse, json
from pathlib import Path
from tools.feasibility_atlas import build_feasibility_atlas_bundle

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--x", required=True)
    ap.add_argument("--y", required=True)
    ap.add_argument("--xlo", type=float, required=True)
    ap.add_argument("--xhi", type=float, required=True)
    ap.add_argument("--ylo", type=float, required=True)
    ap.add_argument("--yhi", type=float, required=True)
    ap.add_argument("--nx", type=int, default=25)
    ap.add_argument("--ny", type=int, default=25)
    ap.add_argument("--outdir", default="out_feasibility_atlas_v124")
    args = ap.parse_args()

    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    bundle = build_feasibility_atlas_bundle(
        baseline_run_artifact=base,
        lever_x=args.x,
        lever_y=args.y,
        x_range=(args.xlo, args.xhi),
        y_range=(args.ylo, args.yhi),
        nx=args.nx,
        ny=args.ny,
        outdir=args.outdir,
        version="v124",
    )
    print("Wrote", Path(args.outdir) / "feasibility_atlas_v124.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
