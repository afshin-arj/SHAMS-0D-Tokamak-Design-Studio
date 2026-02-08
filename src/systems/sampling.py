from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, List
import random


@dataclass(frozen=True)
class SamplePoint:
    """A sampled point in variable space."""

    name: str
    values: Dict[str, float]


def _mid(lo: float, hi: float) -> float:
    return 0.5 * (float(lo) + float(hi))


def generate_precheck_samples(
    variables: Dict[str, Tuple[float, float, float]],
    *,
    include_random: bool = True,
    n_random: int = 8,
    seed: int = 1337,
) -> List[SamplePoint]:
    """Generate a small, information-rich, deterministic sample set.

    This replaces corner-only precheck for high-dimensional problems.

    Samples included:
    - all-low, all-high
    - midpoint
    - one-at-a-time flips low->high and high->low for each variable
    - optional random uniform samples (deterministic seed)
    """

    keys = list(variables.keys())
    bounds = {k: (float(variables[k][1]), float(variables[k][2])) for k in keys}

    def mk(name: str, assign: Dict[str, float]) -> SamplePoint:
        return SamplePoint(name=name, values={k: float(assign[k]) for k in keys})

    lo = {k: bounds[k][0] for k in keys}
    hi = {k: bounds[k][1] for k in keys}
    mid = {k: _mid(bounds[k][0], bounds[k][1]) for k in keys}

    samples: List[SamplePoint] = [
        mk('all_low', lo),
        mk('all_high', hi),
        mk('mid', mid),
    ]

    # One-at-a-time flips around midpoint to learn local sensitivity.
    for k in keys:
        s1 = dict(mid)
        s1[k] = hi[k]
        samples.append(mk(f'{k}_hi', s1))
        s2 = dict(mid)
        s2[k] = lo[k]
        samples.append(mk(f'{k}_lo', s2))

    if include_random and n_random > 0:
        rng = random.Random(int(seed))
        for i in range(int(n_random)):
            r = {}
            for k in keys:
                a, b = bounds[k]
                r[k] = a + (b - a) * rng.random()
            samples.append(mk(f'rand_{i+1}', r))

    # Deduplicate (can happen if bounds are degenerate).
    seen = set()
    uniq: List[SamplePoint] = []
    for sp in samples:
        sig = tuple((k, round(float(sp.values[k]), 12)) for k in keys)
        if sig in seen:
            continue
        seen.add(sig)
        uniq.append(sp)
    return uniq
