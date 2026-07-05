"""Systems Mode Newton target solve — frozen evaluator, canonical artifacts."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

from ui_nicegui.lib.pd_intent_policy import (
    classify_failed_constraints,
    constraint_policy_snapshot,
    design_intent_key,
    hard_constraint_names_for_intent,
)
from ui_nicegui.lib.systems_state_helpers import apply_input_overrides
from ui_nicegui.lib.systems_workflow_helpers import _get_evaluator


def _import_solvers():
    try:
        from src.solvers import DefaultTargetSolverBackend, SolverRequest, solve_request
    except ImportError:
        from solvers import DefaultTargetSolverBackend, SolverRequest, solve_request  # type: ignore
    return SolverRequest, DefaultTargetSolverBackend, solve_request


def _evaluate_constraints(outputs: dict) -> list:
    try:
        try:
            from constraints.constraints import evaluate_constraints
        except ImportError:
            from src.constraints.constraints import evaluate_constraints  # type: ignore
        return list(evaluate_constraints(outputs))
    except Exception:
        return []


def build_systems_solve_artifact(
    *,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    constraints_list: list,
    solver_meta: Optional[dict],
    baseline_inputs: Dict[str, Any],
    design_intent: str,
    solve_ok: bool,
) -> dict:
    try:
        try:
            from shams_io.run_artifact import build_run_artifact
        except ImportError:
            from src.shams_io.run_artifact import build_run_artifact  # type: ignore
        artifact = build_run_artifact(
            inputs=dict(inputs),
            outputs=dict(outputs),
            constraints=constraints_list,
            meta={"mode": "systems", "solve_ok": bool(solve_ok)},
            solver=solver_meta,
            baseline_inputs=dict(baseline_inputs),
        )
    except Exception:
        artifact = {
            "inputs": dict(inputs),
            "outputs": dict(outputs),
            "constraints": list(constraints_list),
            "solver": solver_meta,
            "baseline_inputs": dict(baseline_inputs),
        }

    artifact["source"] = "systems_solve"
    artifact["artifact_kind"] = "systems"
    if design_intent:
        artifact["design_intent"] = str(design_intent)

    failed_names = []
    for c in constraints_list:
        try:
            if not bool(getattr(c, "passed", True)) and str(getattr(c, "severity", "hard")).lower() == "hard":
                failed_names.append(str(getattr(c, "name", "")))
        except Exception:
            pass
    cls = classify_failed_constraints(failed_names, design_intent=design_intent)
    artifact["intent_feasibility_summary"] = {
        **constraint_policy_snapshot(design_intent),
        "blocking_feasible": len(cls.get("blocking", [])) == 0,
        "failed_blocking": cls.get("blocking", []),
        "failed_diagnostic": cls.get("diagnostic", []),
        "failed_ignored": cls.get("ignored", []),
        "note": "Feasibility under active Design Intent from Helm Console.",
    }
    try:
        try:
            from src.systems.schema import SCHEMA_VERSION as _v, freeze_contract as _fc
        except ImportError:
            from systems.schema import SCHEMA_VERSION as _v, freeze_contract as _fc  # type: ignore
        artifact.setdefault("schema_version", int(_v))
        artifact.setdefault("freeze_contract", _fc())
    except Exception:
        pass
    return artifact


def _make_solver_request(
    base,
    targets: Dict[str, float],
    variables: Dict[str, Tuple[float, float, float]],
    *,
    max_iter: int,
    tol: float,
    damping: float,
    block_solve: bool,
    trust_delta: Optional[float],
):
    SolverRequest, _, _ = _import_solvers()
    opts: dict = {"multistart": True, "restarts": 8, "cache_enabled": True, "cache_max": 1024}
    if block_solve:
        opts["block_solve"] = True
    if trust_delta is not None:
        opts["trust_delta"] = float(trust_delta)
    return SolverRequest(
        base=base,
        targets=dict(targets),
        variables=dict(variables),
        max_iter=int(max_iter),
        tol=float(tol),
        damping=float(damping),
        options=opts,
    )


def _run_continuation(
    base,
    targets: Dict[str, float],
    variables: Dict[str, Tuple[float, float, float]],
    *,
    cont_steps: int,
    max_iter: int,
    tol: float,
    damping: float,
    block_solve: bool,
    trust_delta: Optional[float],
) -> tuple[Any, Optional[str]]:
    """Ramp targets from current outputs to final targets."""
    _, DefaultTargetSolverBackend, solve_request = _import_solvers()
    ev = _get_evaluator()
    try:
        out0 = dict(ev.evaluate(base).out or {})
    except Exception:
        out0 = {}

    start_targets: Dict[str, float] = {}
    for k in targets:
        try:
            v = float(out0.get(k, float("nan")))
        except Exception:
            v = float("nan")
        if v == v and abs(v) != float("inf"):
            start_targets[k] = v

    base_stage = base
    steps = max(2, int(cont_steps))
    for s in range(1, steps):
        alpha = float(s) / float(steps)
        step_targets = {}
        for k, final in targets.items():
            if k in start_targets:
                step_targets[k] = float(start_targets[k] + alpha * (float(final) - float(start_targets[k])))
            else:
                step_targets[k] = float(final)
        req = _make_solver_request(
            base_stage,
            step_targets,
            variables,
            max_iter=max_iter,
            tol=tol,
            damping=damping,
            block_solve=block_solve,
            trust_delta=trust_delta,
        )
        res = solve_request(req, backend=DefaultTargetSolverBackend())
        if not res.ok:
            return base_stage, f"continuation_step_fail at alpha={alpha:.2f}: {res.message}"
        base_stage = res.inp
    return base_stage, None


def _run_feasibility_scout(
    base,
    variables: Dict[str, Tuple[float, float, float]],
    *,
    n_samples: int,
    n_refine: int,
    seed: int,
    design_intent: str,
):
    try:
        from src.systems.feasibility_completion import feasibility_scout
    except ImportError:
        from systems.feasibility_completion import feasibility_scout  # type: ignore

    hard = hard_constraint_names_for_intent(design_intent)
    ev = _get_evaluator()
    return feasibility_scout(
        base,
        variables,
        evaluator=ev,
        n_samples=int(n_samples),
        seed=int(seed),
        n_refine=int(n_refine),
        hard_constraint_names=hard if hard else None,
    )


def precheck_blocks_solve(precheck_report: Any, *, design_intent: str, require_precheck: bool) -> tuple[bool, str]:
    if not require_precheck or precheck_report is None:
        return False, ""
    ok = bool(getattr(precheck_report, "ok", precheck_report.get("ok") if isinstance(precheck_report, dict) else False))
    if ok:
        return False, ""
    if design_intent_key(design_intent) == "reactor":
        return True, "Precheck infeasible under reactor intent — adjust bounds/targets or use Recover before solve."
    return False, ""


def run_systems_solve(
    base,
    targets: Dict[str, float],
    variables: Dict[str, Tuple[float, float, float]],
    *,
    max_iter: int = 35,
    tol: float = 1e-3,
    damping: float = 0.6,
    block_solve: bool = False,
    design_intent: str = "",
    trust_delta: Optional[float] = None,
    do_continuation: bool = False,
    cont_steps: int = 10,
    scout_enabled: bool = False,
    scout_n_samples: int = 64,
    scout_n_refine: int = 20,
    scout_seed: int = 1337,
    input_overrides: Optional[Dict[str, float]] = None,
    precheck_report: Any = None,
    require_precheck: bool = True,
) -> dict:
    """Run constraint-target Newton solve with optional scout, continuation, precheck gate."""
    blocked, block_msg = precheck_blocks_solve(
        precheck_report, design_intent=design_intent, require_precheck=require_precheck
    )
    if blocked:
        return {
            "ok": False,
            "blocked": True,
            "message": block_msg,
            "artifact": None,
            "inp": None,
            "out": None,
            "iters": 0,
            "wall_s": 0.0,
        }

    base_for_solve = apply_input_overrides(base, input_overrides)
    scout_note = ""
    if scout_enabled:
        scout = _run_feasibility_scout(
            base_for_solve,
            variables,
            n_samples=scout_n_samples,
            n_refine=scout_n_refine,
            seed=scout_seed,
            design_intent=design_intent,
        )
        if scout.get("ok") and scout.get("best_inp") is not None:
            base_for_solve = scout["best_inp"]
            scout_note = "feasibility_scout_ok"
        else:
            scout_note = "feasibility_scout_no_feasible_start"

    if do_continuation and len(targets) > 0:
        base_for_solve, cont_err = _run_continuation(
            base_for_solve,
            targets,
            variables,
            cont_steps=cont_steps,
            max_iter=max_iter,
            tol=tol,
            damping=damping,
            block_solve=block_solve,
            trust_delta=trust_delta,
        )
        if cont_err:
            return {
                "ok": False,
                "blocked": False,
                "message": cont_err,
                "artifact": None,
                "inp": None,
                "out": None,
                "iters": 0,
                "wall_s": 0.0,
                "scout_note": scout_note,
            }

    _, DefaultTargetSolverBackend, solve_request = _import_solvers()
    req = _make_solver_request(
        base_for_solve,
        targets,
        variables,
        max_iter=max_iter,
        tol=tol,
        damping=damping,
        block_solve=block_solve,
        trust_delta=trust_delta,
    )
    t0 = time.perf_counter()
    res = solve_request(req, backend=DefaultTargetSolverBackend())
    wall_s = float(time.perf_counter() - t0)

    inp_sol = res.inp
    out_sol = dict(res.out or {})
    constraints_list = _evaluate_constraints(out_sol)
    solver_meta = {
        "message": res.message,
        "trace": res.trace or [],
        "ok": bool(res.ok),
        "scout_note": scout_note,
        "continuation": bool(do_continuation),
    }
    inputs_dict = inp_sol.to_dict() if hasattr(inp_sol, "to_dict") else dict(getattr(inp_sol, "__dict__", {}))
    baseline_dict = base.to_dict() if hasattr(base, "to_dict") else dict(getattr(base, "__dict__", {}))

    artifact = build_systems_solve_artifact(
        inputs=inputs_dict,
        outputs=out_sol,
        constraints_list=constraints_list,
        solver_meta=solver_meta,
        baseline_inputs=baseline_dict,
        design_intent=design_intent,
        solve_ok=bool(res.ok),
    )
    return {
        "ok": bool(res.ok),
        "blocked": False,
        "artifact": artifact,
        "inp": inp_sol,
        "out": out_sol,
        "iters": int(res.iters),
        "message": str(res.message or ""),
        "wall_s": wall_s,
        "scout_note": scout_note,
    }


def artifact_from_recovery_eval(
    base,
    rep: dict,
    *,
    design_intent: str = "",
) -> dict:
    """Build a proper artifact from recovery best_point via frozen evaluator."""
    from ui_nicegui.lib.systems_workflow_helpers import _build_inputs

    x = rep.get("best_point") if isinstance(rep.get("best_point"), dict) else {}
    if not x:
        return {
            "verdict": "INFEASIBLE",
            "source": "systems_recovery",
            "recovery": dict(rep),
            "design_intent": design_intent,
        }
    ev = _get_evaluator()
    inp = _build_inputs(base, x)
    res = ev.evaluate(inp)
    if not (res and res.ok and isinstance(res.out, dict)):
        return {
            "verdict": "INFEASIBLE",
            "source": "systems_recovery",
            "recovery": dict(rep),
            "best_point": dict(x),
            "design_intent": design_intent,
        }
    out = dict(res.out)
    constraints_list = _evaluate_constraints(out)
    inputs_dict = inp.to_dict() if hasattr(inp, "to_dict") else dict(getattr(inp, "__dict__", {}))
    baseline_dict = base.to_dict() if hasattr(base, "to_dict") else dict(getattr(base, "__dict__", {}))
    art = build_systems_solve_artifact(
        inputs=inputs_dict,
        outputs=out,
        constraints_list=constraints_list,
        solver_meta={"message": "recovery_eval", "ok": bool(rep.get("ok"))},
        baseline_inputs=baseline_dict,
        design_intent=design_intent,
        solve_ok=bool(rep.get("ok")),
    )
    art["source"] = "systems_recovery"
    art["recovery"] = dict(rep)
    art["best_point"] = dict(x)
    return art
