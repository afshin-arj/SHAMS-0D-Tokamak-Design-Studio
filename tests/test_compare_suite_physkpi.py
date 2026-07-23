"""Compare + Suite PHYS-KPI-001 export watermark contracts."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_watermark_scenario_delta_export_masks_q_on_infeasible():
    from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_scenario_delta_export

    sd = {
        "changed_kpis": {
            "Q": {"base": 10.0, "scenario": 12.0},
            "R0_m": {"base": 5.0, "scenario": 5.5},
        },
        "baseline_outputs": {"Q": 10.0, "R0_m": 5.0},
        "scenario_outputs": {"Q": 12.0, "R0_m": 5.5},
    }
    out = watermark_scenario_delta_export(sd, feasible_base=False, feasible_scenario=True)
    assert "diagnostic" in str(out["changed_kpis"]["Q"]["base"]).lower()
    assert "diagnostic" not in str(out["changed_kpis"]["Q"]["scenario"]).lower()
    assert out["changed_kpis"]["R0_m"]["base"] == 5.0
    assert "diagnostic" in str(out["baseline_outputs"]["Q"]).lower()
    assert "diagnostic" not in str(out["scenario_outputs"]["Q"]).lower()
    assert "PHYS-KPI-001" in str(out.get("phys_kpi_note") or "")


def test_comparison_json_bundle_watermarks_scenario_delta(monkeypatch):
    from ui_nicegui.lib import compare_helpers as ch

    art_a = {"outputs": {"Q": 8.0}, "constraints": []}
    art_b = {
        "outputs": {"Q": 3.0},
        "constraints": [],
        "scenario_delta": {
            "changed_kpis": {"Q": {"base": 8.0, "scenario": 3.0}},
            "baseline_outputs": {"Q": 8.0},
        },
    }

    def _fake_summary(a, b):
        return {
            "feasible_a": False,
            "feasible_b": True,
            "verdict_a": "INFEASIBLE",
            "verdict_b": "FEASIBLE",
        }

    monkeypatch.setattr(ch, "summarize_comparison", _fake_summary)
    monkeypatch.setattr(ch, "metric_diff_rows", lambda *a, **k: [])
    monkeypatch.setattr(ch, "kpi_diff_rows", lambda *a, **k: [])
    monkeypatch.setattr(ch, "numeric_output_diff_rows", lambda *a, **k: [])
    monkeypatch.setattr(ch, "constraint_margin_diff_rows", lambda *a, **k: [])
    monkeypatch.setattr(ch, "subsystem_diff_rows", lambda *a, **k: [])
    monkeypatch.setattr(ch, "input_diff_rows", lambda *a, **k: [])
    monkeypatch.setattr(ch, "structural_diff_report", lambda *a, **k: None)

    bundle = ch.comparison_json_bundle(art_a, art_b)
    sd = bundle["scenario_delta"]
    assert isinstance(sd, dict)
    assert "diagnostic" in str(sd["changed_kpis"]["Q"]["base"]).lower()
    assert "diagnostic" not in str(sd["changed_kpis"]["Q"]["scenario"]).lower()
    assert "diagnostic" in str(sd["baseline_outputs"]["Q"]).lower()
    assert "PHYS-KPI-001" in str(sd.get("phys_kpi_note") or "")


def test_watermark_campaign_jsonl_bytes_masks_claim_foms():
    from ui_nicegui.lib.suite_extended_helpers import watermark_campaign_jsonl_bytes

    lines = [
        json.dumps({"cid": "a", "feasible_hard": False, "Q": 12.0, "R0_m": 6.0}),
        json.dumps({"cid": "b", "feasible_hard": True, "Q": 2.0, "R0_m": 5.0}),
        "not-json-keep-me",
        json.dumps({"cid": "c", "feasible": False, "H98": 1.4}),
    ]
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    out = watermark_campaign_jsonl_bytes(raw)
    parsed = []
    for line in out.decode("utf-8").splitlines():
        if line == "not-json-keep-me":
            parsed.append(line)
            continue
        parsed.append(json.loads(line))
    assert "diagnostic" in str(parsed[0]["Q"]).lower()
    assert parsed[0]["R0_m"] == 6.0
    assert "diagnostic" not in str(parsed[1]["Q"]).lower()
    assert parsed[2] == "not-json-keep-me"
    assert "diagnostic" in str(parsed[3]["H98"]).lower()
    # Session raw path must remain unwatermarked when helper not applied
    assert b"12.0" in raw


def test_suite_compare_download_source_contracts():
    suite_src = Path("ui_nicegui/lib/suite_helpers.py").read_text(encoding="utf-8")
    tabs_src = Path("ui_nicegui/decks/system_suite/tabs.py").read_text(encoding="utf-8")
    cmp_src = Path("ui_nicegui/lib/compare_helpers.py").read_text(encoding="utf-8")
    inp_src = Path("ui_nicegui/decks/compare/inputs_structure.py").read_text(encoding="utf-8")
    adv_src = Path("ui_nicegui/decks/trade_study_studio/advanced.py").read_text(encoding="utf-8")
    assert "watermark_campaign_jsonl_bytes" in suite_src
    assert "watermark_campaign_jsonl_bytes" in tabs_src
    assert "watermark_scenario_delta_export" in cmp_src
    assert "watermark_scenario_delta_export" in inp_src
    assert "_physkpi_atlas_download_payload" in adv_src
    assert "watermark_trade_study_export" in adv_src or "watermark_regime_atlas_export" in adv_src


def test_pick_output_resolves_pe_net_and_h98_aliases():
    from ui_nicegui.lib.compare_helpers import _pick_output

    assert _pick_output({"Pe_net_MW": 42.0}, "P_e_net_MW") == 42.0
    assert _pick_output({"P_net_MW": 11.0}, "P_e_net_MW") == 11.0
    assert _pick_output({"H_IPB98y2": 1.15}, "H98") == 1.15
    assert _pick_output({"H98y2": 1.05}, "H98") == 1.05
    assert _pick_output({"tau_E_s": 2.5}, "tauE_eff_s") == 2.5
    assert _pick_output({"tauE_s": 1.8}, "tauE_eff_s") == 1.8


def test_suite_busy_guard_wires_refresh_tab_if_idle():
    from ui_nicegui.lib.deck_busy_guard import SUITE_RUNNING_ATTRS

    assert "suite_running" in SUITE_RUNNING_ATTRS
    src = Path("ui_nicegui/decks/system_suite/__init__.py").read_text(encoding="utf-8")
    assert "SUITE_RUNNING_ATTRS" in src
    assert "refresh_tab_if_idle" in src
