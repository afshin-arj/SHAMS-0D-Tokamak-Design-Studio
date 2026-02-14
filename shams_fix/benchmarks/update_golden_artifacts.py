#!/usr/bin/env python
"""
Update golden benchmark references.

- Regenerates benchmarks/golden.json (curated numeric keys)
- Regenerates benchmarks/golden_artifacts/*.json (full run artifacts)
"""
from __future__ import annotations

import json
import argparse
from pathlib import Path

# Make src importable when run from repo root
import sys
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from physics.hot_ion import hot_ion_point, PointInputs
from constraints.constraints import evaluate_constraints
from shams_io.run_artifact import build_run_artifact, write_run_artifact

CURATED_KEYS = [
    "B_peak_T",
    "H98",
    "P_SOL_MW",
    "P_net_e_MW",
    "P_rad_MW",
    "betaN_proxy",
    "hts_margin",
    "q95_proxy",
    "sigma_hoop_MPa",
]

def _safe(x):
    try:
        if x is None:
            return float("nan")
        return float(x)
    except Exception:
        return float("nan")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=str, default="", help="Override output directory (defaults to benchmarks/)")
    args = ap.parse_args()

    bench_dir = Path(args.out_dir) if args.out_dir else Path(__file__).resolve().parent
    cases_path = bench_dir / "cases.json"
    if not cases_path.exists():
        raise SystemExit(f"Missing {cases_path}")

    cases_raw = json.loads(cases_path.read_text(encoding="utf-8"))
    # Normalize cases to list
    cases = []
    if isinstance(cases_raw, dict):
        for name, inp in cases_raw.items():
            if isinstance(inp, dict):
                cases.append((str(name), inp))
    elif isinstance(cases_raw, list):
        for i, c in enumerate(cases_raw):
            if isinstance(c, dict):
                name = str(c.get("name", f"case_{i}"))
                inp = c.get("inputs", c.get("inp", c.get("input", {})))
                if isinstance(inp, dict):
                    cases.append((name, inp))

    if not cases:
        raise SystemExit("No benchmark cases found.")

    baseline = dict(cases[0][1])
    def make_inp(overrides: dict) -> PointInputs:
        d = dict(baseline)
        d.update(overrides)
        return PointInputs(**d)

    curated = {}
    art_dir = bench_dir / "golden_artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)

    for name, ov in cases:
        inp = make_inp(ov)
        out = hot_ion_point(inp)
        curated[name] = {k: _safe(out.get(k)) for k in CURATED_KEYS}

        cons = [c.__dict__ for c in evaluate_constraints(out)]
        art = build_run_artifact(inp.__dict__, out, cons, meta={"source":"benchmarks","case":name,"golden":True})
        write_run_artifact(art_dir / f"{name}.json", art)

    (bench_dir / "golden.json").write_text(json.dumps(curated, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {bench_dir / 'golden.json'}")
    print(f"Wrote {len(cases)} artifacts under {art_dir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
