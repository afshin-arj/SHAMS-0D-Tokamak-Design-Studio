"""Scatter-shadow PHYS-KPI honesty — Trade Study explore + Forge archive."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_allow_infeasible_scatter_point_claim_axes():
    from ui_nicegui.lib.plant_kpi_honesty_ui import (
        allow_infeasible_scatter_point,
        is_claim_scatter_axis,
        scatter_physkpi_caption,
    )

    assert is_claim_scatter_axis("max_Q")
    assert is_claim_scatter_axis("P_e_net_MW")
    assert not is_claim_scatter_axis("R0_m")
    assert allow_infeasible_scatter_point(x_key="R0_m", y_key="Bt_T")
    assert not allow_infeasible_scatter_point(x_key="max_Q", y_key="max_H98")
    assert not allow_infeasible_scatter_point(x_key="R0_m", y_key="P_e_net_MW")
    cap = scatter_physkpi_caption("max_Q", "R0_m", show_infeasible=True)
    assert cap and "PHYS-KPI-001" in cap
    assert scatter_physkpi_caption("R0_m", "Bt_T", show_infeasible=True) is None


def test_trade_infeasible_shadow_omits_claim_axes():
    from ui_nicegui.decks.trade_study_studio.explore import _infeasible_shadow

    records = [
        {"is_feasible": False, "max_Q": 10.0, "R0_m": 6.0, "Bt_T": 5.0},
        {"is_feasible": False, "max_Q": 8.0, "R0_m": 5.5, "Bt_T": 4.5},
        {"is_feasible": True, "max_Q": 2.0, "R0_m": 5.0, "Bt_T": 4.0},
    ]
    assert _infeasible_shadow(records, "max_Q", "max_H98") == []
    assert _infeasible_shadow(records, "R0_m", "max_Q") == []
    geom = _infeasible_shadow(records, "R0_m", "Bt_T")
    assert len(geom) == 2
    assert all(not r["is_feasible"] for r in geom)


def test_trade_explore_wires_physkpi():
    src = Path("ui_nicegui/decks/trade_study_studio/explore.py").read_text(encoding="utf-8")
    assert "allow_infeasible_scatter_point" in src
    assert "scatter_physkpi_caption" in src


def test_forge_workbench_wires_physkpi_scatter():
    src = Path("ui_nicegui/decks/reactor_design_forge/workbench.py").read_text(encoding="utf-8")
    assert "allow_infeasible_scatter_point" in src
    assert "scatter_physkpi_caption" in src
    assert "Omitted" in src and "PHYS-KPI-001" in src
