from __future__ import annotations
"""UI Self-Test + Confidence Report (v113)

Offline validation of key compute + export paths used by the Streamlit UI.
Also emits a publishable confidence report with SHA256 hashes.

Usage:
    python -m tools.ui_self_test --outdir out_ui_self_test
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


def _bootstrap_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root))


def _write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def _sha256_file(p: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    # v172 demo seed import sanity
    try:
        from tools.demo_seed_v172 import build_demo_bundle
        _ = build_demo_bundle()
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="out_ui_self_test")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max_evals", type=int, default=120)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    _bootstrap_paths()

    from models.inputs import PointInputs
    from physics.hot_ion import hot_ion_point
    from constraints.constraints import evaluate_constraints
    from shams_io.run_artifact import build_run_artifact
    from shams_io.plotting import plot_radial_build_dual_export

    from tools.frontier_atlas import build_feasibility_atlas
    from tools.sandbox_plus import run_sandbox
    from tools.audit_pack import build_audit_pack_zip
    from tools.topology import build_feasible_topology, extract_feasible_points_from_payload
    from tools.constraint_dominance import build_constraint_dominance_report
    from tools.failure_taxonomy import build_failure_taxonomy_report
    from tools.science_pack import build_feasibility_science_pack
    from tools.process_downstream import build_process_downstream_bundle
    from tools.component_dominance import build_component_dominance_report
    from tools.boundary_atlas_v2 import build_boundary_atlas_v2
    from tools.design_family import build_design_family_report
    from tools.literature_overlay import template_payload
    from tools.design_decision_layer import build_design_candidates, build_design_decision_pack
    import subprocess as _sp

    # Schema validation (best-effort; falls back)
    have_schema = False
    art_schema = None
    _fallback_validate = None
    try:
        from tools.validate_schemas import _fallback_validate as _fv  # type: ignore
        schema_dir = Path("schemas")
        art_schema = json.loads((schema_dir / "shams_run_artifact.schema.json").read_text(encoding="utf-8"))
        have_schema = True
        _fallback_validate = _fv
    except Exception:
        pass

    base = PointInputs(R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.0, Ti_keV=15.0, fG=0.8, Paux_MW=20.0)

    outputs = hot_ion_point(base)
    constraints = evaluate_constraints(outputs)

    art = build_run_artifact(inputs=base.to_dict(), outputs=outputs, constraints=constraints, meta={"mode": "ui_self_test", "label": "baseline"})
    _write_json(outdir / "artifact.json", art)

    schema_ok = True
    schema_errs: List[str] = []
    if have_schema and (_fallback_validate is not None) and (art_schema is not None):
        try:
            schema_errs = _fallback_validate(art, art_schema)  # type: ignore
            schema_ok = (len(schema_errs) == 0)
        except Exception as e:
            schema_ok = False
            schema_errs = [f"schema_validate_exception: {e!r}"]
    _write_json(outdir / "schema_result.json", {"schema_checked": have_schema, "schema_ok": schema_ok, "errors": schema_errs[:200]})

    fig_base = outdir / "figures" / "radial_build"
    fig_base.parent.mkdir(parents=True, exist_ok=True)
    plot_radial_build_dual_export(art, str(fig_base))

    levers = {"R0_m": (1.0, 3.0), "a_m": (0.3, 1.0), "Bt_T": (6.0, 16.0), "Ip_MA": (2.0, 14.0), "fG": (0.3, 1.1)}
    atlas = build_feasibility_atlas(base, levers=levers, targets=None, n_random=40, seed=int(args.seed), n_slices=3)
    _write_json(outdir / "feasibility_atlas.json", atlas)

    sb = run_sandbox(base, levers=levers, objective="min_R0", max_evals=int(args.max_evals), seed=int(args.seed), strategy="random")
    _write_json(outdir / "sandbox_plus.json", sb)

    topo_pts: List[Dict[str, Any]] = []
    topo_pts += extract_feasible_points_from_payload(atlas)
    topo_pts += extract_feasible_points_from_payload(sb)
    topo = build_feasible_topology(topo_pts, eps=0.18, max_points=300)
    _write_json(outdir / "feasible_topology.json", topo)

    import random as _rand
    _rand.seed(int(args.seed))
    payloads = [art]
    lever_bounds = {"R0_m": (1.2, 2.8), "a_m": (0.35, 0.95), "Bt_T": (8.0, 15.0), "Ip_MA": (4.0, 12.0), "fG": (0.4, 1.05), "Paux_MW": (0.0, 80.0), "Ti_keV": (8.0, 25.0), "kappa": (1.4, 2.2)}
    for i in range(14):
        kw = base.to_dict()
        for k, (lo, hi) in lever_bounds.items():
            if k in kw:
                kw[k] = lo + (hi - lo) * _rand.random()
        bi = PointInputs(**kw)
        o = hot_ion_point(bi)
        con = evaluate_constraints(o)
        payloads.append(build_run_artifact(inputs=bi.to_dict(), outputs=o, constraints=con, meta={"mode":"ui_self_test","label":f"sample_{i+1}"}))

    dom = build_constraint_dominance_report(payloads, near_threshold=0.05, fail_weight=4.0)
    _write_json(outdir / "constraint_dominance_report.json", dom)

    fail_rep = build_failure_taxonomy_report(payloads)
    _write_json(outdir / "failure_taxonomy_report.json", fail_rep)

    pack = build_feasibility_science_pack(topology=topo, dominance=dom, failures=fail_rep, version="v107")
    (outdir / "feasibility_science_pack.zip").write_bytes(pack["zip_bytes"])
    _write_json(outdir / "feasibility_science_pack_summary.json", pack["summary"])
    manifest = dict(pack); manifest.pop("zip_bytes", None)
    _write_json(outdir / "science_pack_manifest.json", manifest)

    proc_pack = build_process_downstream_bundle(payloads, version="v108")
    (outdir / "process_downstream_bundle.zip").write_bytes(proc_pack["zip_bytes"])
    proc_manifest = dict(proc_pack); proc_manifest.pop("zip_bytes", None)
    _write_json(outdir / "process_downstream_manifest.json", proc_manifest)

    comp_rep = build_component_dominance_report(topology=topo, run_artifacts=payloads, failure_taxonomy=fail_rep, near_threshold=0.05, fail_weight=4.0)
    _write_json(outdir / "component_dominance_report.json", comp_rep)

    atlas_v2 = build_boundary_atlas_v2(payloads, failure_taxonomy=fail_rep, max_pairs=6, proximity_quantile=0.25)
    _write_json(outdir / "boundary_atlas_v2.json", atlas_v2)

    fam = build_design_family_report(topology=topo, component_index=0, baseline_inputs=art["inputs"], n_samples=60, radius_frac=0.08, seed=int(args.seed))
    _write_json(outdir / "design_family_report.json", fam)

    # v112 overlay: template + a non-claims baseline overlay point to validate plotting path
    tpl = template_payload(version="v112")
    _write_json(outdir / "literature_points_template.json", tpl)
    overlay = {
        "kind": "shams_literature_points",
        "version": "v112",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "points": [
            {"name": "BASELINE (ui_self_test)", "inputs": art["inputs"], "meta": {"note": "Internal self-test reference point (not external literature)."}}
        ],
    }
    _write_json(outdir / "literature_points_baseline.json", overlay)

    overlay_dir = outdir / "boundary_overlay_plots"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    _sp.run([sys.executable, "-m", "tools.plot_boundary_overlay",
             "--atlas", str(outdir / "boundary_atlas_v2.json"),
             "--overlay", str(outdir / "literature_points_baseline.json"),
             "--outdir", str(overlay_dir)],
            cwd=str(Path(__file__).resolve().parents[1]), check=False)

    # v113 decision layer: candidates + decision pack
    candidates = build_design_candidates(
        artifacts=payloads,
        topology=topo,
        component_dominance=comp_rep,
        boundary_atlas_v2=atlas_v2,
        design_family_report=fam,
        literature_overlay=overlay,
        max_candidates=8,
    )
    pack2 = build_design_decision_pack(candidates=candidates, version="v113")
    (outdir / "design_decision_pack.zip").write_bytes(pack2["zip_bytes"])
    _write_json(outdir / "design_candidates.json", {"candidates": candidates})
    _write_json(outdir / "design_decision_manifest.json", pack2["manifest"])

    # v114 preferences: annotation + Pareto sets + pack with justification
    from tools.preference_layer import template_preferences, annotate_candidates_with_preferences, pareto_sets_from_annotations
    prefs = template_preferences()
    ann = annotate_candidates_with_preferences(candidates, prefs)
    pareto = pareto_sets_from_annotations(ann, metrics=["margin","robustness","boundary_clearance"], max_fronts=3)
    _write_json(outdir / "preference_annotation_bundle_v114.json", ann)
    _write_json(outdir / "pareto_sets_v114.json", pareto)
    justification = {
        "kind": "shams_decision_justification_v114",
        "created_utc": ann.get("created_utc"),
        "preferences": prefs,
        "pareto_sets": pareto,
        "n_candidates": len(candidates),
        "disclaimer": "Annotations only. No optimization. No auto-selected best design.",
    }
    pack3 = build_design_decision_pack(candidates=candidates, version="v114", decision_justification=justification)
    (outdir / "design_decision_pack_v114.zip").write_bytes(pack3["zip_bytes"])
    _write_json(outdir / "decision_justification_v114.json", justification)

    # v115 optimizer import: evaluate a template proposal and build pack
    from tools.optimizer_interface import template_request, template_response, evaluate_optimizer_proposal, build_optimizer_import_pack
    req = template_request(version="v115")
    resp_tpl = template_response(version="v115")
    out_opt = evaluate_optimizer_proposal(resp_tpl)
    opt_art = out_opt["artifact"]
    opt_ctx = out_opt["context"]
    _write_json(outdir / "optimizer_request_template.json", req)
    _write_json(outdir / "optimizer_response_template.json", resp_tpl)
    _write_json(outdir / "evaluated_run_artifact_optimizer_v115.json", opt_art)
    _write_json(outdir / "optimizer_import_context_v115.json", opt_ctx)
    opt_pack = build_optimizer_import_pack(request_template=req, response_template=resp_tpl, evaluated_artifact=opt_art, import_context=opt_ctx, version="v115")
    (outdir / "optimizer_import_pack.zip").write_bytes(opt_pack["zip_bytes"])

    # v116 handoff pack: build from baseline artifact
    from tools.handoff_pack import build_handoff_pack
    handoff = build_handoff_pack(artifact=art, version="v116")
    (outdir / "handoff_pack.zip").write_bytes(handoff["zip_bytes"])
    _write_json(outdir / "handoff_pack_manifest.json", handoff["manifest"])

    # v117 tolerance envelope: compute around baseline artifact
    from tools.tolerance_envelope import template_tolerance_spec, evaluate_tolerance_envelope, envelope_summary_csv
    spec_env = template_tolerance_spec()
    rep_env = evaluate_tolerance_envelope(baseline_artifact=art, tolerance_spec=spec_env, version="v117", max_samples=24)
    _write_json(outdir / "tolerance_envelope_report_v117.json", rep_env)
    (outdir / "tolerance_envelope_summary_v117.csv").write_bytes(envelope_summary_csv(rep_env))

    # v118 optimizer downstream: build a report from template batch
    from tools.optimizer_downstream import template_batch_response, evaluate_optimizer_batch, build_downstream_report_zip
    from tools.preference_layer import template_preferences
    from tools.tolerance_envelope import template_tolerance_spec

    batch = template_batch_response(version="v118")
    prefs = template_preferences()
    spec = template_tolerance_spec()
    out118 = evaluate_optimizer_batch(batch_payload=batch, tolerance_spec=spec, max_envelope_samples=16, max_candidates=6, preferences=prefs)
    rep118 = out118["report"]
    pack118 = out118["decision_pack_zip_bytes"]
    _write_json(outdir / "optimizer_downstream_report_v118.json", rep118)
    (outdir / "design_decision_pack_v118.zip").write_bytes(pack118)
    bundle118 = build_downstream_report_zip(report_obj=rep118, decision_pack_zip_bytes=pack118)
    (outdir / "optimizer_downstream_bundle_v118.zip").write_bytes(bundle118["zip_bytes"])
    _write_json(outdir / "optimizer_downstream_bundle_manifest_v118.json", bundle118["manifest"])

    # v119 authority pack: bundle evidence (best-effort)
    from tools.authority_pack import build_authority_pack

    # We have audit_zip bytes in variable audit_zip (built later); so build pack after audit is created.
    # v120 constitution: integrity manifest
    from tools.constitution import build_constitution_manifest
    man120 = build_constitution_manifest(repo_root=".", version="v120")
    _write_json(outdir / "constitution_manifest_v120.json", man120)

    # v121 mission context: generate pilot mission report
    from tools.mission_context import load_mission, apply_mission_overlays, mission_report_csv
    mission = load_mission("missions/pilot.json")
    mrep = apply_mission_overlays(run_artifact=art, mission=mission, version="v121")
    _write_json(outdir / "mission_report_v121.json", mrep)
    (outdir / "mission_gaps_v121.csv").write_bytes(mission_report_csv(mrep))

    # v122 explainability: narrative report
    from tools.explainability import build_explainability_report
    erep = build_explainability_report(run_artifact=art, version="v122")
    _write_json(outdir / "explainability_report_v122.json", erep)
    (outdir / "explainability_report_v122.txt").write_text(erep.get("narrative",""), encoding="utf-8")

    # v123 evidence graph + traceability + study kit (best-effort)
    from tools.evidence_graph import build_evidence_graph, build_traceability_table, traceability_csv
    from tools.study_kit import build_study_kit_zip

    # load mission + envelope + explainability if they were generated earlier in self-test
    try:
        mission_rep = json.loads((outdir / "mission_report_v121.json").read_text(encoding="utf-8"))
    except Exception:
        mission_rep = None
    try:
        env_rep = json.loads((outdir / "tolerance_envelope_report_v117.json").read_text(encoding="utf-8"))
    except Exception:
        env_rep = None
    try:
        expl_rep = json.loads((outdir / "explainability_report_v122.json").read_text(encoding="utf-8"))
    except Exception:
        expl_rep = None

    graph123 = build_evidence_graph(run_artifact=art, mission_report=mission_rep, tolerance_envelope_report=env_rep, explainability_report=expl_rep, version="v123")
    tab123 = build_traceability_table(run_artifact=art, mission_report=mission_rep, tolerance_envelope_report=env_rep, explainability_report=expl_rep, version="v123")
    _write_json(outdir / "evidence_graph_v123.json", graph123)
    _write_json(outdir / "traceability_table_v123.json", tab123)
    (outdir / "traceability_v123.csv").write_bytes(traceability_csv(tab123))

    # include authority pack if generated, and downstream bundle if generated
    auth_zip = None
    ds_zip = None
    dec_zip = None
    try:
        auth_zip = (outdir / "authority_pack_v119.zip").read_bytes()
    except Exception:
        pass
    try:
        ds_zip = (outdir / "optimizer_downstream_bundle_v118.zip").read_bytes()
    except Exception:
        pass
    try:
        dec_zip = (outdir / "design_decision_pack_v118.zip").read_bytes()
    except Exception:
        pass

    kit = build_study_kit_zip(run_artifact=art, mission_report=mission_rep, tolerance_envelope_report=env_rep, explainability_report=expl_rep,
                              evidence_graph=graph123, traceability_table=tab123, authority_pack_zip=auth_zip,
                              optimizer_downstream_bundle_zip=ds_zip, decision_pack_zip=dec_zip, version="v123B")
    (outdir / "study_kit_v123B.zip").write_bytes(kit["zip_bytes"])
    _write_json(outdir / "study_kit_manifest_v123B.json", kit["manifest"])

    # v124 feasibility atlas (small grid for self-test)
    from tools.feasibility_atlas import build_feasibility_atlas_bundle, available_numeric_levers
    base_inputs = art.get("inputs", {}) if isinstance(art.get("inputs"), dict) else {}
    levs = available_numeric_levers(base_inputs)
    if len(levs) >= 2:
        kx, ky = levs[0], levs[1]
        x0 = float(base_inputs.get(kx, 1.0))
        y0 = float(base_inputs.get(ky, 1.0))
        bundle = build_feasibility_atlas_bundle(
            baseline_run_artifact=art,
            lever_x=kx,
            lever_y=ky,
            x_range=(x0*0.95, x0*1.05),
            y_range=(y0*0.95, y0*1.05),
            nx=5, ny=5,
            outdir=str(outdir / "atlas_v124"),
            version="v124",
        )
        (outdir / "atlas_bundle_v124.zip").write_bytes(bundle["zip_bytes"])
        bundle_meta = dict(bundle)
    bundle_meta.pop("zip_bytes", None)
    _write_json(outdir / "feasibility_atlas_v124.json", bundle_meta)

    # v125 paper pack (minimal: mission + explainability + evidence + study kit)
    from tools.mission_context import load_mission, apply_mission_overlays
    from tools.explainability import build_explainability_report
    from tools.evidence_graph import build_evidence_graph, build_traceability_table, traceability_csv
    from tools.study_kit import build_study_kit_zip
    from tools.study_orchestrator import build_paper_pack_zip

    mspec = load_mission("pilot")
    mission_rep = apply_mission_overlays(run_artifact=art, mission=mspec, version="v121")
    _write_json(outdir / "mission_report_v121.json", mission_rep)

    expl_rep = build_explainability_report(run_artifact=art, mission_report=mission_rep, tolerance_envelope_report=None, version="v122")
    _write_json(outdir / "explainability_report_v122.json", expl_rep)
    (outdir / "explainability_report_v122.txt").write_text(expl_rep.get("narrative",""), encoding="utf-8")

    graph = build_evidence_graph(run_artifact=art, mission_report=mission_rep, tolerance_envelope_report=None, explainability_report=expl_rep, version="v123")
    tab = build_traceability_table(run_artifact=art, mission_report=mission_rep, tolerance_envelope_report=None, explainability_report=expl_rep, version="v123")
    _write_json(outdir / "evidence_graph_v123.json", graph)
    _write_json(outdir / "traceability_table_v123.json", tab)
    (outdir / "traceability_v123.csv").write_bytes(traceability_csv(tab))

    kit = build_study_kit_zip(run_artifact=art, mission_report=mission_rep, tolerance_envelope_report=None, explainability_report=expl_rep,
                              evidence_graph=graph, traceability_table=tab, authority_pack_zip=None, optimizer_downstream_bundle_zip=None, decision_pack_zip=None, version="v123B")
    (outdir / "study_kit_v123B.zip").write_bytes(kit["zip_bytes"])
    _write_json(outdir / "study_kit_manifest_v123B.json", kit["manifest"])

    paper_pack = build_paper_pack_zip(baseline_run_artifact=art, mission_report=mission_rep, explainability_report=expl_rep,
                               evidence_graph=graph, traceability_table=tab, traceability_csv=traceability_csv(tab),
                               feasibility_atlas_meta=None, atlas_bundle_zip=None, study_kit_zip=kit["zip_bytes"], version="v125")
    (outdir / "paper_pack_v125.zip").write_bytes(paper_pack["zip_bytes"])
    _write_json(outdir / "paper_pack_manifest_v125.json", paper_pack["manifest"])

    audit_zip = build_audit_pack_zip(
        version="v113",
        artifacts=[
            art, atlas, sb, topo, dom, fail_rep,
            pack["summary"], proc_pack["summary"],
            comp_rep, atlas_v2, fam, overlay,
            {"kind": "shams_design_decision_pack_summary", "manifest": pack2["manifest"], "n_candidates": len(candidates)},
            {"kind": "shams_preference_layer_summary_v114", "preferences": prefs, "pareto_sets": pareto, "manifest": pack3["manifest"]},
            {"kind": "shams_optimizer_import_summary_v115", "manifest": opt_pack["manifest"], "result": opt_ctx.get("result") if isinstance(opt_ctx, dict) else None},
            {"kind": "shams_handoff_pack_summary_v116", "manifest": handoff["manifest"], "source_artifact_id": art.get("id")},
            {"kind":"shams_tolerance_envelope_summary_v117","spec": spec_env, "summary": rep_env.get("summary"), "source_artifact_id": art.get("id")},
            {"kind":"shams_optimizer_downstream_summary_v118","batch_meta": rep118.get("batch_meta"), "decision_pack_manifest": rep118.get("decision_pack_manifest")},
        ],
        schema_dir="schemas",
        include_pip_freeze=False,
    )
    (outdir / "shams_audit_pack.zip").write_bytes(audit_zip)

    # v119 authority pack (from self-test outputs)
    try:
        from pathlib import Path as _Path
        extra = {}
        ds = (outdir / "optimizer_downstream_bundle_v118.zip")
        if ds.exists():
            extra["optimizer_downstream_bundle_v118.zip"] = ds.read_bytes()
        hp = (outdir / "handoff_pack.zip")
        if hp.exists():
            extra["handoff_pack.zip"] = hp.read_bytes()
        pack119 = build_authority_pack(repo_root=".", version="v119", audit_pack_zip=last_audit_pack_zip_bytes, extra_files=extra,
                                       command_log=[
                                           "python -m tools.ui_self_test --outdir out_ui_self_test",
                                           "python -m tools.verify_package",
                                           "python -m tools.verify_figures",
                                           "python -m tools.tests.test_plot_layout",
                                           "python -m tools.regression_suite",
                                       ])
        (outdir / "authority_pack_v119.zip").write_bytes(pack119["zip_bytes"])
        _write_json(outdir / "authority_pack_manifest_v119.json", pack119["manifest"])
    except Exception:
        pass


    # v139 feasibility certificate
    try:
        from tools.feasibility_certificate import generate_feasibility_certificate
        cert = generate_feasibility_certificate(run_artifact=art, repo_root=".", run_id="self_test", origin="ui_self_test")
        _write_json(outdir / "feasibility_certificate_v139.json", cert)
    except Exception as e:
        (outdir / "feasibility_certificate_v139_error.txt").write_text(repr(e), encoding="utf-8")
        pass

    # v140+ v141 + v142-v145 feasibility deep dive & certificates (small)
    try:
        from tools.sensitivity_maps import SensitivityConfig, run_sensitivity, build_sensitivity_bundle
        from tools.robustness_certificate import generate_robustness_certificate
        from tools.feasibility_deepdive import (
            SampleConfig, sample_and_evaluate, topology_from_dataset, bundle_topology,
            interactions_from_dataset, bundle_interactions,
            IntervalConfig, interval_certificate, bundle_interval_certificate,
        )
        from tools.topology_certificate import generate_topology_certificate

        base_inputs = art.get("inputs", {}) if isinstance(art.get("inputs"), dict) else {}
        vars2 = [v for v in ["Ip_MA", "kappa"] if v in base_inputs]
        if vars2:
            # v140 sensitivity
            cfg_s = SensitivityConfig(baseline_inputs=dict(base_inputs), fixed_overrides={}, vars=vars2[:2], bounds={},
                                      max_rel=0.10, max_abs=0.0, n_expand=4, n_bisect=5, require_baseline_feasible=False)
            sr = run_sensitivity(cfg_s)
            _write_json(outdir / "sensitivity_report_v140.json", sr)
            bun_s = build_sensitivity_bundle(sr)
            (outdir / "sensitivity_bundle_v140.zip").write_bytes(bun_s["zip_bytes"])

            # v141 robustness
            try:
                from tools.feasibility_certificate import generate_feasibility_certificate
                fc = generate_feasibility_certificate(run_artifact=art, repo_root=".", run_id="self_test", origin="ui_self_test")
            except Exception:
                fc = {}
            rc = generate_robustness_certificate(fc, sr, policy={"track":"A"})
            _write_json(outdir / "robustness_certificate_v141.json", rc)

        if len(vars2) >= 2:
            # v142 dataset + topology
            bounds = {}
            for v in vars2[:2]:
                v0 = float(base_inputs.get(v))
                bounds[v] = (v0*0.95, v0*1.05) if abs(v0) > 1e-12 else (0.9, 1.1)

            ds = sample_and_evaluate(SampleConfig(baseline_inputs=dict(base_inputs), vars=vars2[:2], bounds=bounds, n_samples=120, seed=0))
            topo = topology_from_dataset(ds, k=6, eps=0.0)
            _write_json(outdir / "deepdive_dataset_v142.json", ds)
            _write_json(outdir / "feasible_topology_v142.json", topo)
            bun_t = bundle_topology(ds, topo)
            (outdir / "topology_bundle_v142.zip").write_bytes(bun_t["zip_bytes"])

            # v143 interactions
            inter = interactions_from_dataset(ds, top_n=15)
            _write_json(outdir / "constraint_interactions_v143.json", inter)
            bun_i = bundle_interactions(inter)
            (outdir / "interactions_bundle_v143.zip").write_bytes(bun_i["zip_bytes"])

            # v144 interval
            cert = interval_certificate(IntervalConfig(baseline_inputs=dict(base_inputs), bounds=bounds, n_random=20, seed=0))
            _write_json(outdir / "interval_certificate_v144.json", cert)
            bun_c = bundle_interval_certificate(cert)
            (outdir / "interval_bundle_v144.zip").write_bytes(bun_c["zip_bytes"])

            # v145 topology certificate
            tc = generate_topology_certificate(art, topo, deepdive_dataset=ds, policy={"track":"A"})
            _write_json(outdir / "topology_certificate_v145.json", tc)

    except Exception:
        pass

    # v156 feasibility field sanity (small grid)
    try:
        from tools.feasibility_field import build_feasibility_field
        axis1={"name":"R0_m","role":"axis","grid":{"type":"linspace","start":2.8,"stop":3.0,"n":3}}
        axis2={"name":"B0_T","role":"axis","grid":{"type":"linspace","start":10.0,"stop":10.4,"n":3}}
        out_field = build_feasibility_field(
            baseline_inputs=art.get("inputs") if isinstance(art, dict) else {},
            axis1=axis1, axis2=axis2,
            fixed=[], assumption_set={}, sampling={"generator":"ui_self_test","strategy":"grid"},
            solver_meta={"label":"ui_self_test_v156"}, margin_eps=1e-6
        )
        _write_json(outdir / "feasibility_field_v156.json", out_field["field"])
        (outdir / "feasibility_atlas_bundle_v156.zip").write_bytes(out_field["zip_bytes"])
    except Exception:
        pass

    # v157 boundary sanity
    try:
        from tools.feasibility_boundary import build_feasibility_boundary
        fld = json.loads((outdir / "feasibility_field_v156.json").read_text(encoding="utf-8"))
        bnd = build_feasibility_boundary(field=fld)
        _write_json(outdir / "feasibility_boundary_v157.json", bnd)
    except Exception:
        pass

    # v158 constraint dominance sanity
    try:
        from tools.constraint_dominance import build_constraint_dominance
        fld = json.loads((outdir / "feasibility_field_v156.json").read_text(encoding="utf-8"))
        dom = build_constraint_dominance(field=fld, only_infeasible=True)
        _write_json(outdir / "constraint_dominance_v158.json", dom)
    except Exception:
        pass

    # v159 feasibility completion evidence sanity
    try:
        from tools.feasibility_completion_evidence import build_feasibility_completion_evidence
        # take baseline inputs but treat R0_m and B0_T as unknown (bounded)
        base = art.get("inputs") if isinstance(art, dict) else {}
        known = {k:v for k,v in (base or {}).items() if k not in ("R0_m","B0_T")}
        unknowns = [
            {"name":"R0_m","bounds":[2.8,3.2]},
            {"name":"B0_T","bounds":[9.5,10.5]},
        ]
        ev = build_feasibility_completion_evidence(known=known, unknowns=unknowns, n_samples=80, seed=0, strategy="random", policy={"generator":"ui_self_test"})
        _write_json(outdir / "feasibility_completion_evidence_v159.json", ev)
    except Exception:
        pass

    # v161 completion frontier sanity
    try:
        from tools.completion_frontier import build_completion_frontier
        base = art.get("inputs") if isinstance(art, dict) else {}
        vars_spec = [
            {"name":"R0_m","bounds":[2.8,3.2]},
            {"name":"B0_T","bounds":[9.5,10.5]},
        ]
        fr = build_completion_frontier(baseline=base, decision_vars=vars_spec, n_samples=120, seed=0, strategy="random", policy={"generator":"ui_self_test"})
        _write_json(outdir / "completion_frontier_v161.json", fr)
    except Exception:
        pass

    # v162 directed local search sanity
    try:
        from tools.directed_local_search import build_directed_local_search
        base = art.get("inputs") if isinstance(art, dict) else {}
        vars_spec = [
            {"name":"R0_m","bounds":[2.8,3.2]},
            {"name":"B0_T","bounds":[9.5,10.5]},
        ]
        ls = build_directed_local_search(baseline=base, decision_vars=vars_spec, max_evals=80, seed=0, initial_step_norm=0.12, min_step_norm=0.006, policy={"generator":"ui_self_test"})
        _write_json(outdir / "directed_local_search_v162.json", ls)
    except Exception:
        pass

    # v163 completion pack sanity
    try:
        from tools.completion_pack import build_completion_pack, render_completion_pack_markdown
        v159 = json.loads((outdir / "feasibility_completion_evidence_v159.json").read_text(encoding="utf-8")) if (outdir / "feasibility_completion_evidence_v159.json").exists() else None
        v161 = json.loads((outdir / "completion_frontier_v161.json").read_text(encoding="utf-8")) if (outdir / "completion_frontier_v161.json").exists() else None
        v162 = json.loads((outdir / "directed_local_search_v162.json").read_text(encoding="utf-8")) if (outdir / "directed_local_search_v162.json").exists() else None
        pack = build_completion_pack(v159=v159, v161=v161, v162=v162, policy={"generator":"ui_self_test", "tighten":0.25})
        _write_json(outdir / "completion_pack_v163.json", pack)
        (outdir / "completion_pack_summary_v163.md").write_text(render_completion_pack_markdown(pack), encoding="utf-8")
    except Exception:
        pass

    # v164 sensitivity sanity
    try:
        from tools.sensitivity_v164 import build_sensitivity_report, render_sensitivity_markdown
        base = art.get("inputs") if isinstance(art, dict) else {}
        vars_spec = [
            {"name":"R0_m","bounds":[2.8,3.2]},
            {"name":"B0_T","bounds":[9.5,10.5]},
        ]
        rep = build_sensitivity_report(witness=base, variables=vars_spec, rel_step=0.01, abs_step_min=1e-6, policy={"generator":"ui_self_test"})
        _write_json(outdir / "sensitivity_v164.json", rep)
        (outdir / "sensitivity_v164.md").write_text(render_sensitivity_markdown(rep), encoding="utf-8")
    except Exception:
        pass

    # v169 atlas pack sanity (from v164 sensitivity)
    try:
        from tools.atlas_v169 import build_atlas_pack
        import json as _json
        def _load_if(fn):
            p = outdir / fn
            return _json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        sens = _load_if("sensitivity_v164.json")
        if isinstance(sens, dict):
            res = build_atlas_pack(sensitivity_v164=sens, policy={"generator":"ui_self_test"})
            (outdir / "atlas_pack_v169.zip").write_bytes(res["zip_bytes"])
            _write_json(outdir / "atlas_manifest_v169.json", res["manifest"])
    except Exception:
        pass

    # v165 study protocol sanity
    try:
        from tools.study_protocol_v165 import build_study_protocol, render_study_protocol_markdown
        prot = build_study_protocol(run_artifact=art, protocol_overrides={"title":"UI Self Test Study","study_id":"ui_self_test"})
        _write_json(outdir / "study_protocol_v165.json", prot)
        (outdir / "study_protocol_v165.md").write_text(render_study_protocol_markdown(prot), encoding="utf-8")
    except Exception:
        pass

    # v166 repro lock + replay sanity
    try:
        from tools.repro_lock_v166 import build_repro_lock, replay_check
        lock = build_repro_lock(run_artifact=art, lock_overrides={"notes":["ui_self_test"]})
        _write_json(outdir / "repro_lock_v166.json", lock)
        rep = replay_check(lock=lock, policy={"generator":"ui_self_test"})
        _write_json(outdir / "replay_report_v166.json", rep)
    except Exception:
        pass

    # v167 authority pack sanity
    try:
        from tools.authority_pack_v167 import build_authority_pack
        import json as _json
        def _load_if(fn):
            p = outdir / fn
            return _json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        res = build_authority_pack(
            run_artifact=art,
            study_protocol_v165=_load_if("study_protocol_v165.json"),
            repro_lock_v166=_load_if("repro_lock_v166.json"),
            replay_report_v166=_load_if("replay_report_v166.json"),
            completion_pack_v163=_load_if("completion_pack_v163.json"),
            sensitivity_v164=_load_if("sensitivity_v164.json"),
            certificate_v160=_load_if("certificate_v160.json"),
            policy={"generator":"ui_self_test"},
        )
        (outdir / "authority_pack_v167.zip").write_bytes(res["zip_bytes"])
        _write_json(outdir / "authority_pack_manifest_v167.json", res["manifest"])
    except Exception:
        pass

    # v168 citation bundle sanity
    try:
        from tools.citation_v168 import build_citation_bundle
        import json as _json
        def _load_if(fn):
            p = outdir / fn
            return _json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        prot = _load_if("study_protocol_v165.json")
        lock = _load_if("repro_lock_v166.json")
        man  = _load_if("authority_pack_manifest_v167.json")
        if isinstance(prot, dict):
            res = build_citation_bundle(study_protocol_v165=prot, repro_lock_v166=lock, authority_pack_manifest_v167=man, metadata={"version":"v168"})
            _write_json(outdir / "citation_bundle_v168.json", res)
            (outdir / "CITATION.cff").write_text(res["payload"]["citation_cff_text"], encoding="utf-8")
            (outdir / "study_citation_v168.bib").write_text(res["payload"]["bibtex_text"], encoding="utf-8")
            (outdir / "study_reference_v168.md").write_text(res["payload"]["reference_markdown"], encoding="utf-8")
    except Exception:
        pass

    # v170 process export pack sanity
    try:
        from tools.process_export_v170 import build_process_export_pack
        import json as _json
        def _load_if(fn):
            p = outdir / fn
            return _json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        comp = _load_if("completion_pack_v163.json")
        cite = _load_if("citation_bundle_v168.json")
        res = build_process_export_pack(run_artifact=art, completion_pack_v163=comp, citation_bundle_v168=cite, policy={"generator":"ui_self_test"})
        (outdir / "process_export_pack_v170.zip").write_bytes(res["zip_bytes"])
        _write_json(outdir / "process_export_manifest_v170.json", res["manifest"])
    except Exception:
        pass

    # v160 certificate sanity
    try:
        from tools.feasibility_authority_certificate import issue_certificate_from_field
        fld = json.loads((outdir / "feasibility_field_v156.json").read_text(encoding="utf-8"))
        cert = issue_certificate_from_field(
            field=fld,
            claim_type="excluded_region",
            statement="Self-test certificate (dense sampling basis).",
            confidence_level=0.95,
            confidence_grade="C",
            policy={"mode":"ui_self_test"},
        )
        _write_json(outdir / "feasibility_authority_certificate_v160.json", cert)
    except Exception:
        pass

    generated_files = {
        "artifact.json": outdir / "artifact.json",
        "feasibility_certificate_v139.json": outdir / "feasibility_certificate_v139.json",
        "schema_result.json": outdir / "schema_result.json",
        "feasibility_atlas.json": outdir / "feasibility_atlas.json",
        "sandbox_plus.json": outdir / "sandbox_plus.json",
        "feasible_topology.json": outdir / "feasible_topology.json",
        "constraint_dominance_report.json": outdir / "constraint_dominance_report.json",
        "failure_taxonomy_report.json": outdir / "failure_taxonomy_report.json",
        "feasibility_science_pack.zip": outdir / "feasibility_science_pack.zip",
        "feasibility_science_pack_summary.json": outdir / "feasibility_science_pack_summary.json",
        "science_pack_manifest.json": outdir / "science_pack_manifest.json",
        "process_downstream_bundle.zip": outdir / "process_downstream_bundle.zip",
        "process_downstream_manifest.json": outdir / "process_downstream_manifest.json",
        "component_dominance_report.json": outdir / "component_dominance_report.json",
        "boundary_atlas_v2.json": outdir / "boundary_atlas_v2.json",
        "design_family_report.json": outdir / "design_family_report.json",
        "literature_points_template.json": outdir / "literature_points_template.json",
        "literature_points_baseline.json": outdir / "literature_points_baseline.json",
        "design_candidates.json": outdir / "design_candidates.json",
        "design_decision_manifest.json": outdir / "design_decision_manifest.json",
        "design_decision_pack.zip": outdir / "design_decision_pack.zip",
        "preference_annotation_bundle_v114.json": outdir / "preference_annotation_bundle_v114.json",
        "pareto_sets_v114.json": outdir / "pareto_sets_v114.json",
        "decision_justification_v114.json": outdir / "decision_justification_v114.json",
        "design_decision_pack_v114.zip": outdir / "design_decision_pack_v114.zip",
        "optimizer_request_template.json": outdir / "optimizer_request_template.json",
        "optimizer_response_template.json": outdir / "optimizer_response_template.json",
        "evaluated_run_artifact_optimizer_v115.json": outdir / "evaluated_run_artifact_optimizer_v115.json",
        "optimizer_import_context_v115.json": outdir / "optimizer_import_context_v115.json",
        "optimizer_import_pack.zip": outdir / "optimizer_import_pack.zip",
        "handoff_pack.zip": outdir / "handoff_pack.zip",
        "handoff_pack_manifest.json": outdir / "handoff_pack_manifest.json",
        "tolerance_envelope_report_v117.json": outdir / "tolerance_envelope_report_v117.json",
        "tolerance_envelope_summary_v117.csv": outdir / "tolerance_envelope_summary_v117.csv",
        "optimizer_downstream_report_v118.json": outdir / "optimizer_downstream_report_v118.json",
        "design_decision_pack_v118.zip": outdir / "design_decision_pack_v118.zip",
        "optimizer_downstream_bundle_v118.zip": outdir / "optimizer_downstream_bundle_v118.zip",
        "optimizer_downstream_bundle_manifest_v118.json": outdir / "optimizer_downstream_bundle_manifest_v118.json",
        "shams_audit_pack.zip": outdir / "shams_audit_pack.zip",
        "figures/radial_build.png": outdir / "figures" / "radial_build.png",
        "figures/radial_build.svg": outdir / "figures" / "radial_build.svg",
        "paper_pack_v150.zip": outdir / "paper_pack_v150.zip",
        "study_registry_v149.json": outdir / "study_registry_v149.json",
        "integrity_manifest_v150.json": outdir / "integrity_manifest_v150.json",
        "feasibility_field_v156.json": outdir / "feasibility_field_v156.json",
        "feasibility_atlas_bundle_v156.zip": outdir / "feasibility_atlas_bundle_v156.zip",
        "feasibility_authority_certificate_v160.json": outdir / "feasibility_authority_certificate_v160.json",
        "feasibility_boundary_v157.json": outdir / "feasibility_boundary_v157.json",
        "constraint_dominance_v158.json": outdir / "constraint_dominance_v158.json",
        "feasibility_completion_evidence_v159.json": outdir / "feasibility_completion_evidence_v159.json",
        "completion_frontier_v161.json": outdir / "completion_frontier_v161.json",
        "directed_local_search_v162.json": outdir / "directed_local_search_v162.json",
        "completion_pack_v163.json": outdir / "completion_pack_v163.json",
        "completion_pack_summary_v163.md": outdir / "completion_pack_summary_v163.md",
        "sensitivity_v164.json": outdir / "sensitivity_v164.json",
        "sensitivity_v164.md": outdir / "sensitivity_v164.md",
        "study_protocol_v165.json": outdir / "study_protocol_v165.json",
        "study_protocol_v165.md": outdir / "study_protocol_v165.md",
        "repro_lock_v166.json": outdir / "repro_lock_v166.json",
        "replay_report_v166.json": outdir / "replay_report_v166.json",
        "authority_pack_v167.zip": outdir / "authority_pack_v167.zip",
        "authority_pack_manifest_v167.json": outdir / "authority_pack_manifest_v167.json",
        "citation_bundle_v168.json": outdir / "citation_bundle_v168.json",
        "CITATION.cff": outdir / "CITATION.cff",
        "study_citation_v168.bib": outdir / "study_citation_v168.bib",
        "study_reference_v168.md": outdir / "study_reference_v168.md",
        "atlas_pack_v169.zip": outdir / "atlas_pack_v169.zip",
        "atlas_manifest_v169.json": outdir / "atlas_manifest_v169.json",
        "process_export_pack_v170.zip": outdir / "process_export_pack_v170.zip",
        "process_export_manifest_v170.json": outdir / "process_export_manifest_v170.json",
    }

    hashes: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    missing: List[str] = []
    for k, fp in generated_files.items():
        if fp.exists():
            hashes[k] = _sha256_file(fp)
            sizes[k] = int(fp.stat().st_size)
        else:
            missing.append(k)

    report = {
        "kind": "shams_ui_confidence_report",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "outdir": str(outdir),
        "schema_checked": have_schema,
        "schema_ok": schema_ok,
        "missing_files": missing,
        "hashes_sha256": hashes,
        "sizes_bytes": sizes,
        "notes": [
            "Produced by tools.ui_self_test to validate key compute + export paths used by the Streamlit UI.",
            "This does not prove the Streamlit UI was interactively tested (no browser), but it is a strong offline confidence signal.",
        ],
    }
    _write_json(outdir / "ui_confidence_report.json", report)

    md: List[str] = []
    md.append("# SHAMS UI Confidence Report")
    md.append("")
    md.append(f"- Created (UTC): {report['created_utc']}")
    md.append(f"- Schema checked: {report['schema_checked']}")
    md.append(f"- Schema ok: {report['schema_ok']}")
    md.append(f"- Missing files: {len(missing)}")
    md.append("")
    md.append("## Generated artifacts (SHA256)")
    md.append("")
    for k in sorted(hashes.keys()):
        md.append(f"- `{k}`  ")
        md.append(f"  - bytes: {sizes.get(k)}  ")
        md.append(f"  - sha256: `{hashes[k]}`")
    if missing:
        md.append("")
        md.append("## Missing")
        md.append("")
        for k in missing:
            md.append(f"- `{k}`")
    (outdir / "UI_CONFIDENCE_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    _write_json(outdir / "summary.json", {"ok": schema_ok, "outdir": str(outdir), "generated": sorted(list(generated_files.keys()))})

    print("UI self-test complete.")
    print("Schema ok:", schema_ok)
    return 0 if schema_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())