from __future__ import annotations
"""CLI: Study Matrix v2 (v132)

Example:
  python -m tools.cli_study_matrix_v2 --baseline run_artifact.json --sweep Bt_T 9 12 5 --sweep R0_m 2.5 3.5 4 --missions pilot --outdir out_study_v132
"""

import argparse, json
from pathlib import Path
from tools.study_matrix_v2 import build_cases_multi_sweep, build_study_matrix_bundle_v2

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--outdir", default="out_study_matrix_v132")
    ap.add_argument("--missions", nargs="*", default=None)
    ap.add_argument("--sweep", action="append", nargs=4, metavar=("LEVER","MIN","MAX","N"),
                    help="Repeatable: --sweep Bt_T 9 12 5")
    ap.add_argument("--derived", nargs="*", default=["Pnet_per_R0","Q_per_Bt","margin_penalty"])
    args = ap.parse_args()

    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    if not args.sweep:
        raise SystemExit("Provide at least one --sweep")

    sweeps=[]
    for lever, vmin, vmax, n in args.sweep:
        sweeps.append({"lever": lever, "min": float(vmin), "max": float(vmax), "n": int(n)})
    cases = build_cases_multi_sweep(baseline_run_artifact=baseline, sweeps=sweeps, missions=(list(args.missions) if args.missions else None))
    bundle = build_study_matrix_bundle_v2(baseline_run_artifact=baseline, cases=cases, outdir=args.outdir, version="v132", derived=list(args.derived or []))

    outp = Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp / "study_matrix_v132.zip").write_bytes(bundle["zip_bytes"])
    (outp / "study_matrix_manifest_v132.json").write_text(json.dumps(bundle["manifest"], indent=2, sort_keys=True), encoding="utf-8")
    print("Wrote", outp / "study_matrix_v132.zip")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
