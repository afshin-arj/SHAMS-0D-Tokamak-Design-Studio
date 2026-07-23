"""Pareto ExtOpt PHYS-KPI-001 download watermark contracts."""
from __future__ import annotations

import io
import json
import os
import sys
import zipfile
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_watermark_concept_cockpit_export_masks_q_on_infeasible():
    from ui_nicegui.lib.external_optimizer_helpers import watermark_concept_cockpit_export

    rep = {
        "n_total": 2,
        "n_feasible": 1,
        "results": [
            {"cid": "a", "feasible_hard": False, "Q_DT_eqv": 9.0, "R0_m": 6.0},
            {"cid": "b", "feasible_hard": True, "Q_DT_eqv": 2.0, "R0_m": 5.0},
            {
                "cid": "c",
                "verdict": "INFEASIBLE",
                "outputs": {"Q": 11.0, "H98": 1.2},
            },
        ],
    }
    out = watermark_concept_cockpit_export(rep)
    assert "diagnostic" in str(out["results"][0]["Q_DT_eqv"]).lower()
    assert out["results"][0]["R0_m"] == 6.0
    assert "diagnostic" not in str(out["results"][1]["Q_DT_eqv"]).lower()
    assert "diagnostic" in str(out["results"][2]["outputs"]["Q"]).lower()
    assert "PHYS-KPI-001" in str(out.get("phys_kpi_note") or "")


def test_watermark_extopt_zip_bytes_redacts_fail_artifact():
    from ui_nicegui.lib.external_optimizer_helpers import watermark_extopt_zip_bytes

    art = {
        "verdict": "INFEASIBLE",
        "outputs": {
            "Q_DT_eqv": 12.0,
            "H98": 1.5,
            "hard_feasible": False,
            "constraints_failed": ["x"],
        },
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("artifacts/c1.json", json.dumps(art))
        zf.writestr("readme.txt", "keep me")
    wm = watermark_extopt_zip_bytes(buf.getvalue())
    with zipfile.ZipFile(io.BytesIO(wm), "r") as zf:
        assert zf.read("readme.txt") == b"keep me"
        loaded = json.loads(zf.read("artifacts/c1.json").decode("utf-8"))
    assert "diagnostic" in str(loaded["outputs"]["Q_DT_eqv"]).lower()
    assert "diagnostic" in str(loaded["outputs"]["H98"]).lower()


def test_atlas_evidence_zip_uses_regime_watermark():
    from ui_nicegui.lib.external_optimizer_helpers import atlas_evidence_zip

    atlas = {
        "schema": "regime_atlas.v1",
        "pareto_sets": [
            {
                "robustness_class": "INFEASIBLE",
                "metrics": {"P_e_net_MW": 100.0, "R0_m": 6.0},
            }
        ],
    }
    data = atlas_evidence_zip(atlas)
    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        names = [n for n in zf.namelist() if n.endswith("atlas.json")]
        assert names
        payload = json.loads(zf.read(names[0]).decode("utf-8"))
    assert "diagnostic" in str(payload["pareto_sets"][0]["metrics"]["P_e_net_MW"]).lower()
    assert payload["pareto_sets"][0]["metrics"]["R0_m"] == 6.0
    assert "PHYS-KPI-001" in str(payload.get("phys_kpi_note") or "")


def test_external_py_wires_extopt_download_watermarks():
    src = Path("ui_nicegui/decks/pareto_lab/external.py").read_text(encoding="utf-8")
    assert "watermark_extopt_zip_bytes" in src
    assert "watermark_concept_cockpit_export" in src
    assert "PHYS-KPI-001" in src
