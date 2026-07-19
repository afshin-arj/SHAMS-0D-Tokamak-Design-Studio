"""Scan Lab NiceGUI workflow — labels, restore, archive helpers."""
from __future__ import annotations

import json

import pytest

from ui_nicegui.decks.scan_lab import export_archive, insights, orientation
from ui_nicegui.decks.scan_lab import render_scan_lab
from ui_nicegui.lib.scan_archive_helpers import (
    boundaries_json_bytes,
    freeze_statement_text,
    restore_scan_artifact,
    run_replay_determinism_audit,
)
from ui_nicegui.lib.scan_helpers import build_scan_artifact_if_available, default_scan_bounds, run_cartography_scan
from ui_nicegui.lib.scan_labels import (
    DECISION_TO_TAB,
    SCAN_TABS,
    normalize_scan_tab,
    teaching_banner,
)
from ui_nicegui.session import DesignSession


def test_scan_workflow_renderer_import() -> None:
    assert callable(render_scan_lab)
    assert callable(orientation.render_orientation_panel)
    assert callable(insights.render_interpret_tab)
    assert callable(export_archive.render_export_tab)


def test_scan_labels_normalize_legacy() -> None:
    assert normalize_scan_tab("Cartography") == "1 · Setup & Run"
    assert normalize_scan_tab("2 · Map & Probe") == "2 · Map & Probe"
    assert normalize_scan_tab("unknown") == "1 · Setup & Run"


def test_decision_routes_to_tabs() -> None:
    for state, tab in DECISION_TO_TAB.items():
        assert tab in SCAN_TABS


def test_teaching_banner_guided_default() -> None:
    s = DesignSession()
    assert s.scan_teaching_mode is True
    assert teaching_banner(s) is not None
    s.scan_teaching_mode = False
    assert teaching_banner(s) is None


def test_estimate_eval_count() -> None:
    from ui_nicegui.lib.scan_helpers import estimate_eval_count

    assert estimate_eval_count(31, 25) == 775


def test_format_causality_trace() -> None:
    from ui_nicegui.lib.scan_insight_display import format_causality_trace

    txt = format_causality_trace({"constraint": "q95", "margin_baseline": -0.1})
    assert "q95" in txt


def test_cartography_uses_evaluated_constraints() -> None:
    from ui_nicegui.lib.helm_helpers import apply_legacy_reference_machine_to_session

    s = DesignSession()
    apply_legacy_reference_machine_to_session(s, "SPARC-class (compact HTS)")
    base = s.build_point_inputs()
    x_lo, x_hi, y_lo, y_hi = default_scan_bounds(base, "Ip_MA", "R0_m")
    rep = run_cartography_scan(
        base,
        x_key="Ip_MA",
        y_key="R0_m",
        x_lo=x_lo,
        x_hi=x_hi,
        y_lo=y_lo,
        y_hi=y_hi,
        nx=11,
        ny=11,
        intents=["Reactor"],
    )
    from ui_nicegui.lib.scan_helpers import summarize_scan_report

    sm = summarize_scan_report(rep, intent="Reactor")
    assert sm["feasible_rate"] < 1.0
    assert str(sm["dominant"]) not in ("PASS", "(none)")


def test_restore_scan_artifact_roundtrip() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    x_lo, x_hi, y_lo, y_hi = default_scan_bounds(base, "Ip_MA", "R0_m")
    rep = run_cartography_scan(
        base,
        x_key="Ip_MA",
        y_key="R0_m",
        x_lo=x_lo,
        x_hi=x_hi,
        y_lo=y_lo,
        y_hi=y_hi,
        nx=11,
        ny=11,
        intents=["Reactor"],
    )
    settings = {
        "x_key": "Ip_MA",
        "y_key": "R0_m",
        "x_lo": x_lo,
        "x_hi": x_hi,
        "y_lo": y_lo,
        "y_hi": y_hi,
        "nx": 11,
        "ny": 11,
        "intents": ["Reactor"],
        "include_outputs": False,
    }
    art = build_scan_artifact_if_available(rep, settings)
    assert isinstance(art, dict)
    updates = restore_scan_artifact(art)
    assert isinstance(updates.get("scan_cartography_report"), dict)
    assert updates.get("scan_cart_x_key") == "Ip_MA"


def test_freeze_statement_nonempty() -> None:
    text = freeze_statement_text()
    assert isinstance(text, str)
    assert len(text) > 20


