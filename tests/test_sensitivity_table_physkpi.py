"""PHYS-KPI-001 watermarking for sensitivity / jacobian tables."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_format_sens_value_watermarks_claim_kpi_on_infeasible():
    from ui_nicegui.lib.sensitivity_honesty import format_sens_value

    assert format_sens_value("Q_DT_eqv", 1.23, feasible=False).startswith("diag·")
    assert format_sens_value("H98", 1.1, feasible=False).startswith("diag·")
    assert format_sens_value("H_IPB98y2", 1.15, feasible=False).startswith("diag·")
    assert format_sens_value("P_e_net_MW", 50.0, feasible=False).startswith("diag·")
    assert format_sens_value("q95_proxy", 3.2, feasible=False) == "3.2"
    assert format_sens_value("Q_DT_eqv", 1.23, feasible=True) == "1.23"


def test_format_sens_base_suppresses_claim_on_infeasible():
    from ui_nicegui.lib.sensitivity_honesty import format_sens_base_output

    assert "diagnostic" in format_sens_base_output("Q_DT_eqv", 12.0, feasible=False).lower()
    assert format_sens_base_output("Q_DT_eqv", 12.0, feasible=True) == "12"


def test_jacobian_and_fd_rows_watermark():
    from ui_nicegui.lib.sensitivity_honesty import (
        fd_parity_rows_watermark,
        fd_sensitivity_table_rows,
        jacobian_table_rows,
    )

    pack = {"jacobian": {"Q_DT_eqv": {"Ip_MA": 0.5}, "q95_proxy": {"Ip_MA": 0.1}}}
    rows = jacobian_table_rows(pack, ["Ip_MA"], ["Q_DT_eqv", "q95_proxy"], feasible=False)
    by = {(r["output"], r["knob"]): r["jacobian"] for r in rows}
    assert str(by[("Q_DT_eqv", "Ip_MA")]).startswith("diag·")
    assert by[("q95_proxy", "Ip_MA")] == "0.1"

    rep = {"_base": {"Q_DT_eqv": 5.0}, "Q_DT_eqv": {"Ip_MA": 0.2}, "beta_N": {"Ip_MA": 0.01}}
    fd = fd_sensitivity_table_rows(rep, feasible=False)
    q_rows = [r for r in fd if r["output"] == "Q_DT_eqv"]
    assert q_rows and str(q_rows[0]["sensitivity"]).startswith("diag·")
    base_rows = [r for r in fd if str(r["output"]).startswith("base:")]
    assert base_rows
    assert "diagnostic" in str(base_rows[0]["sensitivity"]).lower()

    parity = fd_parity_rows_watermark(
        [{"output": "Q_DT_eqv", "param": "Ip_MA", "dY/dX": "0.4", "elasticity": "0.2"}],
        feasible=False,
    )
    assert str(parity[0]["dY/dX"]).startswith("diag·")


def test_cr_sensitivity_table_rows_forwards_feasible():
    import inspect
    from ui_nicegui.lib import cr_chronicle_helpers as h

    assert "feasible" in inspect.signature(h.sensitivity_table_rows).parameters


def test_surfaces_use_sensitivity_honesty():
    assert "sensitivity_honesty" in Path("ui_nicegui/decks/systems_mode/tools_ui.py").read_text(encoding="utf-8")
    assert "sensitivity_honesty" in Path("ui_nicegui/decks/control_room/chronicle.py").read_text(encoding="utf-8")
    assert "fd_parity_rows_watermark" in Path(
        "ui_nicegui/decks/point_designer/sensitivity_lab.py"
    ).read_text(encoding="utf-8")
    assert "format_claim_kpi_for_table" in Path(
        "ui_nicegui/decks/point_designer/sensitivity_lab.py"
    ).read_text(encoding="utf-8")
