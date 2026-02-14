from __future__ import annotations
from typing import Dict, Tuple, Optional, Any

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore
from solvers.optimize import robust_feasibility_monte_carlo

def robustness_summary(
    base: PointInputs,
    perturb: Dict[str, Tuple[float, float]],
    n: int = 200,
    seed: Optional[int] = None,
    *,
    metrics: Optional[Tuple[str, ...]] = ("P_net_MWe", "COE_proxy_USD_per_MWh", "LCOE_proxy_USD_per_MWh"),
    thresholds: Optional[Dict[str, Tuple[str, float]]] = None,
) -> Dict[str, Any]:
    """Robustness summary suitable for embedding into artifacts.

    Adds:
    - metric_stats for chosen metrics
    - threshold probabilities (if provided)
    """
    return robust_feasibility_monte_carlo(
        base=base,
        perturb=perturb,
        n=n,
        seed=seed,
        metrics=metrics,
        thresholds=thresholds,
    )
