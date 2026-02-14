from __future__ import annotations

"""Streamlit UI client for PROCESS Benchmark & Parity Harness 3.0 (v364.0).

This tool is an overlay: it runs deterministic benchmark suites and generates
reviewer-grade artifacts. It does not modify physics truth.

© 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import io
import json
import zipfile

import pandas as pd
import streamlit as st

from src.parity_harness.case_io import list_case_paths, load_case
from src.parity_harness.runner import run_benchmark_suite


def render_benchmark_parity_harness_v364(*, default_suite: str = "v364") -> None:
    st.subheader("🆚 Benchmark & Parity Harness 3.0")
    st.caption(
        "Reviewer-grade parity plumbing: run synthetic benchmark cases through SHAMS, "
        "optionally compare against user-provided PROCESS outputs, and export delta dossiers. "
        "SHAMS truth remains frozen."
    )

    # v366.0: fidelity tier stamp (global registry baseline).
    try:
        from src.provenance.authority import authority_snapshot_from_outputs
        from src.provenance.fidelity_tiers import global_fidelity_from_registry
    except Exception:
        from provenance.authority import authority_snapshot_from_outputs  # type: ignore
        from provenance.fidelity_tiers import global_fidelity_from_registry  # type: ignore
    try:
        _fl = global_fidelity_from_registry(authority_snapshot_from_outputs({}))
        if _fl:
            st.markdown(f"**Fidelity tier:** `{_fl}`")
    except Exception:
        pass

    c1, c2, c3 = st.columns([1.2, 1.2, 1.6])
    with c1:
        suite = st.text_input("Suite", value=str(default_suite), key="bench_suite_v364")
    with c2:
        preset = st.selectbox("Profile contracts preset", ["C8", "C16", "C32"], index=0, key="bench_pc_preset_v364")
    with c3:
        tier = st.selectbox("Profile contracts tier", ["optimistic", "robust", "both"], index=2, key="bench_pc_tier_v364")

    st.markdown("#### Case Library")
    cases_dir = Path("benchmarks/cases")
    paths = list_case_paths(cases_dir, suite=str(suite))
    if not paths:
        st.warning(f"No cases found under {cases_dir} for suite '{suite}'.")
        return

    case_ids = [p.stem.replace(f"{suite}_", "") for p in paths]
    sel = st.selectbox("Select case", case_ids, index=0, key="bench_case_sel_v364")
    case_path = cases_dir / f"{suite}_{sel}.json"
    case = load_case(case_path)
    with st.expander("Case JSON", expanded=False):
        st.code(json.dumps(case.raw, indent=2, sort_keys=True), language="json")

    st.markdown("#### Optional PROCESS outputs")
    st.caption("Upload a PROCESS output JSON (your format) to generate delta dossiers. SHAMS will store it only in-session.")
    up = st.file_uploader("PROCESS outputs JSON", type=["json"], key="bench_process_upload_v364")
    process_blob: Optional[Dict[str, Any]] = None
    if up is not None:
        try:
            process_blob = json.loads(up.read().decode("utf-8"))
            st.success("Loaded PROCESS outputs JSON (session-only).")
        except Exception as ex:
            st.error(f"Failed to parse JSON: {ex}")
            process_blob = None

    run_btn = st.button("Run selected case", type="primary", key="bench_run_one_v364")
    run_all_btn = st.button("Run full suite", key="bench_run_all_v364")

    if not (run_btn or run_all_btn):
        return

    # Run deterministically.
    selected_paths: List[Path] = paths if run_all_btn else [case_path]
    rep = run_benchmark_suite(
        suite=str(suite),
        case_paths=selected_paths,
        profile_contracts_preset=str(preset),
        profile_contracts_tier=str(tier),
        process_outputs_by_case={sel: process_blob} if (process_blob and not run_all_btn) else {},
    )

    st.success(f"Completed: {rep['n_cases']} case(s)")

    # Summary table
    rows = rep.get("summary_rows", [])
    df = pd.DataFrame(rows)
    with st.expander("Summary", expanded=False):
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Per-case artifacts
    with st.expander("Artifacts (JSON)", expanded=False):
        st.json(rep.get("cases", {}), expanded=False)

    # Export bundle
    zbytes = _pack_zip(rep)
    st.download_button(
        "Export reviewer pack ZIP",
        data=zbytes,
        file_name=f"SHAMS_ParityHarness_{suite}_v364.zip",
        mime="application/zip",
        key="bench_export_zip_v364",
    )


def _pack_zip(rep: Dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("README_REVIEWER_PACK.txt", _readme_text())
        z.writestr("parity_report.json", json.dumps(rep, indent=2, sort_keys=True))
        cases = rep.get("cases", {}) if isinstance(rep.get("cases"), dict) else {}
        for cid, blob in cases.items():
            z.writestr(f"cases/{cid}/shams_artifact.json", json.dumps(blob.get("shams_artifact", {}), indent=2, sort_keys=True))
            z.writestr(f"cases/{cid}/process_map.json", json.dumps(blob.get("process_map", {}), indent=2, sort_keys=True))
            z.writestr(f"cases/{cid}/delta_dossier.json", json.dumps(blob.get("delta_dossier", {}), indent=2, sort_keys=True))
            md = blob.get("delta_dossier_md", "")
            if isinstance(md, str) and md.strip():
                z.writestr(f"cases/{cid}/delta_dossier.md", md)
    return buf.getvalue()


def _readme_text() -> str:
    return (
        "SHAMS — PROCESS Benchmark & Parity Harness 3.0 (v364)\n"
        "\n"
        "This ZIP is a reviewer pack generated by SHAMS. It contains:\n"
        "- SHAMS run artifacts for each benchmark case\n"
        "- PROCESS↔SHAMS intent mapping artifacts (assumption registry)\n"
        "- Delta dossiers (if PROCESS outputs were supplied)\n"
        "\n"
        "Notes:\n"
        "- SHAMS truth is frozen and deterministic.\n"
        "- Benchmark cases under benchmarks/cases are synthetic templates unless noted otherwise.\n"
    )
