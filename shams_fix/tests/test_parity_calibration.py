from __future__ import annotations


def test_parity_calibration_runner_runs() -> None:
    # Calibration is reference-dependent; this test only checks the runner
    # executes and returns a structured payload.
    from tools.parity_calibrate import run_parity_calibration

    res = run_parity_calibration()
    assert isinstance(res, dict)
    assert "ok" in res
    assert "results" in res
