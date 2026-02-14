from __future__ import annotations

from shams_io.run_artifact import build_run_artifact, write_run_artifact, read_run_artifact
from shams_io.schema import CURRENT_SCHEMA_VERSION
from models.inputs import PointInputs
from models.reference_machines import REFERENCE_MACHINES

def test_run_artifact_roundtrip(tmp_path):
    inp = PointInputs.from_dict(next(iter(REFERENCE_MACHINES.values())))
    art = build_run_artifact(inputs=inp.to_dict(), outputs={"x":1.0}, constraints=[], meta={"label":"t","mode":"point"})
    assert art.get("schema_version") == CURRENT_SCHEMA_VERSION
    p = tmp_path/"a.json"
    write_run_artifact(p, art)
    art2 = read_run_artifact(p)
    assert art2["schema_version"] == CURRENT_SCHEMA_VERSION
    assert art2["outputs"]["x"] == 1.0
