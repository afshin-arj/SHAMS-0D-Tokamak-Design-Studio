from __future__ import annotations
"""CLI: Explainability (v122)

Usage:
  python -m tools.cli_explainability --artifact run_artifact.json --outdir out_expl
  python -m tools.cli_explainability --artifact run_artifact.json --mission mission_report.json --envelope tolerance_envelope_report.json --outdir out_expl

Outputs:
- explainability_report.json
- explainability_report.txt
"""
import argparse, json
from pathlib import Path
from tools.explainability import build_explainability_report

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--mission", default=None)
    ap.add_argument("--envelope", default=None)
    ap.add_argument("--outdir", default="out_explainability")
    args = ap.parse_args()

    art = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
    mission = json.loads(Path(args.mission).read_text(encoding="utf-8")) if args.mission else None
    env = json.loads(Path(args.envelope).read_text(encoding="utf-8")) if args.envelope else None

    rep = build_explainability_report(run_artifact=art, mission_report=mission, tolerance_envelope_report=env, version="v122")
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "explainability_report.json").write_text(json.dumps(rep, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "explainability_report.txt").write_text(rep.get("narrative",""), encoding="utf-8")
    print("Wrote", outdir / "explainability_report.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
