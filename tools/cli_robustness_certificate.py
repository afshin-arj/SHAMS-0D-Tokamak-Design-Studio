from __future__ import annotations
"""CLI: Robustness Certificate (v141)

Example:
  python -m tools.cli_robustness_certificate \
      --feasibility feasibility_certificate_v139.json \
      --sensitivity sensitivity_report_v140.json \
      --outdir out_v141
"""

import argparse, json
from pathlib import Path
from tools.robustness_certificate import generate_robustness_certificate

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feasibility", required=True)
    ap.add_argument("--sensitivity", required=True)
    ap.add_argument("--outdir", default="out_robustness_v141")
    ap.add_argument("--policy_json", default="")
    args = ap.parse_args()

    fc = json.loads(Path(args.feasibility).read_text(encoding="utf-8"))
    sr = json.loads(Path(args.sensitivity).read_text(encoding="utf-8"))
    policy = json.loads(args.policy_json) if args.policy_json else {}

    cert = generate_robustness_certificate(fc, sr, policy=policy)
    outp = Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"robustness_certificate_v141.json").write_text(json.dumps(cert, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"robustness_certificate_v141.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
