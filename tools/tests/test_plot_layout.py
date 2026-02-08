from __future__ import annotations
"""Deterministic plot layout test (offline) — v92

Usage:
  python -m tools.tests.test_plot_layout --outdir out_plot_tests
"""
import argparse
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="out_plot_tests")
    args = ap.parse_args()
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    dummy = {
        "kind": "shams_run_artifact",
        "version": "dummy",
        "timestamp": "dummy",
        "inputs": {"R0": 3.0, "a": 1.0},
        "outputs": {"Q": 10.0},
        "radial_build": {
            "segments": [
                {"name": "Gap", "thickness": 0.08},
                {"name": "Vacuum vessel", "thickness": 0.05},
                {"name": "Shield", "thickness": 0.75},
                {"name": "Blanket", "thickness": 0.5},
                {"name": "First wall", "thickness": 0.06},
                {"name": "TF winding pack", "thickness": 0.10},
                {"name": "TF structure", "thickness": 0.25},
            ],
            "R0_minus_a": 1.28,
            "spent": 1.65,
            "R_coil_inner": -0.12,
            "feasible": False,
        },
        "constraints": [{"name": "dummy_constraint", "signed_margin": 0.1}],
        "meta": {"constraint_set_hash": "dummy"}
    }

    from src.shams_io.plotting import plot_radial_build_from_artifact
    ok = True
    for dpi in (120, 180, 240, 300):
        png = out / f"radial_build_dpi{dpi}.png"
        try:
            plot_radial_build_from_artifact(dummy, str(png))
        except Exception as e:
            print("FAIL exception dpi", dpi, repr(e))
            ok = False
            continue
        size = png.stat().st_size if png.exists() else 0
        if size < 500:
            print("FAIL size dpi", dpi, size)
            ok = False
        else:
            print("OK dpi", dpi, "size", size)
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
