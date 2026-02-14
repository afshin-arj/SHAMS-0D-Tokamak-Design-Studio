from __future__ import annotations


def test_transport_contracts_v371_smoke() -> None:
    """v371: transport contract library should be deterministic and import-safe."""

    from models.inputs import PointInputs
    from physics.hot_ion import hot_ion_point
    from constraints.constraints import evaluate_constraints

    inp = PointInputs(
        R0_m=6.2,
        a_m=2.0,
        kappa=1.8,
        Bt_T=6.0,
        Ip_MA=10.0,
        Ti_keV=12.0,
        fG=0.8,
        Paux_MW=50.0,
        include_transport_contracts_v371=True,
        H_required_max_optimistic=2.0,
        H_required_max_robust=1.5,
    )

    out1 = hot_ion_point(inp)
    out2 = hot_ion_point(inp)
    assert out1.get("transport_contracts_v371_enabled") is True
    assert out1.get("transport_contracts_v371_contract") is not None
    # Deterministic key subset
    for k in ("tauE_envelope_min_s", "tauE_envelope_max_s", "transport_confinement_regime_v371"):
        assert k in out1
        assert out1[k] == out2[k]
    # Envelope sanity
    assert float(out1["tauE_envelope_min_s"]) <= float(out1["tauE_envelope_max_s"])

    # Constraint exposure: if caps are set, the constraint list should include them.
    cs = evaluate_constraints(out1)
    names = {str(getattr(c, "name", "")) for c in (cs or [])}
    assert "H_required_opt" in names or "H_required_rob" in names
