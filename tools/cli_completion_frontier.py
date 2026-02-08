from __future__ import annotations
"""CLI: Completion Frontier (v161)

Example:
  python -m tools.cli_completion_frontier --baseline baseline.json --vars vars.json --outdir out_v161
"""

import argparse, json
from pathlib import Path
from tools.completion_frontier import build_completion_frontier

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, help="JSON object baseline inputs")
    ap.add_argument("--vars", required=True, help="JSON list of {name,bounds:[lo,hi]}")
    ap.add_argument("--fixed", default=None, help="Optional JSON list of {name,value}")
    ap.add_argument("--assumptions", default=None, help="Optional JSON object")
    ap.add_argument("--n_samples", type=int, default=800)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--strategy", default="random", choices=["random","lhs"])
    ap.add_argument("--outdir", default="out_completion_frontier_v161")
    args=ap.parse_args()

    baseline=json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    vars=json.loads(Path(args.vars).read_text(encoding="utf-8"))
    fixed=json.loads(Path(args.fixed).read_text(encoding="utf-8")) if args.fixed else []
    assumptions=json.loads(Path(args.assumptions).read_text(encoding="utf-8")) if args.assumptions else {}

    out=build_completion_frontier(
        baseline=baseline, decision_vars=vars, fixed=fixed, assumption_set=assumptions,
        n_samples=int(args.n_samples), seed=int(args.seed), strategy=str(args.strategy),
        policy={"generator":"cli"},
    )
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"completion_frontier_v161.json").write_text(json.dumps(out, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"completion_frontier_v161.json")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
