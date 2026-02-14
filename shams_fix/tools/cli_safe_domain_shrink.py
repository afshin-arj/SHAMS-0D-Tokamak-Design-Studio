from __future__ import annotations
"""CLI: Safe Domain Shrink (v147)

Usage:
  python -m tools.cli_safe_domain_shrink --baseline artifact.json --bounds Ip_MA:8:12 kappa:1.4:2.2 --outdir out_v147
"""

import argparse, json
from pathlib import Path
from tools.safe_domain_shrink import ShrinkConfig, run_safe_domain_shrink

def _parse_bounds(items):
    b={}
    for it in items:
        k,lo,hi = it.split(":")
        b[k]=(float(lo), float(hi))
    return b

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--bounds", nargs="+", required=True)
    ap.add_argument("--shrink_factor", type=float, default=0.85)
    ap.add_argument("--max_iter", type=int, default=10)
    ap.add_argument("--n_random", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--outdir", default="out_safe_domain_v147")
    args=ap.parse_args()

    base=json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    inputs=base.get("inputs", {}) if isinstance(base, dict) else {}
    cfg=ShrinkConfig(baseline_inputs=dict(inputs), bounds=_parse_bounds(args.bounds), shrink_factor=args.shrink_factor, max_iter=args.max_iter, n_random=args.n_random, seed=args.seed)
    rep=run_safe_domain_shrink(cfg)
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"safe_domain_shrink_report_v147.json").write_text(json.dumps(rep, indent=2, sort_keys=True, default=str), encoding="utf-8")
    cert=rep.get("interval_certificate_v144")
    if isinstance(cert, dict):
        (outp/"interval_certificate_v144.json").write_text(json.dumps(cert, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"safe_domain_shrink_report_v147.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
