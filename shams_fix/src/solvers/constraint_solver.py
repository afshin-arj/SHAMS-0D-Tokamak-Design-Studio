from __future__ import annotations

"""Generic bounded vector solver for PROCESS-like constraint targeting.

This solver is intentionally dependency-light (no SciPy) so it works out of the
box on Windows. It uses a damped Newton method with finite-difference Jacobian
and simple bound clamping.

The key API is `solve_for_targets`, which adjusts a small set of iteration
variables (e.g., Ip_MA, fG) to match numeric targets (e.g., H98, Q_DT_eqv).

It does NOT attempt to replicate PROCESS's full VMCON behaviour; rather it gives
SHAMS a PROCESS-like *workflow primitive*.
"""

from dataclasses import dataclass
from .report import SolveReport
from .scaling import default_residual_scaling, default_variable_scaling, scale_bounds
from typing import Dict, Iterable, Iterator, List, Tuple
import math

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    try:
        from models.inputs import PointInputs  # type: ignore
    except Exception:
        from models.inputs import PointInputs  # type: ignore
from evaluator.core import Evaluator


@dataclass
class SolveResult:
    inp: PointInputs
    out: Dict[str, float]
    ok: bool
    iters: int
    message: str = ""
    # Full solver trace (JSON-serializable) for scientific auditability.
    trace: list = None
    # Standard solve report for UI/artifacts.
    report: dict | None = None
    # Optional diagnostic corner evaluations.
    corners: list | None = None




def _mk_report(*, backend: str, status: str, message: str, iters: int, trace: list, out: Dict[str, float], targets: Dict[str, float], var_keys: List[str], x: List[float], bounds: List[tuple], corners: list | None = None, scaling: dict | None = None) -> dict:
    rep = SolveReport(
        backend=backend,
        status=status,
        message=message,
        n_iter=iters,
        trace=trace or [],
        best_achieved={k: float(out.get(k, float("nan"))) for k in targets.keys()},
        target_errors={k: float(out.get(k, float("nan")) - float(t)) for k, t in targets.items()},
    )
    # active bounds
    ab = {}
    for i,k in enumerate(var_keys):
        lo,hi = bounds[i]
        if abs(x[i]-lo) <= 1e-12: ab[k]="lo"
        elif abs(x[i]-hi) <= 1e-12: ab[k]="hi"
        else: ab[k]=""
    rep.active_bounds = ab
    rep.corners = corners
    if scaling:
        rep.scaling = scaling
    # crude residual norm (L2 of target errors)
    try:
        import math
        rep.residual_norm = float(math.sqrt(sum((rep.target_errors[k])**2 for k in rep.target_errors)))
    except Exception:
        rep.residual_norm = float("nan")
    return rep.to_dict()

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _make_inp(base: PointInputs, updates: Dict[str, float]) -> PointInputs:
    return base.__class__(**{**base.__dict__, **updates})


