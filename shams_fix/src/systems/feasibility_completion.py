from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Tuple, List, Optional, Set, Any
import math
import time

try:
    from evaluator.core import Evaluator
except Exception:
    from evaluator.core import Evaluator  # type: ignore

try:
    from constraints.constraints import evaluate_constraints
except Exception:
    from constraints.constraints import evaluate_constraints  # type: ignore

try:
    from models.inputs import PointInputs
except Exception:
    from models.inputs import PointInputs  # type: ignore

from .sampling import SamplePoint, generate_precheck_samples


@dataclass
class PrecheckSampleResult:
    sample: SamplePoint
    outputs: Dict[str, float]
    hard_failed: List[str]
    hard_best_margin_by_name: Dict[str, float]


@dataclass
class PrecheckReport:
    ok: bool
    reason: str
    precheck_seconds: float
    n_samples: int
    samples: List[PrecheckSampleResult]
    hard_constraints_failed_at_all_samples: List[str]
    hard_constraints_best_margin: Dict[str, float]
    hard_constraints_best_sample: Dict[str, str]
    unreachable_targets: List[Dict[str, Any]]
    unreachable_targets_confidence: str


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def _apply_vars(base: PointInputs, var_values: Dict[str, float]) -> PointInputs:
    # dataclass-like object; create a new PointInputs with updated attributes
    d = dict(base.__dict__)
    d.update({k: float(v) for k, v in var_values.items()})
    return PointInputs(**d)


def run_precheck(
    base: PointInputs,
    targets: Dict[str, float],
    variables: Dict[str, Tuple[float, float, float]],
    *,
    include_random: bool = True,
    n_random: int = 8,
    seed: int = 1337,
    evaluator: Optional[Evaluator] = None,
    hard_constraint_names: Optional[Set[str]] = None,
) -> PrecheckReport:
    """Run Systems Mode precheck using an information-rich sample set.

    Returns a detailed report that can be shown in UI and used for feasibility completion.
    """

    t0 = time.perf_counter()
    ev = evaluator or Evaluator(cache_enabled=True, cache_max=512)

    hard_set = set(hard_constraint_names) if hard_constraint_names else None

    samples = generate_precheck_samples(
        variables,
        include_random=include_random,
        n_random=int(n_random),
        seed=int(seed),
    )

    sample_results: List[PrecheckSampleResult] = []

    # Track hard constraint best margins across samples
    best_margin: Dict[str, float] = {}
    best_sample: Dict[str, str] = {}

    # For unreachable target ranges across samples
    tgt_minmax: Dict[str, Tuple[float, float]] = {k: (math.inf, -math.inf) for k in targets.keys()}

    for sp in samples:
        inp = _apply_vars(base, sp.values)
        try:
            out = ev.evaluate(inp).out
        except Exception:
            out = {}

        # update min/max for targets
        for tk in targets.keys():
            v = float(out.get(tk, float('nan')))
            if math.isfinite(v):
                mn, mx = tgt_minmax.get(tk, (math.inf, -math.inf))
                tgt_minmax[tk] = (min(mn, v), max(mx, v))

        hard_failed: List[str] = []
        hard_best_margin_by_name: Dict[str, float] = {}
        try:
            constraints = evaluate_constraints(out)
            for c in constraints:
                name = str(getattr(c, 'name', ''))
                sev = str(getattr(c, 'severity', 'soft'))
                if hard_set is None:
                    if sev != 'hard':
                        continue
                else:
                    if name not in hard_set:
                        continue
                passed = bool(getattr(c, 'passed', False))
                margin = getattr(c, 'margin', None)
                try:
                    m = float(margin) if margin is not None else float('nan')
                except Exception:
                    m = float('nan')

                hard_best_margin_by_name[name] = m
                if name not in best_margin or (math.isfinite(m) and (not math.isfinite(best_margin[name]) or m > best_margin[name])):
                    best_margin[name] = m
                    best_sample[name] = sp.name
                if not passed:
                    hard_failed.append(name)
        except Exception:
            pass

        sample_results.append(
            PrecheckSampleResult(
                sample=sp,
                outputs=dict(out),
                hard_failed=list(hard_failed),
                hard_best_margin_by_name=dict(hard_best_margin_by_name),
            )
        )

    # Determine which hard constraints fail at all samples
    all_failed: List[str] = []
    hard_names = sorted(set(best_margin.keys()))
    for nm in hard_names:
        if all(nm in sr.hard_failed for sr in sample_results):
            all_failed.append(nm)

    # Determine unreachable targets
    #
    # IMPORTANT: Targets in SHAMS are generally interpreted as *thresholds* (e.g., Q >= Q_min, H98 >= H98_min),
    # not equality constraints. Therefore, a target is "unreachable" only if the sampled range cannot meet the
    # threshold in the required direction.
    #
    # Heuristic policy:
    #   - default: "min" (must be >= target)
    #   - if key looks like a maximum ("max_*" or "*_max"): "max" (must be <= target)
    unreachable: List[Dict[str, Any]] = []

    def _target_sense(key: str) -> str:
        k = str(key).strip().lower()
        if k.startswith('max_') or k.endswith('_max'):
            return 'max'
        return 'min'

    for tk, tv in targets.items():
        mn, mx = tgt_minmax.get(tk, (math.inf, -math.inf))
        if not (math.isfinite(mn) and math.isfinite(mx)):
            unreachable.append({'target': tk, 'target_value': float(tv), 'reason': 'nonfinite_range'})
            continue
        sense = _target_sense(tk)
        if sense == 'min':
            # Need mx >= tv to be able to satisfy a "minimum" target.
            if float(mx) < float(tv):
                unreachable.append({'target': tk, 'target_value': float(tv), 'sample_min': float(mn), 'sample_max': float(mx)})
        else:
            # Need mn <= tv to be able to satisfy a "maximum" target.
            if float(mn) > float(tv):
                unreachable.append({'target': tk, 'target_value': float(tv), 'sample_min': float(mn), 'sample_max': float(mx)})

    # Confidence heuristic based on sample richness
    n = len(samples)
    n_vars = len(variables)
    if n_vars <= 4 and n >= (2 ** n_vars):
        conf = 'high'
    elif n >= max(10, 2 * n_vars + 3):
        conf = 'medium'
    else:
        conf = 'low'

    ok = (len(all_failed) == 0) and (len(unreachable) == 0)
    reason = 'ok' if ok else 'precheck_infeasible'
    dt = float(time.perf_counter() - t0)

    return PrecheckReport(
        ok=bool(ok),
        reason=str(reason),
        precheck_seconds=dt,
        n_samples=int(len(samples)),
        samples=sample_results,
        hard_constraints_failed_at_all_samples=all_failed,
        hard_constraints_best_margin={k: float(v) for k, v in best_margin.items()},
        hard_constraints_best_sample={k: str(v) for k, v in best_sample.items()},
        unreachable_targets=unreachable,
        unreachable_targets_confidence=str(conf),
    )


