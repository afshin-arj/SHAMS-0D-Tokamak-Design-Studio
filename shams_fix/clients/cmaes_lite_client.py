from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import json, random

from src.extopt.family import load_concept_family
from src.extopt.batch import evaluate_concept_family
from src.extopt.metrics import compute_feasibility_metrics
from src.extopt.scenarios import default_corner_scenarios, scenarios_hash
from src.extopt.problem_spec import ProblemSpec, VariableSpec, ObjectiveSpec, ConstraintSpec
from src.extopt.bundle import BundleCandidate, BundleProvenance, export_bundle_zip_v273 as export_bundle_zip

def build_default_problem_spec(name: str = "default") -> Dict[str, Any]:
    ps = ProblemSpec(
        name=name,
        variables=[
            VariableSpec(name="Bt", vtype="continuous", lower=4.0, upper=16.0, units="T"),
            VariableSpec(name="Ip", vtype="continuous", lower=5e6, upper=25e6, units="A"),
            VariableSpec(name="Paux", vtype="continuous", lower=0.0, upper=120e6, units="W"),
            VariableSpec(name="f_G", vtype="continuous", lower=0.3, upper=1.1, units=""),
        ],
        objectives=[
            ObjectiveSpec(field="outputs.P_fus", direction="max"),
            ObjectiveSpec(field="derived.distance_to_feasible", direction="min"),
        ],
        constraints=[ConstraintSpec(margin_field="constraints.*.margin", kind="hard")],
        notes="CMAES-lite reference spec.",
    )
    return ps.to_json_dict()

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _score(art: Dict[str, Any]) -> float:
    m = compute_feasibility_metrics(art)
    P_fus = float(((art.get("outputs") or {}).get("P_fus")) or 0.0)
    return -1e6 * m.sum_hard_violation + P_fus

def run_cmaes_lite(
    family_yaml: Path,
    out_dir: Path,
    *,
    seed: int = 1,
    n_iter: int = 20,
    pop: int = 16,
    evaluator_label: str = "hot_ion_point",
    robust: bool = False,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(int(seed))
    fam = load_concept_family(family_yaml)
    ps = build_default_problem_spec(name=str(fam.name))
    vars_ = ps["variables"]

    mean = {v["name"]: 0.5*(float(v["lower"])+float(v["upper"])) for v in vars_}
    sigma = {v["name"]: 0.15*(float(v["upper"])-float(v["lower"])) for v in vars_}

    trace = {"schema_version":"extopt.optimizer_trace.v1","optimizer":"cmaes_lite","seed":seed,"robust":robust,"iterations":[]}

    scenarios = default_corner_scenarios() if robust else []
    trace["robust_scenarios_hash"] = scenarios_hash(scenarios) if robust else ""

    for it in range(int(n_iter)):
        cand_overrides = []
        for _ in range(int(pop)):
            x = {}
            for v in vars_:
                name=v["name"]; lo=float(v["lower"]); hi=float(v["upper"])
                val = rng.gauss(mean[name], sigma[name])
                x[name] = _clamp(val, lo, hi)
            cand_overrides.append(x)

        fam.candidates = cand_overrides  # type: ignore[assignment]
        run = evaluate_concept_family(
            fam,
            evaluator_label=evaluator_label,
            cache_enabled=True,
            cache_dir=out_dir/".cache",
            export_evidence_packs=False,
            evidence_dir=None,
        )
        scored=[(_score(art), cid, art) for cid, art in run.artifacts.items()]
        scored.sort(reverse=True, key=lambda t: t[0])

        if scored:
            best_score, best_cid, best_art = scored[0]
            xin = best_art.get("inputs") or {}
            for v in vars_:
                if v["name"] in xin:
                    mean[v["name"]] = float(xin[v["name"]])
            trace["iterations"].append({"it":it,"best_score":float(best_score)})
        else:
            trace["iterations"].append({"it":it,"best_score":None})

    fam.candidates = [mean]  # type: ignore[assignment]
    run = evaluate_concept_family(
        fam,
        evaluator_label=evaluator_label,
        cache_enabled=True,
        cache_dir=out_dir/".cache",
        export_evidence_packs=False,
        evidence_dir=None,
    )

    candidates=[BundleCandidate(cid=str(cid), artifact=dict(art), cache_hit=False) for cid, art in run.artifacts.items()]
    prov = BundleProvenance(shams_version="unknown", evaluator_label=evaluator_label, intent=str(fam.intent),
                            family_name=str(fam.name), family_source=str(family_yaml))
    runspec={"schema_version":"extopt.runspec.v1","optimizer":"cmaes_lite","seed":seed,"n_iter":n_iter,"pop":pop,"robust":robust,
             "robust_scenarios":[{"name":s.name,"overrides":s.overrides} for s in scenarios]}

    bundle = out_dir/"cmaes_lite_bundle.zip"
    export_bundle_zip(
        out_zip=bundle,
        candidates=candidates,
        provenance=prov,
        include_artifact_json=True,
        include_evidence_packs=False,
        evidence_pack_paths={},
        problem_spec_json=ps,
        runspec_json=runspec,
        optimizer_trace_json=trace,
    )
    (out_dir/"optimizer_trace.json").write_text(json.dumps(trace, sort_keys=True, indent=2), encoding="utf-8")
    return bundle
