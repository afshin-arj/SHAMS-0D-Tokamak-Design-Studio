from __future__ import annotations
"""CLI: Design Decision Pack (v113)

Usage:
  python -m tools.cli_design_decision_pack --outdir out_decision --artifact a1.json --artifact a2.json --family design_family_report.json --atlas boundary_atlas_v2.json --component component_dominance_report.json --overlay literature_points.json
"""

import argparse
import json
from pathlib import Path

from tools.design_decision_layer import build_design_candidates, build_design_decision_pack

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="out_design_decision")
    ap.add_argument("--artifact", action="append", default=[])
    ap.add_argument("--topology", default=None)
    ap.add_argument("--component", default=None)
    ap.add_argument("--atlas", default=None)
    ap.add_argument("--family", default=None)
    ap.add_argument("--overlay", default=None)
    ap.add_argument("--max_candidates", type=int, default=12)
    ap.add_argument("--preferences", default=None, help="Optional preferences JSON (v114) for annotation + Pareto sets")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    artifacts = [json.loads(Path(p).read_text(encoding="utf-8")) for p in (args.artifact or [])]
    topology = json.loads(Path(args.topology).read_text(encoding="utf-8")) if args.topology else None
    component = json.loads(Path(args.component).read_text(encoding="utf-8")) if args.component else None
    atlas = json.loads(Path(args.atlas).read_text(encoding="utf-8")) if args.atlas else None
    family = json.loads(Path(args.family).read_text(encoding="utf-8")) if args.family else None
    overlay = json.loads(Path(args.overlay).read_text(encoding="utf-8")) if args.overlay else None
    preferences = json.loads(Path(args.preferences).read_text(encoding="utf-8")) if args.preferences else None

    candidates = build_design_candidates(
        artifacts=artifacts,
        topology=topology,
        component_dominance=component,
        boundary_atlas_v2=atlas,
        design_family_report=family,
        literature_overlay=overlay,
        max_candidates=int(args.max_candidates),
    )

    from tools.preference_layer import annotate_candidates_with_preferences, pareto_sets_from_annotations, template_preferences
    prefs = preferences if isinstance(preferences, dict) else template_preferences()
    ann = annotate_candidates_with_preferences(candidates, prefs)
    pareto = pareto_sets_from_annotations(ann)
    justification = {"kind":"shams_decision_justification_v114","created_utc": ann.get("created_utc"), "preferences": prefs, "pareto_sets": pareto, "n_candidates": len(candidates)}
    pack = build_design_decision_pack(candidates=candidates, version="v114", decision_justification=justification)
    (outdir / "design_decision_pack.zip").write_bytes(pack["zip_bytes"])
    (outdir / "candidates.json").write_text(json.dumps({"candidates": candidates}, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "manifest.json").write_text(json.dumps(pack["manifest"], indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "decision_justification.json").write_text(json.dumps(justification, indent=2, sort_keys=True), encoding="utf-8")
    print("Wrote", outdir / "design_decision_pack.zip")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
