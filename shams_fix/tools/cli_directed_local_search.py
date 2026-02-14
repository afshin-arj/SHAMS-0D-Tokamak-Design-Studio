from __future__ import annotations
"""CLI: Directed Local Search (v162)

Example:
  python -m tools.cli_directed_local_search --baseline baseline.json --vars vars.json --outdir out_v162
"""

import argparse, json
from pathlib import Path
from tools.directed_local_search import build_directed_local_search

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, help="JSON object baseline inputs")
    ap.add_argument("--vars", required=True, help="JSON list of {name,bounds:[lo,hi]}")
    ap.add_argument("--fixed", default=None, help="Optional JSON list of {name,value}")
    ap.add_argument("--assumptions", default=None, help="Optional JSON object")
    ap.add_argument("--max_evals", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--initial_step_norm", type=float, default=0.12)
    ap.add_argument("--min_step_norm", type=float, default=0.004)
    ap.add_argument("--step_shrink", type=float, default=0.5)
    ap.add_argument("--outdir", default="out_directed_local_search_v162")
    args=ap.parse_args()

    baseline=json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    vars=json.loads(Path(args.vars).read_text(encoding="utf-8"))
    fixed=json.loads(Path(args.fixed).read_text(encoding="utf-8")) if args.fixed else []
    assumptions=json.loads(Path(args.assumptions).read_text(encoding="utf-8")) if args.assumptions else {}

    out=build_directed_local_search(
        baseline=baseline, decision_vars=vars, fixed=fixed, assumption_set=assumptions,
        max_evals=int(args.max_evals), seed=int(args.seed),
        initial_step_norm=float(args.initial_step_norm),
        min_step_norm=float(args.min_step_norm),
        step_shrink=float(args.step_shrink),
        policy={"generator":"cli"},
    )
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"directed_local_search_v162.json").write_text(json.dumps(out, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"directed_local_search_v162.json")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
