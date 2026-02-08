from __future__ import annotations
"""Slow-time evolution proxies for pulsed operation.

PROCESS largely assumes steady-state or quasi-steady. SHAMS can go further by
tracking duty factor and cycle counts for pulsed concepts, without adding heavy
time-dependent plasma physics.
"""

from typing import Dict

def duty_factor(t_burn_s: float, t_dwell_s: float) -> float:
    t_burn_s = max(0.0, float(t_burn_s))
    t_dwell_s = max(0.0, float(t_dwell_s))
    if t_burn_s + t_dwell_s <= 0:
        return 0.0
    return t_burn_s / (t_burn_s + t_dwell_s)

def cycles_per_year(t_burn_s: float, t_dwell_s: float) -> float:
    seconds_per_year = 365.25 * 24 * 3600
    t_cycle = max(1e-9, float(t_burn_s) + float(t_dwell_s))
    return seconds_per_year / t_cycle

def pulsed_summary(t_burn_s: float, t_dwell_s: float) -> Dict[str, float]:
    return {
        "t_burn_s": float(t_burn_s),
        "t_dwell_s": float(t_dwell_s),
        "duty_factor": float(duty_factor(t_burn_s, t_dwell_s)),
        "cycles_per_year": float(cycles_per_year(t_burn_s, t_dwell_s)),
    }
