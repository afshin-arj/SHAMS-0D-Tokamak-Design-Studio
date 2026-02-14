from __future__ import annotations

def test_validation_envelope_check_smoke():
    from validation.envelopes import default_envelopes
    from validation.checks import check_point_against_envelope

    envs = default_envelopes()
    assert isinstance(envs, dict)
    assert len(envs) >= 1
    env = next(iter(envs.values()))
    outputs = {k: 0.0 for k in env.bounds.keys()}
    res = check_point_against_envelope(outputs, env)
    assert res is not None
