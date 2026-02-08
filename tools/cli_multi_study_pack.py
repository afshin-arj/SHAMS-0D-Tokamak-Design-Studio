from __future__ import annotations
"""CLI: Multi-Study Comparison Pack (v155)

Example:
  python -m tools.cli_multi_study_pack --packs pack1.zip pack2.zip --outdir out_multi
"""

import argparse
from pathlib import Path
from tools.multi_study_pack import build_multi_study_pack

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--packs", nargs="+", required=True)
    ap.add_argument("--outdir", default="out_multi_v155")
    args=ap.parse_args()

    packs=[]
    for p in args.packs:
        b=Path(p).read_bytes()
        packs.append((Path(p).name, b))

    bun=build_multi_study_pack(packs, policy={"source":"cli"})
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"multi_study_pack_v155.zip").write_bytes(bun["zip_bytes"])
    print("Wrote", outp/"multi_study_pack_v155.zip")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
