"""Smoke: import NiceGUI modules and verify evaluate wiring without starting server."""
from __future__ import annotations


def test_nicegui_evaluate_module_imports() -> None:
    from ui_nicegui.evaluate import ui_evaluate  # noqa: F401


def test_nicegui_session_builds_point_inputs() -> None:
    from ui_nicegui.session import DesignSession

    s = DesignSession(inputs={"R0_m": 1.85, "a_m": 0.57, "kappa": 1.8, "Bt_T": 12.2,
                              "Ip_MA": 8.7, "Ti_keV": 12.0, "fG": 0.85, "Paux_MW": 25.0})
    inp = s.build_point_inputs()
    assert float(inp.R0_m) == 1.85


def test_ui_evaluate_routes_through_evaluator() -> None:
    from ui_nicegui.evaluate import ui_evaluate
    from ui_nicegui.session import DesignSession

    s = DesignSession(inputs={"R0_m": 1.85, "a_m": 0.57, "kappa": 1.8, "Bt_T": 12.2,
                              "Ip_MA": 8.7, "Ti_keV": 12.0, "fG": 0.85, "Paux_MW": 25.0})
    out = ui_evaluate(s.build_point_inputs(), origin="test")
    assert isinstance(out, dict)
    assert len(out) > 10
    assert "B0_T" in out or "Pfus_MW" in out
