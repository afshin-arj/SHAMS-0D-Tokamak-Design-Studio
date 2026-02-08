from __future__ import annotations
"""
Offline figure verification (v91):
- Generates radial build PNG/SVG from a dummy artifact
- Ensures files exist and are non-trivial size
"""
import argparse, json, os
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="out_verify_figures")
    args = ap.parse_args()
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    dummy = {
        "kind": "shams_run_artifact",
        "version": "dummy",
        "timestamp": "dummy",
        "inputs": {"R0": 3.0, "a": 1.0},
        "outputs": {"Q": 10.0},
        # include minimal radial build fields expected by plotting (best-effort; plotting may skip if missing)
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

    from src.shams_io.plotting import plot_radial_build_dual_export
    produced = plot_radial_build_dual_export(dummy, str(out / "radial_build"))
    # Verify
    ok = True
    for k, p in produced.items():
        size = Path(p).stat().st_size if Path(p).exists() else 0
        if size < 500:
            ok = False
            print("FAIL:", k, p, "size", size)
        else:
            print("OK:", k, p, "size", size)
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
