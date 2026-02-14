
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

@dataclass
class AvailabilityResult:
    availability: float
    planned_outage_fraction: float
    forced_outage_fraction: float
    notes: str

def availability_proxy(out: Dict[str, float], inp: object) -> AvailabilityResult:
    """Simple availability model proxy.

    planned: blanket replacement cycle interval (years) and duration (months)
    forced: penalty based on component complexity and power density
    """
    interval_y = float(getattr(inp, "blanket_replace_interval_y", 4.0))
    duration_mo = float(getattr(inp, "blanket_replace_duration_mo", 4.0))
    planned = min(0.5, (duration_mo/12.0) / max(0.5, interval_y))

    # forced outage proxy increases with fusion power density and tech aggressiveness
    Pfus = float(out.get("Pfus_MW", 0.0))
    R0 = float(out.get("R0_m", getattr(inp, "R0_m", 6.2)))
    vol = max(1e-6, (2*3.14159*R0) * (3.14159*(float(out.get("a_m", getattr(inp,"a_m",2.0)))**2)) )
    pden = Pfus / vol  # MW/m^3 proxy
    base_forced = float(getattr(inp, "forced_outage_base", 0.10))
    forced = min(0.6, base_forced + 0.03*(pden/0.5))

    avail = max(0.0, 1.0 - planned - forced)
    return AvailabilityResult(availability=avail, planned_outage_fraction=planned, forced_outage_fraction=forced, notes="proxy")
