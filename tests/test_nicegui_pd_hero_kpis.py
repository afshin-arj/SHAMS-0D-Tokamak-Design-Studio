"""Hero KPI suppression policy — infeasible diagnostic honesty."""
from __future__ import annotations

from ui_nicegui.decks.point_designer.configure_engineering import _apply_confidence
from ui_nicegui.lib.pd_hero_kpis import hero_kpi_cells
from ui_nicegui.lib.verdict_core import verdict_summary
from ui_nicegui.session import DesignSession


def _summary_infeasible() -> dict:
    return {
        "loaded": True,
        "feasible": False,
        "verdict": "INFEASIBLE",
        "dominant": "q_div",
        "q_label": "Q=679",
        "nt_label": "nτE≈1.2e21",
        "subsystems": {},
    }


def test_hero_suppresses_extreme_q_on_infeasible() -> None:
    out = {"Q_DT_eqv": 679.0, "H98": 1.07, "P_net_e_MW": 100.0}
    cells = hero_kpi_cells(out, _summary_infeasible(), design_intent="Power Reactor (net-electric)")
    perf = cells[0]
    assert perf.suppressed is True
    assert "diagnostic" in perf.display.lower()
    assert cells[2].suppressed is True


def test_hero_suppresses_high_h98_on_infeasible() -> None:
    out = {"Q_DT_eqv": 5.0, "H98": 3.28, "P_net_e_MW": 50.0}
    cells = hero_kpi_cells(out, _summary_infeasible(), design_intent="Experimental Device (research)")
    h98 = cells[1]
    assert h98.suppressed is True
    assert "implied" in h98.display.lower()


def test_hero_shows_kpis_when_feasible() -> None:
    out = {"Q_DT_eqv": 2.5, "H98": 1.05, "P_net_e_MW": 120.0}
    summary = {
        "loaded": True,
        "feasible": True,
        "verdict": "FEASIBLE",
        "q_label": "Q=2.50",
        "nt_label": "nτE≈1e21",
        "subsystems": {},
    }
    cells = hero_kpi_cells(out, summary, design_intent="Power Reactor (net-electric)")
    assert cells[0].suppressed is False
    assert cells[1].suppressed is False
    assert "120" in cells[2].display


def test_confidence_preset_overwrites_knobs() -> None:
    s = DesignSession()
    s.knobs["q_div_max_MW_m2"] = 10.0
    _apply_confidence(s, "Conservative")
    assert float(s.knobs["q_div_max_MW_m2"]) == 7.0
    _apply_confidence(s, "Aggressive")
    assert float(s.knobs["q_div_max_MW_m2"]) == 15.0


def test_verdict_summary_still_raw() -> None:
    from ui_nicegui.evaluate import ui_evaluate

    s = DesignSession()
    out = ui_evaluate(s.build_point_inputs(), origin="test")
    summary = verdict_summary(out)
    assert "Q=" in summary["q_label"]


def test_helm_calibration_wired_to_point_inputs() -> None:
    s = DesignSession()
    s.calib_confinement = 0.75
    s.calib_divertor = 1.1
    s.calib_bootstrap = 0.9
    inp = s.build_point_inputs()
    assert float(inp.calib_confinement) == 0.75
    assert float(inp.calib_divertor) == 1.1
    assert float(inp.calib_bootstrap) == 0.9


def test_sparc_preset_credible_mission_closure() -> None:
    from ui_nicegui.lib.helm_helpers import apply_legacy_reference_machine_to_session
    from ui_nicegui.evaluate import ui_evaluate

    s = DesignSession()
    apply_legacy_reference_machine_to_session(s, "SPARC-class (compact HTS)")
    out = ui_evaluate(s.build_point_inputs(), origin="test")
    q = float(out.get("Q_DT_eqv", 0))
    h98 = float(out.get("H98", 0))
    assert 0.5 < q < 5.0
    assert 1.0 < h98 < 2.5


def test_calibration_scales_h98_in_evaluation() -> None:
    from ui_nicegui.evaluate import ui_evaluate

    s1 = DesignSession()
    s1.calib_confinement = 0.7
    s2 = DesignSession()
    s2.calib_confinement = 1.3
    h1 = float(ui_evaluate(s1.build_point_inputs(), origin="t").get("H98"))
    h2 = float(ui_evaluate(s2.build_point_inputs(), origin="t").get("H98"))
    assert h1 < h2


def test_confidence_shifts_engineering_limits_in_constraints() -> None:
    from ui_nicegui.decks.point_designer.configure_engineering import _apply_confidence
    from ui_nicegui.evaluate import ui_evaluate
    from ui_nicegui.lib.verdict_core import constraint_table_rows

    s_c = DesignSession()
    _apply_confidence(s_c, "Conservative")
    s_a = DesignSession()
    _apply_confidence(s_a, "Aggressive")
    lim_c = float(s_c.build_point_inputs().q_div_max_MW_m2)
    lim_a = float(s_a.build_point_inputs().q_div_max_MW_m2)
    assert lim_c == 7.0 and lim_a == 15.0

    out_c = ui_evaluate(s_c.build_point_inputs(), origin="t")
    out_a = ui_evaluate(s_a.build_point_inputs(), origin="t")
    qdiv_c = next(r for r in constraint_table_rows(out_c) if r["name"] == "q_div")
    qdiv_a = next(r for r in constraint_table_rows(out_a) if r["name"] == "q_div")
    assert float(qdiv_c["limit"]) == 7.0
    assert float(qdiv_a["limit"]) == 15.0
    assert float(qdiv_a["residual"]) > float(qdiv_c["residual"])
