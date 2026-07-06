"""Target sense policy for Systems Mode — precheck (min) vs Newton residuals."""

from __future__ import annotations

from typing import Dict

# Performance targets are usually floors (≥), not equalities.
_DEFAULT_SENSES: Dict[str, str] = {
    "Q_DT_eqv": "min",
    "H98": "min",
    "P_e_net_MW": "min",
    "Pfus_DT_adj_MW": "min",
}


def default_target_sense(key: str) -> str:
    return _DEFAULT_SENSES.get(str(key), "eq")


def build_target_senses(targets: Dict[str, float]) -> Dict[str, str]:
    return {k: default_target_sense(k) for k in targets}
