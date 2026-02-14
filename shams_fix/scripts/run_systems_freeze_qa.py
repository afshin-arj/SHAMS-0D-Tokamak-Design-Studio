#!/usr/bin/env python
"""Freeze-readiness QA for Systems Mode.

Fast, non-UI script meant to run locally or in CI before declaring Systems Mode
"frozen". It runs a small matrix of presets × intents and exercises:

- feasibility precheck
- seeded recovery

It validates:
- outputs are JSON-serializable
- systems schema helpers upgrade/validate cleanly (schema_version=1)

Writes:
  artifacts/qa/system_mode_freeze_report.json

Usage:
  python scripts/run_systems_freeze_qa.py
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict


def _repo_bootstrap() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    src = repo_root / "src"
    if src.exists() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _to_jsonable(x: Any) -> Any:
    if x is None or isinstance(x, (bool, int, float, str)):
        return x
    if is_dataclass(x):
        return {k: _to_jsonable(v) for k, v in asdict(x).items()}
    if isinstance(x, dict):
        return {str(k): _to_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_to_jsonable(v) for v in x]
    # fallback: repr
    return str(x)


def main() -> int:
    _repo_bootstrap()

    report: Dict[str, Any] = {
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ok": True,
        "cases": [],
        "errors": [],
    }

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
            from systems.recovery import recover_feasible_near_seed
        except Exception:
            from src.systems.recovery import recover_feasible_near_seed  # type: ignore

        try:
            from systems.schema import upgrade_systems_artifact, validate_systems_artifact
        except Exception:
            from src.systems.schema import upgrade_systems_artifact, validate_systems_artifact  # type: ignore

        try:
            from models.reference_machines import reference_presets
        except Exception:
            from src.models.reference_machines import reference_presets  # type: ignore

        presets = reference_presets()
        # Keep the matrix small (freeze checks should be quick)
        preset_names = [
            name for name in ["ITER-inspired", "SPARC-inspired", "ARC-inspired", "HH170-inspired"] if name in presets
        ]
        if not preset_names:
            preset_names = list(presets.keys())[:2]

        intents = ["reactor", "research"]

        ev = Evaluator(cache_enabled=True, cache_max=2048)

        for pname in preset_names:
            base = presets[pname]
            for intent in intents:
                # Intent affects which constraints are treated as hard in UI; in core we pass explicit hard set
                # Keep this aligned with current policy: reactor => all hard; research => q95 only.
                hard_set = None if intent == "reactor" else {"q95"}

                # Minimal targets/vars for quick checks
                targets = {"Q_DT_eqv": 0.001}
                variables = {"Paux_MW": (float(getattr(base, "Paux_MW", 50.0)), 0.0, 200.0)}

                t0 = time.perf_counter()
                pre = run_precheck(
                    base,
                    targets,
                    variables,
                    include_random=True,
                    n_random=4,
                    seed=1234,
                    evaluator=ev,
                    hard_constraint_names=hard_set,
                )
                dt_pre = time.perf_counter() - t0

                # Seeded recovery (very small budget)
                t1 = time.perf_counter()
                rec = recover_feasible_near_seed(
                    base=base,
                    seed={"Paux_MW": float(getattr(base, "Paux_MW", 50.0))},
                    variables={"Paux_MW": {"lo": 0.0, "hi": 200.0}},
                    evaluator=ev,
                    hard_constraint_names=hard_set,
                    budget_evals=60,
                    rng_seed=1234,
                )
                dt_rec = time.perf_counter() - t1

                # Build a tiny synthetic systems artifact from the reports
                art = {
                    "schema_version": 1,
                    "artifact_kind": "systems",
                    "inputs_hash": getattr(base, "inputs_hash", None),
                    "preset": pname,
                    "intent_key": intent,
                    "precheck": _to_jsonable(getattr(pre, "__dict__", pre)),
                    "recovery": _to_jsonable(getattr(rec, "__dict__", rec)),
                    "timing": {"precheck_s": dt_pre, "recovery_s": dt_rec},
                }

                art = upgrade_systems_artifact(art)
                issues = validate_systems_artifact(art)

                # JSON-serializable check
                json.dumps(art, indent=2, sort_keys=True)

                case_ok = True
                if issues:
                    # Warnings are allowed, but mark case as "soft fail" for visibility
                    case_ok = False

                report["cases"].append(
                    {
                        "preset": pname,
                        "intent": intent,
                        "precheck_ok": bool(getattr(pre, "ok", False)),
                        "precheck_reason": str(getattr(pre, "reason", "")),
                        "recovery_ok": bool(getattr(rec, "ok", False)),
                        "recovery_reason": str(getattr(rec, "reason", "")),
                        "schema_warnings": issues,
                        "case_ok": case_ok,
                        "timing": {"precheck_s": dt_pre, "recovery_s": dt_rec},
                    }
                )

        # Overall ok if no hard errors
        report["ok"] = len(report["errors"]) == 0

    except Exception as e:
        report["ok"] = False
        report["errors"].append({"error": str(e), "traceback": traceback.format_exc()})

    out_dir = Path(__file__).resolve().parents[1] / "artifacts" / "qa"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "system_mode_freeze_report.json"
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print(f"SYSTEMS_FREEZE_QA: wrote {out_path}")
    if report["ok"]:
        print("SYSTEMS_FREEZE_QA: PASS")
        return 0
    print("SYSTEMS_FREEZE_QA: FAIL")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
