"""Pareto Lab helpers — LHS sampling study via frozen evaluator."""
from __future__ import annotations

import json
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

OBJ_CATALOG: Dict[str, Dict[str, str]] = {
    "R0_m": {"units": "m", "desc": "Major radius"},
    "Bt_T": {"units": "T", "desc": "Toroidal field on axis"},
    "Ip_MA": {"units": "MA", "desc": "Plasma current"},
    "fG": {"units": "-", "desc": "Greenwald fraction"},
    "Paux_MW": {"units": "MW", "desc": "Auxiliary heating power"},
    "B_peak_T": {"units": "T", "desc": "Peak TF field"},
    "P_e_net_MW": {"units": "MW", "desc": "Net electric power"},
    "Q_DT_eqv": {"units": "-", "desc": "Equivalent DT gain"},
    "H98": {"units": "-", "desc": "H-mode confinement factor"},
    "Pfus_DT_adj_MW": {"units": "MW", "desc": "DT-adjusted fusion power (screening)"},
    "Pfus_total_MW": {"units": "MW", "desc": "Total fusion power"},
    "tauE_eff_s": {"units": "s", "desc": "Effective energy confinement time"},
    "t_flat_s": {"units": "s", "desc": "Flat-top burn duration"},
    "beta_N": {"units": "-", "desc": "Normalized beta"},
    "q_div_MW_m2": {"units": "MW/m^2", "desc": "Divertor heat-flux proxy"},
    "sigma_vm_MPa": {"units": "MPa", "desc": "Von Mises stress proxy"},
    "hts_margin_cs": {"units": "-", "desc": "HTS margin (critical surface)"},
    "TBR": {"units": "-", "desc": "Tritium breeding ratio (screening proxy)"},
    "P_recirc_MW": {"units": "MW", "desc": "Recirculating power"},
}

FOCUS_METRIC_KEYS = [
    "Q_DT_eqv",
    "H98",
    "Pfus_total_MW",
    "Pfus_DT_adj_MW",
    "P_e_net_MW",
    "TBR",
    "q_div_MW_m2",
    "min_constraint_margin",
    "t_flat_s",
]

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
    "Research - Confinement": {
        "H98": "max",
        "Q_DT_eqv": "max",
        "tauE_eff_s": "max",
        "R0_m": "min",
    },
    "Reactor - Fusion power": {
        "Pfus_total_MW": "max",
        "Q_DT_eqv": "max",
        "q_div_MW_m2": "min",
        "R0_m": "min",
    },
}

DEFAULT_MIN_KEYS = {"R0_m", "B_peak_T", "q_div_MW_m2", "sigma_vm_MPa", "P_recirc_MW"}


def metric_label(key: str) -> str:
    meta = OBJ_CATALOG.get(key, {})
    units = meta.get("units", "")
    desc = meta.get("desc", key)
    if units and units != "-":
        return f"{desc} [{units}]"
    return str(desc)


def frontier_posture(summary: dict) -> tuple[str, str]:
    """Return (message, tone) for verdict-first dashboard."""
    n_pareto = int(summary.get("n_pareto") or 0)
    n_feasible = int(summary.get("n_feasible") or 0)
    conf = str(summary.get("confidence") or "")
    if n_feasible == 0:
        return "No feasible designs in sampled bounds — widen bounds or relax intent lens.", "negative"
    if n_pareto == 0:
        return "Feasible samples exist but no non-dominated front — check objective redundancy.", "warning"
    if conf == "Sparse":
        return "Sparse Pareto front — increase samples or widen bounds for better coverage.", "warning"
    if conf == "Low":
        return "Low-confidence front — treat trade-offs as indicative, not definitive.", "warning"
    if conf == "Moderate":
        return "Moderate sampling confidence — front is usable with standard caveats.", "info"
    return "High-confidence feasible-only front — explore trade-offs on the plot.", "positive"


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
    paux = _g("Paux_MW", 50.0)
    out = {
        "R0_m": (0.8 * r0, 1.25 * r0),
        "Bt_T": (0.7 * bt, 1.15 * bt),
        "Ip_MA": (0.6 * ip, 1.6 * ip),
        "fG": (0.3, 1.1),
    }
    if paux > 0:
        out["Paux_MW"] = (max(5.0, 0.6 * paux), min(200.0, 1.5 * paux))
    return out


def _baseline_knob_values(base, keys: Optional[List[str]] = None) -> Dict[str, float]:
    """Extract knob values from a PointInputs-like baseline (PARETO-BOUNDS-001)."""
    keys = keys or ["R0_m", "Bt_T", "Ip_MA", "fG", "Paux_MW"]
    out: Dict[str, float] = {}
    for k in keys:
        try:
            out[k] = float(getattr(base, k))
        except Exception:
            continue
    return out


