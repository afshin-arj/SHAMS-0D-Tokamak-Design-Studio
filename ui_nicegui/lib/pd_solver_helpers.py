"""Point Designer solver / hash / frontier helpers (no Streamlit)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any, Dict, Iterator, List, Optional, Tuple

try:
    from frontier.frontier import find_nearest_feasible
    from solvers.design_envelope import solve_sparc_envelope
    from solvers.optimize import optimize_design
    from solvers.point_solver import (
        solve_Ip_for_H98_with_Q_match,
        solve_Ip_for_H98_with_Q_match_stream,
    )
except ImportError:
    from src.frontier.frontier import find_nearest_feasible
    from src.solvers.design_envelope import solve_sparc_envelope
    from src.solvers.optimize import optimize_design
    from src.solvers.point_solver import (
        solve_Ip_for_H98_with_Q_match,
        solve_Ip_for_H98_with_Q_match_stream,
    )

from ui_nicegui.evaluate import ui_evaluate
from ui_nicegui.session import DesignSession


def _sf(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def sync_solver_bounds_from_inputs(session: DesignSession) -> None:
    """Initialize solver bounds from current machine knobs if unset."""
    ip = _sf(session.inputs.get("Ip_MA"), 8.0)
    fg = _sf(session.inputs.get("fG"), 0.8)
    if session.pd_ip_min <= 0:
        session.pd_ip_min = max(0.1, 0.80 * ip)
    if session.pd_ip_max <= session.pd_ip_min:
        session.pd_ip_max = max(0.2, 1.20 * ip)
    if session.pd_fg_min < 0:
        session.pd_fg_min = max(0.0, fg - 0.20)
    if session.pd_fg_max <= session.pd_fg_min:
        session.pd_fg_max = min(2.0, fg + 0.20)
    fuel = str(session.inputs.get("fuel_mode", "DT"))
    if fuel == "DD":
        session.pd_q_target = min(session.pd_q_target, 0.05) if session.pd_q_target > 0.1 else session.pd_q_target
        session.pd_h98_target = min(session.pd_h98_target, 1.0) if session.pd_h98_target > 1.05 else session.pd_h98_target


def compute_pd_inputs_fingerprint(session: DesignSession) -> Dict[str, Any]:
    inp = session.inputs
    return {
        "R0_m": _sf(inp.get("R0_m")),
        "a_m": _sf(inp.get("a_m")),
        "kappa": _sf(inp.get("kappa")),
        "delta": _sf(inp.get("delta")),
        "Bt_T": _sf(inp.get("Bt_T")),
        "Paux_MW": _sf(inp.get("Paux_MW")),
        "Ti_keV": _sf(inp.get("Ti_keV")),
        "Ti_over_Te": _sf(inp.get("Ti_over_Te")),
        "fuel_mode": str(inp.get("fuel_mode", "DT")),
        "Q_target": _sf(session.pd_q_target),
        "H98_target": _sf(session.pd_h98_target),
        "Ip_min": _sf(session.pd_ip_min),
        "Ip_max": _sf(session.pd_ip_max),
        "fG_min": _sf(session.pd_fg_min),
        "fG_max": _sf(session.pd_fg_max),
        "t_shield_m": _sf(inp.get("t_shield_m")),
        "magnet_technology": str(inp.get("magnet_technology", "")),
        "Tcoil_K": _sf(inp.get("Tcoil_K")),
        "pd_eval_mode": str(session.pd_eval_mode),
        "overlay": {k: session.overlay.get(k) for k in sorted(session.overlay.keys())},
    }


def compute_pd_inputs_hash(session: DesignSession) -> str:
    fp = compute_pd_inputs_fingerprint(session)
    payload = json.dumps(fp, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def inputs_stale(session: DesignSession) -> bool:
    cur = compute_pd_inputs_hash(session)
    session.pd_current_inputs_hash = cur
    last = session.pd_last_inputs_hash
    return bool(session.pd_last_outputs and last and cur != last)


def _log_append(log_lines: List[str], line: str) -> None:
    try:
        log_lines.append(str(line))
    except Exception:
        pass


def _solver_event_iter(session: DesignSession, base) -> Iterator[Dict[str, Any]]:
    mode = str(session.pd_eval_mode)
    if mode == "envelope":
        tgt: Dict[str, float] = {
            "Q_DT_eqv": float(session.pd_q_target),
            "H98": float(session.pd_h98_target),
        }
        pfus = float(session.pd_pfus_target)
        pnet = float(session.pd_pnet_target)
        if pfus > 0:
            tgt["Pfus_MW"] = pfus
        if pnet > 0:
            tgt["P_e_net_MW"] = pnet

        vary = ["Ip_MA", "fG"]
        bounds: Dict[str, Tuple[float, float]] = {
            "Ip_MA": (float(session.pd_ip_min), float(session.pd_ip_max)),
            "fG": (float(session.pd_fg_min), float(session.pd_fg_max)),
        }
        paux = _sf(base.Paux_MW, 50.0)
        if pnet > 0:
            vary.append("Paux_MW")
            bounds["Paux_MW"] = (0.0, max(paux, 1e-6) * 2.0)

        sol_inp, out_env, ok_env, msg_env = solve_sparc_envelope(
            base,
            tgt,
            vary=vary,
            bounds=bounds,
            tol=float(session.pd_solver_tol),
            max_iter=40,
        )

        def _env_events() -> Iterator[Dict[str, Any]]:
            yield {
                "event": "iter",
                "iter": 0,
                "Ip_MA": sol_inp.Ip_MA,
                "fG": sol_inp.fG,
                "H98": out_env.get("H98", float("nan")),
                "Q": out_env.get("Q_DT_eqv", float("nan")),
            }
            yield {"event": "done", "sol": sol_inp, "out": out_env, "ok": ok_env, "message": msg_env}

        return _env_events()
    return solve_Ip_for_H98_with_Q_match_stream(
        base=base,
        target_H98=float(session.pd_h98_target),
        target_Q=float(session.pd_q_target),
        Ip_min=float(session.pd_ip_min),
        Ip_max=float(session.pd_ip_max),
        fG_min=float(session.pd_fg_min),
        fG_max=float(session.pd_fg_max),
        tol=float(session.pd_solver_tol),
        Paux_for_Q_MW=session.paux_for_q,
    )


def run_point_designer_evaluation(session: DesignSession) -> Dict[str, Any]:
    """Evaluate Point Designer (direct or solver path). Returns result dict."""
    sync_solver_bounds_from_inputs(session)
    base = session.build_point_inputs()
    log_lines: List[str] = []
    trace: List[Dict[str, Any]] = []
    _log_append(log_lines, "Point Designer evaluation")

    if session.pd_do_opt:
        _log_append(
            log_lines,
            f"Optimization: objective={session.pd_opt_objective}, iters={session.pd_opt_iters}, seed={session.pd_opt_seed}",
        )
        var_bounds = {
            "Ip_MA": (float(session.pd_ip_min), float(session.pd_ip_max)),
            "fG": (float(session.pd_fg_min), float(session.pd_fg_max)),
            "Paux_MW": (0.0, max(_sf(base.Paux_MW), 1e-6) * 2.0),
        }
        best_inp, best_out = optimize_design(
            base,
            objective=str(session.pd_opt_objective),
            variables=var_bounds,
            n_iter=int(session.pd_opt_iters),
            seed=int(session.pd_opt_seed),
        )
        base = best_inp
        _log_append(
            log_lines,
            f"Optimized: Ip={best_inp.Ip_MA:.4g} MA, fG={best_inp.fG:.4g}, Paux={best_inp.Paux_MW:.4g} MW",
        )
        _log_append(
            log_lines,
            f"  Bpeak={best_out.get('B_peak_T', float('nan')):.4g} T, Pnet={best_out.get('P_e_net_MW', float('nan')):.4g} MW",
        )

    mode = str(session.pd_eval_mode)
    sol_inp = base
    out: Dict[str, Any] = {}
    ok = True

    if mode in ("solver", "envelope"):
        _log_append(log_lines, f"Solver mode: {mode}")
        for ev in _solver_event_iter(session, base):
            evt = str(ev.get("event", ""))
            if evt == "bracket":
                okb = bool(ev.get("ok"))
                _log_append(
                    log_lines,
                    f"BRACKET: H98(Ip_lo)={ev.get('H98_lo'):.6g}, H98(Ip_hi)={ev.get('H98_hi'):.6g} -> "
                    f"{'OK' if okb else 'NO_BRACKET'}",
                )
                trace.append(dict(ev))
            elif evt == "iter":
                _log_append(
                    log_lines,
                    f"ITER {int(ev.get('iter', 0)):>3d}: Ip={ev.get('Ip_MA'):.8g} MA, fG={ev.get('fG'):.8g}, "
                    f"H98={ev.get('H98'):.8g}, Q={ev.get('Q'):.8g}, residual={ev.get('residual'):.8g}",
                )
                trace.append({
                    "iter": ev.get("iter"),
                    "Ip_MA": ev.get("Ip_MA"),
                    "fG": ev.get("fG"),
                    "H98": ev.get("H98"),
                    "Q": ev.get("Q"),
                    "residual": ev.get("residual"),
                })
            elif evt == "done":
                sol_inp = ev.get("sol") or base
                out = dict(ev.get("out") or {})
                ok = bool(ev.get("ok", True))
                _log_append(
                    log_lines,
                    f"DONE: Ip={out.get('Ip_MA', float('nan')):.8g} MA, fG={out.get('fG', float('nan')):.8g}, "
                    f"H98={out.get('H98', float('nan')):.8g}, Q={out.get('Q_DT_eqv', float('nan')):.8g}",
                )
            elif evt == "fail":
                ok = False
                _log_append(log_lines, f"FAIL: {ev.get('reason', 'solver_failed')}")
                trace.append(dict(ev))

        if not ok and mode == "solver":
            sol_inp, out, ok = solve_Ip_for_H98_with_Q_match(
                base,
                target_H98=float(session.pd_h98_target),
                target_Q=float(session.pd_q_target),
                Ip_min=float(session.pd_ip_min),
                Ip_max=float(session.pd_ip_max),
                fG_min=float(session.pd_fg_min),
                fG_max=float(session.pd_fg_max),
                tol=float(session.pd_solver_tol),
                Paux_for_Q_MW=session.paux_for_q,
            )
    else:
        _log_append(log_lines, "Direct frozen-point evaluate (no solver)")
        out = ui_evaluate(sol_inp, origin="NiceGUI:Point Designer", Paux_for_Q_MW=session.paux_for_q)

    if mode in ("solver", "envelope") and ok and sol_inp is not None:
        session.inputs["Ip_MA"] = float(getattr(sol_inp, "Ip_MA", session.inputs.get("Ip_MA")))
        session.inputs["fG"] = float(getattr(sol_inp, "fG", session.inputs.get("fG")))
        if not out:
            out = ui_evaluate(sol_inp, origin="NiceGUI:Point Designer", Paux_for_Q_MW=session.paux_for_q)

    session.pd_solver_trace = trace
    session.pd_last_log_lines = log_lines
    cur_hash = compute_pd_inputs_hash(session)
    session.pd_current_inputs_hash = cur_hash

    inputs_dict = asdict(sol_inp) if hasattr(sol_inp, "__dataclass_fields__") else dict(session.inputs)
    if hasattr(sol_inp, "to_dict"):
        inputs_dict = sol_inp.to_dict()

    return {
        "ok": ok,
        "outputs": dict(out),
        "inputs": inputs_dict,
        "log_lines": log_lines,
        "trace": trace,
        "inputs_hash": cur_hash,
    }


def search_nearest_feasible(session: DesignSession) -> Dict[str, Any]:
    base = session.build_point_inputs()
    fr = find_nearest_feasible(
        base,
        levers={"Ip_MA": (session.pd_ip_min, session.pd_ip_max), "fG": (session.pd_fg_min, session.pd_fg_max)},
        targets={"H98": float(session.pd_h98_target), "Q_DT_eqv": float(session.pd_q_target)},
        n_random=80,
        seed=0,
    )
    report = dict(fr.report) if hasattr(fr, "report") else {}
    session.pd_frontier_last = report
    return report


def build_summary_pdf_bytes(artifact: Dict[str, Any]) -> Optional[bytes]:
    import os
    import tempfile

    try:
        from shams_io.plotting import plot_summary_pdf
    except ImportError:
        from src.shams_io.plotting import plot_summary_pdf

    try:
        tmpdir = tempfile.mkdtemp(prefix="shams_export_")
        pdf_path = os.path.join(tmpdir, "summary.pdf")
        plot_summary_pdf(artifact, pdf_path)
        with open(pdf_path, "rb") as f:
            return f.read()
    except Exception:
        return None
