from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import math

@dataclass(frozen=True)
class AvailabilityResult:
    availability: float
    fw_replace_interval_y: float
    div_replace_interval_y: float
    blanket_replace_interval_y: float
    downtime_scheduled_frac: float
    downtime_trips_frac: float

def compute_availability(out: Dict[str, Any], inp: Any) -> AvailabilityResult:
    """Compute a simple availability model based on replacement intervals and unscheduled trips.

    - Replacement intervals derived from dpa/year proxy (first wall/blanket) and divertor erosion rate proxy.
    - Downtime = scheduled maintenance time / year + unscheduled trips time / year.

    This is a transparent proxy for systems studies; it is not a plant availability simulator.
    """
    def f(key: str, default: float = float('nan')) -> float:
        try:
            return float(out.get(key, default))
        except Exception:
            return default

    dpa_y = f("fw_dpa_per_year", float('nan'))
    erosion_mm_y = f("div_erosion_mm_per_year", float('nan'))

    # Intervals (years). If proxy missing, assume long interval (less limiting).
    fw_interval = 2.0 if not (dpa_y == dpa_y) or dpa_y <= 0 else max(0.1, 20.0 / dpa_y)
    blanket_interval = 3.0 if not (dpa_y == dpa_y) or dpa_y <= 0 else max(0.1, 40.0 / dpa_y)
    div_interval = 1.5 if not (erosion_mm_y == erosion_mm_y) or erosion_mm_y <= 0 else max(0.1, 10.0 / erosion_mm_y)

    # Scheduled maintenance time per year (days)
    fw_days = float(getattr(inp, "fw_replace_time_days", 30.0))
    div_days = float(getattr(inp, "div_replace_time_days", 30.0))
    blanket_days = float(getattr(inp, "blanket_replace_time_days", 90.0))

    scheduled_days = fw_days/fw_interval + div_days/div_interval + blanket_days/blanket_interval

    # Unscheduled trips
    trips_per_year = float(getattr(inp, "trips_per_year", 5.0))
    trip_duration_days = float(getattr(inp, "trip_duration_days", 2.0))
    trips_days = trips_per_year * trip_duration_days

    downtime_sched = max(0.0, min(1.0, scheduled_days/365.0))
    downtime_trips = max(0.0, min(1.0, trips_days/365.0))
    availability = max(0.0, 1.0 - downtime_sched - downtime_trips)

    return AvailabilityResult(
        availability=float(availability),
        fw_replace_interval_y=float(fw_interval),
        div_replace_interval_y=float(div_interval),
        blanket_replace_interval_y=float(blanket_interval),
        downtime_scheduled_frac=float(downtime_sched),
        downtime_trips_frac=float(downtime_trips),
    )