@dataclass
class ProposedChange:
    kind: str  # bounds | constraints | targets
    description: str
    changes: Dict[str, Any]
    score: float


def apply_bound_changes(
    variables: Dict[str, Tuple[float, float, float]],
    bound_changes: Dict[str, Dict[str, float]],
) -> Dict[str, Tuple[float, float, float]]:
    out = dict(variables)
    for k, ch in (bound_changes or {}).items():
        if k not in out:
            continue
        x0, lo, hi = out[k]
        lo2 = float(ch.get('lo', lo))
        hi2 = float(ch.get('hi', hi))
        out[k] = (float(x0), float(lo2), float(hi2))
    return out


def apply_target_changes(targets: Dict[str, float], target_changes: Dict[str, float]) -> Dict[str, float]:
    out = dict(targets)
    for k, v in (target_changes or {}).items():
        if k in out:
            out[k] = float(v)
    return out


def apply_constraint_relaxations(
    base_inputs_dict: Dict[str, Any],
    relax: Dict[str, float],
) -> Dict[str, Any]:
    """Applies constraint threshold relaxations to an inputs dict.

    NOTE: constraints live in PointInputs (inputs) as knobs; if the run uses
    defaults overridden elsewhere, UI should propagate appropriately.
    """
    d = dict(base_inputs_dict)
    for k, v in (relax or {}).items():
        d[k] = float(v)
    return d


