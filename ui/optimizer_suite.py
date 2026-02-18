from __future__ import annotations
from pathlib import Path
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

    tabs = st.tabs(["📦 Orchestrator 2.0 (import & verify)", "🧪 Lite optimizers (reference)"])

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
    with tabs[1]:

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
