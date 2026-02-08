"""verification/run_ui_mode_benchmarks.py

Read-only end-to-end checks for the 4 primary UI modes:
  - Point Designer (single evaluation)
  - Systems Mode (coupled constraint solve)
  - Scan Lab (bounded sampling + feasibility filter)
  - Pareto Lab (pareto front extraction)

Goal: answer the question "are physics/models/logic wired correctly in each mode?"
This is NOT a calibration tool and does not change SHAMS behavior.

Outputs: verification/ui_mode_benchmark_report.json
"""

from __future__ import annotations

import json
import math
import pathlib
import sys
sys.path.insert(0, str((pathlib.Path(__file__).resolve().parents[1] / 'src')))
import time
from dataclasses import asdict
from typing import Any, Dict, List, Tuple

from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from solvers.constraint_solver import solve_for_targets
from solvers.optimize import scan_feasible_and_pareto, pareto_front
from constraints.constraints import evaluate_constraints


ROOT = pathlib.Path(__file__).resolve().parents[1]


# -----------------------------
# Literature reference formulas
# -----------------------------
def _eich_lambda_q_mm(Bpol_T: float) -> float:
    """Eich et al. (NF 2013) regression #14 (all devices):
    lambda_q(mm) = 0.63 * Bpol(T)^(-1.19)

    Stored as a validation-only reference (read-only).
    """
    if not (Bpol_T > 0.0):
        return float("nan")
    return 0.63 * (Bpol_T ** (-1.19))


def _goldston_lambda_q_m(P_SOL_W: float, Bt_T: float, kappa: float, a_m: float, Ip_A: float, R_m: float, Zeff: float,
                        Abar: float = 2.0, Zbar: float = 1.0, Z: float = 1.0, use_electron_drift: bool = True) -> float:
    """Goldston heuristic drift model (NF 2012) eq (5)/(6), SI units.

    This is used as a magnitude/scaling cross-check only.
    We default to the electron-drift version (eq 6) because it removes Zbar from the prefactor.

    NOTE: SHAMS uses its own native lambda_q model; this function does not feed back.
    """
    if not (P_SOL_W > 0 and Bt_T > 0 and a_m > 0 and Ip_A > 0 and R_m > 0 and (1 + kappa*kappa) > 0):
        return float("nan")

    # Common factors from eq (5)/(6)
    pref = 5671.0
    term = (P_SOL_W ** (1.0/8.0)) * ((1.0 + kappa*kappa) ** (5.0/8.0)) * (a_m ** (17.0/8.0)) * (Bt_T ** (1.0/4.0))
    term *= (Ip_A ** (-9.0/8.0)) * (R_m ** (-1.0))

    # Species factor (eq 5 has (2*Abar/(Zbar^2*(1+Zbar)))^(7/16); eq 6 has (2*Abar/(1+Zbar))^(7/16))
    if use_electron_drift:
        species = (2.0 * Abar / (1.0 + Zbar)) ** (7.0/16.0)
    else:
        species = (2.0 * Abar / (Zbar*Zbar * (1.0 + Zbar))) ** (7.0/16.0)

    zeff_term = ((Zeff + 4.0) / 5.0) ** (1.0/8.0)
    return pref * term * species * zeff_term


# -----------------------------
# Helpers
# -----------------------------
def _finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def _default_point_inputs() -> PointInputs:
    # Matches UI "first success" point defaults.
    return PointInputs(R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.0, Ti_keV=15.0, fG=0.8, Paux_MW=20.0)


