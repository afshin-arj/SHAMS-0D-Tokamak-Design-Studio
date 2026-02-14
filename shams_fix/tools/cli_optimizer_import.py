from __future__ import annotations
"""CLI: External Optimizer Import (v115)

Usage:
  # create templates
  python -m tools.cli_optimizer_import --outdir out_opt --write-templates

  # evaluate a proposal json
  python -m tools.cli_optimizer_import --outdir out_opt --response optimizer_response.json

Outputs:
- evaluated_run_artifact.json
- optimizer_import_context.json
- optimizer_import_pack.zip
"""

import argparse
import json
from pathlib import Path

from tools.optimizer_interface import template_request, template_response, evaluate_optimizer_proposal, build_optimizer_import_pack

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="out_optimizer_import")
    ap.add_argument("--write-templates", action="store_true")
    ap.add_argument("--response", default=None, help="Path to shams_optimizer_response JSON")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    req = template_request(version="v115")
    resp_tpl = template_response(version="v115")

    if args.write_templates:
        (outdir / "optimizer_request_template.json").write_text(json.dumps(req, indent=2, sort_keys=True), encoding="utf-8")
        (outdir / "optimizer_response_template.json").write_text(json.dumps(resp_tpl, indent=2, sort_keys=True), encoding="utf-8")

    evaluated = None
    ctx = None
    if args.response:
        payload = json.loads(Path(args.response).read_text(encoding="utf-8"))
        out = evaluate_optimizer_proposal(payload)
        evaluated = out["artifact"]
        ctx = out["context"]
        (outdir / "evaluated_run_artifact.json").write_text(json.dumps(evaluated, indent=2, sort_keys=True), encoding="utf-8")
        (outdir / "optimizer_import_context.json").write_text(json.dumps(ctx, indent=2, sort_keys=True), encoding="utf-8")

    pack = build_optimizer_import_pack(request_template=req, response_template=resp_tpl, evaluated_artifact=evaluated, import_context=ctx, version="v115")
    (outdir / "optimizer_import_pack.zip").write_bytes(pack["zip_bytes"])
    (outdir / "optimizer_import_pack_manifest.json").write_text(json.dumps(pack["manifest"], indent=2, sort_keys=True), encoding="utf-8")

    print("Wrote", outdir / "optimizer_import_pack.zip")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
