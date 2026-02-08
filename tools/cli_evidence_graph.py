from __future__ import annotations
"""CLI: Evidence Graph & Traceability (v123)

Usage:
  python -m tools.cli_evidence_graph --artifact run_artifact.json --outdir out_ev
Optional:
  --mission mission_report.json
  --envelope tolerance_envelope_report.json
  --explain explainability_report.json
"""

import argparse, json
from pathlib import Path
from tools.evidence_graph import build_evidence_graph, build_traceability_table, traceability_csv

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--mission", default=None)
    ap.add_argument("--envelope", default=None)
    ap.add_argument("--explain", default=None)
    ap.add_argument("--outdir", default="out_evidence")
    args = ap.parse_args()

    art = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
    mission = json.loads(Path(args.mission).read_text(encoding="utf-8")) if args.mission else None
    env = json.loads(Path(args.envelope).read_text(encoding="utf-8")) if args.envelope else None
    expl = json.loads(Path(args.explain).read_text(encoding="utf-8")) if args.explain else None

    graph = build_evidence_graph(run_artifact=art, mission_report=mission, tolerance_envelope_report=env, explainability_report=expl, version="v123")
    tab = build_traceability_table(run_artifact=art, mission_report=mission, tolerance_envelope_report=env, explainability_report=expl, version="v123")

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "evidence_graph.json").write_text(json.dumps(graph, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "traceability_table.json").write_text(json.dumps(tab, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "traceability.csv").write_bytes(traceability_csv(tab))
    print("Wrote", outdir / "evidence_graph.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
