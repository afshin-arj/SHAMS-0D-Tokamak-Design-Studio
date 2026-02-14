from __future__ import annotations
from typing import Callable, Tuple
import math

def bisect(f, x_lo: float, x_hi: float, target: float, tol: float, max_iter: int = 80) -> Tuple[float, bool]:
    """
    Generic bisection root finder for monotonic functions.

    Returns (x_sol, ok). ok may be False if no bracket or non-finite values occur.
    """
    flo = f(x_lo) - target
    fhi = f(x_hi) - target
    if (not math.isfinite(flo)) or (not math.isfinite(fhi)) or (flo * fhi > 0):
        return x_lo, False
    lo, hi = x_lo, x_hi
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        fmid = f(mid) - target
        if not math.isfinite(fmid):
            return mid, False
        if abs(fmid) < tol:
            return mid, True
        if flo * fmid <= 0:
            hi = mid
            fhi = fmid
        else:
            lo = mid
            flo = fmid
    return 0.5 * (lo + hi), True
