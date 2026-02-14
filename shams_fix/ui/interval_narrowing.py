"""UI panel: Interval Narrowing & Repair Contracts (v343.0).

Read-only / explanatory. Does not modify frozen truth.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _flatten_certified_search_artifact(art: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Extract (variables, records) from certified_search_orchestrator_evidence.v2."""

    variables = []
    try:
        spec = art.get("spec") or {}
        variables = list(spec.get("variables") or [])
    except Exception:
        variables = []

    records: List[Dict[str, Any]] = []
    for stg in (art.get("stages") or []):
        for r in (stg.get("records") or []):
            rr = {
                "x": r.get("x") or {},
                "verdict": r.get("verdict"),
                "score": r.get("score"),
                "evidence": r.get("evidence") or {},
                "stage": stg.get("name"),
            }
            if isinstance(rr["x"], dict):
                records.append(rr)
    return variables, records


def render_interval_narrowing_panel(st, pd, repo_root, session_state: Dict[str, Any]) -> None:
    """Render interval narrowing and repair contract tools."""

    from src.solvers.interval_narrowing import propose_interval_narrowing, build_repair_contract
    from tools.simple_evidence_zip import build_simple_evidence_zip_bytes
    import json
    import pandas as pd

    st.subheader("🛠️ Interval Narrowing & Repair Contracts")
    st.caption(
        "Analyze evaluated candidate sets to flag dead regions and propose advisory interval narrowing. "
        "Exports deterministic governance artifacts (no truth mutation)."
    )

    art = session_state.get("v340_cert_search_last")
    if not isinstance(art, dict) or not str(art.get("schema_version", "")).startswith("certified_search_orchestrator"):
        st.info("Run Certified Search first (Chronicle → Certified Search) so a candidate set exists.")
        return

    variables, records = _flatten_certified_search_artifact(art)
    n_tot = len(records)
    n_pass = sum(1 for r in records if str(r.get("verdict", "")).upper() == "PASS")

    cols = st.columns(3)
    cols[0].metric("Candidates", str(n_tot))
    cols[1].metric("PASS", str(n_pass))
    cols[2].metric("Repairability", "REPAIRABLE" if n_pass > 0 else "STRUCTURALLY INFEASIBLE")

    st.divider()
    st.markdown("#### Narrowing parameters")
    c1, c2, c3, c4 = st.columns(4)
    bins = int(c1.number_input("Bins", value=12, min_value=4, max_value=40, step=1, key="v343_bins"))
    min_bin = int(c2.number_input("Min samples/bin", value=2, min_value=1, max_value=20, step=1, key="v343_minbin"))
    qlo = float(c3.slider("PASS quantile lo", min_value=0.0, max_value=0.45, value=0.05, step=0.05, key="v343_qlo"))
    qhi = float(c4.slider("PASS quantile hi", min_value=0.55, max_value=1.0, value=0.95, step=0.05, key="v343_qhi"))

    if st.button("Analyze candidate set", use_container_width=True, key="v343_run"):
        ev = propose_interval_narrowing(
            variables=variables,
            records=records,
            bins=bins,
            min_samples_per_bin=min_bin,
            pass_quantile_lo=qlo,
            pass_quantile_hi=qhi,
        )
        session_state["v343_interval_narrowing_evidence"] = ev

        # Build a repair contract from declared variable intervals (advisory)
        base_intervals = {}
        for v in variables:
            try:
                name = str(v.get("name"))
                lo = float(v.get("lo"))
                hi = float(v.get("hi"))
                if name and hi > lo:
                    base_intervals[name] = (lo, hi)
            except Exception:
                continue

        rc = build_repair_contract(
            base_intervals,
            allowed_knobs=[str(v.get("name")) for v in variables if v.get("name")],
            max_delta_frac=0.10,
            forbid_relaxation=True,
            notes="Generated from Certified Search knob intervals; advisory only.",
        )
        session_state["v343_repair_contract"] = rc
        st.success("Interval narrowing analysis complete.")

    ev = session_state.get("v343_interval_narrowing_evidence")
    if isinstance(ev, dict) and ev.get("schema_version") == "interval_narrowing_evidence.v1":
        st.markdown("#### Suggestions")
        sugg = ev.get("suggestions") or []
        if sugg:
            df = pd.DataFrame(sugg)
            with st.expander("Narrowing suggestions", expanded=False):
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No narrowing suggestions (likely no PASS points).")

        db = ev.get("dead_bins") or []
        if db:
            with st.expander("Dead bins (no PASS)", expanded=False):
                st.dataframe(pd.DataFrame(db), use_container_width=True, hide_index=True)

        # Evidence pack
        st.markdown("#### Evidence pack")
        if st.button("Build interval_narrowing evidence pack", use_container_width=True, key="v343_build_zip"):
            b = build_simple_evidence_zip_bytes(ev, basename="interval_narrowing")
            session_state["v343_interval_narrowing_zip"] = b
            st.success("Evidence pack built.")
        b = session_state.get("v343_interval_narrowing_zip")
        if isinstance(b, (bytes, bytearray)) and len(b) > 0:
            st.download_button(
                "Download interval_narrowing_evidence.zip",
                data=b,
                file_name="interval_narrowing_evidence.zip",
                mime="application/zip",
                use_container_width=True,
                key="v343_dl_zip",
            )

    rc = session_state.get("v343_repair_contract")
    if isinstance(rc, dict) and rc.get("schema_version") == "repair_contract.v1":
        st.divider()
        st.markdown("#### Repair contract (governance artifact)")
        with st.expander("repair_contract.v1", expanded=False):
            st.json(rc)
        st.download_button(
            "Download repair_contract.json",
            data=json.dumps(rc, indent=2, sort_keys=True),
            file_name="repair_contract.json",
            mime="application/json",
            use_container_width=True,
            key="v343_dl_contract",
        )
