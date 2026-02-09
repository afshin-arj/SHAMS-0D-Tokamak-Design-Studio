from __future__ import annotations
import json
from pathlib import Path
import streamlit as st

try:
    from ui.handoff import maybe_add_dsg_node_id_column
except Exception:  # pragma: no cover
    maybe_add_dsg_node_id_column = None


def render_extopt_workbench(repo_root: Path):
    st.markdown("## 📈 External Optimization Workbench")
    st.caption("Firewalled reference optimizer client + audit-grade handoff bundle (problem spec, runspec, trace).")

    ex_dir = repo_root / "examples" / "concept_families"
    yaml_files = sorted([p for p in ex_dir.glob("*.y*ml")]) if ex_dir.exists() else []
    if not yaml_files:
        st.warning("No concept family YAMLs found under examples/concept_families.")
        return

    fam_path = st.selectbox("Concept family YAML", options=yaml_files, format_func=lambda p: p.name, index=0)
    seed = st.number_input("Seed", min_value=0, value=1, step=1)
    nprop = st.number_input("Proposals", min_value=4, value=64, step=4)
    robust = st.toggle("Robust mode (UQ-lite corners, worst-case margins)", value=False)
    evaluator_label = st.text_input("Evaluator label", value="hot_ion_point")

    st.markdown("### Problem spec (JSON)")
    st.caption("This is passed to external optimizers. It does not change truth.")
    default_ps = None
    try:
        from clients.reference_optimizer import build_default_problem_spec
        default_ps = build_default_problem_spec(name=str(Path(fam_path).stem))
    except Exception:
        default_ps = {"schema_version": "extopt.problem_spec.v1", "name": "default", "variables": [], "objectives": [], "constraints": []}
    ps_text = st.text_area("problem_spec.json", value=json.dumps(default_ps, sort_keys=True, indent=2), height=240)

    out_dir = repo_root / "ui_runs" / "extopt_workbench"
    out_dir.mkdir(parents=True, exist_ok=True)

    if st.button("Run reference optimizer (firewalled)", use_container_width=True):
        try:
            ps = json.loads(ps_text)
        except Exception as e:
            st.error(f"Invalid JSON in problem spec: {e}")
            return

        # Run in-process (still firewalled: no truth changes; uses ExtOpt evaluate_concept_family)
        from clients.reference_optimizer import run_reference_optimizer
        bundle = run_reference_optimizer(
            family_yaml=Path(fam_path),
            out_dir=out_dir,
            seed=int(seed),
            n_proposals=int(nprop),
            evaluator_label=str(evaluator_label),
            robust=bool(robust),
        )
        st.success("Run completed.")
        st.session_state["extopt_workbench_last_bundle"] = str(bundle)

    pth = st.session_state.get("extopt_workbench_last_bundle")
    if isinstance(pth, str) and pth:
        p = Path(pth)
        if p.exists():
            st.markdown("### Outputs")
            st.download_button(
                "Download optimizer bundle ZIP",
                data=p.read_bytes(),
                file_name=p.name,
                mime="application/zip",
                use_container_width=True,
            )
            tr = out_dir / "optimizer_trace.json"
            if tr.exists():
                st.download_button(
                    "Download optimizer_trace.json",
                    data=tr.read_bytes(),
                    file_name=tr.name,
                    mime="application/json",
                    use_container_width=True,
                )


    # v327.5: pipeline-native DSG subset linking (best-effort)
    try:
        from ui.handoff import render_subset_linker_best_effort  # type: ignore
        _df_for_link = locals().get("df_show") or locals().get("df") or locals().get("df_props") or locals().get("df_candidates")
        if _df_for_link is not None:
            render_subset_linker_best_effort(df=_df_for_link, label="ExtOpt", kind="extopt_select", note="Selection from ExtOpt table")
    except Exception:
        pass
