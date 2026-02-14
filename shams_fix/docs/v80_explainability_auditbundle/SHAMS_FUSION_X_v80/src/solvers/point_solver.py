from __future__ import annotations
from typing import Callable, Dict, Optional, Tuple, Iterator, Any
from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from solvers.root import bisect
from solvers.constraint_solver import solve_for_targets
import math

def solve_Ip_for_H98_with_Q_match_stream(
    base: 'PointInputs',
    target_H98: float,
    target_Q: float,
    Ip_min: float,
    Ip_max: float,
    fG_min: float,
    fG_max: float,
    tol: float,
    Paux_for_Q_MW: Optional[float],
    max_iter: int = 80,
) -> Iterator[Dict[str, Any]]:
    """Stream the nested (Ip, fG) solve so a UI can visualize progress.

    Yields dict events of the form:
      - {'event': 'bracket', ...}
      - {'event': 'iter', 'iter': i, 'Ip_MA': mid, 'fG': fG_sol, 'H98': H, 'Q': Q, 'residual': H-target_H98, ...}
      - {'event': 'done', 'sol': PointInputs, 'out': out_dict}
      - {'event': 'fail', 'reason': 'no_bracket' | 'nonfinite'}

    Notes:
    - Inner fG solve is *not* streamed (to keep output compact). Each outer evaluation solves fG fully.
    - Intended for interactive UX only; the non-streaming solver remains the canonical API.
    """

    def eval_at_Ip(Ip: float) -> Tuple[float, Optional['PointInputs'], Optional[Dict[str, float]], bool]:
        tmp = PointInputs(**{**base.__dict__, "Ip_MA": float(Ip)})
        sol_fG, out2, ok2 = solve_fG_for_QDTeqv(tmp, target_Q, fG_min, fG_max, tol, Paux_for_Q_MW)
        if not ok2:
            return float('nan'), None, None, False
        H = float(out2.get('H98', float('nan')))
        if not math.isfinite(H):
            return float('nan'), sol_fG, out2, False
        return H, sol_fG, out2, True

    # Bracketing
    H_lo, sol_lo, out_lo, ok_lo = eval_at_Ip(Ip_min)
    H_hi, sol_hi, out_hi, ok_hi = eval_at_Ip(Ip_max)
    if (not ok_lo) or (not ok_hi) or (not math.isfinite(H_lo)) or (not math.isfinite(H_hi)):
        yield {"event": "fail", "reason": "nonfinite"}
        return
    flo = H_lo - target_H98
    fhi = H_hi - target_H98
    yield {
        "event": "bracket",
        "Ip_lo": float(Ip_min), "Ip_hi": float(Ip_max),
        "H98_lo": float(H_lo), "H98_hi": float(H_hi),
        "fG_lo": float(sol_lo.fG) if sol_lo is not None else float('nan'),
        "fG_hi": float(sol_hi.fG) if sol_hi is not None else float('nan'),
        "Q_lo": float(out_lo.get('Q_DT_eqv', float('nan'))) if out_lo else float('nan'),
        "Q_hi": float(out_hi.get('Q_DT_eqv', float('nan'))) if out_hi else float('nan'),
        "res_lo": float(flo), "res_hi": float(fhi),
        "ok": bool(flo * fhi <= 0),
    }
    if flo * fhi > 0:
        # No bracket within Ip bounds. Clamp to nearest bound (feasibility-first),
        # but remain explicit and audit-friendly.
        if abs(flo) <= abs(fhi):
            Ip_sol = float(Ip_min)
            sol = sol_lo
            out = dict(out_lo) if out_lo else {}
            out['Ip_MA'] = float(Ip_sol)
            if sol is not None:
                out['fG'] = float(sol.fG)
            out['H98'] = float(H_lo)
            H_at = float(H_lo)
            res = float(flo)
            which = "Ip_min"
        else:
            Ip_sol = float(Ip_max)
            sol = sol_hi
            out = dict(out_hi) if out_hi else {}
            out['Ip_MA'] = float(Ip_sol)
            if sol is not None:
                out['fG'] = float(sol.fG)
            out['H98'] = float(H_hi)
            H_at = float(H_hi)
            res = float(fhi)
            which = "Ip_max"
        if out is None:
            out = {}
        out["_solver_clamped"] = True
        out["_solver_clamped_on"] = which
        out["_H98_target"] = float(target_H98)
        out["_H98_at_bound"] = float(H_at)
        out["_H98_residual"] = float(res)
        out["_note"] = "H98 target not bracketed within Ip bounds; clamped to nearest bound."
        yield {"event": "done", "sol": sol, "out": out}
        return

    lo, hi = float(Ip_min), float(Ip_max)
    for it in range(int(max_iter)):
        mid = 0.5 * (lo + hi)
        H_mid, sol_mid, out_mid, ok_mid = eval_at_Ip(mid)
        if not ok_mid:
            yield {"event": "fail", "reason": "nonfinite", "iter": it, "Ip_MA": float(mid)}
            return
        res = H_mid - target_H98
        yield {
            "event": "iter",
            "iter": int(it),
            "Ip_MA": float(mid),
            "fG": float(sol_mid.fG) if sol_mid is not None else float('nan'),
            "H98": float(H_mid),
            "Q": float(out_mid.get('Q_DT_eqv', float('nan'))) if out_mid else float('nan'),
            "Pfus_DT_adj_MW": float(out_mid.get('Pfus_DT_adj_MW', float('nan'))) if out_mid else float('nan'),
            "Ploss_MW": float(out_mid.get('Ploss_MW', float('nan'))) if out_mid else float('nan'),
            "residual": float(res),
            "Ip_lo": float(lo), "Ip_hi": float(hi),
        }
        if abs(res) < tol:
            Ip_sol = float(mid)
            inp_Ip = PointInputs(**{**base.__dict__, "Ip_MA": Ip_sol})
            sol, out, ok2 = solve_fG_for_QDTeqv(inp_Ip, target_Q, fG_min, fG_max, tol, Paux_for_Q_MW)
            if not ok2:
                yield {"event": "fail", "reason": "nonfinite", "Ip_MA": float(Ip_sol)}
                return
            yield {"event": "done", "sol": sol, "out": out}
            return
        # Update bracket
        if flo * res <= 0:
            hi = mid
            fhi = res
        else:
            lo = mid
            flo = res

    # Max iterations reached: accept mid as solution attempt
    Ip_sol = 0.5 * (lo + hi)
    inp_Ip = PointInputs(**{**base.__dict__, "Ip_MA": float(Ip_sol)})
    sol, out, ok2 = solve_fG_for_QDTeqv(inp_Ip, target_Q, fG_min, fG_max, tol, Paux_for_Q_MW)
    if not ok2:
        yield {"event": "fail", "reason": "nonfinite", "Ip_MA": float(Ip_sol)}
        return
    yield {"event": "done", "sol": sol, "out": out}

