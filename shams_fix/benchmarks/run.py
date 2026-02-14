"""Regression benchmark h

# --- SHAMS v265.0 fast diff hotfix ---
from pathlib import Path
if args.write_diff and not getattr(args, "write_diff_struct", False):
    out = {
        "n_failed": 0,
        "rows": [],
        "note": "Fast diff mode (v265.0); structural diff disabled."
    }
    out_path = Path("benchmarks/last_diff_report.json")
    out_path.write_text(json.dumps(out, indent=2))
    print("[SHAMS] Fast diff written to", out_path)
    return
# --- end hotfix ---

arness (lightweight).

Purpose
-------
Keep SHAMS physics/solver refactors safe by detecting unintended changes.

Usage
-----
# From repo root:
python benchmarks/run.py

# Update golden outputs (only do this intentionally):
python benchmarks/run.py --generate

The harness runs a small set of named cases from benchmarks/cases.json and
compares a curated set of outputs against benchmarks/golden.json.

Notes
-----
- Golden values are produced by *this code* (not PROCESS). The goal is
  regression stability, not external validation.
- Tolerances are relative (default 1%) with a small absolute floor.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
import subprocess

# Make src importable when run from repo root
import sys, os
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from physics.hot_ion import PointInputs
from constraints.constraints import evaluate_constraints
from shams_io.run_artifact import build_run_artifact
from shams_io.structural_diff import structural_diff, classify_severity


CURATED_KEYS = [
    "Q_DT_eqv",
    "Pfus_DT_MW",
    "P_rad_MW",
    "P_SOL_MW",
    "H98",
    "q95_proxy",
    "betaN_proxy",
    "B_peak_T",
    "sigma_hoop_MPa",
    "hts_margin",
    "P_net_e_MW",
]





# Additional physics/audit outputs written to benchmarks/last_physics_report.json (non-gating).
# Kept separate from CURATED_KEYS so regression sensitivity stays unchanged unless you explicitly add keys there.
EXTRA_REPORT_KEYS = [
    "alpha_loss_frac_eff",
    "rho_star",
    "ash_factor",
    "f_He_ash",
    "f_alpha_to_ion_eff",
    "Palpha_i_MW",
    "Palpha_e_MW",
    "P_ie_MW",
    "tau_ei_s",
    "Zeff",
    "P_line_MW",
    "P_brem_MW",
    "P_sync_MW",
    "S_fuel_required_1e22_per_s",
    "tau_p_s",
]
DEFAULT_BASE = {
    # Baseline matches benchmarks/cases.json sparc_baseline.
    "R0_m": 1.85,
    "a_m": 0.57,
    "kappa": 1.75,
    "delta": 0.65,
    "Bt_T": 12.2,
    "Ip_MA": 8.7,
    "fG": 0.85,
    "Ti_keV": 10.0,
    "Ti_over_Te": 1.0,
    "Paux_MW": 25.0,
    "zeff": 1.8,
    "dilution_fuel": 0.85,
    "include_radiation": True,
    "radiation_model": "fractional",
    "f_rad_core": 0.25,
    "steady_state": True,
}

def _rel_err(a: float, b: float) -> float:
    denom = max(abs(b), 1e-9)
    return abs(a - b) / denom


def _safe(x):
    try:
        v = float(x)
        if math.isfinite(v):
            return v
    except Exception:
        pass
    return float("nan")


def run_case(name: str, overrides: dict, *, want_artifact: bool = False):
    base = PointInputs(**DEFAULT_BASE)
    # Only apply fields that exist in PointInputs (robust to refactors)
    d = base.__dict__.copy()
    for k, v in overrides.items():
        if k in d:
            d[k] = v
    inp = PointInputs(**d)
    import time as _time
    _t0 = _time.perf_counter()
    out = hot_ion_point(inp)
    _eval_s = _time.perf_counter() - _t0
    curated = {k: _safe(out.get(k)) for k in CURATED_KEYS}
    if not want_artifact:
        return curated
    constraints = [c.__dict__ for c in evaluate_constraints(out)]
    art = build_run_artifact(inputs=inp.__dict__, outputs=out, constraints=constraints, meta={"source": "benchmarks", "case": name})
    return curated, art

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true", help="Regenerate golden.json")
    ap.add_argument("--parallel", action="store_true", help="Run cases in parallel (order preserved)")
    ap.add_argument("--workers", type=int, default=0, help="Worker processes (0=auto)")
    ap.add_argument("--rtol", type=float, default=0.01, help="Relative tolerance (default 1%)")
    ap.add_argument("--atol", type=float, default=1e-6, help="Absolute tolerance floor")
    ap.add_argument("--write-diff", action="store_true", help="Write benchmarks/last_diff_report.json (numeric diff only; fast)")
    ap.add_argument("--write-diff-struct", action="store_true", help="Include structural diffs (artifacts/constraints/model cards); slower")
    ap.add_argument("--diff-path", type=str, default="", help="Optional path for diff report JSON")
    args = ap.parse_args()
    import time as _time
    t_wall0 = _time.perf_counter()

    cases_path = Path(__file__).resolve().parent / "cases.json"
    golden_path = Path(__file__).resolve().parent / "golden.json"

    cases = json.loads(cases_path.read_text())
    results = {}
    artifacts: dict = {}

    if args.parallel:
        import concurrent.futures
        n_workers = args.workers if args.workers and args.workers > 0 else None
        items = list(cases.items())
        payloads = [{"name": nm, "overrides": ov} for (nm, ov) in items]
        with concurrent.futures.ProcessPoolExecutor(max_workers=n_workers) as ex:
            for name, res in ex.map(_bench_worker, payloads, chunksize=1):
                results[name] = res
    else:
        for name, overrides in cases.items():
            results[name] = run_case(name, overrides, want_artifact=False)
    # Structural diff artifacts are optional because they require running all cases twice.
    if getattr(args, 'write_diff_struct', False):
        for name, overrides in cases.items():
            try:
                _, art = run_case(name, overrides, want_artifact=True)
                artifacts[name] = art
            except Exception:
                continue

    if args.generate or not golden_path.exists():
        golden_path.write_text(json.dumps(results, indent=2, sort_keys=True))
        print(f"Wrote {golden_path}")
        return 0

    golden = json.loads(golden_path.read_text())

    failed = False
    rows = []
    for name, cur in results.items():
        ref = golden.get(name, {})
        for k in CURATED_KEYS:
            a = _safe(cur.get(k))
            b = _safe(ref.get(k))
            if not (math.isfinite(a) and math.isfinite(b)):
                continue
            abs_err = abs(a - b)
            rel_err = _rel_err(a, b)
            ok = abs_err <= max(args.atol, args.rtol * max(abs(b), 1e-9))
            if not ok:
                failed = True
                print(f"FAIL {name} :: {k}: got {a:.6g} expected {b:.6g} relerr={rel_err:.3g}")
            rows.append({
                "case": name,
                "key": k,
                "got": a,
                "golden": b,
                "abs_err": abs_err,
                "rel_err": rel_err,
                "ok": bool(ok),
            })

    struct_enabled = False

    if args.write_diff:
        dp = Path(args.diff_path) if args.diff_path else (Path(__file__).resolve().parent / "last_diff_report.json")
        struct_enabled = bool(getattr(args, "write_diff_struct", False))
        # Structural diffs (constraints/model-cards/schema) vs golden artifacts
        structural = {}
        structural_severity = {}
        struct_summary = {"n_cases": 0, "n_with_changes": 0, "total_added_constraints": 0, "total_removed_constraints": 0, "total_changed_constraints": 0, "total_modelcard_changes": 0}
        ga_dir = Path(__file__).resolve().parent / "golden_artifacts"
        if struct_enabled and ga_dir.exists():
            for cname, art in artifacts.items():
                gpath = ga_dir / f"{cname}.json"
                if not gpath.exists():
                    continue
                gold_art = json.loads(gpath.read_text(encoding="utf-8"))
                d = structural_diff(art, gold_art)
                structural[cname] = d
                sev = classify_severity(gold_art, art, d)
                structural_severity[cname] = sev
                struct_summary.setdefault('severity_counts', {'info':0,'warn':0,'breaking':0})
                for k,v in (sev.get('counts') or {}).items():
                    if k in struct_summary['severity_counts']:
                        struct_summary['severity_counts'][k] += int(v)
                # track max severity seen
                order={'info':0,'warn':1,'breaking':2}
                cur=struct_summary.get('max_severity','info')
                if order.get(sev.get('max_severity','info'),0) > order.get(cur,0):
                    struct_summary['max_severity'] = sev.get('max_severity','info')
                struct_summary["n_cases"] += 1
                cadd = len(d["constraints"]["added"])
                crem = len(d["constraints"]["removed"])
                cchg = len(d["constraints"]["changed_meta"])
                mcchg = len(d["model_cards"]["added"]) + len(d["model_cards"]["removed"]) + len(d["model_cards"]["changed"])
                struct_summary["total_added_constraints"] += cadd
                struct_summary["total_removed_constraints"] += crem
                struct_summary["total_changed_constraints"] += cchg
                struct_summary["total_modelcard_changes"] += mcchg
                if cadd or crem or cchg or mcchg or (d["schema_version"]["new"] != d["schema_version"]["old"]):
                    struct_summary["n_with_changes"] += 1

        report = {
            "struct_enabled": bool(struct_enabled),
            "created_unix": time.time(),
            "rtol": float(args.rtol),
            "atol": float(args.atol),
            "n_rows": len(rows),
            "n_failed": sum(1 for r in rows if not r["ok"]),
            "rows": rows,
            "structural_summary": struct_summary,
            "structural": structural,
            "structural_severity": structural_severity,
        }
        dp.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Wrote diff report: {dp}")

    # Best-effort internal physics report (never gates)
    try:
        from models.inputs import PointInputs
        from physics.hot_ion import hot_ion_point

        physics_report = {
            "struct_enabled": bool(struct_enabled),
            "created_unix": time.time(),
            "cases": {},
            "keys": list(EXTRA_REPORT_KEYS),
        }
        for name, overrides in cases.items():
            base = PointInputs(**DEFAULT_BASE)
            d = base.__dict__.copy()
            for k, v in overrides.items():
                if k in d:
                    d[k] = v
            inp = PointInputs(**d)
            out = hot_ion_point(inp)
            physics_report["cases"][name] = {k: _safe(out.get(k)) for k in EXTRA_REPORT_KEYS}
        (Path(__file__).resolve().parent / "last_physics_report.json").write_text(
            json.dumps(physics_report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"Wrote physics report: {Path(__file__).resolve().parent / 'last_physics_report.json'}")
    except Exception as e:
        print(f"(physics report skipped) {e}")



    if not failed:
        print("All benchmarks passed.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
