from __future__ import annotations
"""CLI for PROCESS downstream export (v108)

Builds process_downstream_bundle.zip from a list of SHAMS run artifact JSON files.

Usage:
    python -m tools.cli_process_downstream --outdir out_process --artifact artifact1.json --artifact artifact2.json
"""

import argparse
import json
from pathlib import Path

from tools.process_downstream import build_process_downstream_bundle

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="out_process_downstream")
    ap.add_argument("--artifact", action="append", required=True, help="Path to a shams_run_artifact JSON file")
    ap.add_argument("--version", default="v108")
    args = ap.parse_args()

    payloads = []
    for p in args.artifact:
        payloads.append(json.loads(Path(p).read_text(encoding="utf-8")))

    pack = build_process_downstream_bundle(payloads, version=str(args.version))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "process_downstream_bundle.zip").write_bytes(pack["zip_bytes"])

    manifest = dict(pack)
    manifest.pop("zip_bytes", None)
    (outdir / "process_downstream_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print("Wrote:", outdir / "process_downstream_bundle.zip")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
