from __future__ import annotations
"""Plot Boundary Atlas v2 (v110)

Generates PNG/SVG plots for each slice in a boundary_atlas_v2 report.
Uses matplotlib defaults (audit friendly).

Usage:
    python -m tools.plot_boundary_atlas_v2 --atlas boundary_atlas_v2.json --outdir out_boundary_plots
"""

import argparse
import json
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--atlas", required=True)
    ap.add_argument("--outdir", default="out_boundary_plots")
    args = ap.parse_args()

    atlas = json.loads(Path(args.atlas).read_text(encoding="utf-8"))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    import matplotlib.pyplot as plt

    slices = atlas.get("slices", [])
    if not isinstance(slices, list) or not slices:
        print("No slices to plot.")
        return 0

    for i, sl in enumerate(slices):
        if not isinstance(sl, dict):
            continue
        kx = sl.get("lever_x"); ky = sl.get("lever_y")
        lines = sl.get("boundary_polylines", [])
        if not (isinstance(kx, str) and isinstance(ky, str) and isinstance(lines, list)):
            continue

        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.set_xlabel(kx)
        ax.set_ylabel(ky)
        ax.set_title(f"Boundary Atlas v2: {kx} vs {ky}")

        # plot lines
        for line in lines[:12]:
            if not isinstance(line, list) or len(line) < 2:
                continue
            xs = [p.get(kx) for p in line if isinstance(p, dict) and (kx in p) and (ky in p)]
            ys = [p.get(ky) for p in line if isinstance(p, dict) and (kx in p) and (ky in p)]
            if len(xs) >= 2 and len(ys) >= 2:
                ax.plot(xs, ys, linewidth=1.5)

        png = outdir / f"boundary_{i+1:02d}_{kx}_vs_{ky}.png"
        svg = outdir / f"boundary_{i+1:02d}_{kx}_vs_{ky}.svg"
        fig.tight_layout()
        fig.savefig(png, dpi=200)
        fig.savefig(svg)
        plt.close(fig)

    print("Wrote plots to", outdir)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
