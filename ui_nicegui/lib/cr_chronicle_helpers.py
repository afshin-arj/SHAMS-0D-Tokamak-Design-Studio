"""Control Room Chronicle helpers — Phase 18."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ui_nicegui.bootstrap import repo_root


def repo() -> Path:
    return Path(repo_root())


def point_inputs_from_artifact(art: dict):
    from src.models.inputs import PointInputs

    inp_d = art.get("inputs") if isinstance(art.get("inputs"), dict) else {}
    if not inp_d:
        raise ValueError("Artifact has no inputs block")
    try:
        return PointInputs.from_dict(inp_d)
    except Exception:
        fields = PointInputs.__dataclass_fields__.keys()
        return PointInputs(**{k: inp_d[k] for k in fields if k in inp_d})


def run_sensitivity_pack(
    base,
    *,
    knobs: List[str],
    outputs: List[str],
    step_rel: float = 1e-3,
) -> dict:
    from src.analysis.sensitivity import deterministic_sensitivity_pack
    from ui_nicegui.evaluate import ui_evaluate

    scales = {k: 1.0 for k in knobs}
    scales.update({"Paux_MW": 10.0, "Ip_MA": 1.0, "fG": 0.1, "Bt_T": 0.5, "R0_m": 0.5, "a_m": 0.2})

    def _eval(inp):
        return ui_evaluate(inp, origin="NiceGUI:CRSensitivity")

    return deterministic_sensitivity_pack(
        base,
        variables={k: scales.get(k, 1.0) for k in knobs},
        outputs=list(outputs),
        step_rel=float(step_rel),
        evaluate_fn=_eval,
    )


def sensitivity_table_rows(
    pack: dict,
    knobs: List[str],
    outputs: List[str],
    *,
    feasible: bool = True,
) -> List[dict]:
    from ui_nicegui.lib.sensitivity_honesty import jacobian_table_rows

    return jacobian_table_rows(pack, knobs, outputs, feasible=feasible)


def load_study_index(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Study index must be a JSON object")
    return data


def feasibility_map_grid(cases: List[dict], xcol: str, ycol: str) -> dict:
    xs = sorted({c.get(xcol) for c in cases if xcol in c})
    ys = sorted({c.get(ycol) for c in cases if ycol in c})
    grid: List[List[Optional[bool]]] = []
    for y in ys:
        row: List[Optional[bool]] = []
        for x in xs:
            match = [c for c in cases if c.get(xcol) == x and c.get(ycol) == y]
            if not match:
                row.append(None)
            else:
                row.append(bool(match[0].get("ok", match[0].get("is_feasible"))))
        grid.append(row)
    return {"x": xs, "y": ys, "ok_grid": grid, "n_cases": len(cases)}


def flatten_certified_search_artifact(art: dict) -> tuple:
    variables = list((art.get("spec") or {}).get("variables") or [])
    records: List[dict] = []
    for stg in art.get("stages") or []:
        if not isinstance(stg, dict):
            continue
        for r in stg.get("records") or []:
            if not isinstance(r, dict):
                continue
            x = r.get("x") or {}
            if isinstance(x, dict):
                records.append(
                    {
                        "x": x,
                        "verdict": r.get("verdict"),
                        "score": r.get("score"),
                        "evidence": r.get("evidence") or {},
                        "stage": stg.get("name"),
                    }
                )
    return variables, records


def analyze_interval_narrowing(
    variables: List[dict],
    records: List[dict],
    *,
    bins: int = 12,
    min_samples_per_bin: int = 2,
) -> dict:
    from src.solvers.interval_narrowing import propose_interval_narrowing

    return propose_interval_narrowing(
        variables=variables,
        records=records,
        bins=int(bins),
        min_samples_per_bin=int(min_samples_per_bin),
    )


def run_local_forensics(base, *, design_intent: str = "Reactor") -> dict:
    from src.analysis.forensics import local_sensitivity
    from ui_nicegui.evaluate import ui_evaluate

    def _eval(inp):
        return ui_evaluate(inp, origin="NiceGUI:CRForensics")

    return local_sensitivity(base, design_intent=design_intent, evaluate_fn=_eval)


def list_variable_registry_keys() -> List[str]:
    try:
        from docs.variable_registry import VARIABLES
    except ImportError:
        try:
            from src.docs.variable_registry import VARIABLES
        except ImportError:
            return []
    return sorted({str(v.get("key", "")) for v in VARIABLES if v.get("key")})


def evaluate_knob_trade_grid(
    base,
    *,
    kx: str,
    ky: str,
    x_span: float,
    y_span: float,
    nx: int,
    ny: int,
    patch: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Evaluate a 2-knob feasibility grid around the base point (frozen truth only)."""
    from dataclasses import replace

    from ui_nicegui.evaluate import ui_evaluate
    from ui_nicegui.lib.verdict_core import verdict_summary

    pi = base
    if patch:
        pi = replace(base, **{k: float(v) for k, v in patch.items() if hasattr(base, k)})

    def _getv(obj, key: str) -> float:
        return float(getattr(obj, key))

    def _setv(obj, key: str, val: float):
        return replace(obj, **{key: float(val)})

    x0 = _getv(pi, kx)
    y0 = _getv(pi, ky)
    nx = max(2, int(nx))
    ny = max(2, int(ny))
    xs = [x0 - x_span + (2 * x_span * i / (nx - 1)) for i in range(nx)]
    ys = [y0 - y_span + (2 * y_span * j / (ny - 1)) for j in range(ny)]
    rows: List[Dict[str, Any]] = []
    for xv in xs:
        for yv in ys:
            cand = _setv(_setv(pi, kx, xv), ky, yv)
            try:
                out = ui_evaluate(cand, origin="control_room_knob_grid")
                vs = verdict_summary(out)
                # Hard / governance feasibility only — soft/diagnostic fails are not INFEASIBLE.
                ok = bool(vs.get("feasible"))
                top = vs.get("dominant") if not ok else None
                rows.append(
                    {
                        kx: float(xv),
                        ky: float(yv),
                        "feasible": bool(ok),
                        "top_blocker": top,
                        "Q": float(out.get("Q_DT_eqv", out.get("Q", float("nan")))),
                        "H98": float(out.get("H98", float("nan"))),
                        "Pfus_total_MW": float(
                            out.get("Pfus_total_MW", out.get("P_fus_MW", out.get("Pfus_MW", float("nan"))))
                        ),
                        "P_e_net_MW": float(
                            out.get("P_e_net_MW", out.get("P_net_e_MW", float("nan")))
                        ),
                    }
                )
            except Exception:
                rows.append(
                    {
                        kx: float(xv),
                        ky: float(yv),
                        "feasible": False,
                        "top_blocker": "eval_error",
                        "Q": float("nan"),
                        "H98": float("nan"),
                        "Pfus_total_MW": float("nan"),
                        "P_e_net_MW": float("nan"),
                    }
                )
    return rows


