"""Pulse scenario templates (quasi-static).

SHAMS law:
- No time-domain solvers.
- No iteration.
- Scenario is an explicit contract that may override a few pulsed-operation
  timing proxies used for PF average power bookkeeping and cycle fatigue counters.

If pulse_scenario == 'as_input', do nothing.
"""

from __future__ import annotations

from typing import Dict


SCENARIOS: Dict[str, Dict[str, float]] = {
    "steady": {"t_burn_s": 24 * 3600.0, "t_dwell_s": 0.0, "pulse_ramp_s": 0.0},
    "standard_pulse": {"t_burn_s": 7200.0, "t_dwell_s": 600.0, "pulse_ramp_s": 300.0},
    "long_pulse": {"t_burn_s": 8 * 3600.0, "t_dwell_s": 900.0, "pulse_ramp_s": 600.0},
    "aggressive_pulse": {"t_burn_s": 3600.0, "t_dwell_s": 600.0, "pulse_ramp_s": 180.0},
}


def apply_pulse_scenario(inputs_dict: Dict[str, float]) -> Dict[str, float]:
    """Return a copy of inputs with scenario overrides applied."""
    name = str(inputs_dict.get("pulse_scenario", "as_input")).strip().lower()
    if name in ("", "none", "as_input", "as-input", "asis"):
        out = dict(inputs_dict)
        out["pulse_scenario_used"] = "as_input"
        return out

    if name not in SCENARIOS:
        out = dict(inputs_dict)
        out["pulse_scenario_used"] = "as_input"
        out["pulse_scenario_unknown"] = name
        return out

    sc = SCENARIOS[name]
    out = dict(inputs_dict)
    out["pulse_scenario_used"] = name
    out["t_burn_s"] = float(sc.get("t_burn_s", out.get("t_burn_s", 7200.0)))
    out["t_dwell_s"] = float(sc.get("t_dwell_s", out.get("t_dwell_s", 600.0)))
    out["pulse_ramp_s"] = float(sc.get("pulse_ramp_s", out.get("pulse_ramp_s", 300.0)))
    return out
