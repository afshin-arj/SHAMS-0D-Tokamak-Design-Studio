from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter, defaultdict
import math
import numpy as np

def _safe_float(x: Any) -> float:
    try:
        v = float(x)
        return v
    except Exception:
        return float('nan')

def _extract_blockers(candidate: Dict[str, Any]) -> List[Tuple[str,float]]:
    out=[]
    for r in (candidate.get('constraints') or []):
        try:
            sm=float(r.get('signed_margin'))
        except Exception:
            continue
        name=str(r.get('name') or r.get('constraint') or '')
        if not name:
            continue
        if sm < 0:
            out.append((name, sm))
    out.sort(key=lambda t: t[1])
    return out

def build_resistance_report(
    *,
    trace: List[Dict[str, Any]],
    archive: List[Dict[str, Any]],
    intent: str,
    lens_contract: Dict[str, Any],
    bounds: Dict[str, Any],
    var_specs: List[Dict[str, Any]],
    last_n: int = 500,
) -> Dict[str, Any]:
    T=(trace or [])[-int(last_n):]
    blockers=Counter()
    severity=defaultdict(list)
    failure_modes=Counter()
    pair_counts=Counter()
    feas=0
    for t in T:
        if bool(t.get('feasible', False)):
            feas += 1
            continue
        failure_modes[str(t.get('failure_mode') or 'unknown')] += 1
        bs = [name for name, sm in _extract_blockers(t)]
        for name, sm in _extract_blockers(t):
            blockers[name]+=1
            severity[name].append(float(sm))
        # co-occurrence conflicts (descriptive): count blocker pairs appearing together
        # Strength is frequency-weighted; this is not a causal claim.
        if len(bs) >= 2:
            uniq = sorted(list(dict.fromkeys(bs)))
            for i in range(len(uniq)):
                for j in range(i+1, len(uniq)):
                    pair_counts[(uniq[i], uniq[j])] += 1
    top=[]
    for name,cnt in blockers.most_common(12):
        vals=severity.get(name,[])
        top.append({
            "constraint": name,
            "count": int(cnt),
            "worst_signed_margin": float(min(vals)) if vals else None,
            "median_signed_margin": float(np.median(vals)) if vals else None,
        })

    # crude sensitivity: correlate inputs with min_signed_margin over recent trace
    keys=[str(v.get('key')) for v in (var_specs or []) if v.get('key')]
    sens=[]
    if keys and T:
        ms=np.array([_safe_float(t.get('min_signed_margin')) for t in T], dtype=float)
        for k in keys:
            xs=np.array([_safe_float(((t.get('inputs') or {}).get(k))) for t in T], dtype=float)
            if np.sum(np.isfinite(xs)) < 10 or np.sum(np.isfinite(ms)) < 10:
                continue
            # pearson
            x=xs[np.isfinite(xs) & np.isfinite(ms)]
            y=ms[np.isfinite(xs) & np.isfinite(ms)]
            if len(x) < 10:
                continue
            x = (x - float(np.mean(x))) / (float(np.std(x)) + 1e-12)
            y = (y - float(np.mean(y))) / (float(np.std(y)) + 1e-12)
            corr=float(np.mean(x*y))
            if abs(corr) < 0.15:
                continue
            sens.append({"var": k, "corr_with_min_margin": corr})
        sens.sort(key=lambda d: abs(d["corr_with_min_margin"]), reverse=True)
        sens=sens[:12]

    report={
        "schema": "shams.opt_sandbox.resistance_report.v1",
        "intent": str(intent),
        "lens": dict(lens_contract or {}),
        "bounds": dict(bounds or {}),
        "n_trace": int(len(T)),
        "feasible_rate": float(feas)/float(len(T)) if T else 0.0,
        "top_blockers": top,
        "failure_modes": dict(failure_modes),
        "sensitivity": sens,
        "conflicts": [
            {"a": a, "b": b, "count": int(c), "strength": float(c) / float(max(1, len(T)))}
            for (a, b), c in pair_counts.most_common(20)
        ],
        "notes": [
            "This report is descriptive, not prescriptive.",
            "All feasibility is validated by the frozen Point Designer evaluator."
        ],
    }
    return report
