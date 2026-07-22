"""Compare dual-INFEASIBLE honesty — constraints caption + Apply CTAs."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_new_hard_failures_caption_dual_infeasible_not_positive():
    from ui_nicegui.lib.compare_helpers import new_hard_failures_caption

    msg, cls = new_hard_failures_caption(feas_a=False, feas_b=False, n_new_fail=0)
    assert "INFEASIBLE" in msg
    assert "not a PASS" in msg
    assert "text-positive" not in cls
    assert "text-orange" in cls

    ok_msg, ok_cls = new_hard_failures_caption(feas_a=True, feas_b=True, n_new_fail=0)
    assert "No new hard constraint failures" in ok_msg
    assert "text-positive" in ok_cls

    fail_msg, fail_cls = new_hard_failures_caption(feas_a=True, feas_b=True, n_new_fail=2)
    assert "2 new hard failure" in fail_msg
    assert "text-negative" in fail_cls


def test_constraints_panel_wires_caption_helper():
    src = Path("ui_nicegui/decks/compare/constraints_panel.py").read_text(encoding="utf-8")
    assert "new_hard_failures_caption" in src
    assert "text-positive q-mb-sm" not in src or "new_hard_failures_caption" in src
    # Must not hard-code green success when no new failures without feasibility gate.
    assert "No new hard constraint failures in B relative to A." not in src


def test_verdict_detail_states_dual_infeasible_not_pass():
    src = Path("ui_nicegui/decks/compare/verdict.py").read_text(encoding="utf-8")
    assert "Both slots INFEASIBLE — comparison is diagnostic, not a PASS" in src
    assert 'in ("FEASIBLE", "PASS")' in src
    assert '"FEAS" in' not in src


def test_export_apply_marks_diagnostic_on_infeasible():
    src = Path("ui_nicegui/decks/compare/export_panel.py").read_text(encoding="utf-8")
    assert "(diagnostic)" in src
    assert "INFEASIBLE" in src
    assert "feasible=feas_a" in src or "feasible=feas_a" in src.replace(" ", "")
