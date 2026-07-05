"""Pareto Lab helpers — LHS sampling study via frozen evaluator (Batch 5)."""
from __future__ import annotations

import json
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

OBJ_CATALOG: Dict[str, Dict[str, str]] = {
    "R0_m": {"units": "m", "desc": "Major radius"},
    "Bt_T": {"units": "T", "desc": "Toroidal field on axis"},
    "Ip_MA": {"units": "MA", "desc": "Plasma current"},
    "fG": {"units": "-", "desc": "Greenwald fraction"},
    "B_peak_T": {"units": "T", "desc": "Peak TF field"},
    "P_e_net_MW": {"units": "MW", "desc": "Net electric power"},
    "Q_DT_eqv": {"units": "-", "desc": "Equivalent DT gain"},
    "q_div_MW_m2": {"units": "MW/m^2", "desc": "Divertor heat-flux proxy"},
    "sigma_vm_MPa": {"units": "MPa", "desc": "Von Mises stress proxy"},
    "hts_margin_cs": {"units": "-", "desc": "HTS margin (critical surface)"},
    "TBR": {"units": "-", "desc": "Tritium breeding ratio"},
}

OBJ_TEMPLATES: Dict[str, Optional[Dict[str, str]]] = {
    "Custom": None,
    "Reactor - Compact power": {
        "R0_m": "min",
        "P_e_net_MW": "max",
        "q_div_MW_m2": "min",
        "sigma_vm_MPa": "min",
        "TBR": "max",
    },
    "Reactor - Max gain": {
        "Q_DT_eqv": "max",
        "P_e_net_MW": "max",
        "R0_m": "min",
        "q_div_MW_m2": "min",
    },
    "Research - High current/density": {
        "Ip_MA": "max",
        "fG": "max",
        "R0_m": "min",
        "Bt_T": "max",
    },
    "Research - High field": {"Bt_T": "max", "B_peak_T": "max", "R0_m": "min"},
}

DEFAULT_MIN_KEYS = {"R0_m", "B_peak_T", "q_div_MW_m2", "sigma_vm_MPa"}


def default_objective_sense(key: str) -> str:
    return "min" if key in DEFAULT_MIN_KEYS else "max"


def default_bounds(base) -> Dict[str, Tuple[float, float]]:
    def _g(attr: str, default: float) -> float:
        try:
            return float(getattr(base, attr))
        except Exception:
            return float(default)

    r0 = _g("R0_m", 1.85)
    bt = _g("Bt_T", 12.0)
    ip = _g("Ip_MA", 8.0)
    return {
        "R0_m": (0.8 * r0, 1.25 * r0),
        "Bt_T": (0.7 * bt, 1.15 * bt),
        "Ip_MA": (0.6 * ip, 1.6 * ip),
        "fG": (0.3, 1.1),
    }


def intent_list(intent_mode: str) -> List[str]:
    if str(intent_mode).startswith("Both"):
        return ["Reactor", "Research"]
    return [str(intent_mode)]


def run_pareto_study(
    base,
    *,
    bounds: Dict[str, Tuple[float, float]],
    objectives: Dict[str, str],
    n_samples: int,
    seed: int,
    intent_mode: str,
    robust_margin_thr: float = 0.10,
) -> dict:
    try:
        from src.solvers.optimize import pareto_optimize
    except ImportError:
        from solvers.optimize import pareto_optimize  # type: ignore

    intents = intent_list(intent_mode)
    all_feasible: List[dict] = []
    all_pareto: List[dict] = []
    all_samples: List[dict] = []
    perf_runs: List[dict] = []

    for it in intents:
        res = pareto_optimize(
            base,
            bounds=bounds,
            objectives=objectives,
            n_samples=int(n_samples),
            seed=int(seed),
            intent_key=it,
        )
        perf = res.get("perf")
        if isinstance(perf, dict):
            perf_runs.append(perf)
        for row in res.get("feasible") or []:
            if isinstance(row, dict):
                r = dict(row)
                r["intent"] = it
                all_feasible.append(r)
        for row in res.get("pareto") or []:
            if isinstance(row, dict):
                r = dict(row)
                r["intent"] = it
                all_pareto.append(r)
        for row in res.get("all") or []:
            if isinstance(row, dict):
                r = dict(row)
                r["intent"] = it
                all_samples.append(r)

    payload = {
        "objectives": dict(objectives),
        "intent_mode": intent_mode,
        "bounds": {k: (float(v[0]), float(v[1])) for k, v in bounds.items()},
        "seed": int(seed),
        "n_samples": int(n_samples),
        "robust_margin_thr": float(robust_margin_thr),
        "feasible": all_feasible,
        "pareto": all_pareto,
        "all": all_samples,
        "perf": perf_runs,
    }
    payload["summary"] = summarize_pareto_run(payload)
    return payload


def summarize_pareto_run(pareto_last: dict) -> Dict[str, Any]:
    feasible = pareto_last.get("feasible") or []
    pareto = pareto_last.get("pareto") or []
    n_feasible = len(feasible)
    n_pareto = len(pareto)
    n_samples = int(pareto_last.get("n_samples") or 0)
    n_intents = len(intent_list(str(pareto_last.get("intent_mode", "Reactor"))))
    total_samples = max(n_samples * n_intents, 1)

    top_constraint = "-"
    if pareto:
        doms = [str(p.get("dominant_constraint") or "") for p in pareto if p.get("dominant_constraint")]
        if doms:
            top_constraint = Counter(doms).most_common(1)[0][0]

    thr = float(pareto_last.get("robust_margin_thr") or 0.10)
    robust_n = 0
    for p in pareto:
        try:
            m = float(p.get("min_constraint_margin", float("nan")))
            if m == m and m >= thr:
                robust_n += 1
        except (TypeError, ValueError):
            pass
    robust_mix = f"{robust_n}/{n_pareto}" if n_pareto else "-"

    feas_frac = float(n_feasible) / float(total_samples)
    if feas_frac >= 0.01 and n_pareto >= 10:
        confidence = "High"
    elif feas_frac >= 0.001 and n_pareto >= 3:
        confidence = "Moderate"
    elif n_pareto >= 1:
        confidence = "Low"
    else:
        confidence = "Sparse"

    return {
        "n_feasible": n_feasible,
        "n_pareto": n_pareto,
        "top_constraint": top_constraint,
        "robust_mix": robust_mix,
        "confidence": confidence,
        "feasible_fraction": feas_frac,
    }


def build_pareto_artifact(pareto_last: dict) -> dict:
    objectives = pareto_last.get("objectives") or {}
    return {
        "schema": "shams.pareto.v1",
        "intent_mode": pareto_last.get("intent_mode"),
        "objectives": {
            k: {"sense": v, **OBJ_CATALOG.get(k, {})} for k, v in objectives.items()
        },
        "bounds": pareto_last.get("bounds"),
        "seed": pareto_last.get("seed"),
        "n_samples": pareto_last.get("n_samples"),
        "robust_margin_thr": pareto_last.get("robust_margin_thr"),
        "feasible": pareto_last.get("feasible") or [],
        "pareto": pareto_last.get("pareto") or [],
    }


def artifact_to_json_bytes(artifact: dict) -> bytes:
    return json.dumps(artifact, indent=2, sort_keys=True, default=str).encode("utf-8")
