from __future__ import annotations
"""CLI: Design Study Kit (v123B)

Usage:
  python -m tools.cli_study_kit --artifact run_artifact.json --outdir out_kit
Optional:
  --mission mission_report.json
  --envelope tolerance_envelope_report.json
  --explain explainability_report.json
  --authority authority_pack.zip
  --downstream optimizer_downstream_bundle.zip
  --decision decision_pack.zip
"""

import argparse, json
from pathlib import Path
from tools.evidence_graph import build_evidence_graph, build_traceability_table, traceability_csv
from tools.study_kit import build_study_kit_zip

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--mission", default=None)
    ap.add_argument("--envelope", default=None)
    ap.add_argument("--explain", default=None)
    ap.add_argument("--authority", default=None)
    ap.add_argument("--downstream", default=None)
    ap.add_argument("--decision", default=None)
    ap.add_argument("--outdir", default="out_study_kit")
    args = ap.parse_args()

    art = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
    mission = json.loads(Path(args.mission).read_text(encoding="utf-8")) if args.mission else None
    env = json.loads(Path(args.envelope).read_text(encoding="utf-8")) if args.envelope else None
    expl = json.loads(Path(args.explain).read_text(encoding="utf-8")) if args.explain else None
    auth = Path(args.authority).read_bytes() if args.authority else None
    down = Path(args.downstream).read_bytes() if args.downstream else None
    dec = Path(args.decision).read_bytes() if args.decision else None

    graph = build_evidence_graph(run_artifact=art, mission_report=mission, tolerance_envelope_report=env, explainability_report=expl, version="v123")
    tab = build_traceability_table(run_artifact=art, mission_report=mission, tolerance_envelope_report=env, explainability_report=expl, version="v123")

    kit = build_study_kit_zip(
        run_artifact=art,
        mission_report=mission,
        tolerance_envelope_report=env,
        explainability_report=expl,
        evidence_graph=graph,
        traceability_table=tab,
        authority_pack_zip=auth,
        optimizer_downstream_bundle_zip=down,
        decision_pack_zip=dec,
        version="v123B",
    )

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "study_kit_v123B.zip").write_bytes(kit["zip_bytes"])
    (outdir / "study_kit_manifest_v123B.json").write_text(json.dumps(kit["manifest"], indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "traceability.csv").write_bytes(traceability_csv(tab))
    print("Wrote", outdir / "study_kit_v123B.zip")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
