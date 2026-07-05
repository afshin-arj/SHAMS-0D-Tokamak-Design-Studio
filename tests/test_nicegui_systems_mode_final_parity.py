"""Systems Mode final parity helpers — certs, cockpit, reproduce, atlas."""

from __future__ import annotations

from ui_nicegui.lib.systems_cert_registry import CERT_REGISTRY
from ui_nicegui.lib.systems_cockpit import build_compact_cockpit_markdown
from ui_nicegui.lib.systems_plant_authority import build_exhaust_authority_bundle, exhaust_unit_suspect
from ui_nicegui.lib.systems_reproduce import json_structural_diff, systems_run_records
from ui_nicegui.lib.systems_workflow_helpers import append_run_card, systems_run_payload
from ui_nicegui.session import DesignSession


def test_cert_registry_expert_titles() -> None:
    assert len(CERT_REGISTRY) >= 15
    for title, _key, *_rest in CERT_REGISTRY:
        assert "(v" not in title.lower()
        assert "v3" not in title  # no version codes in UI titles


def test_exhaust_authority_bundle() -> None:
    out = {"q_div_MW_m2": 10.0, "lambda_q_mm": 1.0, "n_strike_points": 2}
    bundle = build_exhaust_authority_bundle(out)
    assert bundle["q_div_MW_m2"] == 10.0
    assert not exhaust_unit_suspect({"q_div_unit_suspect": 0.0})


def test_json_diff_detects_change() -> None:
    diffs = json_structural_diff({"a": 1}, {"a": 2})
    assert any("a" in d for d in diffs)


def test_cockpit_markdown_without_artifact() -> None:
    s = DesignSession()
    md = build_compact_cockpit_markdown(s, None)
    assert "No solve artifact" in md


def test_run_card_payload_roundtrip() -> None:
    s = DesignSession()
    s.systems_last_solve_artifact = {"ok": True, "outputs": {"Q_DT_eqv": 5.0}}
    s.systems_targets_overrides = {"Q_DT_eqv": 10.0}
    payload = systems_run_payload(s)
    rid = append_run_card(
        s,
        kind="TestRun",
        settings={},
        outcome={"ok": True},
        payload=payload,
    )
    runs = systems_run_records(s)
    assert runs[0]["id"] == rid
    assert runs[0]["payload"].get("ui_state", {}).get("systems_targets_overrides") == {"Q_DT_eqv": 10.0}
