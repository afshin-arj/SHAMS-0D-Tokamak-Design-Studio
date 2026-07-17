#!/usr/bin/env python
"""Run Independence Phase 3.3 champion cases and emit artifacts + summary.

Usage (from SHAMS-0D repo root)::

    python benchmarks/champions/run_champions.py
    python benchmarks/champions/run_champions.py --outdir benchmarks/champions/out

Does not change L0 physics. Does not invent PROCESS MFILE numbers.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from studies.champion_cases import DEFAULT_CASES_PATH, write_champion_pack  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SHAMS champion feasibility cases (Phase 3.3)")
    p.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES_PATH,
        help="Path to champion cases JSON",
    )
    p.add_argument(
        "--outdir",
        type=Path,
        default=ROOT / "benchmarks" / "champions" / "out",
        help="Output directory for summary.json + artifacts/",
    )
    args = p.parse_args(argv)

    pack = write_champion_pack(args.outdir, cases_path=args.cases)
    print(json.dumps(
        {
            "outdir": str(args.outdir),
            "n_cases": pack["n_cases"],
            "n_hard_feasible": pack["n_hard_feasible"],
            "n_infeasible": pack["n_infeasible"],
            "pack_sha256": pack["pack_sha256"],
            "shams_version": pack["shams_version"],
            "cases": [
                {
                    "case_id": s["case_id"],
                    "hard_feasible": s["hard_feasible"],
                    "dominant_mechanism": s.get("dominant_mechanism"),
                    "dominant_constraint": s.get("dominant_constraint"),
                    "citation_sha256": s["citation_sha256"],
                }
                for s in pack["cases"]
            ],
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
