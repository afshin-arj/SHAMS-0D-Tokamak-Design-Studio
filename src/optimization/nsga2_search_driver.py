"""NSGA-II / MOEA SearchDriver — Certified Optimizer Phase 3.1.

Propose-only multi-objective search **outside** L0. The driver:

* Proposes ``PointInputs`` only (never mutates ``Evaluator`` / ``hot_ion``).
* Scores FoMs from a hashed ``multi_objective_contract.v1`` (list of
  ``objective_contract.v1``) — never inside physics truth.
* Feasible-first constrained domination (hard constraints =
  SHAMS-evaluated governance filters; **no soft negotiation**).
* Pure-Python NSGA-II (seeded) as ``nsga2_fallback``; optional ``pymoo``
  backend as ``nsga2`` when installed (not a required dependency).
* Reuses ``solvers.optimize.dominates`` / ``pareto_front`` for nondominated
  filtering — does not reinvent Pareto algebra.
* Emits stamp-ready shortlist + CCFS hooks; atlas-on-dominatees is Phase 3.2
  (hook reserved below).

Driver ids: ``nsga2`` | ``nsga2_fallback``.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from src.optimization.objective_contract import (
    MULTI_SCHEMA,
    MultiObjectiveContract,
    ObjectiveContract,
    ObjectiveContractError,
    build_multi_objective_contract,
    from_registry_name,
    parse_multi_objective_contract,
)
from src.optimization.opt_run_stamp import (
    DRIVER_NSGA2,
    DRIVER_NSGA2_FALLBACK,
    build_opt_run_stamp,
)

SCHEMA = "nsga2_search_result.v1"
ATLAS_DOMINATEE_HOOK_SCHEMA = "atlas_dominatee_hook.v1"

# Phase 3.2 will annotate dominated / REJECTED rows with atlas mechanisms.
ATLAS_DOMINATEE_HOOK: Dict[str, Any] = {
    "schema": ATLAS_DOMINATEE_HOOK_SCHEMA,
    "status": "pending_phase_3_2",
    "note": (
        "Dominated / REJECTED candidates will carry no_solution_atlas.v1 "
        "dominant hard mechanism in ticket 3.2 — not shipped in 3.1."
    ),
}

DEFAULT_VARIABLE_BOUNDS: Dict[str, Tuple[float, float]] = {
    "Ip_MA": (4.0, 12.0),
    "fG": (0.4, 1.1),
    "Paux_MW": (5.0, 80.0),
}

DEFAULT_POP_SIZE = 12
DEFAULT_N_GENERATIONS = 5
DEFAULT_SHORTLIST_K = 8


class Nsga2SearchDriverError(ValueError):
    """Invalid NSGA-II SearchDriver configuration or result."""


def pymoo_available() -> bool:
    """True when optional ``pymoo`` can be imported (not a required dep)."""
    try:
        import pymoo  # noqa: F401

        return True
    except Exception:
        return False


def _as_multi_contract(
    contract: Union[
        MultiObjectiveContract,
        Mapping[str, Any],
        Sequence[Union[ObjectiveContract, Mapping[str, Any]]],
    ],
) -> MultiObjectiveContract:
    if isinstance(contract, MultiObjectiveContract):
        return contract
    if isinstance(contract, Mapping):
        schema = str(contract.get("schema", "")).strip()
        if schema == MULTI_SCHEMA:
            return parse_multi_objective_contract(contract)
        # Single contract mapping is not enough for MOEA.
        raise Nsga2SearchDriverError(
            f"expected {MULTI_SCHEMA} mapping or a sequence of ObjectiveContracts; "
            f"got schema={schema!r}"
        )
    if isinstance(contract, (list, tuple)):
        try:
            return build_multi_objective_contract(list(contract))
        except ObjectiveContractError as exc:
            raise Nsga2SearchDriverError(str(exc)) from exc
    raise Nsga2SearchDriverError(
        "objective_contracts must be MultiObjectiveContract, "
        "multi_objective_contract.v1 mapping, or a sequence of contracts"
    )


def _normalize_bounds(
    variables: Optional[Mapping[str, Tuple[float, float]]],
) -> Dict[str, Tuple[float, float]]:
    raw = dict(variables) if variables is not None else dict(DEFAULT_VARIABLE_BOUNDS)
    if not raw:
        raise Nsga2SearchDriverError("variables must be a non-empty bounds map")
    out: Dict[str, Tuple[float, float]] = {}
    for name, pair in raw.items():
        key = str(name).strip()
        if not key:
            raise Nsga2SearchDriverError("variable names must be non-empty")
        try:
            lo, hi = float(pair[0]), float(pair[1])
        except Exception as exc:
            raise Nsga2SearchDriverError(
                f"bounds for {key!r} must be (lo, hi) floats; got {pair!r}"
            ) from exc
        if not (math.isfinite(lo) and math.isfinite(hi)):
            raise Nsga2SearchDriverError(f"bounds for {key!r} must be finite")
        if hi < lo:
            raise Nsga2SearchDriverError(f"bounds for {key!r}: hi < lo ({hi} < {lo})")
        out[key] = (lo, hi)
    return out


def _point_to_dict(inp: Any) -> Dict[str, Any]:
    if hasattr(inp, "__dict__"):
        return dict(inp.__dict__)
    if isinstance(inp, Mapping):
        return dict(inp)
    raise Nsga2SearchDriverError("base must be PointInputs or a mapping")


def _as_point_inputs(base: Any):
    try:
        from models.inputs import PointInputs  # type: ignore
    except ImportError:
        from src.models.inputs import PointInputs  # type: ignore

    if isinstance(base, PointInputs):
        return base
    if isinstance(base, Mapping):
        return PointInputs(**dict(base))
    raise Nsga2SearchDriverError("base must be PointInputs or a mapping of fields")


def _apply_x(base: Any, names: Sequence[str], x: Sequence[float]) -> Any:
    updates = {name: float(val) for name, val in zip(names, x)}
    return replace(base, **updates)


def _clip(x: Sequence[float], bounds: Sequence[Tuple[float, float]]) -> List[float]:
    return [min(hi, max(lo, float(xi))) for xi, (lo, hi) in zip(x, bounds)]


_EVALUATOR = None


def _evaluate_outputs(inp: Any, *, origin: str) -> Dict[str, Any]:
    """Frozen choke-point eval for search guidance (propose-only; not CCFS)."""
    global _EVALUATOR
    try:
        from evaluator.core import Evaluator  # type: ignore
    except ImportError:
        from src.evaluator.core import Evaluator  # type: ignore

    if _EVALUATOR is None:
        _EVALUATOR = Evaluator(label=str(origin), cache_enabled=True)
    res = _EVALUATOR.evaluate(inp)
    out = getattr(res, "out", None)
    return dict(out) if isinstance(out, dict) else {}


def _hard_feasible(out: Mapping[str, Any]) -> bool:
    """SHAMS-evaluated hard filter — no soft negotiation."""
    try:
        from constraints.unified import build_all_constraints  # type: ignore
    except ImportError:
        from src.constraints.unified import build_all_constraints  # type: ignore

    bundle = build_all_constraints(dict(out))
    return bool(getattr(bundle, "governance_feasible", False))


def _metric_vector(
    out: Mapping[str, Any],
    multi: MultiObjectiveContract,
) -> Dict[str, float]:
    vals: Dict[str, float] = {}
    for oc in multi.objectives:
        key = oc.primary_metric_key()
        raw = out.get(key)
        if raw is None and len(oc.metric_keys) > 1:
            for k in oc.metric_keys[1:]:
                if out.get(k) is not None:
                    raw = out.get(k)
                    break
        try:
            v = float(raw)  # type: ignore[arg-type]
        except Exception:
            v = float("nan")
        if not math.isfinite(v):
            v = float("nan")
        vals[key] = v
    return vals


def _constraint_violation(out: Mapping[str, Any]) -> float:
    """Non-negative violation measure for constrained domination (infeasible only)."""
    try:
        from constraints.unified import build_all_constraints  # type: ignore
        from constraints.constraints import constraint_is_hard  # type: ignore
    except ImportError:
        from src.constraints.unified import build_all_constraints  # type: ignore
        from src.constraints.constraints import constraint_is_hard  # type: ignore

    bundle = build_all_constraints(dict(out))
    viol = 0.0
    for c in list(getattr(bundle, "governance", []) or []):
        if not constraint_is_hard(c):
            continue
        if bool(getattr(c, "passed", False)):
            continue
        mf = getattr(c, "margin_frac", None)
        if mf is None:
            viol += 1.0
        else:
            try:
                viol += max(0.0, -float(mf))
            except Exception:
                viol += 1.0
    return float(viol)


def _import_dominates():
    try:
        from solvers.optimize import dominates  # type: ignore
    except ImportError:
        from src.solvers.optimize import dominates  # type: ignore
    return dominates


def _import_pareto_front():
    try:
        from solvers.optimize import pareto_front  # type: ignore
    except ImportError:
        from src.solvers.optimize import pareto_front  # type: ignore
    return pareto_front


def _constrained_dominates(
    a: Mapping[str, Any],
    b: Mapping[str, Any],
    objectives: Mapping[str, str],
) -> bool:
    """Feasible-first constrained domination (Deb et al. style)."""
    fa = bool(a.get("feasible"))
    fb = bool(b.get("feasible"))
    if fa and not fb:
        return True
    if not fa and fb:
        return False
    if not fa and not fb:
        return float(a.get("violation", 0.0)) < float(b.get("violation", 0.0))
    # Both feasible: reuse existing Pareto dominates helper.
    dominates = _import_dominates()
    return bool(dominates(dict(a.get("metrics") or {}), dict(b.get("metrics") or {}), dict(objectives)))


@dataclass(frozen=True)
class ProposedCandidate:
    """One propose-only multi-objective candidate (not yet CCFS-certified)."""

    id: str
    inputs: Dict[str, Any]
    proposed_metrics: Dict[str, Optional[float]]
    hard_feasible_filter: bool
    rank: int
    crowding_distance: float
    front_rank: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "inputs": dict(self.inputs),
            "proposed_metrics": dict(self.proposed_metrics),
            "hard_feasible_filter": bool(self.hard_feasible_filter),
            "rank": int(self.rank),
            "crowding_distance": float(self.crowding_distance),
            "front_rank": int(self.front_rank),
            "certification": "propose_only",
        }


@dataclass(frozen=True)
class Nsga2SearchResult:
    """Stamp-ready multi-objective SearchDriver result (Phase 3.1)."""

    search_driver_id: str
    multi_objective_contract: Dict[str, Any]
    objective_contract_hash: str
    seed: int
    n_evals: int
    pymoo_used: bool
    variable_names: Tuple[str, ...]
    bounds: Dict[str, Tuple[float, float]]
    candidates: Tuple[ProposedCandidate, ...]
    proposed_front: Tuple[ProposedCandidate, ...]
    schema: str = SCHEMA
    notes: str = ""
    atlas_dominatee_hook: Dict[str, Any] = field(
        default_factory=lambda: dict(ATLAS_DOMINATEE_HOOK)
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": SCHEMA,
            "search_driver_id": self.search_driver_id,
            "multi_objective_contract": dict(self.multi_objective_contract),
            "objective_contract_hash": self.objective_contract_hash,
            "seed": int(self.seed),
            "n_evals": int(self.n_evals),
            "pymoo_used": bool(self.pymoo_used),
            "variable_names": list(self.variable_names),
            "bounds": {k: [float(lo), float(hi)] for k, (lo, hi) in self.bounds.items()},
            "candidates": [c.to_dict() for c in self.candidates],
            "proposed_front": [c.to_dict() for c in self.proposed_front],
            "notes": self.notes,
            "propose_only": True,
            "certification_required": "CCFS",
            "atlas_dominatee_hook": dict(self.atlas_dominatee_hook or ATLAS_DOMINATEE_HOOK),
            "feasible_first": True,
        }

    def to_ccfs_bundle(self) -> Dict[str, Any]:
        """CandidateBatch as ``ccfs_bundle.v1`` for CCFS certification."""
        cands = []
        for c in self.candidates:
            cands.append(
                {
                    "id": c.id,
                    "inputs": dict(c.inputs),
                    "claims": {
                        "proposed_metrics": dict(c.proposed_metrics),
                        "hard_feasible_filter": c.hard_feasible_filter,
                        "front_rank": c.front_rank,
                        "search_driver_id": self.search_driver_id,
                        "status": "PROPOSED",
                    },
                }
            )
        return {
            "schema_version": "ccfs_bundle.v1",
            "candidates": cands,
            "opt_run": {
                "multi_objective_contract": dict(self.multi_objective_contract),
                "objective_contract_hash": self.objective_contract_hash,
                "seed": int(self.seed),
                "search_driver_id": self.search_driver_id,
            },
            "atlas_dominatee_hook": dict(self.atlas_dominatee_hook or ATLAS_DOMINATEE_HOOK),
        }

    def stamp_ready(
        self,
        *,
        n_verified: int = 0,
        n_rejected: int = 0,
        shams_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build ``opt_run_stamp.v1`` for the proposal shortlist (pre-CCFS counts)."""
        stamp = build_opt_run_stamp(
            search_driver_id=self.search_driver_id,
            n_candidates=len(self.candidates),
            n_verified=n_verified,
            n_rejected=n_rejected,
            objective_contract_hash=self.objective_contract_hash,
            seed=self.seed,
            shams_version=shams_version,
        )
        return stamp.to_dict()

    def to_frontier_candidate_rows(self) -> List[Dict[str, Any]]:
        """Rows compatible with frontier-intake style candidate lists (propose-only)."""
        rows: List[Dict[str, Any]] = []
        for c in self.candidates:
            row: Dict[str, Any] = {
                "id": c.id,
                "inputs": dict(c.inputs),
                "feasible": bool(c.hard_feasible_filter),
                "in_proposed_front": c.id in {p.id for p in self.proposed_front},
                "front_rank": int(c.front_rank),
                "certification": "propose_only",
            }
            for k, v in c.proposed_metrics.items():
                row[k] = v
            rows.append(row)
        return rows


