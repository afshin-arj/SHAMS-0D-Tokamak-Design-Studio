from __future__ import annotations
"""CLI: Citation bundle v168

Example:
  python -m tools.cli_citation_v168 --protocol study_protocol_v165.json --lock repro_lock_v166.json --manifest authority_pack_manifest_v167.json --outdir out_v168
"""

import argparse, json
from pathlib import Path
from tools.citation_v168 import build_citation_bundle

def _load(p: str):
    if not p:
        return None
    return json.loads(Path(p).read_text(encoding="utf-8"))

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--lock", default=None)
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--pack_sha", default=None)
    ap.add_argument("--metadata", default=None)
    ap.add_argument("--outdir", default="out_citation_v168")
    args=ap.parse_args()

    meta=_load(args.metadata) if args.metadata else {}
    res=build_citation_bundle(
        study_protocol_v165=_load(args.protocol),
        repro_lock_v166=_load(args.lock) if args.lock else None,
        authority_pack_manifest_v167=_load(args.manifest) if args.manifest else None,
        authority_pack_zip_sha256=args.pack_sha,
        metadata=meta,
    )
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"citation_bundle_v168.json").write_text(json.dumps(res, indent=2, sort_keys=True, default=str), encoding="utf-8")
    (outp/"CITATION.cff").write_text(res["payload"]["citation_cff_text"], encoding="utf-8")
    (outp/"study_citation_v168.bib").write_text(res["payload"]["bibtex_text"], encoding="utf-8")
    (outp/"study_reference_v168.md").write_text(res["payload"]["reference_markdown"], encoding="utf-8")
    print("Wrote", outp/"citation_bundle_v168.json")
    print("Wrote", outp/"CITATION.cff")
    print("Wrote", outp/"study_citation_v168.bib")
    print("Wrote", outp/"study_reference_v168.md")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
