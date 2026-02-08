from __future__ import annotations

"""Feasible-first surrogate acceleration (v316.0).

This module is intentionally **non-authoritative** and lives strictly in the exploration
layer. It must NOT modify frozen truth.

Workflow
  1) Train a lightweight deterministic surrogate (ridge regression) for a chosen objective.
  2) Train a deterministic surrogate for feasibility using the *verified* hard-margin
     proxy (min_margin_frac). We do **not** perform probabilistic classification.
  3) Sample a candidate pool uniformly within bounds.
  4) Rank by a deterministic acquisition: predicted improvement + kappa*uncertainty,
     filtered by predicted feasibility (margin > 0).

Uncertainty proxy
  - residual std from training
  - distance-to-nearest training point in normalized knob space
  - uncertainty = sigma * d_nn

All randomization is controlled by an explicit seed.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import math
import random

import numpy as np


@dataclass(frozen=True)
class SurrogateFit:
    keys: Tuple[str, ...]
    x_mean: np.ndarray  # (d,)
    x_scale: np.ndarray  # (d,)
    w: np.ndarray  # (p,) including bias term
    resid_sigma: float
    x_train_n: np.ndarray  # (n,d) normalized


def _validate_bounds(bounds: Mapping[str, Tuple[float, float]]) -> Dict[str, Tuple[float, float]]:
    bb: Dict[str, Tuple[float, float]] = {}
    for k, (lo, hi) in bounds.items():
        lo_f = float(lo)
        hi_f = float(hi)
        if not math.isfinite(lo_f) or not math.isfinite(hi_f) or hi_f <= lo_f:
            raise ValueError(f"Invalid bounds for {k}: ({lo}, {hi})")
        bb[str(k)] = (lo_f, hi_f)
    return bb


def _poly2_features(xn: np.ndarray) -> np.ndarray:
    """Deterministic quadratic feature map with bias.

    For d dims:
      - 1 bias
      - d linear
      - d squares
      - d*(d-1)/2 cross terms
    """
    n, d = xn.shape
    cols: List[np.ndarray] = [np.ones((n, 1), dtype=float), xn]
    cols.append(xn * xn)
    # cross terms
    cross = []
    for i in range(d):
        for j in range(i + 1, d):
            cross.append((xn[:, i] * xn[:, j]).reshape(n, 1))
    if cross:
        cols.append(np.concatenate(cross, axis=1))
    return np.concatenate(cols, axis=1)


def _ridge_fit(x: np.ndarray, y: np.ndarray, *, alpha: float) -> Tuple[np.ndarray, float]:
    """Closed-form ridge regression fit: w = (X^T X + aI)^{-1} X^T y."""
    X = x
    yv = y.reshape(-1, 1)
    p = X.shape[1]
    A = X.T @ X
    A = A + float(alpha) * np.eye(p)
    b = X.T @ yv
    w = np.linalg.solve(A, b).reshape(-1)
    resid = (X @ w.reshape(-1, 1) - yv).reshape(-1)
    # unbiased-ish sigma proxy
    dof = max(1, int(len(resid) - p))
    sigma = float(np.sqrt(float(np.sum(resid * resid)) / float(dof)))
    return w, sigma


def fit_surrogate(
    records: Sequence[Mapping[str, Any]],
    *,
    knob_keys: Sequence[str],
    target_key: str,
    alpha: float = 1e-3,
) -> SurrogateFit:
    """Fit a deterministic surrogate from tabular study records."""
    keys = tuple(str(k) for k in knob_keys)
    if not keys:
        raise ValueError("No knob keys provided")
    xs: List[List[float]] = []
    ys: List[float] = []
    for r in records:
        try:
            row = [float(r[k]) for k in keys]
            yv = float(r[target_key])
        except Exception:
            continue
        if not all(math.isfinite(v) for v in row) or not math.isfinite(yv):
            continue
        xs.append(row)
        ys.append(yv)
    if len(xs) < max(8, 2 * len(keys) + 1):
        raise ValueError(f"Insufficient training rows: {len(xs)}")

    X = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)

    x_mean = np.mean(X, axis=0)
    x_scale = np.std(X, axis=0)
    x_scale = np.where(x_scale <= 1e-12, 1.0, x_scale)
    Xn = (X - x_mean) / x_scale
    Phi = _poly2_features(Xn)
    w, sigma = _ridge_fit(Phi, y, alpha=float(alpha))
    return SurrogateFit(
        keys=keys,
        x_mean=x_mean,
        x_scale=x_scale,
        w=w,
        resid_sigma=float(sigma),
        x_train_n=Xn,
    )


def predict(fit: SurrogateFit, x: Mapping[str, float] | Sequence[float]) -> float:
    """Predict surrogate output for one point."""
    if isinstance(x, Mapping):
        xv = np.asarray([float(x[k]) for k in fit.keys], dtype=float)
    else:
        xv = np.asarray(list(x), dtype=float)
    xn = (xv - fit.x_mean) / fit.x_scale
    Phi = _poly2_features(xn.reshape(1, -1))
    return float(Phi.reshape(-1) @ fit.w.reshape(-1))


def uncertainty(fit: SurrogateFit, x: Mapping[str, float]) -> float:
    """Deterministic uncertainty proxy: sigma * d_nn(normalized)."""
    xv = np.asarray([float(x[k]) for k in fit.keys], dtype=float)
    xn = (xv - fit.x_mean) / fit.x_scale
    # nearest neighbor distance in normalized space
    dif = fit.x_train_n - xn.reshape(1, -1)
    d2 = np.sum(dif * dif, axis=1)
    d_nn = float(np.sqrt(float(np.min(d2)))) if d2.size else 0.0
    return float(fit.resid_sigma * d_nn)


def propose_candidates(
    *,
    records: Sequence[Mapping[str, Any]],
    bounds: Mapping[str, Tuple[float, float]],
    objective_key: str,
    objective_sense: str,
    feasibility_margin_key: str = "min_margin_frac",
    n_pool: int = 4000,
    n_propose: int = 32,
    seed: int = 7,
    kappa: float = 0.5,
    ridge_alpha: float = 1e-3,
) -> List[Dict[str, float]]:
    """Propose a batch of candidate knob points (dicts) within bounds."""
    bb = _validate_bounds(bounds)
    keys = tuple(bb.keys())
    if objective_sense not in ("min", "max"):
        raise ValueError(f"objective_sense must be 'min' or 'max', got {objective_sense}")

    # Train surrogates on *feasible* subset if available, else all records.
    rec_all = list(records)
    rec_feas = [r for r in rec_all if bool(r.get("is_feasible", False))]
    train_recs = rec_feas if len(rec_feas) >= 16 else rec_all

    fit_obj = fit_surrogate(train_recs, knob_keys=keys, target_key=objective_key, alpha=float(ridge_alpha))
    fit_mrg = fit_surrogate(train_recs, knob_keys=keys, target_key=feasibility_margin_key, alpha=float(ridge_alpha))

    # Baseline best verified objective among feasible points
    feas_vals: List[float] = []
    for r in rec_feas:
        try:
            feas_vals.append(float(r[objective_key]))
        except Exception:
            pass
    if not feas_vals:
        # fallback: use all
        for r in rec_all:
            try:
                feas_vals.append(float(r[objective_key]))
            except Exception:
                pass
    if not feas_vals:
        raise ValueError(f"No finite objective values found for {objective_key}")

    best = float(min(feas_vals) if objective_sense == "min" else max(feas_vals))

    rng = random.Random(int(seed))
    pool_n = max(50, int(n_pool))
    props: List[Tuple[float, Dict[str, float]]] = []
    for _ in range(pool_n):
        x: Dict[str, float] = {}
        for k, (lo, hi) in bb.items():
            x[k] = float(lo + rng.random() * (hi - lo))
        pred_m = float(predict(fit_mrg, x))
        if not math.isfinite(pred_m) or pred_m <= 0.0:
            continue
        pred_y = float(predict(fit_obj, x))
        if not math.isfinite(pred_y):
            continue
        # improvement (positive is good)
        if objective_sense == "min":
            imp = float(best - pred_y)
        else:
            imp = float(pred_y - best)
        u = float(uncertainty(fit_obj, x))
        score = float(imp + float(kappa) * u)
        props.append((score, x))

    props.sort(key=lambda t: float(t[0]), reverse=True)
    out: List[Dict[str, float]] = []
    seen: set[Tuple[float, ...]] = set()
    for _, x in props:
        key = tuple(round(float(x[k]), 12) for k in keys)
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(x))
        if len(out) >= int(n_propose):
            break
    return out


def verify_candidates_as_rows(
    *,
    evaluator: Any,
    base_inputs: Any,
    candidates: Sequence[Mapping[str, float]],
    objectives: Sequence[str],
    objective_senses: Mapping[str, str],
    policy: Mapping[str, Any] | None = None,
    include_outputs: bool = False,
) -> List[Dict[str, Any]]:
    """Verify candidate knob points against frozen truth.

    Returns rows compatible with trade_studies.runner output schema.

    Notes
    - `evaluator` is expected to expose `.evaluate(PointInputs)`.
    - `base_inputs` is expected to be a dataclass-like PointInputs.
    """
    from dataclasses import asdict

    from constraints.constraints import evaluate_constraints
    from constraints.bookkeeping import summarize as summarize_constraints
    from models.inputs import PointInputs
    from optimization.objectives import get_objective

    base_d = asdict(base_inputs)
    rows: List[Dict[str, Any]] = []
    for i, x in enumerate(candidates):
        dd = dict(base_d)
        for k, v in x.items():
            if k in dd:
                dd[k] = float(v)
        inp = PointInputs(**dd)
        res = evaluator.evaluate(inp)
        out = dict(res.out or {})
        cons = evaluate_constraints(out, policy=dict(policy) if policy else None)
        summ = summarize_constraints(cons).to_dict()
        feas = bool(summ.get("feasible", False))
        mmin = summ.get("worst_hard_margin_frac", None)
        try:
            mmin_f = float(mmin) if mmin is not None else float("nan")
        except Exception:
            mmin_f = float("nan")

        row: Dict[str, Any] = {
            "i": int(i),
            "is_feasible": bool(feas),
            "min_margin_frac": float(mmin_f),
        }
        row.update({str(k): float(v) for k, v in x.items()})

        for obj in objectives:
            spec = get_objective(str(obj))
            if spec is None:
                continue
            try:
                row[str(obj)] = float(spec.fn(out))
            except Exception:
                row[str(obj)] = float("nan")

        row["dominant_mechanism"] = str(summ.get("dominant_mechanism", ""))
        row["dominant_constraint"] = str(summ.get("dominant_constraint", ""))
        row["objective_senses"] = dict(objective_senses)

        if include_outputs:
            row["outputs"] = out
            row["constraints_summary"] = summ
        rows.append(row)
    return rows