def _infer_lever_vars(failed_constraints: List[str]) -> List[str]:
    """Map failed constraint names to likely variable levers."""
    levers: List[str] = []
    for nm in failed_constraints:
        if 'q_div' in nm:
            levers += ['Paux_MW', 'Ip_MA', 'R0_m']
        elif 'sigma' in nm:
            levers += ['Bt_T', 'R0_m']
        elif 'HTS' in nm or 'margin' in nm:
            levers += ['Bt_T', 'R0_m', 't_shield_m']
        elif 'TBR' in nm:
            levers += ['t_shield_m', 'R0_m']
        else:
            levers += ['R0_m']
    # keep unique while preserving order
    seen = set()
    out = []
    for v in levers:
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def propose_feasibility_completion(
    base: PointInputs,
    targets: Dict[str, float],
    variables: Dict[str, Tuple[float, float, float]],
    *,
    evaluator: Optional[Evaluator] = None,
    include_random: bool = True,
    n_random: int = 8,
    seed: int = 1337,
    max_k_changes: int = 2,
    hard_constraint_names: Optional[Set[str]] = None,
) -> List[ProposedChange]:
    """Propose minimal changes to reach precheck feasibility.

    Deterministic heuristic search over small bound expansions and target nudges.
    The UI can present these as one-click actions.
    """

    ev = evaluator or Evaluator(cache_enabled=True, cache_max=1024)
    base_report = run_precheck(
        base,
        targets,
        variables,
        include_random=include_random,
        n_random=n_random,
        seed=seed,
        evaluator=ev,
        hard_constraint_names=hard_constraint_names,
    )
    if base_report.ok:
        return []

    failed = list(base_report.hard_constraints_failed_at_all_samples)
    lever_vars = [v for v in _infer_lever_vars(failed) if v in variables]

    proposals: List[ProposedChange] = []

    # --- 1) bound expansions (preferred) ---
    # Try small expansions on lever variables (hi up or down depending on variable nature).
    steps = [0.05, 0.10, 0.20]

    def score(rep: PrecheckReport) -> float:
        """Higher is better.

        We primarily penalize hard-constraint infeasibility, but we also use
        best-margins to differentiate between proposals that have the same
        pass/fail count (important for UX; otherwise many proposals appear
        "identical" with equal scores).
        """
        s = -10.0 * len(rep.hard_constraints_failed_at_all_samples) - 5.0 * len(rep.unreachable_targets)
        # Add a small continuous term based on best hard-constraint margins.
        # Less-negative (closer to feasible) => better score.
        bm = rep.hard_constraints_best_margin or {}
        for _k, _v in bm.items():
            try:
                v = float(_v)
            except Exception:
                v = float('nan')
            if not math.isfinite(v):
                s -= 50.0
            else:
                s += 0.05 * v
        return float(s)

    # Single-variable expansions
    for v in lever_vars[: max(1, len(lever_vars))]:
        x0, lo, hi = variables[v]
        for s in steps:
            hi2 = hi * (1.0 + s) if hi != 0 else hi + s
            lo2 = lo
            # For power-like variables, also consider reducing upper bound (if lever is reduce)
            if v in ('Paux_MW',):
                # reducing hi might help q_div
                hi2_alt = max(lo, hi * (1.0 - s))
                for tag, _hi in [('inc', hi2), ('dec', hi2_alt)]:
                    vars2 = apply_bound_changes(variables, {v: {'lo': lo2, 'hi': _hi}})
                    rep2 = run_precheck(base, targets, vars2, include_random=include_random, n_random=n_random, seed=seed, evaluator=ev, hard_constraint_names=hard_constraint_names)
                    base_s = score(rep2)
                    # Prefer smaller changes when outcomes are similar.
                    base_s -= 50.0 * float(s)
                    proposals.append(
                        ProposedChange(
                            kind='bounds',
                            description=f"Adjust bound for {v} ({tag} {int(s*100)}%)",
                            changes={'bounds': {v: {'lo': lo2, 'hi': float(_hi)}}},
                            score=float(base_s),
                        )
                    )
            else:
                vars2 = apply_bound_changes(variables, {v: {'lo': lo2, 'hi': hi2}})
                rep2 = run_precheck(base, targets, vars2, include_random=include_random, n_random=n_random, seed=seed, evaluator=ev, hard_constraint_names=hard_constraint_names)
                base_s = score(rep2)
                base_s -= 50.0 * float(s)
                proposals.append(
                    ProposedChange(
                        kind='bounds',
                        description=f"Expand upper bound for {v} (+{int(s*100)}%)",
                        changes={'bounds': {v: {'lo': lo2, 'hi': float(hi2)}}},
                        score=float(base_s),
                    )
                )

    # Two-variable combined (limited)
    if max_k_changes >= 2 and len(lever_vars) >= 2:
        v1, v2 = lever_vars[0], lever_vars[1]
        for s in [0.10, 0.20]:
            x0, lo1, hi1 = variables[v1]
            x0, lo2, hi2 = variables[v2]
            vars2 = apply_bound_changes(
                variables,
                {
                    v1: {'lo': lo1, 'hi': float(hi1 * (1.0 + s) if hi1 != 0 else hi1 + s)},
                    v2: {'lo': lo2, 'hi': float(hi2 * (1.0 + s) if hi2 != 0 else hi2 + s)},
                },
            )
            rep2 = run_precheck(base, targets, vars2, include_random=include_random, n_random=n_random, seed=seed, evaluator=ev, hard_constraint_names=hard_constraint_names)
            base_s = score(rep2)
            base_s -= 50.0 * float(s) * 2.0
            proposals.append(
                ProposedChange(
                    kind='bounds',
                    description=f"Expand upper bounds for {v1} and {v2} (+{int(s*100)}%)",
                    changes={'bounds': {v1: {'lo': lo1, 'hi': float(vars2[v1][2])}, v2: {'lo': lo2, 'hi': float(vars2[v2][2])}}},
                    score=float(base_s),
                )
            )

    # --- 2) target suggestions (if unreachable) ---
    for u in base_report.unreachable_targets:
        tk = u.get('target')
        if tk in targets and 'sample_min' in u and 'sample_max' in u:
            mn = float(u['sample_min'])
            mx = float(u['sample_max'])
            # propose clamping to reachable range edge
            tv = float(targets[tk])
            newv = mn if tv < mn else mx
            t2 = apply_target_changes(targets, {tk: newv})
            rep2 = run_precheck(base, t2, variables, include_random=include_random, n_random=n_random, seed=seed, evaluator=ev)
            proposals.append(
                ProposedChange(
                    kind='targets',
                    description=f"Adjust target {tk} into sampled reachable range",
                    changes={'targets': {tk: float(newv)}},
                    score=score(rep2),
                )
            )

    # --- 3) constraint relaxations (explicit, second-line) ---
    # We only propose if bounds/targets do not help much. Provide safe-ish small relaxations.
    # These are returned as 'constraints' changes for UI to apply to inputs dict.
    relax_map = {
        'sigma_vm': ('sigma_allow_MPa', +0.10),
        'q_div': ('q_div_max_MW_m2', +0.10),
        'HTS margin': ('hts_margin_min', -0.10),
        'TBR': ('TBR_min', -0.05),
    }
    for nm in failed:
        if nm not in relax_map:
            continue
        knob, frac = relax_map[nm]
        try:
            base_val = float(getattr(base, knob))
        except Exception:
            base_val = float('nan')
        if not math.isfinite(base_val):
            continue
        new_val = base_val * (1.0 + frac) if frac > 0 else base_val * (1.0 + frac)
        # If decreasing a minimum, ensure not negative
        if knob.endswith('_min'):
            new_val = max(0.0, float(new_val))
        proposals.append(
            ProposedChange(
                kind='constraints',
                description=f"Relax constraint knob {knob} ({'+' if frac>0 else ''}{int(frac*100)}%)",
                changes={'constraints': {knob: float(new_val)}},
                score=-99.0,  # always below bound/target suggestions
            )
        )

    # Sort best-first, but keep constraints last
    def _key(p: ProposedChange):
        tier = 0 if p.kind == 'bounds' else (1 if p.kind == 'targets' else 2)
        return (tier, -p.score)

    proposals.sort(key=_key)

    # prune duplicates by semantic change key (not by description)
    def _change_key(p: ProposedChange) -> str:
        try:
            import json
            return f"{p.kind}|{json.dumps(p.changes, sort_keys=True)}"
        except Exception:
            return f"{p.kind}|{str(p.changes)}"

    best_by_key: Dict[str, ProposedChange] = {}
    for p in proposals:
        k = _change_key(p)
        if (k not in best_by_key) or (p.score > best_by_key[k].score):
            best_by_key[k] = p

    uniq = list(best_by_key.values())
    uniq.sort(key=_key)

    # UX prune: avoid spamming the same variable with many near-identical steps
    # (keep at most 3 bound proposals per variable).
    out: List[ProposedChange] = []
    per_var: Dict[str, int] = {}
    for p in uniq:
        if p.kind == 'bounds':
            try:
                var = next(iter((p.changes.get('bounds') or {}).keys()))
            except Exception:
                var = None
            if var:
                per_var[var] = per_var.get(var, 0) + 1
                if per_var[var] > 3:
                    continue
        out.append(p)
        if len(out) >= 12:
            break
    return out


