"""Systems Mode workflow helpers — recovery, search, apply, export (Phase 12)."""
from __future__ import annotations

import json
import math
import random
import time
from dataclasses import fields, replace
from typing import Any, Dict, List, Optional, Tuple

from ui_nicegui.lib.verdict_core import verdict_summary


def tuple_bounds_to_dict(
    variables: Dict[str, Tuple[float, float, float]],
) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for k, (_, lo, hi) in variables.items():
        out[k] = {"lo": float(lo), "hi": float(hi)}
    return out


def recovery_seed(
    session: Any,
    variables: Dict[str, Tuple[float, float, float]],
    *,
    mode: str = "point_designer",
) -> Dict[str, float]:
    seed: Dict[str, float] = {}
    for k, (center, lo, hi) in variables.items():
        if mode == "midpoint":
            seed[k] = 0.5 * (float(lo) + float(hi))
        else:
            v = session.inputs.get(k, center)
            seed[k] = float(v) if isinstance(v, (int, float)) else float(center)
        seed[k] = max(float(lo), min(float(hi), seed[k]))
    return seed


def _get_evaluator():
    try:
        from src.evaluator.core import Evaluator
    except ImportError:
        from evaluator.core import Evaluator  # type: ignore
    return Evaluator(label="NiceGUI:Systems", cache_enabled=True, cache_max=8192)


def _build_inputs(base, x: Dict[str, float]):
    valid = {f.name for f in fields(base)}
    kwargs = {k: float(v) for k, v in x.items() if k in valid}
    return replace(base, **kwargs)


def _feasible_outputs(out: dict) -> bool:
    return bool(verdict_summary(out).get("feasible"))


def _violation_score(out: dict) -> float:
    rows = []
    try:
        try:
            from constraints.constraints import evaluate_constraints
        except ImportError:
            from src.constraints.constraints import evaluate_constraints  # type: ignore
        cons = evaluate_constraints(out or {})
        for c in cons:
            if str(getattr(c, "severity", "hard")).lower() != "hard":
                continue
            if bool(getattr(c, "passed", False)):
                continue
            m = getattr(c, "margin", float("nan"))
            try:
                mv = float(m)
            except (TypeError, ValueError):
                mv = float("nan")
            if not math.isfinite(mv):
                return 1e6
            rows.append(max(0.0, -mv))
    except Exception:
        return 1e6 if not _feasible_outputs(out) else 0.0
    return float(sum(v * v for v in rows))


def run_seeded_recovery(
    base,
    variables: Dict[str, Tuple[float, float, float]],
    *,
    seed: Optional[Dict[str, float]] = None,
    weights: Optional[Dict[str, float]] = None,
    variables_bounds: Optional[Dict[str, Dict[str, float]]] = None,
    rng_seed: int = 2026,
    budget_evals: int = 120,
    local_steps: int = 40,
    multi_start: int = 20,
) -> dict:
    try:
        from src.systems.recovery import recover_feasible_near_seed
    except ImportError:
        from systems.recovery import recover_feasible_near_seed  # type: ignore

    bounds = variables_bounds or tuple_bounds_to_dict(variables)
    ev = _get_evaluator()
    return recover_feasible_near_seed(
        base=base,
        variables=bounds,
        evaluator=ev,
        seed=seed,
        weights=weights,
        rng_seed=int(rng_seed),
        budget_evals=int(budget_evals),
        local_steps=int(local_steps),
        multi_start=int(multi_start),
        return_trace=True,
        trace_keep=500,
    )


