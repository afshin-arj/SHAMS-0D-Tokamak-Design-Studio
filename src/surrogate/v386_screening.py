from __future__ import annotations

"""
Feasible-First Screening (v386)

- Harvests training data from cached artifacts.
- Builds a ridge surrogate for a scalar feasibility proxy (min margin).
- Screens a concept family and allocates a truth-evaluation budget.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import math
from pathlib import Path
import json

import numpy as np

from .v386_surrogate import extract_numeric_features, vectorize_features, fit_ridge, RidgeModel


def _walk_records(obj: Any, out: List[Dict[str, Any]]) -> None:
    """Recursively walk a structure collecting candidate-like dicts."""
    if isinstance(obj, dict):
        # common containers
        for k in ("records", "results", "candidates", "points", "grid", "front", "items"):
            v = obj.get(k)
            if isinstance(v, (list, tuple)):
                for it in v:
                    _walk_records(it, out)

        # record leaf
        keys = set(obj.keys())
        if ("inputs" in keys) and (("outputs" in keys) or ("artifact" in keys) or ("out" in keys) or ("result" in keys)):
            out.append(obj)
            return

        # otherwise recurse all values
        for v in obj.values():
            _walk_records(v, out)
    elif isinstance(obj, (list, tuple)):
        for it in obj:
            _walk_records(it, out)


def harvest_candidate_records(*sources: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in sources:
        _walk_records(s, out)
    # de-duplicate by stable json hash of inputs+outputs if possible
    uniq: Dict[str, Dict[str, Any]] = {}
    for r in out:
        inp = r.get("inputs")
        outp = r.get("outputs") or r.get("artifact") or r.get("out") or r.get("result")
        try:
            key = json.dumps({"inputs": inp, "outputs": outp}, sort_keys=True, default=str)
        except Exception:
            key = str(id(r))
        uniq[key] = r
    return list(uniq.values())


def _extract_constraints_container(outputs: Any) -> Optional[Any]:
    if not isinstance(outputs, dict):
        return None
    for k in ("constraints", "constraint_results", "cons", "constraints_table"):
        v = outputs.get(k)
        if v is not None:
            return v
    return None


def compute_min_margin(outputs: Any) -> Optional[float]:
    """Best-effort minimum margin (positive => feasible, negative => violated)."""
    if outputs is None:
        return None

    # direct
    if isinstance(outputs, dict):
        for k in ("min_margin", "minimum_margin", "min_margin_norm"):
            v = outputs.get(k)
            if isinstance(v, (int, float)) and math.isfinite(float(v)):
                return float(v)

    cons = _extract_constraints_container(outputs)
    if cons is None:
        # sometimes nested in artifact
        if isinstance(outputs, dict) and isinstance(outputs.get("artifact"), dict):
            return compute_min_margin(outputs.get("artifact"))
        return None

    margins: List[float] = []
    if isinstance(cons, list):
        for c in cons:
            if not isinstance(c, dict):
                continue
            for k in ("margin", "slack", "margin_norm", "signed_margin"):
                v = c.get(k)
                if isinstance(v, (int, float)) and math.isfinite(float(v)):
                    margins.append(float(v))
                    break
    elif isinstance(cons, dict):
        # dict of name->margin
        for v in cons.values():
            if isinstance(v, (int, float)) and math.isfinite(float(v)):
                margins.append(float(v))

    if margins:
        return float(min(margins))
    return None


@dataclass(frozen=True)
class ScreeningSpec:
    schema: str = "shams_surrogate_screening_spec.v386"
    accept_margin: float = 0.05
    reject_margin: float = -0.05
    max_truth_evals: int = 200
    ridge_alpha: float = 5.0


@dataclass
class ScreeningDecision:
    cid: str
    predicted_min_margin: float
    bucket: str  # "likely_feasible" | "uncertain" | "likely_infeasible"


@dataclass(frozen=True)
class ScreeningRunLedger:
    schema: str
    version: str
    model: Dict[str, Any]
    spec: Dict[str, Any]
    n_total: int
    n_truth_evaluated: int
    decisions: List[Dict[str, Any]]
    selected_for_truth: List[str]


def build_surrogate_min_margin(
    records: Sequence[Dict[str, Any]],
    *,
    alpha: float = 5.0,
    feature_names: Optional[Sequence[str]] = None,
) -> RidgeModel:
    feats_list: List[Dict[str, float]] = []
    y_list: List[float] = []

    for r in records:
        inp = r.get("inputs")
        outp = r.get("outputs") or r.get("artifact") or r.get("out") or r.get("result")
        if not isinstance(inp, dict):
            continue
        mm = compute_min_margin(outp)
        if mm is None or (not math.isfinite(float(mm))):
            continue
        feats_list.append(extract_numeric_features(inp))
        y_list.append(float(mm))

    if len(y_list) < 10:
        raise ValueError("Insufficient training data with min_margin for v386 surrogate (need >=10)")

    X, keys = vectorize_features(feats_list, feature_names=feature_names)
    y = np.asarray(y_list, dtype=float)

    model = fit_ridge(X, y, alpha=float(alpha))
    # fill feature names
    return RidgeModel(
        **{**model.__dict__, "feature_names": list(keys)}
    )


def screen_concept_family(
    *,
    concept_family: Any,
    model: RidgeModel,
    spec: ScreeningSpec,
) -> Tuple[List[ScreeningDecision], List[str]]:
    """Screen candidates in a concept family object (from src.extopt.family)."""

    # v385 family has fields: base_inputs, candidates: list with cid, overrides
    base_inputs = getattr(concept_family, "base_inputs", None)
    candidates = getattr(concept_family, "candidates", None)
    if not isinstance(base_inputs, dict) or not isinstance(candidates, list):
        raise ValueError("Unsupported concept family object for screening")

    decisions: List[ScreeningDecision] = []
    # vectorize all candidates
    feats_list: List[Dict[str, float]] = []
    cids: List[str] = []
    for c in candidates:
        cid = str(getattr(c, "cid", getattr(c, "id", "")))
        ov = getattr(c, "overrides", None)
        if not isinstance(ov, dict):
            ov = {}
        merged = dict(base_inputs)
        merged.update(ov)
        feats_list.append(extract_numeric_features(merged))
        cids.append(cid)

    X, _ = vectorize_features(feats_list, feature_names=model.feature_names)
    yhat = model.predict(X)

    for cid, yh in zip(cids, yhat):
        pm = float(yh)
        if pm >= float(spec.accept_margin):
            bucket = "likely_feasible"
        elif pm <= float(spec.reject_margin):
            bucket = "likely_infeasible"
        else:
            bucket = "uncertain"
        decisions.append(ScreeningDecision(cid=cid, predicted_min_margin=pm, bucket=bucket))

    # allocate truth eval budget: uncertain first (sorted by |margin| ascending), then likely_feasible (ascending)
    uncertain = [d for d in decisions if d.bucket == "uncertain"]
    likely = [d for d in decisions if d.bucket == "likely_feasible"]

    uncertain_sorted = sorted(uncertain, key=lambda d: abs(d.predicted_min_margin))
    likely_sorted = sorted(likely, key=lambda d: abs(d.predicted_min_margin))

    selected: List[str] = []
    for d in uncertain_sorted + likely_sorted:
        if len(selected) >= int(spec.max_truth_evals):
            break
        selected.append(d.cid)

    return decisions, selected


def build_screening_ledger(
    *,
    model: RidgeModel,
    spec: ScreeningSpec,
    decisions: List[ScreeningDecision],
    selected: List[str],
) -> ScreeningRunLedger:
    return ScreeningRunLedger(
        schema="shams_surrogate_screening_run_ledger.v386",
        version="v386.0.0",
        model={k: getattr(model, k) for k in model.__dataclass_fields__.keys()} if hasattr(model, "__dataclass_fields__") else model.__dict__,
        spec=spec.__dict__,
        n_total=len(decisions),
        n_truth_evaluated=len(selected),
        decisions=[d.__dict__ for d in decisions],
        selected_for_truth=list(selected),
    )
