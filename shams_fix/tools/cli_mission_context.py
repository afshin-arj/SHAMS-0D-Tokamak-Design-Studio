from __future__ import annotations
"""CLI: Mission Context (v121)

Usage:
  python -m tools.cli_mission_context --artifact run_artifact.json --mission missions/pilot.json --outdir out_mission

Outputs:
- mission_report.json
- mission_gaps.csv
"""
import argparse, json
from pathlib import Path
from tools.mission_context import load_mission, apply_mission_overlays, mission_report_csv

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--mission", required=True)
    ap.add_argument("--outdir", default="out_mission")
    args = ap.parse_args()

    art = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
    mission = load_mission(args.mission)
    rep = apply_mission_overlays(run_artifact=art, mission=mission, version="v121")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "mission_report.json").write_text(json.dumps(rep, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "mission_gaps.csv").write_bytes(mission_report_csv(rep))
    print("Wrote", outdir / "mission_report.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