def run_feasible_search(
    base,
    variables: Dict[str, Tuple[float, float, float]],
    *,
    rng_seed: int = 2026,
    budget: int = 150,
    topk: int = 8,
    radius: float = 0.25,
    reactor_intent: bool = True,
) -> dict:
    bounds = tuple_bounds_to_dict(variables)
    if not bounds:
        return {"ok": False, "reason": "no_bounds", "candidates": []}

    ev = _get_evaluator()
    rng = random.Random(int(rng_seed))
    search_vars = list(bounds.keys())

    x_start = {
        k: 0.5 * (bounds[k]["lo"] + bounds[k]["hi"]) for k in search_vars
    }
    res0 = ev.evaluate(_build_inputs(base, x_start))
    out0 = res0.out if res0 and res0.ok else {}
    feas0 = _feasible_outputs(out0)
    obj0 = float(out0.get("Q_DT_eqv", out0.get("Q", float("inf"))) or float("inf"))
    V0 = _violation_score(out0)

    best_x = dict(x_start)
    best_obj = obj0 if math.isfinite(obj0) else float("inf")
    best_V = V0
    cands: List[dict] = []

    def _headline(out: dict) -> dict:
        return {
            "Q": out.get("Q_DT_eqv", out.get("Q")),
            "H98": out.get("H98"),
            "P_net": out.get("P_e_net_MW", out.get("P_net_MW")),
        }

    if (not reactor_intent) or feas0:
        cands.append(
            {
                "x": dict(x_start),
                "obj": obj0,
                "V": V0,
                "feasible": feas0,
                "headline": _headline(out0),
            }
        )

    for i in range(max(0, int(budget) - 1)):
        frac = max(0.05, float(radius) * (1.0 - i / max(1, int(budget) - 1)))
        x: Dict[str, float] = {}
        for k, b in bounds.items():
            lo, hi = b["lo"], b["hi"]
            span = hi - lo
            x0 = float(best_x.get(k, x_start.get(k)))
            xv = x0 + (rng.random() * 2.0 - 1.0) * frac * span
            x[k] = max(lo, min(hi, xv))

        res = ev.evaluate(_build_inputs(base, x))
        if not (res and res.ok and isinstance(res.out, dict)):
            continue
        out = res.out
        feas = _feasible_outputs(out)
        V = _violation_score(out)
        obj = float(out.get("Q_DT_eqv", out.get("Q", float("inf"))) or float("inf"))

        if reactor_intent and not feas:
            continue

        cands.append(
            {
                "x": dict(x),
                "obj": obj,
                "V": V,
                "feasible": feas,
                "headline": _headline(out),
            }
        )

        if reactor_intent:
            if feas and obj < best_obj:
                best_obj = obj
                best_x = dict(x)
        elif V < best_V - 1e-12 or (abs(V - best_V) <= 1e-12 and obj < best_obj):
            best_V = V
            best_obj = obj
            best_x = dict(x)

    if reactor_intent:
        cands.sort(key=lambda c: float(c.get("obj", float("inf"))))
    else:
        cands.sort(key=lambda c: (float(c.get("V", float("inf"))), float(c.get("obj", float("inf")))))

    top = cands[: max(1, int(topk))]
    return {
        "ok": bool(len(top) > 0),
        "reason": "feasible_candidates" if top else "no_feasible_found",
        "candidates": top,
        "best_point": dict(best_x),
        "eval_budget": int(budget),
        "seed": int(rng_seed),
    }


def collect_candidates(session: Any) -> List[dict]:
    out: List[dict] = []
    rec = getattr(session, "systems_recovery_last", None)
    if isinstance(rec, dict) and isinstance(rec.get("best_point"), dict):
        out.append(
            {
                "id": "recovery",
                "source": "Seeded Recovery",
                "x": dict(rec["best_point"]),
                "feasible": bool(rec.get("ok")),
                "reason": str(rec.get("reason", "")),
                "headline": rec.get("headline") or {},
            }
        )
    fs = getattr(session, "systems_feasible_search_last", None)
    if isinstance(fs, dict):
        for i, c in enumerate(fs.get("candidates") or []):
            if not isinstance(c, dict) or not isinstance(c.get("x"), dict):
                continue
            out.append(
                {
                    "id": f"search_{i}",
                    "source": "Feasible Search",
                    "x": dict(c["x"]),
                    "feasible": bool(c.get("feasible")),
                    "reason": str(fs.get("reason", "")),
                    "headline": c.get("headline") or {},
                }
            )
    return out


