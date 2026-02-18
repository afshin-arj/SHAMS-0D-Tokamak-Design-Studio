from __future__ import annotations

"""
Feasible-First Surrogate Accelerator (v386)

Non-authoritative surrogate utilities for screening/ranking candidate designs.

Hard laws:
- Never replaces frozen truth.
- Deterministic and audit-friendly.
- Any stochastic component must be explicitly seeded and recorded.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import math
import numpy as np


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float, np.integer, np.floating)) and not isinstance(x, bool)


def _to_float(x: Any) -> Optional[float]:
    if _is_number(x):
        xf = float(x)
        if math.isfinite(xf):
            return xf
    if isinstance(x, bool):
        return 1.0 if x else 0.0
    return None


def extract_numeric_features(
    inputs: Dict[str, Any],
    *,
    include_bools: bool = True,
    allow_nan: bool = False,
) -> Dict[str, float]:
    """Extract scalar numeric features from an inputs dict (flat). Deterministic key order is handled later."""
    feats: Dict[str, float] = {}
    for k, v in inputs.items():
        if isinstance(v, (dict, list, tuple)):
            continue  # flat features only (v386.0.0)
        if isinstance(v, bool) and include_bools:
            feats[k] = 1.0 if v else 0.0
            continue
        xf = _to_float(v)
        if xf is None:
            continue
        if (not allow_nan) and (not math.isfinite(xf)):
            continue
        feats[k] = xf
    return feats


def vectorize_features(
    feats_list: Sequence[Dict[str, float]],
    *,
    feature_names: Optional[Sequence[str]] = None,
) -> Tuple[np.ndarray, List[str]]:
    """Vectorize feature dicts into X with stable feature ordering."""
    if feature_names is None:
        keys = sorted({k for d in feats_list for k in d.keys()})
    else:
        keys = list(feature_names)
    X = np.zeros((len(feats_list), len(keys)), dtype=float)
    for i, d in enumerate(feats_list):
        for j, k in enumerate(keys):
            if k in d:
                X[i, j] = float(d[k])
    return X, keys


@dataclass(frozen=True)
class RidgeModel:
    schema: str
    version: str
    feature_names: List[str]
    x_mean: List[float]
    x_std: List[float]
    alpha: float
    weights: List[float]
    bias: float
    y_mean: float
    y_std: float
    train_rmse: float
    train_n: int

    def predict(self, X: np.ndarray) -> np.ndarray:
        w = np.asarray(self.weights, dtype=float)
        mu = np.asarray(self.x_mean, dtype=float)
        sd = np.asarray(self.x_std, dtype=float)
        Xn = (X - mu) / sd
        yhat = Xn @ w + float(self.bias)
        # unnormalize y
        return yhat * float(self.y_std) + float(self.y_mean)


def fit_ridge(
    X: np.ndarray,
    y: np.ndarray,
    *,
    alpha: float = 1.0,
) -> RidgeModel:
    """Deterministic ridge regression with standardization."""
    if X.ndim != 2:
        raise ValueError("X must be 2D")
    if y.ndim != 1:
        raise ValueError("y must be 1D")
    if X.shape[0] != y.shape[0]:
        raise ValueError("X and y length mismatch")
    n, d = X.shape
    if n < 5:
        raise ValueError("Need at least 5 training samples for v386 ridge surrogate")

    x_mean = X.mean(axis=0)
    x_std = X.std(axis=0)
    x_std = np.where(x_std <= 0.0, 1.0, x_std)
    Xn = (X - x_mean) / x_std

    y_mean = float(y.mean())
    y_std = float(y.std())
    if y_std <= 0.0:
        y_std = 1.0
    yn = (y - y_mean) / y_std

    # closed form: w = (X^T X + alpha I)^-1 X^T y
    A = Xn.T @ Xn + float(alpha) * np.eye(d)
    b = Xn.T @ yn
    w = np.linalg.solve(A, b)
    bias = float(yn.mean() - (Xn.mean(axis=0) @ w))  # should be ~0 but keep robust

    yhat_n = Xn @ w + bias
    rmse = float(np.sqrt(np.mean((yhat_n - yn) ** 2)))

    return RidgeModel(
        schema="shams_surrogate_ridge.v386",
        version="v386.0.0",
        feature_names=[],  # filled by caller
        x_mean=[float(v) for v in x_mean],
        x_std=[float(v) for v in x_std],
        alpha=float(alpha),
        weights=[float(v) for v in w],
        bias=float(bias),
        y_mean=float(y_mean),
        y_std=float(y_std),
        train_rmse=float(rmse),
        train_n=int(n),
    )
