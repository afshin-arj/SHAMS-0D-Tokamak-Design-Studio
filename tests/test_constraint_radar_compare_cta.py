"""Constraint radar proxy labels + Compare dual-INFEAS CTA (helm-decks deep loop)."""
from __future__ import annotations

from pathlib import Path


def test_constraint_display_name_proxy_honesty():
    from ui_nicegui.lib.pd_parity_helpers import (
        constraint_display_name,
        constraint_suggestion,
    )

    assert constraint_display_name("q95") == "q95 (cyl. proxy)"
    assert constraint_display_name("Safety factor (q95)") == "q95 (cyl. proxy)"
    assert "screening" in constraint_display_name("Troyon beta_N").lower()
    assert "screening" in constraint_display_name("betaN").lower()
    sug = constraint_suggestion("q95")
    assert "cyl" in sug.lower() or "proxy" in sug.lower()
    assert "equilibrium" in sug.lower()
    beta_sug = constraint_suggestion("Troyon beta_N")
    assert "screening" in beta_sug.lower()
    assert "ideal-wall" in beta_sug.lower() or "troyon" in beta_sug.lower()


def test_constraint_radar_rows_remap_display_keep_id():
    from ui_nicegui.lib.pd_parity_helpers import constraint_radar_rows

    art = {
        "constraints": [
            {
                "name": "q95",
                "passed": False,
                "margin_frac": -0.1,
                "severity": "hard",
                "sense": ">=",
                "value": 2.0,
                "limit": 3.0,
            },
            {
                "name": "Troyon beta_N",
                "passed": True,
                "margin_frac": 0.2,
                "severity": "hard",
                "sense": "<=",
                "value": 2.5,
                "limit": 3.5,
            },
        ]
    }
    rows = constraint_radar_rows({}, art)
    by_id = {r["constraint_id"]: r for r in rows}
    assert by_id["q95"]["constraint"] == "q95 (cyl. proxy)"
    assert "screening" in by_id["Troyon beta_N"]["constraint"].lower()


def test_mission_snapshot_wires_display_map():
    src = Path("ui_nicegui/decks/point_designer/mission_snapshot.py").read_text(encoding="utf-8")
    assert "constraint_display_name" in src
    assert "cylindrical / screening proxies" in src
    assert "constraint_id" in src


def test_compare_dual_infeas_cta_and_chrome():
    verdict = Path("ui_nicegui/decks/compare/verdict.py").read_text(encoding="utf-8")
    assert 'step="3 · Constraints"' in verdict
    assert "Go to Constraints" in verdict
    assert "Subsystem pass ≠ overall FEASIBLE" in verdict
    init = Path("ui_nicegui/decks/compare/__init__.py").read_text(encoding="utf-8")
    assert "dual INFEASIBLE (diagnostic compare)" in init
    assert "mixed feasibility (not a PASS)" in init
    assert "text-positive" in init  # still used for dual-feasible ready chrome
