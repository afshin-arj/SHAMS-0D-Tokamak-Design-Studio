from __future__ import annotations


def test_stability_risk_tiering_smoke() -> None:
    from diagnostics.stability_risk import evaluate_stability_risk

    # Nominally benign
    out = {
        "mhd_risk_proxy": 0.4,
        "vs_margin": 0.9,
        "rwm_control_ok": True,
        "rwm_chi": 0.4,
        "control_contract_margins": {"VS_total": 0.25, "PF_power": 0.1},
    }
    sr = evaluate_stability_risk(out)
    assert sr.tier in {"LOW", "MED", "HIGH"}
    assert sr.tier == "LOW"

    # Force RWM failure
    out2 = dict(out)
    out2["rwm_control_ok"] = False
    sr2 = evaluate_stability_risk(out2)
    assert sr2.tier in {"MED", "HIGH"}
    assert sr2.components.get("rwm", 0.0) >= 1.25

    # Poor vertical stability and tight control margins
    out3 = {
        "mhd_risk_proxy": 1.1,
        "vs_margin": 0.2,
        "rwm_control_ok": True,
        "control_contract_margins": {"VS_total": -0.05},
    }
    sr3 = evaluate_stability_risk(out3)
    assert sr3.tier in {"MED", "HIGH"}
    assert sr3.components.get("vertical_stability", 0.0) >= 1.0
