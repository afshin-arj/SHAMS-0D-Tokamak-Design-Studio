from __future__ import annotations
"""CLI: Completion Pack (v163)

Example:
  python -m tools.cli_completion_pack --v159 v159.json --v161 v161.json --v162 v162.json --outdir out_v163
"""

import argparse, json
from pathlib import Path
from tools.completion_pack import build_completion_pack, render_completion_pack_markdown

def _load(p: str):
    if not p:
        return None
    return json.loads(Path(p).read_text(encoding="utf-8"))

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--v159", default=None)
    ap.add_argument("--v161", default=None)
    ap.add_argument("--v162", default=None)
    ap.add_argument("--tighten", type=float, default=0.25)
    ap.add_argument("--outdir", default="out_completion_pack_v163")
    args=ap.parse_args()

    pack=build_completion_pack(
        v159=_load(args.v159),
        v161=_load(args.v161),
        v162=_load(args.v162),
        policy={"generator":"cli", "tighten": float(args.tighten)},
    )
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"completion_pack_v163.json").write_text(json.dumps(pack, indent=2, sort_keys=True, default=str), encoding="utf-8")
    (outp/"completion_pack_summary_v163.md").write_text(render_completion_pack_markdown(pack), encoding="utf-8")
    print("Wrote", outp/"completion_pack_v163.json")
    print("Wrote", outp/"completion_pack_summary_v163.md")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