def _fast_nondominated_sort(
    individuals: List[Dict[str, Any]],
    objectives: Mapping[str, str],
) -> List[List[int]]:
    """NSGA-II fast nondominated sort using constrained domination."""
    n = len(individuals)
    S: List[List[int]] = [[] for _ in range(n)]
    n_dom = [0] * n
    fronts: List[List[int]] = [[]]

    for p in range(n):
        for q in range(n):
            if p == q:
                continue
            if _constrained_dominates(individuals[p], individuals[q], objectives):
                S[p].append(q)
            elif _constrained_dominates(individuals[q], individuals[p], objectives):
                n_dom[p] += 1
        if n_dom[p] == 0:
            individuals[p]["front_rank"] = 0
            fronts[0].append(p)

    i = 0
    while fronts[i]:
        nxt: List[int] = []
        for p in fronts[i]:
            for q in S[p]:
                n_dom[q] -= 1
                if n_dom[q] == 0:
                    individuals[q]["front_rank"] = i + 1
                    nxt.append(q)
        i += 1
        fronts.append(nxt)
    return fronts[:-1]


def _crowding_distance(
    individuals: List[Dict[str, Any]],
    front: Sequence[int],
    objectives: Mapping[str, str],
) -> None:
    """Assign crowding_distance on individuals for indices in ``front``."""
    if not front:
        return
    for idx in front:
        individuals[idx]["crowding_distance"] = 0.0
    keys = list(objectives.keys())
    for key in keys:
        sorted_idx = sorted(
            front,
            key=lambda i: float((individuals[i].get("metrics") or {}).get(key, float("nan"))),
        )
        individuals[sorted_idx[0]]["crowding_distance"] = float("inf")
        individuals[sorted_idx[-1]]["crowding_distance"] = float("inf")
        vals = [
            float((individuals[i].get("metrics") or {}).get(key, float("nan")))
            for i in sorted_idx
        ]
        finite = [v for v in vals if math.isfinite(v)]
        if len(finite) < 2:
            continue
        span = max(finite) - min(finite)
        if span <= 0.0:
            continue
        for j in range(1, len(sorted_idx) - 1):
            if not (math.isfinite(vals[j - 1]) and math.isfinite(vals[j + 1])):
                continue
            individuals[sorted_idx[j]]["crowding_distance"] = float(
                individuals[sorted_idx[j]]["crowding_distance"]
            ) + (vals[j + 1] - vals[j - 1]) / span


