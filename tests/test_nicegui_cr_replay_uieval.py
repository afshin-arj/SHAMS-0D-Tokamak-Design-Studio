"""Control Room replay must use NiceGUI ui_evaluate choke point."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_ui_replay_evaluate_calls_ui_evaluate_not_hot_ion() -> None:
    from ui_nicegui.lib.cr_provenance_helpers import _ui_replay_evaluate

    fake_out = {"Q_DT_eqv": 1.0, "H98": 1.0}
    fake_art = {
        "kind": "shams_run_artifact",
        "outputs": fake_out,
        "min_margin": 0.1,
        "dominant_constraint": "demo",
        "constraints": [],
        "metrics": {"Q_DT_eqv": 1.0},
        "meta": {},
    }
    fake_inp = MagicMock()
    fake_inp.to_dict.return_value = {"R0_m": 6.0}

    with patch("src.schema.inputs.PointInputs.from_dict", return_value=fake_inp), patch(
        "ui_nicegui.evaluate.ui_evaluate", return_value=fake_out
    ) as uev, patch(
        "constraints.constraints.evaluate_constraints", return_value=[]
    ), patch(
        "shams_io.run_artifact.build_run_artifact", return_value=dict(fake_art)
    ):
        art = _ui_replay_evaluate(inputs_dict={"R0_m": 6.0}, solver_meta={"label": "test"})

    assert uev.called
    assert uev.call_args.kwargs.get("origin") == "ControlRoom:Replay" or (
        len(uev.call_args.args) >= 1 and uev.call_args.kwargs.get("origin") == "ControlRoom:Replay"
    )
    # origin is keyword-only
    assert uev.call_args.kwargs["origin"] == "ControlRoom:Replay"
    assert art.get("meta", {}).get("evaluator") == "ui_evaluate"
    assert art.get("meta", {}).get("origin") == "ControlRoom:Replay"


def test_replay_check_passes_ui_evaluate_fn() -> None:
    import inspect

    from ui_nicegui.lib import cr_provenance_helpers as crp
    from tools import repro_lock_v166 as rl

    src = inspect.getsource(crp.replay_check)
    assert "evaluate_fn=_ui_replay_evaluate" in src
    assert "ui_evaluate" in inspect.getsource(crp._ui_replay_evaluate)
    sig = inspect.signature(rl.replay_check)
    assert "evaluate_fn" in sig.parameters


def test_vacuous_metrics_fail_replay() -> None:
    from tools.repro_lock_v166 import replay_check

    lock = {
        "kind": "shams_repro_lock",
        "payload": {
            "integrity": {"lock_sha256": "abc"},
            "frozen": {"inputs": {"R0_m": 6.0}, "assumptions": {}},
            "comparison": {"tolerances": {}},
            "expected": {
                "min_margin": None,
                "dominant_constraint": "",
                "constraints": [],
                "metrics": {"Q_DT_eqv": 10.0},
            },
        },
    }

    def _eval(*, inputs_dict=None, solver_meta=None, **_kw):
        return {
            "kind": "shams_run_artifact",
            "min_margin": None,
            "dominant_constraint": "",
            "constraints": [],
            "metrics": {"H98": 1.0},  # no overlap with expected Q_DT_eqv
            "meta": {"evaluator": "ui_evaluate"},
        }

    rep = replay_check(lock=lock, evaluate_fn=_eval)
    payload = rep["payload"]
    assert payload["ok"] is False
    assert payload["checks"]["metrics_vacuous"] is True
    assert payload["checks"]["metrics_ok"] is False
