from __future__ import annotations
"""Constrained optimization helpers (PROCESS-like studies).

SHAMS supports lightweight optimization on top of the constraint solver:
- random / LHS sampling within bounds
- constraint filtering
- Pareto front extraction for multi-objective exploration

This is not intended to be a full optimizer replacement; it's a pragmatic tool for early design space
exploration with transparent behavior.
"""
import random
import os
from dataclasses import replace
from typing import Callable, Dict, List, Tuple, Optional

from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from constraints.system import build_constraints_from_outputs
from optimization.objectives import get_objective, list_objectives

def default_objectives() -> Dict[str, str]:
    """Default Pareto objective senses."""
    return {"R0_m": "min", "B_peak_T": "min", "P_e_net_MW": "max"}


def default_objective(out: Dict[str, float], name: str) -> float:
    """Compute an objective score.

    Compatibility:
    - Historical names (min_R0, min_Bpeak, max_Pnet, min_recirc) are supported.
    - New objectives can be added via the objective registry.

    Returns a score where *lower is better* (so max objectives are negated).
    """
    spec = get_objective(name)
    if spec is None:
        # fall back to legacy names
        if name == "min_R0":
            return float(out.get("R0_m", 1e9))
        if name == "min_Bpeak":
            return float(out.get("B_peak_T", 1e9))
        if name == "max_Pnet":
            return -float(out.get("P_e_net_MW", -1e9))
        if name == "min_recirc":
            return float(out.get("P_recirc_MW", 1e9))
        return float(out.get("R0_m", 1e9))

    v = float(spec.fn(out))
    return v if spec.sense == "min" else -v

def is_feasible(out: Dict[str, float]) -> bool:
    cs = build_constraints_from_outputs(out)
    return all(c.ok for c in cs if c.name != "Radial build closes" or c.value >= 0.5)

def optimize_design(base: PointInputs,
                    objective: str = "min_R0",
                    variables: Optional[Dict[str, Tuple[float,float]]] = None,
                    n_iter: int = 200,
                    seed: int = 1) -> Tuple[PointInputs, Dict[str,float]]:
    """Very lightweight constrained optimizer.

    Random-search with elitism inside bounds. No SciPy required.
    """
    rng = random.Random(seed)
    if variables is None:
        variables = {
            "Ip_MA": (0.5*base.Ip_MA, 1.5*base.Ip_MA),
            "fG": (0.3, 1.2),
            "Paux_MW": (0.0, max(base.Paux_MW*2.0, 20.0)),
        }
    best_inp = base
    best_out = hot_ion_point(base)
    best_score = default_objective(best_out, objective) if is_feasible(best_out) else 1e99

    for _ in range(max(n_iter, 1)):
        cand = base
        for k,(lo,hi) in variables.items():
            val = lo + (hi-lo)*rng.random()
            cand = replace(cand, **{k: val})
        out = hot_ion_point(cand)
        if not is_feasible(out):
            continue
        score = default_objective(out, objective)
        if score < best_score:
            best_score, best_inp, best_out = score, cand, out

    return best_inp, best_out

def latin_hypercube_samples(n: int, bounds: Dict[str, Tuple[float, float]], seed: Optional[int] = None) -> List[Dict[str, float]]:
    """Generate Latin hypercube samples in given bounds (1D stratification per variable)."""
    if seed is not None:
        random.seed(seed)
    keys = list(bounds.keys())
    strata = list(range(n))
    samples = [{k: 0.0 for k in keys} for _ in range(n)]
    for k in keys:
        random.shuffle(strata)
        lo, hi = bounds[k]
        for i, s in enumerate(strata):
            u = (s + random.random()) / n
            samples[i][k] = lo + u * (hi - lo)
    return samples

def dominates(a: Dict[str, float], b: Dict[str, float], objectives: Dict[str, str]) -> bool:
    """Return True if a dominates b for objectives dict {key: 'min'|'max'}."""
    better_or_equal = True
    strictly_better = False
    for key, sense in objectives.items():
        va, vb = a.get(key, float('nan')), b.get(key, float('nan'))
        if va != va or vb != vb:
            return False
        if sense == 'min':
            if va > vb:
                better_or_equal = False
            if va < vb:
                strictly_better = True
        else:
            if va < vb:
                better_or_equal = False
            if va > vb:
                strictly_better = True
    return better_or_equal and strictly_better