def solve_fG_for_QDTeqv(base: PointInputs, target_Q: float, fG_min: float, fG_max: float, tol: float, Paux_for_Q_MW: Optional[float]) -> Tuple[PointInputs, Dict[str, float], bool]:
    """
    Solve for Greenwald fraction fG such that Q_DT_eqv matches target_Q.
    """
    def Q_of_fG(fG: float) -> float:
        inp = PointInputs(**{**base.__dict__, "fG": fG})
        return hot_ion_point(inp, Paux_for_Q_MW)["Q_DT_eqv"]
    fG_sol, ok = bisect(Q_of_fG, fG_min, fG_max, target_Q, tol=tol)
    if not ok:
        # No bracket inside bounds. Clamp to the nearest bound (feasibility-first),
        # but emit explicit audit flags in the output.
        Q_lo = Q_of_fG(fG_min)
        Q_hi = Q_of_fG(fG_max)
        # Choose bound with smallest absolute residual
        res_lo = Q_lo - target_Q
        res_hi = Q_hi - target_Q
        if abs(res_lo) <= abs(res_hi):
            fG_sol = float(fG_min)
            Q_at = float(Q_lo)
            which = "fG_min"
            res = float(res_lo)
        else:
            fG_sol = float(fG_max)
            Q_at = float(Q_hi)
            which = "fG_max"
            res = float(res_hi)
        sol = PointInputs(**{**base.__dict__, "fG": float(fG_sol)})
        out = dict(hot_ion_point(sol, Paux_for_Q_MW))
        out["_solver_clamped_Q"] = True
        out["_solver_clamped_Q_on"] = which
        out["_Q_target"] = float(target_Q)
        out["_Q_at_bound"] = float(Q_at)
        out["_Q_residual"] = float(res)
        return sol, out, True
    sol = PointInputs(**{**base.__dict__, "fG": float(fG_sol)})
    out = dict(hot_ion_point(sol, Paux_for_Q_MW))
    out["_solver_clamped_Q"] = False
    return sol, out, True