def solve_for_targets(
    base: PointInputs,
    targets: Dict[str, float],
    variables: Dict[str, Tuple[float, float, float]],
    *,
    max_iter: int = 30,
    tol: float = 1e-3,
    damping: float = 0.6,
    trust_delta: float | None = None,
    solver_backend: str = "hybrid_newton",
    cache_enabled: bool = True,
    cache_max: int = 256,
) -> SolveResult:
    """Solve for iteration variables so that selected outputs hit targets.

    Parameters
    ----------
    base:
        Base PointInputs.
    targets:
        Mapping from output key -> target value. Example:
          {"H98": 1.0, "Q_DT_eqv": 10.0}
    variables:
        Mapping from variable name -> (x0, lo, hi). Example:
          {"Ip_MA": (8.0, 4.0, 14.0), "fG": (0.8, 0.1, 1.2)}
    """

    out_keys = list(targets.keys())
    var_keys = list(variables.keys())
    m = len(out_keys)
    n = len(var_keys)
    evaluator = Evaluator()

    # Iteration trace for auditability (must exist before any telemetry uses it)
    trace: List[dict] = []

    # Early exit: targets and variables must have same dimension
    if m != n:
        base_eval = evaluator.evaluate(base)
        try:
            trace.append({"event": "cache_stats", "cache": evaluator.cache_stats(), "solver_backend": str(solver_backend)})
        except Exception:
            pass
        return SolveResult(
            base,
            base_eval.out,
            False,
            0,
            "targets and variables must have same dimension",
            trace=trace,
            report=_mk_report(
                backend="bounded_newton_fd",
                status="failed",
                message="targets and variables must have same dimension",
                iters=0,
                trace=trace,
                out=base_eval.out,
                targets=targets,
                var_keys=var_keys,
                x=[variables[k][0] for k in var_keys],
                bounds=[(variables[k][1], variables[k][2]) for k in var_keys],
            ),
        )

    # Telemetry only (no effect on results)
    try:
        trace.append({"event": "cache_stats", "cache": evaluator.cache_stats(), "solver_backend": str(solver_backend)})
    except Exception:
        pass

    # --- Scaling (PROCESS-inspired) ---
    x = [float(variables[k][0]) for k in var_keys]
    bounds = [(float(variables[k][1]), float(variables[k][2])) for k in var_keys]

    x0_map = {k: float(variables[k][0]) for k in var_keys}
    var_scaling = default_variable_scaling(x0_map)
    res_scaling = default_residual_scaling(targets)
    x_scales = [float(var_scaling.scale_by_name.get(k, 1.0)) for k in var_keys]
    b_scaled = scale_bounds(bounds, x_scales)
    scaling_dict = {
        "variables": {k: float(var_scaling.scale_by_name.get(k, 1.0)) for k in var_keys},
        "residuals": {k: float(res_scaling.scale_by_name.get(k, 1.0)) for k in targets.keys()},
    }

    # --- Trust-region step control (PROCESS-inspired numerics; SHAMS-native) ---
    # Operates in *scaled* variable space to improve conditioning.
    # Defaults are permissive to preserve prior behaviour.
    delta = float(trust_delta) if trust_delta is not None else 5.0  # max |dx_scaled| allowed
    delta_min = 1e-6
    delta_max = 50.0

    def _apply_trust_region(dx_vec: List[float], delta_now: float) -> Tuple[List[float], float, float]:
        try:
            maxabs = float(max(abs(float(v)) for v in dx_vec)) if dx_vec else 0.0
        except Exception:
            maxabs = 0.0
        if (not math.isfinite(maxabs)) or maxabs <= 0.0 or maxabs <= delta_now:
            return list(dx_vec), 1.0, maxabs
        s = float(delta_now) / maxabs
        return [float(s) * float(v) for v in dx_vec], float(s), maxabs


    def eval_out(xvec_scaled: List[float]) -> Dict[str, float]:
        # xvec_scaled is dimensionless; convert to physical and clamp.
        upd = {}
        for i, k in enumerate(var_keys):
            xv = float(xvec_scaled[i]) * x_scales[i]
            upd[k] = _clamp(xv, bounds[i][0], bounds[i][1])
        return evaluator.evaluate(_make_inp(base, upd)).out

    # work in scaled variables for conditioning
    x_s = [x[i] / x_scales[i] if x_scales[i] != 0 else x[i] for i in range(n)]
    out = eval_out(x_s)
    trace.append({"iter": 0, "x": {var_keys[i]: float(x_s[i] * x_scales[i]) for i in range(n)}, "out": {k: float(out.get(k, float('nan'))) for k in out_keys}})
    for it in range(max_iter):
        r = []
        ok_fin = True
        for key in out_keys:
            val = float(out.get(key, float("nan")))
            tgt = float(targets[key])
            ri = (val - tgt) / float(res_scaling.scale_by_name.get(key, 1.0) or 1.0)
            r.append(ri)
            if not math.isfinite(ri) or abs(ri) > tol:
                ok_fin = False

        trace.append({
            "iter": int(it),
            "x": {var_keys[i]: float(x_s[i] * x_scales[i]) for i in range(n)},
            "residuals_scaled": {k: float(r[i]) for i, k in enumerate(out_keys)},
            "out": {k: float(out.get(k, float('nan'))) for k in out_keys},
        })
        if ok_fin:
            inp = _make_inp(base, {k: _clamp(x_s[i] * x_scales[i], *bounds[i]) for i, k in enumerate(var_keys)})
            return SolveResult(inp, out, True, it, "converged", trace=trace, report=_mk_report(backend="bounded_newton_scaled", status="success", message="converged", iters=it, trace=trace, out=out, targets=targets, var_keys=var_keys, x=[x_s[i]*x_scales[i] for i in range(n)], bounds=bounds, scaling=scaling_dict))

        # Jacobian J (m x n): hybrid analytic/FD via Evaluator when available.
        # Note: Evaluator.jacobian_targets already uses analytic partials when registered and
        # falls back to finite-difference for missing entries.
        try:
            inp_cur = _make_inp(base, {k: _clamp(x_s[i] * x_scales[i], *bounds[i]) for i, k in enumerate(var_keys)})
            J_phys = evaluator.jacobian_targets(inp_cur, targets=out_keys, variables=var_keys)
        except Exception:
            # Local finite-difference fallback (physical units)
            J_phys = [[0.0 for _ in range(n)] for __ in range(m)]
            for j in range(n):
                x_phys = float(x_s[j]) * float(x_scales[j])
                step_phys = max(1e-6, 0.02 * abs(x_phys) if x_phys != 0 else 0.02)
                step_s = step_phys / float(x_scales[j]) if float(x_scales[j]) != 0 else step_phys
                x2 = list(x_s)
                x2[j] = _clamp(x2[j] + step_s, b_scaled[j][0], b_scaled[j][1])
                o2 = eval_out(x2)
                for i, key in enumerate(out_keys):
                    v0 = float(out.get(key, float("nan")))
                    v1 = float(o2.get(key, float("nan")))
                    if not (math.isfinite(v0) and math.isfinite(v1)):
                        J_phys[i][j] = 0.0
                    else:
                        J_phys[i][j] = (v1 - v0) / max(step_phys, 1e-12)

        # Convert Jacobian to scaled system: dr_scaled/dx_scaled
        J = [[0.0 for _ in range(n)] for __ in range(m)]
        for i, key in enumerate(out_keys):
            sr = float(res_scaling.scale_by_name.get(key, 1.0) or 1.0)
            for j in range(n):
                J[i][j] = float(J_phys[i][j]) * float(x_scales[j]) / sr

        
        # --- v76: solver backend selection (auditably opt-in) ---
        backend = str(solver_backend or "hybrid_newton").strip().lower()
        if backend not in ("hybrid_newton", "broyden"):
            backend = "hybrid_newton"

        if backend == "broyden":
            if not hasattr(evaluator, "_broyden_state"):
                evaluator._broyden_state = {"J": None, "x": None, "r": None}
            stt = evaluator._broyden_state
            if stt.get("J") is None:
                stt["J"] = [row[:] for row in J]
                stt["x"] = list(x_s)
                stt["r"] = list(r)
                step_method_prefix = "broyden_init"
            else:
                try:
                    dx_prev = [float(x_s[i] - float(stt["x"][i])) for i in range(n)]
                    dr_prev = [float(r[i] - float(stt["r"][i])) for i in range(m)]
                    denom = sum(float(dx_prev[i]) * float(dx_prev[i]) for i in range(n))
                    if denom > 1e-18:
                        Jdx = [sum(float(stt["J"][ii][jj]) * float(dx_prev[jj]) for jj in range(n)) for ii in range(m)]
                        u = [float(dr_prev[ii] - float(Jdx[ii])) for ii in range(m)]
                        for ii in range(m):
                            for jj in range(n):
                                stt["J"][ii][jj] = float(stt["J"][ii][jj]) + float(u[ii]) * float(dx_prev[jj]) / denom
                        step_method_prefix = "broyden_update"
                    else:
                        step_method_prefix = "broyden_skip_small_dx"
                except Exception:
                    step_method_prefix = "broyden_update_failed"
                stt["x"] = list(x_s)
                stt["r"] = list(r)
            J = [row[:] for row in stt["J"]]
        else:
            step_method_prefix = "newton"