def _summarize_constraints(out: Dict[str, Any]) -> Dict[str, Any]:
    cs = evaluate_constraints(out)
    n = len(cs)
    n_ok = sum(1 for c in cs if getattr(c, "passed", False))
    failed: List[Dict[str, Any]] = []
    for c in cs:
        if getattr(c, "passed", False):
            continue
        lo = None
        hi = None
        try:
            if str(getattr(c, "sense", "")).strip() == "<=":
                hi = float(getattr(c, "limit", float("nan")))
            elif str(getattr(c, "sense", "")).strip() == ">=":
                lo = float(getattr(c, "limit", float("nan")))
        except Exception:
            pass
        failed.append({
            "name": getattr(c, "name", ""),
            "value": getattr(c, "value", None),
            "lo": lo,
            "hi": hi,
            "units": getattr(c, "units", ""),
            "severity": getattr(c, "severity", "hard"),
            "note": getattr(c, "note", ""),
            "group": getattr(c, "group", "general"),
        })
    return {
        "n_constraints": n,
        "n_ok": n_ok,
        "n_fail": n - n_ok,
        "failed": failed[:20],
    }

# -----------------------------
# Mode checks# -----------------------------
# Mode checks
# -----------------------------
def check_point_designer() -> Dict[str, Any]:
    base = _default_point_inputs()
    t0 = time.time()
    out = hot_ion_point(base)
    elapsed = time.time() - t0

    # Basic health checks
    required = ["Pfus_DT_eqv_MW", "Q_DT_eqv", "H98", "lambda_q_mm", "P_SOL_MW", "Bpol_out_mid_T"]
    missing = [k for k in required if k not in out]
    ok = (len(missing) == 0)

    # Reference comparisons (magnitude only; wide tolerances)
    Bpol = float(out.get("Bpol_out_mid_T", float("nan")))
    lam_shams = float(out.get("lambda_q_mm", float("nan")))
    lam_eich = _eich_lambda_q_mm(Bpol)

    P_SOL_W = float(out.get("P_SOL_MW", float("nan"))) * 1e6
    lam_gold = _goldston_lambda_q_m(P_SOL_W=P_SOL_W, Bt_T=float(base.Bt_T), kappa=float(base.kappa),
                                    a_m=float(base.a_m), Ip_A=float(base.Ip_MA)*1e6, R_m=float(base.R0_m),
                                    Zeff=float(base.zeff), use_electron_drift=True) * 1e3  # -> mm

    # Categorize closeness without declaring SHAMS "wrong" (literature uncertainty is large)
    def ratio(a: float, b: float) -> float:
        if not (_finite(a) and _finite(b) and b != 0.0):
            return float("nan")
        return float(a) / float(b)

    r_eich = ratio(lam_shams, lam_eich)
    r_gold = ratio(lam_shams, lam_gold)

    # Heuristic bands: within 0.3x..3x = OK; within 0.1x..10x = marginal; else fail.
    def band(r: float) -> str:
        if not _finite(r):
            return "na"
        ar = abs(r)
        if 0.3 <= ar <= 3.0:
            return "ok"
        if 0.1 <= ar <= 10.0:
            return "marginal"
        return "fail"

    return {
        "mode": "Point Designer",
        "ok": ok,
        "elapsed_s": elapsed,
        "missing": missing,
        "key_outputs": {k: out.get(k) for k in required if k in out},
        "constraints": _summarize_constraints(out),
        "references": {
            "eich_lambda_q_mm": lam_eich,
            "goldston_lambda_q_mm": lam_gold,
            "ratio_shams_over_eich": r_eich,
            "ratio_shams_over_goldston": r_gold,
            "band_vs_eich": band(r_eich),
            "band_vs_goldston": band(r_gold),
        },
    }


