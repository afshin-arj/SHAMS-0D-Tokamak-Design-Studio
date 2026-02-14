from __future__ import annotations
"""CLI: Authority Pack (v119)

Usage:
  python -m tools.cli_authority_pack --outdir out_auth
  python -m tools.cli_authority_pack --outdir out_auth --audit_pack audit_pack.zip --downstream optimizer_downstream_bundle_v118.zip --handoff handoff_pack.zip

Outputs:
- authority_pack_v119.zip
- authority_pack_manifest_v119.json
"""

import argparse, json
from pathlib import Path
from tools.authority_pack import build_authority_pack

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="out_authority_pack")
    ap.add_argument("--audit_pack", default=None)
    ap.add_argument("--downstream", default=None)
    ap.add_argument("--handoff", default=None)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    audit = Path(args.audit_pack).read_bytes() if args.audit_pack else None
    down = Path(args.downstream).read_bytes() if args.downstream else None
    hand = Path(args.handoff).read_bytes() if args.handoff else None

    pack = build_authority_pack(repo_root=".", version="v119", audit_pack_zip=audit, downstream_bundle_zip=down, handoff_pack_zip=hand)
    (outdir / "authority_pack_v119.zip").write_bytes(pack["zip_bytes"])
    (outdir / "authority_pack_manifest_v119.json").write_text(json.dumps(pack["manifest"], indent=2, sort_keys=True), encoding="utf-8")
    print("Wrote", outdir / "authority_pack_v119.zip")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
