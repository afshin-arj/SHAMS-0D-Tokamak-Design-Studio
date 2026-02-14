#!/usr/bin/env python
"""Batch runner for SHAMS studies (headless).

Usage:
  python tools/batch_run.py --study path/to/study.json --outdir results/

The study.json is the same format exported by the Streamlit Studies tab.
Each run writes a shams_run_artifact.json into outdir/run_<N>/.
"""
from __future__ import annotations
import argparse, json, os, pathlib
from typing import Any, Dict

from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from constraints.constraints import evaluate_constraints
from shams_io.run_artifact import build_run_artifact, write_run_artifact

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", required=True, help="Path to a study config JSON exported by the UI.")
    ap.add_argument("--outdir", required=True, help="Output directory for artifacts.")
    args = ap.parse_args()

    study = json.loads(pathlib.Path(args.study).read_text(encoding="utf-8"))
    runs = study.get("runs", [])
    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    for i, run in enumerate(runs):
        inp_dict = run.get("inputs", run)
        inp = PointInputs(**inp_dict)
        out = hot_ion_point(inp)
        cons = evaluate_constraints(out)
        artifact = build_run_artifact(inputs=dict(inp.__dict__), outputs=dict(out), constraints=cons,
                                   meta={"label": run.get("name", f"run_{i}") , "mode":"batch"},
                                   solver={"message":"batch_run"},
                                   economics=dict((out or {}).get("_economics", {})))
        run_dir = outdir / f"run_{i:04d}"
        run_dir.mkdir(parents=True, exist_ok=True)
        write_run_artifact(artifact, run_dir / "shams_run_artifact.json")

    print(f"Wrote {len(runs)} artifacts into {outdir}")

if __name__ == "__main__":
    main()
