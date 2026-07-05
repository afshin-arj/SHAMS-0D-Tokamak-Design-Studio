"""Trade Study Studio helpers (Batch 6)."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

try:
    from src.evaluator.core import Evaluator
    from src.trade_studies.runner import run_trade_study
    from src.trade_studies.spec import default_knob_sets, KnobSet
    from src.trade_studies.families import attach_families, family_summary
    from src.optimization.objectives import list_objectives
except ImportError:
    from evaluator.core import Evaluator  # type: ignore
    from trade_studies.runner import run_trade_study  # type: ignore
    from trade_studies.spec import default_knob_sets, KnobSet  # type: ignore
    from trade_studies.families import attach_families, family_summary  # type: ignore
    from optimization.objectives import list_objectives  # type: ignore


STUDY_SETUP_DECK = "Study Setup & Run"

ADVANCED_DECKS = [
    "Multi-Objective Feasible Frontier Atlas (v351)",
    "Robust Design Envelope Certification (v352)",
    "Feasible-First Surrogate Accelerator",
    "Optimizer Kits (External)",
    "Fast Optimistic Design (Two-Lane)",
    "Design Family Atlas",
    "Regime Maps & Narratives (v324)",
    "Mirage Pathfinding",
]


def objectives_catalog() -> Tuple[List[str], Dict[str, str]]:
    reg = list_objectives()
    names = sorted(reg.keys())
    senses = {k: str(reg[k].sense) for k in names}
    return names, senses


def default_objectives() -> List[str]:
    obj_names, _ = objectives_catalog()
    preferred = ["min_R0", "min_Bpeak", "max_Pnet"]
    return [o for o in preferred if o in obj_names] or obj_names[:3]


def run_studio_trade_study(
    base,
    *,
    knob_set: KnobSet,
    objectives: List[str],
    objective_senses: Dict[str, str],
    n_samples: int,
    seed: int,
    include_outputs: bool = False,
) -> dict:
    ev = Evaluator(label="NiceGUI:TradeStudy", cache_enabled=True, cache_max=4096)
    rep = run_trade_study(
        evaluator=ev,
        base_inputs=base,
        bounds=knob_set.bounds,
        objectives=list(objectives),
        objective_senses=dict(objective_senses),
        n_samples=int(n_samples),
        seed=int(seed),
        include_outputs=include_outputs,
    )
    rep["records"] = attach_families(rep.get("records") or [])
    rep["feasible"] = attach_families(rep.get("feasible") or [])
    rep["pareto"] = attach_families(rep.get("pareto") or [])
    rep["family_summary"] = family_summary(rep.get("records") or [])
    rep["knob_set_name"] = knob_set.name
    rep["summary"] = summarize_trade_study(rep)
    return rep


def summarize_trade_study(rep: dict) -> Dict[str, Any]:
    meta = rep.get("meta") or {}
    n_samples = int(meta.get("n_samples") or len(rep.get("records") or []))
    n_feasible = len(rep.get("feasible") or [])
    n_pareto = len(rep.get("pareto") or [])
    feas_frac = float(n_feasible) / max(n_samples, 1)
    if feas_frac >= 0.05 and n_pareto >= 5:
        confidence = "High"
    elif n_pareto >= 1:
        confidence = "Moderate"
    elif n_feasible >= 1:
        confidence = "Low"
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
    }


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
