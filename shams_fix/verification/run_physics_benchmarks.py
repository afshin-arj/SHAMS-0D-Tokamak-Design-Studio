"""
verification/run_physics_benchmarks.py

Read-only physics benchmarking against literature-derived reference formulas.
This script:
- evaluates a small set of SHAMS points
- computes derived reference metrics (Greenwald f_G, beta_N, Eich-normalized lambda_q)
- writes a JSON report with explicit pass/marginal/fail per check

IMPORTANT:
- Validation only (no runtime coupling; no model tuning)
- Does not modify any SHAMS behavior.
"""

from __future__ import annotations

import json
import math
import pathlib
from dataclasses import asdict
from typing import Any, Dict, List

# SHAMS imports (repo root assumed on PYTHONPATH or run as: python -m verification.run_physics_benchmarks)
from models.inputs import PointInputs
from evaluator.core import Evaluator


def _greenwald_nG_1e20(Ip_MA: float, a_m: float) -> float:
    return Ip_MA / (math.pi * a_m * a_m)


def _betaN(beta_frac: float, a_m: float, B_T: float, Ip_MA: float) -> float:
    # beta_N = beta[%] * a[m] * B[T] / Ip[MA]
    return beta_frac * 100.0 * a_m * B_T / Ip_MA


def _eich_norm_lambda_q(lambda_q_mm: float, Btor_T: float, q95: float, Psol_MW: float, Rgeo_m: float) -> float:
    """
    Normalize lambda_q by Eich 2013 proportionality:
        lambda_q ∝ B_tor^{-0.8} q95^{1.1} P_SOL^{0.1} R_geo^{1.0}

    Returns a "coefficient-like" value:
        C = lambda_q * B_tor^{0.8} / ( q95^{1.1} * P_SOL^{0.1} * R_geo )
    Useful for consistency checks (not a hard pass/fail unless user defines tolerance).
    """
    if any(x is None for x in [lambda_q_mm, Btor_T, q95, Psol_MW, Rgeo_m]):
        return float("nan")
    if Btor_T <= 0 or q95 <= 0 or Psol_MW <= 0 or Rgeo_m <= 0:
        return float("nan")
    return lambda_q_mm * (Btor_T ** 0.8) / ((q95 ** 1.1) * (Psol_MW ** 0.1) * (Rgeo_m ** 1.0))


def run() -> Dict[str, Any]:
    ev = Evaluator()

    # Minimal benchmark set:
    # - baseline point (matches UI default-ish)
    # - B-field perturbation (tests beta_N + lambda_q sensitivity)
    # - current perturbation (tests Greenwald + beta_N)
    points: List[PointInputs] = [
        PointInputs(R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.0, Ti_keV=15.0, fG=0.8, Paux_MW=20.0),
        PointInputs(R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=10.0, Ip_MA=8.0, Ti_keV=15.0, fG=0.8, Paux_MW=20.0),
        PointInputs(R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=6.0, Ti_keV=15.0, fG=0.8, Paux_MW=20.0),
    ]

    report: Dict[str, Any] = {
        "schema_version": 1,
        "checks": [],
        "points": [],
    }

    for idx, inp in enumerate(points):
        r = ev.evaluate(inp)
        out = r.out

        # Derived reference metrics
        nG = _greenwald_nG_1e20(Ip_MA=inp.Ip_MA, a_m=inp.a_m)
        fG_from_outputs = float("nan")
        if "ne20" in out and out["ne20"] is not None:
            fG_from_outputs = out["ne20"] / nG

        betaN_from_outputs = float("nan")
        if "beta_proxy" in out and out["beta_proxy"] is not None:
            betaN_from_outputs = _betaN(out["beta_proxy"], inp.a_m, out.get("B0_T", inp.Bt_T), inp.Ip_MA)

        eich_norm = float("nan")
        if "lambda_q_mm" in out:
            eich_norm = _eich_norm_lambda_q(
                lambda_q_mm=out.get("lambda_q_mm"),
                Btor_T=out.get("B0_T", inp.Bt_T),
                q95=out.get("q95_proxy", float("nan")),
                Psol_MW=out.get("P_SOL_MW", float("nan")),
                Rgeo_m=out.get("R0_m", inp.R0_m),
            )

        # Checks (hard pass/fail) where SHAMS should match its own documented definitions
        # These are "logic correctness" checks, not matching external coefficients.
        checks = []

        # Greenwald fraction consistency
        if "ne20" in out:
            ok_fg = (abs(fG_from_outputs - inp.fG) <= 1e-9)
            checks.append({
                "id": "greenwald_fG_consistency",
                "ok": ok_fg,
                "detail": {
                    "fG_input": inp.fG,
                    "fG_from_outputs": fG_from_outputs,
                    "nG_1e20": nG,
                    "ne20": out.get("ne20"),
                },
            })

        # beta_N consistency
        if "betaN_proxy" in out and "beta_proxy" in out:
            ok_bn = (abs(out["betaN_proxy"] - betaN_from_outputs) <= 1e-9)
            checks.append({
                "id": "betaN_definition_consistency",
                "ok": ok_bn,
                "detail": {
                    "betaN_proxy": out.get("betaN_proxy"),
                    "betaN_from_beta_proxy": betaN_from_outputs,
                    "beta_proxy": out.get("beta_proxy"),
                    "a_m": inp.a_m,
                    "B0_T": out.get("B0_T", inp.Bt_T),
                    "Ip_MA": inp.Ip_MA,
                },
            })

        report["points"].append({
            "index": idx,
            "inp": asdict(inp),
            "eval_ok": r.ok,
            "message": r.message,
            "key_outputs": {
                "Q_DT_eqv": out.get("Q_DT_eqv"),
                "Pfus_DT_eqv_MW": out.get("Pfus_DT_eqv_MW"),
                "P_SOL_MW": out.get("P_SOL_MW"),
                "lambda_q_mm": out.get("lambda_q_mm"),
                "q_div_MW_m2": out.get("q_div_MW_m2"),
                "beta_proxy": out.get("beta_proxy"),
                "betaN_proxy": out.get("betaN_proxy"),
                "ne20": out.get("ne20"),
                "q95_proxy": out.get("q95_proxy"),
            },
            "derived_reference_metrics": {
                "nG_1e20": nG,
                "fG_from_outputs": fG_from_outputs,
                "betaN_from_outputs": betaN_from_outputs,
                "eich_norm_lambda_q": eich_norm,
            },
            "checks": checks,
        })

    # Summarize check outcomes
    all_checks = []
    for p in report["points"]:
        for c in p["checks"]:
            all_checks.append(c["ok"])
    report["summary"] = {
        "all_logic_checks_ok": all(all_checks) if all_checks else True,
        "num_points": len(report["points"]),
        "num_checks": len(all_checks),
    }
    return report


def main() -> None:
    report = run()
    out_path = pathlib.Path(__file__).resolve().parent / "physics_benchmark_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