def flatten_certified_search_table_rows(art: dict) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for stg in art.get("stages") or []:
        if not isinstance(stg, dict):
            continue
        for r in stg.get("records") or []:
            if not isinstance(r, dict):
                continue
            row = {
                "stage": stg.get("name"),
                "i": r.get("i"),
                "verdict": r.get("verdict"),
                "score": r.get("score"),
            }
            x = r.get("x") or {}
            if isinstance(x, dict):
                row.update(x)
            ev = r.get("evidence") or {}
            if isinstance(ev, dict):
                for k, v in ev.items():
                    row[f"e_{k}"] = v
            rows.append(row)
    return rows


def run_orchestrated_certified_search_nicegui(
    base,
    *,
    variables: List[Dict[str, float]],
    budget: int,
    seed: int,
    method: str,
    objective: str,
    two_stage: bool,
    stage2_budget_frac: float,
    stage2_shrink: float,
    stage2_method: str,
    insert_surr: bool,
    surr_frac: float,
    surr_pool_mult: int,
    surr_kappa: float,
    surr_ridge: float,
    mode: str,
    pareto_objectives: Optional[List[Dict[str, str]]] = None,
    max_frontier: int = 30,
    filter_mirage: bool = True,
) -> dict:
    """Run certified search orchestrator (external to frozen truth)."""
    from dataclasses import replace

    from solvers.budgeted_search import SearchVar
    from solvers.certified_search_orchestrator import (
        OrchestratorSpec,
        ParetoObjective,
        SearchStage,
        run_orchestrated_certified_pareto_search,
        run_orchestrated_certified_search,
    )

    from ui_nicegui.evaluate import ui_evaluate

    try:
        from constraints.constraints import evaluate_constraints
    except ImportError:
        from src.constraints.constraints import evaluate_constraints

    vars_ = [
        SearchVar(name=str(v["name"]), lo=float(v["lo"]), hi=float(v["hi"]))
        for v in variables
    ]

    def _builder(b, overrides):
        return replace(b, **{k: float(v) for k, v in overrides.items()})

    def _verifier(inp_obj):
        out = ui_evaluate(inp_obj, origin="certified_search_verifier")
        cons = evaluate_constraints(out, point_inputs=inp_obj)
        from ui_nicegui.lib.verdict_core import verdict_summary

        try:
            from constraints.constraints import constraint_is_hard
        except ImportError:
            from src.constraints.constraints import constraint_is_hard  # type: ignore

        try:
            from constraints.bookkeeping import summarize as _summarize_constraints

            _cs = _summarize_constraints(cons)
            _min_margin_frac = (
                float(_cs.worst_hard_margin_frac) if _cs.worst_hard_margin_frac is not None else float("nan")
            )
            _worst_hard = str(_cs.worst_hard or "")
        except Exception:
            _min_margin_frac = float("nan")
            _worst_hard = ""
        vs = verdict_summary(out)
        # Hard / governance feasibility only — soft/diagnostic fails are not REJECTED.
        ok = bool(vs.get("feasible"))
        hard_fails = [c for c in cons if (not bool(getattr(c, "passed", True))) and constraint_is_hard(c)]
        score = float(out.get(objective, 0.0)) if ok else float("-inf")
        evidence = {
            "objective": objective,
            "objective_value": float(out.get(objective, float("nan"))),
            "min_margin_frac": _min_margin_frac,
            "worst_hard": _worst_hard or str(vs.get("dominant") or ""),
            "worst_hard_margin_frac": float(_min_margin_frac) if _min_margin_frac == _min_margin_frac else float("nan"),
            "n_failed": int(len(hard_fails)),
            "top_blocker": (
                getattr(hard_fails[0], "name", None)
                if hard_fails
                else (vs.get("dominant") if not ok else None)
            ),
        }
        return ("PASS" if ok else "FAIL"), score, evidence

    b1 = int(max(1, round(float(budget) * (1.0 - float(stage2_budget_frac)))))
    b2 = int(max(0, round(float(budget) * float(stage2_budget_frac))))
    bs = int(max(0, round(float(budget) * float(surr_frac)))) if insert_surr else 0
    b2 = int(min(int(b2), int(max(0, budget - 1))))
    bs = int(min(int(bs), int(max(0, budget - 1 - b2))))
    b1 = int(max(1, int(budget) - int(b2) - int(bs)))

    stages = [SearchStage(name="stage1", method=str(method), budget=int(b1), seed=int(seed), local_refine=False)]
    if insert_surr and bs > 0:
        stages.append(
            SearchStage(
                name="surrogate",
                method="surrogate",
                budget=int(bs),
                seed=int(seed + 1),
                local_refine=False,
                surrogate_pool_mult=int(surr_pool_mult),
                surrogate_kappa=float(surr_kappa),
                surrogate_ridge_alpha=float(surr_ridge),
                surrogate_feas_margin_key="min_margin_frac",
            )
        )
    if two_stage and b2 > 0:
        stages.append(
            SearchStage(
                name="stage2",
                method=str(stage2_method),
                budget=int(b2),
                seed=int(seed + (2 if (insert_surr and bs > 0) else 1)),
                local_refine=True,
                local_shrink=float(stage2_shrink),
            )
        )

    spec = OrchestratorSpec(variables=tuple(vars_), stages=tuple(stages))
    if mode == "pareto":
        objs = [
            ParetoObjective(key=str(o["key"]), sense=str(o["sense"]))
            for o in (pareto_objectives or [{"key": "R0_m", "sense": "min"}])
        ]

        def _eval_fn(inp_obj):
            return ui_evaluate(inp_obj, origin="pareto_frontier_v405")

        def _cons_fn(out_obj, inp_obj):
            """Serialize constraints so soft/diagnostic fails do not reject candidates."""
            try:
                from constraints.constraints import constraint_is_hard
            except ImportError:
                from src.constraints.constraints import constraint_is_hard  # type: ignore

            cons = evaluate_constraints(out_obj, point_inputs=inp_obj)
            rows = []
            for c in cons or []:
                hard = constraint_is_hard(c)
                soft_fail = not bool(getattr(c, "passed", True))
                # Orchestrator treats any failed=True as REJECTED — only mark hard fails.
                rows.append(
                    {
                        "name": getattr(c, "name", ""),
                        "failed": bool(soft_fail and hard),
                        "passed": not (soft_fail and hard),
                        "severity": "hard" if hard else str(getattr(c, "severity", "diagnostic")),
                    }
                )
            return rows

        return run_orchestrated_certified_pareto_search(
            base_inputs=base,
            spec=spec,
            objectives=objs,
            builder=_builder,
            evaluator_fn=_eval_fn,
            constraints_fn=_cons_fn,
            max_frontier=int(max_frontier),
            filter_mirage=bool(filter_mirage),
        )

    return run_orchestrated_certified_search(base, spec, verifier=_verifier, builder=_builder)


