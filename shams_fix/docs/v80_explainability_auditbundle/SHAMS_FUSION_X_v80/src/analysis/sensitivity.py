from __future__ import annotations
"""Sensitivity and uncertainty utilities.

This module provides a Monte Carlo wrapper around SHAMS evaluation:
- perturb uncertain knobs (H98, lambda_q, Zeff, CD efficiency, HTS Jc, ...)
- compute probability of feasibility and the most common violated constraints

Used to answer: "Is this point robust or razor-thin?"
"""

import math
import random
from dataclasses import asdict, replace
from typing import Dict, List, Tuple, Callable, Optional

from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from constraints.system import build_constraints_from_outputs

def _rand_lognormal(mu: float, sigma: float) -> float:
    # mu,sigma in linear space, approximate by sampling in log space
    if mu <= 0:
        return mu
    return math.exp(random.gauss(math.log(mu), sigma))

def monte_carlo_feasibility(
    base: PointInputs,
    n: int = 200,
    *,
    # relative uncertainties (1-sigma) on multiplicative factors
    sigma_confinement: float = 0.10,
    sigma_lambda_q: float = 0.25,
    sigma_hts_jc: float = 0.10,
    # additive uncertainties
    sigma_zeff: float = 0.15,
    seed: Optional[int] = None,
) -> Dict[str, object]:
    """
    Simple Monte Carlo uncertainty engine.

    Returns:
      - p_feasible: fraction of samples that satisfy all constraints
      - worst_constraints: list of most frequently violated constraints
      - samples: list of dict summaries (lightweight)
    """
    if seed is not None:
        random.seed(seed)

    violated_counts: Dict[str, int] = {}
    samples: List[Dict[str, float]] = []
    ok_count = 0

    for _ in range(max(1, int(n))):
        inp = replace(
            base,
            confinement_mult=_rand_lognormal(max(getattr(base, "confinement_mult", 1.0), 1e-6), sigma_confinement),
            lambda_q_mult=_rand_lognormal(max(getattr(base, "lambda_q_mult", 1.0), 1e-6), sigma_lambda_q),
            hts_Jc_mult=_rand_lognormal(max(getattr(base, "hts_Jc_mult", 1.0), 1e-6), sigma_hts_jc),
            zeff=max(1.0, random.gauss(base.zeff, sigma_zeff)),
        )
        out = hot_ion_point(inp)
        cs = build_constraints_from_outputs(out)
        ok = all(c.ok for c in cs)
        if ok:
            ok_count += 1
        else:
            for c in cs:
                if not c.ok:
                    violated_counts[c.name] = violated_counts.get(c.name, 0) + 1

        samples.append({
            "Q": float(out.get("Q_DT_eqv", float("nan"))),
            "H98": float(out.get("H98", float("nan"))),
            "Pnet_MW": float(out.get("P_e_net_MW", float("nan"))),
            "Bpeak_T": float(out.get("B_peak_T", float("nan"))),
            "ok": 1.0 if ok else 0.0,
        })

    worst = sorted(violated_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    return {
        "p_feasible": ok_count / max(1, int(n)),
        "worst_constraints": [{"name": k, "count": v} for k, v in worst],
        "samples": samples,
    }
