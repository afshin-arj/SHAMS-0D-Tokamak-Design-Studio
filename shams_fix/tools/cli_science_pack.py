from __future__ import annotations
"""CLI for Feasibility Science Pack (v107)

Builds feasibility_science_pack.zip from three JSON artifacts.

Usage:
    python -m tools.cli_science_pack \
        --outdir out_science_pack \
        --topology out/feasible_topology.json \
        --dominance out/constraint_dominance_report.json \
        --failures out/failure_taxonomy_report.json
"""

import argparse
import json
from pathlib import Path

from tools.science_pack import build_feasibility_science_pack

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="out_science_pack")
    ap.add_argument("--topology", required=True)
    ap.add_argument("--dominance", required=True)
    ap.add_argument("--failures", required=True)
    ap.add_argument("--version", default="v107")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    topo = json.loads(Path(args.topology).read_text(encoding="utf-8"))
    dom = json.loads(Path(args.dominance).read_text(encoding="utf-8"))
    fail = json.loads(Path(args.failures).read_text(encoding="utf-8"))

    pack = build_feasibility_science_pack(
        topology=topo,
        dominance=dom,
        failures=fail,
        version=str(args.version),
    )

    (outdir / "feasibility_science_pack.zip").write_bytes(pack["zip_bytes"])
    (outdir / "feasibility_science_pack_summary.json").write_text(
        json.dumps(pack["summary"], indent=2, sort_keys=True), encoding="utf-8"
    )

    manifest = dict(pack)
    manifest.pop("zip_bytes", None)
    (outdir / "science_pack_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    print("Wrote:", outdir / "feasibility_science_pack.zip")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