def check_systems_mode() -> Dict[str, Any]:
    base = _default_point_inputs()

    # Representative Systems Mode targets/variables: (Q, H98) solved by (Ip, fG)
    targets = {"Q_DT_eqv": 2.0, "H98": 1.15}
    variables = {
        "Ip_MA": (float(base.Ip_MA), 0.5*float(base.Ip_MA), 1.8*float(base.Ip_MA)),
        "fG": (float(base.fG), 0.2, 1.2),
    }

    t0 = time.time()
    res = solve_for_targets(base, targets=targets, variables=variables, tol=1e-3, damping=0.6, max_iter=35)
    elapsed = time.time() - t0

    out = res.out or {}
    # OK if solver converged and target residuals are small (as defined by solver)
    ok = bool(res.ok)

    # compute residuals explicitly for transparency
    residuals = {}
    for k, v in targets.items():
        try:
            residuals[k] = float(out.get(k, float("nan"))) - float(v)
        except Exception:
            residuals[k] = None

    return {
        "mode": "Systems Mode",
        "ok": ok,
        "elapsed_s": elapsed,
        "solver": {"ok": bool(res.ok), "iters": int(res.iters), "message": res.message, "residuals": residuals},
        "constraints": _summarize_constraints(out) if out else None,
        "key_outputs": {k: out.get(k) for k in ["Q_DT_eqv","H98","Ip_MA","fG","Paux_MW","Pfus_DT_eqv_MW","P_e_net_MW"] if k in out},
    }


def check_scan_lab() -> Dict[str, Any]:
    base = _default_point_inputs()
    bounds = {
        "Ip_MA": (0.8*base.Ip_MA, 1.2*base.Ip_MA),
        "fG": (0.6, 1.0),
        "Paux_MW": (0.0, 40.0),
    }

    t0 = time.time()
    res = scan_feasible_and_pareto(base_inputs=base, bounds=bounds, n_samples=40, objectives={"R0_m": "min", "P_e_net_MW": "max"}, seed=1)
    elapsed = time.time() - t0

    # res is dict with points + pareto etc (per UI usage)
    ok = isinstance(res, dict) and ("feasible" in res) and ("pareto" in res)

    npts = len(res.get("feasible", [])) if isinstance(res, dict) else 0
    npar = len(res.get("pareto", [])) if isinstance(res, dict) else 0

    # sanity: scan should at least run and produce a (possibly empty) feasible set without exceptions
    return {
        "mode": "Scan Lab",
        "ok": ok,
        "elapsed_s": elapsed,
        "scan": {"n_points": npts, "n_pareto": npar, "bounds": bounds},
        "note": "Empty pareto can be OK if feasibility is tight; failure here is about wiring/exceptions.",
    }


def check_pareto_lab() -> Dict[str, Any]:
    # Pareto Lab is effectively a post-process on points; verify pareto_front itself works.
    base = _default_point_inputs()
    bounds = {"Ip_MA": (0.8*base.Ip_MA, 1.2*base.Ip_MA), "fG": (0.6, 1.0)}
    res = scan_feasible_and_pareto(base_inputs=base, bounds=bounds, n_samples=30, objectives={"R0_m": "min", "P_e_net_MW": "max"}, seed=2)
    pts = res.get("feasible", []) if isinstance(res, dict) else []

    objectives = {"R0_m": "min", "P_e_net_MW": "max"}
    t0 = time.time()
    front = pareto_front(points=pts, objectives=objectives)
    elapsed = time.time() - t0

    ok = isinstance(front, list)
    return {
        "mode": "Pareto Lab",
        "ok": ok,
        "elapsed_s": elapsed,
        "pareto": {"n_input_points": len(pts), "n_front": len(front) if isinstance(front, list) else None},
    }


def run() -> Dict[str, Any]:
    started = time.time()
    results = []
    for fn in [check_point_designer, check_systems_mode, check_scan_lab, check_pareto_lab]:
        try:
            results.append(fn())
        except Exception as e:
            results.append({"mode": fn.__name__, "ok": False, "error": f"{type(e).__name__}: {e}"})

    overall_ok = all(bool(r.get("ok")) for r in results)
    return {
        "ts": time.time(),
        "elapsed_s": time.time() - started,
        "overall_ok": overall_ok,
        "results": results,
    }


def main() -> None:
    report = run()
    out_path = ROOT / "verification" / "ui_mode_benchmark_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
