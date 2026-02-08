from __future__ import annotations
"""CLI: Atlas Pack v169

Example:
  python -m tools.cli_atlas_v169 --sensitivity sensitivity_v164.json --outdir out_v169
"""

import argparse, json
from pathlib import Path
from tools.atlas_v169 import build_atlas_pack

def _load(p: str):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--sensitivity", required=True, help="sensitivity_v164.json")
    ap.add_argument("--outdir", default="out_atlas_v169")
    args=ap.parse_args()

    sens=_load(args.sensitivity)
    res=build_atlas_pack(sensitivity_v164=sens, policy={"generator":"cli"})
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"atlas_pack_v169.zip").write_bytes(res["zip_bytes"])
    (outp/"atlas_manifest_v169.json").write_text(json.dumps(res["manifest"], indent=2, sort_keys=True, default=str), encoding="utf-8")
    (outp/"atlas_meta_v169.json").write_text(json.dumps(res["pack"], indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"atlas_pack_v169.zip")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
