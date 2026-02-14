from __future__ import annotations

"""Multi-node lumped thermal network (diagnostic-only).

This is an external diagnostic client (no effect on feasibility).
It integrates a linear thermal RC network with fixed-step Euler for
strict determinism.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
import math
from typing import Dict, List, Sequence


@dataclass(frozen=True)
class ThermalNode:
    name: str
    C_kJ_per_K: float


@dataclass(frozen=True)
class ThermalEdge:
    i: int
    j: int
    G_kW_per_K: float


@dataclass(frozen=True)
class ThermalConfig:
    dt_s: float = 1.0
    t_end_s: float = 600.0


def simulate_thermal_network_v2(
    nodes: Sequence[ThermalNode],
    edges: Sequence[ThermalEdge],
    Q_kW: Sequence[float],
    T0_K: Sequence[float],
    cfg: ThermalConfig,
) -> Dict[str, object]:
    """Simulate dT/dt = (Q - sum G(Ti-Tj))/C.

    - nodes: thermal capacities
    - edges: conductances
    - Q_kW: heat inputs per node (kW)
    - Euler fixed step for determinism
    """
    n = len(nodes)
    if n == 0 or len(Q_kW) != n or len(T0_K) != n or cfg.dt_s <= 0 or cfg.t_end_s <= 0:
        return {'schema': 'thermal_network.v2', 'ok': False, 'reason': 'bad_inputs'}

    dt = float(cfg.dt_s)
    steps = int(max(1, math.ceil(cfg.t_end_s / dt)))

    C = [max(1e-6, float(nd.C_kJ_per_K) * 1e3) for nd in nodes]  # J/K
    Q = [float(q) * 1e3 for q in Q_kW]  # W
    T = [float(t) for t in T0_K]

    names = [nd.name for nd in nodes]
    ts: List[float] = []
    T_hist: List[List[float]] = []

    for k in range(steps + 1):
        ts.append(k * dt)
        T_hist.append(list(T))

        # Compute net heat flow per node from edges
        net = [Q[i] for i in range(n)]
        for e in edges:
            if e.i < 0 or e.i >= n or e.j < 0 or e.j >= n:
                continue
            G = float(e.G_kW_per_K) * 1e3  # W/K
            dT = T[e.i] - T[e.j]
            # heat from i to j: G*dT
            net[e.i] -= G * dT
            net[e.j] += G * dT

        # Euler update
        for i in range(n):
            T[i] = T[i] + (net[i] / C[i]) * dt

    return {
        'schema': 'thermal_network.v2',
        'ok': True,
        'config': cfg.__dict__,
        'nodes': [{'name': n.name, 'C_kJ_per_K': n.C_kJ_per_K} for n in nodes],
        'edges': [{'i': e.i, 'j': e.j, 'G_kW_per_K': e.G_kW_per_K} for e in edges],
        'inputs': {'Q_kW': list(Q_kW), 'T0_K': list(T0_K)},
        't_s': ts,
        'T_K': T_hist,
        'names': names,
    }
