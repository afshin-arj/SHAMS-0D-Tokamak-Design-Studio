from __future__ import annotations
"""CLI: Feasibility Deep Dive (v142–v144)

Topology + interactions:
  python -m tools.cli_feasibility_deepdive --baseline artifact.json --vars Ip_MA kappa --bounds Ip_MA:8:12 kappa:1.4:2.2 --samples 300

Interval certificate:
  python -m tools.cli_feasibility_deepdive --baseline artifact.json --interval Ip_MA:8:12 kappa:1.4:2.2
"""

import argparse, json
from pathlib import Path
from tools.feasibility_deepdive import (
    SampleConfig, sample_and_evaluate, topology_from_dataset, bundle_topology,
    interactions_from_dataset, bundle_interactions,
    IntervalConfig, interval_certificate, bundle_interval_certificate,
)

def _parse_bounds(items):
    b={}
    for it in items:
        k,lo,hi = it.split(":")
        b[k]=(float(lo), float(hi))
    return b

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--vars", nargs="*", default=[])
    ap.add_argument("--bounds", nargs="*", default=[])
    ap.add_argument("--samples", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--eps", type=float, default=0.0)
    ap.add_argument("--interval", nargs="*", default=[])
    ap.add_argument("--outdir", default="out_deepdive_v144")
    args=ap.parse_args()

    base=json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_inputs = base.get("inputs", {}) if isinstance(base, dict) else {}
    if not isinstance(base_inputs, dict):
        raise SystemExit("baseline must contain inputs dict")
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)

    if args.interval:
        b=_parse_bounds(args.interval)
        cert = interval_certificate(IntervalConfig(baseline_inputs=base_inputs, bounds=b, n_random=60, seed=args.seed))
        bun = bundle_interval_certificate(cert)
        (outp/"interval_certificate_v144.json").write_text(json.dumps(cert, indent=2, sort_keys=True, default=str), encoding="utf-8")
        (outp/"interval_bundle_v144.zip").write_bytes(bun["zip_bytes"])
        print("Wrote", outp/"interval_bundle_v144.zip")

    if args.vars and args.bounds:
        b=_parse_bounds(args.bounds)
        cfg=SampleConfig(baseline_inputs=base_inputs, vars=list(args.vars), bounds=b, n_samples=args.samples, seed=args.seed)
        ds=sample_and_evaluate(cfg)
        topo=topology_from_dataset(ds, k=args.k, eps=args.eps)
        bun=bundle_topology(ds, topo)
        (outp/"topology_bundle_v142.zip").write_bytes(bun["zip_bytes"])
        inter=interactions_from_dataset(ds, top_n=20)
        bun2=bundle_interactions(inter)
        (outp/"interactions_bundle_v143.zip").write_bytes(bun2["zip_bytes"])
        print("Wrote", outp/"topology_bundle_v142.zip", "and", outp/"interactions_bundle_v143.zip")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
