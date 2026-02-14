#!/usr/bin/env python
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shams_io.run_artifact import read_run_artifact
from shams_io.sankey import write_sankey_html

def main():
    ap = argparse.ArgumentParser(description="Generate an interactive power-balance Sankey HTML from a run artifact JSON.")
    ap.add_argument("-f", "--file", required=True, help="Path to shams_run_artifact.json")
    ap.add_argument("-o", "--out", default="shams_power_balance.html", help="Output HTML path")
    args = ap.parse_args()

    art = read_run_artifact(args.file)
    out = write_sankey_html(art, args.out)
    print(f"Wrote {out}")

if __name__ == "__main__":
    main()
