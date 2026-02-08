from __future__ import annotations
"""CLI: Paper Pack Generator (v148–v150)

Example:
  python -m tools.cli_paper_pack --artifacts out_ui_self_test/artifact.json --outdir out_paper_pack
"""

import argparse, json
from pathlib import Path
from tools.design_study_kit import PaperPackConfig, build_paper_pack

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--artifacts", nargs="+", required=True, help="Paths to run artifact json(s)")
    ap.add_argument("--title", default="SHAMS design study")
    ap.add_argument("--authors", default="")
    ap.add_argument("--description", default="")
    ap.add_argument("--shams_version", default="unknown")
    ap.add_argument("--outdir", default="out_paper_pack")
    args=ap.parse_args()

    run_arts=[]
    for p in args.artifacts:
        obj=json.loads(Path(p).read_text(encoding="utf-8"))
        run_arts.append(obj)

    cfg=PaperPackConfig(
        shams_version=args.shams_version,
        title=args.title,
        authors=[a.strip() for a in args.authors.split(",") if a.strip()] if args.authors else [],
        description=args.description,
        run_artifacts=run_arts,
        certificates=[],
        figures=[],
        tables=[],
        methods={},
        policy={"source":"cli"},
    )
    bun=build_paper_pack(cfg)
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"paper_pack_v150.zip").write_bytes(bun["zip_bytes"])
    (outp/"study_registry_v149.json").write_text(json.dumps(bun["study_registry"], indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"paper_pack_v150.zip")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
