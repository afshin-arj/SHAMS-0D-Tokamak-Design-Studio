#!/usr/bin/env python
from __future__ import annotations
import argparse
from pathlib import Path
import sys, json

# Add src to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shams_io.run_artifact import read_run_artifact
from shams_io.plotting import plot_summary_pdf

def main():
    ap = argparse.ArgumentParser(description="Generate a SHAMS summary PDF from a run artifact JSON (PROCESS-inspired).")
    ap.add_argument("-f", "--file", required=True, help="Path to shams_run_artifact.json")
    ap.add_argument("-o", "--out", default="shams_summary.pdf", help="Output PDF path")
    args = ap.parse_args()

    art = read_run_artifact(args.file)
    out = plot_summary_pdf(art, args.out)
    print(f"Wrote {out}")

if __name__ == "__main__":
    main()
