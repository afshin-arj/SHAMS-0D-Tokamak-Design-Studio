"""Trade Study Studio helpers."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

try:
    from src.trade_studies.runner import run_trade_study
    from src.trade_studies.spec import default_knob_sets, KnobSet
    from src.trade_studies.families import attach_families, family_summary
    from src.optimization.objectives import list_objectives
except ImportError:
    from trade_studies.runner import run_trade_study  # type: ignore
    from trade_studies.spec import default_knob_sets, KnobSet  # type: ignore
    from trade_studies.families import attach_families, family_summary  # type: ignore
    from optimization.objectives import list_objectives  # type: ignore

from ui_nicegui.evaluate import ui_evaluator


from ui_nicegui.lib.display_labels import (
    DECK_FRONTIER_ATLAS,
    DECK_REGIME_MAPS,
    DECK_ROBUST_CERT,
)

STUDY_SETUP_DECK = "Study Setup & Run"

ADVANCED_DECKS = [
    DECK_FRONTIER_ATLAS,
    DECK_ROBUST_CERT,
    "Feasible-First Surrogate Accelerator",
    "Optimizer Kits (External)",
    "Fast Optimistic Design (Two-Lane)",
    "Design Family Atlas",
    DECK_REGIME_MAPS,
    "Mirage Pathfinding",
]


def objectives_catalog() -> Tuple[List[str], Dict[str, str]]:
    reg = list_objectives()
    names = sorted(reg.keys())
    senses = {k: str(reg[k].sense) for k in names}
    return names, senses


def default_objectives() -> List[str]:
    obj_names, _ = objectives_catalog()
    preferred = ["min_R0", "min_Bpeak", "max_Pnet", "max_Q"]
    return [o for o in preferred if o in obj_names] or obj_names[:3]


_KNOB_OBJECTIVE_HINTS: Dict[str, List[str]] = {
    "geometry": ["min_R0", "min_Bpeak", "max_Q"],
    "plasma": ["max_Q", "max_H98", "min_precirc"],
    "exhaust": ["min_q_div", "max_Pnet", "min_COE"],
    "magnet": ["min_Bpeak", "min_sigma_vm", "max_Pnet"],
}


def suggested_objectives_for_knob_set(knob_name: str) -> List[str]:
    obj_names, _ = objectives_catalog()
    n = str(knob_name or "").lower()
    if "exhaust" in n or "radiation" in n:
        key = "exhaust"
    elif "plasma" in n or "heating" in n:
        key = "plasma"
    elif "magnet" in n or "build" in n:
        key = "magnet"
    else:
        key = "geometry"
    hinted = _KNOB_OBJECTIVE_HINTS.get(key, [])
    return [o for o in hinted if o in obj_names] or default_objectives()


def run_studio_trade_study(
    base,
    *,
    knob_set: KnobSet,
    objectives: List[str],
    objective_senses: Dict[str, str],
    n_samples: int,
    seed: int,
    design_intent: str = "Power Reactor (net-electric)",
    include_outputs: bool = False,
) -> dict:
    ev = ui_evaluator(origin="NiceGUI:TradeStudy", cache_enabled=True, cache_max=4096)
    rep = run_trade_study(
        evaluator=ev,
        base_inputs=base,
        bounds=knob_set.bounds,
        objectives=list(objectives),
        objective_senses=dict(objective_senses),
        n_samples=int(n_samples),
        seed=int(seed),
        design_intent=str(design_intent),
        include_outputs=include_outputs,
    )
    rep["records"] = attach_families(rep.get("records") or [])
    rep["feasible"] = attach_families(rep.get("feasible") or [])
    rep["pareto"] = attach_families(rep.get("pareto") or [])
    rep["family_summary"] = family_summary(rep.get("records") or [])
    rep["knob_set_name"] = knob_set.name
    rep["design_intent"] = str(design_intent)
    rep["feasibility_mode"] = "governance+intent"
    rep["summary"] = summarize_trade_study(rep)
    return rep


def summarize_trade_study(rep: dict) -> Dict[str, Any]:
    meta = rep.get("meta") or {}
    n_samples = int(meta.get("n_samples") or len(rep.get("records") or []))
    n_feasible = len(rep.get("feasible") or [])
    n_pareto = len(rep.get("pareto") or [])
    feas_frac = float(n_feasible) / max(n_samples, 1)
    if feas_frac >= 0.05 and n_pareto >= 5:
        confidence = "Sampling-dense"
    elif n_pareto >= 1:
        confidence = "Sampling-moderate"
    elif n_feasible >= 1:
        confidence = "Sampling-sparse"
    else:
        confidence = "Sparse"
    return {
        "n_samples": n_samples,
        "n_feasible": n_feasible,
        "n_pareto": n_pareto,
        "feasible_fraction": feas_frac,
        "confidence": confidence,
        "objectives": meta.get("objectives") or [],
        "knob_set": rep.get("knob_set_name") or meta.get("knob_set"),
        "seed": meta.get("seed"),
        "design_intent": rep.get("design_intent") or meta.get("design_intent"),
        "feasibility_mode": rep.get("feasibility_mode") or meta.get("feasibility_mode", "governance+intent"),
    }


def frontier_posture(summary: dict) -> tuple[str, str]:
    """Return (message, tone) for Trade Study screening dashboard — not L0 Verdict."""
    n_pareto = int(summary.get("n_pareto") or 0)
    n_feasible = int(summary.get("n_feasible") or 0)
    conf = str(summary.get("confidence") or "")
    if n_feasible == 0:
        return (
            "No blocking-OK designs in sampled knobs (intent-gate) — widen knobs or relax intent lens.",
            "negative",
        )
    if n_pareto == 0:
        return "blocking-OK samples exist but no non-dominated front — check objective redundancy.", "warning"
    if conf in ("Sparse", "Sampling-sparse", "Low"):
        return "Sparse sampled front — increase samples or widen knobs; not a certified optimum.", "warning"
    if conf in ("Sampling-moderate", "Moderate"):
        return "Moderate sample density — trade-offs are indicative, not UQ-certified.", "info"
    return (
        "Sampling-dense blocking-OK front (intent-gate — not L0 FEASIBLE) — "
        "explore trade-offs; not a convergence proof.",
        "info",
    )


def build_study_capsule(rep: dict, base, knob_set: KnobSet, *, lane_mode: str) -> dict:
    meta = rep.get("meta") or {}
    objectives = list(meta.get("objectives") or [])
    senses = dict(meta.get("objective_senses") or {})
    seed = int(meta.get("seed") or 0)
    n_samples = int(meta.get("n_samples") or 0)
    payload = {
        "schema": "shams.study_capsule.v1",
        "created_ts": float(time.time()),
        "meta": dict(meta),
        "knob_set": {"name": str(knob_set.name), "bounds": dict(knob_set.bounds)},
        "objectives": objectives,
        "objective_senses": senses,
        "base_inputs": asdict(base) if hasattr(base, "__dict__") else {},
        "records": rep.get("records") or [],
        "feasible": rep.get("feasible") or [],
        "pareto": rep.get("pareto") or [],
        "lane_mode": str(lane_mode),
        "design_intent": str(rep.get("design_intent") or (rep.get("meta") or {}).get("design_intent") or ""),
        "feasibility_mode": str(rep.get("feasibility_mode") or "governance+intent"),
    }
    h = hashlib.sha256(
        json.dumps(
            {"meta": meta, "knobs": knob_set.name, "seed": seed, "n": n_samples, "obj": objectives},
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    payload["id"] = h[:12]
    return payload


def report_to_json_bytes(rep: dict) -> bytes:
    return json.dumps(rep, indent=2, sort_keys=True, default=str).encode("utf-8")
