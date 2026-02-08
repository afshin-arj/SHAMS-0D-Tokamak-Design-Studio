from __future__ import annotations
"""CLI: UI Smoke Runner (v126)

Usage:
  python -m tools.cli_ui_smoke --outdir out_ui_smoke --scenarios render_all paper_pack
"""

import argparse, json
from pathlib import Path
from tools.ui_smoke_runner import run_smoke

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="out_ui_smoke_v126")
    ap.add_argument("--scenarios", nargs="*", default=["render_all", "paper_pack"])
    args = ap.parse_args()

    rep = run_smoke(outdir=args.outdir, scenarios=args.scenarios)
    Path(args.outdir).mkdir(parents=True, exist_ok=True)
    (Path(args.outdir) / "ui_smoke_report.json").write_text(json.dumps(rep, indent=2, sort_keys=True), encoding="utf-8")
    print("Wrote", Path(args.outdir) / "UI_SMOKE_REPORT.md")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
