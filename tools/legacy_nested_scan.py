"""Legacy nested Ti/H98/a/Q/g_conf screening scan (solver-assisted).

Governance note: this is NOT frozen cartography. Each grid cell runs a nested
(Ip, fG) point solver to match H98 and Q targets, then applies screening cuts.
Use Scan Lab cartography for evaluate-only slice truth.
"""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from phase1_core import solve_Ip_for_H98_with_Q_match
except ImportError:
    from src.phase1_core import solve_Ip_for_H98_with_Q_match  # type: ignore


def frange(start: float, stop: float, step: float) -> List[float]:
    vals: List[float] = []
    if step == 0:
        return [float(start)]
    x = float(start)
    if step > 0:
        while x <= float(stop) + 1e-12:
            vals.append(float(x))
            x += step
    else:
        while x >= float(stop) - 1e-12:
            vals.append(float(x))
            x += step
    return vals


def estimate_legacy_grid_count(spec: Dict[str, Any]) -> int:
    g = frange(spec["gconf_start"], spec["gconf_stop"], abs(float(spec["gconf_step"])))
    ti = frange(spec["Ti_start"], spec["Ti_stop"], abs(float(spec["Ti_step"])))
    h = frange(spec["H98_start"], spec["H98_stop"], abs(float(spec["H98_step"])))
    a = frange(spec["a_min"], spec["a_max"], abs(float(spec["a_step"])))
    q = frange(spec["Q_start"], spec["Q_stop"], abs(float(spec["Q_step"])))
    return max(1, len(g) * len(ti) * len(h) * len(a) * len(q))


def default_legacy_spec_from_session(session) -> Dict[str, Any]:
    inp = getattr(session, "inputs", {}) or {}
    base = session.build_point_inputs()
    r0 = float(getattr(base, "R0_m", inp.get("R0_m", 6.0)))
    a0 = float(getattr(base, "a_m", inp.get("a_m", 2.0)))
    ti0 = float(getattr(base, "Ti_keV", inp.get("Ti_keV", 10.0)))
    return {
        "R0": r0,
        "B0": float(getattr(base, "Bt_T", inp.get("Bt_T", 5.0))),
        "kappa": float(getattr(base, "kappa", inp.get("kappa", 1.7))),
        "tshield": float(getattr(base, "t_shield_m", inp.get("t_shield_m", 0.6))),
        "Paux": float(getattr(base, "Paux_MW", inp.get("Paux_MW", 50.0))),
        "Paux_for_Q": float(inp.get("Paux_for_Q_MW", getattr(base, "Paux_MW", 50.0))),
        "Ti_over_Te": float(getattr(base, "Ti_over_Te", inp.get("Ti_over_Te", 1.0))),
        "Zeff": float(getattr(base, "zeff", inp.get("zeff", 1.5))),
        "dilution_fuel": float(getattr(base, "dilution_fuel", inp.get("dilution_fuel", 0.9))),
        "extra_rad_factor": float(getattr(base, "extra_rad_factor", inp.get("extra_rad_factor", 1.0))),
        "alpha_loss_frac": float(getattr(base, "alpha_loss_frac", inp.get("alpha_loss_frac", 0.0))),
        "C_bs": float(getattr(base, "C_bs", inp.get("C_bs", 0.5))),
        "require_Hmode": bool(getattr(base, "require_Hmode", inp.get("require_Hmode", False))),
        "PLH_margin": float(getattr(base, "PLH_margin", inp.get("PLH_margin", 0.0))),
        "Ip_min": 1.0,
        "Ip_max": 20.0,
        "fG_min": 0.2,
        "fG_max": 1.0,
        "tol": 1e-3,
        "q95_min": 2.0,
        "betaN_max": 5.0,
        "f_bs_max": 0.95,
        "PSOL_over_R_max": 50.0,
        "Ti_start": max(1.0, 0.7 * ti0),
        "Ti_stop": min(40.0, 1.3 * ti0),
        "Ti_step": max(0.5, 0.2 * ti0),
        "H98_start": 0.8,
        "H98_stop": 1.4,
        "H98_step": 0.1,
        "a_min": max(0.2, 0.8 * a0),
        "a_max": min(5.0, 1.2 * a0),
        "a_step": max(0.05, 0.1 * a0),
        "Q_start": 5.0,
        "Q_stop": 20.0,
        "Q_step": 5.0,
        "gconf_start": 0.8,
        "gconf_stop": 1.2,
        "gconf_step": 0.2,
        "clean_knobs": dict(getattr(session, "knobs", {}) or {}),
    }


