
from __future__ import annotations
from dataclasses import replace
from typing import List
try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore

def default_envelope_points(base: PointInputs) -> List[PointInputs]:
    """Generate a small operating envelope: startup, nominal, EoL blanket/derated.

    Transparent heuristic; users can override by providing their own list externally.
    """
    pts=[]
    # Startup: lower Ip and auxiliary heating
    pts.append(replace(base, Ip_MA=0.7*base.Ip_MA, Paux_MW=0.8*base.Paux_MW, Ti_keV=0.8*base.Ti_keV))
    # Nominal
    pts.append(base)
    # EoL / derated: slightly reduced Bt, thicker blanket (if field exists)
    t_blank = getattr(base, "t_blanket_m", 0.80)
    pts.append(replace(base, Bt_T=0.95*base.Bt_T, Paux_MW=1.1*base.Paux_MW, Ti_keV=0.95*base.Ti_keV, t_blanket_m=min(1.2, t_blank+0.05)))
    return pts
