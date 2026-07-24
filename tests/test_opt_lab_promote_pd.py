"""Opt Lab / ExtOpt promote-to-PD honesty (helm-decks deep loop)."""
from __future__ import annotations

from pathlib import Path

from ui_nicegui.session import DesignSession


def test_promote_opt_lab_best_from_cert_search():
    from ui_nicegui.lib.opt_lab_promote import promote_opt_lab_best_to_point_designer

    s = DesignSession()
    s.pd_last_outputs = {"Q_DT_eqv": 99.0}
    s.pd_last_artifact = {"outputs": {"Q_DT_eqv": 99.0}}
    before = float(s.inputs.get("Ip_MA", 0) or 0)
    s.v340_cert_search_last = {
        "schema_version": "certified_search_orchestrator_evidence.v3",
        "best": {"stage": "s1", "score": 1.0, "x": {"Ip_MA": before + 2.0}},
    }
    n, src = promote_opt_lab_best_to_point_designer(s)
    assert n >= 1
    assert src == "certified_search"
    assert float(s.inputs["Ip_MA"]) == before + 2.0
    assert s.pd_last_outputs is None


def test_promote_opt_lab_best_falls_back_to_pareto():
    from ui_nicegui.lib.opt_lab_promote import promote_opt_lab_best_to_point_designer

    s = DesignSession()
    s.pd_last_outputs = {"Q_DT_eqv": 50.0}
    before = float(s.inputs.get("R0_m", 0) or 0)
    s.pareto_last = {"pareto": [{"R0_m": before + 0.25, "Ip_MA": 9.0}]}
    s.pareto_bounds = {"R0_m": (1.0, 10.0), "Ip_MA": (1.0, 20.0)}
    n, src = promote_opt_lab_best_to_point_designer(s)
    assert n >= 1
    assert src == "pareto_front"
    assert float(s.inputs["R0_m"]) == before + 0.25
    assert s.pd_last_outputs is None


def test_promote_extopt_from_run_dir(tmp_path):
    from ui_nicegui.lib.opt_lab_promote import promote_extopt_first_feasible_to_point_designer

    run_dir = tmp_path / "extopt_run"
    run_dir.mkdir()
    (run_dir / "proposed_candidates.json").write_text(
        '{"n":1,"candidates":[{"status":"VERIFIED","inputs":{"Ip_MA":11.5,"R0_m":6.2}}]}',
        encoding="utf-8",
    )
    s = DesignSession()
    s.pd_last_outputs = {"Q": 1.0}
    s.extopt_last_run = {"run_dir": str(run_dir), "n_feasible": 1}
    n, src = promote_extopt_first_feasible_to_point_designer(s)
    assert n >= 1
    assert src == "extopt_ccfs_verified"
    assert float(s.inputs["Ip_MA"]) == 11.5
    assert s.pd_last_outputs is None


def test_opt_lab_and_extopt_ui_wires_promote():
    opt = Path("ui_nicegui/components/opt_lab_entry_panel.py").read_text(encoding="utf-8")
    assert "promote_opt_lab_best_to_point_designer" in opt
    assert "Promote certified best → Point Designer" in opt
    assert "navigate_to_point_designer" in opt
    ext = Path("ui_nicegui/decks/pareto_lab/external.py").read_text(encoding="utf-8")
    assert "promote_extopt_first_feasible_to_point_designer" in ext
    assert "PARETO_RUNNING_ATTRS" in Path("ui_nicegui/decks/pareto_lab/__init__.py").read_text(
        encoding="utf-8"
    )
    assert "PARETO_RUNNING_ATTRS" in Path("ui_nicegui/lib/deck_busy_guard.py").read_text(
        encoding="utf-8"
    )
    assert "FORGE_RUNNING_ATTRS" in Path("ui_nicegui/lib/deck_busy_guard.py").read_text(
        encoding="utf-8"
    )