def _tournament(
    rng: random.Random,
    individuals: List[Dict[str, Any]],
) -> Dict[str, Any]:
    i, j = rng.randrange(len(individuals)), rng.randrange(len(individuals))
    a, b = individuals[i], individuals[j]
    ra, rb = int(a.get("front_rank", 10**9)), int(b.get("front_rank", 10**9))
    if ra < rb:
        return a
    if rb < ra:
        return b
    if float(a.get("crowding_distance", 0.0)) > float(b.get("crowding_distance", 0.0)):
        return a
    if float(b.get("crowding_distance", 0.0)) > float(a.get("crowding_distance", 0.0)):
        return b
    return a if rng.random() < 0.5 else b


def _sbx_crossover(
    rng: random.Random,
    p1: Sequence[float],
    p2: Sequence[float],
    bound_pairs: Sequence[Tuple[float, float]],
    *,
    eta: float = 15.0,
) -> Tuple[List[float], List[float]]:
    c1, c2 = list(p1), list(p2)
    if rng.random() > 0.9:
        return _clip(c1, bound_pairs), _clip(c2, bound_pairs)
    for i, (lo, hi) in enumerate(bound_pairs):
        if abs(p1[i] - p2[i]) < 1e-14:
            continue
        u = rng.random()
        if u <= 0.5:
            beta = (2.0 * u) ** (1.0 / (eta + 1.0))
        else:
            beta = (1.0 / (2.0 * (1.0 - u))) ** (1.0 / (eta + 1.0))
        c1[i] = 0.5 * ((1.0 + beta) * p1[i] + (1.0 - beta) * p2[i])
        c2[i] = 0.5 * ((1.0 - beta) * p1[i] + (1.0 + beta) * p2[i])
    return _clip(c1, bound_pairs), _clip(c2, bound_pairs)


