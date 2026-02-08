from __future__ import annotations
"""CLI: Study Protocol (v165)

Example:
  python -m tools.cli_study_protocol_v165 --run_artifact run_artifact.json --outdir out_v165
"""

import argparse, json
from pathlib import Path
from tools.study_protocol_v165 import build_study_protocol, render_study_protocol_markdown

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--run_artifact", required=True, help="JSON shams_run_artifact")
    ap.add_argument("--overrides", default=None, help="Optional JSON object overrides")
    ap.add_argument("--outdir", default="out_study_protocol_v165")
    args=ap.parse_args()

    run_art=json.loads(Path(args.run_artifact).read_text(encoding="utf-8"))
    overrides=json.loads(Path(args.overrides).read_text(encoding="utf-8")) if args.overrides else {}

    prot=build_study_protocol(run_artifact=run_art, protocol_overrides=overrides)
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"study_protocol_v165.json").write_text(json.dumps(prot, indent=2, sort_keys=True, default=str), encoding="utf-8")
    (outp/"study_protocol_v165.md").write_text(render_study_protocol_markdown(prot), encoding="utf-8")
    print("Wrote", outp/"study_protocol_v165.json")
    print("Wrote", outp/"study_protocol_v165.md")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
