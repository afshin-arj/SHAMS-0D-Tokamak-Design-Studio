from __future__ import annotations
"""CLI: Build Design Handoff Pack (v116)

Usage:
  python -m tools.cli_handoff_pack --artifact artifact.json --outdir out_handoff

Outputs:
- handoff_pack.zip
- handoff_pack_manifest.json
"""

import argparse
import json
from pathlib import Path
from tools.handoff_pack import build_handoff_pack

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True, help="Path to shams_run_artifact.json")
    ap.add_argument("--outdir", default="out_handoff_pack")
    args = ap.parse_args()

    art = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
    pack = build_handoff_pack(artifact=art, version="v116")
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "handoff_pack.zip").write_bytes(pack["zip_bytes"])
    (outdir / "handoff_pack_manifest.json").write_text(json.dumps(pack["manifest"], indent=2, sort_keys=True), encoding="utf-8")
    print("Wrote", outdir / "handoff_pack.zip")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