def _pareto_worker(payload):
    """Worker-safe evaluation for pareto sampling (pickleable)."""
    base_dict = payload["base"]
    sample = payload["sample"]
    # local imports for multiprocessing
    from dataclasses import replace
    from models.inputs import PointInputs
    from physics.hot_ion import hot_ion_point
    from constraints.system import build_constraints_from_outputs
    base = PointInputs(**base_dict)
    inp = base
    for k, v in sample.items():
        inp = replace(inp, **{k: float(v)})
    import time as _time
    _t0 = _time.perf_counter()
    out = hot_ion_point(inp)
    _eval_s = _time.perf_counter() - _t0
    cs = build_constraints_from_outputs(out)
    if not all(c.ok for c in cs):
        return None
    row = {**sample}
    row.update({
        "eval_s": float(_eval_s),
        "Q_DT_eqv": float(out.get("Q_DT_eqv", float("nan"))),
        "H98": float(out.get("H98", float("nan"))),
        "B_peak_T": float(out.get("B_peak_T", float("nan"))),
        "P_e_net_MW": float(out.get("P_e_net_MW", float("nan"))),
        "t_flat_s": float(out.get("t_flat_s", float("nan"))),
    })
    return row

def pareto_front(points: List[Dict[str, float]], objectives: Dict[str, str]) -> List[Dict[str, float]]:
    """Filter nondominated points."""
    front: List[Dict[str, float]] = []
    for p in points:
        dominated = False
        for q in points:
            if q is p:
                continue
            if dominates(q, p, objectives):
                dominated = True
                break
        if not dominated:
            front.append(p)
    return front

def pareto_optimize(
    base: PointInputs,
    bounds: Dict[str, Tuple[float, float]],
    objectives: Dict[str, str],
    n_samples: int = 300,
    seed: Optional[int] = None,
    parallel: bool = False,
    workers: Optional[int] = None,
) -> Dict[str, object]:
    """
    Pareto search: Latin hypercube sampling within bounds, keep feasible points, return Pareto front.

    objectives example:
      {'R0_m': 'min', 'B_peak_T': 'min', 'P_e_net_MW': 'max'}
    """
    import time as _time
    t_wall0 = _time.perf_counter()

    samples = latin_hypercube_samples(n_samples, bounds, seed=seed)
    feasible: List[Dict[str, float]] = []
    if parallel:
        import concurrent.futures
        payloads = [{"base": base.__dict__, "sample": s} for s in samples]
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
            for res in ex.map(_pareto_worker, payloads, chunksize=1):
                if res is not None:
                    feasible.append(res)
    else:
        for s in samples:
            inp = base
            for k, v in s.items():
                inp = replace(inp, **{k: float(v)})
            out = hot_ion_point(inp)
            cs = build_constraints_from_outputs(out)
            if all(c.ok for c in cs):
                row = {**s}
                row.update({
                    "Q_DT_eqv": float(out.get("Q_DT_eqv", float("nan"))),
                    "H98": float(out.get("H98", float("nan"))),
                    "B_peak_T": float(out.get("B_peak_T", float("nan"))),
                    "P_e_net_MW": float(out.get("P_e_net_MW", float("nan"))),
                    "t_flat_s": float(out.get("t_flat_s", float("nan"))),
                })
                feasible.append(row)

    front = pareto_front(feasible, objectives)
    # ---- Performance meta (telemetry only) ----
    wall_s = float(_time.perf_counter() - t_wall0)
    eval_sum_s = float(sum(float(r.get('eval_s', 0.0) or 0.0) for r in feasible))
    perf = {
        'parallel': bool(parallel),
        'workers': int(workers) if workers is not None else 0,
        'n_samples': int(n_samples),
        'n_feasible': int(len(feasible)),
        'wall_s': wall_s,
        'eval_sum_s': eval_sum_s,
        'speedup_est': (eval_sum_s / wall_s) if wall_s > 1e-12 else float('nan'),
    }

    return {"feasible": feasible, "pareto": front, "objectives": objectives, "perf": perf}



