from __future__ import annotations

"""
Feasible-only optimizer client for SHAMS (external selection layer).

This client is intentionally outside the frozen evaluator:
- It queries the evaluator as a black box.
- It never modifies physics closures, constraints, or truth.
- It performs deterministic sampling and feasible-only selection.

Outputs
-------
Creates an evidence pack directory under:
<repo_root>/runs/optimizer/<run_id>/

Evidence pack contains:
- run_config.json
- meta.json
- progress.json (updated during run)
- records.json (all samples)
- best.json (best feasible by objective contract)
- summary.json (dominant failure histogram, feasible yield)
- log.txt
- manifest.sha256 (hashes)

Determinism
-----------
- Sampling is deterministic for a given (seed, bounds, fixed/caps, n).
- Run directory name is deterministic up to the UTC timestamp prefix. The config hash suffix is deterministic.

v230.0: External Optimizer UI Console Bundle
© 2026 Afshin Arjhangmehr
"""

import argparse
import json
import math
import os
import time
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import numpy as np

import sys
# Make src importable when run from repo root or UI
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from evaluator.core import Evaluator
from models.inputs import PointInputs
from constraints.constraints import evaluate_constraints


# -----------------------------
# Utilities
# -----------------------------

def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()
def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, obj: Any, *, indent: int = 2, sort_keys: bool = True) -> None:
    path.write_text(json.dumps(obj, indent=indent, sort_keys=sort_keys), encoding="utf-8")


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _c_margin(c: Any) -> float:
    """Return signed margin for a constraint, robust to schema."""
    m = getattr(c, "margin", None)
    try:
        if callable(m):
            v = float(m())
        else:
            v = float(m)
        return v
    except Exception:
        return float("nan")
# -----------------------------
# Mechanism guidance helpers (v252)
# -----------------------------

def _choose_mechanism_condition(mode: str, last_dom_mech: str, mech_trace: List[str], available: List[str]) -> str:
    """Choose a mechanism label to condition client-side proposal scoring.

    mode:
      - neutral: keep last_dom_mech (default)
      - avoid: focus on last_dom_mech
      - seek: deterministically choose a *different* mechanism with lowest recent count (diversify)
    """
    mode = str(mode or "neutral").strip().lower()
    last = str(last_dom_mech or "GENERAL").upper()
    avail = sorted({str(a).upper() for a in (available or []) if a})
    if not avail:
        return last
    if mode in ("neutral", "avoid"):
        return last if last in avail else avail[0]
    # seek: pick a different mechanism if possible, preferring rarely-seen
    recent = [str(s or "GENERAL").upper() for s in (mech_trace or [])][-200:]
    counts = {a: 0 for a in avail}
    for s in recent:
        if s in counts:
            counts[s] += 1
    # exclude last if there are alternatives
    candidates = [a for a in avail if a != last] or avail
    # deterministic: sort by (count, name)
    candidates.sort(key=lambda a: (counts.get(a, 0), a))
    return candidates[0]


# -----------------------------
# Scenario robustness (deterministic scenario cube)
# -----------------------------

def _make_scenarios(base: Dict[str, Any], scenario_factors: Dict[str, List[float]], scenario_max: int) -> List[Dict[str, Any]]:
    """Deterministically generate scenario input dictionaries by applying multiplicative factors.

    Only keys present in 'base' and numeric are perturbed.
    Generates a corner cube (2^k) truncated to scenario_max, in deterministic key order.
    """
    keys = sorted([k for k in scenario_factors.keys() if k in base])
    # Filter to numeric
    kk = []
    for k in keys:
        try:
            float(base[k])
            kk.append(k)
        except Exception:
            continue
    keys = kk
    if not keys:
        return [dict(base)]
    # Corner combinations
    combos: List[List[float]] = []
    for k in keys:
        lo, hi = scenario_factors[k]
        combos.append([lo, hi])
    scenarios: List[Dict[str, Any]] = []
    # Deterministic binary enumeration
    ncomb = 1 << len(keys)
    for mask in range(ncomb):
        if len(scenarios) >= scenario_max:
            break
        d = dict(base)
        for i, k in enumerate(keys):
            fac = combos[i][(mask >> i) & 1]
            try:
                d[k] = float(d[k]) * float(fac)
            except Exception:
                pass
        scenarios.append(d)
    return scenarios

def _worst_hard_margin(constraints: List[Any]) -> float:
    worst = float("inf")
    for c in constraints:
        if str(getattr(c, "severity", "hard")) != "hard":
            continue
        m = _c_margin(c)
        if math.isfinite(m) and m < worst:
            worst = m
    return float("nan") if worst == float("inf") else float(worst)

def _scenario_robust_metrics(
    evaluator: Evaluator,
    policy: str,
    base_inputs: Dict[str, Any],
    scenario_factors: Dict[str, List[float]],
    scenario_max: int,
) -> Dict[str, Any]:
    scenarios = _make_scenarios(base_inputs, scenario_factors, scenario_max)
    n = len(scenarios)
    n_pass = 0
    worst_margin = float("inf")
    for s in scenarios:
        inp = _filter_pointinputs(s)
        res = evaluator.evaluate(inp)
        out = dict(res.out or {})
        cs = evaluate_constraints(out)
        cand = _is_candidate(policy, cs)
        if cand:
            n_pass += 1
        wm = _worst_hard_margin(cs)
        if math.isfinite(wm) and wm < worst_margin:
            worst_margin = wm
    if worst_margin == float("inf"):
        worst_margin = float("nan")
    pass_frac = float(n_pass) / float(n) if n > 0 else 0.0
    return {
        "scenario_n": int(n),
        "scenario_pass": int(n_pass),
        "scenario_pass_frac": float(pass_frac),
        "scenario_worst_hard_margin": float(worst_margin),
    }

# -----------------------------
# Boundary tracing (deterministic constraint-surface walking)
# -----------------------------

