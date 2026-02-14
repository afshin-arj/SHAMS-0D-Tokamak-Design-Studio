from __future__ import annotations

from pathlib import Path
import json
import streamlit as st


def render_certified_optimization_orchestrator(repo_root: Path) -> None:
    """UI deck: Certified Optimization Orchestrator 3.0 (v325).

    This deck creates a hash-stable optimizer job, runs an external kit, and
    re-verifies candidates against frozen truth.
    """

    st.markdown("## 🧾 Certified Optimization Orchestrator")
    st.caption(
        "External-only optimization with certificate-carrying verification. "
        "Produces an auditable run directory under runs/orchestrator/."
    )

    from src.extopt.orchestrator import OptimizerJob, run_optimizer_job  # import-guard safe

    # Objective catalog is intentionally small; users can type custom keys.
    default_objs = ["P_e_net_MW", "R0_m", "B_peak_T", "q_div_MW_m2", "f_recirc"]

    c1, c2, c3, c4 = st.columns(4)
    kit = c1.selectbox(
        "Kit",
        options=["NSGA2-lite", "CMAES-lite", "BO-lite"],
        index=0,
        help="Firewalled proposal generator. Truth is re-verified by SHAMS.",
    )
    seed = c2.number_input("Seed", min_value=0, value=1, step=1)
    n = c3.number_input("Budget (n)", min_value=50, value=300, step=50)
    verify_phase = c4.toggle("Verify phase envelope", value=False)
    verify_uq = c4.toggle("Verify UQ contracts", value=False)

    st.markdown("### Objectives")
    objs = st.multiselect("Objective keys", options=default_objs, default=["P_e_net_MW", "B_peak_T"])
    if not objs:
        st.warning("Select at least one objective.")
        return

    senses = {}
    cols = st.columns(len(objs))
    for i, o in enumerate(objs):
        senses[o] = cols[i].selectbox(f"{o} sense", options=["min", "max"], index=0 if o != "P_e_net_MW" else 1)

    st.markdown("### Objective contract")
    cA, cB = st.columns(2)
    robustness_first = cA.toggle("Robustness-first selection", value=True, help="If enabled, feasible designs are ranked primarily by worst hard margin, then objective.")
    ordering = ["worst_hard_margin", "objective"] if robustness_first else ["objective", "worst_hard_margin"]
    scenario_robust = cB.toggle("Scenario robustness", value=False, help="Propagate a scenario-robustness request to the external client (still deterministic).")

    objective_contract = {
        "schema": "objective_contract.v3",
        "objectives": [{"key": str(k), "sense": str(v)} for k, v in senses.items()],
        "selection": {
            "ordering": ordering,
            "scenario_robustness": bool(scenario_robust),
        },
    }

    st.markdown("### Bounds")
    st.caption("Bounds are specified as JSON: { \"var\": [lo, hi], ... }. Variables are PointInputs fields.")
    bounds_text = st.text_area(
        "Bounds JSON",
        value=json.dumps({"R0_m": [2.5, 4.5], "Bt_T": [4.0, 7.0]}, indent=2),
        height=140,
    )

    st.markdown("### Base point inputs")
    st.caption("Seed inputs used as baseline; any keys not listed remain defaulted by PointInputs.")
    base_text = st.text_area(
        "Base inputs JSON",
        value=json.dumps({"R0_m": 3.2, "Bt_T": 5.6, "Ip_MA": 12.0}, indent=2),
        height=140,
    )

    try:
        bounds = json.loads(bounds_text) if bounds_text.strip() else {}
        base_inputs = json.loads(base_text) if base_text.strip() else {}
        if not isinstance(bounds, dict) or not isinstance(base_inputs, dict):
            raise TypeError("bounds/base_inputs must be JSON objects")
    except Exception as e:
        st.error(f"Invalid JSON: {e}")
        return

    verify_request = {"phase_envelope": bool(verify_phase), "uq_contracts": bool(verify_uq)}

    job = OptimizerJob(
        schema_version="optimizer_job.v2",
        kit=str(kit),
        seed=int(seed),
        n=int(n),
        objective_contract=dict(objective_contract),
        objectives=list(objs),
        objective_senses=dict(senses),
        bounds={k: list(v) for k, v in (bounds or {}).items()},
        base_inputs=dict(base_inputs),
        verify_request=dict(verify_request),
    )

    with st.expander("Job preview (hash-stable)", expanded=False):
        st.json({"job_id": job.stable_id(), **job.to_dict()}, expanded=False)

    if st.button("Run + Certify", use_container_width=True):
        try:
            run_dir = run_optimizer_job(repo_root, job)
            st.session_state["last_orchestrator_run_dir"] = str(run_dir)
            st.success(f"Certified optimizer job finished: {run_dir.name}")
        except Exception as e:
            st.error(f"Orchestrator failed: {e}")
            return

    run_dir_s = st.session_state.get("last_orchestrator_run_dir")
    if isinstance(run_dir_s, str) and run_dir_s:
        run_dir = Path(run_dir_s)
        if run_dir.exists():
            st.markdown("### Outputs")
            ccfs = run_dir / "ccfs_verified.json"
            cert = run_dir / "certified_feasible.json"
            dos = run_dir / "optimizer_dossier.json"
            man = run_dir / "manifest.sha256.json"
            cols = st.columns(4)
            if ccfs.exists():
                cols[0].download_button("Download ccfs_verified.json", ccfs.read_bytes(), file_name=ccfs.name, mime="application/json", use_container_width=True)
            if cert.exists():
                cols[1].download_button("Download certified_feasible.json", cert.read_bytes(), file_name=cert.name, mime="application/json", use_container_width=True)
            if man.exists():
                cols[3].download_button("Download manifest.sha256.json", man.read_bytes(), file_name=man.name, mime="application/json", use_container_width=True)
            if dos.exists():
                cols[2].download_button("Download optimizer_dossier.json", dos.read_bytes(), file_name=dos.name, mime="application/json", use_container_width=True)
            if cert.exists():
                try:
                    data = json.loads(cert.read_text(encoding="utf-8"))
                    front = data.get("pareto") or []
                    feas = data.get("feasible") or []
                    st.metric("Verified feasible", len(feas))
                    st.metric("Certified Pareto", len(front))
                    if front:
                        st.dataframe(front, use_container_width=True)
                except Exception:
                    pass
            if dos.exists():
                try:
                    d = json.loads(dos.read_text(encoding="utf-8"))
                    with st.expander("Dossier summary", expanded=False):
                        st.json(d, expanded=False)
                except Exception:
                    pass
