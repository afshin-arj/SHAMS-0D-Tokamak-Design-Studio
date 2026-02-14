"""🧭 External Optimizer Co-Pilot (v342.0 UI).

This panel helps users *run external optimizers safely* by:

- evaluating externally generated candidates in batch (frozen truth),
- exporting deterministic evidence folders (trace + interpretation + dossiers),
- summarizing feasibility attrition via dominance/constraints.

No optimization is performed here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import json


def _load_json(p: Path) -> Dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def render_extopt_copilot(repo_root: Path) -> None:
    try:
        import streamlit as st
        import pandas as pd
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"Streamlit UI dependency missing: {e}")

    from src.extopt.copilot import run_copilot_from_concept_family
    from src.extopt.interpretation import load_optimizer_registry

    st.subheader("🧭 External Optimizer Co-Pilot")
    st.caption(
        "Evaluate external-optimizer candidates with frozen truth, then generate an audit-ready run folder "
        "(trace + interpretation + optional dossiers)."
    )

    reg = load_optimizer_registry(repo_root)
    opts = reg.get("optimizers", {}) if isinstance(reg.get("optimizers"), dict) else {}
    opt_names = sorted(list(opts.keys())) if opts else ["(unknown)"]

    ui_key = "extopt_copilot_v342"
    cols = st.columns(3)
    optimizer_name = cols[0].selectbox(
        "Optimizer profile",
        options=opt_names,
        index=0,
        key=f"{ui_key}_opt",
        help="Metadata only; SHAMS does not run the optimizer internally.",
    )
    evaluator_label = cols[1].selectbox(
        "Evaluator label",
        options=["hot_ion_point"],
        index=0,
        key=f"{ui_key}_evlabel",
    )
    export_packs = cols[2].checkbox(
        "Export candidate dossiers",
        value=True,
        key=f"{ui_key}_packs",
        help="Writes per-candidate evidence pack ZIPs under runs/extopt/<run_id>/evidence_packs/",
    )

    st.markdown("#### 1) Upload candidate set")
    st.caption("Supported: concept family YAML (concept_family.v1)")
    up = st.file_uploader(
        "Upload concept family YAML",
        type=["yml", "yaml"],
        key=f"{ui_key}_family_upl",
    )

    run_id = st.text_input(
        "Run ID (folder name)",
        value="extopt_run",
        key=f"{ui_key}_runid",
        help="Created under runs/extopt/<run_id>. Choose a stable name for audit/replay.",
    )

    cache_dir = repo_root / "runs" / "extopt" / "_cache"
    out_dir = repo_root / "runs" / "extopt" / run_id.strip()

    if st.button("Evaluate candidates (batch)", key=f"{ui_key}_run_btn", use_container_width=True):
        if up is None:
            st.error("Please upload a concept family YAML.")
            st.stop()
        # Persist upload into run folder inputs for audit
        out_dir.mkdir(parents=True, exist_ok=True)
        tmp_in = out_dir / "inputs" / "concept_family.yaml"
        tmp_in.parent.mkdir(parents=True, exist_ok=True)
        tmp_in.write_bytes(up.getvalue())

        with st.spinner("Evaluating candidates with frozen truth..."):
            rr = run_copilot_from_concept_family(
                tmp_in,
                optimizer_name=str(optimizer_name),
                run_dir=out_dir,
                evaluator_label=str(evaluator_label),
                cache_dir=cache_dir,
                export_candidate_packs=bool(export_packs),
            )

        st.success(f"Completed: {rr.n_feasible}/{rr.n_total} feasible. Run folder: {rr.run_dir}")
        st.session_state[f"{ui_key}_last_run_dir"] = str(rr.run_dir)

    st.divider()

    st.markdown("#### 2) Review last run")
    last = st.session_state.get(f"{ui_key}_last_run_dir")
    if last:
        run_dir = Path(str(last))
        st.info(f"Loaded run: {run_dir}")

        trace = _load_json(run_dir / "optimizer_trace.json")
        report = _load_json(run_dir / "interpretation_report.json")
        results = _load_json(run_dir / "eval_results.json")

        with st.expander("Narrative", expanded=True):
            st.markdown(report.get("narrative", "(no narrative)"))

        with st.expander("Attrition by dominant authority", expanded=False):
            da = report.get("attrition_by_dominant_authority", {})
            if isinstance(da, dict) and da:
                df = pd.DataFrame({"authority": list(da.keys()), "count": list(da.values())})
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No attrition table available.")

        with st.expander("Attrition by dominant constraint", expanded=False):
            dc = report.get("attrition_by_dominant_constraint", {})
            if isinstance(dc, dict) and dc:
                df = pd.DataFrame({"constraint": list(dc.keys()), "count": list(dc.values())})
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No constraint table available.")

        with st.expander("Candidate summaries", expanded=False):
            res_list = (results.get("results") if isinstance(results, dict) else None) or []
            if isinstance(res_list, list) and res_list:
                st.dataframe(pd.DataFrame(res_list), use_container_width=True)
            else:
                st.info("No candidate summaries found.")

        # Convenience: download trace/report for external optimizer tooling
        cols2 = st.columns(3)
        cols2[0].download_button(
            "Download optimizer_trace.json",
            data=json.dumps(trace, indent=2, sort_keys=True),
            file_name="optimizer_trace.json",
            mime="application/json",
            use_container_width=True,
        )
        cols2[1].download_button(
            "Download interpretation_report.json",
            data=json.dumps(report, indent=2, sort_keys=True),
            file_name="interpretation_report.json",
            mime="application/json",
            use_container_width=True,
        )
        cols2[2].download_button(
            "Download RUN_MANIFEST_SHA256.json",
            data=(run_dir / "RUN_MANIFEST_SHA256.json").read_text(encoding="utf-8"),
            file_name="RUN_MANIFEST_SHA256.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        st.caption("No run yet. Evaluate a candidate set above.")
