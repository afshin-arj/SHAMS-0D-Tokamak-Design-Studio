from __future__ import annotations
"""CLI: Feasibility Authority Certificate (v160)

Example:
  python -m tools.cli_feasibility_authority_certificate --field feasibility_field_v156.json --claim excluded_region --statement "..." --outdir out_cert
"""

import argparse, json
from pathlib import Path
from tools.feasibility_authority_certificate import issue_certificate_from_field

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--field", required=True)
    ap.add_argument("--claim", required=True, choices=["feasible_region","excluded_region","boundary_surface","completion_existence"])
    ap.add_argument("--statement", required=True)
    ap.add_argument("--outdir", default="out_feasibility_authority_v160")
    ap.add_argument("--confidence", default="0.95")
    ap.add_argument("--grade", default="B")
    args=ap.parse_args()

    field=json.loads(Path(args.field).read_text(encoding="utf-8"))
    cert=issue_certificate_from_field(field=field, claim_type=args.claim, statement=args.statement,
                                      confidence_level=float(args.confidence), confidence_grade=args.grade, policy={"source":"cli"})
    outp=Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"feasibility_authority_certificate_v160.json").write_text(json.dumps(cert, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"feasibility_authority_certificate_v160.json")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
