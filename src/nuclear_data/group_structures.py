from __future__ import annotations

"""Nuclear data group structures (v407).

Hard rule: deterministic, no solvers, no hidden iteration.

This module defines a small set of multi-group energy boundaries used for
screening proxies in the Nuclear Data Authority Deepening upgrade (v407).

Notes
-----
- Group edges are expressed in MeV.
- This is *not* a transport solver; it is an envelope/sensitivity proxy.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class GroupStructure:
    group_structure_id: str
    edges_MeV: List[float]  # length = n_groups + 1

    @property
    def n_groups(self) -> int:
        return max(len(self.edges_MeV) - 1, 0)


# v407 default: 6 groups (14 MeV -> thermal)
# Edges chosen to separate DT primary (~14 MeV), fast downscatter, epithermal,
# and thermal regimes.
G6_V407 = GroupStructure(
    group_structure_id="G6_V407",
    edges_MeV=[14.0, 6.0, 2.0, 0.5, 0.1, 1e-3, 0.0],
)


GROUP_STRUCTURES: Dict[str, GroupStructure] = {
    G6_V407.group_structure_id: G6_V407,
}


def get_group_structure(group_structure_id: str) -> GroupStructure:
    if group_structure_id in GROUP_STRUCTURES:
        return GROUP_STRUCTURES[group_structure_id]
    raise KeyError(f"Unknown group_structure_id: {group_structure_id}")
