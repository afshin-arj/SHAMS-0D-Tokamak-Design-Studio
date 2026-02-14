from __future__ import annotations
from pathlib import Path
import streamlit as st

def render_external_optimizer_suite(repo_root: Path):
    st.markdown("## 📦 External Optimizer Suite")
    st.caption("Reference firewalled optimizers (NSGA2-lite, CMAES-lite) + repair kernel. Produces audit bundles.")

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