# Solve J dx = -r (2x2 explicit, else fallback to gradient step)
        dx = [0.0 for _ in range(n)]
        step_method = "none"
        step_method_prefix = locals().get("step_method_prefix", "newton")
        jac_det = None
        if n == 1:
            denom = float(J[0][0])
            jac_det = denom
            if math.isfinite(denom) and abs(denom) > 1e-12:
                dx[0] = -r[0] / denom
                step_method = "newton1"
            else:
                dx[0] = -0.1 * r[0] if math.isfinite(r[0]) else 0.0
                step_method = "fallback_grad_singular"
        elif n == 2:
            a, b = float(J[0][0]), float(J[0][1])
            c, d = float(J[1][0]), float(J[1][1])
            det = a * d - b * c
            jac_det = float(det) if math.isfinite(det) else None
            if math.isfinite(det) and abs(det) > 1e-12:
                dx[0] = (-r[0] * d + r[1] * b) / det
                dx[1] = (-a * r[1] + c * r[0]) / det
                step_method = "newton2"
            else:
                # singular/ill-conditioned Jacobian: take a conservative descent-like step
                dx[0] = -0.1 * r[0] if math.isfinite(r[0]) else 0.0
                dx[1] = -0.1 * r[1] if math.isfinite(r[1]) else 0.0
                step_method = "fallback_grad_singular"
        else:
            # fallback: small step opposite residual magnitude
            for j in range(n):
                dx[j] = -0.1 * r[j] if math.isfinite(r[j]) else 0.0
            step_method = "fallback_grad_nd"

        # Trust-region clip in scaled space (prevents huge jumps even when bounds allow it).
        dx_clipped, trust_scale, dx_maxabs = _apply_trust_region(dx, delta)
        if trust_scale != 1.0:
            dx = dx_clipped
        trace.append({
            "event": "trust_region",
            "iter": int(it),
            "delta": float(delta),
            "dx_maxabs": float(dx_maxabs) if math.isfinite(dx_maxabs) else None,
            "trust_scale": float(trust_scale),
        })
        trace.append({
            "event": "step",
            "iter": int(it),
            "jac_det": float(jac_det) if jac_det is not None else None,
            "step_method": str(step_method),
            "dx_scaled": {var_keys[j]: float(dx[j]) for j in range(n)},
        })

        # Apply damped update in scaled space + simple backtracking line-search
        # (reduces brittle behaviour when finite-difference Jacobians are noisy).
        def _rnorm(out_dict: Dict[str, float]) -> float:
            rr = []
            for key in out_keys:
                val = float(out_dict.get(key, float("nan")))
                tgt = float(targets[key])
                ri = (val - tgt) / float(res_scaling.scale_by_name.get(key, 1.0) or 1.0)
                rr.append(ri)
            try:
                return float(math.sqrt(sum((ri * ri) for ri in rr)))
            except Exception:
                return float("inf")

        r0 = _rnorm(out)
        if not math.isfinite(r0):
            inp = _make_inp(base, {k: _clamp(x_s[i] * x_scales[i], *bounds[i]) for i, k in enumerate(var_keys)})
            return SolveResult(inp, out, False, it, "nonfinite_residual", trace=trace, report=_mk_report(backend="bounded_newton_scaled", status="failed", message="nonfinite_residual", iters=it, trace=trace, out=out, targets=targets, var_keys=var_keys, x=[x_s[i]*x_scales[i] for i in range(n)], bounds=bounds, scaling=scaling_dict))

        step = float(damping)
        best_x = list(x_s)
        best_out = out
        best_r = r0
        improved = False
        ls_used = 0

        # up to 8 backtracking attempts
        for _ls in range(8):
            ls_used = _ls + 1
            x_try = [0.0 for _ in range(n)]
            for j in range(n):
                x_try[j] = _clamp(x_s[j] + step * dx[j], b_scaled[j][0], b_scaled[j][1])
            out_try = eval_out(x_try)
            r_try = _rnorm(out_try)
            if math.isfinite(r_try) and r_try <= best_r:
                best_x, best_out, best_r = x_try, out_try, r_try
                improved = (r_try < r0 * (1.0 - 1e-9))
                break
            step *= 0.5

        trace.append({
            "event": "linesearch",
            "iter": int(it),
            "r0": float(r0),
            "r_best": float(best_r),
            "step_final": float(step),
            "n_tries": int(ls_used),
            "improved": bool(improved),
        })

        # Update trust-region radius based on line-search outcome (non-invasive).
        if improved and ls_used <= 2 and step >= float(damping) * 0.99:
            delta = min(delta_max, max(delta, 1.0) * 1.5)
        elif (not improved) and ls_used >= 4:
            delta = max(delta_min, delta * 0.5)
        # If we cannot make progress, exit early with an explicit diagnostic.
        if (not improved) and step < 1e-6:
            inp = _make_inp(base, {k: _clamp(x_s[i] * x_scales[i], *bounds[i]) for i, k in enumerate(var_keys)})
            return SolveResult(inp, out, False, it, "no_descent", trace=trace, report=_mk_report(backend="bounded_newton_scaled", status="failed", message="no_descent", iters=it, trace=trace, out=out, targets=targets, var_keys=var_keys, x=[x_s[i]*x_scales[i] for i in range(n)], bounds=bounds, scaling=scaling_dict))

        x_s = best_x
        out = best_out

    inp = _make_inp(base, {k: _clamp(x_s[i] * x_scales[i], *bounds[i]) for i, k in enumerate(var_keys)})
    return SolveResult(inp, out, False, max_iter, "max_iter", trace=trace, report=_mk_report(backend="bounded_newton_scaled", status="failed", message="max_iter", iters=max_iter, trace=trace, out=out, targets=targets, var_keys=var_keys, x=[x_s[i]*x_scales[i] for i in range(n)], bounds=bounds, scaling=scaling_dict))


