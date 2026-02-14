from __future__ import annotations
"""
Design Study Kit — one-command pipeline:
scan -> feasible set -> pareto -> report bundle

Additive only. No physics or solver changes.
"""
import argparse, os, json, time, subprocess, sys
from pathlib import Path

def run(cmd):
    print(">>", " ".join(cmd))
    subprocess.check_call(cmd)

def main():
    ap = argparse.ArgumentParser(description="SHAMS Design Study Kit (v84)")
    ap.add_argument("--base", required=True)
    ap.add_argument("--var", required=True)
    ap.add_argument("--lo", type=float, required=True)
    ap.add_argument("--hi", type=float, required=True)
    ap.add_argument("--n", type=int, default=31)
    ap.add_argument("--objectives", default=None)
    ap.add_argument("--outdir", default="out_design_study")
    args = ap.parse_args()

    out = Path(args.outdir)
    out.mkdir(exist_ok=True)

    # 1) Feasible scan
    scan_dir = out / "scan"
    run([sys.executable, "-m", "tools.studies.feasible_scan",
         "--base", args.base,
         "--var", args.var,
         "--lo", str(args.lo),
         "--hi", str(args.hi),
         "--n", str(args.n),
         "--outdir", str(scan_dir)])

    scan_json = scan_dir / "feasible_scan.json"

    # 2) Pareto (optional)
    pareto_json = None
    if args.objectives:
        pareto_dir = out / "pareto"
        run([sys.executable, "-m", "tools.studies.feasible_pareto",
             "--feasible-scan-json", str(scan_json),
             "--objectives", args.objectives,
             "--outdir", str(pareto_dir)])
        pareto_json = pareto_dir / "feasible_pareto.json"

    # 3) PROCESS handoff
    run([sys.executable, "-m", "tools.studies.process_handoff",
         "--feasible-scan-json", str(scan_json),
         "--out", str(out / "shams_process_handoff.json")])

    # 4) Report bundle
    bundle = {
        "kind": "design_study_bundle",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "scan": str(scan_json),
        "pareto": str(pareto_json) if pareto_json else None,
        "handoff": str(out / "shams_process_handoff.json")
    }
    with open(out / "study_bundle.json", "w") as f:
        json.dump(bundle, f, indent=2)

    print("Design study completed.")
    print("Outputs in:", out)

if __name__ == "__main__":
    main()
