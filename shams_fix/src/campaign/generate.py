from __future__ import annotations

"""Deterministic candidate generation (v363.0).

Modes
-----
- grid: Cartesian grid (truncated) over continuous variables.
- lhs: Latin Hypercube Sampling (seeded).
- sobol: Low-discrepancy sequence using Halton bases (seeded scramble).
- passthrough: use provided candidates.

This module never performs optimization.

© 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import hashlib
import math

import numpy as np

from .spec import CampaignSpec, CampaignVariable


_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]


def _stable_sha256(obj: Any) -> str:
    b = repr(obj).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def _halton(i: int, base: int) -> float:
    """Halton radical inverse in (0,1)."""
    f = 1.0
    r = 0.0
    x = int(i)
    b = int(base)
    while x > 0:
        f /= float(b)
        r += f * float(x % b)
        x //= b
    return float(r)


def _halton_sequence(n: int, d: int, *, seed: int) -> np.ndarray:
    """Deterministic low-discrepancy points in [0,1)^d.

    Implemented as Halton with a deterministic Cranley-Patterson rotation
    (seeded) to reduce axis artifacts.
    """
    if d > len(_PRIMES):
        raise ValueError("dimension too large for Halton primes")

    pts = np.zeros((n, d), dtype=float)
    for j in range(d):
        base = _PRIMES[j]
        for i in range(n):
            pts[i, j] = _halton(i + 1, base)

    rng = np.random.default_rng(int(seed))
    rot = rng.random(d)
    pts = (pts + rot) % 1.0
    return pts


def _lhs(n: int, d: int, *, seed: int) -> np.ndarray:
    """Latin Hypercube in [0,1)^d (seeded)."""
    rng = np.random.default_rng(int(seed))
    # stratify each dimension
    cut = np.linspace(0.0, 1.0, n + 1)
    u = rng.random((n, d))
    a = cut[:n]
    b = cut[1:]
    pts = u * (b - a)[:, None] + a[:, None]
    # independent shuffles per dimension
    for j in range(d):
        rng.shuffle(pts[:, j])
    return pts


def _grid(n: int, d: int) -> np.ndarray:
    if d <= 0:
        return np.zeros((0, 0), dtype=float)
    k = int(max(2, round(float(n) ** (1.0 / float(d)))))
    axes = [np.linspace(0.0, 1.0, k) for _ in range(d)]
    mesh = np.meshgrid(*axes, indexing="ij")
    pts = np.stack([m.reshape(-1) for m in mesh], axis=1)
    if pts.shape[0] > n:
        pts = pts[:n, :]
    return pts


def _scale_var(v: CampaignVariable, u: float) -> Any:
    kind = str(v.kind or "float").lower().strip()
    if kind == "choice":
        vals = list(v.values or [])
        if not vals:
            raise ValueError(f"choice variable '{v.name}' has no values")
        idx = int(math.floor(u * len(vals)))
        idx = max(0, min(len(vals) - 1, idx))
        return vals[idx]
    lo = float(v.lo)
    hi = float(v.hi)
    x = lo + float(u) * (hi - lo)
    if kind == "int":
        return int(round(x))
    return float(x)


def generate_candidates(
    spec: CampaignSpec,
    *,
    provided_candidates: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Generate deterministic candidate inputs for a campaign."""
    spec.validate()
    mode = str(spec.generator.mode or "sobol").lower().strip()
    n = int(spec.generator.n)
    seed = int(spec.generator.seed)

    vars_ = list(spec.variables)
    d = len(vars_)

    if mode == "passthrough":
        if not provided_candidates:
            raise ValueError("passthrough mode requires provided_candidates")
        out: List[Dict[str, Any]] = []
        for row in provided_candidates:
            if not isinstance(row, dict):
                continue
            out.append(dict(row))
        return out

    if d == 0:
        return [{} for _ in range(n)]

    if mode == "grid":
        U = _grid(n, d)
    elif mode == "lhs":
        U = _lhs(n, d, seed=seed)
    elif mode == "sobol":
        U = _halton_sequence(n, d, seed=seed)
    else:
        raise ValueError(f"unknown generator mode: {mode}")

    cands: List[Dict[str, Any]] = []
    for i in range(U.shape[0]):
        dct: Dict[str, Any] = {}
        for j, v in enumerate(vars_):
            dct[v.name] = _scale_var(v, float(U[i, j]))
        # deterministic candidate id (stable)
        dct["cid"] = _stable_sha256((spec.name, i, dct))[:16]
        cands.append(dct)
    return cands
