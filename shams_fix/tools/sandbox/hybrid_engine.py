
from __future__ import annotations
"""
Optimization Sandbox — Hybrid Machine Finder (SHAMS-native)

Goals:
- Self-contained machine finding (no external PROCESS).
- Feasible-first global search -> surrogate-guided acceleration -> local refinement.
- Always audited by the frozen evaluator passed as evaluate_fn.
- Deterministic given a seed.

This module is UI-facing and produces a schema-stable run dict:
{
  kind, seed, intent, objectives, var_specs, budgets,
  trace: [ {phase, iter, feasible, score, failure_mode, dominant_constraints, min_margin, ...} ],
  archive: [ candidate dicts ... ],
  resistance: { ... summaries ... },
  provenance: { ... hashes ... },
}

Design discipline:
- No constraint relaxation.
- Feasible dominates infeasible.
- Infeasible ranked only by violation distance (for guidance) and always labeled infeasible.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import math
import os
import json
import hashlib
import numpy as np

from tools.sandbox.archive_v2 import diversity_prune, annotate_dominance


try:
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
except Exception:  # pragma: no cover
    RandomForestClassifier = None  # type: ignore
    RandomForestRegressor = None  # type: ignore


@dataclass(frozen=True)
class Objective:
    key: str
    sense: str = "max"  # "max" or "min"
    weight: float = 1.0


@dataclass(frozen=True)
class VarSpec:
    key: str
    lo: float
    hi: float


def _safe_float(x: Any) -> float:
    try:
        if x is None:
            return float("nan")
        return float(x)
    except Exception:
        return float("nan")


def _vector_from_inputs(inp: Dict[str, Any], var_specs: List[VarSpec]) -> np.ndarray:
    return np.array([_safe_float(inp.get(v.key)) for v in var_specs], dtype=float)


def _clip(x: np.ndarray, var_specs: List[VarSpec]) -> np.ndarray:
    lo = np.array([v.lo for v in var_specs], dtype=float)
    hi = np.array([v.hi for v in var_specs], dtype=float)
    return np.clip(x, lo, hi)


def scalar_score(outputs: Dict[str, Any], objectives: List[Objective]) -> float:
    """Higher is better. Missing values -> very poor."""
    s = 0.0
    for o in objectives:
        v = _safe_float(outputs.get(o.key))
        if not math.isfinite(v):
            return -1e30
        if o.sense == "min":
            v = -v
        s += float(o.weight) * float(v)
    return float(s)


def violation_distance(constraints: List[Dict[str, Any]]) -> float:
    """Sum of negative signed margins (0 means feasible)."""
    d = 0.0
    for r in constraints or []:
        sm = _safe_float(r.get("signed_margin"))
        if math.isfinite(sm) and sm < 0:
            d += -sm
    return float(d)


def _feasible_key(res: Dict[str, Any], objectives: List[Objective]) -> Tuple[int, float, float]:
    """
    Sort key:
      1) feasible first (0 for feasible, 1 for infeasible)
      2) if feasible: higher score better
         else: lower violation distance better (closer to feasible)
      3) tie-break: higher score (even if infeasible, for guidance)
    """
    feas = 0 if bool(res.get("feasible", False)) else 1
    sc = float(res.get("_score", -1e30))
    vd = float(res.get("_violation", 1e30))
    if feas == 0:
        return (0, -sc, vd)
    return (1, vd, -sc)


def _dominant_constraints(res: Dict[str, Any], k: int = 3) -> List[str]:
    ac = res.get("active_constraints") or []
    out = []
    for c in ac[:k]:
        out.append(str(c))
    return out


def _trace_row(phase: str, it: int, res: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "phase": str(phase),
        "iter": int(it),
        "feasible": bool(res.get("feasible", False)),
        "score": float(res.get("_score", -1e30)),
        "violation": float(res.get("_violation", 1e30)),
        "min_signed_margin": float(res.get("min_signed_margin", float("nan"))),
        "failure_mode": res.get("failure_mode"),
        "dominant_constraints": _dominant_constraints(res),
    }


def propose_de(
    rng: np.random.Generator,
    pop: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    F: float,
    CR: float,
) -> np.ndarray:
    """DE/rand/1/bin mutation+recombination with optional physics-aware operators.

    Physics-aware operators are *proposal generators* only; every proposal is still
    audited by the frozen evaluator. They are designed to improve efficiency on
    tokamak-like non-convex feasible regions.
    """
    n, d = pop.shape
    trial = np.zeros_like(pop)

    def _physics_operator(x: np.ndarray) -> np.ndarray:
        # A small library of domain-shaped moves in *normalized* variable space.
        # We do not assume which keys correspond to which dims here; the operators
        # are generic: scale a subset, trade two dims, nudge toward center.
        y = x.copy()
        op = int(rng.integers(0, 4))
        if op == 0 and d >= 2:
            # Scale a random subset together ("size scaling"-like).
            idx = rng.choice(np.arange(d), size=int(max(1, d // 3)), replace=False)
            s = float(rng.normal(loc=1.0, scale=0.06))
            y[idx] = y[idx] * s
        elif op == 1 and d >= 2:
            # Two-way trade ("field-current"-like): one up, one down.
            i, j = rng.choice(np.arange(d), size=2, replace=False)
            dv = float(rng.normal(scale=0.08))
            y[i] = y[i] * (1.0 + dv)
            y[j] = y[j] * (1.0 - dv)
        elif op == 2:
            # Relief move: contract along a random direction.
            y = y + rng.normal(scale=(hi - lo) / 30.0, size=d)
        else:
            # Centering jitter: keep within bounds and avoid extremes.
            mid = (lo + hi) / 2.0
            y = 0.85 * y + 0.15 * mid + rng.normal(scale=(hi - lo) / 60.0, size=d)
        return np.clip(y, lo, hi)

    for i in range(n):
        # With small probability, use a physics-aware operator instead of DE.
        if float(rng.random()) < 0.18:
            trial[i] = _physics_operator(pop[i])
            continue
        idxs = rng.choice([j for j in range(n) if j != i], size=3, replace=False)
        a, b, c = pop[idxs[0]], pop[idxs[1]], pop[idxs[2]]
        mutant = a + F * (b - c)
        mutant = np.clip(mutant, lo, hi)
        cross = rng.random(d) < CR
        if not np.any(cross):
            cross[rng.integers(0, d)] = True
        trial[i] = np.where(cross, mutant, pop[i])
    return trial


def _fingerprint(payload: Dict[str, Any]) -> str:
    """Stable fingerprint for reproducibility.

    This is not a security feature; it is an audit convenience.
    """
    try:
        s = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
    except Exception:
        s = repr(payload).encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def _knowledge_path() -> str:
    d = os.path.expanduser("~/.shams")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return os.path.join(d, "opt_knowledge.json")


def load_knowledge() -> List[Dict[str, Any]]:
    """Opt-in, cross-run memory store (active learning).

    Stores evaluated candidates only (inputs + feasibility + score + violation).
    """
    p = _knowledge_path()
    try:
        if os.path.exists(p):
            return list(json.loads(open(p, "r", encoding="utf-8").read()) or [])
    except Exception:
        return []
    return []


def save_knowledge(rows: List[Dict[str, Any]], max_rows: int = 5000) -> None:
    p = _knowledge_path()
    try:
        cur = load_knowledge()
        cur.extend(rows)
        # Keep most recent max_rows
        cur = cur[-int(max_rows):]
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cur, f)
    except Exception:
        return


def surface_surf_phase(
    *,
    evaluate_fn,
    anchor_inputs: Dict[str, Any],
    var_specs: List[VarSpec],
    objectives: List[Objective],
    seed: int,
    seeds: List[Dict[str, Any]],
    steps: int = 80,
    eps_margin: float = 0.015,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Constraint-surface surfing (Tier-1).

    Strategy (simple, robust):
    - Pick feasible points near a binding surface (min_signed_margin close to 0).
    - Propose tangent-ish steps using differences between feasible seeds.
    - Line-search the step size to keep the binding constraint approximately active.

    This is not a gradient method; it is a manifold-exploration heuristic.
    """
    rng = np.random.default_rng(int(seed) + 101)
    keys = [v.key for v in var_specs]
    lo = np.array([v.lo for v in var_specs], dtype=float)
    hi = np.array([v.hi for v in var_specs], dtype=float)

    # Select candidate seeds near the boundary.
    feas = [s for s in (seeds or []) if s.get("feasible", False)]
    near = [s for s in feas if abs(float(s.get("min_signed_margin", 1e9))) < float(eps_margin)]
    pool = near or feas
    if not pool:
        return [], []

    def _get_binding_name(res: Dict[str, Any]) -> Optional[str]:
        recs = res.get("constraints") or []
        best = None
        best_sm = None
        for r in recs:
            sm = _safe_float(r.get("signed_margin"))
            if not math.isfinite(sm):
                continue
            if best_sm is None or sm < best_sm:
                best_sm = sm
                best = str(r.get("name") or r.get("constraint") or "")
        return best

    def _binding_margin(res: Dict[str, Any], name: str) -> float:
        for r in (res.get("constraints") or []):
            if str(r.get("name") or r.get("constraint") or "") == name:
                return _safe_float(r.get("signed_margin"))
        return float("nan")

    out_pts: List[Dict[str, Any]] = []
    trace: List[Dict[str, Any]] = []

    for it in range(int(steps)):
        a = pool[int(rng.integers(0, len(pool)))]
        b = pool[int(rng.integers(0, len(pool)))]
        xa = _vector_from_inputs(a.get("inputs") or {}, var_specs)
        xb = _vector_from_inputs(b.get("inputs") or {}, var_specs)
        if not np.all(np.isfinite(xa)) or not np.all(np.isfinite(xb)):
            continue
        dirn = xb - xa
        if float(np.linalg.norm(dirn)) <= 1e-12:
            dirn = rng.normal(size=len(keys))
        dirn = dirn / (np.linalg.norm(dirn) + 1e-12)

        # Binding constraint at point a
        bind = _get_binding_name(a) or ""
        if not bind:
            continue
        target = _binding_margin(a, bind)
        if not math.isfinite(target):
            target = 0.0

        # Propose a step and line-search for binding margin.
        step0 = float(rng.normal(scale=0.12))
        x_try = _clip(xa + step0 * dirn * (hi - lo), var_specs)

        # Bisection on scalar t to keep binding margin close to target.
        t_lo, t_hi = -0.35, 0.35
        best_res = None
        best_err = 1e30
        for _ in range(10):
            t = 0.5 * (t_lo + t_hi)
            x = _clip(xa + t * dirn * (hi - lo), var_specs)
            cand = dict(anchor_inputs)
            for k, vv in zip(keys, x.tolist()):
                cand[k] = float(vv)
            res = evaluate_fn(cand)
            res["_score"] = scalar_score(res.get("outputs", {}) or {}, objectives)
            res["_violation"] = violation_distance(res.get("constraints", []) or [])
            bm = _binding_margin(res, bind)
            err = abs((bm if math.isfinite(bm) else 0.0) - target)
            if err < best_err:
                best_err = err
                best_res = res
            # steer interval
            if math.isfinite(bm) and bm > target:
                t_hi = t
            else:
                t_lo = t
        if best_res is not None:
            trace.append(_trace_row("surf", it, best_res))
            out_pts.append(best_res)

    return out_pts, trace


