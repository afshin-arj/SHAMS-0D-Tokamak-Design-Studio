from __future__ import annotations

import json
from pathlib import Path


def test_baseline_envelope_present_and_passes() -> None:
    """Baseline envelope is a regression guard.

    The baseline is generated from this codebase (v223.0). This test asserts:
      - the envelope is registered
      - evaluating the stored baseline inputs reproduces outputs within the stored bounds
      - invariant guardrails pass
    """

    import sys

    sys.path.insert(0, str(Path('src').resolve()))

    from validation.envelopes import default_envelopes
    from evaluator.core import Evaluator
    from models.inputs import PointInputs
    from validation.invariants import check_invariants

    envs = default_envelopes()
    assert 'ENV|BASELINE_v2230' in envs
    env = envs['ENV|BASELINE_v2230']

    base = json.loads(Path('src/validation/baselines/baseline_v2230.json').read_text(encoding='utf-8'))
    inp = PointInputs(**(base.get('inputs', {}) or {}))
    out = Evaluator(cache_enabled=False).evaluate(inp).out

    rep = env.check(out)
    assert rep, 'baseline envelope bounds empty'
    assert all(bool(v.get('ok')) for v in rep.values()), f"baseline envelope failed: {[k for k,v in rep.items() if not v.get('ok')] }"

    inv = check_invariants(out)
    assert bool(inv.get('ok')), f"invariant failures: {inv.get('failures')}"
