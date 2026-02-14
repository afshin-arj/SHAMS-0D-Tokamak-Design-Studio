
from __future__ import annotations
"""
Optimization Sandbox — internal machine-finding engines (PROCESS-replacing, SHAMS-native)

Design rules:
- Frozen SHAMS evaluator is the only truth.
- No relaxation. No hidden penalties.
- Feasible-first selection: feasible always dominates infeasible.
- If infeasible: distance-to-feasible is tracked for guidance, but results remain labeled infeasible.

Implements:
- Global feasible-first DE (dependency-light)
- Surrogate-guided proposal (RF) to accelerate (optional)
- Multi-objective archive (non-dominated set) + diversity pruning
- Resistance explanations (constraint dominance stats)
- Optional economics proxies (transparent)
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional
import math
import numpy as np

try:
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
except Exception:  # pragma: no cover
    RandomForestRegressor = None  # type: ignore
    RandomForestClassifier = None  # type: ignore


@dataclass(frozen=True)
class Objective:
    key: str
    sense: str = "max"   # "max" or "min"
    weight: float = 1.0


@dataclass(frozen=True)
class VarSpec:
    key: str
    lo: float
    hi: float


@dataclass(frozen=True)
class ObjectivePack:
    name: str
    description: str
    objectives: List[Objective]


def default_objective_packs(intent: str) -> List[ObjectivePack]:
    """Explicit one-click objective packs (fully visible)."""
    intent = (intent or "Reactor").strip()
    packs: List[ObjectivePack] = []

    # A) Reactor-ish
    packs.append(ObjectivePack(
        name="Reactor: maximize net electric power (with gain awareness)",
        description="Maximize P_e_net_MW, encourage Q_DT_eqv; avoids trivial solutions.",
        objectives=[Objective("P_e_net_MW","max",1.0), Objective("Q_DT_eqv","max",0.5)],
    ))
    packs.append(ObjectivePack(
        name="Reactor: minimize heat-flux and stress proxies",
        description="Minimize q_div and peak field proxy (softer engineering push).",
        objectives=[Objective("q_div_MW_m2","min",1.0), Objective("B_peak_T","min",0.4)],
    ))
    packs.append(ObjectivePack(
        name="Compact machine: minimize size at fixed performance proxy",
        description="Minimize R0 while maximizing Pfus (trade-off exposed).",
        objectives=[Objective("R0_m","min",1.0), Objective("Pfus_total_MW","max",0.6)],
    ))

    # B) Research-ish
    packs.append(ObjectivePack(
        name="Research: maximize plasma current",
        description="Maximize Ip_MA while keeping outputs defined.",
        objectives=[Objective("Ip_MA","max",1.0)],
    ))
    packs.append(ObjectivePack(
        name="Research: maximize temperature proxy",
        description="Maximize Ti_keV while keeping feasibility truth unchanged.",
        objectives=[Objective("Ti_keV","max",1.0)],
    ))

    # C) PROCESS-emulation packs (inside SHAMS)
    # These are explicit scalarizations that resemble common PROCESS use patterns.
    # They remain fully transparent and are always audited by the frozen evaluator.
    packs.append(ObjectivePack(
        name="PROCESS emulation: minimize COE proxy (explicit)",
        description="Minimize COE_proxy from SHAMS economics proxies (transparent).",
        objectives=[Objective("COE_proxy", "min", 1.0)],
    ))
    packs.append(ObjectivePack(
        name="PROCESS emulation: minimize CAPEX proxy (explicit)",
        description="Minimize CAPEX_proxy (transparent) while encouraging P_e_net.",
        objectives=[Objective("CAPEX_proxy", "min", 1.0), Objective("P_e_net_MW", "max", 0.25)],
    ))
    packs.append(ObjectivePack(
        name="PROCESS emulation: maximize net electric at fixed cost pressure",
        description="Encourage P_e_net while penalizing COE proxy. Explicit weights.",
        objectives=[Objective("P_e_net_MW", "max", 1.0), Objective("COE_proxy", "min", 0.4)],
    ))

    # D) Scenario packs (parity-aware lenses)
    # These are 'program lenses': explicit objective sets that surface typical reactor program concerns.
    packs.append(ObjectivePack(
        name="Scenario: net-electric viability (low recirc)",
        description="Maximize P_e_net_MW while minimizing recirculating power and COE proxy (explicit).",
        objectives=[Objective("P_e_net_MW", "max", 1.0), Objective("P_recirc_MW", "min", 0.35), Objective("COE_proxy", "min", 0.25)],
    ))
    packs.append(ObjectivePack(
        name="Scenario: magnet-limited program (stress/field pressure)",
        description="Minimize B_peak_T and engineering stress proxy while preserving gain awareness.",
        objectives=[Objective("B_peak_T", "min", 0.9), Objective("sigma_vm_MPa", "min", 0.7), Objective("Q_DT_eqv", "max", 0.3)],
    ))
    packs.append(ObjectivePack(
        name="Scenario: cryo-limited program",
        description="Minimize cryo electric proxy and recirc burden while encouraging net electric.",
        objectives=[Objective("P_cryo_electric_MW", "min", 1.0), Objective("P_recirc_MW", "min", 0.35), Objective("P_e_net_MW", "max", 0.3)],
    ))
    packs.append(ObjectivePack(
        name="Scenario: cost-envelope conservative",
        description="Minimize CAPEX and COE proxies while keeping a weak push toward net electric.",
        objectives=[Objective("CAPEX_proxy", "min", 0.9), Objective("COE_proxy", "min", 1.0), Objective("P_e_net_MW", "max", 0.2)],
    ))
    return packs


def _safe_float(x: Any) -> float:
    try:
        if x is None:
            return float("nan")
        return float(x)
    except Exception:
        return float("nan")


def _objective_vector(outputs: Dict[str, Any], objectives: List[Objective]) -> np.ndarray:
    vals = []
    for o in objectives:
        v = _safe_float(outputs.get(o.key))
        if not math.isfinite(v):
            v = float("nan")
        if o.sense == "min" and math.isfinite(v):
            v = -v
        vals.append(v)
    return np.array(vals, dtype=float)


def scalar_score(outputs: Dict[str, Any], objectives: List[Objective]) -> float:
    """Weighted scalar score (explicit). Higher is better."""
    v = _objective_vector(outputs, objectives)
    if not np.all(np.isfinite(v)):
        return -1e30
    w = np.array([float(o.weight) for o in objectives], dtype=float)
    return float(np.dot(v, w))


def constraint_distance(constraint_records: List[Dict[str, Any]]) -> float:
    """Compute a normalized violation distance (0 is feasible)."""
    d = 0.0
    for r in constraint_records or []:
        try:
            sm = float(r.get("signed_margin", float("nan")))
            if math.isfinite(sm) and sm < 0:
                d += (-sm)
        except Exception:
            continue
    return float(d)


def nondominated_mask(Y: np.ndarray) -> np.ndarray:
    """Return boolean mask for non-dominated points assuming all objectives are maximized."""
    n = Y.shape[0]
    keep = np.ones(n, dtype=bool)
    for i in range(n):
        if not keep[i]:
            continue
        for j in range(n):
            if i == j or not keep[j]:
                continue
            if np.all(Y[j] >= Y[i]) and np.any(Y[j] > Y[i]):
                keep[i] = False
                break
    return keep


def diversity_prune(points: List[Dict[str, Any]], var_keys: List[str], k: int) -> List[Dict[str, Any]]:
    """Greedy max-min diversity prune in variable space (keeps top-quality first)."""
    if len(points) <= k:
        return points
    X = np.array([[ _safe_float(p.get("inputs", {}).get(v)) for v in var_keys] for p in points], dtype=float)
    # replace non-finite with column medians
    for c in range(X.shape[1]):
        col = X[:,c]
        good = col[np.isfinite(col)]
        med = float(np.median(good)) if len(good) else 0.0
        col[~np.isfinite(col)] = med
        X[:,c] = col
    chosen = [0]
    dist = np.full(len(points), np.inf)
    for _ in range(1, k):
        last = chosen[-1]
        d = np.linalg.norm(X - X[last], axis=1)
        dist = np.minimum(dist, d)
        nxt = int(np.argmax(dist))
        if nxt in chosen:
            break
        chosen.append(nxt)
    return [points[i] for i in chosen]


def summarize_resistance(trace: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate failure/constraint dominance info from a trace list."""
    from collections import Counter
    fm = Counter()
    ac = Counter()
    feas = 0
    for t in trace or []:
        if t.get("feasible", False):
            feas += 1
        fm[str(t.get("failure_mode",""))] += 1
        for c in (t.get("active_constraints") or [])[:3]:
            ac[str(c)] += 1
    return {
        "n_trace": len(trace or []),
        "n_feasible": int(feas),
        "failure_modes": dict(fm),
        "dominant_constraints": dict(ac),
    }