def solve_for_targets_stream(
    base: PointInputs,
    targets: Dict[str, float],
    variables: Dict[str, Tuple[float, float, float]],
    *,
    max_iter: int = 30,
    tol: float = 1e-3,
    damping: float = 0.6,
    trust_delta: float | None = None,
    cache_enabled: bool = True,
    cache_max: int = 256,
    solver_backend: str = "hybrid_newton",
) -> Iterator[Dict[str, float]]:
    """Streaming variant for UI: yields per-iteration diagnostics.

    This function mirrors `solve_for_targets` but yields lightweight rows for UI.
    It keeps backward compatibility (same fields as before) and adds optional
    diagnostics events (jac_det / step_method / line-search).
    """
    out_keys = list(targets.keys())
    var_keys = list(variables.keys())
    m = len(out_keys)
    n = len(var_keys)
    if m != n:
        # Keep UI streaming safe: mirror solve_for_targets() behavior (no crash on mismatch).
        yield {"event": "fail", "reason": "mismatch_targets_variables", "m": float(m), "n": float(n)}
        return
    x = [float(variables[k][0]) for k in var_keys]
    bounds = [(float(variables[k][1]), float(variables[k][2])) for k in var_keys]

    # scaling for comparable residual magnitudes
    res_scaling = default_residual_scaling(targets)
    evaluator = Evaluator(cache_enabled=bool(cache_enabled), cache_max=int(cache_max))

    # Trust-region (streaming): clips large dx steps to reduce divergence.
    delta = float(trust_delta) if trust_delta is not None else 5.0
    delta_min = 1e-6
    delta_max = 50.0

    def _apply_trust_region_stream(dx_vec: List[float], delta_now: float) -> Tuple[List[float], float, float]:
        try:
            maxabs = float(max(abs(float(v)) for v in dx_vec)) if dx_vec else 0.0
        except Exception:
            maxabs = 0.0
        if (not math.isfinite(maxabs)) or maxabs <= 0.0 or maxabs <= delta_now:
            return list(dx_vec), 1.0, maxabs
        s = float(delta_now) / maxabs
        return [float(s) * float(v) for v in dx_vec], float(s), maxabs


    def eval_out(xvec: List[float]) -> Dict[str, float]:
        upd = {k: _clamp(v, bounds[i][0], bounds[i][1]) for i, (k, v) in enumerate(zip(var_keys, xvec))}
        return evaluator.evaluate(_make_inp(base, upd)).out

    def rnorm(out_dict: Dict[str, float]) -> float:
        rr = []
        for key in out_keys:
            val = float(out_dict.get(key, float("nan")))
            tgt = float(targets[key])
            sr = float(res_scaling.scale_by_name.get(key, 1.0) or 1.0)
            rr.append((val - tgt) / sr)
        try:
            return float(math.sqrt(sum((ri * ri) for ri in rr)))
        except Exception:
            return float("inf")

    out = eval_out(x)
    for it in range(max_iter):
        row: Dict[str, float] = {"event": "iter", "it": float(it)}
        for j, k in enumerate(var_keys):
            row[k] = float(x[j])
        for key in out_keys:
            row[key] = float(out.get(key, float("nan")))
            row[f"res_{key}"] = row[key] - float(targets[key])
        yield row

        # check
        if all(math.isfinite(row[f"res_{key}"]) and abs(row[f"res_{key}"]) < tol for key in out_keys):
            yield {"event": "done", "it": float(it)}
            return

        # Jacobian (scaled residuals / physical vars)
        m, n = len(out_keys), len(var_keys)
        J = [[0.0 for _ in range(n)] for __ in range(m)]
        for j in range(n):
            step = max(1e-6, 0.02 * abs(x[j]) if x[j] != 0 else 0.02)
            x2 = list(x)
            x2[j] = _clamp(x2[j] + step, bounds[j][0], bounds[j][1])
            o2 = eval_out(x2)
            for i, key in enumerate(out_keys):
                v0 = float(out.get(key, float("nan")))
                v1 = float(o2.get(key, float("nan")))
                if math.isfinite(v0) and math.isfinite(v1):
                    sr = float(res_scaling.scale_by_name.get(key, 1.0) or 1.0)
                    J[i][j] = ((v1 - v0) / max(step, 1e-12)) / sr

        # solve (2x2 explicit, else fallback)
        r = [
            (float(out.get(k, float("nan"))) - float(targets[k]))
            / float(res_scaling.scale_by_name.get(k, 1.0) or 1.0)
            for k in out_keys
        ]
        dx = [0.0 for _ in range(n)]
        step_method = "none"
        jac_det = None
        if n == 1:
            denom = float(J[0][0])
            jac_det = denom
            if math.isfinite(denom) and abs(denom) > 1e-12:
                dx[0] = -r[0] / denom
                step_method = "newton1"
            else:
                dx[0] = -0.1 * r[0] if math.isfinite(r[0]) else 0.0
                step_method = "fallback_grad_singular"
        elif n == 2:
            a, b = float(J[0][0]), float(J[0][1])
            c, d = float(J[1][0]), float(J[1][1])
            det = a * d - b * c
            jac_det = float(det) if math.isfinite(det) else None
            if math.isfinite(det) and abs(det) > 1e-12:
                dx[0] = (-r[0] * d + r[1] * b) / det
                dx[1] = (-a * r[1] + c * r[0]) / det
                step_method = "newton2"
            else:
                dx[0] = -0.1 * r[0] if math.isfinite(r[0]) else 0.0
                dx[1] = -0.1 * r[1] if math.isfinite(r[1]) else 0.0
                step_method = "fallback_grad_singular"
        else:
            for j in range(n):
                dx[j] = -0.1 * r[j] if math.isfinite(r[j]) else 0.0
            step_method = "fallback_grad_nd"

        dx_clipped, trust_scale, dx_maxabs = _apply_trust_region_stream(dx, delta)
        if trust_scale != 1.0:
            dx = dx_clipped
        yield {
            "event": "trust_region",
            "it": float(it),
            "delta": float(delta),
            "dx_maxabs": float(dx_maxabs) if math.isfinite(dx_maxabs) else float("nan"),
            "trust_scale": float(trust_scale),
        }
        yield {
            "event": "step",
            "it": float(it),
            "jac_det": float(jac_det) if jac_det is not None else float("nan"),
            "step_method": str(step_method),
        }

        # backtracking line-search
        r0 = rnorm(out)
        step = float(damping)
        best_x = list(x)
        best_out = out
        best_r = r0
        improved = False
        ls_used = 0

        for _ls in range(8):
            ls_used = _ls + 1
            x_try = [0.0 for _ in range(n)]
            for j in range(n):
                x_try[j] = _clamp(x[j] + step * dx[j], bounds[j][0], bounds[j][1])
            out_try = eval_out(x_try)
            r_try = rnorm(out_try)
            if math.isfinite(r_try) and r_try <= best_r:
                best_x, best_out, best_r = x_try, out_try, r_try
                improved = (r_try < r0 * (1.0 - 1e-9))
                break
            step *= 0.5

        yield {
            "event": "linesearch",
            "it": float(it),
            "r0": float(r0),
            "r_best": float(best_r),
            "step_final": float(step),
            "n_tries": float(ls_used),
            "improved": float(1.0 if improved else 0.0),
        }

        if improved and ls_used <= 2 and step >= float(damping) * 0.99:
            delta = min(delta_max, max(delta, 1.0) * 1.5)
        elif (not improved) and ls_used >= 4:
            delta = max(delta_min, delta * 0.5)

        if (not improved) and step < 1e-6:
            yield {"event": "fail", "reason": "no_descent", "it": float(it)}
            return

        x = best_x
        out = best_out

    yield {"event": "fail", "reason": "max_iter", "it": float(it), "max_iter": float(max_iter)}