def _poly_mutation(
    rng: random.Random,
    x: Sequence[float],
    bound_pairs: Sequence[Tuple[float, float]],
    *,
    eta: float = 20.0,
    prob: Optional[float] = None,
) -> List[float]:
    y = list(x)
    dim = len(y)
    p = (1.0 / dim) if prob is None else float(prob)
    for i, (lo, hi) in enumerate(bound_pairs):
        if rng.random() > p:
            continue
        span = hi - lo
        if span <= 0.0:
            continue
        u = rng.random()
        if u < 0.5:
            delta = (2.0 * u) ** (1.0 / (eta + 1.0)) - 1.0
        else:
            delta = 1.0 - (2.0 * (1.0 - u)) ** (1.0 / (eta + 1.0))
        y[i] = y[i] + delta * span
    return _clip(y, bound_pairs)


def _eval_individual(
    *,
    x: Sequence[float],
    names: Sequence[str],
    bound_pairs: Sequence[Tuple[float, float]],
    base: Any,
    multi: MultiObjectiveContract,
    origin: str,
    eval_counter: List[int],
) -> Dict[str, Any]:
    xc = _clip(x, bound_pairs)
    inp = _apply_x(base, names, xc)
    out = _evaluate_outputs(inp, origin=origin)
    eval_counter[0] += 1
    feas = _hard_feasible(out)
    metrics = _metric_vector(out, multi)
    viol = 0.0 if feas else _constraint_violation(out)
    return {
        "x": list(xc),
        "inputs": _point_to_dict(inp),
        "metrics": metrics,
        "feasible": feas,
        "violation": float(viol),
        "front_rank": 10**9,
        "crowding_distance": 0.0,
    }


