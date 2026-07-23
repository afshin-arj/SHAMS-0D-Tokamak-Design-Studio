"""CCFS / frontier NiceGUI choke-point injection + Compare PHYS-KPI honesty."""
from __future__ import annotations

import inspect
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_verify_ccfs_bundle_accepts_evaluator_kwarg():
    from src.extopt.certified_solve import verify_ccfs_bundle

    assert "evaluator" in inspect.signature(verify_ccfs_bundle).parameters


def test_run_optimizer_job_accepts_evaluator_kwarg():
    from src.extopt.orchestrator import run_optimizer_job

    assert "evaluator" in inspect.signature(run_optimizer_job).parameters


def test_nicegui_ccfs_helper_injects_ui_evaluator():
    from ui_nicegui.lib import external_optimizer_helpers as h

    src = inspect.getsource(h.run_optimizer_job)
    assert "ui_evaluator" in src
    assert "evaluator=ev" in src or "evaluator=ev," in src
    # Call-order bug fix: repo root first positional
    assert "_run_job(repo()" in src or "_run_job(repo()," in src


def test_frontier_uses_evaluator_bridge():
    from src.frontier import frontier as fr

    src = inspect.getsource(fr.find_nearest_feasible)
    assert "evaluate_point" in src
    assert "Evaluator()" not in src


def test_search_nearest_feasible_sets_override():
    from ui_nicegui.lib import pd_solver_helpers as pd

    src = inspect.getsource(pd.search_nearest_feasible)
    assert "set_evaluate_point_override" in src
    assert "ui_evaluate" in src


def test_compare_helpers_watermark_claim_kpis():
    from ui_nicegui.lib import compare_helpers as ch

    assert "format_claim_kpi_for_table" in inspect.getsource(ch.metric_diff_rows)
    assert "format_claim_kpi_for_table" in inspect.getsource(ch.kpi_diff_rows)
    assert "PHYS-KPI-001" in inspect.getsource(ch.comparison_markdown)


def test_systems_handoff_clears_pd_kpis_and_refreshes_helm():
    from ui_nicegui.lib import systems_handoff as sh

    src = inspect.getsource(sh.consume_systems_mode_queue)
    assert "invalidate_point_designer_after_seed" in src
    assert "refresh_helm" in src
    assert "prior KPIs cleared" in src


def test_frontier_panel_distinguishes_best_effort():
    from pathlib import Path

    src = Path("ui_nicegui/decks/point_designer/chronicle_export.py").read_text(encoding="utf-8")
    assert "best_ok" in src
    assert "BEST-EFFORT" in src
    assert "FEASIBLE neighbor found" in src