def de_global_search(
    *,
    evaluate_fn,
    anchor_inputs: Dict[str, Any],
    var_specs: List[VarSpec],
    objectives: List[Objective],
    pop_size: int = 60,
    generations: int = 60,
    F: float = 0.7,
    CR: float = 0.9,
    seed: int = 1,
    keep_trace: bool = True,
) -> Dict[str, Any]:
    """Feasible-first Differential Evolution (DE/rand/1/bin)."""
    rng = np.random.default_rng(int(seed))
    keys = [v.key for v in var_specs]
    lo = np.array([v.lo for v in var_specs], dtype=float)
    hi = np.array([v.hi for v in var_specs], dtype=float)
    dim = len(keys)
    if dim == 0:
        raise ValueError("No variables selected")

    # init population (mix anchor-centered + uniform)
    pop = rng.uniform(lo, hi, size=(int(pop_size), dim))
    if anchor_inputs:
        a = np.array([_safe_float(anchor_inputs.get(k)) for k in keys], dtype=float)
        a = np.clip(a, lo, hi)
        for i in range(min(5, pop.shape[0])):
            pop[i] = np.clip(a + rng.normal(scale=(hi-lo)/8.0, size=dim), lo, hi)

    def _eval_vec(x: np.ndarray) -> Dict[str, Any]:
        cand = dict(anchor_inputs)
        for k,vv in zip(keys, x.tolist()):
            cand[k] = float(vv)
        res = evaluate_fn(cand)
        out = res.get("outputs", {}) or {}
        res["_score"] = scalar_score(out, objectives)
        # distance for infeasible guidance
        res["_dist"] = constraint_distance(res.get("constraints", []))
        return res

    # evaluate
    pop_res = [_eval_vec(pop[i]) for i in range(pop.shape[0])]
    trace: List[Dict[str, Any]] = []

    def _better(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        # True if a is better than b (feasible dominates)
        fa = bool(a.get("feasible", False))
        fb = bool(b.get("feasible", False))
        if fa and not fb:
            return True
        if fb and not fa:
            return False
        if fa and fb:
            return float(a.get("_score", -1e30)) > float(b.get("_score", -1e30))
        # both infeasible: smaller distance wins
        return float(a.get("_dist", 1e30)) < float(b.get("_dist", 1e30))

    best = None
    archive: List[Dict[str, Any]] = []
    for g in range(int(generations)):
        for i in range(pop.shape[0]):
            # mutation indices
            idxs = [j for j in range(pop.shape[0]) if j != i]
            a,b,c = rng.choice(idxs, size=3, replace=False)
            xa, xb, xc = pop[a], pop[b], pop[c]
            v = xa + float(F) * (xb - xc)
            v = np.clip(v, lo, hi)
            # crossover
            jrand = rng.integers(0, dim)
            u = np.array([v[j] if (rng.random() < float(CR) or j==jrand) else pop[i,j] for j in range(dim)], dtype=float)
            u = np.clip(u, lo, hi)

            cand_res = _eval_vec(u)
            if keep_trace:
                trace.append({
                    "gen": g,
                    "feasible": bool(cand_res.get("feasible", False)),
                    "score": float(cand_res.get("_score", -1e30)),
                    "dist": float(cand_res.get("_dist", 1e30)),
                    "failure_mode": cand_res.get("failure_mode"),
                    "active_constraints": cand_res.get("active_constraints", []),
                })
            if _better(cand_res, pop_res[i]):
                pop[i] = u
                pop_res[i] = cand_res

            if cand_res.get("feasible", False):
                archive.append(cand_res)

        # track best feasible
        feas = [r for r in pop_res if r.get("feasible", False)]
        if feas:
            feas.sort(key=lambda r: float(r.get("_score",-1e30)), reverse=True)
            if best is None or float(feas[0].get("_score",-1e30)) > float(best.get("_score",-1e30)):
                best = feas[0]

    archive.sort(key=lambda r: float(r.get("_score",-1e30)), reverse=True)

    return {
        "kind": "optimization_sandbox_de_global_search",
        "seed": int(seed),
        "pop_size": int(pop_size),
        "generations": int(generations),
        "F": float(F),
        "CR": float(CR),
        "var_specs": [v.__dict__ for v in var_specs],
        "objectives": [o.__dict__ for o in objectives],
        "best_feasible": best,
        "archive": archive,
        "trace": trace,
        "resistance": summarize_resistance(trace),
    }


def surrogate_guided_rounds(
    *,
    evaluate_fn,
    anchor_inputs: Dict[str, Any],
    var_specs: List[VarSpec],
    objectives: List[Objective],
    n_init: int = 300,
    rounds: int = 8,
    proposal_pool: int = 3000,
    top_take: int = 80,
    seed: int = 1,
) -> Dict[str, Any]:
    """Surrogate-guided acceleration:
    - Random initial design of experiments
    - Train feasibility classifier + score regressor
    - Propose candidates maximizing P(feasible)*score
    """
    rng = np.random.default_rng(int(seed))
    keys = [v.key for v in var_specs]
    lo = np.array([v.lo for v in var_specs], dtype=float)
    hi = np.array([v.hi for v in var_specs], dtype=float)
    dim = len(keys)
    if dim == 0:
        raise ValueError("No variables selected")

    def _eval_x(x: np.ndarray) -> Dict[str, Any]:
        cand = dict(anchor_inputs)
        for k,vv in zip(keys, x.tolist()):
            cand[k] = float(vv)
        res = evaluate_fn(cand)
        out = res.get("outputs", {}) or {}
        res["_score"] = scalar_score(out, objectives)
        res["_dist"] = constraint_distance(res.get("constraints", []))
        return res

    # init
    X = rng.uniform(lo, hi, size=(int(n_init), dim))
    evals: List[Dict[str, Any]] = []
    trace: List[Dict[str, Any]] = []
    for i in range(X.shape[0]):
        r = _eval_x(X[i])
        evals.append(r)
        trace.append({"phase":"init", "idx": i, "feasible": bool(r.get("feasible",False)), "score": float(r.get("_score",-1e30)),
                      "dist": float(r.get("_dist",1e30)), "failure_mode": r.get("failure_mode"), "active_constraints": r.get("active_constraints",[]) })

    if RandomForestRegressor is None or RandomForestClassifier is None:
        # fallback: no sklearn
        feas = [e for e in evals if e.get("feasible", False)]
        feas.sort(key=lambda r: float(r.get("_score",-1e30)), reverse=True)
        return {
            "kind": "optimization_sandbox_surrogate_guided",
            "warning": "sklearn unavailable; returned init DOE results only.",
            "best_feasible": feas[0] if feas else None,
            "archive": feas,
            "trace": trace,
            "resistance": summarize_resistance(trace),
        }

    def _features(e: Dict[str, Any]) -> List[float]:
        return [ _safe_float(e.get("inputs", {}).get(k)) for k in keys ]

    for rr in range(int(rounds)):
        # train on all evals so far
        Xtr = np.array([_features(e) for e in evals], dtype=float)
        yfeas = np.array([1 if e.get("feasible", False) else 0 for e in evals], dtype=int)
        yscore = np.array([float(e.get("_score",-1e30)) for e in evals], dtype=float)

        clf = RandomForestClassifier(n_estimators=200, random_state=int(seed)+rr, max_depth=12)
        reg = RandomForestRegressor(n_estimators=300, random_state=int(seed)+rr, max_depth=14)
        clf.fit(Xtr, yfeas)
        reg.fit(Xtr, yscore)

        # propose
        P = rng.uniform(lo, hi, size=(int(proposal_pool), dim))
        pfeas = clf.predict_proba(P)[:,1]
        pscore = reg.predict(P)
        util = pfeas * pscore
        idx = np.argsort(util)[::-1][: int(top_take)]
        for j,ii in enumerate(idx):
            r = _eval_x(P[ii])
            evals.append(r)
            trace.append({"phase":"guided", "round": rr, "rank": j, "feasible": bool(r.get("feasible",False)),
                          "score": float(r.get("_score",-1e30)), "dist": float(r.get("_dist",1e30)),
                          "failure_mode": r.get("failure_mode"), "active_constraints": r.get("active_constraints",[]) })

    feas = [e for e in evals if e.get("feasible", False)]
    feas.sort(key=lambda r: float(r.get("_score",-1e30)), reverse=True)
    best = feas[0] if feas else None
    return {
        "kind": "optimization_sandbox_surrogate_guided",
        "seed": int(seed),
        "n_init": int(n_init),
        "rounds": int(rounds),
        "proposal_pool": int(proposal_pool),
        "top_take": int(top_take),
        "var_specs": [v.__dict__ for v in var_specs],
        "objectives": [o.__dict__ for o in objectives],
        "best_feasible": best,
        "archive": feas,
        "trace": trace,
        "resistance": summarize_resistance(trace),
    }


def build_candidate_archive(
    *,
    feasible_candidates: List[Dict[str, Any]],
    var_specs: List[VarSpec],
    objectives: List[Objective],
    topk: int = 50,
    keep_pareto: bool = True,
) -> Dict[str, Any]:
    """Build a candidate machine archive: ranked list + (optional) non-dominated front."""
    keys = [v.key for v in var_specs]
    feas = feasible_candidates[:] if feasible_candidates else []
    feas.sort(key=lambda r: float(r.get("_score",-1e30)), reverse=True)
    top = feas[: int(topk)]
    top = diversity_prune(top, keys, min(len(top), int(topk)))

    pareto = []
    if keep_pareto and len(top) >= 2 and len(objectives) >= 2:
        Y = np.array([_objective_vector((t.get("outputs",{}) or {}), objectives) for t in top], dtype=float)
        m = np.all(np.isfinite(Y), axis=1)
        Y = Y[m]
        top2 = [t for t,ok in zip(top, m.tolist()) if ok]
        if len(top2) >= 2:
            nd = nondominated_mask(Y)
            pareto = [t for t,kp in zip(top2, nd.tolist()) if kp]

    return {
        "ranked": top,
        "pareto": pareto,
        "objectives": [o.__dict__ for o in objectives],
        "variables": [v.__dict__ for v in var_specs],
    }