def _select_next_generation(
    combined: List[Dict[str, Any]],
    pop_size: int,
    objectives: Mapping[str, str],
) -> List[Dict[str, Any]]:
    fronts = _fast_nondominated_sort(combined, objectives)
    for fr in fronts:
        _crowding_distance(combined, fr, objectives)
    next_pop: List[Dict[str, Any]] = []
    for fr in fronts:
        if len(next_pop) + len(fr) <= pop_size:
            next_pop.extend(combined[i] for i in fr)
        else:
            remaining = pop_size - len(next_pop)
            ordered = sorted(
                fr,
                key=lambda i: float(combined[i].get("crowding_distance", 0.0)),
                reverse=True,
            )
            next_pop.extend(combined[i] for i in ordered[:remaining])
            break
    return next_pop


def _run_nsga2_fallback(
    *,
    x0: List[float],
    bound_pairs: List[Tuple[float, float]],
    names: Sequence[str],
    base: Any,
    multi: MultiObjectiveContract,
    seed: int,
    pop_size: int,
    n_generations: int,
    origin: str,
    eval_counter: List[int],
) -> List[Dict[str, Any]]:
    """Deterministic pure-Python NSGA-II (no pymoo / SciPy)."""
    rng = random.Random(int(seed))
    objectives = multi.metric_senses()
    dim = len(x0)

    def _random_x() -> List[float]:
        return [
            lo + (hi - lo) * rng.random()
            for (lo, hi) in bound_pairs
        ]

    population: List[Dict[str, Any]] = []
    # Seed population with clipped baseline + random individuals.
    population.append(
        _eval_individual(
            x=x0,
            names=names,
            bound_pairs=bound_pairs,
            base=base,
            multi=multi,
            origin=origin,
            eval_counter=eval_counter,
        )
    )
    while len(population) < pop_size:
        population.append(
            _eval_individual(
                x=_random_x(),
                names=names,
                bound_pairs=bound_pairs,
                base=base,
                multi=multi,
                origin=origin,
                eval_counter=eval_counter,
            )
        )

    fronts0 = _fast_nondominated_sort(population, objectives)
    for fr in fronts0:
        _crowding_distance(population, fr, objectives)

    for _gen in range(max(0, int(n_generations))):
        offspring: List[Dict[str, Any]] = []
        while len(offspring) < pop_size:
            p1 = _tournament(rng, population)
            p2 = _tournament(rng, population)
            c1x, c2x = _sbx_crossover(rng, p1["x"], p2["x"], bound_pairs)
            c1x = _poly_mutation(rng, c1x, bound_pairs)
            c2x = _poly_mutation(rng, c2x, bound_pairs)
            offspring.append(
                _eval_individual(
                    x=c1x,
                    names=names,
                    bound_pairs=bound_pairs,
                    base=base,
                    multi=multi,
                    origin=origin,
                    eval_counter=eval_counter,
                )
            )
            if len(offspring) < pop_size:
                offspring.append(
                    _eval_individual(
                        x=c2x,
                        names=names,
                        bound_pairs=bound_pairs,
                        base=base,
                        multi=multi,
                        origin=origin,
                        eval_counter=eval_counter,
                    )
                )
        combined = population + offspring
        population = _select_next_generation(combined, pop_size, objectives)

    # Final ranking for export.
    fronts = _fast_nondominated_sort(population, objectives)
    for fr in fronts:
        _crowding_distance(population, fr, objectives)
    return population


