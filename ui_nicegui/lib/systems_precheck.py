"""Systems Mode precheck runner — proposes samples only; truth via Evaluator."""

from __future__ import annotations

from typing import Any, Dict, Tuple


def build_targets_and_variables(session, base) -> Tuple[Dict[str, float], Dict[str, Tuple[float, float, float]]]:
    targets: Dict[str, float] = {}
    if session.systems_use_q:
        targets["Q_DT_eqv"] = float(session.systems_q_target)
    if session.systems_use_h:
        targets["H98"] = float(session.systems_h_target)
    if session.systems_use_pnet:
        targets["P_e_net_MW"] = float(session.systems_pnet_target)
    elif getattr(session, "systems_use_pfus", False) and float(getattr(session, "systems_pfus_target", 0) or 0) > 0:
        targets["Pfus_DT_adj_MW"] = float(session.systems_pfus_target)

    variables: Dict[str, Tuple[float, float, float]] = {}
    ip = float(getattr(base, "Ip_MA", 8.0))
    fg = float(getattr(base, "fG", 0.8))
    paux = float(getattr(base, "Paux_MW", 50.0))
    if session.systems_solve_ip:
        variables["Ip_MA"] = (ip, 0.5 * ip, 1.8 * ip)
    if session.systems_solve_fg:
        variables["fG"] = (fg, 0.2, min(1.0, 1.2))
    if session.systems_solve_paux:
        variables["Paux_MW"] = (paux, 0.0, max(200.0, 3.0 * paux))
    return targets, variables


def run_systems_precheck(
    base,
    targets: Dict[str, float],
    variables: Dict[str, Tuple[float, float, float]],
    *,
    n_random: int = 8,
    seed: int = 1337,
    design_intent: str = "",
    paux_for_q_mw: float | None = None,
) -> Any:
    try:
        from src.evaluator.core import Evaluator
        from src.systems.feasibility_completion import run_precheck
    except ImportError:
        from evaluator.core import Evaluator  # type: ignore
        from systems.feasibility_completion import run_precheck  # type: ignore

    ev = Evaluator(label="NiceGUI:Systems", cache_enabled=True, cache_max=4096)
    if paux_for_q_mw is not None:
        _base_ev = ev

        class _PauxWrapper:
            def evaluate(self, inp, Paux_for_Q_MW=None):
                return _base_ev.evaluate(inp, Paux_for_Q_MW=float(paux_for_q_mw))

        ev = _PauxWrapper()

    return run_precheck(
        base,
        targets,
        variables,
        include_random=True,
        n_random=int(n_random),
        seed=int(seed),
        evaluator=ev,
        hard_constraint_names=None,
    )
