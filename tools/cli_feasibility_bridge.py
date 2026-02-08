from __future__ import annotations
"""CLI: Feasibility Bridge (v146)

Usage:
  python -m tools.cli_feasibility_bridge --A artifactA.json --B artifactB.json --vars Ip_MA kappa --outdir out_v146
"""

import argparse, json
from pathlib import Path
from tools.feasibility_bridge import BridgeConfig, run_bridge, bridge_certificate

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--A", required=True, help="artifact.json containing inputs")
    ap.add_argument("--B", required=True, help="artifact.json containing inputs")
    ap.add_argument("--vars", nargs="+", required=True)
    ap.add_argument("--n_steps", type=int, default=21)
    ap.add_argument("--max_bisect_depth", type=int, default=6)
    ap.add_argument("--outdir", default="out_bridge_v146")
    args=ap.parse_args()

    a=json.loads(Path(args.A).read_text(encoding="utf-8"))
    b=json.loads(Path(args.B).read_text(encoding="utf-8"))
    Ain=a.get("inputs", {}) if isinstance(a, dict) else {}
    Bin=b.get("inputs", {}) if isinstance(b, dict) else {}

    cfg=BridgeConfig(inputs_A=dict(Ain), inputs_B=dict(Bin), vars=list(args.vars), n_steps=args.n_steps, max_bisect_depth=args.max_bisect_depth)
    rep=run_bridge(cfg)
    cert=bridge_certificate(rep, baseline_inputs_sha256="")
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"bridge_report_v146.json").write_text(json.dumps(rep, indent=2, sort_keys=True, default=str), encoding="utf-8")
    (outp/"bridge_certificate_v146.json").write_text(json.dumps(cert, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"bridge_certificate_v146.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
