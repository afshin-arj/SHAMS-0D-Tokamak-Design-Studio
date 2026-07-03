from __future__ import annotations

from constraints.pipeline_diff import build_pipeline_diff_dossier


def test_pipeline_diff_dossier_structure() -> None:
    out = {
        "transport_spread_ratio_v396": 1.2,
        "transport_spread_max_v396": 1.5,
    }
    dossier = build_pipeline_diff_dossier(out)
    assert "registry_governance" in dossier
    assert "legacy_governance" in dossier
    assert "parity" in dossier
    assert len(dossier["registry_governance"]) >= 1