def sanitize_sampling_bounds(
    bounds: Dict[str, Any],
    *,
    baseline: Optional[Dict[str, float]] = None,
    defaults: Optional[Dict[str, Tuple[float, float]]] = None,
) -> Dict[str, Tuple[float, float]]:
    """Ensure each sampling box has lo ≤ hi and includes the PD baseline.

    PARETO-BOUNDS-001: stale session bounds (e.g. R0 max≈2.26 from default R0=1.81)
    can invert or exclude a raised PD point (R0=4). Strategy per knob:
    - missing/corrupt → seed from ``defaults`` when available
    - inverted → swap edges
    - PD baseline outside → expand the nearer edge to include it
    """
    out: Dict[str, Tuple[float, float]] = {}
    keys = list(bounds.keys()) if bounds else []
    if defaults:
        for k in defaults:
            if k not in keys:
                keys.append(k)

    for key in keys:
        pair = (bounds or {}).get(key)
        lo: Optional[float] = None
        hi: Optional[float] = None
        if pair is not None:
            try:
                lo, hi = float(pair[0]), float(pair[1])
            except (TypeError, ValueError, IndexError, KeyError):
                lo = hi = None

        if lo is None or hi is None:
            if defaults and key in defaults:
                lo, hi = float(defaults[key][0]), float(defaults[key][1])
            else:
                continue

        if lo > hi:
            lo, hi = hi, lo

        v: Optional[float] = None
        if baseline and key in baseline:
            try:
                v = float(baseline[key])
            except (TypeError, ValueError):
                v = None

        if v is not None:
            if v < lo:
                lo = v
            if v > hi:
                hi = v
            if lo >= hi:
                pad = max(abs(v) * 0.05, 1e-9)
                lo, hi = v - pad, v + pad

        out[key] = (float(lo), float(hi))
    return out


def ensure_pareto_bounds(session: Any, base=None) -> Dict[str, Tuple[float, float]]:
    """Seed/refresh ``session.pareto_bounds`` from the current PD baseline (sane lo≤hi)."""
    if base is None:
        base = session.build_point_inputs()
    fresh = default_bounds(base)
    baseline = _baseline_knob_values(base, list(fresh.keys()))
    current = getattr(session, "pareto_bounds", None)
    if not isinstance(current, dict) or not current:
        session.pareto_bounds = dict(fresh)
    else:
        session.pareto_bounds = sanitize_sampling_bounds(
            current, baseline=baseline, defaults=fresh
        )
    return session.pareto_bounds


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
        "feasibility_mode": "governance+intent",
        "feasible": all_feasible,
        "pareto": all_pareto,
        "all": all_samples,
        "perf": perf_runs,
    }
    if str(intent_mode).startswith("Both") and len(objectives) >= 2 and all_pareto:
        try:
            from src.solvers.optimize import pareto_front
        except ImportError:
            from solvers.optimize import pareto_front  # type: ignore
        payload["pareto_union"] = pareto_front(list(all_pareto), objectives)
    payload["summary"] = summarize_pareto_run(payload)
    payload["_nan_objective_rates"] = compute_nan_objective_rates(all_feasible, list(objectives.keys()))
    return payload


def compute_nan_objective_rates(feasible: list, obj_keys: List[str]) -> Dict[str, float]:
    if not feasible or not obj_keys:
        return {}
    rates: Dict[str, float] = {}
    n = max(len(feasible), 1)
    for k in obj_keys:
        bad = 0
        for r in feasible:
            v = r.get(k) if isinstance(r, dict) else None
            try:
                fv = float(v)
                if fv != fv:
                    bad += 1
            except (TypeError, ValueError):
                bad += 1
        rates[k] = float(bad) / float(n)
    return rates


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

    mirage_n = sum(1 for p in pareto if bool(p.get("mirage_flag_v402")))
    mirage_mix = f"{mirage_n}/{n_pareto}" if n_pareto else "-"

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
        "mirage_mix": mirage_mix,
        "confidence": confidence,
        "feasible_fraction": feas_frac,
    }


def build_pareto_artifact(pareto_last: dict) -> dict:
    objectives = pareto_last.get("objectives") or {}
    prov: Dict[str, Any] = {}
    try:
        from pathlib import Path

        ver_path = Path(__file__).resolve().parents[2] / "VERSION"
        if ver_path.is_file():
            prov["shams_version"] = ver_path.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    prov["intent_mode"] = pareto_last.get("intent_mode")
    prov["created_schema"] = "shams.pareto.v1"
    prov["feasibility_mode"] = pareto_last.get("feasibility_mode", "governance+intent")
    return {
        "schema": "shams.pareto.v1",
        "provenance": prov,
        "feasibility_mode": pareto_last.get("feasibility_mode", "governance+intent"),
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