def test_replay_audit_smoke() -> None:
    s = DesignSession()
    try:
        result = run_replay_determinism_audit(
            s.build_point_inputs(),
            x_key="Ip_MA",
            y_key="R0_m",
            intents=["Reactor"],
        )
    except RuntimeError as exc:
        pytest.skip(str(exc))
    assert isinstance(result, dict)
    assert "pass" in result


def test_boundaries_bytes_optional() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    x_lo, x_hi, y_lo, y_hi = default_scan_bounds(base, "Ip_MA", "R0_m")
    rep = run_cartography_scan(
        base,
        x_key="Ip_MA",
        y_key="R0_m",
        x_lo=x_lo,
        x_hi=x_hi,
        y_lo=y_lo,
        y_hi=y_hi,
        nx=11,
        ny=11,
        intents=["Reactor"],
    )
    bnd = boundaries_json_bytes(rep)
    assert bnd is None or isinstance(bnd, bytes)


def test_legacy_nested_scan_helpers() -> None:
    from tools.legacy_nested_scan import estimate_legacy_grid_count, frange

    assert frange(0.0, 1.0, 0.5) == [0.0, 0.5, 1.0]
    assert frange(1.0, 0.0, -0.5) == [1.0, 0.5, 0.0]
    n = estimate_legacy_grid_count(
        {
            "gconf_start": 0.8,
            "gconf_stop": 1.0,
            "gconf_step": 0.2,
            "Ti_start": 10.0,
            "Ti_stop": 11.0,
            "Ti_step": 1.0,
            "H98_start": 1.0,
            "H98_stop": 1.0,
            "H98_step": 0.1,
            "a_min": 2.0,
            "a_max": 2.0,
            "a_step": 0.1,
            "Q_start": 10.0,
            "Q_stop": 10.0,
            "Q_step": 5.0,
        }
    )
    assert n == 4  # g: 2 × Ti: 2 × singleton axes


def test_format_projection_stability() -> None:
    from ui_nicegui.lib.scan_insight_display import format_projection_stability

    txt = format_projection_stability(
        {
            "ok": True,
            "z_key": "Paux_MW",
            "z0": 50.0,
            "mode_dominant": "q95",
            "dominant_stability": 0.75,
            "dominant": ["q95", "q95", "betaN"],
            "note": "Slice caveat applies.",
        }
    )
    assert "Paux_MW" in txt
    assert "75%" in txt


def test_scan_governance_labels_and_imports() -> None:
    from ui_nicegui.decks.scan_lab.governance_ui import render_governance_panel
    from ui_nicegui.decks.scan_lab.legacy_nested_ui import render_legacy_nested_panel
    from ui_nicegui.decks.scan_lab.slice_diagnostics_ui import render_slice_diagnostics
    from ui_nicegui.lib.scan_labels import NO_OPTIMIZATION_NOTICE, SLICE_MITIGATION, helm_suggested_scan_lens

    assert "does **not** optimize" in NO_OPTIMIZATION_NOTICE
    assert "off-plane" in SLICE_MITIGATION.lower()
    assert helm_suggested_scan_lens("Experimental Device (research)") == "Research"
    assert helm_suggested_scan_lens("Power Reactor (net-electric)") == "Reactor"
    assert callable(render_governance_panel)
    assert callable(render_legacy_nested_panel)
    assert callable(render_slice_diagnostics)


def test_v396_transport_strip_helpers() -> None:
    from ui_nicegui.lib.scan_v396_display import extract_v396_transport, format_v396_caption

    assert extract_v396_transport(None) is None
    assert extract_v396_transport({}) is None
    info = extract_v396_transport(
        {"transport_spread_ratio_v396": 1.47, "transport_credibility_tier_v396": "tight"}
    )
    assert info is not None
    assert abs(float(info["spread"]) - 1.47) < 1e-9
    assert info["tier"] == "tight"
    cap = format_v396_caption(info)
    assert "1.47" in cap
    assert "tight" in cap


def test_probe_cell_summary_includes_v396_when_present() -> None:
    from ui_nicegui.lib.scan_workbench_helpers import probe_cell_summary

    grid = {
        (0, 0): {
            "x": 1.0,
            "y": 2.0,
            "intent": {"Reactor": {"blocking_feasible": True}},
            "outputs": {
                "Q_DT_eqv": 10.0,
                "transport_spread_ratio_v396": 1.5,
                "transport_credibility_tier_v396": "comfortable",
            },
        }
    }
    summary = probe_cell_summary(grid, {}, "Reactor", 0, 0)
    assert summary.get("v396") is not None
    assert summary["v396"]["tier"] == "comfortable"
