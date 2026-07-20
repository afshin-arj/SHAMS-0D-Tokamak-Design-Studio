"""Phase 22: Point Designer final parity — governance, envelope, intake, telemetry tables."""
from __future__ import annotations

from ui_nicegui.decks.point_designer.configure_governance import render_design_governance
from ui_nicegui.decks.point_designer.configure_nuclear_intake import render_nuclear_dataset_intake
from ui_nicegui.lib.pd_parity_helpers import point_summary_rows, raw_telemetry_rows
from ui_nicegui.lib.pd_panel_labels import TELEMETRY_VIEWS, normalize_telemetry_view
from ui_nicegui.lib.pd_solver_helpers import compute_pd_inputs_fingerprint
from ui_nicegui.session import DesignSession


def test_phase22_telemetry_view_labels() -> None:
    assert len(TELEMETRY_VIEWS) == 7
    assert normalize_telemetry_view("Mission Snapshot") == "Verdict & KPIs"


def test_phase22_governance_defaults() -> None:
    s = DesignSession()
    assert s.inputs.get("q95_enforcement") == "hard"
    assert s.inputs.get("tech_tier") == "TRL7"


def test_phase22_envelope_targets() -> None:
    s = DesignSession()
    assert s.pd_pfus_target == 0.0
    assert s.pd_pnet_target == -1.0


def test_phase22_point_summary_and_raw() -> None:
    out = {"Ip_MA": 8.0, "H98": 1.1, "Q_DT_eqv": 5.0, "extra_key": 1.23}
    ps = point_summary_rows(out)
    assert any(r["quantity"].startswith("Ip") for r in ps)
    rt = raw_telemetry_rows(out)
    assert any(r["key"] == "H98" for r in rt)


def test_phase22_fingerprint_includes_mode() -> None:
    s = DesignSession()
    fp = compute_pd_inputs_fingerprint(s)
    assert "pd_eval_mode" in fp


def test_phase22_configure_modules_import() -> None:
    from ui_nicegui.decks.point_designer.configure_advanced_materials import render_advanced_materials
    from ui_nicegui.decks.point_designer.configure_systems_bridge import render_systems_precheck_bridge

    assert callable(render_design_governance)
    assert callable(render_nuclear_dataset_intake)
    assert callable(render_advanced_materials)
    assert callable(render_systems_precheck_bridge)


def test_phase22_run_lock() -> None:
    from ui_nicegui.lib.run_lock import acquire, release, status

    assert acquire("test", "A")
    locked, task, owner = status("B")
    assert locked and task == "test" and not owner
    assert acquire("test2", "A") is False  # non-reentrant same owner
    release("A")
    assert not status("A")[0]


def test_phase22_navigation_register() -> None:
    from ui_nicegui.lib import navigation

    seen = []

    navigation.register_deck_change(lambda n: seen.append(n))
    navigation.switch_deck("Systems Mode")
    assert seen == ["Systems Mode"]