# Backward-compatible alias (UI expects this name)
def scan_feasible_and_pareto(
    base_inputs,
    bounds,
    n_samples: int = 200,
    objectives: Optional[Dict[str, str]] = None,
    seed: Optional[int] = None,
    parallel: bool = False,
    workers: Optional[int] = None,
):
    """Compatibility wrapper around pareto_optimize.

    Parallelism is opt-in either via `parallel=True` or env `SHAMS_PARALLEL_PARETO=1`.
    Worker count may be set via `workers` or env `SHAMS_WORKERS=<int>`.
    """
    _par = bool(parallel) or bool(int(os.getenv('SHAMS_PARALLEL_PARETO', '0') or '0'))
    _w_env = os.getenv('SHAMS_WORKERS', '').strip()
    _w = workers if workers is not None else (int(_w_env) if _w_env.isdigit() else None)
    return pareto_optimize(
        base=base_inputs,
        bounds=bounds,
        objectives=objectives or default_objectives(),
        n_samples=n_samples,
        seed=seed,
        parallel=_par,
        workers=_w,
    )

def differential_evolution_optimize(
    base: PointInputs,
    bounds: Dict[str, Tuple[float, float]],
    objective: Callable[[Dict[str, float]], float],
    n_pop: int = 24,
    n_gen: int = 40,
    F: float = 0.7,
    Cr: float = 0.9,
    seed: Optional[int] = None,
    parallel: bool = False,
    workers: Optional[int] = None,
) -> Dict[str, object]:
    """Global optimizer (DE/rand/1/bin) for constraint-heavy design searches.

    - Windows-native, no SciPy dependency
    - Deterministic if seed is provided
    - Uses SHAMS point solver; infeasible points receive +inf objective

    Returns dict with: best_inputs, best_out, history.
    """
    if seed is not None:
        random.seed(seed)

    keys = list(bounds.keys())
    lo = [bounds[k][0] for k in keys]
    hi = [bounds[k][1] for k in keys]

    def sample_vec():
        return [random.uniform(l, h) for l, h in zip(lo, hi)]

    def vec_to_inputs(vec):
        data = {k: float(v) for k, v in zip(keys, vec)}
        return replace(base, **data)

    from solvers.point_solver import evaluate_point

    def eval_vec(vec):
        inp = vec_to_inputs(vec)
        out = evaluate_point(inp)
        feasible = bool(out.get("feasible", True)) and bool(out.get("hard_ok", True))
        if not feasible:
            return float("inf"), inp, out
        try:
            val = float(objective(out))
        except Exception:
            val = float("inf")
        return val, inp, out

    # init population
    pop = [sample_vec() for _ in range(max(4, n_pop))]
    vals = []
    for v in pop:
        vals.append(eval_vec(v)[0])
    history = []

    best_i = min(range(len(pop)), key=lambda i: vals[i])
    best = pop[best_i]
    best_val, best_inp, best_out = eval_vec(best)

    for g in range(n_gen):
        for i in range(len(pop)):
            idxs = [j for j in range(len(pop)) if j != i]
            a, b, c = random.sample(idxs, 3)
            xa, xb, xc = pop[a], pop[b], pop[c]
            # mutation
            mutant = [xa[d] + F*(xb[d]-xc[d]) for d in range(len(keys))]
            # crossover + bounds
            trial = []
            jrand = random.randrange(len(keys))
            for d in range(len(keys)):
                if random.random() < Cr or d == jrand:
                    val = mutant[d]
                else:
                    val = pop[i][d]
                # clip
                val = max(lo[d], min(hi[d], val))
                trial.append(val)
            f_trial, _, _ = eval_vec(trial)
            if f_trial <= vals[i]:
                pop[i] = trial
                vals[i] = f_trial

        best_i = min(range(len(pop)), key=lambda i: vals[i])
        best = pop[best_i]
        best_val, best_inp, best_out = eval_vec(best)
        history.append({"gen": g, "best_obj": best_val})

    return {"best_inputs": best_inp, "best_out": best_out, "history": history}


