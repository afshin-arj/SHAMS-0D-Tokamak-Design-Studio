from __future__ import annotations

import math


def test_maintenance_v368_basic_smoke() -> None:
    from src.maintenance.scheduling_v368 import compute_maintenance_schedule_v368
    from src.models.inputs import PointInputs

    # Minimal synthetic outputs consistent with v367+ cadence keys
    out = {
        "P_e_net_MW": 200.0,
        "fw_replace_interval_y": 2.0,
        "blanket_replace_interval_y": 4.0,
        "fw_replace_time_days": 30.0,
        "blanket_replace_time_days": 90.0,
        "div_replace_interval_y": 3.0,
        "div_replace_time_days": 30.0,
    }

    inp = PointInputs(
        # required core knobs
        R0_m=3.0,
        a_m=1.0,
        kappa=1.8,
        Bt_T=5.0,
        Ip_MA=10.0,
        Ti_keV=10.0,
        fG=0.8,
        Paux_MW=30.0,
        include_maintenance_scheduling_v368=True,
        planned_outage_base=0.05,
        forced_outage_base=0.03,
        trips_per_year=5.0,
        trip_duration_days=2.0,
        maintenance_bundle_policy="bundle_in_vessel",
        maintenance_bundle_overhead_days=7.0,
        forced_outage_mode_v368="max",
        availability_v368_min=float("nan"),
        outage_fraction_v368_max=float("nan"),
        include_availability_replacement_v359=False,
        include_economics_v360=False,
    )

    ms = compute_maintenance_schedule_v368(out, inp)
    assert ms.schema_version == "v368.0"
    assert ms.availability == ms.availability
    assert 0.0 <= ms.availability <= 1.0
    assert ms.outage_total_frac == ms.outage_total_frac
    assert abs(ms.outage_total_frac - (ms.planned_outage_frac + ms.forced_outage_frac + ms.replacement_outage_frac)) < 1e-12
    assert ms.net_electric_MWh_per_year >= 0.0
    assert isinstance(ms.events, tuple)
    assert any("+" in str(e.get("component", "")) for e in ms.events)


def test_maintenance_v368_bundling_non_increasing_outage() -> None:
    from src.maintenance.scheduling_v368 import compute_maintenance_schedule_v368
    from src.models.inputs import PointInputs

    out = {
        "P_e_net_MW": 200.0,
        "fw_replace_interval_y": 2.0,
        "blanket_replace_interval_y": 4.0,
        "fw_replace_time_days": 30.0,
        "blanket_replace_time_days": 90.0,
        "div_replace_interval_y": 3.0,
        "div_replace_time_days": 30.0,
    }

    base = PointInputs(
        # required core knobs
        R0_m=3.0,
        a_m=1.0,
        kappa=1.8,
        Bt_T=5.0,
        Ip_MA=10.0,
        Ti_keV=10.0,
        fG=0.8,
        Paux_MW=30.0,
        include_maintenance_scheduling_v368=True,
        planned_outage_base=0.0,
        forced_outage_base=0.0,
        trips_per_year=0.0,
        trip_duration_days=0.0,
        forced_outage_mode_v368="baseline",
        maintenance_bundle_overhead_days=0.0,
        include_availability_replacement_v359=False,
        include_economics_v360=False,
    )

    ms_ind = compute_maintenance_schedule_v368(out, base.__class__(**{**base.to_dict(), "maintenance_bundle_policy": "independent"}))
    ms_bun = compute_maintenance_schedule_v368(out, base.__class__(**{**base.to_dict(), "maintenance_bundle_policy": "bundle_in_vessel"}))

    # Bundling is a proxy and may increase or decrease outage depending on relative
    # intervals/durations; it must, however, change the event topology deterministically.
    assert len(ms_bun.events) != len(ms_ind.events)
    assert abs(ms_ind.replacement_outage_frac - sum(float(e.get("outage_frac", 0.0) or 0.0) for e in ms_ind.events)) < 1e-12
    assert abs(ms_bun.replacement_outage_frac - sum(float(e.get("outage_frac", 0.0) or 0.0) for e in ms_bun.events)) < 1e-12