def solve_Ip_for_H98_with_Q_match_stream(
    base: 'PointInputs',
    target_H98: float,
    target_Q: float,
    Ip_min: float,
    Ip_max: float,
    fG_min: float,
    fG_max: float,
    tol: float,
    Paux_for_Q_MW: Optional[float],
    max_iter: int = 80,
) -> Iterator[Dict[str, Any]]:
    """Stream the nested (Ip, fG) solve so a UI can visualize progress.

    Yields dict events of the form:
      - {'event': 'bracket', ...}
      - {'event': 'iter', 'iter': i, 'Ip_MA': mid, 'fG': fG_sol, 'H98': H, 'Q': Q, 'residual': H-target_H98, ...}
      - {'event': 'done', 'sol': PointInputs, 'out': out_dict}
      - {'event': 'fail', 'reason': 'no_bracket' | 'nonfinite'}

    Notes:
    - Inner fG solve is *not* streamed (to keep output compact). Each outer evaluation solves fG fully.
    - Intended for interactive UX only; the non-streaming solver remains the canonical API.
    """

    def eval_at_Ip(Ip: float) -> Tuple[float, Optional['PointInputs'], Optional[Dict[str, float]], bool]:
        tmp = PointInputs(**{**base.__dict__, "Ip_MA": float(Ip)})
        sol_fG, out2, ok2 = solve_fG_for_QDTeqv(tmp, target_Q, fG_min, fG_max, tol, Paux_for_Q_MW)
        if not ok2:
            return float('nan'), None, None, False
        H = float(out2.get('H98', float('nan')))
        if not math.isfinite(H):
            return float('nan'), sol_fG, out2, False
        return H, sol_fG, out2, True

    # Bracketing
    H_lo, sol_lo, out_lo, ok_lo = eval_at_Ip(Ip_min)
    H_hi, sol_hi, out_hi, ok_hi = eval_at_Ip(Ip_max)
    if (not ok_lo) or (not ok_hi) or (not math.isfinite(H_lo)) or (not math.isfinite(H_hi)):
        yield {"event": "fail", "reason": "nonfinite"}
        return
    flo = H_lo - target_H98
    fhi = H_hi - target_H98
    yield {
        "event": "bracket",
        "Ip_lo": float(Ip_min), "Ip_hi": float(Ip_max),
        "H98_lo": float(H_lo), "H98_hi": float(H_hi),
        "fG_lo": float(sol_lo.fG) if sol_lo is not None else float('nan'),
        "fG_hi": float(sol_hi.fG) if sol_hi is not None else float('nan'),
        "Q_lo": float(out_lo.get('Q_DT_eqv', float('nan'))) if out_lo else float('nan'),
        "Q_hi": float(out_hi.get('Q_DT_eqv', float('nan'))) if out_hi else float('nan'),
        "res_lo": float(flo), "res_hi": float(fhi),
        "ok": bool(flo * fhi <= 0),
    }
    if flo * fhi > 0:
        # No bracket within Ip bounds. Clamp to nearest bound (feasibility-first),
        # but remain explicit and audit-friendly.
        if abs(flo) <= abs(fhi):
            Ip_sol = float(Ip_min)
            sol = sol_lo
            out = dict(out_lo) if out_lo else {}
            out['Ip_MA'] = float(Ip_sol)
            if sol is not None:
                out['fG'] = float(sol.fG)
            out['H98'] = float(H_lo)
            H_at = float(H_lo)
            res = float(flo)
            which = "Ip_min"
        else:
            Ip_sol = float(Ip_max)
            sol = sol_hi
            out = dict(out_hi) if out_hi else {}
            out['Ip_MA'] = float(Ip_sol)
            if sol is not None:
                out['fG'] = float(sol.fG)
            out['H98'] = float(H_hi)
            H_at = float(H_hi)
            res = float(fhi)
            which = "Ip_max"
        if out is None:
            out = {}
        out["_solver_clamped"] = True
        out["_solver_clamped_on"] = which
        out["_H98_target"] = float(target_H98)
        out["_H98_at_bound"] = float(H_at)
        out["_H98_residual"] = float(res)
        out["_note"] = "H98 target not bracketed within Ip bounds; clamped to nearest bound."
        yield {"event": "done", "sol": sol, "out": out}
        return

    lo, hi = float(Ip_min), float(Ip_max)
    for it in range(int(max_iter)):
        mid = 0.5 * (lo + hi)
        H_mid, sol_mid, out_mid, ok_mid = eval_at_Ip(mid)
        if not ok_mid:
            yield {"event": "fail", "reason": "nonfinite", "iter": it, "Ip_MA": float(mid)}
            return
        res = H_mid - target_H98
        yield {
            "event": "iter",
            "iter": int(it),
            "Ip_MA": float(mid),
            "fG": float(sol_mid.fG) if sol_mid is not None else float('nan'),
            "H98": float(H_mid),
            "Q": float(out_mid.get('Q_DT_eqv', float('nan'))) if out_mid else float('nan'),
            "Pfus_DT_adj_MW": float(out_mid.get('Pfus_DT_adj_MW', float('nan'))) if out_mid else float('nan'),
            "Ploss_MW": float(out_mid.get('Ploss_MW', float('nan'))) if out_mid else float('nan'),
            "residual": float(res),
            "Ip_lo": float(lo), "Ip_hi": float(hi),
        }
        if abs(res) < tol:
            Ip_sol = float(mid)
            inp_Ip = PointInputs(**{**base.__dict__, "Ip_MA": Ip_sol})
            sol, out, ok2 = solve_fG_for_QDTeqv(inp_Ip, target_Q, fG_min, fG_max, tol, Paux_for_Q_MW)
            if not ok2:
                yield {"event": "fail", "reason": "nonfinite", "Ip_MA": float(Ip_sol)}
                return
            yield {"event": "done", "sol": sol, "out": out}
            return
        # Update bracket
        if flo * res <= 0:
            hi = mid
            fhi = res
        else:
            lo = mid
            flo = res

    # Max iterations reached: accept mid as solution attempt
    Ip_sol = 0.5 * (lo + hi)
    inp_Ip = PointInputs(**{**base.__dict__, "Ip_MA": float(Ip_sol)})
    sol, out, ok2 = solve_fG_for_QDTeqv(inp_Ip, target_Q, fG_min, fG_max, tol, Paux_for_Q_MW)
    if not ok2:
        yield {"event": "fail", "reason": "nonfinite", "Ip_MA": float(Ip_sol)}
        return
    yield {"event": "done", "sol": sol, "out": out}


