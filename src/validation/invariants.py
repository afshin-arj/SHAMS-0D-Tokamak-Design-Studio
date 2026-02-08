from __future__ import annotations

from typing import Any, Dict
import math


def _f(out: Dict[str, Any], key: str) -> float:
    try:
        return float(out.get(key, float('nan')))
    except Exception:
        return float('nan')


def check_invariants(out: Dict[str, Any]) -> Dict[str, Any]:
    """Check conservative invariants for audit/CI.

    This is not a physics validation against experiments; it is a bookkeeping
    and sign-consistency screen.
    """

    failures: Dict[str, str] = {}
    values: Dict[str, float] = {}

    def record(name: str, v: float) -> float:
        values[name] = float(v)
        return v

    # Non-negativity screens
    for k in [
        'Pfus_total_MW', 'Palpha_MW', 'Paux_MW', 'Ploss_MW', 'Prad_core_MW',
        'P_e_gross_MW', 'P_e_net_MW', 'P_recirc_MW',
    ]:
        v = record(k, _f(out, k))
        if math.isfinite(v) and v < -1e-9:
            failures[k] = f'negative ({v:.4g})'

    # Net must not exceed gross when both available
    Pnet = record('P_e_net_MW', _f(out, 'P_e_net_MW'))
    Pgross = record('P_e_gross_MW', _f(out, 'P_e_gross_MW'))
    if math.isfinite(Pnet) and math.isfinite(Pgross):
        if Pnet - Pgross > 1e-6:
            failures['net_leq_gross'] = f'P_net > P_gross ({Pnet:.3g} > {Pgross:.3g})'

    # Availability bounded
    A = record('availability_model', _f(out, 'availability_model'))
    if math.isfinite(A) and (A < -1e-6 or A > 1.000001):
        failures['availability_bounds'] = f'availability_model out of [0,1] ({A:.4g})'

    # Confinement time positive if present
    tau = record('tauE_s', _f(out, 'tauE_s'))
    if math.isfinite(tau) and tau <= 0:
        failures['tauE_positive'] = f'tauE_s <= 0 ({tau:.4g})'

    # Basic geometric sanity if present
    R0 = record('R0_m', _f(out, 'R0_m'))
    a = record('a_m', _f(out, 'a_m'))
    if math.isfinite(R0) and math.isfinite(a) and a > 0:
        if R0 / a < 1.1:
            failures['aspect_ratio'] = f'R0/a too small ({R0/a:.3g})'

    return {
        'ok': (len(failures) == 0),
        'failures': failures,
        'values': values,
        'schema_version': 'invariants.v1',
    }
