from __future__ import annotations

"""Campaign CLI (v363.0).

Usage
-----
python -m src.campaign.cli export --campaign campaigns/my_campaign.json --out out.zip
python -m src.campaign.cli eval --campaign campaigns/my_campaign.json --in candidates.csv --out results.jsonl

This CLI is intentionally minimal and deterministic.

© 2026 Afshin Arjhangmehr
"""

import argparse
from pathlib import Path
import sys

from .spec import load_campaign_spec
from .generate import generate_candidates
from .export import export_campaign_bundle
from .eval import read_candidates_csv, evaluate_campaign_candidates, write_results_jsonl


def _cmd_export(args: argparse.Namespace) -> int:
    spec = load_campaign_spec(Path(args.campaign))
    cands = generate_candidates(spec)
    zip_path = export_campaign_bundle(spec, candidates=cands, out_zip=Path(args.out))
    print(str(zip_path))
    return 0


def _cmd_eval(args: argparse.Namespace) -> int:
    spec = load_campaign_spec(Path(args.campaign))
    rows = read_candidates_csv(Path(args.input))
    results = evaluate_campaign_candidates(spec, rows)
    write_results_jsonl(results, Path(args.out))
    print(str(Path(args.out)))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="shams-campaign", add_help=True)
    sp = p.add_subparsers(dest="cmd", required=True)

    pe = sp.add_parser("export", help="Export an optimizer-ready campaign ZIP")
    pe.add_argument("--campaign", required=True, help="Path to campaign JSON")
    pe.add_argument("--out", required=True, help="Output ZIP path")
    pe.set_defaults(func=_cmd_export)

    pv = sp.add_parser("eval", help="Evaluate a candidates CSV and write results JSONL")
    pv.add_argument("--campaign", required=True, help="Path to campaign JSON")
    pv.add_argument("--in", dest="input", required=True, help="Input candidates CSV")
    pv.add_argument("--out", required=True, help="Output results JSONL")
    pv.set_defaults(func=_cmd_eval)

    ns = p.parse_args(argv)
    return int(ns.func(ns))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
