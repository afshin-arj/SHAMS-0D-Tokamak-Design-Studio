"""Phase 21: Point Designer telemetry parity helpers and panel wiring."""
from __future__ import annotations

from ui_nicegui.decks.point_designer import (
    chronicle_export,
    control_contracts,
    forensics,
    ledgers,
    mission_snapshot,
    plot_deck,
    sensitivity_lab,
    telemetry,
)
from ui_nicegui.evaluate import ui_evaluate
from ui_nicegui.lib.pd_parity_helpers import (
    assumptions_snapshot,
    authority_contract_rows,
    baseline_delta_rows,
    build_coils_metrics,
    constraint_radar_rows,
    fuel_cycle_metric_groups,
    lever_recipe_tables,
    local_fd_sensitivity_rows,
    magnet_card_metrics,
    magnet_v400_summary,
    pin_ploss_closure_mw,
    power_ledger_badged_rows,
    regime_compass_rows,
    run_perturbation_scan,
    tau_peaking_panel_data,
    v396_scaling_rows,
    v397_profile_summary,
    PERT_SCAN_PARAMS,
)
from ui_nicegui.session import DesignSession


def test_phase21_telemetry_tau_peaking_hook() -> None:
    assert callable(telemetry.render_tau_peaking_panel)
    data = tau_peaking_panel_data({})
    assert data is None or isinstance(data, dict)


def test_phase21_assumptions_snapshot() -> None:
    s = DesignSession()
    snap = assumptions_snapshot(s)
    assert "design_intent" in snap
    assert "fuel_mode" in snap


def test_phase21_regime_compass_rows_smoke() -> None:
    rows = regime_compass_rows({"H98": 1.0, "fG": 0.8, "q95_proxy": 3.5})
    assert len(rows) >= 10
    assert rows[1]["metric"] == "H98"


def test_phase21_authority_contract_rows_smoke() -> None:
    rows, n_proxy = authority_contract_rows({})
    assert isinstance(rows, list)
    assert isinstance(n_proxy, int)


def test_phase21_power_ledger_badges_and_closure() -> None:
    out = {"Pin_MW": 100.0, "Ploss_MW": 95.0, "Paux_MW": 50.0}
    rows = power_ledger_badged_rows(out)
    assert any(r["type"] == "Authoritative" for r in rows)
    closure = pin_ploss_closure_mw(out)
    assert closure is not None and abs(closure - 5.0) < 1e-6


def test_phase21_build_coils_and_magnet_card() -> None:
    out = {"inboard_margin_m": 0.1, "B_peak_T": 12.0, "magnet_technology": "HTS_REBCO", "tf_sc_flag": 1.0}
    coils = build_coils_metrics(out)
    assert len(coils) == 8
    mc = magnet_card_metrics(out)
    assert mc["tech"] == "HTS_REBCO"
    assert magnet_v400_summary(out) is None


def test_phase21_fuel_cycle_groups_smoke() -> None:
    groups = fuel_cycle_metric_groups({"TBR": 1.1, "availability_model": 0.85})
    assert len(groups) >= 2


def test_phase21_constraint_radar_smoke() -> None:
    s = DesignSession()
    inp = s.build_point_inputs()
    out = ui_evaluate(inp, origin="test:phase21")
    rows = constraint_radar_rows(out)
    assert isinstance(rows, list)


def test_phase21_baseline_delta_rows() -> None:
    base = {"outputs": {"Q_DT_eqv": 1.0, "H98": 1.0}}
    cur = {"outputs": {"Q_DT_eqv": 2.0, "H98": 1.1}}
    rows = baseline_delta_rows(base, cur)
    assert rows[0]["KPI"] == "Q_DT_eqv"
    assert rows[0]["delta"] != "n/a"


def test_phase21_lever_recipe_tables_empty() -> None:
    help_r, hurt_r, dom = lever_recipe_tables({})
    assert help_r == [] and hurt_r == [] and dom == ""


def test_phase21_pert_scan_params_count() -> None:
    assert len(PERT_SCAN_PARAMS) == 8


def test_phase21_local_fd_and_pert_scan_smoke() -> None:
    s = DesignSession()
    base = s.build_point_inputs()

    def _eval(pi):
        return ui_evaluate(pi, origin="test:phase21fd")

    fd_rows = local_fd_sensitivity_rows(base, _eval, params=["R0_m", "Ip_MA"], outputs=["Q_DT_eqv"])
    assert isinstance(fd_rows, list)
    scan_rows = run_perturbation_scan(base, _eval, params=["Ip_MA"])
    assert isinstance(scan_rows, list)


def test_phase21_v396_v397_helpers() -> None:
    assert v396_scaling_rows({}) == []
    assert v397_profile_summary({}) is None


def test_phase21_renderers_import() -> None:
    assert callable(mission_snapshot.render_mission_snapshot)
    assert callable(control_contracts.render_control_contracts)
    assert callable(ledgers.render_ledgers)
    assert callable(sensitivity_lab.render_sensitivity_lab)
    assert callable(forensics.render_forensics)
    assert callable(plot_deck.render_plot_deck)
    assert callable(chronicle_export.render_chronicle_export)
    assert callable(chronicle_export.render_compare_slot_actions)
    assert callable(chronicle_export.render_radial_build_export)
    assert callable(telemetry.render_telemetry)
