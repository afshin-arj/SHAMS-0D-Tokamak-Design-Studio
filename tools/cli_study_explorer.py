from __future__ import annotations
"""CLI: Study Explorer (v128)

Usage:
  python -m tools.cli_study_explorer --study study_matrix_v127.zip --list
  python -m tools.cli_study_explorer --study study_matrix_v127.zip --compare CASE_A CASE_B --outdir out_compare
"""

import argparse, json
from pathlib import Path
from tools.study_explorer import load_study_zip, parse_study_index, filter_cases, load_case_run_artifact, compare_two_runs

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", required=True)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--feasible_only", action="store_true")
    ap.add_argument("--mission", default=None)
    ap.add_argument("--compare", nargs=2, default=None, metavar=("CASE_A","CASE_B"))
    ap.add_argument("--outdir", default="out_compare_v128")
    args = ap.parse_args()

    files = load_study_zip(args.study)
    idx = parse_study_index(files)
    rows = filter_cases(idx, feasible_only=args.feasible_only, mission=args.mission)

    if args.list:
        for r in rows:
            print(r.get("case_id"), r.get("feasible"), r.get("Q"), r.get("Pnet_MW"))
        return 0

    if args.compare:
        a_id,b_id=args.compare
        a_row=next((r for r in rows if str(r.get("case_id"))==a_id), None)
        b_row=next((r for r in rows if str(r.get("case_id"))==b_id), None)
        if not a_row or not b_row:
            raise SystemExit("Case id not found in filtered rows.")
        a_art=load_case_run_artifact(files, a_row)
        b_art=load_case_run_artifact(files, b_row)
        comp=compare_two_runs(a_art, b_art)

        outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
        (outp/"comparison_v128.json").write_text(json.dumps(comp, indent=2, sort_keys=True), encoding="utf-8")
        print("Wrote", outp/"comparison_v128.json")
        return 0

    print("Nothing to do. Use --list or --compare.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