def build_feasibility_skeleton(
    archive: List[Dict[str, Any]],
    var_specs: List[VarSpec],
    k: int = 8,
) -> Dict[str, Any]:
    """Build a simple feasible-region graph (Tier-1).

    Returns:
      {n_feasible, n_components, components: [sizes], bottleneck_edges: [(i,j,dist)], ...}
    """
    feas = [a for a in (archive or []) if a.get("feasible", False)]
    if len(feas) < 3:
        return {"n_feasible": len(feas), "n_components": 0, "components": [], "bottleneck_edges": []}
    X = np.array([_vector_from_inputs(a.get("inputs") or {}, var_specs) for a in feas], dtype=float)
    # Replace non-finite with column medians
    for c in range(X.shape[1]):
        col = X[:, c]
        good = col[np.isfinite(col)]
        med = float(np.median(good)) if len(good) else 0.0
        col[~np.isfinite(col)] = med
        X[:, c] = col
    # kNN
    n = X.shape[0]
    k = int(min(max(2, k), n - 1))
    dmat = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)
    nn = np.argsort(dmat, axis=1)[:, 1 : k + 1]
    # graph adjacency
    adj = [[] for _ in range(n)]
    for i in range(n):
        for j in nn[i].tolist():
            adj[i].append(int(j))
            adj[int(j)].append(i)
    # components
    seen = set()
    comps = []
    for i in range(n):
        if i in seen:
            continue
        stack = [i]
        seen.add(i)
        comp = []
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    # bottleneck edges: long edges within kNN (top few)
    edges = []
    for i in range(n):
        for j in nn[i].tolist():
            if i < int(j):
                edges.append((i, int(j), float(dmat[i, int(j)])))
    edges.sort(key=lambda t: t[2], reverse=True)
    return {
        "n_feasible": int(n),
        "n_components": int(len(comps)),
        "components": [int(len(c)) for c in comps],
        "bottleneck_edges": edges[: min(10, len(edges))],
    }


