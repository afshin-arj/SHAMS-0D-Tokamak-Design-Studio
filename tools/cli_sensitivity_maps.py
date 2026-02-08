from __future__ import annotations
"""CLI: Sensitivity Maps (v140)

Example:
  python -m tools.cli_sensitivity_maps --baseline artifact.json --vars Ip_MA kappa q95 --max_rel 0.4 --outdir out_sens
"""

import argparse, json
from pathlib import Path
from tools.sensitivity_maps import SensitivityConfig, run_sensitivity, build_sensitivity_bundle

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, help="Path to run artifact JSON with inputs")
    ap.add_argument("--vars", nargs="+", required=True)
    ap.add_argument("--max_rel", type=float, default=0.4)
    ap.add_argument("--max_abs", type=float, default=0.0)
    ap.add_argument("--n_expand", type=int, default=8)
    ap.add_argument("--n_bisect", type=int, default=10)
    ap.add_argument("--outdir", default="out_sensitivity_v140")
    args = ap.parse_args()

    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    baseline_inputs = base.get("inputs", {}) if isinstance(base, dict) else {}
    if not isinstance(baseline_inputs, dict):
        raise SystemExit("baseline must contain inputs dict")

    cfg = SensitivityConfig(
        baseline_inputs=baseline_inputs,
        fixed_overrides={},
        vars=list(args.vars),
        bounds={},
        max_rel=float(args.max_rel),
        max_abs=float(args.max_abs),
        n_expand=int(args.n_expand),
        n_bisect=int(args.n_bisect),
        require_baseline_feasible=True,
    )
    rep = run_sensitivity(cfg)
    bun = build_sensitivity_bundle(rep)

    outp = Path(args.outdir); outp.mkdir(parents=True, exist_ok=True)
    (outp/"sensitivity_bundle_v140.zip").write_bytes(bun["zip_bytes"])
    (outp/"sensitivity_report_v140.json").write_text(json.dumps(rep, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print("Wrote", outp/"sensitivity_bundle_v140.zip")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
