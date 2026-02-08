from __future__ import annotations
"""CLI: Topology Certificate (v145)

Example:
  python -m tools.cli_topology_certificate --baseline artifact.json --topology feasible_topology_v142.json --dataset deepdive_dataset_v142.json --outdir out_v145
"""

import argparse, json
from pathlib import Path
from tools.topology_certificate import generate_topology_certificate

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--topology", required=True)
    ap.add_argument("--dataset", default="")
    ap.add_argument("--policy_json", default="")
    ap.add_argument("--outdir", default="out_topology_certificate_v145")
    args = ap.parse_args()

    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    topo = json.loads(Path(args.topology).read_text(encoding="utf-8"))
    ds = json.loads(Path(args.dataset).read_text(encoding="utf-8")) if args.dataset else None
    policy = json.loads(args.policy_json) if args.policy_json else {}

    cert = generate_topology_certificate(base, topo, deepdive_dataset=ds, policy=policy)
    outp = Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"topology_certificate_v145.json").write_text(json.dumps(cert, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"topology_certificate_v145.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
