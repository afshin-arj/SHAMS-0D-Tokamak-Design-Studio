from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict

@dataclass(frozen=True)
class FidelityConfig:
    plasma: str = "0D"        # 0D / 1/2D
    magnets: str = "limits"   # limits / stress
    exhaust: str = "proxy"    # proxy / enriched
    neutronics: str = "proxy" # proxy / enriched
    profiles: str = "off"     # off / analytic
    economics: str = "proxy"  # proxy / enriched

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

DEFAULT = FidelityConfig()

def normalize_fidelity(d: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(d, dict):
        return DEFAULT.to_dict()
    base = DEFAULT.to_dict()
    for k,v in d.items():
        if k in base and isinstance(v, str):
            base[k]=v
    return base
