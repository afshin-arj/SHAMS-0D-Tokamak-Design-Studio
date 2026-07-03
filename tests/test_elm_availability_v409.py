from __future__ import annotations

from analysis.elm_transient_heat_v409 import evaluate_elm_transient_heat_v409


class _Inp:
    include_elm_transient_heat_v409 = True
    elm_energy_fraction_v409 = 0.05
    elm_duration_ms_v409 = 0.5
    elm_duty_cycle_v409 = 0.04
    elm_recovery_downtime_frac_v409 = 0.5
    elm_transient_q_parallel_max_MW_m2_v409 = 500.0


def test_elm_duty_cycle_availability_proxy() -> None:
    out = {"q_parallel_MW_per_m2": 100.0, "W_th_MJ": 200.0, "tauE_s": 1.0}
    patch = evaluate_elm_transient_heat_v409(out, _Inp())
    assert patch["elm_duty_cycle_v409"] == 0.04
    assert patch["elm_availability_downtime_frac_v409"] == 0.02
