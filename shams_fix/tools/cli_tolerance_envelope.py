from __future__ import annotations
"""CLI: Tolerance Envelope (v117)

Usage:
  python -m tools.cli_tolerance_envelope --artifact artifact.json --outdir out_env
  python -m tools.cli_tolerance_envelope --artifact artifact.json --spec tolerance_spec.json --outdir out_env

Outputs:
- tolerance_envelope_report.json
- tolerance_envelope_summary.csv
"""

import argparse
import json
from pathlib import Path
from tools.tolerance_envelope import evaluate_tolerance_envelope, envelope_summary_csv, template_tolerance_spec

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--spec", default=None)
    ap.add_argument("--outdir", default="out_tolerance_envelope")
    ap.add_argument("--max_samples", type=int, default=200)
    args = ap.parse_args()

    art = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8")) if args.spec else template_tolerance_spec()
    rep = evaluate_tolerance_envelope(baseline_artifact=art, tolerance_spec=spec, version="v117", max_samples=int(args.max_samples))

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "tolerance_envelope_report.json").write_text(json.dumps(rep, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "tolerance_envelope_summary.csv").write_bytes(envelope_summary_csv(rep))
    print("Wrote", outdir / "tolerance_envelope_report.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
