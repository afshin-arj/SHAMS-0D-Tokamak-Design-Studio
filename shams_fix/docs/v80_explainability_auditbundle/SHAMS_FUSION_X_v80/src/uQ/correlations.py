
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple
import random
import math

@dataclass
class CorrelatedSpec:
    keys: List[str]
    corr: List[List[float]]  # symmetric
    sigmas: Dict[str, float] # stdev for each key

def _cholesky(a: List[List[float]]) -> List[List[float]]:
    n = len(a)
    L = [[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1):
            s = sum(L[i][k]*L[j][k] for k in range(j))
            if i == j:
                v = a[i][i] - s
                L[i][j] = math.sqrt(max(v, 0.0))
            else:
                if L[j][j] == 0:
                    L[i][j] = 0.0
                else:
                    L[i][j] = (a[i][j] - s) / L[j][j]
    return L

def sample_correlated_normals(spec: CorrelatedSpec, n: int, rng_seed: int | None=None) -> List[Dict[str,float]]:
    """Generate correlated normal samples with mean 0 and given sigmas."""
    if rng_seed is not None:
        random.seed(rng_seed)
    L=_cholesky(spec.corr)
    out=[]
    for _ in range(n):
        z=[random.gauss(0.0,1.0) for _ in spec.keys]
        y=[sum(L[i][k]*z[k] for k in range(i+1)) for i in range(len(spec.keys))]
        sample={k: y[i]*float(spec.sigmas.get(k,1.0)) for i,k in enumerate(spec.keys)}
        out.append(sample)
    return out
