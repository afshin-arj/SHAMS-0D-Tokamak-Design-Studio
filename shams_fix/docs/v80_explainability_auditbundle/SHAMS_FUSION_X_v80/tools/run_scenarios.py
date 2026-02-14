import argparse
import json
from pathlib import Path

from models.inputs import PointInputs
from scenarios.spec import ScenarioSpec
from scenarios.runner import run_scenarios_for_point
from shams_io.run_artifact import write_run_artifact

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--point", required=True, help="Path to a point input JSON (PointInputs-like dict).")
    ap.add_argument("--scenarios", required=True, help="Path to scenarios JSON list.")
    ap.add_argument("--outdir", required=True, help="Output directory for scenario artifacts.")
    args = ap.parse_args()

    point_dict = json.loads(Path(args.point).read_text(encoding="utf-8"))
    base = PointInputs(**point_dict)

    scenarios_list = json.loads(Path(args.scenarios).read_text(encoding="utf-8"))
    scenarios = [ScenarioSpec.from_dict(s) for s in scenarios_list]

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    arts = run_scenarios_for_point(base, scenarios)
    for i, art in enumerate(arts):
        name = art.get("scenario", {}).get("name", f"s{i}")
        write_run_artifact(outdir / f"scenario_{i:02d}_{name}.json", art)

if __name__ == "__main__":
    main()