def apply_x_to_session(session: Any, x: Dict[str, float]) -> Dict[str, float]:
    applied: Dict[str, float] = {}
    for k, v in x.items():
        if k in session.inputs:
            session.inputs[k] = float(v)
            applied[k] = float(v)
    return applied


def append_run_card(
    session: Any,
    *,
    kind: str,
    settings: dict,
    outcome: dict,
    payload: Optional[dict] = None,
) -> str:
    cards = list(getattr(session, "systems_run_cards", []) or [])
    rid = f"sys_{int(time.time())}_{len(cards)}"
    cards.append(
        {
            "id": rid,
            "ts": time.time(),
            "kind": str(kind),
            "settings": dict(settings),
            "outcome": dict(outcome),
            "payload": dict(payload) if isinstance(payload, dict) else {},
        }
    )
    session.systems_run_cards = cards
    return rid


def artifact_from_recovery(rep: dict, *, design_intent: str = "", base=None) -> dict:
    """Legacy wrapper — prefer artifact_from_recovery_eval when base is available."""
    if base is not None:
        try:
            from ui_nicegui.lib.systems_solve_helpers import artifact_from_recovery_eval
            return artifact_from_recovery_eval(base, rep, design_intent=design_intent)
        except Exception:
            pass
    x = rep.get("best_point") if isinstance(rep.get("best_point"), dict) else {}
    art = {
        "verdict": "FEASIBLE" if rep.get("ok") else "INFEASIBLE",
        "dominant_constraint": None,
        "source": "systems_recovery",
        "recovery": dict(rep),
        "best_point": dict(x),
    }
    if design_intent:
        art["design_intent"] = design_intent
    return art


def systems_run_payload(session: Any, artifact: Optional[dict] = None) -> dict:
    art = dict(artifact) if isinstance(artifact, dict) else {}
    if not art:
        raw = getattr(session, "systems_last_solve_artifact", None)
        if isinstance(raw, dict):
            art = dict(raw)
    ui_state = {}
    for key in (
        "systems_targets_overrides",
        "systems_bounds_overrides",
        "systems_base_overrides",
        "systems_inputs_overrides",
        "design_intent",
        "systems_workflow_step",
        "systems_decision_state",
    ):
        if hasattr(session, key):
            ui_state[key] = getattr(session, key)
    if art:
        art = dict(art)
        art["ui_state"] = ui_state
    else:
        art = {"ui_state": ui_state}
    return art


def systems_export_bytes(session: Any) -> bytes:
    payload = {
        "exported_ts": time.time(),
        "design_intent": getattr(session, "design_intent", ""),
        "systems_last_solve_artifact": getattr(session, "systems_last_solve_artifact", None),
        "last_precheck_report": _serialize_report(getattr(session, "last_precheck_report", None)),
        "systems_recovery_last": getattr(session, "systems_recovery_last", None),
        "systems_feasible_search_last": getattr(session, "systems_feasible_search_last", None),
        "systems_run_cards": list(getattr(session, "systems_run_cards", []) or []),
        "systems_journal": list(getattr(session, "systems_journal", []) or []),
        "systems_bounds_overrides": getattr(session, "systems_bounds_overrides", None),
        "systems_targets_overrides": getattr(session, "systems_targets_overrides", None),
        "inputs": dict(getattr(session, "inputs", {}) or {}),
    }
    return json.dumps(payload, indent=2, sort_keys=True, default=str).encode("utf-8")


def _serialize_report(report: Any) -> Any:
    if report is None:
        return None
    if isinstance(report, dict):
        return report
    d: Dict[str, Any] = {}
    for name in ("ok", "reason", "n_samples", "unreachable_targets_confidence", "hard_constraints_failed_at_all_samples"):
        if hasattr(report, name):
            d[name] = getattr(report, name)
    return d or str(report)
