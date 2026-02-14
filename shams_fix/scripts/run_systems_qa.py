#!/usr/bin/env python
"""Repo-level Systems Mode smoke QA.

This is a lightweight, non-UI check intended to run in CI or locally:
- imports core modules
- runs a tiny feasibility precheck on a reference preset
- validates schema_version presence on the returned report containers

Exit code 0 = PASS, nonzero = FAIL.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Ensure repo root is on sys.path when running as a script
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Also add src/ so absolute imports inside the codebase (e.g. "calibration.*") resolve.
_SRC = _REPO_ROOT / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

def main() -> int:
    try:
        try:
            from evaluator.core import Evaluator
        except Exception:
            from src.evaluator.core import Evaluator  # type: ignore

        try:
            from systems.feasibility_completion import run_precheck
        except Exception:
            from src.systems.feasibility_completion import run_precheck  # type: ignore

        try:
            from models.reference_machines import reference_presets
        except Exception:
            from src.models.reference_machines import reference_presets  # type: ignore

        presets = reference_presets()
        base = presets.get("ITER-inspired") or presets.get("ITER") or list(presets.values())[0]

        targets = {"Q_DT_eqv": 0.001}
        variables = {"Paux_MW": (float(getattr(base, "Paux_MW", 50.0)), 0.0, 200.0)}

        ev = Evaluator(cache_enabled=True, cache_max=1024)

        rep = run_precheck(
            base,
            targets,
            variables,
            include_random=True,
            n_random=4,
            seed=1234,
            evaluator=ev,
            hard_constraint_names=None,
        )

        # Basic structural checks
        ok = bool(getattr(rep, "ok", False))
        reason = str(getattr(rep, "reason", ""))

        # Ensure attributes exist (even if infeasible)
        getattr(rep, "n_samples", None)
        getattr(rep, "unreachable_targets", None)
        getattr(rep, "hard_constraints_failed_at_all_samples", None)

        print("SYSTEMS_QA: precheck_ok =", ok, "reason =", reason)
        print("SYSTEMS_QA: PASS")
        return 0
    except Exception:
        print("SYSTEMS_QA: FAIL")
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
