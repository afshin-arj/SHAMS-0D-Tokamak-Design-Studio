"""Forge Audit Pack export — bundled narrative, reviewer packet, capsule."""
from __future__ import annotations

import json
import zipfile
from io import BytesIO

from ui_nicegui.lib.forge_machine_finder_helpers import build_forge_audit_pack_zip


def _minimal_run() -> dict:
    return {
        "intent": "Reactor",
        "seed": 1,
        "archive": [
            {
                "intent": "Reactor",
                "feasible": True,
                "failure_mode": "",
                "inputs": {"R0_m": 6.2, "a_m": 2.0, "B_T": 5.3, "Ip_MA": 12.0},
                "outputs": {"Q_DT_eqv": 5.0, "P_fus_MW": 500.0},
                "constraints": [],
            }
        ],
        "trace": [],
    }


def test_build_forge_audit_pack_zip_structure() -> None:
    run = _minimal_run()
    lens = {"intent": "Reactor", "objectives": []}
    bounds = {"R0_m": [5.0, 7.0]}
    data, name = build_forge_audit_pack_zip(
        run,
        row_idx=0,
        lens_contract=lens,
        bounds=bounds,
        intent="Reactor",
    )
    assert isinstance(data, (bytes, bytearray)) and len(data) > 500
    assert name.startswith("shams_forge_audit_pack_")
    assert name.endswith(".zip")

    with zipfile.ZipFile(BytesIO(data), "r") as zf:
        names = set(zf.namelist())
        assert "manifest.json" in names
        assert "README.txt" in names
        assert "narrative/report_pack.md" in names
        if "narrative/design_card.md" in names:
            assert len(zf.read("narrative/design_card.md")) > 0
        assert "reviewer_packet/shams_reviewer_packet.zip" in names
        assert "reviewer_packet/summary.json" in names
        assert any(n.startswith("run_capsule/") and n.endswith(".zip") for n in names)

        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest.get("schema") == "shams.forge.audit_pack.v1"
        assert manifest.get("row_idx") == 0
        assert manifest.get("n_archive") == 1

        reviewer_inner = zf.read("reviewer_packet/shams_reviewer_packet.zip")
        assert len(reviewer_inner) > 200
        with zipfile.ZipFile(BytesIO(reviewer_inner), "r") as inner:
            assert "candidate.json" in set(inner.namelist())
