"""Budgeted multi-knob certified search (v296.0).

This is a deterministic exploration utility that runs *outside* the frozen evaluator
and returns a proof-carrying trace. It is not an internal optimizer.

Key properties:
- Fixed evaluation budget.
- Deterministic sampling given a seed.
- Every candidate is verified by the frozen evaluator (call site provides verifier).

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple, Any, Optional
import hashlib
import json
import math

import numpy as np


@dataclass(frozen=True)
class SearchVar:
    name: str
    lo: float
    hi: float


@dataclass(frozen=True)
class SearchSpec:
    variables: Tuple[SearchVar, ...]
    budget: int = 128
    seed: int = 0
    method: str = "lhs"  # lhs | grid


@dataclass(frozen=True)
class SearchRecord:
    i: int
    x: Dict[str, float]
    verdict: str
    score: float
    evidence: Dict[str, Any]


@dataclass(frozen=True)
class SearchResult:
    spec: SearchSpec
    records: Tuple[SearchRecord, ...]
    best_index: Optional[int]
    best_record: Optional[SearchRecord]
    digest: str


def _lhs(n: int, d: int, rng: np.random.Generator) -> np.ndarray:
    # Latin hypercube sampling in [0,1]
    cut = np.linspace(0.0, 1.0, n + 1)
    u = rng.random((n, d))
    a = cut[:n]
    b = cut[1:n + 1]
    rd = u * (b - a)[:, None] + a[:, None]
    H = np.zeros_like(rd)
    for j in range(d):
        order = rng.permutation(n)
        H[:, j] = rd[order, 0]
        rd = np.roll(rd, -1, axis=1)
    return H


def run_budgeted_search(
    base_inputs: Any,
    spec: SearchSpec,
    verifier: Callable[[Any], Tuple[str, float, Dict[str, Any]]],
    builder: Callable[[Any, Dict[str, float]], Any],
) -> SearchResult:
    """Run deterministic budgeted search.

    Args:
        base_inputs: base PointInputs-like object.
        spec: SearchSpec.
        verifier: function(candidate_inputs)->(verdict, score, evidence).
        builder: function(base_inputs, overrides)->candidate_inputs.

    Returns:
        SearchResult with full trace.
    """

    vars_ = list(spec.variables)
    d = len(vars_)
    n = int(max(1, spec.budget))
    rng = np.random.default_rng(int(spec.seed))

    if spec.method == "grid":
        k = int(round(n ** (1.0 / max(1, d))))
        lin = np.linspace(0.0, 1.0, k)
        mesh = np.stack(np.meshgrid(*([lin] * d), indexing="ij"), axis=-1).reshape(-1, d)
        U = mesh[:n]
    else:
        U = _lhs(n, d, rng)

    records: List[SearchRecord] = []
    best_i: Optional[int] = None
    best_rec: Optional[SearchRecord] = None

    for i in range(U.shape[0]):
        u = U[i]
        overrides: Dict[str, float] = {}
        for j, v in enumerate(vars_):
            xj = v.lo + float(u[j]) * (v.hi - v.lo)
            overrides[v.name] = float(xj)
        cand = builder(base_inputs, overrides)
        verdict, score, evidence = verifier(cand)
        rec = SearchRecord(i=i, x=overrides, verdict=str(verdict), score=float(score), evidence=dict(evidence))
        records.append(rec)
        if verdict == "PASS":
            if best_rec is None or score > best_rec.score:
                best_rec = rec
                best_i = i

    # deterministic digest
    payload = {
        "spec": {
            "variables": [v.__dict__ for v in vars_],
            "budget": spec.budget,
            "seed": spec.seed,
            "method": spec.method,
        },
        "best_index": best_i,
        "records": [
            {"i": r.i, "x": r.x, "verdict": r.verdict, "score": r.score} for r in records
        ],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()

    return SearchResult(
        spec=spec,
        records=tuple(records),
        best_index=best_i,
        best_record=best_rec,
        digest=digest,
    )