def _try_pymoo_nsga2(
    *,
    x0: List[float],
    bound_pairs: List[Tuple[float, float]],
    names: Sequence[str],
    base: Any,
    multi: MultiObjectiveContract,
    seed: int,
    pop_size: int,
    n_generations: int,
    origin: str,
    eval_counter: List[int],
) -> Optional[List[Dict[str, Any]]]:
    """Optional pymoo NSGA-II; returns None if unavailable or on failure."""
    if not pymoo_available():
        return None
    try:
        import numpy as np
        from pymoo.algorithms.moo.nsga2 import NSGA2
        from pymoo.core.problem import ElementwiseProblem
        from pymoo.operators.crossover.sbx import SBX
        from pymoo.operators.mutation.pm import PM
        from pymoo.operators.sampling.rnd import FloatRandomSampling
        from pymoo.optimize import minimize
        from pymoo.termination import get_termination
    except Exception:
        return None

    objectives = multi.metric_senses()
    metric_keys = list(objectives.keys())
    n_obj = len(metric_keys)
    xl = np.array([lo for lo, _ in bound_pairs], dtype=float)
    xu = np.array([hi for _, hi in bound_pairs], dtype=float)
    archive: List[Dict[str, Any]] = []

    class _Problem(ElementwiseProblem):
        def __init__(self) -> None:
            super().__init__(n_var=len(x0), n_obj=n_obj, n_ieq_constr=1, xl=xl, xu=xu)

        def _evaluate(self, x, out, *args, **kwargs):  # noqa: ANN001
            ind = _eval_individual(
                x=list(x),
                names=names,
                bound_pairs=bound_pairs,
                base=base,
                multi=multi,
                origin=origin,
                eval_counter=eval_counter,
            )
            archive.append(ind)
            f = []
            for key in metric_keys:
                v = float(ind["metrics"].get(key, float("nan")))
                sense = objectives[key]
                if not math.isfinite(v):
                    f.append(1.0e12)
                elif sense == "max":
                    f.append(-v)
                else:
                    f.append(v)
            out["F"] = np.array(f, dtype=float)
            # g <= 0 feasible in pymoo; violation > 0 → infeasible
            out["G"] = np.array([float(ind["violation"]) if not ind["feasible"] else -1.0])

    try:
        algo = NSGA2(
            pop_size=int(pop_size),
            sampling=FloatRandomSampling(),
            crossover=SBX(prob=0.9, eta=15),
            mutation=PM(eta=20),
            eliminate_duplicates=True,
        )
        problem = _Problem()
        minimize(
            problem,
            algo,
            get_termination("n_gen", int(max(1, n_generations))),
            seed=int(seed),
            verbose=False,
        )
    except Exception:
        return None

    if not archive:
        return None
    # Deduplicate by rounded x and re-rank with our constrained sort.
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for row in archive:
        key = tuple(round(float(v), 8) for v in row["x"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(row)
    fronts = _fast_nondominated_sort(uniq, objectives)
    for fr in fronts:
        _crowding_distance(uniq, fr, objectives)
    # Keep best pop_size by front then crowding.
    return _select_next_generation(uniq, pop_size, objectives)


def run_nsga2_search(
    base: Any,
    objective_contracts: Union[
        MultiObjectiveContract,
        Mapping[str, Any],
        Sequence[Union[ObjectiveContract, Mapping[str, Any]]],
    ],
    *,
    variables: Optional[Mapping[str, Tuple[float, float]]] = None,
    seed: Optional[int] = None,
    pop_size: int = DEFAULT_POP_SIZE,
    n_generations: int = DEFAULT_N_GENERATIONS,
    shortlist_k: int = DEFAULT_SHORTLIST_K,
    force_fallback: bool = False,
    prefer_feasible_front: bool = True,
    origin: str = "nsga2_search_driver",
) -> Nsga2SearchResult:
    """Run feasible-first NSGA-II-style search; return propose-only shortlist.

    Parameters
    ----------
    base:
        Baseline ``PointInputs`` (or field mapping).
    objective_contracts:
        ``MultiObjectiveContract``, ``multi_objective_contract.v1`` mapping,
        or a sequence of at least two ``ObjectiveContract`` / mappings.
    variables:
        Continuous ``{name: (lo, hi)}`` bounds.
    seed:
        Reproducibility seed (required when multi-contract seed_policy is
        ``required`` / ``fixed``).
    pop_size / n_generations:
        NSGA-II population and generation budget.
    shortlist_k:
        Max proposals retained for CCFS (feasible front preferred).
    force_fallback:
        Skip optional pymoo even when installed (lock-tests the pure-Python path).
    prefer_feasible_front:
        Prefer hard-feasible nondominated proposals when building shortlist.
    """
    multi = _as_multi_contract(objective_contracts)
    bounds = _normalize_bounds(variables)
    names = tuple(sorted(bounds.keys()))
    bound_pairs = [bounds[n] for n in names]
    base_inp = _as_point_inputs(base)
    objectives = multi.metric_senses()

    if seed is None:
        seed = multi.seed
    if seed is None:
        if multi.seed_policy in ("required", "fixed"):
            raise Nsga2SearchDriverError(
                f"seed required by multi_objective_contract seed_policy={multi.seed_policy!r}"
            )
        seed = 0
    seed = int(seed)

    x0: List[float] = []
    for n, (lo, hi) in zip(names, bound_pairs):
        try:
            v = float(getattr(base_inp, n))
        except Exception:
            v = 0.5 * (lo + hi)
        x0.append(min(hi, max(lo, v)))

    eval_counter = [0]
    pop_n = max(4, int(pop_size))
    n_gen = max(0, int(n_generations))
    pymoo_used = False
    population: Optional[List[Dict[str, Any]]] = None

    if (not force_fallback) and pymoo_available():
        population = _try_pymoo_nsga2(
            x0=x0,
            bound_pairs=bound_pairs,
            names=names,
            base=base_inp,
            multi=multi,
            seed=seed,
            pop_size=pop_n,
            n_generations=n_gen,
            origin=origin,
            eval_counter=eval_counter,
        )
        if population is not None:
            pymoo_used = True

    if population is None:
        population = _run_nsga2_fallback(
            x0=x0,
            bound_pairs=bound_pairs,
            names=names,
            base=base_inp,
            multi=multi,
            seed=seed,
            pop_size=pop_n,
            n_generations=n_gen,
            origin=origin,
            eval_counter=eval_counter,
        )
        pymoo_used = False

    # Build shortlist: prefer front_rank==0 (and feasible if requested).
    def _x_key(row: Mapping[str, Any]) -> Tuple[float, ...]:
        return tuple(round(float(v), 8) for v in row.get("x", []))

    ranked = sorted(
        population,
        key=lambda r: (
            (not bool(r.get("feasible"))) if prefer_feasible_front else False,
            int(r.get("front_rank", 10**9)),
            -float(r.get("crowding_distance", 0.0)),
        ),
    )
    seen = set()
    picked: List[Dict[str, Any]] = []
    for row in ranked:
        k = _x_key(row)
        if k in seen:
            continue
        seen.add(k)
        picked.append(row)
        if len(picked) >= max(1, int(shortlist_k)):
            break

    # Proposed front = nondominated among shortlist (reuse pareto_front helper
    # for feasible metric rows; fall back to front_rank==0).
    pareto_front = _import_pareto_front()
    feasible_metric_rows = [
        {**dict(r.get("metrics") or {}), "_idx": i}
        for i, r in enumerate(picked)
        if bool(r.get("feasible"))
        and all(math.isfinite(float(v)) for v in (r.get("metrics") or {}).values())
    ]
    front_idxs: set = set()
    if feasible_metric_rows:
        front_rows = pareto_front(feasible_metric_rows, dict(objectives))
        front_idxs = {int(r["_idx"]) for r in front_rows}
    else:
        front_idxs = {i for i, r in enumerate(picked) if int(r.get("front_rank", 1)) == 0}

    candidates: List[ProposedCandidate] = []
    proposed_front: List[ProposedCandidate] = []
    for i, row in enumerate(picked):
        metrics_raw = dict(row.get("metrics") or {})
        proposed_metrics = {
            k: (None if not math.isfinite(float(v)) else float(v))
            for k, v in metrics_raw.items()
        }
        cand = ProposedCandidate(
            id=f"nsga2_{i:04d}",
            inputs=dict(row["inputs"]),
            proposed_metrics=proposed_metrics,
            hard_feasible_filter=bool(row.get("feasible")),
            rank=i,
            crowding_distance=float(row.get("crowding_distance", 0.0)),
            front_rank=int(row.get("front_rank", 10**9)),
        )
        candidates.append(cand)
        if i in front_idxs:
            proposed_front.append(cand)

    driver_id = DRIVER_NSGA2 if pymoo_used else DRIVER_NSGA2_FALLBACK
    notes = (
        "Propose-only NSGA-II / MOEA SearchDriver. Metric vectors are uncertified; "
        "run CCFS / frozen Evaluator for VERIFIED vs REJECTED. "
        "Hard constraints used as SHAMS-evaluated feasible-first filters only. "
        "Atlas-annotated dominatees deferred to Phase 3.2."
    )
    return Nsga2SearchResult(
        search_driver_id=driver_id,
        multi_objective_contract=multi.to_dict(),
        objective_contract_hash=multi.hash_sha256(),
        seed=seed,
        n_evals=int(eval_counter[0]),
        pymoo_used=bool(pymoo_used),
        variable_names=names,
        bounds=bounds,
        candidates=tuple(candidates),
        proposed_front=tuple(proposed_front),
        notes=notes,
        atlas_dominatee_hook=dict(ATLAS_DOMINATEE_HOOK),
    )


def lightly_certify_shortlist(
    result: Nsga2SearchResult,
    *,
    attach_opt_run_stamp: bool = True,
) -> Dict[str, Any]:
    """Light CCFS pass on the proposal shortlist (no atlas dominatee expand yet)."""
    bundle = result.to_ccfs_bundle()
    if not bundle.get("candidates"):
        raise Nsga2SearchDriverError("no candidates to certify")
    try:
        from extopt.certified_solve import verify_ccfs_bundle  # type: ignore
    except ImportError:
        from src.extopt.certified_solve import verify_ccfs_bundle  # type: ignore

    return verify_ccfs_bundle(
        bundle,
        opt_run=bundle.get("opt_run"),
        attach_opt_run_stamp=attach_opt_run_stamp,
    )


def multi_contract_from_registry(
    names: Sequence[str],
    *,
    seed: int,
    bundle_name: str = "nsga2_multi",
    notes: str = "",
) -> MultiObjectiveContract:
    """Bridge registry FoM names → ``multi_objective_contract.v1`` with fixed seed."""
    objs: List[ObjectiveContract] = []
    for name in names:
        try:
            objs.append(
                from_registry_name(
                    name,
                    seed_policy="fixed",
                    seed=int(seed),
                    notes=f"NSGA-II FoM={name}",
                    provenance={"source": "nsga2_search_driver", "role": "propose_only"},
                )
            )
        except ObjectiveContractError as exc:
            raise Nsga2SearchDriverError(str(exc)) from exc
    try:
        return build_multi_objective_contract(
            objs,
            name=bundle_name,
            seed_policy="fixed",
            seed=int(seed),
            notes=notes or f"NSGA-II multi FoM={list(names)}",
        )
    except ObjectiveContractError as exc:
        raise Nsga2SearchDriverError(str(exc)) from exc