def solve_for_targets_multistart(
    base: PointInputs,
    targets: Dict[str, float],
    variables: Dict[str, Tuple[float, float, float]],
    *,
    max_iter: int = 40,
    tol: float = 1e-3,
    damping: float = 0.7,
    trust_delta: float | None = None,
    restarts: int = 8,
    solver_backend: str | None = None,
) -> SolveResult:
    '''Try multiple starting points within bounds and return the best result.

    Deterministic robustness layer: seeds the bounded Newton solver with a small
    set of candidate initial guesses (x0, midpoint, corners for 2D).
    '''
    out_keys = list(targets.keys())
    var_keys = list(variables.keys())
    m = len(out_keys)
    n = len(var_keys)
    evaluator = Evaluator()

    def residual_norm_for_out(out: Dict[str, float]) -> float:
        res = Evaluator.residuals(out, targets)
        return Evaluator.residual_norm(res)

    bounds = [(float(variables[k][1]), float(variables[k][2])) for k in var_keys]
    x0 = [float(variables[k][0]) for k in var_keys]
    mid = [0.5 * (lo + hi) for lo, hi in bounds]

    candidates = [x0, mid]

    if n == 2:
        (lo0, hi0), (lo1, hi1) = bounds
        candidates += [
            [lo0, lo1],
            [lo0, hi1],
            [hi0, lo1],
            [hi0, hi1],
            [0.25 * lo0 + 0.75 * hi0, 0.75 * lo1 + 0.25 * hi1],
            [0.75 * lo0 + 0.25 * hi0, 0.25 * lo1 + 0.75 * hi1],
        ]
    else:
        for k in range(1, min(restarts, 5)):
            frac = k / float(min(restarts, 5))
            candidates.append([lo + frac * (hi - lo) for (lo, hi) in bounds])

    base_eval = evaluator.evaluate(base).out
    best = SolveResult(base, base_eval, False, 0, "init", trace=[])
    best_norm = residual_norm_for_out(base_eval)

    for cand in candidates[: max(2, restarts)]:
        vars2 = {k: (float(cand[i]), variables[k][1], variables[k][2]) for i, k in enumerate(var_keys)}
        res = solve_for_targets(base, targets, vars2, max_iter=max_iter, tol=tol, damping=damping, solver_backend=solver_backend)
        norm = residual_norm_for_out(res.out)
        if res.ok and norm <= best_norm:
            best, best_norm = res, norm
            if best_norm <= tol:
                break
        elif (not res.ok) and norm < best_norm:
            best, best_norm = res, norm

    if best.ok:
        best.msg = "converged (multistart)"
    else:
        best.msg = f"{best.msg} (best of multistart, norm={best_norm:.3g})"
    return best


