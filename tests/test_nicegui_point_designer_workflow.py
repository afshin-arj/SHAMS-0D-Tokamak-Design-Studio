"""Point Designer Truth Console workflow labels and authority toggles."""
from __future__ import annotations

from ui_nicegui.lib.pd_authority_toggles import (
    AUTHORITY_OVERLAY_TOGGLES,
    AUTHORITY_TOGGLE_KEYS,
    count_enabled,
    default_overlay_bool,
    reactor_intent_hint,
)
from ui_nicegui.lib.pd_workflow_labels import (
    DECISION_STATES,
    DECISION_TO_TAB,
    PD_TRUTH_TABS,
    TAB_HELP,
    normalize_pd_tab,
    teaching_banner,
)
from ui_nicegui.session import DesignSession


def test_pd_workflow_tabs_complete() -> None:
    assert len(PD_TRUTH_TABS) == 3
    for tab in PD_TRUTH_TABS:
        assert tab in TAB_HELP


def test_normalize_pd_tab_legacy() -> None:
    assert normalize_pd_tab("Configure") == "1 · Configure"
    assert normalize_pd_tab("2 · Telemetry") == "2 · Telemetry"
    assert normalize_pd_tab("unknown") == "1 · Configure"


def test_decision_routes_to_tab() -> None:
    assert DECISION_TO_TAB[DECISION_STATES[2]] == "2 · Telemetry"
    assert DECISION_TO_TAB[DECISION_STATES[3]] == "3 · Constraints"


def test_teaching_banner_guided() -> None:
    s = DesignSession()
    s.pd_teaching_mode = True
    s.pd_decision_state = DECISION_STATES[1]
    assert "Evaluate Point" in teaching_banner(s)
    s.pd_teaching_mode = False
    assert teaching_banner(s) == ""


def test_authority_toggle_defaults_reactor() -> None:
    s = DesignSession()
    s.design_intent = "Power Reactor (net-electric)"
    overlay = {}
    for key, _, _ in AUTHORITY_OVERLAY_TOGGLES:
        overlay[key] = default_overlay_bool(overlay, key, s.design_intent)
    enabled, total = count_enabled(overlay)
    assert total == len(AUTHORITY_TOGGLE_KEYS)
    assert enabled >= 0
    assert "tritium" in reactor_intent_hint(s.design_intent).lower()


def test_overlay_gating_clears_v371_when_off() -> None:
    from ui_nicegui.lib.point_inputs_builder import build_point_inputs

    import math

    s = DesignSession()
    s.knobs["H_required_max_optimistic"] = 2.0
    s.knobs["H_required_max_robust"] = 1.5
    s.overlay["include_transport_contracts_v371"] = False
    inp = build_point_inputs(s)
    assert math.isnan(float(inp.H_required_max_optimistic))
    assert math.isnan(float(inp.H_required_max_robust))


def test_envelope_targets_matched_dof() -> None:
    from ui_nicegui.lib.pd_solver_helpers import _envelope_targets

    s = DesignSession()
    s.pd_eval_mode = "envelope"
    s.pd_pfus_target = 0.0
    s.pd_pnet_target = -1.0
    tgt, vary, _ = _envelope_targets(s)
    assert len(tgt) == len(vary) == 2
    assert "Q_DT_eqv" in tgt and "H98" in tgt


def test_run_summary_on_artifact() -> None:
    from ui_nicegui.evaluate import ui_evaluate
    from ui_nicegui.lib.session_store import set_point_evaluation

    s = DesignSession()
    out = ui_evaluate(s.build_point_inputs(), origin="test")
    set_point_evaluation(s, outputs=out, inputs=dict(s.inputs))
    art = s.pd_last_artifact or {}
    assert isinstance(art.get("run_summary"), dict)
    assert "tightest_hard_constraints" in art["run_summary"]


def test_pd_pfus_default_ignores_envelope() -> None:
    s = DesignSession()
    assert s.pd_pfus_target == 0.0


def test_build_point_inputs_physics_parity_fields() -> None:
    from ui_nicegui.lib.point_inputs_builder import build_point_inputs

    s = DesignSession()
    s.inputs["require_Hmode"] = True
    s.inputs["PLH_margin"] = 0.1
    s.inputs["ash_dilution_mode"] = "fixed_fraction"
    s.inputs["f_He_ash"] = 0.05
    s.inputs["include_particle_balance"] = True
    s.inputs["pedestal_enabled"] = True
    inp = build_point_inputs(s)
    assert bool(inp.require_Hmode) is True
    assert float(inp.PLH_margin) == 0.1
    assert str(inp.ash_dilution_mode) == "fixed_fraction"
    assert bool(inp.include_particle_balance) is True
    assert bool(inp.pedestal_enabled) is True


def test_unrealistic_input_warnings_geometry() -> None:
    from types import SimpleNamespace

    from ui_nicegui.lib.pd_input_guardrails import unrealistic_point_input_warnings

    pi = SimpleNamespace(R0_m=0.3, a_m=0.5, kappa=1.8, delta=0.0, Bt_T=10.0, Ip_MA=8.0,
                         Ti_keV=10.0, fG=0.8, Paux_MW=50.0, t_shield_m=0.8)
    warns = unrealistic_point_input_warnings(pi)
    assert any("aspect" in w.lower() or "R₀" in w for w in warns)


def test_solver_target_rows_direct_empty() -> None:
    from ui_nicegui.lib.pd_solver_banner import solver_target_rows

    s = DesignSession()
    s.pd_eval_mode = "direct"
    assert solver_target_rows(s) == []


def test_solver_target_rows_solver() -> None:
    from ui_nicegui.lib.pd_solver_banner import solver_target_rows

    s = DesignSession()
    s.pd_eval_mode = "solver"
    s.pd_q_target = 2.0
    s.pd_h98_target = 1.15
    rows = solver_target_rows(s, {"Q_DT_eqv": 1.8, "H98": 1.1})
    assert len(rows) == 2
    assert rows[0]["quantity"] == "Q_DT_eqv"


def test_subsystem_enabled_stamped_on_eval() -> None:
    from ui_nicegui.evaluate import ui_evaluate
    from ui_nicegui.lib.session_store import set_point_evaluation

    s = DesignSession()
    s.knobs["_subsystem_enabled"] = {"magnets": True, "fuelcycle": False}
    out = ui_evaluate(s.build_point_inputs(), origin="test")
    set_point_evaluation(s, outputs=out, inputs=dict(s.inputs))
    assert s.pd_last_outputs.get("_subsystem_enabled", {}).get("fuelcycle") is False
