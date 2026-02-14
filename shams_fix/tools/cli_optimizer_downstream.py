from __future__ import annotations
"""CLI: Optimizer Downstream Report (v118)

Usage:
  python -m tools.cli_optimizer_downstream --batch optimizer_batch.json --outdir out_downstream
  python -m tools.cli_optimizer_downstream --write-template --outdir out_downstream

Outputs:
- optimizer_downstream_report_v118.json
- design_decision_pack_v118.zip
- optimizer_downstream_bundle_v118.zip
"""

import argparse, json
from pathlib import Path
from tools.optimizer_downstream import template_batch_response, evaluate_optimizer_batch, build_downstream_report_zip
from tools.preference_layer import template_preferences
from tools.tolerance_envelope import template_tolerance_spec

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="out_optimizer_downstream")
    ap.add_argument("--write-template", action="store_true")
    ap.add_argument("--batch", default=None, help="Path to shams_optimizer_batch_response JSON")
    ap.add_argument("--preferences", default=None, help="Optional preferences JSON (v114)")
    ap.add_argument("--tolerance_spec", default=None, help="Optional tolerance spec JSON (v117)")
    ap.add_argument("--max_envelope_samples", type=int, default=24)
    ap.add_argument("--max_candidates", type=int, default=12)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.write_template:
        (outdir / "optimizer_batch_template.json").write_text(json.dumps(template_batch_response(), indent=2, sort_keys=True), encoding="utf-8")
        (outdir / "preferences_template.json").write_text(json.dumps(template_preferences(), indent=2, sort_keys=True), encoding="utf-8")
        (outdir / "tolerance_spec_template.json").write_text(json.dumps(template_tolerance_spec(), indent=2, sort_keys=True), encoding="utf-8")
        print("Wrote templates to", outdir)
        if not args.batch:
            return 0

    if not args.batch:
        raise SystemExit("Provide --batch or use --write-template")

    batch = json.loads(Path(args.batch).read_text(encoding="utf-8"))
    prefs = json.loads(Path(args.preferences).read_text(encoding="utf-8")) if args.preferences else None
    spec = json.loads(Path(args.tolerance_spec).read_text(encoding="utf-8")) if args.tolerance_spec else None

    out = evaluate_optimizer_batch(
        batch_payload=batch,
        tolerance_spec=spec,
        max_envelope_samples=int(args.max_envelope_samples),
        max_candidates=int(args.max_candidates),
        preferences=prefs,
    )
    rep = out["report"]
    pack_bytes = out["decision_pack_zip_bytes"]

    (outdir / "optimizer_downstream_report_v118.json").write_text(json.dumps(rep, indent=2, sort_keys=True), encoding="utf-8")
    (outdir / "design_decision_pack_v118.zip").write_bytes(pack_bytes)
    bundle = build_downstream_report_zip(report_obj=rep, decision_pack_zip_bytes=pack_bytes)
    (outdir / "optimizer_downstream_bundle_v118.zip").write_bytes(bundle["zip_bytes"])
    (outdir / "optimizer_downstream_bundle_manifest.json").write_text(json.dumps(bundle["manifest"], indent=2, sort_keys=True), encoding="utf-8")
    print("Wrote", outdir / "optimizer_downstream_bundle_v118.zip")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