def robust_feasibility_monte_carlo(
    base: PointInputs,
    perturb: Dict[str, Tuple[float, float]],
    n: int = 200,
    seed: Optional[int] = None,
    parallel: bool = False,
    workers: Optional[int] = None,
    *,
    metrics: Optional[Tuple[str, ...]] = None,
    thresholds: Optional[Dict[str, Tuple[str, float]]] = None,
) -> Dict[str, object]:
    """Monte Carlo robustness check.

    perturb maps field -> (sigma_fraction, min_fraction_of_base)
      - sample x ~ Normal(base, sigma_fraction*base), then clamp >= min_fraction*base

    metrics: optional list of output keys to track (e.g. ('P_net_MWe','COE_proxy_USD_per_MWh'))
    thresholds: optional dict metric -> (sense, limit) where sense is one of: '>=','<=','>','<'
                probabilities for meeting each threshold are returned.

    Returns:
      feasible_prob: fraction of samples passing hard constraints (as evaluated by constraints module)
      margin_stats: basic quantiles for common margin keys
      metric_stats: basic quantiles for selected metrics
      threshold_probs: P(metric meets threshold) for selected thresholds
    """
    if seed is not None:
        random.seed(seed)

    from constraints.constraints import evaluate_constraints
    from physics.hot_ion import hot_ion_point

    feas = 0
    margin_samples: Dict[str, list] = {}
    metric_samples: Dict[str, list] = {}

    # pre-derive metric keys
    metric_keys = tuple(metrics or ())
    thr = dict(thresholds or {})

    for _ in range(max(n, 1)):
        # sample perturbed point
        inp = replace(base)
        for k, (sig_frac, min_frac) in perturb.items():
            if not hasattr(inp, k):
                continue
            b = float(getattr(base, k))
            sigma = abs(float(sig_frac)) * abs(b)
            x = random.gauss(b, sigma) if sigma > 0 else b
            x = max(x, float(min_frac) * b)
            setattr(inp, k, x)

        out = hot_ion_point(inp) or {}
        cons = evaluate_constraints(out)
        ok = all(bool(c.passed) for c in cons if bool(getattr(c, "hard", True)))
        feas += 1 if ok else 0

        # collect margins (if present)
        for mk in ("min_constraint_margin", "min_margin", "q_div_margin", "tf_margin", "beta_margin"):
            if mk in out:
                margin_samples.setdefault(mk, []).append(float(out[mk]))

        # collect selected metrics
        for mk in metric_keys:
            if mk in out:
                v = out.get(mk)
                if isinstance(v, (int, float)) and math.isfinite(float(v)):
                    metric_samples.setdefault(mk, []).append(float(v))

    def _qstats(arr: list) -> Dict[str, float]:
        arr_s = sorted(arr)
        if not arr_s:
            return {}
        def q(p: float) -> float:
            i = int(p * (len(arr_s) - 1))
            return float(arr_s[max(0, min(i, len(arr_s)-1))])
        return {"mean": float(sum(arr_s)/len(arr_s)), "p05": q(0.05), "p50": q(0.50), "p95": q(0.95)}

    stats = {mk: _qstats(arr) for mk, arr in margin_samples.items() if arr}
    mstats = {mk: _qstats(arr) for mk, arr in metric_samples.items() if arr}

    # threshold probabilities
    tprobs: Dict[str, float] = {}
    for mk, (sense, lim) in thr.items():
        arr = metric_samples.get(mk, [])
        if not arr:
            continue
        if sense in (">=", ">"):
            limf = float(lim)
            if sense == ">=":
                tprobs[mk] = sum(1 for v in arr if v >= limf) / len(arr)
            else:
                tprobs[mk] = sum(1 for v in arr if v > limf) / len(arr)
        elif sense in ("<=", "<"):
            limf = float(lim)
            if sense == "<=":
                tprobs[mk] = sum(1 for v in arr if v <= limf) / len(arr)
            else:
                tprobs[mk] = sum(1 for v in arr if v < limf) / len(arr)

    return {
        "feasible_prob": feas / max(n, 1),
        "n": int(n),
        "margin_stats": stats,
        "metric_stats": mstats,
        "threshold_probs": tprobs,
    }

