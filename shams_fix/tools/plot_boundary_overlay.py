from __future__ import annotations
"""Plot Boundary Atlas v2 with Literature Overlay (v112)

Usage:
  python -m tools.plot_boundary_overlay --atlas boundary_atlas_v2.json --overlay literature_points.json --outdir out_overlay

Produces PNG/SVG per slice with boundary polylines + overlay points (labels in legend).
"""

import argparse
import json
from pathlib import Path

from tools.literature_overlay import validate_literature_points, extract_xy_points

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--atlas", required=True)
    ap.add_argument("--overlay", required=True)
    ap.add_argument("--outdir", default="out_boundary_overlay")
    args = ap.parse_args()

    atlas = json.loads(Path(args.atlas).read_text(encoding="utf-8"))
    overlay = json.loads(Path(args.overlay).read_text(encoding="utf-8"))
    errs = validate_literature_points(overlay)
    if errs:
        print("Overlay validation warnings:", errs[:20])

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
        ax.set_title(f"Boundary + Overlay: {kx} vs {ky}")

        # plot boundary polylines
        for line in lines[:12]:
            if not isinstance(line, list) or len(line) < 2:
                continue
            xs = [p.get(kx) for p in line if isinstance(p, dict) and (kx in p) and (ky in p)]
            ys = [p.get(ky) for p in line if isinstance(p, dict) and (kx in p) and (ky in p)]
            if len(xs) >= 2 and len(ys) >= 2:
                ax.plot(xs, ys, linewidth=1.5)

        # overlay points
        pts = extract_xy_points(overlay, kx, ky)
        if pts:
            xs = [p[kx] for p in pts]
            ys = [p[ky] for p in pts]
            ax.scatter(xs, ys, s=25, marker="o")
            # add small text labels (avoid clutter by limiting)
            for p in pts[:15]:
                ax.text(p[kx], p[ky], str(p["name"])[:18], fontsize=7)

        fig.tight_layout()
        png = outdir / f"boundary_overlay_{i+1:02d}_{kx}_vs_{ky}.png"
        svg = outdir / f"boundary_overlay_{i+1:02d}_{kx}_vs_{ky}.svg"
        fig.savefig(png, dpi=200)
        fig.savefig(svg)
        plt.close(fig)

    print("Wrote overlay plots to", outdir)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
