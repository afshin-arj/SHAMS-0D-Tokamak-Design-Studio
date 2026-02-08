from __future__ import annotations
"""CLI: Authority Pack v167

Example:
  python -m tools.cli_authority_pack_v167 --run run_artifact.json --protocol study_protocol_v165.json --lock repro_lock_v166.json --replay replay_report_v166.json --completion completion_pack_v163.json --sens sensitivity_v164.json --outdir out_v167
"""

import argparse, json
from pathlib import Path
from tools.authority_pack_v167 import build_authority_pack

def _load(p: str):
    if not p:
        return None
    return json.loads(Path(p).read_text(encoding="utf-8"))

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--run", default=None)
    ap.add_argument("--protocol", default=None)
    ap.add_argument("--lock", default=None)
    ap.add_argument("--replay", default=None)
    ap.add_argument("--completion", default=None)
    ap.add_argument("--sens", default=None)
    ap.add_argument("--cert", default=None)
    ap.add_argument("--outdir", default="out_authority_pack_v167")
    args=ap.parse_args()

    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    res=build_authority_pack(
        run_artifact=_load(args.run),
        study_protocol_v165=_load(args.protocol),
        repro_lock_v166=_load(args.lock),
        replay_report_v166=_load(args.replay),
        completion_pack_v163=_load(args.completion),
        sensitivity_v164=_load(args.sens),
        certificate_v160=_load(args.cert),
        policy={"generator":"cli"},
    )
    (outp/"authority_pack_v167.zip").write_bytes(res["zip_bytes"])
    (outp/"authority_pack_manifest_v167.json").write_text(json.dumps(res["manifest"], indent=2, sort_keys=True, default=str), encoding="utf-8")
    (outp/"authority_pack_meta_v167.json").write_text(json.dumps(res["pack"], indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"authority_pack_v167.zip")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
