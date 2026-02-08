from __future__ import annotations

from models.inputs import PointInputs
from shams_io.run_artifact import build_run_artifact


def test_decision_consequences_embedded_minimal():
    inp = PointInputs.from_dict(
        {
            "R0_m": 1.8,
            "a_m": 0.55,
            "kappa": 1.7,
            "Bt_T": 10.0,
            "Ip_MA": 8.0,
            "Ti_keV": 10.0,
            "fG": 0.8,
            "Paux_MW": 20.0,
        }
    )

    art = build_run_artifact(
        inputs=inp.to_dict(),
        outputs={"q95": 3.2, "fG": 0.8},
        constraints=[],
        meta={"label": "t", "mode": "point"},
    )

    dc = art.get("decision_consequences")
    assert isinstance(dc, dict)
    assert dc.get("schema_version") == "decision_consequences.v1"
    assert dc.get("decision_posture") in ("PROCEED", "PROCEED_TARGETED_RD", "HOLD_FOUNDATIONAL", "UNKNOWN")
    assert isinstance(dc.get("leverage_knobs"), list)
    assert isinstance(dc.get("narrative"), str)
