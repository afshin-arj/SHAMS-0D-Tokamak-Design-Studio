from __future__ import annotations


def test_v374_certification_smoke() -> None:
    from certification.stability_control_certification_v374 import certify_stability_control_margins

    inputs = {"R0_m": 3.0, "a_m": 1.0, "kappa": 1.7, "Bt_T": 5.0, "Ip_MA": 10.0}
    outputs = {
        "q95": 4.0,
        "beta_N": 2.0,
        "vs_margin": 0.2,
        "rwm_proximity_index": 0.3,
    }
    cert = certify_stability_control_margins(inputs=inputs, outputs=outputs)
    assert isinstance(cert, dict)
    assert cert.get("cert_version") == "v374.0"
    assert "vertical_stability" in cert
