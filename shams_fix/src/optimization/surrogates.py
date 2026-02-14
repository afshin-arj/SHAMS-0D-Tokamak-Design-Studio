"""Non-authoritative surrogate overlays (v296.0).

Purpose:
- provide fast visualization and candidate proposals.
- never authoritative; all outputs must be verified by frozen truth.

Implementation:
- deterministic ridge regression on standardized features.
- uncertainty proxy based on distance to nearest training point.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import numpy as np


@dataclass(frozen=True)
class SurrogateModel:
    feature_names: Tuple[str, ...]
    x_mean: np.ndarray
    x_std: np.ndarray
    w: np.ndarray
    b: float
    ridge: float
    x_train: np.ndarray


def fit_ridge_surrogate(
    samples: List[Dict[str, float]],
    targets: List[float],
    feature_names: List[str],
    ridge: float = 1e-6,
) -> SurrogateModel:
    if len(samples) != len(targets):
        raise ValueError("samples and targets length mismatch")
    if len(samples) == 0:
        raise ValueError("no samples")

    X = np.array([[float(s.get(f, 0.0)) for f in feature_names] for s in samples], dtype=float)
    y = np.array([float(t) for t in targets], dtype=float)

    x_mean = X.mean(axis=0)
    x_std = X.std(axis=0)
    x_std = np.where(x_std <= 0.0, 1.0, x_std)

    Xs = (X - x_mean) / x_std

    # Ridge: solve (Xs^T Xs + ridge I) w = Xs^T y
    A = Xs.T @ Xs + ridge * np.eye(Xs.shape[1])
    w = np.linalg.solve(A, Xs.T @ y)
    b = float(y.mean())
    # center y by mean in weights by augmenting? keep simple: predict = b + (Xs @ w - mean(Xs@w))
    pred0 = Xs @ w
    b = float(y.mean() - pred0.mean())

    return SurrogateModel(
        feature_names=tuple(feature_names),
        x_mean=x_mean,
        x_std=x_std,
        w=w,
        b=b,
        ridge=float(ridge),
        x_train=X.copy(),
    )


def predict_surrogate(model: SurrogateModel, x: Dict[str, float]) -> Tuple[float, float]:
    """Predict value and uncertainty proxy."""
    xv = np.array([float(x.get(f, 0.0)) for f in model.feature_names], dtype=float)
    xs = (xv - model.x_mean) / model.x_std
    yhat = float(model.b + xs @ model.w)

    # uncertainty proxy: min distance to train in standardized space
    if model.x_train.shape[0] == 0:
        unc = 1.0
    else:
        Xs_train = (model.x_train - model.x_mean) / model.x_std
        d = np.sqrt(((Xs_train - xs) ** 2).sum(axis=1))
        unc = float(np.min(d))
    return yhat, unc
