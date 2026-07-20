"""Batch 3: Systems Mode verdict-first + precheck wiring."""

from __future__ import annotations



from ui_nicegui.decks.systems_mode import render_systems_mode

from ui_nicegui.evaluate import ui_evaluate

from ui_nicegui.lib.session_store import set_point_evaluation

from ui_nicegui.lib.systems_artifact import fetch_systems_artifact, synthesize_from_point

from ui_nicegui.lib.systems_precheck import (

    build_targets_and_variables,

    run_systems_precheck,

)

from ui_nicegui.session import DesignSession





def test_systems_mode_renderer_import() -> None:

    assert callable(render_systems_mode)





def test_build_targets_variables_defaults() -> None:

    s = DesignSession()

    base = s.build_point_inputs()

    targets, variables = build_targets_and_variables(s, base)

    assert "Q_DT_eqv" in targets

    assert "Paux_MW" in variables

    assert len(variables["Paux_MW"]) == 3





def test_synthesize_artifact_from_point_eval() -> None:

    s = DesignSession()

    out = ui_evaluate(s.build_point_inputs(), origin="test")

    art = synthesize_from_point(out)

    assert art["verdict"] in ("FEASIBLE", "INFEASIBLE")

    assert isinstance(art.get("constraints"), list)





def test_fetch_systems_artifact_after_point_eval() -> None:

    s = DesignSession()

    out = ui_evaluate(s.build_point_inputs(), origin="test")

    set_point_evaluation(s, outputs=out, inputs=dict(s.inputs))

    art = fetch_systems_artifact(s)

    assert isinstance(art, dict)

    assert art.get("verdict") in ("FEASIBLE", "INFEASIBLE")
    assert art.get("source") == "point_designer_fallback"





def test_run_precheck_smoke() -> None:

    s = DesignSession()

    base = s.build_point_inputs()

    targets, variables = build_targets_and_variables(s, base)

    report = run_systems_precheck(

        base,

        targets,

        variables,

        n_random=2,

        seed=42,

    )

    assert hasattr(report, "ok")

    assert hasattr(report, "n_samples")

    assert int(report.n_samples) >= 1


def test_post_solve_authority_shows_v400_when_keys_present() -> None:
    import inspect

    from ui_nicegui.decks.systems_mode import post_solve_authority_ui as mod

    body = inspect.getsource(mod)
    assert "magnet_v400_summary" in body
    assert "PROXY" in body
    assert "Tritium / TBR" in body


