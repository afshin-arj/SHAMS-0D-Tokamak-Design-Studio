"""Phase 15: System Suite Campaign/Parity + Control Room Provenance."""
from __future__ import annotations

import json

import pytest

from ui_nicegui.decks.control_room import provenance
from ui_nicegui.decks.system_suite import tabs
from ui_nicegui.lib.cr_provenance_helpers import (
    list_session_run_artifacts,
    regression_artifact_diff,
    save_point_study,
)
from ui_nicegui.lib.suite_extended_helpers import (
    default_campaign_template,
    list_parity_cases,
    parse_campaign_spec,
)
from ui_nicegui.session import DesignSession


def test_phase15_renderers_import() -> None:
    assert callable(tabs.render_campaign_pack)
    assert callable(tabs.render_benchmark_parity)
    assert callable(provenance.render_provenance)


def test_default_campaign_template() -> None:
    spec = default_campaign_template({"R0_m": 6.0, "B0_T": 5.3, "P_aux_MW": 50.0})
    assert spec["schema"] == "shams_campaign.v1"
    assert len(spec["variables"]) >= 1


def test_parse_campaign_spec_smoke() -> None:
    spec = default_campaign_template({"R0_m": 6.0})
    text = json.dumps(spec)
    parsed = parse_campaign_spec(text)
    assert parsed.name == "campaign_v363"


def test_list_parity_cases_smoke() -> None:
    cases = list_parity_cases("v364")
    if not cases:
        pytest.skip("No v364 benchmark cases in repo")
    assert isinstance(cases[0][0], str)
    assert cases[0][1].exists()


def test_list_session_run_artifacts_empty() -> None:
    s = DesignSession()
    assert list_session_run_artifacts(s) == []


def test_list_session_run_artifacts_point() -> None:
    s = DesignSession()
    s.pd_last_artifact = {"kind": "shams_run_artifact", "run_id": "r1", "outputs": {"Q": 1.0}}
    arts = list_session_run_artifacts(s)
    assert len(arts) == 1
    assert arts[0]["id"] == "r1"


def test_regression_artifact_diff() -> None:
    a = {"outputs": {"Q": 1.0}, "constraints": [{"name": "beta", "failed": False, "margin": 0.1}]}
    b = {"outputs": {"Q": 1.1}, "constraints": [{"name": "beta", "failed": True, "margin": -0.01}]}
    d = regression_artifact_diff(a, b)
    # Alias Q → Q_DT_eqv; claim cells watermarked when sides are not hard-feasible.
    assert any(r["kpi"] == "Q_DT_eqv" for r in d["kpi_rows"])
    assert len(d["new_failures"]) == 1


def test_save_point_study() -> None:
    s = DesignSession()
    entry = save_point_study(s, notes="test")
    assert entry["type"] == "point"
    assert len(s.cr_studies) == 1
