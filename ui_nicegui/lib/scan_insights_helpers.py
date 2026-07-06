"""Scan Lab next-tier and local insight wrappers."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


NEXT_TIER_TOOLS = [
    "Explain infeasible region",
    "Constraint irrelevance",
    "Assumption stress hotspots",
    "Surprise detector",
    "Local scaling law",
    "Regime label at cell",
    "Counterfactual lens",
    "Projection stability",
    "Path-follow scan",
    "Guided walkthrough",
]

LOCAL_INSIGHTS = [
    "Causality trace",
    "Time-to-failure along knob",
    "Uncertainty stress-test",
    "Null direction (2D)",
]


def explain_impossible(rep: dict, intent: str) -> dict:
    from tools.scan_next_tier import explain_impossible_region

    return explain_impossible_region(report=rep, intent=str(intent))


def irrelevant_constraints(rep: dict, intent: str) -> dict:
    from tools.scan_next_tier import detect_irrelevant_constraints

    return detect_irrelevant_constraints(report=rep, intent=str(intent))


def stress_hotspots(rep: dict, intent: str, *, tol: float = 0.05) -> dict:
    from tools.scan_next_tier import assumption_stress_hotspots

    return assumption_stress_hotspots(report=rep, intent=str(intent), tol=float(tol))


def surprise_regions(rep: dict, intent: str, *, radius: int = 1) -> dict:
    from tools.scan_next_tier import surprise_regions as _surprise

    return _surprise(report=rep, intent=str(intent), radius=int(radius))


def local_scaling(rep: dict, intent: str, i: int, j: int, *, target: str = "min_blocking_margin") -> dict:
    from tools.scan_next_tier import local_powerlaw_fit

    return local_powerlaw_fit(report=rep, intent=str(intent), i0=int(i), j0=int(j), target=str(target))


def regime_label(rep: dict, intent: str, i: int, j: int) -> dict:
    from tools.scan_next_tier import label_regime

    return label_regime(report=rep, intent=str(intent), i0=int(i), j0=int(j))


def counterfactual(rep: dict, intent: str, drop_constraint: str) -> dict:
    from tools.scan_next_tier import counterfactual_lens

    return counterfactual_lens(report=rep, intent=str(intent), drop_constraint=str(drop_constraint))


def projection_stability(base, rep: dict, intent: str, i: int, j: int, z_key: str, rel_step: float) -> dict:
    from tools.scan_next_tier import projection_stability_check
    from src.evaluator.core import Evaluator

    ev = Evaluator(label="NiceGUI:ScanProjStab", cache_enabled=True, cache_max=4096)
    return projection_stability_check(
        evaluator=ev,
        base_inputs=base,
        report=rep,
        intent=str(intent),
        i0=int(i),
        j0=int(j),
        z_key=str(z_key),
        rel_step=float(rel_step),
    )


def path_follow_scan(base, rep: dict, *, target_output: str, intent: str = "Reactor") -> dict:
    from tools.scan_next_tier import path_follow_scan as _path
    from src.evaluator.core import Evaluator

    ev = Evaluator(label="NiceGUI:ScanPath", cache_enabled=True, cache_max=4096)
    x_vals = list(rep.get("x_vals") or [])
    return _path(
        evaluator=ev,
        base_inputs=base,
        x_key=str(rep.get("x_key") or ""),
        y_key=str(rep.get("y_key") or ""),
        x_vals=x_vals,
        target_output=str(target_output),
        intent=str(intent),
    )


def guided_walkthrough() -> List[dict]:
    from tools.scan_next_tier import guided_steps

    return list(guided_steps() or [])


def time_to_failure(base, rep: dict, intent: str, i: int, j: int, knob: str, rel_step: float) -> dict:
    from tools.scan_insights import time_to_failure_along_knob
    from src.evaluator.core import Evaluator
    from ui_nicegui.lib.scan_workbench_helpers import build_point_grid, cell_intent_state, _cell_xy_overrides

    grid = build_point_grid(rep)
    cell = grid.get((int(i), int(j)), {})
    s = cell_intent_state(grid, intent, i, j)
    domc = str(s.get("dominant_blocking") or "").strip()
    overrides = _cell_xy_overrides(rep, cell)
    ev = Evaluator(label="NiceGUI:ScanTTF", cache_enabled=True, cache_max=4096)
    return time_to_failure_along_knob(
        evaluator=ev,
        base_inputs=base,
        point_overrides=overrides,
        constraint_name=domc,
        knob=str(knob),
        rel_step=float(rel_step),
    )


def uncertainty_stress(base, rep: dict, intent: str, i: int, j: int, *, n_samples: int = 40, seed: int = 1) -> dict:
    from tools.scan_insights import uncertainty_stress_test
    from src.evaluator.core import Evaluator
    from ui_nicegui.lib.scan_workbench_helpers import build_point_grid, _cell_xy_overrides

    grid = build_point_grid(rep)
    cell = grid.get((int(i), int(j)), {})
    overrides = _cell_xy_overrides(rep, cell)
    ev = Evaluator(label="NiceGUI:ScanUQ", cache_enabled=True, cache_max=4096)
    return uncertainty_stress_test(
        evaluator=ev,
        base_inputs=base,
        point_overrides=overrides,
        intent=str(intent),
        n_samples=int(n_samples),
        seed=int(seed),
    )


def null_direction_from_trace(trace: dict, *, x_key: str = "", y_key: str = "") -> dict:
    from tools.scan_insights import null_direction_2d

    drivers = trace.get("drivers") or []
    gx = gy = 0.0
    for d in drivers:
        if not isinstance(d, dict):
            continue
        dm = float(d.get("d_margin_d_knob") or 0.0)
        knob = str(d.get("knob") or "")
        if x_key and knob == x_key:
            gx = dm
        elif y_key and knob == y_key:
            gy = dm
    return null_direction_2d(gx, gy)


def build_claim_evidence(rep: dict, intent: str) -> dict:
    from tools.scan_expert_features import build_claim_evidence as _bce

    return _bce(rep, str(intent))


def falsify_claim(rep: dict, intent: str, claim_type: str, expected: str) -> dict:
    from tools.scan_expert_features import falsify_claim as _fc

    ct = "dominance" if claim_type.lower().startswith("dom") else "robustness"
    return _fc(rep, intent=str(intent), claim_type=ct, expected=str(expected))


def build_claim_pdf(*, claim, evidence: dict, map_png: Optional[bytes], fingerprint: dict) -> bytes:
    from tools.scan_expert_features import build_claim_pdf_bytes

    return build_claim_pdf_bytes(
        claim=claim,
        evidence=evidence,
        map_png=map_png,
        fingerprint=fingerprint,
    )


def topology_alerts(rep: dict, intent: str) -> List[str]:
    alerts: List[str] = []
    topo_all = rep.get("topology") if isinstance(rep.get("topology"), dict) else {}
    topo = topo_all.get(str(intent)) if isinstance(topo_all, dict) else None
    if not isinstance(topo, dict) or not topo:
        return alerts
    n_comp = int(topo.get("n_components") or 1)
    if n_comp > 1:
        alerts.append(f"{n_comp} disconnected feasible islands (intent {intent}).")
    if bool(topo.get("has_holes")):
        alerts.append(f"Hole-like infeasible pockets (count={topo.get('hole_count')}).")
    return alerts


def intent_narrative(rep: dict, intent: str) -> str:
    nar_all = rep.get("narrative") or {}
    nar_int = (nar_all.get("intents") or {}) if isinstance(nar_all, dict) else {}
    n0 = nar_int.get(str(intent), {}) if isinstance(nar_int, dict) else {}
    if isinstance(n0, dict):
        return str(n0.get("plain_language") or "")
    return ""
