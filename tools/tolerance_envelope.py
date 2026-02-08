from __future__ import annotations
"""Tolerance Envelope (v117)

Deterministic, bounded tolerance analysis around an already-evaluated run artifact.
No probability assumptions. No Monte Carlo. No optimization.

Given a baseline run artifact and a tolerance spec, we generate a finite set of
deterministic samples (center + corners + optional edge midpoints) and evaluate
each using frozen physics+constraints.

Outputs:
- shams_tolerance_envelope_report with per-sample feasibility + worst constraint + margins
- CSV summary

Tolerance spec example:
{
  "kind": "shams_tolerance_spec_v117",
  "mode": "relative",   # relative uses +/- frac; absolute uses +/- delta
  "tolerances": {
     "Bt_T": 0.03,
     "Ip_MA": 0.02,
     "R0_m": 0.02,
     "a_m": 0.02,
     "fG": 0.05
  },
  "include_edge_midpoints": true,
  "notes": ["..."]
}
"""

from typing import Any, Dict, List, Tuple, Optional
import time
import itertools
import math
import csv
import io
import json

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def template_tolerance_spec() -> Dict[str, Any]:
    return {
        "kind": "shams_tolerance_spec_v117",
        "mode": "relative",
        "tolerances": {
            "Bt_T": 0.03,
            "Ip_MA": 0.02,
            "R0_m": 0.02,
            "a_m": 0.02,
            "fG": 0.05,
        },
        "include_edge_midpoints": True,
        "notes": [
            "Deterministic tolerance envelope. No probability interpretation.",
            "relative mode: value -> value*(1±tol). absolute mode: value -> value±tol.",
        ],
    }

def _is_num(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False

def _apply_tol(x: float, tol: float, sign: int, mode: str) -> float:
    if mode == "absolute":
        return x + sign * tol
    return x * (1.0 + sign * tol)

def _sample_points(inputs: Dict[str, Any], spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    mode = spec.get("mode", "relative")
    tmap = spec.get("tolerances", {})
    if not isinstance(tmap, dict):
        return [inputs]
    levers = [k for k,v in tmap.items() if isinstance(k, str) and _is_num(v) and _is_num(inputs.get(k))]
    if not levers:
        return [inputs]

    include_mid = bool(spec.get("include_edge_midpoints", True))

    # center
    pts = [dict(inputs)]

    # corners: all combinations of +/- for each lever
    signs = list(itertools.product([-1, 1], repeat=len(levers)))
    for svec in signs:
        p = dict(inputs)
        for k,sgn in zip(levers, svec):
            p[k] = _apply_tol(float(inputs[k]), float(tmap[k]), int(sgn), str(mode))
        pts.append(p)

    # edge midpoints: vary one lever at a time +/- (others at nominal)
    if include_mid:
        for k in levers:
            for sgn in (-1, 1):
                p = dict(inputs)
                p[k] = _apply_tol(float(inputs[k]), float(tmap[k]), int(sgn), str(mode))
                pts.append(p)

    # Deduplicate (float-safe stringify)
    seen = set()
    out = []
    for p in pts:
        key = tuple((k, round(float(p[k]), 12) if _is_num(p.get(k)) else str(p.get(k))) for k in sorted(p.keys()))
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out

def evaluate_tolerance_envelope(
    *,
    baseline_artifact: Dict[str, Any],
    tolerance_spec: Optional[Dict[str, Any]] = None,
    version: str = "v117",
    max_samples: int = 200,
) -> Dict[str, Any]:
    if not (isinstance(baseline_artifact, dict) and baseline_artifact.get("kind") == "shams_run_artifact"):
        raise ValueError("expected shams_run_artifact dict")
    inputs = baseline_artifact.get("inputs", {})
    if not isinstance(inputs, dict):
        raise ValueError("baseline artifact missing inputs dict")

    spec = tolerance_spec if isinstance(tolerance_spec, dict) else template_tolerance_spec()
    pts = _sample_points(inputs, spec)[: int(max_samples)]

    # Evaluate each point through frozen physics+constraints
    from models.inputs import PointInputs
    from physics.hot_ion import hot_ion_point
    from constraints.constraints import evaluate_constraints
    from shams_io.run_artifact import build_run_artifact

    samples: List[Dict[str, Any]] = []
    feasible_count = 0
    worst_margin = None
    worst_name = None

    for i, pin in enumerate(pts):
        pi = PointInputs(**pin)  # may raise; propagate (caller handles)
        out = hot_ion_point(pi)
        cons = evaluate_constraints(out)
        art = build_run_artifact(inputs=pi.to_dict(), outputs=out, constraints=cons, meta={"mode":"tolerance_envelope_v117","sample_index": i})
        cs = art.get("constraints_summary", {})
        feas = cs.get("feasible") if isinstance(cs, dict) else None
        if feas is True:
            feasible_count += 1
        wm = cs.get("worst_hard_margin_frac") if isinstance(cs, dict) else None
        wn = cs.get("worst_hard") if isinstance(cs, dict) else None
        if _is_num(wm):
            wm = float(wm)
            if (worst_margin is None) or (wm < worst_margin):
                worst_margin = wm
                worst_name = wn
        # track deltas from baseline for lever keys
        deltas = {}
        for k in (spec.get("tolerances") or {}).keys() if isinstance(spec.get("tolerances"), dict) else []:
            if k in inputs and k in pin and _is_num(inputs.get(k)) and _is_num(pin.get(k)):
                deltas[k] = float(pin[k]) - float(inputs[k])
        samples.append({
            "kind":"shams_tolerance_sample",
            "index": i,
            "inputs": pi.to_dict(),
            "deltas": deltas,
            "artifact_id": art.get("id"),
            "feasible": feas,
            "worst_hard": wn,
            "worst_hard_margin_frac": wm,
        })

    summary = {
        "n_samples": len(samples),
        "n_feasible": feasible_count,
        "feasible_fraction": (feasible_count / len(samples)) if samples else None,
        "worst_margin_over_envelope": worst_margin,
        "worst_margin_constraint": worst_name,
    }

    report = {
        "kind":"shams_tolerance_envelope_report",
        "version": version,
        "created_utc": _created_utc(),
        "source_artifact_id": baseline_artifact.get("id"),
        "tolerances": spec,
        "samples": samples,
        "summary": summary,
        "notes": [
            "Deterministic tolerance envelope. No probability interpretation.",
            "All samples re-evaluated using frozen physics+constraints.",
        ],
    }
    return report

def envelope_summary_csv(report: Dict[str, Any]) -> bytes:
    samples = report.get("samples", [])
    if not isinstance(samples, list):
        samples = []
    buf = io.StringIO()
    fieldnames = ["index","feasible","worst_hard","worst_hard_margin_frac"]
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for s in samples:
        if not isinstance(s, dict):
            continue
        w.writerow({
            "index": s.get("index"),
            "feasible": s.get("feasible"),
            "worst_hard": s.get("worst_hard"),
            "worst_hard_margin_frac": s.get("worst_hard_margin_frac"),
        })
    return buf.getvalue().encode("utf-8")
