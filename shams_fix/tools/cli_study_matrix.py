from __future__ import annotations
"""CLI: Study Matrix (v127)

Usage examples:
  # simple 1D sweep from baseline artifact inputs
  python -m tools.cli_study_matrix --baseline run_artifact.json --lever Bt_T --values 10 11 12 --missions pilot demo --outdir out_study

  # explicit cases json
  python -m tools.cli_study_matrix --baseline run_artifact.json --cases cases.json --outdir out_study
"""

import argparse, json
from pathlib import Path
from tools.study_matrix import build_cases_1d_sweep, build_study_matrix_bundle

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, help="Path to shams_run_artifact JSON.")
    ap.add_argument("--outdir", default="out_study_matrix_v127")
    ap.add_argument("--cases", default=None, help="Optional path to explicit cases JSON list.")
    ap.add_argument("--lever", default=None, help="Optional 1D sweep lever name.")
    ap.add_argument("--values", nargs="*", default=None, help="Optional 1D sweep values (floats).")
    ap.add_argument("--missions", nargs="*", default=None, help="Optional mission names (pilot, demo, powerplant).")
    args = ap.parse_args()

    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    if args.cases:
        cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
        if not isinstance(cases, list):
            raise SystemExit("cases file must be a JSON list")
    else:
        if not (args.lever and args.values):
            raise SystemExit("Provide either --cases or (--lever and --values).")
        values = [float(v) for v in args.values]
        missions = list(args.missions) if args.missions else None
        cases = build_cases_1d_sweep(baseline_run_artifact=baseline, lever=str(args.lever), values=values, missions=missions)

    bundle = build_study_matrix_bundle(baseline_run_artifact=baseline, cases=cases, outdir=args.outdir, version="v127")

    outp = Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp / "study_matrix_v127.zip").write_bytes(bundle["zip_bytes"])
    (outp / "study_matrix_manifest_v127.json").write_text(json.dumps(bundle["manifest"], indent=2, sort_keys=True), encoding="utf-8")
    print("Wrote", outp / "study_matrix_v127.zip")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
