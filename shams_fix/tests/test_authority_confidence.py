from __future__ import annotations

from shams_io.run_artifact import build_run_artifact
from models.inputs import PointInputs


def test_authority_confidence_embedded_minimal():
    inp = PointInputs.from_dict({
        "R0_m": 1.8,
        "a_m": 0.55,
        "kappa": 1.7,
        "Bt_T": 10.0,
        "Ip_MA": 8.0,
        "Ti_keV": 10.0,
        "fG": 0.8,
        "Paux_MW": 20.0,
    })

    art = build_run_artifact(
        inputs=inp.to_dict(),
        outputs={"q95": 3.2, "fG": 0.8},
        constraints=[],
        meta={"label": "t", "mode": "point"},
    )

    assert isinstance(art.get("authority_contracts"), dict)
    assert isinstance(art.get("authority_confidence"), dict)
    ac = art["authority_confidence"]
    assert ac.get("schema_version") == "authority_confidence.v1"
    assert "design" in ac and "subsystems" in ac
