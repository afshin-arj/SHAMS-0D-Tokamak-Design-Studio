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


def test_teaching_banner_off_by_default() -> None:
    s = DesignSession()
    assert teaching_banner(s) is None
    s.scan_teaching_mode = True
    assert teaching_banner(s) is not None


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
