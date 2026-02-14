from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st

from tools.regulatory_pack import (
    export_regulatory_evidence_pack_zip,
    validate_regulatory_pack_zip,
)


def _pick_artifact_from_session() -> Optional[Dict[str, Any]]:
    # Prefer canonical "last_run_artifact"; fall back to Point Designer last.
    for k in ("last_run_artifact", "pd_last_artifact", "pd_baseline_artifact", "systems_last_solve_artifact"):
        a = st.session_state.get(k)
        if isinstance(a, dict) and a:
            return a
    return None


def render_regulatory_evidence_pack_panel(repo_root: Path) -> None:
    st.subheader("🧾 Regulatory & Reviewer Evidence Packs (v334.0)")
    st.caption(
        "Licensing-grade deterministic ZIP exports with schema v2 + pack validator + PDF summary report. "
        "Read-only; does not affect truth."
    )

    art = _pick_artifact_from_session()
    if not isinstance(art, dict) or not art:
        st.warning("No current run artifact found in this session. Run 🧭 Point Designer first or load an artifact.")
        return

    # Optional extras if available
    extra: Dict[str, Any] = {}

    # Design family context (from v332): store most recent family selection if present
    fam = st.session_state.get("design_family_last_archetype")
    if isinstance(fam, dict) and fam:
        extra["design_family"] = fam

    # ExtOpt interpretation (from v331) if present
    interp = st.session_state.get("extopt_interpretation_last")
    if isinstance(interp, dict) and interp:
        extra["extopt_interpretation"] = interp

    out_dir = repo_root / "ui_runs" / "regulatory_evidence_pack"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_zip = out_dir / "reviewer_pack_v334.zip"

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Snapshot")
        st.json(
            {
                "shams_version": art.get("shams_version"),
                "intent": art.get("intent"),
                "verdict": art.get("verdict"),
                "dominant_mechanism": art.get("dominant_mechanism") or art.get("dominant_authority"),
                "magnet_regime": art.get("magnet_regime"),
                "exhaust_regime": art.get("exhaust_regime"),
            }
        )
    with c2:
        st.markdown("### Export (schema v2)")
        if st.button("Generate reviewer pack ZIP", use_container_width=True, key="regpack_gen_btn_v334"):
            try:
                export_regulatory_evidence_pack_zip(repo_root, art, out_zip, extra=extra, basename="reviewer_pack")
                st.session_state["regulatory_pack_zip_path"] = str(out_zip)
                st.success("Reviewer pack generated (v334.0).")
            except Exception as e:
                st.error(f"Reviewer pack build failed: {e}")

        p = st.session_state.get("regulatory_pack_zip_path")
        if isinstance(p, str) and p:
            zp = Path(p)
            if zp.exists():
                st.download_button(
                    "Download reviewer pack ZIP",
                    data=zp.read_bytes(),
                    file_name=zp.name,
                    mime="application/zip",
                    use_container_width=True,
                    key="regpack_download_btn_v334",
                )
                if st.button("Validate this ZIP", use_container_width=True, key="regpack_validate_btn_v334"):
                    res = validate_regulatory_pack_zip(zp)
                    if res.ok:
                        st.success("Validation OK: hashes + required sections present.")
                    else:
                        st.error("Validation FAILED.")
                    if res.warnings:
                        with st.expander("Warnings", expanded=False):
                            for w in res.warnings:
                                st.warning(w)
                    if res.errors:
                        with st.expander("Errors", expanded=False):
                            for e in res.errors:
                                st.error(e)

    with st.expander("What this pack contains (v334.0 schema v2)", expanded=False):
        st.markdown(
            "- `artifact.json`: full run artifact\n"
            "- `dominance.json`: authority dominance snapshot\n"
            "- `assumptions.json`: scope + contract hashes\n"
            "- `narrative.md`: deterministic narrative header\n"
            "- `tables/constraints_all.csv`: full constraints table (if present)\n"
            "- `tables/constraints_top.csv`: top limiting constraints (if present)\n"
            "- `report/reviewer_summary.pdf`: deterministic PDF summary (if reportlab available)\n"
            "- `contracts/*.json`: copied contracts used (when present)\n"
            "- `PACK_MANIFEST.json`: strict schema v2 pack manifest + per-file SHA-256\n"
        )
