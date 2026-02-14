import math

from tools.system_suite import ops_availability_overlay, thermal_network_diagnostics_client


def test_ops_availability_overlay_deterministic():
    point_out = {"P_e_net_MW": 500.0, "t_flat_s": 3600.0, "t_dwell_s": 600.0}
    point_inp = {"pulse_ramp_s": 300.0, "design_intent": "reactor"}

    r1 = ops_availability_overlay(point_out, point_inp, availability=0.80)
    r2 = ops_availability_overlay(point_out, point_inp, availability=0.80)

    assert math.isfinite(r1.duty_cycle)
    assert r1.stamp_sha256 == r2.stamp_sha256
    assert abs(r1.avg_delivered_MW - r2.avg_delivered_MW) < 1e-12


def test_thermal_network_diagnostics_client_runs():
    point_out = {
        "P_fus_MW": 1500.0,
        "P_e_gross_MW": 600.0,
        "t_flat_s": 1800.0,
        "t_dwell_s": 300.0,
    }
    point_inp = {"pulse_ramp_s": 200.0}

    tr = thermal_network_diagnostics_client(point_out, point_inp, n_points=121)

    assert len(tr.t_s) == 121
    assert "fw" in tr.nodes_K
    assert "divertor" in tr.nodes_K
    assert all(math.isfinite(x) for x in tr.nodes_K["fw"])
