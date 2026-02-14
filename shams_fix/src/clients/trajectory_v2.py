from __future__ import annotations

"""Deterministic trajectory diagnostic client (external to frozen truth).

This module is a *firewalled client* in SHAMS terms. It may integrate simple
low-order ODEs to produce timelines for expert diagnostics. Its outputs:
- MUST NOT be used to recover feasibility or modify frozen evaluator results
- SHOULD be stamped into artifacts and treated as diagnostic-only

v2 uses a fixed-step integrator for determinism.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
import math
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class TrajectoryConfig:
    dt_s: float = 0.5
    t_end_s: float = 200.0


def _finite(x: float) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def integrate_energy_balance_v2(out: Dict[str, float], cfg: TrajectoryConfig) -> Dict[str, object]:
    """Toy energy-balance trajectory.

    State: W (MJ). dW/dt = P_heat - P_loss, with constant coefficients derived
    from a point evaluation.

    This is intentionally simplistic: it provides a deterministic *timeline* for
    when margins would be violated if powers were held constant.
    """
    P_heat = float(out.get('P_heat_MW', out.get('P_in_MW', float('nan'))))
    P_loss = float(out.get('P_loss_MW', out.get('Ploss_MW', float('nan'))))
    W0 = float(out.get('W_MJ', out.get('W_plasma_MJ', float('nan'))))
    if not all(_finite(x) for x in [P_heat, P_loss, W0]) or cfg.dt_s <= 0 or cfg.t_end_s <= 0:
        return {
            'schema': 'trajectory_diagnostic.v2',
            'ok': False,
            'reason': 'missing_inputs',
            'config': cfg.__dict__,
            't_s': [],
            'W_MJ': [],
        }

    dt = float(cfg.dt_s)
    n = int(max(1, math.ceil(cfg.t_end_s / dt)))
    t: List[float] = []
    W: List[float] = []
    w = W0
    for k in range(n + 1):
        tk = k * dt
        t.append(tk)
        W.append(w)
        # Euler step
        dw_dt = (P_heat - P_loss)  # MW = MJ/s
        w = max(0.0, w + dw_dt * dt)

    return {
        'schema': 'trajectory_diagnostic.v2',
        'ok': True,
        'model': 'energy_balance_euler_fixed',
        'config': cfg.__dict__,
        'inputs': {'P_heat_MW': P_heat, 'P_loss_MW': P_loss, 'W0_MJ': W0},
        't_s': t,
        'W_MJ': W,
    }