def _boundary_trace(
    rng: np.random.Generator,
    bounds: Dict[str, Tuple[float, float]],
    seed_inputs: Dict[str, Any],
    fixed: Dict[str, Any],
    caps: Dict[str, Any],
    objective_key: str,
    objective_dir: str,
    policy: str,
    evaluator: Evaluator,
    *,
    steps: int,
    step_frac: float,
    tol: float,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Trace the feasibility boundary by pushing objective and backtracking to keep feasibility.

    Outputs:
      - records: all evaluated points
      - frontier: subset where min hard margin is within [0, tol]
    """
    # Start at seed (clipped)
    x = {}
    for k,(lo,hi) in bounds.items():
        v = seed_inputs.get(k, (lo+hi)/2.0)
        try: v=float(v)
        except Exception: v=(lo+hi)/2.0
        x[k]=min(max(v,lo),hi)
    records=[]
    frontier=[]
    # choose a deterministic knob order for objective push
    knob_order = list(bounds.keys())
    knob_order.sort()
    # evaluate start
    def eval_point(xx, tag):
        d=dict(xx); d.update(fixed); d.update(caps)
        inp=_filter_pointinputs(d)
        res=evaluator.evaluate(inp)
        out=dict(res.out or {})
        cs=evaluate_constraints(out)
        cand=_is_candidate(policy, cs)
        obj=float(out.get(objective_key, float("nan")))
        if objective_dir=="min" and math.isfinite(obj):
            obj=-obj
        wm=_worst_hard_margin(cs)
        dom=_dominant_failure(cs)
        dom_mech=str(getattr(next((c for c in cs if str(getattr(c,"severity","hard"))=="hard" and not _c_passed(c)), None),"mechanism_group","GENERAL") or "GENERAL")
        rec={"inputs":d, "candidate":bool(cand), "objective":obj, "worst_hard_margin":wm, "dominant_constraint":dom, "dominant_mechanism":dom_mech, "phase":tag}
        return rec
    r0=eval_point(x,"boundary_start")
    records.append(r0)
    # If start not feasible, nothing to trace.
    if not r0["candidate"]:
        return records, frontier
    # step size based on ranges
    step_size={k: max(1e-12, step_frac*(hi-lo)) for k,(lo,hi) in bounds.items()}
    for i in range(steps):
        # propose move: pick knob deterministically by cycling, but direction from objective trend (random tiebreak deterministic via rng)
        k = knob_order[i % len(knob_order)]
        lo,hi=bounds[k]
        # direction: try increasing knob first, then decreasing if no improvement
        for dir_sign in (+1.0, -1.0):
            xt=dict(x)
            xt[k]=min(max(xt[k]+dir_sign*step_size[k], lo), hi)
            # backtrack to restore feasibility if needed
            bt=1.0
            rec=None
            for _ in range(20):
                rec=eval_point(xt,"boundary_step")
                records.append(rec)
                if rec["candidate"]:
                    break
                bt*=0.5
                xt[k]=min(max(x[k]+dir_sign*bt*step_size[k], lo), hi)
            if rec and rec["candidate"]:
                # accept move
                x= {kk: float(xt[kk]) for kk in x.keys()}
                # frontier point if close to boundary
                wm=float(rec.get("worst_hard_margin", float("nan")))
                if math.isfinite(wm) and (wm >= 0.0) and (wm <= tol):
                    frontier.append(rec)
                break
    return records, frontier



# -----------------------------
# Mechanism-conditioned surrogate guidance (deterministic, dependency-free)
# -----------------------------

def _norm_vec(d: Dict[str, float], bounds: Dict[str, Tuple[float, float]]) -> np.ndarray:
    xs = []
    for k,(lo,hi) in bounds.items():
        v = float(d.get(k, lo))
        den = (hi - lo) if (hi - lo) != 0 else 1.0
        xs.append((v - lo)/den)
    return np.array(xs, dtype=float)

class _DiagGauss:
    def __init__(self, dim: int):
        self.n = 0
        self.mean = np.zeros(dim, dtype=float)
        self.m2 = np.zeros(dim, dtype=float)  # sum of squares of diffs
    def update(self, x: np.ndarray) -> None:
        x = np.asarray(x, dtype=float)
        if x.ndim != 1:
            x = x.reshape(-1)
        self.n += 1
        delta = x - self.mean
        self.mean += delta / max(self.n, 1)
        delta2 = x - self.mean
        self.m2 += delta * delta2
    def var(self) -> np.ndarray:
        if self.n < 2:
            return np.ones_like(self.mean)
        v = self.m2 / max(self.n - 1, 1)
        v = np.maximum(v, 1e-6)
        return v
    def score(self, x: np.ndarray) -> float:
        # exp(-0.5 * sum((x-mean)^2/var)) (diag gaussian)
        x = np.asarray(x, dtype=float).reshape(-1)
        v = self.var()
        z2 = np.sum(((x - self.mean)**2) / v)
        return float(np.exp(-0.5 * z2))

def _surrogate_score(xn: np.ndarray, feas: _DiagGauss, fails: Dict[str, _DiagGauss]) -> float:
    # Feasible likelihood
    p_ok = feas.score(xn) if feas.n >= 5 else 0.0
    if p_ok <= 0:
        return 0.0
    # Penalize regions near observed failure clusters (mechanism-conditioned)
    p_bad = 0.0
    for _k, mdl in (fails or {}).items():
        if mdl.n >= 5:
            p_bad = max(p_bad, mdl.score(xn))
    return float(p_ok * (1.0 - p_bad))

def _sigmoid(z: float) -> float:
    try:
        if z >= 0:
            ez = math.exp(-z)
            return 1.0 / (1.0 + ez)
        else:
            ez = math.exp(z)
            return ez / (1.0 + ez)
    except Exception:
        return 0.5


class _MechFeasClassifier:
    """Lightweight mechanism-conditioned feasibility classifier.

    Deterministic, dependency-free. Uses diagonal Gaussian likelihood ratio:
      score = log p(x|feasible) - log p(x|fail_mech)
    and maps to (0,1) with a sigmoid.

    Positives (feasible) are shared across mechanisms. Negatives are per mechanism.
    """

    def __init__(self, dim: int, mech: str):
        self.mech = str(mech)
        self.pos = _DiagGauss(dim)
        self.neg = _DiagGauss(dim)

    def update_pos(self, xn: np.ndarray) -> None:
        self.pos.update(xn)

    def update_neg(self, xn: np.ndarray) -> None:
        self.neg.update(xn)

    def ready(self, min_pos: int = 10, min_neg: int = 10) -> bool:
        return (self.pos.n >= min_pos) and (self.neg.n >= min_neg)

    def prob_feasible(self, xn: np.ndarray) -> float:
        # Likelihood ratio under diagonal Gaussians; stable in log-domain.
        xn = np.asarray(xn, dtype=float).reshape(-1)
        v_pos = self.pos.var()
        v_neg = self.neg.var()
        # -0.5 sum((x-mean)^2/var) - 0.5 sum(log var)
        lp = -0.5 * float(np.sum(((xn - self.pos.mean) ** 2) / v_pos + np.log(v_pos)))
        ln = -0.5 * float(np.sum(((xn - self.neg.mean) ** 2) / v_neg + np.log(v_neg)))
        return float(_sigmoid(lp - ln))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mechanism": self.mech,
            "n_pos": int(self.pos.n),
            "n_neg": int(self.neg.n),
            "pos_mean": self.pos.mean.tolist(),
            "neg_mean": self.neg.mean.tolist(),
            "pos_var": self.pos.var().tolist(),
            "neg_var": self.neg.var().tolist(),
        }

def _c_passed(c: Any) -> bool:
    try:
        return bool(getattr(c, "passed", getattr(c, "ok", True)))
    except Exception:
        return True

def _now_utc_fs() -> str:
    return time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    if cfg.get("schema") not in ("extopt_config.v1", "extopt_config.v251", "feasible_opt.v1"):
        raise ValueError("config schema must be extopt_config.v1 (UI) or feasible_opt.v1 (legacy)")
    n = int(cfg.get("n", 200))
    if n < 1 or n > 500000:
        raise ValueError("n out of range")
    seed = int(cfg.get("seed", 0))
    objective = str(cfg.get("objective", "P_net_MW"))
    policy = str(cfg.get("policy", "strict_pass"))
    # Objective Contract (explicit selection contract; evaluator remains immutable)
    obj_contract = cfg.get("objective_contract", None)
    contract_obj_dir = ""
    if isinstance(obj_contract, dict) and str(obj_contract.get("schema", "")).strip() in ("objective_contract.v2", "objective_contract.v3"):
        prim = obj_contract.get("primary", {}) or {}
        schema = str(obj_contract.get("schema", "")).strip()
        if schema == "objective_contract.v3":
            objs = obj_contract.get("objectives", []) or []
            if isinstance(objs, list) and objs:
                o0 = objs[0] if isinstance(objs[0], dict) else {}
                objective = str(o0.get("key", objective))
                contract_obj_dir = str(o0.get("sense", "") or "").lower().strip()
            else:
                contract_obj_dir = ""
            selection = obj_contract.get("selection", {}) or {}
            ordering = selection.get("ordering", None)
        else:
            try:
                objective = str(prim.get("key", objective))
            except Exception:
                pass
            # objective_direction from contract is optional; legacy defaults apply if missing/invalid.
            try:
                contract_obj_dir = str(prim.get("direction", "") or "").lower().strip()
            except Exception:
                contract_obj_dir = ""
            ordering = obj_contract.get("ordering", None)
        if isinstance(ordering, list) and ordering:
            try:
                robustness_first = (ordering.index("worst_hard_margin") < ordering.index("objective"))
            except Exception:
                pass

    obj_dir = str(cfg.get("objective_direction", "") or contract_obj_dir or "").lower().strip()
    if obj_dir not in ("", "min", "max"):
        raise ValueError("objective_direction must be min or max")
    if obj_dir == "":
        # backward-compatible defaults
        obj_dir = "min" if objective in ("CAPEX_$", "recirc_frac") else "max"
    design_intent = str(cfg.get("design_intent", "Reactor"))
    if design_intent.lower() not in ("reactor","research"):
        design_intent = "Reactor"
    # A1: robustness-first defaults ON for Reactor intent if not explicitly provided
    if "robustness_first" not in cfg:
        robustness_first = (design_intent.lower() == "reactor")
    else:
        robustness_first = bool(cfg.get("robustness_first", False))
    constraint_aware = bool(cfg.get("constraint_aware", True))
    multi_island = bool(cfg.get("multi_island", True))
    surrogate_guidance = bool(cfg.get("surrogate_guidance", (design_intent.lower() == "reactor")))
    mechanism_classifier = bool(cfg.get("mechanism_classifier", (design_intent.lower() == "reactor")))
    mech_min_pos = int(cfg.get("mech_min_pos", 10))
    mech_min_neg = int(cfg.get("mech_min_neg", 10))
    mech_batch = int(cfg.get("mech_batch", 64))
    if mech_batch < 8 or mech_batch > 4096: raise ValueError("mech_batch out of range")
    if mech_min_pos < 5 or mech_min_pos > 1000: raise ValueError("mech_min_pos out of range")
    if mech_min_neg < 5 or mech_min_neg > 1000: raise ValueError("mech_min_neg out of range")
    if mech_batch < 8 or mech_batch > 4096: raise ValueError("mech_batch out of range")
    sensitivity_step = bool(cfg.get("sensitivity_step", True))
    hybrid_guidance = bool(cfg.get("hybrid_guidance", False))
    # Hybrid guidance enforces the safe ordering: sensitivities → mechanism steering → surrogate.
    if hybrid_guidance:
        sensitivity_step = True
        constraint_aware = True
        surrogate_guidance = True
        mechanism_classifier = True
    sens_step_frac = float(cfg.get("sens_step_frac", 0.05))
    surrogate_guidance = bool(cfg.get("surrogate_guidance", True))
    constraint_aware = bool(cfg.get("constraint_aware", True))
    multi_island = bool(cfg.get("multi_island", True))
    robustness_first = bool(cfg.get("robustness_first", False))
    hybrid_guidance = bool(cfg.get("hybrid_guidance", False))
    mechanism_classifier = bool(cfg.get("mechanism_classifier", False))
    mech_min_pos = int(cfg.get("mech_min_pos", 10))
    mech_min_neg = int(cfg.get("mech_min_neg", 10))
    mech_batch = int(cfg.get("mech_batch", 64))
    if sens_step_frac <= 0 or sens_step_frac > 0.5:
        raise ValueError("sens_step_frac out of range (0,0.5]")
    strategy = str(cfg.get("strategy", "random") or "random").strip()
    if strategy not in ("random", "scan_seeded_pattern", "boundary_trace", "boundary_trace_multi"):
        raise ValueError("strategy must be random, scan_seeded_pattern, boundary_trace, or boundary_trace_multi")
    seeds = cfg.get("seeds", []) or []
    if not isinstance(seeds, list):
        raise ValueError("seeds must be a list")
    seed_source = cfg.get("seed_source", {}) or {}
    if not isinstance(seed_source, dict):
        raise ValueError("seed_source must be an object")
    if policy not in ("strict_pass", "pass_plus_diag"):
        raise ValueError("policy must be strict_pass or pass_plus_diag")
    bounds = cfg.get("bounds", {}) or {}
    if not isinstance(bounds, dict) or not bounds:
        raise ValueError("bounds must be a non-empty object")
    fixed = cfg.get("fixed", {}) or {}
    caps = cfg.get("caps", {}) or {}
    if not isinstance(fixed, dict) or not isinstance(caps, dict):
        raise ValueError("fixed and caps must be objects")

    # Parse bounds
    b2: Dict[str, Tuple[float, float]] = {}
    for k, v in bounds.items():
        if not (isinstance(v, list) and len(v) == 2):
            raise ValueError(f"bounds[{k}] must be [lo, hi]")
        lo, hi = float(v[0]), float(v[1])
        if not (math.isfinite(lo) and math.isfinite(hi) and hi > lo):
            raise ValueError(f"invalid bounds for {k}: lo={lo}, hi={hi}")
        b2[str(k)] = (lo, hi)

    out = dict(cfg)
    out["n"] = n
    out["seed"] = seed
    out["objective"] = objective
    if isinstance(cfg.get("objective_contract", None), dict):
        out["objective_contract"] = cfg.get("objective_contract")
    out["policy"] = policy
    out["objective_direction"] = obj_dir
    out["strategy"] = strategy
    out["seeds"] = seeds
    out["seed_source"] = seed_source
    out["design_intent"] = design_intent
    out["robustness_first"] = bool(robustness_first)
    out["constraint_aware"] = bool(constraint_aware)
    out["multi_island"] = bool(multi_island)
    out["hybrid_guidance"] = bool(hybrid_guidance)
    out["surrogate_guidance"] = bool(surrogate_guidance)
    out["sensitivity_step"] = bool(sensitivity_step)
    out["sens_step_frac"] = float(sens_step_frac)
    out["mechanism_classifier"] = bool(mechanism_classifier)
    out["mech_min_pos"] = int(mech_min_pos)
    out["mech_min_neg"] = int(mech_min_neg)
    out["mech_batch"] = int(mech_batch)
    # v252: mechanism switch mode (client-side guidance only)
    msm = str(cfg.get("mechanism_switch_mode", "neutral") or "neutral").strip().lower()
    if msm not in ("neutral","avoid","seek"):
        raise ValueError("mechanism_switch_mode must be neutral, avoid, or seek")
    out["mechanism_switch_mode"] = msm
    # Suggested v241+ upgrades: boundary tracing and scenario-robust selection
    out["scenario_robustness"] = bool(cfg.get("scenario_robustness", False))
    out["scenario_max"] = int(cfg.get("scenario_max", 16))
    if out["scenario_max"] < 1 or out["scenario_max"] > 128:
        raise ValueError("scenario_max out of range")
    # scenario_factors: {key: [low, high]} multiplicative factors applied to numeric inputs if key exists
    sf_raw = cfg.get("scenario_factors", {}) or {}
    scenario_factors: Dict[str, List[float]] = {}
    if isinstance(sf_raw, dict):
        for k, vv in sf_raw.items():
            if not isinstance(k, str):
                continue
            if isinstance(vv, (list, tuple)) and len(vv) == 2:
                try:
                    lo = float(vv[0]); hi = float(vv[1])
                except Exception:
                    continue
                if lo <= 0 or hi <= 0:
                    continue
                scenario_factors[k] = [lo, hi]

    out["scenario_factors"] = scenario_factors

    # Scenario preset (UQ-lite library; authority/intent-tied defaults)
    # Supported:
    #   - "custom" (no auto-fill)
    #   - legacy: proxy/parametric/external (mapped by design_intent)
    #   - library presets, e.g. "proxy (research)", "external (reactor)"
    preset_raw = str(cfg.get("scenario_preset", "") or "").strip()
    preset = preset_raw.strip().lower()
    if preset in ("", "custom", "(custom)"):
        preset = "custom"

    # Map legacy short names to intent-specific library presets
    if preset in ("proxy", "parametric", "external"):
        intent = str(design_intent or "research").strip().lower()
        if intent not in ("research", "reactor"):
            intent = "research"
        preset = f"{preset} ({intent})"

    # Validate against library presets if possible
    try:
        from tools.scenario_library import preset_names, get_preset  # type: ignore
        allowed = {n.lower(): n for n in preset_names()}
        if preset != "custom" and preset not in allowed:
            # If user passed a mixed-case name, normalize
            if preset_raw.lower() in allowed:
                preset = preset_raw.lower()
            else:
                preset = "custom"
        out["scenario_preset"] = preset if preset == "custom" else allowed.get(preset, preset)
        # If robustness enabled and factors empty, auto-fill from library preset
        if out["scenario_robustness"] and (not out["scenario_factors"]) and out["scenario_preset"] != "custom":
            out["scenario_factors"] = get_preset(str(out["scenario_preset"]))
    except Exception:
        # Fallback (no library available)
        out["scenario_preset"] = preset if preset in ("custom",) else "custom"

    out["boundary_steps"] = int(cfg.get("boundary_steps", 30))
    out["boundary_tol"] = float(cfg.get("boundary_tol", 0.02))
    out["boundary_step_frac"] = float(cfg.get("boundary_step_frac", 0.05))
    if out["boundary_steps"] < 1 or out["boundary_steps"] > 10000:
        raise ValueError("boundary_steps out of range")
    if out["boundary_tol"] <= 0 or out["boundary_tol"] > 1.0:
        raise ValueError("boundary_tol out of range")
    if out["boundary_step_frac"] <= 0 or out["boundary_step_frac"] > 0.5:
        raise ValueError("boundary_step_frac out of range")

    out["bounds"] = {k: [lo, hi] for k, (lo, hi) in b2.items()}
    out["fixed"] = fixed
    out["caps"] = caps
    return out


def _dominant_failure(constraints: List[Any]) -> str:
    # Choose the worst hard constraint (most negative margin). If none, try diag.
    worst_name = "UNKNOWN"
    worst_margin = float("inf")
    for c in constraints:
        sev = getattr(c, "severity", "hard")
        passed = _c_passed(c)
        margin = _c_margin(c)
        name = getattr(c, "name", None) or getattr(c, "id", None) or "constraint"
        if sev == "hard" and not passed:
            try:
                m = float(margin)
            except Exception:
                m = float("nan")
            if math.isfinite(m) and m < worst_margin:
                worst_margin = m
                worst_name = str(name)
    if worst_name != "UNKNOWN":
        return worst_name
    # fallback
    for c in constraints:
        passed = _c_passed(c)
        if not passed:
            name = getattr(c, "name", None) or getattr(c, "id", None) or "constraint"
            return str(name)
    return "NONE"


def _is_candidate(policy: str, constraints: List[Any]) -> bool:
    # Candidate iff all hard constraints pass.
    for c in constraints:
        if getattr(c, "severity", "hard") == "hard" and not _c_passed(c):
            return False
    if policy == "strict_pass":
        # Also require diagnostics to pass (if they exist and have pass/fail semantics).
        for c in constraints:
            if getattr(c, "severity", "hard") != "hard" and not _c_passed(c):
                return False
    return True




def _objective_better(a: float, b: float, direction: str) -> bool:
    if not (math.isfinite(a) and math.isfinite(b)):
        return math.isfinite(a) and (not math.isfinite(b))
    if direction == "min":
        return a < b
    return a > b

def _candidate_better(a: Dict[str, Any], b: Dict[str, Any], *, objective_dir: str, robustness_first: bool, scenario_robustness: bool=False) -> bool:
    """Return True if candidate record a is better than b under selection policy.

    If robustness_first is True:
      primary: maximize worst_hard_margin (more positive = more robust)
      secondary: objective (min/max)

    Otherwise:
      primary: objective (min/max)
    """

    # Scenario-robust selection (if enabled and metrics available)
    if scenario_robustness:
        a_pf = float(a.get("scenario_pass_frac", float("nan")))
        b_pf = float(b.get("scenario_pass_frac", float("nan")))
        a_wm = float(a.get("scenario_worst_hard_margin", float("nan")))
        b_wm = float(b.get("scenario_worst_hard_margin", float("nan")))
        # Prefer higher pass fraction, then higher worst-case margin
        a_pf_f = a_pf if math.isfinite(a_pf) else float("-inf")
        b_pf_f = b_pf if math.isfinite(b_pf) else float("-inf")
        if a_pf_f != b_pf_f:
            return a_pf_f > b_pf_f
        a_wm_f = a_wm if math.isfinite(a_wm) else float("-inf")
        b_wm_f = b_wm if math.isfinite(b_wm) else float("-inf")
        if a_wm_f != b_wm_f:
            return a_wm_f > b_wm_f
        # Fall through to robustness/objective policy
    a_obj = float(a.get("objective", float("nan")))
    b_obj = float(b.get("objective", float("nan")))
    a_m = float(a.get("worst_hard_margin", float("nan")))
    b_m = float(b.get("worst_hard_margin", float("nan")))

    if robustness_first:
        # Prefer finite margins; treat NaN as -inf.
        a_m_f = a_m if math.isfinite(a_m) else float("-inf")
        b_m_f = b_m if math.isfinite(b_m) else float("-inf")
        if a_m_f != b_m_f:
            return a_m_f > b_m_f
        return _objective_better(a_obj, b_obj, objective_dir)

    return _objective_better(a_obj, b_obj, objective_dir)



def _pattern_search(
    *,
    rng: np.random.Generator,
    bounds: Dict[str, Tuple[float, float]],
    seed_inputs: Dict[str, Any],
    fixed: Dict[str, Any],
    caps: Dict[str, Any],
    objective_key: str,
    objective_dir: str,
    policy: str,
    evaluator: Evaluator,
    budget: int,
    robustness_first: bool,
    constraint_aware: bool,
    sensitivity_step: bool,
    sens_step_frac: float,
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Deterministic feasible-only coordinate pattern search around a seed.

    - Never changes the frozen evaluator.
    - Rejects infeasible moves.
    - Stops after a fixed budget (reviewer-safe).
    """
    knobs = list(bounds.keys())
    def _knob_order(last: Optional[Dict[str, Any]]) -> List[str]:
        if not constraint_aware:
            return list(knobs)
        if not last:
            return list(knobs)
        # 1) dominant_inputs first (if present and in bounds)
        dom_inputs = last.get("dominant_inputs") or []
        ordered: List[str] = []
        for k in dom_inputs:
            kk = str(k)
            if kk in bounds and kk not in ordered:
                ordered.append(kk)
        # 2) mechanism-informed heuristics
        mech = str(last.get("dominant_mechanism") or "").upper()
        heur: List[str] = []
        if mech == "CONTROL":
            heur = [k for k in knobs if any(s in k.lower() for s in ("pf","vs","rwm","ctrl","wave","di_dt","v_pf","i_pf"))]
        elif mech == "EXHAUST":
            heur = [k for k in knobs if any(s in k.lower() for s in ("lambda","q_","p_sep","prad","rad","f_rad","te_tgt"))]
        elif mech == "MAGNETS":
            heur = [k for k in knobs if any(s in k.lower() for s in ("bt","b_peak","r0","a_","kappa","delta","build","tf"))]
        elif mech == "NEUTRONICS":
            heur = [k for k in knobs if any(s in k.lower() for s in ("tbr","shield","blanket","fw","nwl"))]
        elif mech == "PLASMA":
            heur = [k for k in knobs if any(s in k.lower() for s in ("ip","ngw","fg","h98","te","ti","ne","q95","beta"))]
        for k in heur:
            if k in bounds and k not in ordered:
                ordered.append(k)
        # 3) remaining
        order = _knob_order(records[-1] if records else None)
        for k in order:
            if k not in ordered:
                ordered.append(k)
        return ordered

    # Initialize x from seed, otherwise midpoint
    x = {}
    for k,(lo,hi) in bounds.items():
        if k in seed_inputs:
            try: x[k]=float(seed_inputs[k])
            except Exception: x[k]=(lo+hi)/2.0
        else:
            x[k]=(lo+hi)/2.0
        x[k]=min(max(x[k], lo), hi)

    # Initial step size: 10% of range (min absolute epsilon)
    step = {k: max(1e-12, 0.10*(hi-lo)) for k,(lo,hi) in bounds.items()}
    min_step = {k: max(1e-12, 0.001*(hi-lo)) for k,(lo,hi) in bounds.items()}

    records: List[Dict[str, Any]] = []
    best_rec: Optional[Dict[str, Any]] = None

    def _eval_at(xx: Dict[str, float], i_local: int) -> Dict[str, Any]:
        d = dict(xx)
        d.update(fixed); d.update(caps)
        inp = _filter_pointinputs(d)
        rec: Dict[str, Any] = {"i_local": i_local, "inputs": d}
        res = evaluator.evaluate(inp)
        out = dict(res.out or {})
        cs = evaluate_constraints(out)
        cand = _is_candidate(policy, cs)
        dom = _dominant_failure(cs)
        worst_hard = float("inf")
        dom_mech = "GENERAL"
        for cc in cs:
            if str(getattr(cc, "severity", "hard")) != "hard":
                continue
            if _c_passed(cc):
                continue
            mm = _c_margin(cc)
            if math.isfinite(mm) and mm < worst_hard:
                worst_hard = mm
                dom_mech = str(getattr(cc, "mechanism_group", "GENERAL") or "GENERAL")
        if worst_hard == float("inf"):
            worst_hard = float("nan")
        # Optional driver hints
        dom_inputs = out.get("dominant_inputs") or out.get("best_knobs") or []
        if not isinstance(dom_inputs, list):
            dom_inputs = []
        rec.update({
            "ok": bool(res.ok),
            "elapsed_s": float(res.elapsed_s),
            "candidate": bool(cand),
            "dominant_constraint": str(dom),
            "dominant_mechanism": str(dom_mech),
            "worst_hard_margin": float(worst_hard),
            "dominant_inputs": list(dom_inputs),
            "objective": float(out.get(objective_key, float("nan"))),
        })
        return rec

    # Evaluate seed point first
    i_local = 0
    rec0 = _eval_at(x, i_local)
    records.append(rec0)
    if rec0["candidate"]:
        best_rec = rec0

    # Coordinate exploration with step-halving
    while len(records) < budget:
        improved = False
        # Newton-lite: if failing and sensitivities available, try a single directed step
        if sensitivity_step and records and (not bool(records[-1].get("candidate", False))):
            dom_list = records[-1].get("dominant_inputs") or []
            best = None  # (abs_s, name, s)
            for it in dom_list:
                if not isinstance(it, dict):
                    continue
                name = it.get("name") or it.get("var") or it.get("knob")
                s = it.get("dmargin_dx")
                if s is None:
                    s = it.get("sensitivity") if it.get("sensitivity") is not None else it.get("grad")
                if name is None or str(name) not in bounds:
                    continue
                try:
                    sv = float(s)
                except Exception:
                    continue
                if not math.isfinite(sv) or sv == 0.0:
                    continue
                cand = (abs(sv), str(name), sv)
                if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[1] < best[1]):
                    best = cand
            if best is not None and len(records) < budget:
                _, k_s, sv = best
                lo, hi = bounds[k_s]
                cur = float(x[k_s])
                step_dir = 1.0 if sv > 0 else -1.0
                step_abs = max(1e-12, float(sens_step_frac) * (hi - lo))
                trial = dict(x)
                trial[k_s] = min(max(cur + step_dir * step_abs, lo), hi)
                i_local += 1
                rec = _eval_at(trial, i_local)
                records.append(rec)
                if rec.get("candidate"):
                    if best_rec is None or _candidate_better(rec, best_rec, objective_dir=objective_dir, robustness_first=robustness_first):
                        best_rec = rec
                        x = {kk: float(trial[kk]) for kk in knobs}
                        improved = True
        order = _knob_order(records[-1] if records else None)
        for k in order:
            if len(records) >= budget:
                break
            lo,hi = bounds[k]
            cur = x[k]
            for sgn in (+1.0, -1.0):
                if len(records) >= budget:
                    break
                trial = dict(x)
                trial[k] = min(max(cur + sgn*step[k], lo), hi)
                i_local += 1
                rec = _eval_at(trial, i_local)
                records.append(rec)
                if not rec["candidate"]:
                    continue
                if best_rec is None:
                    best_rec = rec
                    x = {kk: float(trial[kk]) for kk in knobs}
                    improved = True
                else:
                    if _candidate_better(rec, best_rec, objective_dir=objective_dir, robustness_first=robustness_first):
                        best_rec = rec
                        x = {kk: float(trial[kk]) for kk in knobs}
                        improved = True
        if not improved:
            # reduce step
            for k in knobs:
                step[k] *= 0.5
            # stop when all steps are small
            if all(step[k] <= min_step[k] for k in knobs):
                break

    return records, best_rec

