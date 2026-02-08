from __future__ import annotations

def test_epoch_feasibility_schema_smoke():
    from src.shams_io.run_artifact import build_run_artifact
    from src.constraints.constraints import Constraint

    # minimal artifact with a couple constraints
    inputs = {"design_intent": "Reactor"}
    outputs = {"q95": 3.0, "q95_min": 3.0, "fG": 0.9, "P_e_net_MW": 200.0, "P_net_min_MW": 0.0}
    constraints = [
        Constraint(name="q95", value=2.5, limit=3.0, sense=">=", passed=False, severity="hard", mechanism_group="PLASMA"),
        Constraint(name="P_net", value=50.0, limit=100.0, sense=">=", passed=False, severity="hard", mechanism_group="ECONOMICS"),
    ]
    art = build_run_artifact(inputs, outputs, constraints, meta={"shams_version": "v258.0", "label": "test", "mode": "unit"})
    ef = art.get("epoch_feasibility")
    assert isinstance(ef, dict)
    assert str(ef.get("schema_version","")).startswith("epoch_feasibility.v1")
    epochs = ef.get("epochs")
    assert isinstance(epochs, list)
    assert len(epochs) >= 1
