from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st


def _read_json_file(p: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_json_upload(uploaded) -> Optional[Dict[str, Any]]:
    try:
        if uploaded is None:
            return None
        data = uploaded.getvalue()
        if not isinstance(data, (bytes, bytearray)):
            return None
        return json.loads(data.decode("utf-8"))
    except Exception:
        return None


def render_extopt_interpretation(repo_root: Path) -> None:
    """v331.0: External Optimization Interpretation Layer (UI).

    Interpretation-only: consumes optimizer_trace.json and produces
    feasibility attrition tables, dominance histograms, and narratives.
    """

    st.markdown("## 🧪 External Optimization Interpretation")
    st.caption(
        "Interpret external optimizer runs (firewalled). This panel does not run optimization and does not modify truth."
    )

    # Capability registry (metadata only)
    try:
        from src.extopt.interpretation import load_optimizer_registry, interpret_optimizer_trace
    except Exception as e:  # pragma: no cover
        st.error(f"Interpretation layer import failed: {e}")
        return

    reg = {}
    try:
        reg = load_optimizer_registry(repo_root)
    except Exception:
        reg = {}

    with st.expander("📦 Optimizer capability registry (metadata)", expanded=False):
        if reg:
            st.code(json.dumps(reg, sort_keys=True, indent=2), language="json")
        else:
            st.info("No optimizer_capability_registry.json found in this build.")

    # Trace selection
    default_trace_path = repo_root / "ui_runs" / "extopt_workbench" / "optimizer_trace.json"
    src = st.radio(
        "Trace source",
        options=["Use last Workbench trace", "Upload optimizer_trace.json"],
        horizontal=True,
        index=0,
        key="v331_trace_source",
    )

    trace: Optional[Dict[str, Any]] = None
    if src == "Use last Workbench trace":
        if default_trace_path.exists():
            trace = _read_json_file(default_trace_path)
            st.caption(f"Using: {default_trace_path}")
        else:
            st.warning("No previous optimizer_trace.json found. Run External Optimization Workbench or upload a trace.")
    else:
        up = st.file_uploader("Upload optimizer_trace.json", type=["json"], key="v331_trace_upload")
        trace = _read_json_upload(up)

    if not trace:
        st.info("No trace loaded.")
        return

    # Interpret
    try:
        report = interpret_optimizer_trace(trace)
    except Exception as e:
        st.error(f"Interpretation failed: {e}")
        return

    st.markdown("### Narrative")
    st.info(report.get("narrative", "(no narrative)") )

    c1, c2, c3 = st.columns(3)
    c1.metric("Candidates", report.get("n_total", 0))
    c2.metric("Feasible", report.get("n_feasible", 0))
    c3.metric("Infeasible", report.get("n_infeasible", 0))

    # Attrition tables (expandable by default per global rule)
    import pandas as pd

    with st.expander("📉 Attrition by dominant authority", expanded=False):
        d = report.get("attrition_by_dominant_authority", {})
        df = pd.DataFrame([{"authority": k, "count": v} for k, v in d.items()])
        if len(df) == 0:
            st.info("No infeasible points (no attrition).")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            try:
                st.bar_chart(df.set_index("authority"))
            except Exception:
                pass

    with st.expander("🧱 Attrition by limiting constraint", expanded=False):
        d2 = report.get("attrition_by_dominant_constraint", {})
        df2 = pd.DataFrame([{"constraint": k, "count": v} for k, v in d2.items()])
        if len(df2) == 0:
            st.info("No infeasible points (no attrition).")
        else:
            st.dataframe(df2, use_container_width=True, hide_index=True)

    with st.expander("🧾 Interpretation report (JSON)", expanded=False):
        st.code(json.dumps(report, sort_keys=True, indent=2), language="json")

    st.download_button(
        "Download interpretation_report.json",
        data=json.dumps(report, sort_keys=True, indent=2).encode("utf-8"),
        file_name="interpretation_report.json",
        mime="application/json",
        use_container_width=True,
        key="v331_download_report",
    )
