from __future__ import annotations
"""CLI: Write demo artifacts to disk (v172)

Example:
  python -m tools.cli_demo_seed_v172 --outdir out_demo_v172
"""

import argparse, json
from pathlib import Path
from tools.demo_seed_v172 import build_demo_bundle

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--outdir", default="out_demo_v172")
    args=ap.parse_args()
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    b=build_demo_bundle()
    for k,v in b.items():
        (outp/f"{k}_demo_v172.json").write_text(json.dumps(v, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote demo bundle to", outp)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
