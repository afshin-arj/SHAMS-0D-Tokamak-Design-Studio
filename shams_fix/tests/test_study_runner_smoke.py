from __future__ import annotations

from studies.spec import StudySpec
from studies.runner import run_study

def test_run_study_smoke(tmp_path):
    spec = StudySpec(
        name="smoke",
        targets={"H98": 1.0, "Q_DT_eqv": 5.0},
        variables={"Ip_MA":[8.0, 4.0, 12.0], "fG":[0.8, 0.1, 1.2]},
        sweeps=[],
    )
    idx = run_study(spec, tmp_path)
    assert idx["n_cases"] >= 1
    assert (tmp_path/"index.json").exists()