def validation_envelope_report(envelope_name: str, outputs: dict) -> Dict[str, Any]:
    from validation.envelopes import default_envelopes

    envs = default_envelopes()
    env = envs[envelope_name]
    report = env.check(outputs)
    rows = []
    n_fail = 0
    for k, r in report.items():
        if not r.get("ok"):
            n_fail += 1
        rows.append(
            {
                "metric": k,
                "value": r.get("value"),
                "lo": r.get("lo"),
                "hi": r.get("hi"),
                "ok": bool(r.get("ok")),
            }
        )
    return {"envelope": envelope_name, "notes": env.notes, "rows": rows, "n_fail": n_fail}


def constraint_provenance_rows(art: dict) -> List[Dict[str, Any]]:
    cons = art.get("constraints") if isinstance(art.get("constraints"), list) else []
    rows: List[Dict[str, Any]] = []
    for c in cons:
        if not isinstance(c, dict):
            continue
        rows.append(
            {
                "group": c.get("group", c.get("mechanism_group")),
                "name": c.get("name", c.get("id")),
                "failed": c.get("failed"),
                "soft_failed": c.get("soft_failed"),
                "severity": c.get("severity"),
                "value": c.get("value"),
                "limit": c.get("limit"),
                "margin": c.get("margin"),
                "margin_frac": c.get("margin_frac"),
                "units": c.get("units"),
                "fingerprint": c.get("fingerprint"),
                "provenance_fingerprint": c.get("provenance_fingerprint"),
                "maturity": c.get("maturity"),
            }
        )
    return rows
