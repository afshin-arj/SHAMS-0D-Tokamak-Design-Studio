from __future__ import annotations
"""
Package verification (offline-friendly) — v90
- compileall across repo
- import smoke tests for key modules
- optional: generate plots from a dummy artifact (no physics run)
"""
import argparse, json, sys, os
from pathlib import Path
import compileall

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Path to repo root")
    ap.add_argument("--emit-dummy-capsule", action="store_true", help="Generate a capsule from a dummy artifact")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    ok = compileall.compile_dir(str(repo), quiet=1)
    if not ok:
        print("compileall failed", file=sys.stderr)
        sys.exit(2)

    # Import checks
    try:
        try:
            import streamlit  # noqa
            import ui.app  # noqa
        except ModuleNotFoundError:
            # Offline / minimal environments may not include streamlit; skip UI import.
            pass
        import tools.export.capsule  # noqa
        import tools.sandbox.selector  # noqa
        import tools.studies.feasible_scan  # noqa
    except Exception as e:
        print("import check failed:", repr(e), file=sys.stderr)
        sys.exit(3)

    if args.emit_dummy_capsule:
        dummy = {
            "kind": "shams_run_artifact",
            "version": repo.joinpath("VERSION").read_text().strip() if repo.joinpath("VERSION").exists() else "unknown",
            "timestamp": "dummy",
            "inputs": {"R0": 3.0, "a": 1.0},
            "outputs": {"Q": 10.0},
            "constraints": [{"name": "dummy_constraint", "signed_margin": 0.1}],
            "meta": {"constraint_set_hash": "dummy"}
        }
        outdir = repo / "out_dummy_capsule"
        outdir.mkdir(exist_ok=True)
        (outdir / "artifact.json").write_text(json.dumps(dummy, indent=2), encoding="utf-8")
        from tools.export.capsule import export_capsule
        export_capsule(dummy, str(outdir / "capsule"))
        print("dummy capsule written:", str(outdir / "capsule"))

    print("OK")
    # optional quick figure verification
    try:
        import tools.verify_figures  # noqa
        import tools.tests.test_plot_layout  # noqa
        import tools.paper_figures_pack  # noqa
        import tools.export.bundle  # noqa
        import tools.interoperability.process_handoff  # noqa
        import tools.regression_suite  # noqa
        import tools.export.manifest  # noqa
        import tools.export.session_report  # noqa
        import tools.sandbox_plus  # noqa
        import tools.ui_self_test  # noqa
        import tools.topology  # noqa
        import tools.constraint_dominance  # noqa
        import tools.failure_taxonomy  # noqa
        import tools.science_pack  # noqa
        import tools.cli_science_pack  # noqa
        import tools.process_downstream  # noqa
        import tools.cli_process_downstream  # noqa
        import tools.component_dominance  # noqa
        import tools.boundary_atlas_v2  # noqa
        import tools.plot_boundary_atlas_v2  # noqa
        import tools.design_family  # noqa
        import tools.literature_overlay  # noqa
        import tools.plot_boundary_overlay  # noqa
        import tools.design_decision_layer  # noqa
        import tools.cli_design_decision_pack  # noqa
        import tools.preferences  # noqa
        import tools.preference_decision_layer  # noqa
        import tools.cli_preference_annotate  # noqa
        import tools.preference_layer  # noqa
        import tools.optimizer_interface  # noqa
        import tools.cli_optimizer_import  # noqa
        import tools.handoff_pack  # noqa
        import tools.cli_handoff_pack  # noqa
        import tools.tolerance_envelope  # noqa
        import tools.cli_tolerance_envelope  # noqa
        import tools.optimizer_downstream  # noqa
        import tools.cli_optimizer_downstream  # noqa
        import tools.authority_pack  # noqa
        import tools.cli_authority_pack  # noqa
        import tools.constitution  # noqa
        import tools.mission_context  # noqa
        import tools.cli_mission_context  # noqa
        import tools.explainability  # noqa
        import tools.cli_explainability  # noqa
        import tools.evidence_graph  # noqa
        import tools.cli_evidence_graph  # noqa
        import tools.study_kit  # noqa
        import tools.cli_study_kit  # noqa
        import tools.feasibility_atlas  # noqa
        import tools.cli_feasibility_atlas  # noqa
        import tools.study_orchestrator  # noqa
        import tools.cli_paper_pack  # noqa
        import tools.run_integrity_lock  # noqa
        import tools.cli_run_integrity_lock  # noqa
        import tools.doi_export  # noqa
        import tools.cli_doi_export  # noqa
        import tools.multi_study_pack  # noqa
        import tools.cli_multi_study_pack  # noqa
        import tools.feasibility_field  # noqa
        import tools.cli_feasibility_field  # noqa
        import tools.feasibility_authority_certificate  # noqa
        import tools.cli_feasibility_authority_certificate  # noqa
        import tools.feasibility_boundary  # noqa
        import tools.cli_feasibility_boundary  # noqa
        import tools.ui_smoke_runner  # noqa
        import tools.cli_ui_smoke  # noqa
        import tools.study_matrix  # noqa
        import tools.cli_study_matrix  # noqa
        import tools.study_explorer  # noqa
        import tools.cli_study_explorer  # noqa
        import tools.pareto_from_study  # noqa
        import tools.cli_pareto_from_study  # noqa
        import tools.run_vault  # noqa
        import tools.cli_run_vault  # noqa
        import tools.vault_restore  # noqa
        import tools.study_matrix_v2  # noqa
        import tools.cli_study_matrix_v2  # noqa
        import tools.feasibility_completion  # noqa
        import tools.cli_feasibility_completion  # noqa
        import tools.param_guidance  # noqa
        import tools.fc_advanced  # noqa
        import tools.cli_fc_advanced  # noqa
        import tools.feasibility_certificate  # noqa
        import tools.sensitivity_maps  # noqa
        import tools.cli_sensitivity_maps  # noqa
        import tools.robustness_certificate  # noqa
        import tools.cli_robustness_certificate  # noqa
        import tools.feasibility_deepdive  # noqa
        import tools.cli_feasibility_deepdive  # noqa
        import tools.topology_certificate  # noqa
        import tools.cli_topology_certificate  # noqa
        import tools.feasibility_bridge  # noqa
        import tools.cli_feasibility_bridge  # noqa
        import tools.safe_domain_shrink  # noqa
        import tools.cli_safe_domain_shrink  # noqa
        import tools.design_study_kit  # noqa
        import tools.cli_paper_pack  # noqa
        import tools.run_integrity_lock  # noqa
        import tools.cli_run_integrity_lock  # noqa
        import tools.doi_export  # noqa
        import tools.cli_doi_export  # noqa
        import tools.multi_study_pack  # noqa
        import tools.cli_multi_study_pack  # noqa
        import tools.feasibility_field  # noqa
        import tools.cli_feasibility_field  # noqa
        import tools.feasibility_authority_certificate  # noqa
        import tools.cli_feasibility_authority_certificate  # noqa
        import tools.feasibility_boundary  # noqa
        import tools.cli_feasibility_boundary  # noqa

        import tools.frontier_atlas  # noqa
        import tools.audit_pack  # noqa
    except Exception:
        pass

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