def solve_fG_for_QDTeqv(base: PointInputs, target_Q: float, fG_min: float, fG_max: float, tol: float, Paux_for_Q_MW: Optional[float]) -> Tuple[PointInputs, Dict[str, float], bool]:
    """
    Solve for Greenwald fraction fG such that Q_DT_eqv matches target_Q.
    """
    def Q_of_fG(fG: float) -> float:
        inp = PointInputs(**{**base.__dict__, "fG": fG})
        return hot_ion_point(inp, Paux_for_Q_MW)["Q_DT_eqv"]
    fG_sol, ok = bisect(Q_of_fG, fG_min, fG_max, target_Q, tol=tol)
    if not ok:
        # No bracket inside bounds. Clamp to the nearest bound (feasibility-first),
        # but emit explicit audit flags in the output.
        Q_lo = Q_of_fG(fG_min)
        Q_hi = Q_of_fG(fG_max)
        # Choose bound with smallest absolute residual
        res_lo = Q_lo - target_Q
        res_hi = Q_hi - target_Q
        if abs(res_lo) <= abs(res_hi):
            fG_sol = float(fG_min)
            Q_at = float(Q_lo)
            which = "fG_min"
            res = float(res_lo)
        else:
            fG_sol = float(fG_max)
            Q_at = float(Q_hi)
            which = "fG_max"
            res = float(res_hi)
        sol = PointInputs(**{**base.__dict__, "fG": float(fG_sol)})
        out = dict(hot_ion_point(sol, Paux_for_Q_MW))
        out["_solver_clamped_Q"] = True
        out["_solver_clamped_Q_on"] = which
        out["_Q_target"] = float(target_Q)
        out["_Q_at_bound"] = float(Q_at)
        out["_Q_residual"] = float(res)
        return sol, out, True
    sol = PointInputs(**{**base.__dict__, "fG": float(fG_sol)})
    out = dict(hot_ion_point(sol, Paux_for_Q_MW))
    out["_solver_clamped_Q"] = False
    return sol, out, True


