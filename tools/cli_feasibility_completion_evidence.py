from __future__ import annotations
"""CLI: Feasibility Completion Evidence (v159)

Example:
  python -m tools.cli_feasibility_completion_evidence --known known.json --unknowns unknowns.json --outdir out_v159
"""

import argparse, json
from pathlib import Path
from tools.feasibility_completion_evidence import build_feasibility_completion_evidence

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--known", required=True, help="JSON object of known inputs")
    ap.add_argument("--unknowns", required=True, help="JSON list of {name,bounds:[lo,hi]}")
    ap.add_argument("--fixed", default=None, help="Optional JSON list of {name,value}")
    ap.add_argument("--assumptions", default=None, help="Optional JSON object")
    ap.add_argument("--n_samples", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--strategy", default="random", choices=["random","lhs"])
    ap.add_argument("--outdir", default="out_feasibility_completion_v159")
    args=ap.parse_args()

    known=json.loads(Path(args.known).read_text(encoding="utf-8"))
    unknowns=json.loads(Path(args.unknowns).read_text(encoding="utf-8"))
    fixed=json.loads(Path(args.fixed).read_text(encoding="utf-8")) if args.fixed else []
    assumptions=json.loads(Path(args.assumptions).read_text(encoding="utf-8")) if args.assumptions else {}

    out=build_feasibility_completion_evidence(
        known=known, unknowns=unknowns, fixed=fixed, assumption_set=assumptions,
        n_samples=int(args.n_samples), seed=int(args.seed), strategy=str(args.strategy),
        policy={"generator":"cli"},
    )
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"feasibility_completion_evidence_v159.json").write_text(json.dumps(out, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"feasibility_completion_evidence_v159.json")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
