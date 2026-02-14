"""Reference external optimizer client (firewalled).
This module is intentionally simple, deterministic (seeded), and audit-friendly.
It proposes candidates, asks SHAMS (ExtOpt) to evaluate them, and writes an optimizer trace.

Not a production optimizer; it is a constitutional example client.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
import json, random, time, math
from pathlib import Path

from src.extopt.family import load_concept_family
from src.extopt.batch import evaluate_concept_family
from src.extopt.metrics import compute_feasibility_metrics
from src.extopt.scenarios import default_corner_scenarios, scenarios_hash
from src.extopt.bundle import BundleCandidate, BundleProvenance, export_bundle_zip_v273 as export_bundle_zip
from src.extopt.problem_spec import ProblemSpec, VariableSpec, ObjectiveSpec, ConstraintSpec

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _sample_var(rng: random.Random, spec: Dict[str, Any]) -> Any:
    vtype = spec.get("vtype", "continuous")
    lo = float(spec["lower"]); hi = float(spec["upper"])
    if vtype == "integer":
        return int(rng.randint(int(math.ceil(lo)), int(math.floor(hi))))
    # continuous
    if spec.get("scale","linear") == "log":
        # sample log-uniform
        lo2 = math.log(max(lo, 1e-30)); hi2 = math.log(max(hi, lo+1e-12))
        return float(math.exp(rng.uniform(lo2, hi2)))
    return float(rng.uniform(lo, hi))

def _apply_candidate(base_inputs: Dict[str, Any], x: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base_inputs)
    out.update(x)
    return out

def build_default_problem_spec(name: str = "default") -> Dict[str, Any]:
    """A conservative default problem spec for demonstration."""
    ps = ProblemSpec(
        name=name,
        variables=[
            VariableSpec(name="Bt", vtype="continuous", lower=4.0, upper=16.0, units="T"),
            VariableSpec(name="Ip", vtype="continuous", lower=5e6, upper=25e6, units="A"),
            VariableSpec(name="Paux", vtype="continuous", lower=0.0, upper=120e6, units="W"),
            VariableSpec(name="f_G", vtype="continuous", lower=0.3, upper=1.1, units=""),
        ],
        objectives=[
            ObjectiveSpec(field="outputs.P_fus", direction="max", description="maximize fusion power"),
            ObjectiveSpec(field="derived.distance_to_feasible", direction="min", description="minimize distance to feasibility"),
        ],
        constraints=[
            ConstraintSpec(margin_field="constraints.*.margin", kind="hard", description="all hard margins must be >=0"),
        ],
        notes="Default spec; tailor per concept family + intent.",
    )
    return ps.to_json_dict()

def run_reference_optimizer(
    family_yaml: Path,
    out_dir: Path,
    *,
    seed: int = 1,
    n_proposals: int = 64,
    evaluator_label: str = "hot_ion_point",
    intent_override: Optional[str] = None,
    robust: bool = False,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(int(seed))

    fam = load_concept_family(family_yaml)
    if intent_override:
        fam.intent = intent_override  # type: ignore[attr-defined]

    # build problem spec (demo). In UI, user can edit JSON.
    problem_spec = build_default_problem_spec(name=str(fam.name))

    # propose candidate overrides
    vars_ = problem_spec["variables"]
    proposals = []
    for i in range(int(n_proposals)):
        x = {}
        for v in vars_:
            x[v["name"]] = _sample_var(rng, v)
        proposals.append({"id": f"p{i:04d}", "overrides": x})

    # Convert to a synthetic family with these candidates
    fam.candidates = [p["overrides"] for p in proposals]  # type: ignore[assignment]

    run = evaluate_concept_family(
        family=fam,
        evaluator_label=evaluator_label,
        cache_enabled=True,
        cache_dir=out_dir / ".cache",
        export_evidence_packs=False,
        evidence_dir=None,
    )

    # robust evaluation (UQ-lite corners): compute worst-case min_hard_margin across scenarios
    scenarios = default_corner_scenarios() if robust else []
    robust_hash = scenarios_hash(scenarios) if robust else ""
    robust_worst = {}

    if robust:
        # For each candidate: evaluate all corners by perturbing base_inputs with scenario overrides.
        # We do this deterministically by reusing evaluate_concept_family on per-scenario families.
        for cid, art in run.artifacts.items():
            worst = float("inf")
            worst_scn = "BASE"
            for scn in scenarios:
                fam2 = load_concept_family(family_yaml)
                if intent_override:
                    fam2.intent = intent_override  # type: ignore[attr-defined]
                # apply scenario overrides to base inputs
                fam2.base_inputs = dict(fam2.base_inputs)  # type: ignore[attr-defined]
                fam2.base_inputs.update(scn.overrides)  # type: ignore[attr-defined]
                # single candidate overrides
                fam2.candidates = [proposals[int(cid[1:])]["overrides"]]  # type: ignore[attr-defined]
                run2 = evaluate_concept_family(
                    family=fam2,
                    evaluator_label=evaluator_label,
                    cache_enabled=True,
                    cache_dir=out_dir / ".cache",
                    export_evidence_packs=False,
                    evidence_dir=None,
                )
                art2 = list(run2.artifacts.values())[0] if run2.artifacts else {}
                m = compute_feasibility_metrics(art2)
                if m.min_hard_margin < worst:
                    worst = m.min_hard_margin
                    worst_scn = scn.name
            robust_worst[cid] = {"worst_min_hard_margin": worst, "worst_scenario": worst_scn}

    # Build optimizer trace JSON
    trace = {
        "schema_version": "extopt.optimizer_trace.v1",
        "optimizer": "reference_optimizer",
        "seed": int(seed),
        "n_proposals": int(n_proposals),
        "robust": bool(robust),
        "robust_scenarios_hash": robust_hash,
        "family_source": str(family_yaml),
        "timestamp_utc": time.time(),
        "candidates": [],
    }

    candidates = []
    for cid, art in run.artifacts.items():
        m = compute_feasibility_metrics(art)
        entry = {
            "cid": cid,
            "verdict": art.get("verdict"),
            "min_hard_margin": m.min_hard_margin,
            "sum_hard_violation": m.sum_hard_violation,
            "n_hard_violations": m.n_hard_violations,
            "dominant_mechanism": art.get("dominant_mechanism"),
            "dominant_constraint": art.get("dominant_constraint"),
        }
        if robust and cid in robust_worst:
            entry.update(robust_worst[cid])
        trace["candidates"].append(entry)
        candidates.append(BundleCandidate(cid=str(cid), artifact=dict(art) if isinstance(art, dict) else {}, cache_hit=False))

    prov = BundleProvenance(
        shams_version="unknown",
        evaluator_label=str(evaluator_label),
        intent=str(fam.intent),
        family_name=str(fam.name),
        family_source=str(family_yaml),
    )
    bundle_path = out_dir / "optimizer_bundle.zip"
    runspec = {
        "schema_version": "extopt.runspec.v1",
        "optimizer": "reference_optimizer",
        "seed": int(seed),
        "robust": bool(robust),
        "robust_scenarios": [{"name": s.name, "overrides": s.overrides} for s in scenarios],
    }
    export_bundle_zip(
        out_zip=bundle_path,
        candidates=candidates,
        provenance=prov,
        include_artifact_json=True,
        include_evidence_packs=False,
        evidence_pack_paths={},
        problem_spec_json=problem_spec,
        runspec_json=runspec,
        optimizer_trace_json=trace,
    )
    # Also emit the trace JSON side-by-side for convenience
    (out_dir / "optimizer_trace.json").write_text(json.dumps(trace, sort_keys=True, indent=2), encoding="utf-8")
    (out_dir / "problem_spec.json").write_text(json.dumps(problem_spec, sort_keys=True, indent=2), encoding="utf-8")
    (out_dir / "runspec.json").write_text(json.dumps(runspec, sort_keys=True, indent=2), encoding="utf-8")
    return bundle_path