def solve_Ip_for_H98_with_Q_match(
    base: PointInputs,
    target_H98: float,
    target_Q: float,
    Ip_min: float,
    Ip_max: float,
    fG_min: float,
    fG_max: float,
    tol: float,
    Paux_for_Q_MW: Optional[float],
) -> Tuple[PointInputs, Dict[str, float], bool]:
    """Solve (Ip, fG) for (H98, Q) targets.

    Upgrade (decision-grade robustness):
      1) Try a coupled damped-Newton solve using `solve_for_targets` (no bracketing)
      2) Fall back to the legacy nested-bisection method if the coupled solve fails

    The coupled solve prevents the common UI failure mode where H98 does not
    bracket the target within [Ip_min, Ip_max].
    """

    # Coupled solve first (preferred)
    try:
        variables = {
            "Ip_MA": (float(base.Ip_MA), float(Ip_min), float(Ip_max)),
            "fG": (float(base.fG), float(fG_min), float(fG_max)),
        }
        res = solve_for_targets(
            base=base,
            targets={"H98": float(target_H98), "Q_DT_eqv": float(target_Q)},
            variables=variables,
            max_iter=40,
            tol=float(tol),
            damping=0.6,
        )
        out_c = dict(res.out)
        out_c["_solver"] = {
            "backend": "constraint_solver",
            "ok": bool(res.ok),
            "iters": int(res.iters),
            "message": str(res.message),
            "trace": res.trace,
        }
        if res.ok:
            return res.inp, out_c, True
    except Exception:
        res = None

    # Legacy fallback (nested)
    def H_of_Ip(Ip: float) -> float:
        tmp = PointInputs(**{**base.__dict__, "Ip_MA": float(Ip)})
        tmp2, out2, ok2 = solve_fG_for_QDTeqv(tmp, target_Q, fG_min, fG_max, tol, Paux_for_Q_MW)
        if not ok2:
            return float("nan")
        return float(out2.get("H98", float("nan")))

    Ip_sol, ok = bisect(H_of_Ip, float(Ip_min), float(Ip_max), float(target_H98), tol=float(tol))
    if not ok:
        # Provide a best-effort evaluation at bounds for diagnostics.
        try:
            H_lo = H_of_Ip(float(Ip_min))
            H_hi = H_of_Ip(float(Ip_max))
        except Exception:
            H_lo, H_hi = float("nan"), float("nan")
        return base, {"H98_at_Ip_min": H_lo, "H98_at_Ip_max": H_hi}, False

    inp_Ip = PointInputs(**{**base.__dict__, "Ip_MA": float(Ip_sol)})
    sol, out, ok2 = solve_fG_for_QDTeqv(inp_Ip, target_Q, fG_min, fG_max, tol, Paux_for_Q_MW)
    return sol, out, bool(ok2)
