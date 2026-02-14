from __future__ import annotations
"""Preference-Aware Decision Layer (v114)

Adds post-feasibility candidate annotation:
- Derived metric normalization across candidate set
- Composite scores with explicit weights
- Transparent rule-based modifiers
- Pareto set extraction across candidates (using derived metrics, not objectives)

This does NOT select a design; it annotates and highlights tradeoffs.
"""

from typing import Any, Dict, List, Optional, Tuple
import time
import math

from tools.preferences import validate_preferences, template_preferences


def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _is_num(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _norm(values: List[float], x: Optional[float], *, higher_is_better: bool) -> Optional[float]:
    if x is None or not _is_num(x):
        return None
    vals = [float(v) for v in values if _is_num(v)]
    if not vals:
        return None
    lo = min(vals); hi = max(vals)
    if abs(hi - lo) < 1e-12:
        return 0.5
    t = (float(x) - lo) / (hi - lo)
    t = _clamp01(t)
    return t if higher_is_better else (1.0 - t)


def _extract_metrics(candidate: Dict[str, Any]) -> Dict[str, Optional[float]]:
    inp = candidate.get("inputs", {}) if isinstance(candidate, dict) else {}
    feas = candidate.get("feasibility", {}) if isinstance(candidate, dict) else {}
    rob = candidate.get("robustness", {}) if isinstance(candidate, dict) else {}
    bd = candidate.get("boundary_distance_2d", {}) if isinstance(candidate, dict) else {}

    # margin: worst_hard_margin_frac (higher better)
    margin = feas.get("worst_hard_margin_frac")
    margin = float(margin) if _is_num(margin) else None

    # robustness: family_feasible_fraction (higher better)
    rob_frac = rob.get("family_feasible_fraction")
    rob_frac = float(rob_frac) if _is_num(rob_frac) else None

    # boundary_clearance: mean of available 2D boundary distances (higher better)
    bvals = []
    if isinstance(bd, dict):
        for v in bd.values():
            if _is_num(v):
                bvals.append(float(v))
    boundary_clearance = (sum(bvals) / len(bvals)) if bvals else None

    # size: smaller is better. use R0_m if available.
    size = inp.get("R0_m")
    size = float(size) if _is_num(size) else None

    # optional: field, current
    Bt = inp.get("Bt_T"); Bt = float(Bt) if _is_num(Bt) else None
    Ip = inp.get("Ip_MA"); Ip = float(Ip) if _is_num(Ip) else None

    return {
        "margin": margin,
        "robustness": rob_frac,
        "boundary_clearance": boundary_clearance,
        "size": size,
        "Bt_T": Bt,
        "Ip_MA": Ip,
    }


def annotate_candidates_with_preferences(
    *,
    candidates: List[Dict[str, Any]],
    preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    prefs = preferences if isinstance(preferences, dict) else template_preferences("v114")
    warnings = validate_preferences(prefs)
    weights = prefs.get("weights", {}) if isinstance(prefs.get("weights"), dict) else {}

    # Extract metrics and collect arrays for normalization
    metrics_list = []
    for c in candidates or []:
        metrics_list.append(_extract_metrics(c))

    def collect(key: str) -> List[float]:
        return [m[key] for m in metrics_list if m.get(key) is not None]  # type: ignore

    vals_margin = collect("margin")
    vals_rob = collect("robustness")
    vals_bc = collect("boundary_clearance")
    vals_size = collect("size")
    vals_Bt = collect("Bt_T")
    vals_Ip = collect("Ip_MA")

    annotated = []
    for c, m in zip(candidates or [], metrics_list):
        # normalized scores 0..1
        s_margin = _norm(vals_margin, m.get("margin"), higher_is_better=True)
        s_rob = _norm(vals_rob, m.get("robustness"), higher_is_better=True)
        s_bc = _norm(vals_bc, m.get("boundary_clearance"), higher_is_better=True)
        s_size = _norm(vals_size, m.get("size"), higher_is_better=False)  # smaller better
        s_Bt = _norm(vals_Bt, m.get("Bt_T"), higher_is_better=True)
        s_Ip = _norm(vals_Ip, m.get("Ip_MA"), higher_is_better=False)  # prefer lower current by default

        score_parts = {
            "margin": s_margin,
            "robustness": s_rob,
            "boundary_clearance": s_bc,
            "size": s_size,
        }

        # composite score: weighted average of available parts
        num = 0.0
        den = 0.0
        for k, sv in score_parts.items():
            if sv is None:
                continue
            w = float(weights.get(k, 0.0)) if _is_num(weights.get(k, 0.0)) else 0.0
            if w <= 0:
                continue
            num += w * float(sv)
            den += w
        composite = (num / den) if den > 0 else None

        modifiers = []
        comp2 = composite

        # transparent rules (optional)
        rules = prefs.get("rules", [])
        if isinstance(rules, list):
            for r in rules[:100]:
                if not isinstance(r, dict):
                    continue
                rtype = r.get("type")
                metric = r.get("metric")
                if not (isinstance(rtype, str) and isinstance(metric, str)):
                    continue
                penalty = r.get("penalty")
                weight = r.get("weight")
                # avoid rule: if candidate feasibility.worst_hard equals value
                if rtype == "avoid" and metric == "worst_hard":
                    eq = r.get("equals")
                    worst = ((c.get("feasibility") or {}) if isinstance(c, dict) else {}).get("worst_hard")
                    if isinstance(eq, str) and worst == eq and _is_num(penalty):
                        modifiers.append({"rule": r, "applied": True, "delta": -float(penalty)})
                        if comp2 is not None:
                            comp2 = max(0.0, float(comp2) - float(penalty))
                # prefer_high rule for a raw input metric
                if rtype == "prefer_high" and metric in ("Bt_T", "Ip_MA"):
                    sv = s_Bt if metric == "Bt_T" else None
                    if metric == "Ip_MA":
                        # "prefer_high Ip" not default; use s = 1 - s_Ip if computed
                        sv = (1.0 - s_Ip) if s_Ip is not None else None
                    if sv is not None and _is_num(weight):
                        delta = float(weight) * (float(sv) - 0.5)  # centered
                        modifiers.append({"rule": r, "applied": True, "delta": delta})
                        if comp2 is not None:
                            comp2 = _clamp01(float(comp2) + delta)

        c2 = dict(c)
        c2["preference_annotation"] = {
            "kind": "shams_preference_annotation",
            "created_utc": _created_utc(),
            "preferences_kind": prefs.get("kind"),
            "weights_used": weights,
            "scores_norm01": score_parts,
            "composite_score_norm01": composite,
            "composite_with_rules_norm01": comp2,
            "rule_modifiers": modifiers,
            "raw_metrics": m,
        }
        annotated.append(c2)

    # rank for convenience (not selection): by composite_with_rules then composite then None last
    def keyfun(c):
        pa = c.get("preference_annotation", {})
        a = pa.get("composite_with_rules_norm01")
        b = pa.get("composite_score_norm01")
        aval = float(a) if _is_num(a) else -1.0
        bval = float(b) if _is_num(b) else -1.0
        return (aval, bval)

    annotated_sorted = sorted(annotated, key=keyfun, reverse=True)

    return {
        "kind": "shams_preference_annotation_bundle",
        "created_utc": _created_utc(),
        "warnings": warnings,
        "preferences": prefs,
        "n_candidates": len(candidates or []),
        "candidates_annotated": annotated_sorted,
    }


def pareto_front_indices(
    rows: List[Dict[str, Any]],
    objectives: List[Tuple[str, bool]],
) -> List[int]:
    """Return indices of non-dominated rows.

    objectives: list of (key, higher_is_better)
    A dominates B if it is >= in all objectives (after direction) and > in at least one.
    Missing values count as worst.
    """
    def val(row, key, hib):
        v = row.get(key)
        if not _is_num(v):
            return -1e99 if hib else 1e99
        return float(v) if hib else -float(v)

    n = len(rows)
    nd = []
    for i in range(n):
        dominated = False
        for j in range(n):
            if i == j:
                continue
            better_or_eq_all = True
            strictly_better = False
            for key, hib in objectives:
                vi = val(rows[i], key, hib)
                vj = val(rows[j], key, hib)
                if vj < vi:
                    better_or_eq_all = False
                    break
                if vj > vi:
                    strictly_better = True
            if better_or_eq_all and strictly_better:
                dominated = True
                break
        if not dominated:
            nd.append(i)
    return nd


def build_pareto_sets(bundle: Dict[str, Any]) -> Dict[str, Any]:
    cands = bundle.get("candidates_annotated", [])
    if not isinstance(cands, list) or not cands:
        return {"kind":"shams_pareto_sets", "created_utc": _created_utc(), "sets": []}

    # derive table rows for pareto using norm scores (margin, robustness, boundary_clearance) and size (prefer high score already inverted)
    rows = []
    for c in cands:
        pa = c.get("preference_annotation", {}) if isinstance(c, dict) else {}
        s = pa.get("scores_norm01", {}) if isinstance(pa, dict) else {}
        rows.append({
            "candidate_id": c.get("source_artifact_id"),
            "margin": s.get("margin"),
            "robustness": s.get("robustness"),
            "boundary_clearance": s.get("boundary_clearance"),
            "size": s.get("size"),
            "composite": pa.get("composite_with_rules_norm01"),
        })

    # primary pareto: robustness, margin, boundary_clearance (all higher better) and size (higher means smaller better)
    objectives = [("robustness", True), ("margin", True), ("boundary_clearance", True), ("size", True)]
    idx = pareto_front_indices(rows, objectives)

    front = [rows[i] for i in idx]
    # secondary: pareto of (composite, robustness) as a simplified view
    idx2 = pareto_front_indices(rows, [("composite", True), ("robustness", True)])
    front2 = [rows[i] for i in idx2]

    return {
        "kind": "shams_pareto_sets",
        "created_utc": _created_utc(),
        "sets": [
            {"name":"pareto_robust_margin_boundary_size", "objectives": objectives, "members": front},
            {"name":"pareto_composite_vs_robustness", "objectives": [("composite", True), ("robustness", True)], "members": front2},
        ],
    }
