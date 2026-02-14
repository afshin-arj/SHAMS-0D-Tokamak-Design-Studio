from __future__ import annotations

"""Transport Contract Library Authority (v371.0).

This is a *governance* contract: it does not compute physics and must not
modify frozen-truth outputs. It standardizes:

- which confinement scalings participate in an envelope by regime (L/H)
- how optimistic vs robust caps on required confinement are represented

Design rules
------------
- Deterministic data only (pure python literals).
- No hidden iteration, no solvers.
- Defaults are conservative and OFF unless explicitly enabled in inputs.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass(frozen=True)
class TransportContractV371:
    schema_version: str
    tier: str
    validity_domain: str
    scalings_H: List[str]
    scalings_L: List[str]
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["scalings_H"] = [str(x) for x in (d.get("scalings_H") or [])]
        d["scalings_L"] = [str(x) for x in (d.get("scalings_L") or [])]
        return d


DEFAULT_TRANSPORT_CONTRACT_V371 = TransportContractV371(
    schema_version="transport_contracts.v371",
    tier="semi-authoritative",
    validity_domain=(
        "0-D global confinement scalings envelope, regime-conditioned by a deterministic Martin-2008 P_LH proxy. "
        "H-mode envelope uses IPB98(y,2) as the primary reference; L-mode envelope uses ITER89-P / Kaye-Goldston / "
        "Neo-Alcator comparators. This is a screening/gating aid, not a transport solve."
    ),
    scalings_H=["IPB98Y2"],
    scalings_L=["ITER89P", "KG", "NEOALC"],
    notes=(
        "This contract defines which confinement scalings are considered in the envelope per regime. "
        "It does not provide numerical uncertainty bands; those are represented explicitly by user caps on H_required."
    ),
)


def load_transport_contract_v371(profile: str | None = None) -> Dict[str, Any]:
    """Return a frozen transport contract dict.

    Parameters
    ----------
    profile:
        Reserved for future deterministic variants (e.g. reactor vs research).
        Currently ignored; the default contract is always returned.
    """
    _ = profile
    return DEFAULT_TRANSPORT_CONTRACT_V371.to_dict()