def _filter_pointinputs(d: Dict[str, Any]) -> PointInputs:
    # Ignore unknown keys for forward/backward stability
    try:
        return PointInputs.from_dict(d)
    except Exception:
        fields = {f.name for f in PointInputs.__dataclass_fields__.values()}  # type: ignore
        dd = {k: v for k, v in d.items() if k in fields}
        return PointInputs(**dd)


def _write_manifest(run_dir: Path) -> None:
    lines: List[str] = []
    files = [p for p in run_dir.rglob("*") if p.is_file() and p.name != "manifest.sha256"]
    files.sort(key=lambda p: str(p.relative_to(run_dir)).replace(os.sep, "/"))
    for p in files:
        rel = str(p.relative_to(run_dir)).replace(os.sep, "/")
        lines.append(f"{_sha256_file(p)}  {rel}")
    (run_dir / "manifest.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


# -----------------------------
# Main
# -----------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", help="Path to extopt config JSON (preferred)")
    ap.add_argument("--repo-root", required=True, help="Path to SHAMS repo root")
    # Legacy CLI flags (kept for backward compatibility)
    ap.add_argument("--bounds", help="Legacy: Path to bounds JSON")
    ap.add_argument("--objective", help="Legacy: objective key")
    ap.add_argument("--n", type=int, help="Legacy: number of samples")
    ap.add_argument("--seed", type=int, help="Legacy: RNG seed")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        raise SystemExit(f"repo root does not exist: {repo_root}")

    # Load config
    cfg_path: Optional[Path] = Path(args.config).resolve() if args.config else None
    if cfg_path and not cfg_path.exists():
        raise SystemExit(f"config not found: {cfg_path}")

    if cfg_path:
        cfg_raw = _load_json(cfg_path)
    else:
        # Legacy mode: transform bounds format into extopt_config.v1-ish
        if not args.bounds:
            raise SystemExit("provide --config (preferred) or legacy --bounds")
        b = _load_json(Path(args.bounds))
        cfg_raw = {
            "schema": "feasible_opt.v1",
            "created_utc": _now_utc_fs().replace("-", ":").replace("Z", "Z"),
            "tag": "",
            "seed": int(args.seed or 0),
            "n": int(args.n or 200),
            "objective": str(args.objective or "P_net_MW"),
            "policy": "pass_plus_diag",
            "bounds": b.get("bounds", {}),
            "fixed": b.get("fixed", {}),
            "caps": b.get("caps", {}),
        }

    cfg = _validate_config(cfg_raw)

    # Create deterministic run directory
    runs_root = repo_root / "runs" / "optimizer"
    _ensure_dir(runs_root)

    cfg_bytes = json.dumps(cfg, indent=2, sort_keys=True).encode("utf-8")
    cfg_hash = _sha256_bytes(cfg_bytes)[:12]
    ts = _now_utc_fs()
    tag = str(cfg.get("tag", "")).strip()
    tag_part = f"_{tag}" if tag else ""
    run_id = f"{ts}_seed{cfg['seed']:04d}_N{cfg['n']:04d}{tag_part}_{cfg_hash}"
    run_dir = (runs_root / run_id).resolve()
    _ensure_dir(run_dir)

    # Write handshake for UI if config came from UI pending area
    if cfg_path:
        hs = cfg_path.with_suffix(".run_dir.txt")
        try:
            hs.write_text(str(run_dir), encoding="utf-8")
        except Exception:
            pass

    # Write immutable run config
    _write_json(run_dir / "run_config.json", cfg)
    if isinstance(cfg.get("objective_contract", None), dict):
            _write_json(run_dir / "objective_contract.json", cfg.get("objective_contract"))

    # Log file
    log_path = run_dir / "log.txt"
    log_f = open(log_path, "w", encoding="utf-8")
    def log(msg: str) -> None:
        log_f.write(msg.rstrip("\n") + "\n")
        log_f.flush()

    log(f"[run] {run_id}")
    log(f"[repo_root] {repo_root}")
    log(f"[objective] {cfg['objective']}  [policy] {cfg['policy']}")
    log(f"[bounds] {list(cfg['bounds'].keys())}")

    # Initialize evaluator
    ev = Evaluator(cache_enabled=True)
    rng = np.random.default_rng(int(cfg["seed"]))

    bounds = {k: (float(v[0]), float(v[1])) for k, v in cfg["bounds"].items()}
    fixed = cfg.get("fixed", {}) or {}
    caps = cfg.get("caps", {}) or {}
    objective_key = str(cfg["objective"])
    policy = str(cfg["policy"])
    n = int(cfg["n"])
    sensitivity_step = bool(cfg.get("sensitivity_step", True))
    sens_step_frac = float(cfg.get("sens_step_frac", 0.05))
    surrogate_guidance = bool(cfg.get("surrogate_guidance", True))
    constraint_aware = bool(cfg.get("constraint_aware", True))
    multi_island = bool(cfg.get("multi_island", True))
    robustness_first = bool(cfg.get("robustness_first", False))
    hybrid_guidance = bool(cfg.get("hybrid_guidance", False))
    mechanism_classifier = bool(cfg.get("mechanism_classifier", False))
    mech_min_pos = int(cfg.get("mech_min_pos", 10))
    mech_min_neg = int(cfg.get("mech_min_neg", 10))
    mech_batch = int(cfg.get("mech_batch", 64))
    mechanism_switch_mode = str(cfg.get("mechanism_switch_mode", "neutral") or "neutral").strip().lower()

    records: List[Dict[str, Any]] = []
    feasible: List[Dict[str, Any]] = []
    mech_trace: List[str] = []  # FEASIBLE or dominant mechanism for each evaluated record
    best: Optional[Dict[str, Any]] = None
    dominant_failures: Dict[str, int] = {}

    t0 = time.time()

    # Initial progress
    _write_json(run_dir / "progress.json", {"i": 0, "n": n, "n_feasible": 0, "last_verdict": "—", "last_dominant": "—"})


    strategy = str(cfg.get("strategy", "random"))
    design_intent = str(cfg.get("design_intent", "Reactor"))
    constraint_aware = bool(cfg.get("constraint_aware", True))
    multi_island = bool(cfg.get("multi_island", True))
    surrogate_guidance = bool(cfg.get("surrogate_guidance", (design_intent.lower() == "reactor")))
    mechanism_classifier = bool(cfg.get("mechanism_classifier", (design_intent.lower() == "reactor")))
    mech_min_pos = int(cfg.get("mech_min_pos", 10))
    mech_min_neg = int(cfg.get("mech_min_neg", 10))
    mech_batch = int(cfg.get("mech_batch", 64))
    if mech_batch < 8 or mech_batch > 4096: raise ValueError("mech_batch out of range")
    if mech_min_pos < 5 or mech_min_pos > 1000: raise ValueError("mech_min_pos out of range")
    if mech_min_neg < 5 or mech_min_neg > 1000: raise ValueError("mech_min_neg out of range")
    if mech_batch < 8 or mech_batch > 4096: raise ValueError("mech_batch out of range")
    hybrid_guidance = bool(cfg.get("hybrid_guidance", False))
    # Hybrid guidance forces sens+mechanism+surrogate ordering.
    if hybrid_guidance:
        surrogate_guidance = True
        constraint_aware = True
        sensitivity_step = True
    objective_dir = str(cfg.get("objective_direction", "max"))

    # Scenario-robust selection (v241+)
    scenario_robustness = bool(cfg.get("scenario_robustness", False))
    scenario_factors = cfg.get("scenario_factors", {}) or {}
    scenario_max = int(cfg.get("scenario_max", 16))
    # Boundary tracing parameters (v241+)
    boundary_steps = int(cfg.get("boundary_steps", 30))
    boundary_tol = float(cfg.get("boundary_tol", 0.02))
    boundary_step_frac = float(cfg.get("boundary_step_frac", 0.05))

    # Normalize seeds: list of dicts
    seeds_in: List[Dict[str, Any]] = []
    for s in (cfg.get("seeds") or []):
        if isinstance(s, dict):
            seeds_in.append(dict(s))

    
    # Boundary tracing strategy (deterministic feasibility frontier walking)
    if strategy == "boundary_trace":
        # Choose seed: first provided seed if any, otherwise midpoint of bounds
        seed_inputs = seeds_in[0] if seeds_in else {}
        recs_bt, frontier = _boundary_trace(
            rng=rng,
            bounds=bounds,
            seed_inputs=seed_inputs,
            fixed=fixed,
            caps=caps,
            objective_key=objective_key,
            objective_dir=objective_dir,
            policy=policy,
            evaluator=ev,
            steps=boundary_steps,
            step_frac=boundary_step_frac,
            tol=boundary_tol,
        )
        # Attach scenario robustness (optional) to frontier points only (to control cost)
        if scenario_robustness and scenario_factors:
            for rr in frontier:
                try:
                    m = _scenario_robust_metrics(ev, policy, rr.get("inputs", {}), scenario_factors, scenario_max)
                    rr.update(m)
                except Exception:
                    pass
        # Write artifacts
        try:
            import csv as _csv
            fp = run_dir / "frontier_points.csv"
            with open(fp, "w", newline="", encoding="utf-8") as f:
                w = _csv.DictWriter(f, fieldnames=sorted({k for r in frontier for k in r.keys()}))
                w.writeheader()
                for r in frontier:
                    w.writerow(r)
        except Exception:
            pass
        _write_json(run_dir / "boundary_frontier.json", {"frontier_n": len(frontier), "tol": boundary_tol, "points": frontier[:500]})
        try:
            _write_json(run_dir / "frontier_proof_pack.json", _frontier_proof_pack(frontier, bounds, objective_key=objective_key, objective_direction=objective_dir))
        except Exception:
            pass
        # Merge into records and proceed to normal evidence writing path
        for rr in recs_bt:
            rr2 = dict(rr)
            rr2["i"] = len(records)
            records.append(rr2)
            if rr2.get("candidate"):
                feasible.append(rr2)
        # Skip remaining budgets; write out and exit early
        meta = {
            "run_id": run_id,
            "strategy": strategy,
            "n": len(records),
            "n_feasible": len(feasible),
            "objective": objective_key,
            "objective_direction": objective_dir,
            "policy": policy,
            "scenario_robustness": scenario_robustness,
            "scenario_preset": str(cfg.get("scenario_preset", "custom")),
        }
        _write_json(run_dir / "meta.json", meta)
        _write_json(run_dir / "records.json", records)
        _write_json(run_dir / "best.json", {"best": None, "note": "boundary_trace produces frontier_points.csv"})
        _write_json(run_dir / "summary.json", {"dominant_failures": {}, "feasible_yield": (len(feasible)/max(1,len(records)))})
        _write_json(run_dir / "progress.json", {"i": len(records), "n": len(records), "n_feasible": len(feasible), "last_verdict": "DONE", "last_dominant": ""})
        _write_manifest(run_dir)
        log(f"[done] boundary_trace records={len(records)} frontier={len(frontier)}")
        log_f.close()
        print(json.dumps(meta, indent=2, sort_keys=True))
        return 0

    # Boundary tracing frontier families (per-island)
    if strategy == "boundary_trace_multi":
        # Group seeds by island_id (deterministic). If no seeds, fall back to a single pseudo-island.
        by_island: Dict[str, List[Dict[str, Any]]] = {}
        if seeds_in:
            for s in seeds_in:
                meta = s.get("_seed_meta") if isinstance(s, dict) else None
                isl = None
                if isinstance(meta, dict):
                    isl = meta.get("island_id")
                key = str(isl) if isl is not None else "none"
                by_island.setdefault(key, []).append(s)
        else:
            by_island["none"] = [{}]

        islands = [k for k in sorted(by_island.keys(), key=lambda x: (x == "none", x))]
        n_islands = max(1, len(islands))
        per_island_steps = int(max(5, boundary_steps // n_islands))

        frontiers_dir = run_dir / "frontiers"
        _ensure_dir(frontiers_dir)

        family_summary: Dict[str, Any] = {"islands": [], "family": True, "tol": boundary_tol}
        all_frontier: List[Dict[str, Any]] = []
        all_records: List[Dict[str, Any]] = []

        for isl_key in islands:
            seed_inputs = by_island[isl_key][0] if by_island.get(isl_key) else {}
            recs_bt, frontier = _boundary_trace(
                rng=rng,
                bounds=bounds,
                seed_inputs=seed_inputs,
                fixed=fixed,
                caps=caps,
                objective_key=objective_key,
                objective_dir=objective_dir,
                policy=policy,
                evaluator=ev,
                steps=per_island_steps,
                step_frac=boundary_step_frac,
                tol=boundary_tol,
            )
            for rr in recs_bt:
                rr["island_id"] = isl_key
            for rr in frontier:
                rr["island_id"] = isl_key

            if scenario_robustness and scenario_factors:
                for rr in frontier:
                    try:
                        m = _scenario_robust_metrics(ev, policy, rr.get("inputs", {}), scenario_factors, scenario_max)
                        rr.update(m)
                    except Exception:
                        pass

            try:
                import csv as _csv
                fp = frontiers_dir / f"frontier_island_{isl_key}.csv"
                with open(fp, "w", newline="", encoding="utf-8") as f:
                    w = _csv.DictWriter(f, fieldnames=sorted({k for r in frontier for k in r.keys()}))
                    w.writeheader()
                    for r in frontier:
                        w.writerow(r)
            except Exception:
                pass

            mech_counts: Dict[str, int] = {}
            for rr in frontier:
                m = str(rr.get("dominant_mechanism", "GENERAL"))
                mech_counts[m] = mech_counts.get(m, 0) + 1

            try:
                _write_json(frontiers_dir / f"frontier_proof_pack_island_{isl_key}.json", _frontier_proof_pack(frontier, bounds, objective_key=objective_key, objective_direction=objective_dir))
            except Exception:
                pass

            family_summary["islands"].append({
                "island_id": isl_key,
                "frontier_n": int(len(frontier)),
                "dominant_mechanism_counts": mech_counts,
            })

            all_frontier.extend(frontier)
            all_records.extend(recs_bt)

        try:
            import csv as _csv
            fp_all = run_dir / "frontier_points_all_islands.csv"
            with open(fp_all, "w", newline="", encoding="utf-8") as f:
                w = _csv.DictWriter(f, fieldnames=sorted({k for r in all_frontier for k in r.keys()}))
                w.writeheader()
                for r in all_frontier:
                    w.writerow(r)
        except Exception:
            pass

        _write_json(run_dir / "frontier_family_summary.json", family_summary)
        # v246.0: deterministic family narrative (publication-ready, UI-renderable)
        try:
            from tools.frontier_family_narrative import build_frontier_family_narrative  # type: ignore
            rep, md = build_frontier_family_narrative(run_dir)
            _write_json(run_dir / "frontier_family_narrative.json", rep)
            (run_dir / "frontier_family_narrative.md").write_text(md, encoding="utf-8")
        except Exception:
            pass
        _write_json(run_dir / "boundary_frontier.json", {"family": True, "frontier_n": len(all_frontier), "tol": boundary_tol, "points": all_frontier[:500]})
        try:
            _write_json(run_dir / "frontier_proof_pack_all_islands.json", _frontier_proof_pack(all_frontier, bounds, objective_key=objective_key, objective_direction=objective_dir))
        except Exception:
            pass

        for rr in all_records:
            rr2 = dict(rr)
            rr2["i"] = len(records)
            records.append(rr2)
            if rr2.get("candidate"):
                feasible.append(rr2)

        meta = {
            "run_id": run_id,
            "strategy": strategy,
            "n": len(records),
            "n_feasible": len(feasible),
            "objective": objective_key,
            "objective_direction": objective_dir,
            "policy": policy,
            "scenario_robustness": scenario_robustness,
            "scenario_preset": str(cfg.get("scenario_preset", "custom")),
            "scenario_preset": str(cfg.get("scenario_preset", "custom")),
            "frontier_family": True,
        }
        _write_json(run_dir / "meta.json", meta)
        _write_json(run_dir / "records.json", records)
        _write_json(run_dir / "best.json", {"best": None, "note": "boundary_trace_multi produces frontiers/*.csv"})
        _write_json(run_dir / "summary.json", {"dominant_failures": {}, "feasible_yield": (len(feasible)/max(1,len(records)))})
        _write_json(run_dir / "progress.json", {"i": len(records), "n": len(records), "n_feasible": len(feasible), "last_verdict": "DONE", "last_dominant": ""})
        _write_manifest(run_dir)
        log(f"[done] boundary_trace_multi islands={len(islands)} records={len(records)} frontier={len(all_frontier)}")
        log_f.close()
        print(json.dumps(meta, indent=2, sort_keys=True))
        return 0
# Allocate deterministic budgets
    budgets: List[Tuple[str, Optional[int], int]] = []  # (phase, seed_index, phase_budget)
    if strategy == "scan_seeded_pattern" and seeds_in:
        # Reserve ~70% budget for seeded local search, remainder for global random exploration.
        n_seed_total = int(max(1, round(0.70 * n)))
        n_rand = int(max(0, n - n_seed_total))

        # Optional multi-island grouping
        seed_groups: List[List[int]] = []
        if multi_island:
            by_island: Dict[str, List[int]] = {}
            for si, s in enumerate(seeds_in):
                meta = s.get("_seed_meta") if isinstance(s, dict) else None
                isl = None
                if isinstance(meta, dict):
                    isl = meta.get("island_id")
                key = str(isl) if isl is not None else "none"
                by_island.setdefault(key, []).append(si)
            seed_groups = [by_island[k] for k in sorted(by_island.keys(), key=lambda x: (x=="none", x))]
        else:
            seed_groups = [list(range(len(seeds_in)))]

        # Allocate budget per island then per seed (deterministic)
        n_islands = max(1, len(seed_groups))
        per_island = int(max(10, n_seed_total // n_islands))
        for g in seed_groups:
            per_seed = int(max(10, per_island // max(1, len(g))))
            for si in g:
                budgets.append(("seed_pattern", si, per_seed))

        budgets.append(("random", None, n_rand))
    else:
        budgets.append(("random", None, n))
    global_i = 0

    for phase, si, phase_budget in budgets:
        if phase_budget <= 0:
            continue

        if phase == "seed_pattern" and si is not None:
            seed_inputs = seeds_in[si]
            try:
                recs_local, best_local = _pattern_search(
                    rng=rng,
                    bounds=bounds,
                    seed_inputs=seed_inputs,
                    fixed=fixed,
                    caps=caps,
                    objective_key=objective_key,
                    objective_dir=objective_dir,
                    policy=policy,
                    evaluator=ev,
                    budget=phase_budget,
                    robustness_first=robustness_first,
                    constraint_aware=constraint_aware,
                    sensitivity_step=bool(sensitivity_step),
                    sens_step_frac=float(sens_step_frac),
                )
            except Exception as e:
                # Record a single error entry for this seed phase
                recs_local = [{
                    "i": global_i,
                    "phase": "seed_pattern",
                    "seed_index": int(si),
                    "ok": False,
                    "error": str(e),
                    "candidate": False,
                    "dominant_constraint": "EVALUATION_ERROR",
                    "objective": float("nan"),
                    "inputs": dict(seed_inputs),
                }]
            for rloc in recs_local:
                if global_i >= n:
                    break
                rec = {
                    "i": global_i,
                    "phase": "seed_pattern",
                    "seed_index": int(si),
                    "inputs": rloc.get("inputs", {}),
                    "ok": bool(rloc.get("ok", False)),
                    "elapsed_s": float(rloc.get("elapsed_s", float("nan"))),
                    "objective": float(rloc.get("objective", float("nan"))),
                    "candidate": bool(rloc.get("candidate", False)),
                    "dominant_constraint": str(rloc.get("dominant_constraint", "UNKNOWN")),
                    "dominant_mechanism": str(rloc.get("dominant_mechanism", "GENERAL")),
                    "worst_hard_margin": float(rloc.get("worst_hard_margin", float("nan"))),
                }
                if "error" in rloc:
                    rec["error"] = str(rloc["error"])
                records.append(rec)
                # Scenario robustness (optional; only for feasible candidates)
                if scenario_robustness and rec.get("candidate") and scenario_factors:
                    try:
                        m = _scenario_robust_metrics(ev, policy, dict(rec.get("inputs", {})), dict(scenario_factors), int(scenario_max))
                        rec.update(m)
                    except Exception:
                        pass
                # Mechanism trace (publishable search dynamics)
                mech_trace.append("FEASIBLE" if rec.get("candidate") else str(rec.get("dominant_mechanism","GENERAL")).upper())

                last_verdict = "PASS" if rec["candidate"] else ("ERROR" if ("error" in rec) else "FAIL")
                last_dom = rec["dominant_constraint"]

                if rec["candidate"]:
                    feasible.append(rec)
                    if best is None:
                        best = rec
                    else:
                        if _candidate_better(rec, best, objective_dir=objective_dir, robustness_first=robustness_first, scenario_robustness=scenario_robustness):
                            best = rec
                else:
                    dominant_failures[last_dom] = dominant_failures.get(last_dom, 0) + 1

                global_i += 1

                _write_json(run_dir / "progress.json", {
                    "i": global_i,
                    "n": n,
                    "n_feasible": len(feasible),
                    "last_verdict": last_verdict,
                    "last_dominant": last_dom,
                    "phase": phase,
                })

        if phase == "random":
            # Surrogate models (updated online). They never change truth; they only choose next query.
            dim = len(bounds)
            _feas_mdl = _DiagGauss(dim)
            _fail_mdls: Dict[str, _DiagGauss] = {}
            _mech_clfs: Dict[str, _MechFeasClassifier] = {}
            _mech_filter_stats: Dict[str, Any] = {"filtered": 0, "evaluated": 0, "by_mechanism": {}}

            last_out: Dict[str, Any] = {}
            last_dom_inputs: List[Any] = []
            last_dom_mech: str = "GENERAL"
            for _ in range(phase_budget):
                if global_i >= n:
                    break
                # Propose candidate (optionally surrogate-guided)
                d: Dict[str, Any] = {}
                # Hybrid proposal order: sensitivities → mechanism steering → surrogate → uniform.
                proposed = False

                if hybrid_guidance and sensitivity_step and last_dom_inputs:
                    best = None  # (abs_s, name, s)
                    for it in last_dom_inputs:
                        if not isinstance(it, dict):
                            continue
                        name = it.get("name") or it.get("var") or it.get("knob")
                        s = it.get("dmargin_dx")
                        if s is None:
                            s = it.get("sensitivity") if it.get("sensitivity") is not None else it.get("grad")
                        if name is None:
                            continue
                        k_s = str(name)
                        if k_s not in bounds:
                            continue
                        try:
                            sv = float(s)
                        except Exception:
                            continue
                        if not math.isfinite(sv) or sv == 0.0:
                            continue
                        cand = (abs(sv), k_s, sv)
                        if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[1] < best[1]):
                            best = cand
                    if best is not None:
                        _, k_s, sv = best
                        lo, hi = bounds[k_s]
                        cur = float(last_out.get(k_s, (lo + hi) / 2.0))
                        step_dir = 1.0 if sv > 0 else -1.0
                        step_abs = max(1e-12, float(sens_step_frac) * (hi - lo))
                        d[k_s] = float(min(max(cur + step_dir * step_abs, lo), hi))
                        for kk, (llo, hhi) in bounds.items():
                            if kk in d:
                                continue
                            if kk in last_out and isinstance(last_out.get(kk), (int, float)):
                                vv = float(last_out[kk])
                                jitter = (hhi - llo) * 0.01 * (2.0 * rng.random() - 1.0)
                                d[kk] = float(min(max(vv + jitter, llo), hhi))
                            else:
                                d[kk] = float(llo + (hhi - llo) * rng.random())
                        proposed = True

                if (not proposed) and hybrid_guidance and constraint_aware:
                    # Mechanism-informed small perturbation around last point if available
                    base: Dict[str, float] = {}
                    for kk, (llo, hhi) in bounds.items():
                        if kk in last_out and isinstance(last_out.get(kk), (int, float)):
                            base[kk] = float(min(max(float(last_out[kk]), llo), hhi))
                        else:
                            base[kk] = float(llo + (hhi - llo) * rng.random())
                    mech = str(last_dom_mech or "GENERAL").upper()
                    heur: List[str] = []
                    if mech == "CONTROL":
                        heur = [k for k in bounds.keys() if any(s in k.lower() for s in ("pf","vs","rwm","ctrl","wave","di_dt","v_pf","i_pf"))]
                    elif mech == "EXHAUST":
                        heur = [k for k in bounds.keys() if any(s in k.lower() for s in ("lambda","q_","p_sep","prad","rad","f_rad","te_tgt"))]
                    elif mech == "MAGNETS":
                        heur = [k for k in bounds.keys() if any(s in k.lower() for s in ("bt","b_peak","r0","a_","kappa","delta","build","tf"))]
                    elif mech == "NEUTRONICS":
                        heur = [k for k in bounds.keys() if any(s in k.lower() for s in ("tbr","shield","blanket","fw","nwl"))]
                    elif mech == "PLASMA":
                        heur = [k for k in bounds.keys() if any(s in k.lower() for s in ("ip","ngw","fg","h98","te","ti","ne","q95","beta"))]
                    k_pick = None
                    for kk in heur:
                        if kk in bounds:
                            k_pick = kk
                            break
                    if k_pick is not None:
                        llo, hhi = bounds[k_pick]
                        cur = base[k_pick]
                        step_abs = max(1e-12, 0.05 * (hhi - llo))
                        step_dir = 1.0 if rng.random() < 0.5 else -1.0
                        base[k_pick] = float(min(max(cur + step_dir * step_abs, llo), hhi))
                        d.update(base)
                        proposed = True

                if (not proposed) and surrogate_guidance and (_feas_mdl.n >= 5):
                    best_s = -1.0
                    best_d: Dict[str, Any] = {}
                    # Mechanism-conditioned feasibility classifier (client-side guidance)
                    use_mech = _choose_mechanism_condition(mechanism_switch_mode, str(last_dom_mech or "GENERAL"), mech_trace, list(_mech_clfs.keys()))
                    _clf = _mech_clfs.get(use_mech) if mechanism_classifier else None
                    clf_ready = bool(_clf is not None and _clf.ready(min_pos=mech_min_pos, min_neg=mech_min_neg))
                    if mechanism_classifier:
                        _mech_filter_stats["by_mechanism"].setdefault(use_mech, {"scored": 0, "evaluated": 0})
                    for _j in range(int(mech_batch)):
                        dd: Dict[str, Any] = {}
                        for k, (lo, hi) in bounds.items():
                            dd[k] = float(lo + (hi - lo) * rng.random())
                        xn = _norm_vec(dd, bounds)
                        s = _surrogate_score(xn, _feas_mdl, _fail_mdls)
                        if clf_ready and _clf is not None:
                            try:
                                s *= float(_clf.prob_feasible(xn))
                            except Exception:
                                pass
                        if mechanism_classifier:
                            try:
                                _mech_filter_stats["by_mechanism"][use_mech]["scored"] += 1
                            except Exception:
                                pass
                        if s > best_s:
                            best_s = s
                            best_d = dd
                    d.update(best_d)
                    proposed = True

                if not proposed:
                    for k, (lo, hi) in bounds.items():
                        d[k] = float(lo + (hi - lo) * rng.random())

                d.update(fixed)
                d.update(caps)

                inp = _filter_pointinputs(d)

                rec: Dict[str, Any] = {"i": global_i, "phase": "random", "inputs": d}
                last_verdict = "FAIL"
                last_dom = "—"
                try:
                    res = ev.evaluate(inp)
                    out = res.out if isinstance(res.out, dict) else {}
                    cs = evaluate_constraints(out)

                    candidate = _is_candidate(policy, cs)
                    last_verdict = "PASS" if candidate else "FAIL"
                    last_dom = _dominant_failure(cs)
                    dom_mech = "GENERAL"
                    worst_hard = float("inf")
                    for cc in cs:
                        if str(getattr(cc, "severity", "hard")) != "hard":
                            continue
                        if _c_passed(cc):
                            continue
                        mm = _c_margin(cc)
                        if math.isfinite(mm) and mm < worst_hard:
                            worst_hard = mm
                            dom_mech = str(getattr(cc, "mechanism_group", "GENERAL") or "GENERAL")
                    if worst_hard == float("inf"):
                        worst_hard = float("nan")
                    # Update surrogate models
                    try:
                        xn = _norm_vec(d, bounds)
                        if candidate:
                            _feas_mdl.update(xn)
                            # Update classifier positives for all known mechanisms (shared feasible set)
                            if mechanism_classifier:
                                for _mk, _clf in _mech_clfs.items():
                                    _clf.update_pos(xn)
                        else:
                            mdl = _fail_mdls.get(dom_mech)
                            if mdl is None:
                                mdl = _DiagGauss(dim)
                                _fail_mdls[dom_mech] = mdl
                            mdl.update(xn)
                            if mechanism_classifier:
                                _clf = _mech_clfs.get(dom_mech)
                                if _clf is None:
                                    _clf = _MechFeasClassifier(dim, dom_mech)
                                    # Seed positives from current feasible gaussian summary (best available deterministic proxy)
                                    try:
                                        _clf.pos.n = int(_feas_mdl.n)
                                        _clf.pos.mean = np.array(_feas_mdl.mean, dtype=float).copy()
                                        _clf.pos.m2 = np.array(_feas_mdl.m2, dtype=float).copy()
                                    except Exception:
                                        pass
                                    _mech_clfs[dom_mech] = _clf
                                _clf.update_neg(xn)
                    except Exception:
                        pass
                    dom_inputs = out.get("dominant_inputs") or out.get("best_knobs") or []
                    if not isinstance(dom_inputs, list):
                        dom_inputs = []
                    # Persist last diagnostics for hybrid proposal
                    last_out = dict(out)
                    last_dom_inputs = list(dom_inputs)
                    last_dom_mech = str(dom_mech)

                    obj_val = float(out.get(objective_key, float("nan")))
                    rec.update({
                        "ok": bool(res.ok),
                        "elapsed_s": float(res.elapsed_s),
                        "objective": obj_val,
                        "candidate": bool(candidate),
                        "dominant_constraint": last_dom,
                        "n_constraints": int(len(cs)),
                        "n_hard_failed": int(sum(1 for c in cs if getattr(c, "severity", "hard") == "hard" and not _c_passed(c))),
                        "worst_hard_margin": float(worst_hard),
                        "dominant_mechanism": str(dom_mech),
                        "dominant_inputs": list(dom_inputs),
                        "outputs": {k: out.get(k) for k in [
                            objective_key, "P_net_MW", "CAPEX_$", "recirc_frac", "P_fus_MW", "Q_DT_eqv",
                            "beta_N", "q95_proxy", "q_div_MW_m2", "rwm_regime"
                        ] if k in out},
                    })

                    if mechanism_classifier:
                        _mech_filter_stats["evaluated"] += 1
                        try:
                            um = str(dom_mech or "GENERAL").upper()
                            _mech_filter_stats["by_mechanism"].setdefault(um, {"scored": 0, "evaluated": 0})
                            _mech_filter_stats["by_mechanism"][um]["evaluated"] += 1
                        except Exception:
                            pass

                    records.append(rec)
                    # Scenario robustness (optional; only for feasible candidates)
                    if scenario_robustness and rec.get("candidate") and scenario_factors:
                        try:
                            m = _scenario_robust_metrics(ev, policy, dict(rec.get("inputs", {})), dict(scenario_factors), int(scenario_max))
                            rec.update(m)
                        except Exception:
                            pass
                    mech_trace.append("FEASIBLE" if rec.get("candidate") else str(rec.get("dominant_mechanism","GENERAL")).upper())

                    if candidate:
                        feasible.append(rec)
                        if best is None:
                            best = rec
                        else:
                            if _candidate_better(rec, best, objective_dir=objective_dir, robustness_first=robustness_first, scenario_robustness=scenario_robustness):
                                best = rec
                    else:
                        dominant_failures[last_dom] = dominant_failures.get(last_dom, 0) + 1

                except Exception as e:
                    rec["ok"] = False
                    rec["error"] = str(e)
                    rec["candidate"] = False
                    records.append(rec)
                    dominant_failures["EVALUATION_ERROR"] = dominant_failures.get("EVALUATION_ERROR", 0) + 1
                    last_verdict = "ERROR"
                    last_dom = "EVALUATION_ERROR"

                global_i += 1

                _write_json(run_dir / "progress.json", {
                    "i": global_i,
                    "n": n,
                    "n_feasible": len(feasible),
                    "last_verdict": last_verdict,
                    "last_dominant": last_dom,
                    "phase": phase,
                })

                if global_i % 25 == 0:
                    log(f"[progress] i={global_i}/{n} feasible={len(feasible)} last={last_verdict} dom={last_dom} phase={phase}")


    elapsed = float(time.time() - t0)

    meta = {
        "schema_version": "extopt_evidence_pack.v1",
        "run_id": run_id,
        "created_utc": ts.replace("-", ":").replace("Z", "Z"),
        "seed": int(cfg["seed"]),
        "n": int(n),
        "objective": objective_key,
        "policy": policy,
        "objective_direction": str(cfg.get("objective_direction","max")),
        "strategy": str(cfg.get("strategy","random")),
        "seed_source": cfg.get("seed_source", {}) or {},
        "elapsed_wall_s": elapsed,
        "cache_stats": ev.cache_stats(),
        "n_feasible": int(len(feasible)),
        "cfg_sha256": _sha256_bytes(cfg_bytes),
        "orchestrator_job_id": str(cfg.get("orchestrator_job_id", "")).strip(),
        "objective_contract_schema": (cfg.get("objective_contract", {}) or {}).get("schema"),
    }

    summary = {
        "dominant_failures": dict(sorted(dominant_failures.items(), key=lambda kv: kv[1], reverse=True)),
        "feasible_yield": float(len(feasible) / max(1, n)),
    }

    _write_json(run_dir / "meta.json", meta)
    _write_json(run_dir / "records.json", records, indent=1, sort_keys=False)
    _write_json(run_dir / "summary.json", summary)
    if best is not None:
        _write_json(run_dir / "best.json", best, indent=1, sort_keys=False)

    # v252: Optimization family gallery (group feasible designs by island provenance)
    try:
        from tools.optimizer_family import build_family_gallery, render_family_gallery_md  # type: ignore
        gal = build_family_gallery(records, objective_key=objective_key, objective_direction=str(cfg.get("objective_direction","max")))
        _write_json(run_dir / "optimizer_family_gallery.json", gal)
        (run_dir / "optimizer_family_gallery.md").write_text(render_family_gallery_md(gal), encoding="utf-8")
    except Exception:
        pass

    # Mechanism transition map (publishable search dynamics)
    try:
        seq = [str(s) for s in (mech_trace or [])]
        # compress empty
        seq = [s if s else "GENERAL" for s in seq]
        trans: Dict[str, Dict[str, int]] = {}
        counts: Dict[str, int] = {}
        for s in seq:
            counts[s] = counts.get(s, 0) + 1
        for a, b in zip(seq[:-1], seq[1:]):
            trans.setdefault(a, {})
            trans[a][b] = trans[a].get(b, 0) + 1
        # Normalized matrix
        norm: Dict[str, Dict[str, float]] = {}
        for a, row in trans.items():
            tot = float(sum(row.values())) if row else 1.0
            norm[a] = {b: float(c) / tot for b, c in row.items()}
        _write_json(run_dir / "mechanism_transition_map.json", {
            "sequence_len": int(len(seq)),
            "states": sorted(set(seq)),
            "state_counts": counts,
            "transitions_counts": trans,
            "transitions_normalized": norm,
        })
        # v252: explicit switch-point list (for mechanism-switch-aware narratives)
        switches = []
        for idx, (a, b) in enumerate(zip(seq[:-1], seq[1:])):
            if a != b:
                switches.append({"i": int(idx), "from": str(a), "to": str(b)})
        _write_json(run_dir / "mechanism_switch_points.json", {
            "n_switches": int(len(switches)),
            "switches": switches[:2000],
        })
        # CSV matrix
        states = sorted(set(seq))
        lines = []
        header = ",".join(["from\to"] + states)
        lines.append(header)
        for a in states:
            row = [a]
            for b in states:
                row.append(str(trans.get(a, {}).get(b, 0)))
            lines.append(",".join(row))
        (run_dir / "mechanism_transition_matrix.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass

    # Mechanism-conditioned classifier snapshot
    try:
        if mechanism_classifier:
            clfs = []
            for mk in sorted(_mech_clfs.keys()):
                try:
                    clfs.append(_mech_clfs[mk].to_dict())
                except Exception:
                    pass
            _write_json(run_dir / "mechanism_classifiers.json", {
                "schema": "mech_feas_classifier.v1",
                "min_pos": int(mech_min_pos),
                "min_neg": int(mech_min_neg),
                "mechanisms": clfs,
                "filter_stats": _mech_filter_stats,
            })
    except Exception:
        pass

    # Final progress
    _write_json(run_dir / "progress.json", {
        "i": n,
        "n": n,
        "n_feasible": len(feasible),
        "last_verdict": "DONE",
        "last_dominant": "",
    })

    _write_manifest(run_dir)
    log(f"[done] elapsed_s={elapsed:.3f} feasible={len(feasible)}/{n}")
    log_f.close()

    # Print minimal summary to stdout (captured by UI)
    print(json.dumps(meta, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
