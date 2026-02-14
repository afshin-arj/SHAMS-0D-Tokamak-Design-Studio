from __future__ import annotations
"""CLI: Feasibility Completion (v133)

This CLI requires a baseline input dictionary (or a run_artifact) so SHAMS always
evaluates fully specified points. You can still override a subset via --fixed and
define FREE/UNCERTAIN bounds.

Examples:
  # baseline from run_artifact.json
  python -m tools.cli_feasibility_completion --baseline run_artifact.json \
      --fixed R0_m=3 Bt_T=10 \
      --free Ip_MA:8:18 q95:2.5:4.5 \
      --method grid --n_per_dim 4 --outdir out_fc

  # baseline from inputs.json
  python -m tools.cli_feasibility_completion --baseline inputs.json --baseline_kind inputs \
      --free Ip_MA:8:18 --method random --n_random 500
"""

import argparse, json
from pathlib import Path
from tools.feasibility_completion import FCConfig, run_feasibility_completion, build_fc_bundle_zip

def _parse_kv(s: str):
    if "=" not in s:
        raise ValueError("fixed must be k=v")
    k,v=s.split("=",1)
    return k, float(v)

def _parse_bound(s: str):
    # name:lo:hi
    parts=s.split(":")
    if len(parts)!=3:
        raise ValueError("bound must be name:lo:hi")
    return parts[0], (float(parts[1]), float(parts[2]))

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, help="Path to run_artifact.json or inputs.json")
    ap.add_argument("--baseline_kind", default="run_artifact", choices=["run_artifact","inputs"])
    ap.add_argument("--fixed", nargs="*", default=[])
    ap.add_argument("--free", nargs="*", default=[])
    ap.add_argument("--uncertain", nargs="*", default=[])
    ap.add_argument("--method", default="grid", choices=["grid","random"])
    ap.add_argument("--n_per_dim", type=int, default=5)
    ap.add_argument("--n_random", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--outdir", default="out_fc_v133")
    ap.add_argument("--feasible_only_export", action="store_true", help="If set, export only feasible points in evaluations (still keeps evaluations_all).")
    args = ap.parse_args()

    baseline_obj = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    if args.baseline_kind == "run_artifact":
        if not (isinstance(baseline_obj, dict) and isinstance(baseline_obj.get("inputs"), dict)):
            raise SystemExit("baseline run_artifact must contain inputs dict")
        baseline_inputs = dict(baseline_obj["inputs"])
    else:
        if not isinstance(baseline_obj, dict):
            raise SystemExit("baseline inputs must be a JSON dict")
        baseline_inputs = dict(baseline_obj)

    fixed={}
    for s in args.fixed:
        k,v=_parse_kv(s); fixed[k]=v

    bounds={}
    free=[]
    uncertain=[]
    for s in args.free:
        k,(lo,hi)=_parse_bound(s); bounds[k]=(lo,hi); free.append(k)
    for s in args.uncertain:
        k,(lo,hi)=_parse_bound(s); bounds[k]=(lo,hi); uncertain.append(k)

    cfg = FCConfig(
        baseline_inputs=baseline_inputs,
        fixed=fixed,
        bounds=bounds,
        free=free,
        uncertain=uncertain,
        method=args.method,
        n_per_dim=args.n_per_dim,
        n_random=args.n_random,
        seed=args.seed,
        feasible_only_export=bool(args.feasible_only_export),
    )
    rep = run_feasibility_completion(cfg)
    bun = build_fc_bundle_zip(rep)

    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"fc_bundle_v133.zip").write_bytes(bun["zip_bytes"])
    (outp/"fc_report_v133.json").write_text(json.dumps(rep, indent=2, sort_keys=True), encoding="utf-8")
    print("Wrote", outp/"fc_bundle_v133.zip")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
