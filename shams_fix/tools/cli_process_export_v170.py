from __future__ import annotations
"""CLI: SHAMS → PROCESS export v170

Example:
  python -m tools.cli_process_export_v170 --run run_artifact.json --completion completion_pack_v163.json --citation citation_bundle_v168.json --outdir out_v170
"""

import argparse, json
from pathlib import Path
from tools.process_export_v170 import build_process_export_pack

def _load(p: str):
    if not p:
        return None
    return json.loads(Path(p).read_text(encoding="utf-8"))

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--completion", default=None)
    ap.add_argument("--citation", default=None)
    ap.add_argument("--outdir", default="out_process_export_v170")
    args=ap.parse_args()

    res=build_process_export_pack(
        run_artifact=_load(args.run),
        completion_pack_v163=_load(args.completion) if args.completion else None,
        citation_bundle_v168=_load(args.citation) if args.citation else None,
        policy={"generator":"cli"},
    )
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"process_export_pack_v170.zip").write_bytes(res["zip_bytes"])
    (outp/"process_export_manifest_v170.json").write_text(json.dumps(res["manifest"], indent=2, sort_keys=True, default=str), encoding="utf-8")
    (outp/"process_export_meta_v170.json").write_text(json.dumps(res["pack"], indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"process_export_pack_v170.zip")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
