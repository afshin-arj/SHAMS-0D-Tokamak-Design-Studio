from __future__ import annotations

"""Solver adapter (PROCESS-inspired).

Provides a stable interface between SHAMS problems (targets + variables) and
concrete solver implementations. The default backend preserves SHAMS behaviour
while adding a deterministic robustness ladder (multistart seeding).
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Protocol, Optional, Any

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    try:
        from models.inputs import PointInputs  # type: ignore
    except Exception:
        from models.inputs import PointInputs  # type: ignore
from .constraint_solver import (
    solve_for_targets,
    solve_for_targets_multistart,
    solve_for_targets_continuation,
    SolveResult as ConstraintSolveResult,
)


@dataclass(frozen=True)
class SolverRequest:
    """Generic request for a constraint-targeting solve."""

    base: PointInputs
    targets: Dict[str, float]
    variables: Dict[str, Tuple[float, float, float]]
    max_iter: int = 35
    tol: float = 1e-3
    damping: float = 0.6
    options: Dict[str, Any] = None
    meta: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.options is None:
            object.__setattr__(self, "options", {})


class SolverBackend(Protocol):
    """Backend protocol for solving a SolverRequest."""

    name: str

    def solve(self, req: SolverRequest) -> ConstraintSolveResult: ...


class DefaultTargetSolverBackend:
    """Default backend that preserves existing SHAMS behaviour."""

    name = "default_target_solver"

    def solve(self, req: SolverRequest) -> ConstraintSolveResult:
        trust_delta = req.options.get("trust_delta", None)
        solver_backend = req.options.get("solver_backend", "hybrid_newton")
        cache_enabled = bool(req.options.get("cache_enabled", True))
        cache_max = int(req.options.get("cache_max", 256))
        use_continuation = bool(req.options.get("continuation", False))
        stages = req.options.get("continuation_stages", None)

        use_block = bool(req.options.get("block_solve", False))
        if use_block:
            # Block-ordered solve for numerical robustness (feasibility-first).
            # Stages are heuristic and only apply to provided targets/variables.
            from evaluator.core import Evaluator

            def _stage(name: str, tkeys: set[str], vkeys: set[str], stage_tol: float, stage_max_iter: int) -> ConstraintSolveResult:
                st_targets = {k: req.targets[k] for k in req.targets.keys() if k in tkeys}
                st_vars = {k: req.variables[k] for k in req.variables.keys() if k in vkeys}
                if not st_targets or not st_vars:
                    # Skip empty stage
                    return None
                if use_continuation:
                    return solve_for_targets_continuation(
                        req.base,
                        st_targets,
                        st_vars,
                        stages=stages,
                        max_iter=stage_max_iter,
                        tol=stage_tol,
                        damping=req.damping,
                        trust_delta=trust_delta,
                        solver_backend=solver_backend,
                        cache_enabled=cache_enabled,
                        cache_max=cache_max,
                    )
                return solve_for_targets(
                    req.base,
                    st_targets,
                    st_vars,
                    max_iter=stage_max_iter,
                    tol=stage_tol,
                    damping=req.damping,
                    trust_delta=trust_delta,
                        solver_backend=solver_backend,
                        cache_enabled=cache_enabled,
                        cache_max=cache_max,
                )

            # Heuristic grouping by target/variable names
            tgt_density = {k for k in req.targets if ("fG" in k or "ne" in k or "n" == k)}
            tgt_power = {k for k in req.targets if ("Paux" in k or "Pin" in k or "P_SOL" in k or "q_" in k or "power_balance" in k)}
            tgt_conf = {k for k in req.targets if ("H" in k or "tauE" in k or "Q" in k)}
            tgt_all = set(req.targets.keys())

            var_density = {k for k in req.variables if ("fG" in k or "ne" in k or "n" == k)}
            var_power = {k for k in req.variables if ("Paux" in k or "Pin" in k)}
            var_conf = {k for k in req.variables if ("Ip" in k or "Bt" in k or "confinement" in k)}
            var_all = set(req.variables.keys())

            stages_spec = [
                ("density", tgt_density, var_density),
                ("power", tgt_power, (var_power | var_density)),
                ("confinement", (tgt_conf | tgt_power), (var_conf | var_power | var_density)),
                ("full", tgt_all, var_all),
            ]

            best = None
            best_norm = float("inf")
            current_base = req.base
            full_trace = []
            for i, (nm, tk, vk) in enumerate(stages_spec, start=1):
                r = _stage(nm, tk, vk, stage_tol=float(req.tol) * (5.0 if nm != "full" else 1.0), stage_max_iter=max(12, int(req.max_iter // 2)))
                if r is None:
                    continue
                full_trace.append({"event": "block_stage", "stage": i, "name": nm, "ok": bool(r.ok), "message": str(r.message)})
                full_trace.extend(list(r.trace or []))
                try:
                    nrm = Evaluator.residual_norm(Evaluator.residuals(r.out, {k: req.targets[k] for k in tk if k in req.targets}))
                except Exception:
                    nrm = float("inf")
                if (r.ok and (best is None or not best.ok)) or (nrm <= best_norm):
                    best, best_norm = r, nrm
                current_base = r.inp

            if best is not None:
                # Ensure final solve is at least attempted on full set using the best current base.
                req2 = SolverRequest(base=best.inp, targets=req.targets, variables=req.variables,
                                     max_iter=req.max_iter, tol=req.tol, damping=req.damping, options=req.options, meta=req.meta)
                res_full = solve_for_targets(
                    req2.base, req2.targets, req2.variables,
                    max_iter=req2.max_iter, tol=req2.tol, damping=req2.damping, trust_delta=trust_delta
                )
                res_full.trace = (full_trace + [{"event": "block_stage", "stage": 99, "name": "final_full", "ok": bool(res_full.ok), "message": str(res_full.message)}] + list(res_full.trace or []))
                res = res_full
            else:
                res = None

        if (not use_block) or (res is None):
            # Primary: bounded damped-Newton
            if use_continuation:
                res = solve_for_targets_continuation(
                    req.base,
                    req.targets,
                    req.variables,
                    stages=stages,
                    max_iter=req.max_iter,
                    tol=req.tol,
                    damping=req.damping,
                    trust_delta=trust_delta,
                        solver_backend=solver_backend,
                        cache_enabled=cache_enabled,
                        cache_max=cache_max,
                )
            else:
                res = solve_for_targets(
                    req.base,
                    req.targets,
                    req.variables,
                    max_iter=req.max_iter,
                    tol=req.tol,
                    damping=req.damping,
                    trust_delta=trust_delta,
                        solver_backend=solver_backend,
                        cache_enabled=cache_enabled,
                        cache_max=cache_max,
                )

        # Robustness ladder: deterministic multistart if first attempt fails
        if (not res.ok) and bool(req.options.get("multistart", True)):
            res2 = solve_for_targets_multistart(
                req.base,
                req.targets,
                req.variables,
                max_iter=req.max_iter,
                tol=req.tol,
                damping=req.damping,
                trust_delta=trust_delta,
                        solver_backend=solver_backend,
                        cache_enabled=cache_enabled,
                        cache_max=cache_max,
                restarts=int(req.options.get("restarts", 8)),
            )
            try:
                from evaluator.core import Evaluator
                n1 = Evaluator.residual_norm(Evaluator.residuals(res.out, req.targets))
                n2 = Evaluator.residual_norm(Evaluator.residuals(res2.out, req.targets))
                if (res2.ok and not res.ok) or (n2 <= n1):
                    res = res2
            except Exception:
                if res2.ok:
                    res = res2

        return res


def solve(req: SolverRequest, backend: Optional[SolverBackend] = None) -> ConstraintSolveResult:
    """Solve a request using the selected backend (or default)."""
    b = backend or DefaultTargetSolverBackend()
    return b.solve(req)