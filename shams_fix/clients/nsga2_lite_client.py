from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Tuple
import json, random

from clients.repair_kernel import repair_candidate
from src.extopt.family import load_concept_family
from src.extopt.batch import evaluate_concept_family
from src.extopt.metrics import compute_feasibility_metrics
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
        notes="NSGA2-lite reference spec.",
    )
    return ps.to_json_dict()

def _get(art: Dict[str, Any], path: str, default: float = 0.0) -> float:
    cur: Any = art
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return float(default)
    try:
        return float(cur)
    except Exception:
        return float(default)

def dominates(a: Tuple[float,float], b: Tuple[float,float]) -> bool:
    # maximize a0, minimize a1
    return (a[0] >= b[0] and a[1] <= b[1]) and (a[0] > b[0] or a[1] < b[1])

def run_nsga2_lite(
    family_yaml: Path,
    out_dir: Path,
    *,
    seed: int = 1,
    generations: int = 10,
    pop: int = 40,
    evaluator_label: str = "hot_ion_point",
    do_repair: bool = True,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(int(seed))
    fam = load_concept_family(family_yaml)
    ps = build_default_problem_spec(name=str(fam.name))
    vars_ = ps["variables"]

    def sample() -> Dict[str, Any]:
        x={}
        for v in vars_:
            lo=float(v["lower"]); hi=float(v["upper"])
            x[v["name"]] = rng.uniform(lo, hi)
        return x

    population=[sample() for _ in range(int(pop))]
    trace={"schema_version":"extopt.optimizer_trace.v1","optimizer":"nsga2_lite","seed":seed,
           "generations":generations,"pop":pop,"do_repair":do_repair,"generations_trace":[]}

    last_run=None
    for g in range(int(generations)):
        fam.candidates = population  # type: ignore[assignment]
        run = evaluate_concept_family(
            fam,
            evaluator_label=evaluator_label,
            cache_enabled=True,
            cache_dir=out_dir/".cache",
            export_evidence_packs=False,
            evidence_dir=None,
        )
        last_run=run

        scored=[]
        for cid, art in run.artifacts.items():
            P_fus = _get(art, "outputs.P_fus", 0.0)
            dist = _get(art, "derived.distance_to_feasible", compute_feasibility_metrics(art).sum_hard_violation)
            scored.append((cid, art, (P_fus, dist)))

        front=[]
        for i,(cid_i, art_i, f_i) in enumerate(scored):
            dom=False
            for j,(cid_j, art_j, f_j) in enumerate(scored):
                if j==i:
                    continue
                if dominates(f_j, f_i):
                    dom=True
                    break
            if not dom:
                front.append((cid_i, art_i, f_i))
        trace["generations_trace"].append({"g":g,"front_size":len(front)})

        elites = population[:max(2, int(pop)//5)]
        newpop=list(elites)
        while len(newpop) < int(pop):
            parent = rng.choice(elites)
            child=dict(parent)
            for v in vars_:
                name=v["name"]; lo=float(v["lower"]); hi=float(v["upper"])
                child[name] = max(lo, min(hi, float(child[name]) + rng.gauss(0.0, 0.05*(hi-lo))))
            if do_repair and front:
                child = repair_candidate(child, front[0][1])
            newpop.append(child)
        population=newpop

    candidates=[]
    if last_run is not None:
        for cid, art in last_run.artifacts.items():
            candidates.append(BundleCandidate(cid=str(cid), artifact=dict(art), cache_hit=False))

    prov = BundleProvenance(shams_version="unknown", evaluator_label=evaluator_label, intent=str(fam.intent),
                            family_name=str(fam.name), family_source=str(family_yaml))
    runspec={"schema_version":"extopt.runspec.v1","optimizer":"nsga2_lite","seed":seed,"generations":generations,"pop":pop,"do_repair":do_repair}
    bundle = out_dir/"nsga2_lite_bundle.zip"
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
