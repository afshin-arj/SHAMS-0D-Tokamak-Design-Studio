"""Pareto Lab + Systems explore scatter PHYS-KPI honesty."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_failure_atlas_omits_claim_axes():
    from ui_nicegui.lib.pareto_interpret_helpers import failure_atlas_points

    samples = [
        {"is_feasible": False, "P_e_net_MW": 100.0, "Q_DT_eqv": 12.0, "R0_m": 6.0, "Bt_T": 5.0},
        {"is_feasible": False, "P_e_net_MW": 80.0, "Q_DT_eqv": 8.0, "R0_m": 5.5, "Bt_T": 4.5},
        {"is_feasible": True, "P_e_net_MW": 40.0, "Q_DT_eqv": 3.0, "R0_m": 5.0, "Bt_T": 4.0},
    ]
    assert failure_atlas_points(samples, "P_e_net_MW", "Q_DT_eqv") == []
    assert failure_atlas_points(samples, "R0_m", "P_e_net_MW") == []
    geom = failure_atlas_points(samples, "R0_m", "Bt_T")
    assert len(geom) == 2
    assert all("first_failure" in r for r in geom)


def test_pareto_explore_wires_physkpi():
    src = Path("ui_nicegui/decks/pareto_lab/explore.py").read_text(encoding="utf-8")
    assert "scatter_physkpi_caption" in src
    assert "show_failures" in src
    assert "non-claim axes" in src


def test_systems_trace_omits_infeasible_claim_shadow():
    src = Path("ui_nicegui/decks/systems_mode/explore_ui.py").read_text(encoding="utf-8")
    assert "PHYS-KPI-001: omitted infeasible search-trace" in src
    assert "feasible only" in src
    assert "infeas_x" not in src
