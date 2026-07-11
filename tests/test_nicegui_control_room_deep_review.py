"""Control Room deep review — governance header, artifacts, non-feasibility."""
from __future__ import annotations

from ui_nicegui.decks.control_room import render_control_room
from ui_nicegui.lib.control_room_helpers import LAUNCHPAD_DECK, governance_summary
from ui_nicegui.lib.control_room_labels import TEACHING_HINTS, DECISION_STATES
from ui_nicegui.lib.cr_governance_helpers import nonfeasibility_certificate_view
from ui_nicegui.lib.cr_provenance_helpers import list_session_run_artifacts
from ui_nicegui.session import DesignSession


def test_control_room_renderer_and_ported() -> None:
    from ui_nicegui.decks.control_room import _PORTED

    assert callable(render_control_room)
    assert "Orientation" in _PORTED
    assert len(_PORTED) == 6


def test_launchpad_deck_map() -> None:
    assert LAUNCHPAD_DECK["Compare designs (Artifacts)"] == "Compare"
    assert "Scan Lab" in LAUNCHPAD_DECK.values()


def test_teaching_hint_no_false_links() -> None:
    hint = TEACHING_HINTS[DECISION_STATES[0]]
    assert "Open deck" in hint
    assert "links to a primary" not in hint


def test_governance_summary_verdict_fields() -> None:
    s = DesignSession()
    s.pd_last_outputs = {
        "Q_DT_eqv": 1.0,
        "ne20": 1.0,
        "Ti_keV": 10.0,
        "constraints": [{"name": "q95", "passed": True, "severity": "hard", "value": 3, "limit": 2, "sense": ">="}],
    }
    summary = governance_summary(s)
    assert "dominant" in summary
    assert "q_label" in summary
    assert summary["point_verdict"] in ("FEASIBLE", "INFEASIBLE")


def test_list_session_run_artifacts_extended() -> None:
    s = DesignSession()
    s.pd_last_artifact = {"kind": "shams_run_artifact", "outputs": {"Q": 1}, "run_id": "pd1"}
    s.cmp_slot_a = {"kind": "shams_run_artifact", "outputs": {"Q": 2}, "run_id": "cmp_a"}
    arts = list_session_run_artifacts(s)
    ids = {a["id"] for a in arts}
    assert "pd1" in ids
    assert "cmp_a" in ids


def test_nonfeasibility_certificate_from_constraints() -> None:
    art = {
        "constraints": [
            {
                "name": "q95",
                "severity": "hard",
                "passed": False,
                "margin": -0.2,
                "value": 2.5,
                "limit": 3.0,
                "sense": ">=",
                "best_knobs": ["Ip_MA"],
            }
        ]
    }
    cert = nonfeasibility_certificate_view(art)
    assert cert.get("hard_feasible") is False
    blockers = cert.get("dominant_blockers") or []
    assert blockers and blockers[0]["name"] == "q95"


def test_interop_check_cmp_slot_honest() -> None:
    from ui_nicegui.lib.control_room_helpers import interop_check

    s = DesignSession()
    rep = interop_check(s)
    cmp_check = next(c for c in rep["checks"] if c["name"] == "cmp_slot_a")
    assert cmp_check["ok"] is False


def test_chronicle_and_diag_p2_tabs() -> None:
    from ui_nicegui.lib.control_room_helpers import CHRONICLE_TABS, DIAG_TABS

    assert "Knob Trade-Space" in CHRONICLE_TABS
    assert "Certified Search" in CHRONICLE_TABS
    assert "Validation Envelopes" in DIAG_TABS
    assert len(CHRONICLE_TABS) >= 8


def test_constraint_provenance_rows() -> None:
    from ui_nicegui.lib.cr_chronicle_helpers import constraint_provenance_rows

    art = {
        "constraints": [
            {
                "name": "q95",
                "group": "stability",
                "failed": True,
                "fingerprint": "abc123",
                "maturity": "proxy",
            }
        ]
    }
    rows = constraint_provenance_rows(art)
    assert rows[0]["name"] == "q95"
    assert rows[0]["fingerprint"] == "abc123"


def test_validation_envelope_report_smoke() -> None:
    from ui_nicegui.lib.cr_chronicle_helpers import validation_envelope_report
    from validation.envelopes import default_envelopes

    env_name = next(iter(default_envelopes().keys()))
    rep = validation_envelope_report(env_name, {"Q_DT_eqv": 1.0, "beta_N": 2.0})
    assert "rows" in rep
    assert isinstance(rep["rows"], list)


def test_flatten_certified_search_table_rows() -> None:
    from ui_nicegui.lib.cr_chronicle_helpers import flatten_certified_search_table_rows

    art = {
        "schema_version": "certified_search_orchestrator_evidence.v3",
        "stages": [
            {
                "name": "stage1",
                "records": [{"i": 0, "verdict": "PASS", "score": 1.0, "x": {"Ip_MA": 5.0}, "evidence": {}}],
            }
        ],
    }
    rows = flatten_certified_search_table_rows(art)
    assert len(rows) == 1
    assert rows[0]["verdict"] == "PASS"
    assert rows[0]["Ip_MA"] == 5.0
