"""Phase 19: Point Designer full Streamlit parity batch."""
from __future__ import annotations

from ui_nicegui.decks.point_designer import telemetry
from ui_nicegui.lib.pd_panel_labels import TELEMETRY_VIEWS
from ui_nicegui.lib.pd_intent_policy import classify_failed_constraints, design_intent_key
from ui_nicegui.lib.pd_overlay_catalog import ALL_OVERLAY_KEYS, OVERLAY_GROUPS
from ui_nicegui.lib.pd_parity_helpers import headline_kpi_pairs, pipeline_diff_rows, template_names
from ui_nicegui.lib.pd_plot_helpers import plot_power_stack
from ui_nicegui.lib.session_store import clear_point_designer
from ui_nicegui.session import DesignSession


def test_phase19_telemetry_views_match_streamlit() -> None:
    assert len(TELEMETRY_VIEWS) == 7
    assert "Verdict & KPIs" in TELEMETRY_VIEWS
    assert "Power balance plots" in TELEMETRY_VIEWS
    assert "Run history & export" in TELEMETRY_VIEWS


def test_phase19_overlay_catalog() -> None:
    assert len(OVERLAY_GROUPS) >= 5
    assert "include_control_contracts" in ALL_OVERLAY_KEYS


def test_phase19_intent_policy() -> None:
    assert design_intent_key("Experimental Device (research)") == "research"
    cls = classify_failed_constraints(["TBR", "q95"], design_intent="Experimental Device (research)")
    assert "q95" in cls["blocking"]
    assert "TBR" in cls["ignored"]


def test_phase19_clear_point_designer() -> None:
    s = DesignSession()
    s.pd_last_outputs = {"Q": 1.0}
    clear_point_designer(s)
    assert s.pd_last_outputs is None


def test_phase19_headline_kpis_smoke() -> None:
    pairs = headline_kpi_pairs({"Q_DT_eqv": 5.0, "H98": 1.0, "Pfus_DT_adj_MW": 100.0})
    assert isinstance(pairs, list)
    assert len(pairs) >= 3


def test_phase19_plot_helper_smoke() -> None:
    png = plot_power_stack({"Pfus_MW": 100.0, "Paux_MW": 50.0})
    assert png is None or isinstance(png, bytes)


def test_phase19_template_names_smoke() -> None:
    names = template_names()
    assert isinstance(names, list)


def test_phase19_pipeline_diff_import() -> None:
    s = DesignSession()
    inp = s.build_point_inputs()
    from ui_nicegui.evaluate import ui_evaluate

    out = ui_evaluate(inp, origin="test")
    data = pipeline_diff_rows(out, design_intent=s.design_intent)
    assert "aligned" in data


def test_phase19_renderers_import() -> None:
    from ui_nicegui.decks.point_designer import configure, constraints, mission_snapshot, plot_deck

    assert callable(telemetry.render_telemetry)
    assert callable(configure.render_configure)
    assert callable(constraints.render_constraints)
    assert callable(mission_snapshot.render_mission_snapshot)
    assert callable(plot_deck.render_plot_deck)
