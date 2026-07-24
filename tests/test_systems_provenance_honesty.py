"""Systems Mode provenance honesty — PD fallback vs real Systems solve."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_normalize_never_invents_systems_solve_for_pd_blob():
    from ui_nicegui.lib.systems_artifact import (
        fetch_systems_artifact,
        normalize_systems_artifact_source,
    )
    from ui_nicegui.session import DesignSession

    assert normalize_systems_artifact_source({}) == "point_designer_fallback"
    assert (
        normalize_systems_artifact_source({"source": "systems_solve"}) == "systems_solve"
    )
    assert (
        normalize_systems_artifact_source({"source": "point_designer_apply"})
        == "point_designer_apply"
    )
    assert (
        normalize_systems_artifact_source({"artifact_kind": "systems"})
        == "systems_restored"
    )
    assert normalize_systems_artifact_source({"artifact_kind": "systems"}) != "systems_solve"

    s = DesignSession()
    s.systems_last_solve_artifact = {
        "verdict": "FEASIBLE",
        "outputs": {"Q_DT_eqv": 5.0, "P_e_net_MW": 100.0},
        # missing source — Apply residue must not become systems_solve
    }
    art = fetch_systems_artifact(s)
    assert isinstance(art, dict)
    assert art.get("source") == "point_designer_fallback"


def test_has_systems_closure_ignores_pd_apply():
    from ui_nicegui.lib.helm_workflow_guide import has_systems_closure

    sess = SimpleNamespace(
        systems_last_solve_artifact={
            "source": "point_designer_apply",
            "verdict": "FEASIBLE",
            "outputs": {"Q_DT_eqv": 3.0},
        },
        systems_last_solve_result=None,
    )
    assert has_systems_closure(sess) is False

    # Leftover Newton ok=True must not close when visible artifact is PD Apply.
    sess.systems_last_solve_result = {"ok": True, "intent_feasible": True}
    assert has_systems_closure(sess) is False

    sess.systems_last_solve_artifact = {
        "source": "systems_solve",
        "verdict": "FEASIBLE",
        "outputs": {"Q_DT_eqv": 3.0},
    }
    assert has_systems_closure(sess) is True

    sess.systems_last_solve_artifact = {"source": "systems_recovery", "verdict": "INFEASIBLE"}
    assert has_systems_closure(sess) is False

    sess.systems_last_solve_artifact = {
        "source": "systems_recovery",
        "verdict": "FEASIBLE",
        "outputs": {"Q_DT_eqv": 2.0},
    }
    assert has_systems_closure(sess) is True

    sess.systems_last_solve_artifact = None
    sess.systems_last_solve_result = {"ok": True}
    assert has_systems_closure(sess) is True


def test_next_action_hint_apply_not_systems_solve():
    from ui_nicegui.lib.systems_labels import next_action_hint

    msg = next_action_hint(
        has_artifact=True,
        artifact_source="point_designer_apply",
        targets_ok=True,
        precheck_ok=True,
        solve_ok=True,
        n_candidates=2,
        n_feasible=0,
    )
    assert "not a Systems solve" in msg
    assert "target solve" in msg.lower()


def test_cockpit_markdown_labels_pd_source():
    from ui_nicegui.lib.systems_cockpit import build_compact_cockpit_markdown, compact_next_action

    md = build_compact_cockpit_markdown(
        SimpleNamespace(systems_decision_state=None),
        {
            "source": "point_designer_fallback",
            "verdict": "INFEASIBLE",
            "outputs": {"Q_DT_eqv": 12.0, "Pfus_total_MW": 500.0},
        },
    )
    assert "Artifact source: point_designer_fallback" in md
    assert "not a Systems Mode target solve" in md
    assert "Apply to Point Designer" not in md

    md_feas = build_compact_cockpit_markdown(
        SimpleNamespace(systems_decision_state="Apply & iterate (update Base/x0)"),
        {
            "source": "point_designer_fallback",
            "verdict": "FEASIBLE",
            "outputs": {
                "Q_DT_eqv": 5.0,
                "Pfus_total_MW": 400.0,
                "P_e_net_MW": 80.0,
                "feasible": True,
                "hard_failures": [],
            },
        },
    )
    assert "not a Systems Mode target solve" in md_feas
    assert "Apply to Point Designer" not in md_feas
    assert "PD seed" in md_feas or "not a Systems result" in md_feas

    action = compact_next_action(
        verdict="FEASIBLE",
        dominant="q95",
        step="Apply & iterate (update Base/x0)",
        artifact_source="point_designer_fallback",
    )
    assert "PD seed" in action or "not a Systems result" in action
    assert "Apply to Point Designer" not in action

    solve_action = compact_next_action(
        verdict="FEASIBLE",
        dominant="-",
        step="Apply & iterate (update Base/x0)",
        artifact_source="systems_solve",
    )
    assert "Apply to Point Designer" in solve_action


def test_systems_posture_banner_never_green_feasible_on_pd_seed():
    vsrc = Path("ui_nicegui/decks/systems_mode/verdict.py").read_text(encoding="utf-8")
    assert "PD BASELINE" in vsrc
    assert "normalize_systems_artifact_source" in vsrc
    assert "is_systems_result_source" in vsrc
    # Must not call verdict_banner with raw FEASIBLE for PD seeds as the only path.
    assert 'banner = "PD BASELINE"' in vsrc or 'banner = "PD INFEASIBLE"' in vsrc
    banner = Path("ui_nicegui/components/verdict_banner.py").read_text(encoding="utf-8")
    assert '"PD BASELINE"' in banner
    assert '"PD INFEASIBLE"' in banner


def test_apply_ui_sets_point_designer_apply_source():
    src = Path("ui_nicegui/decks/systems_mode/apply_ui.py").read_text(encoding="utf-8")
    assert 'applied_art["source"] = "point_designer_apply"' in src
    assert "systems_last_solve_result = None" in src
    assert "pd_solver_helpers import inputs_stale" in src or "from ui_nicegui.lib.pd_solver_helpers import inputs_stale" in src


def test_systems_stale_import_uses_pd_solver_helpers():
    for panel in (
        "ui_nicegui/decks/systems_mode/precheck_ui.py",
        "ui_nicegui/decks/systems_mode/solve_ui.py",
        "ui_nicegui/decks/systems_mode/apply_ui.py",
    ):
        src = Path(panel).read_text(encoding="utf-8")
        assert "from ui_nicegui.lib.pd_solver_helpers import inputs_stale" in src
        assert "from ui_nicegui.lib.session_store import inputs_stale" not in src


def test_systems_reproduce_stamps_restored_and_watermarks_download():
    src = Path("ui_nicegui/decks/systems_mode/reproduce_ui.py").read_text(encoding="utf-8")
    assert 'art["source"] = "systems_restored"' in src
    assert "systems_last_solve_result = None" in src
    assert "watermark_run_artifact_export" in src
    chron = Path("ui_nicegui/decks/systems_mode/chronicle_ui.py").read_text(encoding="utf-8")
    assert "_watermark_systems_run_card" in chron


def test_systems_baseline_chip_distinguishes_pd_seed():
    init_src = Path("ui_nicegui/decks/systems_mode/__init__.py").read_text(encoding="utf-8")
    assert "_baseline_chip_state" in init_src
    assert '"seed"' in init_src
    assert "is_systems_result_source" in init_src


def test_kpi_headline_does_not_use_dt_adj_as_total_pfus():
    from ui_nicegui.lib.systems_workflow_helpers import kpi_headline_from_outputs

    h = kpi_headline_from_outputs({"Pfus_DT_adj_MW": 400.0, "H_IPB98y2": 1.1, "Pe_net_MW": 50.0})
    assert h.get("Pfus") is None
    assert h.get("Pfus_DT_adj") == 400.0
    assert h.get("H98") == 1.1
    assert h.get("P_net") == 50.0
    h2 = kpi_headline_from_outputs({"Pfus_total_MW": 500.0, "Pfus_DT_adj_MW": 400.0})
    assert h2.get("Pfus") == 500.0


def test_systems_posture_stale_and_apply_labels():
    init_src = Path("ui_nicegui/decks/systems_mode/__init__.py").read_text(encoding="utf-8")
    assert "inputs_stale" in init_src
    assert "point_designer_apply" in init_src
    assert "systems_recovery" in init_src
    assert "systems_restored" in init_src
    vsrc = Path("ui_nicegui/decks/systems_mode/verdict.py").read_text(encoding="utf-8")
    assert "POINT DESIGNER APPLY" in vsrc
    assert "SYSTEMS RECOVERY" in vsrc
    assert "SYSTEMS RESTORED" in vsrc
    dsrc = Path("ui_nicegui/decks/systems_mode/diagnostics_ui.py").read_text(encoding="utf-8")
    assert "NOT A SYSTEMS SOLVE" in dsrc
    assert "is_systems_result_source" in dsrc
    for panel in (
        "ui_nicegui/decks/systems_mode/precheck_ui.py",
        "ui_nicegui/decks/systems_mode/solve_ui.py",
        "ui_nicegui/decks/systems_mode/apply_ui.py",
    ):
        assert "from ui_nicegui.lib.pd_solver_helpers import inputs_stale" in Path(panel).read_text(
            encoding="utf-8"
        )
    assert "Artifact source:" in Path("tools/reports/decision_report.py").read_text(encoding="utf-8")
    assert "Pfus_DT_adj_MW\": ()" in Path("ui_nicegui/lib/systems_target_banner.py").read_text(
        encoding="utf-8"
    ) or 'Pfus_DT_adj_MW": ()' in Path("ui_nicegui/lib/systems_target_banner.py").read_text(
        encoding="utf-8"
    )

def test_pd_and_cr_busy_guards_wired():
    pd = Path("ui_nicegui/decks/point_designer/__init__.py").read_text(encoding="utf-8")
    assert "PD_RUNNING_ATTRS" in pd
    assert "_refresh_pd_chrome_if_idle" in pd
    cr = Path("ui_nicegui/decks/control_room/__init__.py").read_text(encoding="utf-8")
    assert "_on_cr_tab_change" in cr
    assert 'runlock_status("ControlRoom")' in cr
    assert "watermark_run_artifact_export" in Path(
        "ui_nicegui/decks/control_room/artifacts.py"
    ).read_text(encoding="utf-8")
    pub = Path("benchmarks/publication/run_point_designer_benchmarks.py").read_text(encoding="utf-8")
    assert "Pfus_total_MW" in pub
    assert "q95_proxy" in pub