def feasibility_scout(
    base: PointInputs,
    variables: Dict[str, Tuple[float, float, float]],
    *,
    evaluator: Optional[Evaluator] = None,
    n_samples: int = 64,
    seed: int = 1337,
    n_refine: int = 20,
    hard_constraint_names: Optional[Set[str]] = None,
    return_trace: bool = False,
    trace_keep: int = 2500,
) -> Dict[str, Any]:
    """Feasibility-first scout: attempt to find a feasible point within bounds.

    Returns dict with keys:
      ok, best_inp, best_out, best_score, best_min_margin, hard_failed

    Score is based on sum of negative hard margins (0 is feasible).
    Deterministic.
    """
    ev = evaluator or Evaluator(cache_enabled=True, cache_max=2048)
    hard_set = set(hard_constraint_names) if hard_constraint_names else None
    keys = list(variables.keys())
    bounds = {k: (float(variables[k][1]), float(variables[k][2])) for k in keys}

    rng = __import__('random').Random(int(seed))

    def eval_point(assign: Dict[str, float]):
        inp = _apply_vars(base, assign)
        out = ev.evaluate(inp).out
        cons = evaluate_constraints(out)
        if hard_set is None:
            hard = [c for c in cons if str(getattr(c,'severity','soft')) == 'hard']
        else:
            hard = [c for c in cons if str(getattr(c,'name','')) in hard_set]
        margins = []
        hard_failed = []
        for c in hard:
            m = getattr(c,'margin', None)
            try:
                mv = float(m) if m is not None else float('nan')
            except Exception:
                mv = float('nan')
            margins.append(mv)
            if not bool(getattr(c,'passed', False)):
                hard_failed.append(str(getattr(c,'name','')))
        # violation: sum of negative margins (non-finite treated as large violation)
        viol = 0.0
        min_margin = math.inf
        for mv in margins:
            if not math.isfinite(mv):
                viol += 1e3
                min_margin = -1e3
            else:
                if mv < 0:
                    viol += -mv
                min_margin = min(min_margin, mv)
        return inp, out, viol, min_margin, hard_failed

    # initial random sampling
    trace: List[Dict[str, Any]] = []

    def _trace_add(assign: Dict[str, float], viol: float, minm: float, hard_failed: List[str]) -> None:
        if not return_trace:
            return
        try:
            trace.append({
                'x': {k: float(v) for k, v in (assign or {}).items()},
                'V': float(viol),
                'min_margin': float(minm),
                'feasible': bool(float(viol) <= 0.0),
                'hard_failed': list(hard_failed or []),
            })
            if int(trace_keep) > 0 and len(trace) > int(trace_keep):
                del trace[: max(1, len(trace) - int(trace_keep))]
        except Exception:
            return

    best = None
    for i in range(int(n_samples)):
        assign = {}
        for k in keys:
            lo, hi = bounds[k]
            assign[k] = lo + (hi - lo) * rng.random()
        inp, out, viol, minm, hard_failed = eval_point(assign)
        _trace_add(assign, viol, minm, hard_failed)
        if best is None or viol < best[2]:
            best = (inp, out, viol, minm, hard_failed, assign)
            if viol <= 0.0:
                break

    if best is None:
        return {'ok': False, 'reason': 'no_samples', 'trace': trace if return_trace else None}

    # coordinate refine (simple)
    assign = dict(best[5])
    step_scale = 0.1
    for _ in range(int(n_refine)):
        improved = False
        for k in keys:
            lo, hi = bounds[k]
            span = hi - lo
            if span <= 0:
                continue
            for direction in (-1.0, +1.0):
                cand = dict(assign)
                cand[k] = _clamp(cand[k] + direction * step_scale * span, lo, hi)
                inp, out, viol, minm, hard_failed = eval_point(cand)
                _trace_add(cand, viol, minm, hard_failed)
                if viol < best[2]:
                    best = (inp, out, viol, minm, hard_failed, cand)
                    assign = cand
                    improved = True
                    if viol <= 0.0:
                        break
            if best[2] <= 0.0:
                break
        if not improved:
            step_scale *= 0.5
        if step_scale < 0.005 or best[2] <= 0.0:
            break

    return {
        'ok': bool(best[2] <= 0.0),
        'best_inp': best[0],
        'best_out': best[1],
        'best_score': float(best[2]),
        'best_min_margin': float(best[3]),
        'hard_failed': list(best[4]),
        'best_assign': dict(best[5]),
        'trace': trace if return_trace else None,
    }
