from __future__ import annotations
"""CLI: FC Advanced (v134–v138)

Build atlas from fc_report_v133.json:
  python -m tools.cli_fc_advanced --fc_report fc_report_v133.json --atlas R0_m Bt_T --outdir out_fc_adv

Compress feasible set:
  python -m tools.cli_fc_advanced --fc_report fc_report_v133.json --compress 25

"""

import argparse, json
from pathlib import Path
from tools.fc_advanced import build_fc_atlas_bundle, compress_feasible_set

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fc_report", required=True)
    ap.add_argument("--outdir", default="out_fc_advanced_v138")
    ap.add_argument("--atlas", nargs=2, metavar=("X","Y"), default=None)
    ap.add_argument("--compress", type=int, default=0)
    args = ap.parse_args()

    rep = json.loads(Path(args.fc_report).read_text(encoding="utf-8"))
    outp = Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)

    if args.atlas:
        x,y = args.atlas
        bun = build_fc_atlas_bundle(rep, x_var=x, y_var=y)
        (outp/"fc_atlas_v134.zip").write_bytes(bun["zip_bytes"])
        (outp/"fc_atlas_manifest_v134.json").write_text(json.dumps(bun["manifest"], indent=2, sort_keys=True), encoding="utf-8")
        print("Wrote", outp/"fc_atlas_v134.zip")

    if args.compress and args.compress > 0:
        comp = compress_feasible_set(rep, k=int(args.compress))
        (outp/"fc_compressed_v137.json").write_text(json.dumps(comp, indent=2, sort_keys=True), encoding="utf-8")
        print("Wrote", outp/"fc_compressed_v137.json")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
