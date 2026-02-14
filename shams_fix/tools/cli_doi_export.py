from __future__ import annotations
"""CLI: DOI Export Helper (v153)

Example:
  python -m tools.cli_doi_export --registry study_registry_v149.json --outdir out_doi
"""

import argparse, json
from pathlib import Path
from tools.doi_export import zenodo_metadata_from_registry, crossref_minimal_from_registry

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--outdir", default="out_doi_v153")
    ap.add_argument("--communities", default="")
    ap.add_argument("--keywords", default="")
    ap.add_argument("--doi", default="")
    ap.add_argument("--publisher", default="SHAMS")
    ap.add_argument("--url", default="")
    args=ap.parse_args()

    reg=json.loads(Path(args.registry).read_text(encoding="utf-8"))
    comm=[c.strip() for c in args.communities.split(",") if c.strip()] if args.communities else []
    kws=[k.strip() for k in args.keywords.split(",") if k.strip()] if args.keywords else []

    zen=zenodo_metadata_from_registry(reg, communities=comm, keywords=kws)
    cr=crossref_minimal_from_registry(reg, doi=args.doi, publisher=args.publisher, resource_url=args.url)

    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"zenodo_metadata_v153.json").write_text(json.dumps(zen, indent=2, sort_keys=True, default=str), encoding="utf-8")
    (outp/"crossref_minimal_v153.json").write_text(json.dumps(cr, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"zenodo_metadata_v153.json")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