def solve_for_targets_continuation(
    base: PointInputs,
    targets: Dict[str, float],
    variables: Dict[str, Tuple[float, float, float]],
    *,
    stages: list[dict] | None = None,
    max_iter: int = 35,
    tol: float = 1e-3,
    damping: float = 0.6,
    trust_delta: float | None = None,
    solver_backend: str = "hybrid_newton",
) -> SolveResult:
    """Feasibility-first continuation ladder (homotopy-style).

    This is an opt-in robustness tool. It runs a sequence of solves, each using the
    previous stage's solution as the next initial guess, typically tightening tolerances
    or step controls.

    Defaults preserve behavior: if stages is None, a simple tol ladder is used.
    """
    ladder = stages if stages is not None else [
        {"tol": 1e-1},
        {"tol": 1e-2},
        {"tol": float(tol)},
    ]

    cur_base = base
    last: SolveResult | None = None
    for idx, st in enumerate(ladder):
        st_tol = float(st.get("tol", tol))
        st_damp = float(st.get("damping", damping))
        st_trust = st.get("trust_delta", trust_delta)

        res = solve_for_targets(
            cur_base,
            targets,
            variables,
            max_iter=int(st.get("max_iter", max_iter)),
            tol=st_tol,
            damping=st_damp,
            trust_delta=st_trust,
        )
        # add explicit stage provenance (additive)
        try:
            res.trace.append({
                "event": "continuation_stage",
                "stage": int(idx),
                "tol": float(st_tol),
                "damping": float(st_damp),
                "trust_delta": float(st_trust) if st_trust is not None else None,
                "ok": bool(res.ok),
                "msg": str(res.msg),
            })
        except Exception:
            pass

        last = res
        # update base for next stage using solved variables only
        try:
            d = cur_base.to_dict()
            for k in variables.keys():
                if k in res.x and res.x[k] == res.x[k]:
                    d[k] = float(res.x[k])
            cur_base = PointInputs.from_dict(d)
        except Exception:
            cur_base = cur_base

        if not res.ok:
            # stop early: continuation cannot recover if a stage fails to make progress
            break

    assert last is not None
    if last.ok:
        last.msg = "converged (continuation)"
    else:
        last.msg = f"{last.msg} (continuation)"
    return last


def evaluate_targets_at_corners(
    base: PointInputs,
    targets: Dict[str, float],
    var0: Tuple[str, float, float],
    var1: Tuple[str, float, float],
) -> list[dict]:
    '''Evaluate achieved targets at the four bound corners (var0, var1).'''
    evaluator = Evaluator()
    k0, lo0, hi0 = var0
    k1, lo1, hi1 = var1
    corners = [
        ("lo,lo", lo0, lo1),
        ("lo,hi", lo0, hi1),
        ("hi,lo", hi0, lo1),
        ("hi,hi", hi0, hi1),
    ]
    rows: list[dict] = []
    for name, v0, v1 in corners:
        out = evaluator.evaluate_point(base, {k0: float(v0), k1: float(v1)}).out
        res = Evaluator.residuals(out, targets)
        row = {
            "corner": name,
            k0: float(v0),
            k1: float(v1),
            "res_norm": float(Evaluator.residual_norm(res)),
        }
        for k in targets.keys():
            row[f"ach_{k}"] = float(out.get(k, float("nan")))
            row[f"res_{k}"] = float(res.get(k, float("nan")))
        rows.append(row)
    return rows
