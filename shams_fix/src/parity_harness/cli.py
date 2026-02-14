from __future__ import annotations

"""CLI entrypoint for PROCESS Benchmark & Parity Harness 3.0 (v364.0).

Usage:
  python -m src.parity_harness.cli run --suite v364 --cases_dir benchmarks/cases --out_dir bench_out

Optionally include PROCESS outputs:
  python -m src.parity_harness.cli run --suite v364 --process_dir process_outputs --out_dir bench_out

Where process_outputs may contain JSON files named <suite>_<case_id>.json
with schema:
  {
    "schema": "process_outputs.v1",
    "outputs": { ... },
    "kpis": { ... },
    "constraint_margins": { "name": margin, ... }
  }

© 2026 Afshin Arjhangmehr
"""

import argparse
from pathlib import Path

from .runner import run_benchmark_suite


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="shams-benchmarks")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="Run benchmark suite")
    pr.add_argument("--suite", required=True, type=str)
    pr.add_argument("--cases_dir", default="benchmarks/cases", type=str)
    pr.add_argument("--out_dir", default="bench_out", type=str)
    pr.add_argument("--process_dir", default=None, type=str)
    pr.add_argument("--profile_contract_preset", default="C16", type=str)
    pr.add_argument("--profile_contract_tier", default="robust", type=str)
    pr.add_argument("--include_full_artifact", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    p = _build_parser()
    args = p.parse_args(argv)

    if args.cmd == "run":
        run_benchmark_suite(
            suite=str(args.suite),
            cases_dir=Path(str(args.cases_dir)),
            out_dir=Path(str(args.out_dir)),
            process_dir=Path(str(args.process_dir)) if args.process_dir else None,
            profile_contract_preset=str(args.profile_contract_preset),
            profile_contract_tier=str(args.profile_contract_tier),
            include_full_artifact=bool(args.include_full_artifact),
        )
        return 0

    raise SystemExit(2)


if __name__ == "__main__":
    raise SystemExit(main())