def global_de_phase(
    *,
    evaluate_fn,
    anchor_inputs: Dict[str, Any],
    var_specs: List[VarSpec],
    objectives: List[Objective],
    pop_size: int,
    generations: int,
    seed: int,
    F: float = 0.7,
    CR: float = 0.9,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (evaluated population, trace)."""
    rng = np.random.default_rng(int(seed))
    keys = [v.key for v in var_specs]
    lo = np.array([v.lo for v in var_specs], dtype=float)
    hi = np.array([v.hi for v in var_specs], dtype=float)
    dim = len(keys)
    # init: anchor-centered + uniform
    pop = rng.uniform(lo, hi, size=(int(pop_size), dim))
    a = np.array([_safe_float(anchor_inputs.get(k)) for k in keys], dtype=float)
    a = np.clip(a, lo, hi)
    for i in range(min(8, pop.shape[0])):
        pop[i] = np.clip(a + rng.normal(scale=(hi - lo) / 10.0, size=dim), lo, hi)

    evaluated: List[Dict[str, Any]] = []
    trace: List[Dict[str, Any]] = []

    def _eval_vec(x: np.ndarray, it: int) -> Dict[str, Any]:
        cand = dict(anchor_inputs)
        for k, vv in zip(keys, x.tolist()):
            cand[k] = float(vv)
        res = evaluate_fn(cand)
        res["_score"] = scalar_score(res.get("outputs", {}) or {}, objectives)
        res["_violation"] = violation_distance(res.get("constraints", []) or [])
        trace.append(_trace_row("global", it, res))
        return res

    # Evaluate initial pop
    pop_res = [_eval_vec(pop[i], 0) for i in range(pop.shape[0])]

    for g in range(1, int(generations) + 1):
        trial = propose_de(rng, pop, lo, hi, float(F), float(CR))
        trial_res = [_eval_vec(trial[i], g) for i in range(trial.shape[0])]
        # Selection: feasible-first
        for i in range(pop.shape[0]):
            if _feasible_key(trial_res[i], objectives) < _feasible_key(pop_res[i], objectives):
                pop[i] = trial[i]
                pop_res[i] = trial_res[i]

    evaluated.extend(pop_res)
    return evaluated, trace


def surrogate_phase(
    *,
    evaluate_fn,
    anchor_inputs: Dict[str, Any],
    var_specs: List[VarSpec],
    objectives: List[Objective],
    seed: int,
    history: List[Dict[str, Any]],
    rounds: int = 6,
    propose_per_round: int = 40,
    pool: int = 1200,
    alpha: float = 2.0,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Train feasibility classifier + score regressor (feasible only).
    Propose candidates maximizing P(feasible)^alpha * predicted_score.
    """
    if RandomForestClassifier is None or RandomForestRegressor is None:
        return [], []

    rng = np.random.default_rng(int(seed) + 11)
    keys = [v.key for v in var_specs]
    lo = np.array([v.lo for v in var_specs], dtype=float)
    hi = np.array([v.hi for v in var_specs], dtype=float)

    # Build training data
    X = []
    y_feas = []
    y_score = []
    for r in history:
        inp = r.get("inputs") or {}
        x = np.array([_safe_float(inp.get(k)) for k in keys], dtype=float)
        if not np.all(np.isfinite(x)):
            continue
        X.append(x)
        y_feas.append(1 if r.get("feasible", False) else 0)
        if r.get("feasible", False):
            y_score.append(float(r.get("_score", -1e30)))
        else:
            y_score.append(float("nan"))

    if len(X) < 50:
        return [], []

    X = np.array(X, dtype=float)
    y_feas = np.array(y_feas, dtype=int)
    y_score = np.array(y_score, dtype=float)

    clf = RandomForestClassifier(n_estimators=200, random_state=int(seed), n_jobs=-1)
    clf.fit(X, y_feas)

    feas_mask = y_feas == 1
    reg = None
    if int(feas_mask.sum()) >= 20:
        reg = RandomForestRegressor(n_estimators=300, random_state=int(seed), n_jobs=-1)
        reg.fit(X[feas_mask], y_score[feas_mask])

    new_points: List[Dict[str, Any]] = []
    trace: List[Dict[str, Any]] = []

    def _eval_vec(x: np.ndarray, it: int) -> Dict[str, Any]:
        cand = dict(anchor_inputs)
        for k, vv in zip(keys, x.tolist()):
            cand[k] = float(vv)
        res = evaluate_fn(cand)
        res["_score"] = scalar_score(res.get("outputs", {}) or {}, objectives)
        res["_violation"] = violation_distance(res.get("constraints", []) or [])
        trace.append(_trace_row("surrogate", it, res))
        return res

    for rr in range(int(rounds)):
        # generate a pool uniformly (cheap)
        poolX = rng.uniform(lo, hi, size=(int(pool), len(keys)))
        p = clf.predict_proba(poolX)[:, 1]
        if reg is not None:
            pred = reg.predict(poolX)
        else:
            pred = np.zeros(poolX.shape[0], dtype=float)
        acq = (p ** float(alpha)) * pred
        # choose top proposals
        top_idx = np.argsort(-acq)[: int(propose_per_round)]
        for j, ii in enumerate(top_idx.tolist()):
            res = _eval_vec(poolX[ii], rr * int(propose_per_round) + j + 1)
            new_points.append(res)

        # update history online (simple)
        history.extend(new_points[-int(propose_per_round):])
        # rebuild quickly if we have enough feasible
        # (kept simple to avoid expensive retrains)

    return new_points, trace


def local_refine_phase(
    *,
    evaluate_fn,
    anchor_inputs: Dict[str, Any],
    var_specs: List[VarSpec],
    objectives: List[Objective],
    seed: int,
    seeds: List[Dict[str, Any]],
    steps: int = 80,
    step_frac: float = 0.06,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Pattern-like random local refinement around best feasible seeds."""
    rng = np.random.default_rng(int(seed) + 23)
    keys = [v.key for v in var_specs]
    lo = np.array([v.lo for v in var_specs], dtype=float)
    hi = np.array([v.hi for v in var_specs], dtype=float)
    span = hi - lo
    span = np.where(span <= 0, 1.0, span)

    bests: List[Dict[str, Any]] = []
    trace: List[Dict[str, Any]] = []

    def _eval_vec(x: np.ndarray, it: int) -> Dict[str, Any]:
        cand = dict(anchor_inputs)
        for k, vv in zip(keys, x.tolist()):
            cand[k] = float(vv)
        res = evaluate_fn(cand)
        res["_score"] = scalar_score(res.get("outputs", {}) or {}, objectives)
        res["_violation"] = violation_distance(res.get("constraints", []) or [])
        trace.append(_trace_row("local", it, res))
        return res

    # pick up to 5 feasible seeds
    feas = [s for s in seeds if s.get("feasible", False)]
    feas.sort(key=lambda r: float(r.get("_score", -1e30)), reverse=True)
    feas = feas[:5]
    if not feas:
        return [], []

    for si, s in enumerate(feas):
        x = _vector_from_inputs(s.get("inputs") or {}, var_specs)
        x = np.clip(x, lo, hi)
        best = s
        for it in range(int(steps)):
            step = rng.normal(size=len(keys)) * span * float(step_frac)
            candx = np.clip(x + step, lo, hi)
            res = _eval_vec(candx, si * int(steps) + it + 1)
            if _feasible_key(res, objectives) < _feasible_key(best, objectives):
                best = res
                x = candx
        bests.append(best)

    return bests, trace


def build_archive(points: List[Dict[str, Any]], var_specs: List[VarSpec], topk: int = 50, objectives: Optional[List[Objective]] = None) -> List[Dict[str, Any]]:
    """Build a diverse, feasible-first archive.

    Notes:
    - This is NOT a recommender. It does not label a 'best point'.
    - Feasibility is primary; diversity is preserved in normalized var-space.
    - Dominance is annotated (is_dominant) only when objectives are explicitly declared.
    """
    pts = list(points or [])

    # Feasible-first ordering (no hidden penalties in UI-facing outputs)
    def sk(r: Dict[str, Any]):
        feas = 0 if bool(r.get("feasible", False)) else 1
        if feas == 0:
            return (0, -float(r.get("_score", -1e30)))
        return (1, float(r.get("_violation", 1e30)))
    pts.sort(key=sk)

    # Remove exact/near duplicates in var space
    keys = [v.key for v in (var_specs or [])]
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for r in pts:
        inp = r.get("inputs") or {}
        x = tuple(round(_safe_float(inp.get(k)), 8) for k in keys)
        if x in seen:
            continue
        seen.add(x)
        uniq.append(r)
        if len(uniq) >= int(topk) * 6:
            break

    # Diversity prune
    if len(uniq) > int(topk) and keys:
        uniq = diversity_prune(uniq, keys, int(topk))

    # Dominance annotation (explicit objectives only)
    if objectives:
        obj_contract = [{"key": o.key, "sense": o.sense} for o in objectives]
        uniq = annotate_dominance(uniq, obj_contract)

    return uniq


def resistance_atlas(trace: List[Dict[str, Any]], last_n: int = 250) -> Dict[str, Any]:
    """Live-ish resistance summary for UI (constraint walls, failure modes, feasibility rate)."""
    from collections import Counter
    T = (trace or [])[-int(last_n):]
    if not T:
        return {"n": 0}
    feas = sum(1 for t in T if t.get("feasible", False))
    fm = Counter([str(t.get("failure_mode") or "") for t in T])
    dc = Counter()
    for t in T:
        for c in (t.get("dominant_constraints") or [])[:2]:
            dc[str(c)] += 1
    return {
        "n": len(T),
        "feasible_rate": float(feas) / float(len(T)),
        "failure_modes": dict(fm),
        "dominant_constraints": dict(dc),
    }


def variable_correlations(archive: List[Dict[str, Any]], var_specs: List[VarSpec]) -> Dict[str, Any]:
    """Cheap correlation of variables with min_margin and score over feasible archive."""
    keys = [v.key for v in var_specs]
    feas = [a for a in (archive or []) if a.get("feasible", False)]
    if len(feas) < 10:
        return {"n": len(feas), "corr": {}}
    X = np.array([[ _safe_float((r.get("inputs") or {}).get(k)) for k in keys] for r in feas], dtype=float)
    y_margin = np.array([_safe_float(r.get("min_signed_margin")) for r in feas], dtype=float)
    y_score = np.array([_safe_float(r.get("_score")) for r in feas], dtype=float)
    out = {}
    for i,k in enumerate(keys):
        xi = X[:,i]
        def _corr(a,b):
            good = np.isfinite(a) & np.isfinite(b)
            if good.sum() < 5:
                return float("nan")
            aa = a[good]; bb=b[good]
            if np.std(aa) < 1e-12 or np.std(bb) < 1e-12:
                return float("nan")
            return float(np.corrcoef(aa, bb)[0,1])
        out[k] = {
            "corr_margin": _corr(xi, y_margin),
            "corr_score": _corr(xi, y_score),
        }
    return {"n": len(feas), "corr": out}


def run_hybrid_machine_finder(
    *,
    evaluate_fn,
    evaluate_other_fn=None,
    intent: str,
    anchor_inputs: Dict[str, Any],
    var_specs: List[VarSpec],
    objectives: List[Objective],
    budgets: Dict[str, Any],
    seed: int = 1,
) -> Dict[str, Any]:
    """Orchestrate the hybrid run and return run dict."""
    pop = int(budgets.get("pop_size", 64))
    gens = int(budgets.get("generations", 40))
    srounds = int(budgets.get("surrogate_rounds", 6))
    propose = int(budgets.get("propose_per_round", 36))
    local_steps = int(budgets.get("local_steps", 70))
    topk = int(budgets.get("archive_topk", 60))

    # Honest feasibility-first scheduler (transparent)
    # The scheduler never changes truth or uses penalties; it only allocates later-phase budgets
    # based on observed feasibility in earlier samples.
    budget_allocation = {
        "schema": "shams.opt_sandbox.budget_allocation.v1",
        "initial": {
            "pop_size": pop,
            "generations": gens,
            "surrogate_rounds": srounds,
            "propose_per_round": propose,
            "local_steps": local_steps,
            "surf_steps": int(budgets.get("surf_steps", 80)),
        },
        "after_global": {},
        "final": {},
        "policy": (
            "Allocate effort to (1) reach feasibility if none found, then (2) refine feasible candidates. "
            "This is a scheduler only; constraints are never relaxed and no hidden penalties are used."
        ),
    }

    all_points: List[Dict[str, Any]] = []
    trace: List[Dict[str, Any]] = []

    # Optional cross-run knowledge (Tier-2: active learning)
    use_knowledge = bool(budgets.get("use_knowledge_store", False))
    knowledge_rows = load_knowledge() if use_knowledge else []
    knowledge_points: List[Dict[str, Any]] = []
    if knowledge_rows:
        for r in knowledge_rows[-1500:]:
            try:
                knowledge_points.append({
                    "inputs": dict(r.get("inputs") or {}),
                    "feasible": bool(r.get("feasible", False)),
                    "_score": float(r.get("score", -1e30)),
                    "_violation": float(r.get("violation", 1e30)),
                    "min_signed_margin": float(r.get("min_signed_margin", float("nan"))),
                })
            except Exception:
                continue

    # Phase A: global DE
    pop_pts, tr = global_de_phase(
        evaluate_fn=evaluate_fn,
        anchor_inputs=anchor_inputs,
        var_specs=var_specs,
        objectives=objectives,
        pop_size=pop,
        generations=gens,
        seed=seed,
    )
    all_points.extend(pop_pts); trace.extend(tr)

    # --- Scheduler update after global sampling ---
    try:
        n_g = len(pop_pts) if pop_pts is not None else 0
        n_feas_g = sum(1 for r in (pop_pts or []) if bool(r.get("feasible", False)))
        feas_frac = float(n_feas_g) / float(n_g) if n_g else 0.0
        # 'near-feasible' heuristic: min_signed_margin in [-0.2, 0)
        n_near = 0
        for r in (pop_pts or []):
            try:
                msm = float(r.get("min_signed_margin", float("nan")))
            except Exception:
                msm = float("nan")
            if msm == msm and msm < 0.0 and msm >= -0.2:
                n_near += 1

        # Policy:
        # - If no feasible points: spend more on surrogate proposals and surface steps to reach feasibility.
        # - If some feasible points exist: spend more on local refinement and surfing.
        if n_feas_g == 0:
            srounds = int(max(srounds, 10))
            propose = int(max(propose, 48))
            local_steps = int(max(30, local_steps * 0.6))
            budgets["surf_steps"] = int(max(int(budgets.get("surf_steps", 80)), 100))
        elif feas_frac < 0.05 and n_near > 0:
            srounds = int(max(srounds, 8))
            propose = int(max(propose, 40))
            local_steps = int(max(local_steps, 80))
        else:
            local_steps = int(max(local_steps, 100))
            budgets["surf_steps"] = int(max(int(budgets.get("surf_steps", 80)), 120))

        budget_allocation["after_global"] = {
            "n_global": int(n_g),
            "n_feasible": int(n_feas_g),
            "feasible_fraction": float(feas_frac),
            "n_near_feasible": int(n_near),
            "updated": {
                "surrogate_rounds": int(srounds),
                "propose_per_round": int(propose),
                "local_steps": int(local_steps),
                "surf_steps": int(budgets.get("surf_steps", 80)),
            },
        }
    except Exception:
        pass

    # Phase B: surrogate (with optional active-learning history)
    new_pts, tr2 = surrogate_phase(
        evaluate_fn=evaluate_fn,
        anchor_inputs=anchor_inputs,
        var_specs=var_specs,
        objectives=objectives,
        seed=seed,
        history=(list(all_points) + list(knowledge_points)),
        rounds=srounds,
        propose_per_round=propose,
    )
    all_points.extend(new_pts); trace.extend(tr2)

    # Phase C: local refinement (use best points from all_points)
    all_points.sort(key=lambda r: (0 if r.get("feasible", False) else 1, -float(r.get("_score", -1e30))))
    seed_pts = all_points[: max(10, min(60, len(all_points)))]
    loc_pts, tr3 = local_refine_phase(
        evaluate_fn=evaluate_fn,
        anchor_inputs=anchor_inputs,
        var_specs=var_specs,
        objectives=objectives,
        seed=seed,
        seeds=seed_pts,
        steps=local_steps,
    )
    all_points.extend(loc_pts); trace.extend(tr3)

    # Phase D: constraint-surface surfing (Tier-1)
    if bool(budgets.get("enable_surface_surf", True)):
        surf_pts, tr4 = surface_surf_phase(
            evaluate_fn=evaluate_fn,
            anchor_inputs=anchor_inputs,
            var_specs=var_specs,
            objectives=objectives,
            seed=seed,
            seeds=all_points,
            steps=int(budgets.get("surf_steps", 80)),
        )
        all_points.extend(surf_pts); trace.extend(tr4)

    # Build archive
    archive = build_archive(all_points, var_specs, topk=topk)

    # Resistance summaries
    resist = resistance_atlas(trace, last_n=int(budgets.get("resistance_window", 250)))
    corr = variable_correlations(archive, var_specs)

    # Best feasible
    best = None
    feas = [a for a in archive if a.get("feasible", False)]
    if feas:
        feas.sort(key=lambda r: float(r.get("_score", -1e30)), reverse=True)
        best = feas[0]

    # Tier-1: feasibility skeleton
    skeleton = None
    if bool(budgets.get("enable_skeleton", True)):
        skeleton = build_feasibility_skeleton(archive, var_specs)

    # Tier-4: reproducibility fingerprint
    fp = _fingerprint({
        "intent": str(intent),
        "seed": int(seed),
        "objectives": [o.__dict__ for o in objectives],
        "var_specs": [v.__dict__ for v in var_specs],
        "budgets": dict(budgets),
    })

    # Persist knowledge (Tier-2) — only minimal rows
    if use_knowledge:
        rows = []
        for a in archive[: min(len(archive), 400)]:
            rows.append({
                "inputs": dict(a.get("inputs") or {}),
                "feasible": bool(a.get("feasible", False)),
                "score": float(a.get("_score", -1e30)),
                "violation": float(a.get("_violation", 1e30)),
                "min_signed_margin": float(a.get("min_signed_margin", float("nan"))),
            })
        save_knowledge(rows)

    # Final allocation record
    try:
        budget_allocation["final"] = {
            "surrogate_rounds": int(srounds),
            "propose_per_round": int(propose),
            "local_steps": int(local_steps),
            "surf_steps": int(budgets.get("surf_steps", 80)),
            "archive_topk": int(topk),
        }
    except Exception:
        pass

    return {
        "kind": "optimization_sandbox_hybrid_run",
        "intent": str(intent),
        "seed": int(seed),
        "objectives": [o.__dict__ for o in objectives],
        "var_specs": [v.__dict__ for v in var_specs],
        "budgets": dict(budgets),
        "best_feasible": best,
        "archive": archive,
        "trace": trace,
        "resistance": resist,
        "variable_correlations": corr,
        "feasibility_skeleton": skeleton,
        "budget_allocation": budget_allocation,
        "fingerprint": fp,
        "non_authoritative_notice": (
            "Optimization Sandbox is exploratory. All feasibility claims come from the frozen evaluator. "
            "No relaxation. No auto-apply."
        ),
    }
