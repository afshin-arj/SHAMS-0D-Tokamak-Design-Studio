from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st

from tools.licensing_pack_v355 import export_licensing_evidence_tier2_zip, validate_licensing_pack_tier2_zip


def _pick_artifact_from_session() -> Optional[Dict[str, Any]]:
    # Prefer canonical "last_run_artifact"; fall back to Point Designer and Systems.
    for k in (
        "last_run_artifact",
        "pd_last_artifact",
        "pd_baseline_artifact",
        "systems_last_solve_artifact",
    ):
        a = st.session_state.get(k)
        if isinstance(a, dict) and a:
            return a
    return None


def render_licensing_evidence_tier2_panel(repo_root: Path) -> None:
    st.subheader("🏛️ Licensing Evidence Tier 2 (v355.0)")
    st.caption(
        "Tier 2 is a governance-strengthened, deterministic ZIP pack (schema v3). "
        "Read-only; does not modify truth. Includes contract registry + authority audit + replay payload."
    )

    art = _pick_artifact_from_session()
    if not isinstance(art, dict) or not art:
        st.warning("No current run artifact found in this session. Run 🧭 Point Designer first or load an artifact.")
        return

    extra: Dict[str, Any] = {}
    # Optional: include v352 certification results if present
    cert = st.session_state.get("v352_last_certification")
    if isinstance(cert, dict) and cert:
        extra["certification"] = cert

    out_dir = repo_root / "ui_runs" / "licensing_evidence_tier2"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_zip = out_dir / "licensing_pack_tier2_v355.zip"

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
            },
            expanded=False,
        )
    with c2:
        st.markdown("### Export (schema v3)")
        if st.button("Generate Tier 2 licensing pack ZIP", use_container_width=True, key="licpack_gen_btn_v355"):
            try:
                export_licensing_evidence_tier2_zip(repo_root, art, out_zip, extra=extra, basename="licensing_pack_tier2")
                st.session_state["licensing_pack_tier2_zip_path"] = str(out_zip)
                st.success("Licensing Tier 2 pack generated (v355.0).")
            except Exception as e:
                st.error(f"Tier 2 pack build failed: {e}")

        p = st.session_state.get("licensing_pack_tier2_zip_path")
        if isinstance(p, str) and p:
            zp = Path(p)
            if zp.exists():
                st.download_button(
                    "Download Tier 2 licensing pack ZIP",
                    data=zp.read_bytes(),
                    file_name=zp.name,
                    mime="application/zip",
                    use_container_width=True,
                    key="licpack_download_btn_v355",
                )
                if st.button("Validate this ZIP", use_container_width=True, key="licpack_validate_btn_v355"):
                    res = validate_licensing_pack_tier2_zip(zp)
                    if res.ok:
                        st.success("Validation OK: required sections + per-file SHA-256 verified.")
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

    with st.expander("What Tier 2 contains (schema v3)", expanded=False):
        st.markdown(
            "- `artifact.json`: full run artifact\n"
            "- `contracts/contracts_index.json`: full contract fingerprint registry (all contracts/*.json)\n"
            "- `governance/authority_audit.json`: authority stack audit snapshot + contract stamp extraction\n"
            "- `replay/replay_payload.json`: intent + inputs payload (if present)\n"
            "- `analysis/regime_transitions.json`: regime transition report (when present)\n"
            "- `certification/robust_envelope_certification.json`: v352 certification (when present)\n"
            "- `repo/*`: README/VERSION/RELEASE_NOTES + manifests (when present)\n"
            "- `PACK_MANIFEST.json`: strict schema v3 pack manifest + per-file SHA-256\n"
        )
