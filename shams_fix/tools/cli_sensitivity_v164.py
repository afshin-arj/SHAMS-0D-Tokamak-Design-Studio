from __future__ import annotations
"""CLI: Sensitivity v164

Example:
  python -m tools.cli_sensitivity_v164 --witness witness.json --vars vars.json --outdir out_v164
"""

import argparse, json
from pathlib import Path
from tools.sensitivity_v164 import build_sensitivity_report, render_sensitivity_markdown

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--witness", required=True, help="JSON object: witness inputs")
    ap.add_argument("--vars", required=True, help="JSON list: {name,bounds:[lo,hi]}")
    ap.add_argument("--assumptions", default=None, help="Optional JSON object")
    ap.add_argument("--rel_step", type=float, default=0.01)
    ap.add_argument("--abs_step_min", type=float, default=1e-6)
    ap.add_argument("--outdir", default="out_sensitivity_v164")
    args=ap.parse_args()

    witness=json.loads(Path(args.witness).read_text(encoding="utf-8"))
    vars=json.loads(Path(args.vars).read_text(encoding="utf-8"))
    assumptions=json.loads(Path(args.assumptions).read_text(encoding="utf-8")) if args.assumptions else {}

    rep=build_sensitivity_report(
        witness=witness, variables=vars, assumption_set=assumptions,
        rel_step=float(args.rel_step), abs_step_min=float(args.abs_step_min),
        policy={"generator":"cli"},
    )
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"sensitivity_v164.json").write_text(json.dumps(rep, indent=2, sort_keys=True, default=str), encoding="utf-8")
    (outp/"sensitivity_v164.md").write_text(render_sensitivity_markdown(rep), encoding="utf-8")
    print("Wrote", outp/"sensitivity_v164.json")
    print("Wrote", outp/"sensitivity_v164.md")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
