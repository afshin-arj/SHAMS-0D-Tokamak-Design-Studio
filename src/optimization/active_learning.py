"""Active learning harness (v296.0).

Non-authoritative driver utilities:
- propose new points where surrogate uncertainty is high.
- proposals must be verified by SHAMS truth.

Deterministic sampling with a seed.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np

from .surrogates import SurrogateModel, predict_surrogate


@dataclass(frozen=True)
class ALVar:
    name: str
    lo: float
    hi: float


@dataclass(frozen=True)
class ALProposal:
    x: Dict[str, float]
    y_pred: float
    uncertainty: float


def propose_active_learning_points(
    model: SurrogateModel,
    vars_: List[ALVar],
    n_candidates: int = 512,
    n_select: int = 16,
    seed: int = 0,
) -> List[ALProposal]:
    """Propose points with maximum surrogate uncertainty.

    Uses Latin hypercube sampling in the input box.
    """

    d = len(vars_)
    rng = np.random.default_rng(int(seed))
    n = int(max(1, n_candidates))

    # LHS in [0,1]
    cut = np.linspace(0.0, 1.0, n + 1)
    u = rng.random((n, d))
    a = cut[:n]
    b = cut[1:n+1]
    rd = u * (b - a)[:, None] + a[:, None]
    U = np.zeros_like(rd)
    for j in range(d):
        order = rng.permutation(n)
        U[:, j] = rd[order, 0]
        rd = np.roll(rd, -1, axis=1)

    props: List[ALProposal] = []
    for i in range(n):
        x: Dict[str, float] = {}
        for j,v in enumerate(vars_):
            x[v.name] = float(v.lo + U[i,j]*(v.hi - v.lo))
        yhat, unc = predict_surrogate(model, x)
        props.append(ALProposal(x=x, y_pred=float(yhat), uncertainty=float(unc)))

    props.sort(key=lambda p: (p.uncertainty, p.y_pred), reverse=True)
    return props[: int(max(1, n_select))]