def _screen_point(sol_out: dict, spec: dict, *, Hreq: float, H98_eff: float, Qtar: float) -> bool:
    try:
        if float(sol_out.get("ne20", 0)) > 1.2:
            return False
        if float(sol_out.get("q95_proxy", 1e9)) < float(spec["q95_min"]):
            return False
        if float(sol_out.get("betaN_proxy", 0.0)) > float(spec["betaN_max"]):
            return False
        if float(sol_out.get("f_bs_proxy", 0.0)) > float(spec["f_bs_max"]):
            return False
        psol = float(sol_out.get("Ploss_MW", 0.0)) / float(spec["R0"])
        if psol > float(spec["PSOL_over_R_max"]):
            return False
        if spec.get("require_Hmode") and float(sol_out.get("LH_ok", 1.0)) < 0.5:
            return False
        if H98_eff < float(Hreq):
            return False
        if float(sol_out.get("Q_DT_eqv", 0.0)) < float(Qtar):
            return False
    except (TypeError, ValueError):
        return False
    return True


def run_legacy_nested_scan(
    spec: Dict[str, Any],
    *,
    base_inputs=None,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Run nested solver grid; returns (feasible_rows, meta)."""
    if base_inputs is None:
        raise ValueError("base_inputs required (Point Designer baseline)")
    Ti_grid = frange(spec["Ti_start"], spec["Ti_stop"], abs(float(spec["Ti_step"])))
    H_grid = frange(spec["H98_start"], spec["H98_stop"], abs(float(spec["H98_step"])))
    a_grid = frange(spec["a_min"], spec["a_max"], abs(float(spec["a_step"])))
    Q_grid = frange(spec["Q_start"], spec["Q_stop"], abs(float(spec["Q_step"])))
    g_grid = frange(spec["gconf_start"], spec["gconf_stop"], abs(float(spec["gconf_step"])))

    n_total = max(1, len(g_grid) * len(Ti_grid) * len(H_grid) * len(a_grid) * len(Q_grid))
    rows: List[Dict[str, Any]] = []
    best_g = None
    i_eval = 0
    t0 = time.time()

    for g_conf in g_grid:
        for Ti in Ti_grid:
            for Hreq in H_grid:
                for a in a_grid:
                    for Qtar in Q_grid:
                        i_eval += 1
                        if progress_cb:
                            progress_cb(i_eval, n_total)
                        H_base_target = float(Hreq) / max(float(g_conf), 1e-9)
                        base = replace(
                            base_inputs,
                            R0_m=float(spec["R0"]),
                            a_m=float(a),
                            kappa=float(spec["kappa"]),
                            Bt_T=float(spec["B0"]),
                            Ip_MA=0.5 * (float(spec["Ip_min"]) + float(spec["Ip_max"])),
                            Ti_keV=float(Ti),
                            fG=0.8,
                            t_shield_m=float(spec["tshield"]),
                            Paux_MW=float(spec["Paux"]),
                            Ti_over_Te=float(spec["Ti_over_Te"]),
                            zeff=float(spec["Zeff"]),
                            dilution_fuel=float(spec["dilution_fuel"]),
                            extra_rad_factor=float(spec["extra_rad_factor"]),
                            alpha_loss_frac=float(spec["alpha_loss_frac"]),
                            C_bs=float(spec["C_bs"]),
                            require_Hmode=bool(spec["require_Hmode"]),
                            PLH_margin=float(spec["PLH_margin"]),
                        )
                        sol_inp, sol_out, ok = solve_Ip_for_H98_with_Q_match(
                            base=base,
                            target_H98=H_base_target,
                            target_Q=float(Qtar),
                            Ip_min=float(spec["Ip_min"]),
                            Ip_max=float(spec["Ip_max"]),
                            fG_min=float(spec["fG_min"]),
                            fG_max=float(spec["fG_max"]),
                            tol=float(spec["tol"]),
                            Paux_for_Q_MW=float(spec["Paux_for_Q"]),
                        )
                        if not ok:
                            continue
                        H98_eff = float(g_conf) * float(sol_out.get("H98", 0.0))
                        if not _screen_point(sol_out, spec, Hreq=float(Hreq), H98_eff=H98_eff, Qtar=float(Qtar)):
                            continue
                        if best_g is None or float(g_conf) < best_g:
                            best_g = float(g_conf)
                        row = dict(sol_out)
                        row.update(
                            {
                                "g_conf": float(g_conf),
                                "Ti_keV": float(Ti),
                                "Q_target": float(Qtar),
                                "H98_required": float(Hreq),
                                "a_m": float(a),
                                "Ip_MA": float(sol_inp.Ip_MA),
                                "f_G": float(sol_inp.fG),
                                "H98_eff": float(H98_eff),
                            }
                        )
                        rows.append(row)

    meta = dict(spec)
    meta["n_total"] = int(n_total)
    meta["n_feasible"] = int(len(rows))
    meta["best_g_conf_found"] = best_g if best_g is not None else None
    meta["run_seconds"] = float(time.time() - t0)
    meta["kind"] = "shams_legacy_nested_scan"
    return rows, meta
