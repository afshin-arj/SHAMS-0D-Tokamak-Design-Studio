from __future__ import annotations

import argparse
from pathlib import Path
from studies.spec import StudySpec
from studies.runner import run_study

def main() -> int:
    ap = argparse.ArgumentParser(description="Run a SHAMS study spec (JSON or YAML) headlessly.")
    ap.add_argument("spec", help="Path to StudySpec JSON/YAML")
    ap.add_argument("--out", default="study_out", help="Output directory")
    ap.add_argument("--label-prefix", default="", help="Prefix for per-case labels")
    args = ap.parse_args()

    spec = StudySpec.from_path(args.spec)
    idx = run_study(spec, args.out, label_prefix=args.label_prefix)
    print(f"Wrote {idx['n_cases']} cases to {Path(args.out).resolve()}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
