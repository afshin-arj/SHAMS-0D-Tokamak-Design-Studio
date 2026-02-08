from __future__ import annotations
"""Optimizer Sandbox Plus (v103.1)

Safe orchestration wrapper that *cannot corrupt SHAMS*:
- Calls existing random-search optimizer in `phase1_core.optimize_design`
- Passes user lever bounds via `variables` dict (same structure)
- Returns JSON-serializable run object with best candidate + outputs

Additive only.
"""

from dataclasses import asdict
from typing import Any, Dict, Tuple
import time

def run_sandbox(
    base,
    *,
    levers: Dict[str, Tuple[float, float]],
    objective: str = "min_R0",
    max_evals: int = 200,
    seed: int = 0,
    strategy: str = "random",
) -> Dict[str, Any]:
    created_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    strat = (strategy or "random").lower().strip()
    if strat not in ("random", "lhs"):
        strat = "random"

    from phase1_core import optimize_design  # type: ignore

    variables = {k: (float(lo), float(hi)) for k, (lo, hi) in levers.items()}

    best_inp, best_out = optimize_design(
        base,
        objective=objective,
        variables=variables,
        n_iter=int(max_evals),
        seed=int(seed),
    )

    def _to_dict(x):
        if hasattr(x, "to_dict"):
            try:
                return x.to_dict()
            except Exception:
                pass
        try:
            return asdict(x)
        except Exception:
            return dict(x)

    return {
        "kind": "shams_optimizer_sandbox_run",
        "created_utc": created_utc,
        "strategy": strat,
        "objective": objective,
        "seed": int(seed),
        "max_evals": int(max_evals),
        "variables": {k: [float(a), float(b)] for k, (a, b) in variables.items()},
        "base": _to_dict(base),
        "best_inputs": _to_dict(best_inp),
        "best_outputs": dict(best_out or {}),
    }
