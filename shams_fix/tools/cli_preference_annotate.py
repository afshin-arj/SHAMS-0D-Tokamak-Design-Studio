from __future__ import annotations
"""CLI: Preference annotate candidates (v114)

Usage:
  python -m tools.cli_preference_annotate --candidates candidates.json --prefs prefs.json --outdir out_pref

Writes:
- candidates_annotated.json
- pareto_sets.json
- decision_justification.json
"""

import argparse
import json
from pathlib import Path

from tools.preference_decision_layer import annotate_candidates_with_preferences, build_pareto_sets
from tools.preferences import template_preferences

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="out_pref")
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--prefs", default=None)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cobj = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    cands = cobj.get("candidates", []) if isinstance(cobj, dict) else []
    prefs = json.loads(Path(args.prefs).read_text(encoding="utf-8")) if args.prefs else template_preferences("v114")

    bundle = annotate_candidates_with_preferences(candidates=cands, preferences=prefs)
    pareto = build_pareto_sets(bundle)

    (outdir / "candidates_annotated.json").write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "pareto_sets.json").write_text(json.dumps(pareto, indent=2, sort_keys=True), encoding="utf-8")
    justification = {
        "kind": "shams_decision_justification",
        "version": "v114",
        "created_utc": bundle.get("created_utc"),
        "preferences": bundle.get("preferences"),
        "warnings": bundle.get("warnings"),
        "pareto_sets": pareto.get("sets"),
        "notes": [
            "This file is a post-feasibility annotation. It does not constitute an optimization result.",
            "All scores are derived from existing SHAMS outputs and explicit user preferences.",
        ],
    }
    (outdir / "decision_justification.json").write_text(json.dumps(justification, indent=2, sort_keys=True), encoding="utf-8")
    print("Wrote", outdir)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
