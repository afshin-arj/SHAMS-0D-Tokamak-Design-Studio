from __future__ import annotations
from pathlib import Path
import json
import streamlit as st


def _read_bytes_to_temp(repo_root: Path, data: bytes, *, name: str) -> Path:
    tdir = repo_root / "ui_runs" / "uploads"
    tdir.mkdir(parents=True, exist_ok=True)
    p = tdir / name
    p.write_bytes(data)
    return p

def render_external_optimizer_suite(repo_root: Path):
    st.markdown("## 📦 External Optimizer Suite")
    st.caption("Reference firewalled optimizers (NSGA2-lite, CMAES-lite) + repair kernel. Produces audit bundles.")

    tabs = st.tabs(["📦 Orchestrator 2.0 (import & verify)", "⚡ Feasible-first surrogate accelerator (v386)", "🧪 Lite optimizers (reference)"])

    # --- v385 Orchestrator 2.0 ---
    with tabs[0]:
        st.markdown("### 📦 Certified External Optimizer Orchestrator 2.0")
        st.caption(
            "Import external candidate dossiers as a concept-family YAML, deterministically re-verify through frozen truth, "
            "and export a reviewer-grade evidence bundle ZIP. No optimization occurs inside SHAMS."
        )

        up = st.file_uploader(
            "Upload concept family YAML (concept_family.v1)",
            type=["yaml", "yml"],
            key="v385_orch_upload_yaml",
            help="External optimizers should export candidates as a concept family YAML: base_inputs + per-candidate overrides.",
        )
        evaluator_label = st.text_input("Evaluator label", value="hot_ion_point", key="v385_orch_eval_label")
        intent = st.selectbox("Design intent for verification", options=["research", "reactor"], index=1, key="v385_orch_intent")
        include_ep = st.toggle("Include per-candidate evidence packs", value=True, key="v385_orch_include_ep")

        out_dir = repo_root / "ui_runs" / "extopt_orchestrator_v385"
        out_dir.mkdir(parents=True, exist_ok=True)

        if st.button("Run import & deterministic verification", use_container_width=True, key="v385_orch_run_btn"):
            if up is None:
                st.error("Please upload a concept family YAML.")
            else:
                try:
                    from src.extopt.orchestrator_v385 import (
                        OrchestratorRunSpec,
                        run_orchestrator_v385_from_concept_family,
                    )

                    p = _read_bytes_to_temp(repo_root, up.read(), name=f"v385_{up.name}")
                    rs = OrchestratorRunSpec(
                        evaluator_label=str(evaluator_label),
                        intent=str(intent),
                        include_evidence_packs=bool(include_ep),
                        cache_enabled=True,
                    )
                    res = run_orchestrator_v385_from_concept_family(
                        concept_family_yaml=p,
                        repo_root=repo_root,
                        out_dir=out_dir,
                        runspec=rs,
                    )
                    st.session_state["extopt_last_run"] = res.__dict__
                    st.session_state["extopt_last_export_zip_path"] = res.bundle_zip
                    st.success("Deterministic verification completed.")
                except Exception as e:
                    st.error(f"Orchestrator failed: {e}")

        # Render from cache only
        last = st.session_state.get("extopt_last_run")
        if isinstance(last, dict) and last:
            st.markdown("#### Last orchestrator run (cached)")
            c1, c2, c3 = st.columns(3)
            c1.metric("Candidates", last.get("n_total", "-"))
            c2.metric("Feasible", last.get("n_feasible", "-"))
            try:
                c3.metric("Pass rate", f"{100.0*float(last.get('pass_rate', 0.0)):.1f}%")
            except Exception:
                c3.metric("Pass rate", "-")

            pzip = st.session_state.get("extopt_last_export_zip_path")
            if isinstance(pzip, str) and pzip:
                pp = Path(pzip)
                if pp.exists():
                    st.download_button(
                        "Download evidence bundle ZIP",
                        data=pp.read_bytes(),
                        file_name=pp.name,
                        mime="application/zip",
                        use_container_width=True,
                        key="v385_orch_dl_bundle",
                    )

            run_dir = Path(str(last.get("run_dir", "")))
            if run_dir.exists():
                led = run_dir / "run_ledger.json"
                if led.exists():
                    st.download_button(
                        "Download run_ledger.json",
                        data=led.read_bytes(),
                        file_name=led.name,
                        mime="application/json",
                        use_container_width=True,
                        key="v385_orch_dl_ledger",
                    )
                rm = run_dir / "RUN_MANIFEST_SHA256.json"
                if rm.exists():
                    st.download_button(
                        "Download RUN_MANIFEST_SHA256.json",
                        data=rm.read_bytes(),
                        file_name=rm.name,
                        mime="application/json",
                        use_container_width=True,
                        key="v385_orch_dl_runman",
                    )
            with st.expander("Details (cached JSON)", expanded=False):
                st.json(last, expanded=False)

    # --- Existing reference suite ---
    
    # --- v386 Feasible-first surrogate accelerator ---
    with tabs[2]:
        st.markdown("### ⚡ Feasible-First Surrogate Accelerator (v386)")
        st.caption(
            "Non-authoritative surrogate screening to reduce truth evaluations. "
            "All reported results still come from frozen truth. Deterministic and auditable."
        )

        # Training sources from cache (best effort)
        src_extopt = st.toggle("Use extopt_last_run as training source", value=True, key="v386_src_extopt")
        src_scan = st.toggle("Use scan_last_grid as training source", value=True, key="v386_src_scan")
        src_pareto = st.toggle("Use pareto_last_front as training source", value=True, key="v386_src_pareto")
        src_opt = st.toggle("Use opt_last_records as training source", value=False, key="v386_src_opt")

        c1, c2, c3 = st.columns(3)
        accept = c1.number_input("Accept margin (likely-feasible)", value=0.05, step=0.01, key="v386_accept_margin")
        reject = c2.number_input("Reject margin (likely-infeasible)", value=-0.05, step=0.01, key="v386_reject_margin")
        max_truth = c3.number_input("Max truth evals / run", value=200, min_value=1, step=10, key="v386_max_truth")

        ridge_alpha = st.number_input("Ridge alpha", value=5.0, min_value=0.0, step=1.0, key="v386_ridge_alpha")

        if st.button("Build surrogate from cached training data", use_container_width=True, key="v386_build_btn"):
            try:
                from src.surrogate.v386_screening import harvest_candidate_records, build_surrogate_min_margin
                sources = []
                ss = st.session_state
                if src_extopt and isinstance(ss.get("extopt_last_run"), dict):
                    sources.append(ss.get("extopt_last_run"))
                if src_scan and ss.get("scan_last_grid") is not None:
                    sources.append(ss.get("scan_last_grid"))
                if src_pareto and ss.get("pareto_last_front") is not None:
                    sources.append(ss.get("pareto_last_front"))
                if src_opt and ss.get("opt_last_records") is not None:
                    sources.append(ss.get("opt_last_records"))

                recs = harvest_candidate_records(*sources)
                model = build_surrogate_min_margin(recs, alpha=float(ridge_alpha))
                st.session_state["surrogate_v386_model"] = model.__dict__
                st.success(f"Surrogate built. Training N={model.train_n}, RMSE(norm)={model.train_rmse:.3f}. Features={len(model.feature_names)}")
            except Exception as e:
                st.error(f"Failed to build surrogate: {e}")

        # Render model card from cache
        m = st.session_state.get("surrogate_v386_model")
        if isinstance(m, dict) and m:
            st.markdown("#### Surrogate model card (cached)")
            c1, c2, c3 = st.columns(3)
            c1.metric("Train N", m.get("train_n", "-"))
            c2.metric("Train RMSE (norm)", f"{float(m.get('train_rmse', 0.0)):.3f}" if str(m.get("train_rmse","")).strip() else "-")
            c3.metric("Features", len(m.get("feature_names", []) or []))
            with st.expander("Model JSON", expanded=False):
                st.json(m)

        st.divider()
        st.markdown("#### Screen a concept family YAML (concept_family.v1)")

        up2 = st.file_uploader(
            "Upload concept family YAML to screen",
            type=["yaml", "yml"],
            key="v386_screen_upload_yaml",
            help="Candidates are screened using the surrogate, then a limited subset is re-verified by frozen truth.",
        )

        if st.button("Run screened verification (truth budgeted)", use_container_width=True, key="v386_screen_run_btn"):
            try:
                if up2 is None:
                    raise ValueError("Please upload a concept family YAML to screen.")
                if not (isinstance(st.session_state.get("surrogate_v386_model"), dict) and st.session_state["surrogate_v386_model"]):
                    raise ValueError("Please build a surrogate model first.")
                from src.extopt.family import load_concept_family
                from src.surrogate.v386_surrogate import RidgeModel
                from src.surrogate.v386_screening import ScreeningSpec, screen_concept_family, build_screening_ledger
                from src.extopt.batch import BatchEvalConfig, evaluate_concept_family

                p = _read_bytes_to_temp(repo_root, up2.read(), name=f"v386_{up2.name}")
                fam = load_concept_family(p)

                md = st.session_state["surrogate_v386_model"]
                model = RidgeModel(**md)
                spec = ScreeningSpec(
                    accept_margin=float(accept),
                    reject_margin=float(reject),
                    max_truth_evals=int(max_truth),
                    ridge_alpha=float(ridge_alpha),
                )
                decisions, selected = screen_concept_family(concept_family=fam, model=model, spec=spec)
                ledger = build_screening_ledger(model=model, spec=spec, decisions=decisions, selected=selected)

                # Build filtered family for truth eval (subset)
                selected_set = set(selected)
                fam_candidates = [c for c in fam.candidates if str(c.cid) in selected_set]
                from dataclasses import replace
                fam_sub = replace(fam, candidates=fam_candidates)

                cfg = BatchEvalConfig(
                    evaluator_label="hot_ion_point",
                    cache_dir=(repo_root / "runs" / "disk_cache"),
                    cache_enabled=True,
                )
                ber = evaluate_concept_family(fam_sub, config=cfg, repo_root=repo_root)

                st.session_state["surrogate_v386_last_screening_run"] = {
                    "ledger": ledger.__dict__,
                    "truth_results": [r.__dict__ for r in ber.results],
                    "n_total": len(decisions),
                    "n_truth": len(fam_candidates),
                }
                st.success(f"Screening completed. Total={len(decisions)}; Truth evaluated={len(fam_candidates)}.")
            except Exception as e:
                st.error(f"Screened verification failed: {e}")

        # Render screening run from cache
        last_run = st.session_state.get("surrogate_v386_last_screening_run")
        if isinstance(last_run, dict) and last_run:
            st.markdown("#### Last screening run (cached)")
            c1, c2 = st.columns(2)
            c1.metric("Total candidates", last_run.get("n_total", "-"))
            c2.metric("Truth evaluated", last_run.get("n_truth", "-"))
            with st.expander("Screening ledger JSON", expanded=False):
                st.json(last_run.get("ledger", {}))
            st.download_button(
                "Download screening_ledger.json",
                data=json.dumps(last_run.get("ledger", {}), indent=2, sort_keys=True).encode("utf-8"),
                file_name="screening_ledger_v386.json",
                mime="application/json",
                use_container_width=True,
                key="v386_dl_screening_ledger",
            )


    with tabs[2]:

        ex_dir = repo_root / "examples" / "concept_families"
        yaml_files = sorted([p for p in ex_dir.glob("*.y*ml")]) if ex_dir.exists() else []
        if not yaml_files:
            st.warning("No concept family YAMLs found under examples/concept_families.")
            return

        fam_path = st.selectbox("Concept family YAML", options=yaml_files, format_func=lambda p: p.name, index=0)
        evaluator_label = st.text_input("Evaluator label", value="hot_ion_point")

        algo = st.radio("Optimizer", ["NSGA2-lite (multi-objective)", "CMAES-lite (single-score)"], horizontal=True)
        seed = st.number_input("Seed", min_value=0, value=1, step=1)

        out_dir = repo_root / "ui_runs" / "optimizer_suite"
        out_dir.mkdir(parents=True, exist_ok=True)

        if algo.startswith("NSGA2"):
            generations = st.number_input("Generations", min_value=1, value=10, step=1)
            pop = st.number_input("Population", min_value=8, value=40, step=4)
            do_repair = st.toggle("Enable repair kernel", value=True)
            if st.button("Run NSGA2-lite", use_container_width=True):
                from clients.nsga2_lite_client import run_nsga2_lite
                bundle = run_nsga2_lite(Path(fam_path), out_dir, seed=int(seed), generations=int(generations),
                                       pop=int(pop), evaluator_label=str(evaluator_label), do_repair=bool(do_repair))
                st.session_state["optimizer_suite_last_bundle"] = str(bundle)
                st.success("NSGA2-lite run completed.")
        else:
            n_iter = st.number_input("Iterations", min_value=1, value=20, step=1)
            pop = st.number_input("Population", min_value=4, value=16, step=1)
            robust = st.toggle("Robust mode (UQ-lite corners)", value=False)
            if st.button("Run CMAES-lite", use_container_width=True):
                from clients.cmaes_lite_client import run_cmaes_lite
                bundle = run_cmaes_lite(Path(fam_path), out_dir, seed=int(seed), n_iter=int(n_iter), pop=int(pop),
                                        evaluator_label=str(evaluator_label), robust=bool(robust))
                st.session_state["optimizer_suite_last_bundle"] = str(bundle)
                st.success("CMAES-lite run completed.")

        pth = st.session_state.get("optimizer_suite_last_bundle")
        if isinstance(pth, str) and pth:
            p = Path(pth)
            if p.exists():
                st.markdown("### Outputs")
                st.download_button("Download optimizer bundle ZIP", data=p.read_bytes(), file_name=p.name,
                                   mime="application/zip", use_container_width=True)
                tr = out_dir / "optimizer_trace.json"
                if tr.exists():
                    st.download_button("Download optimizer_trace.json", data=tr.read_bytes(), file_name=tr.name,
                                       mime="application/json", use_container_width=True)
