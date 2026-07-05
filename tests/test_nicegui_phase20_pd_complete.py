"""Phase 20: Point Designer complete parity (solver, deepening, PDF, frontier)."""
from __future__ import annotations

from ui_nicegui.decks.point_designer.pd_physics_deepening import DEEP_VIEWS
from ui_nicegui.lib.pd_overlay_knobs import OVERLAY_NUMERIC_PANELS
from ui_nicegui.lib.pd_solver_helpers import (
    compute_pd_inputs_fingerprint,
    compute_pd_inputs_hash,
    run_point_designer_evaluation,
    sync_solver_bounds_from_inputs,
)
from ui_nicegui.session import DesignSession


def test_phase20_deep_views_count() -> None:
    assert len(DEEP_VIEWS) == 11


def test_phase20_overlay_numeric_panels() -> None:
    assert len(OVERLAY_NUMERIC_PANELS) >= 5
    flags = [p[0] for p in OVERLAY_NUMERIC_PANELS]
    assert "include_transport_envelope_v396" in flags
    assert "include_magnet_technology_authority_v400" in flags


def test_phase20_session_solver_fields() -> None:
    s = DesignSession()
    assert s.pd_eval_mode == "direct"
    assert s.pd_q_target == 2.0
    assert isinstance(s.pd_solver_trace, list)


def test_phase20_sync_solver_bounds() -> None:
    s = DesignSession()
    s.inputs["Ip_MA"] = 10.0
    s.inputs["fG"] = 0.9
    sync_solver_bounds_from_inputs(s)
    assert s.pd_ip_min > 0
    assert s.pd_ip_max > s.pd_ip_min
    assert 0 <= s.pd_fg_min < s.pd_fg_max


def test_phase20_inputs_hash_stable() -> None:
    s = DesignSession()
    sync_solver_bounds_from_inputs(s)
    h1 = compute_pd_inputs_hash(s)
    h2 = compute_pd_inputs_hash(s)
    assert h1 == h2
    fp = compute_pd_inputs_fingerprint(s)
    assert "Q_target" in fp
    assert "pd_eval_mode" in fp


def test_phase20_direct_evaluate_smoke() -> None:
    s = DesignSession()
    s.pd_eval_mode = "direct"
    sync_solver_bounds_from_inputs(s)
    result = run_point_designer_evaluation(s)
    assert isinstance(result.get("outputs"), dict)
    assert result["outputs"]
    assert isinstance(result.get("log_lines"), list)


def test_phase20_solver_evaluate_smoke() -> None:
    s = DesignSession()
    s.pd_eval_mode = "solver"
    sync_solver_bounds_from_inputs(s)
    result = run_point_designer_evaluation(s)
    assert isinstance(result.get("outputs"), dict)
    assert isinstance(result.get("trace"), list)


def test_phase20_build_point_inputs_knobs() -> None:
    s = DesignSession()
    s.overlay["include_transport_envelope_v396"] = True
    s.knobs["transport_spread_max_v396"] = 0.25
    inp = s.build_point_inputs()
    assert bool(getattr(inp, "include_transport_envelope_v396", False))
    assert float(getattr(inp, "transport_spread_max_v396", float("nan"))) == 0.25


def test_phase20_physics_deepening_import() -> None:
    from ui_nicegui.decks.point_designer import configure_operating_targets, pd_physics_deepening

    assert callable(configure_operating_targets.render_operating_targets)
    assert callable(pd_physics_deepening.render_physics_deepening)


def test_phase20_configure_operating_targets_import() -> None:
    from ui_nicegui.decks.point_designer.configure import render_configure

    assert callable(render_configure)
