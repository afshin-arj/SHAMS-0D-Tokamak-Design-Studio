"""Compare deck -- extracted from ui/app.py (UI redesign).

Pure move + cosmetic de-emoji (UI redesign). No physics, constraint,
solver, evaluator, session-state key, or routing-ID changes. The block runs
with app.py module globals injected (namespace bridge, including app.py's
__file__ so path computations resolve as before); this bridge is temporary
tech debt to be replaced with explicit imports/ctx in a later cleanup commit.
"""
from __future__ import annotations
import streamlit as st
import sys


from ._bridge import bridge_deck

def render_compare(_app_module) -> None:
    # Namespace bridge: borrow app.py module globals so this extracted block
    # resolves every bare name exactly as it did inline. __file__ is injected
    # so Path(__file__).resolve().parent.parent / .parents[1] still resolve to
    # the SHAMS-0D root (app.py's location), not ui/decks/. Pure move.
    bridge_deck(_app_module, globals())

    st.header("Compare")
    st.caption("Side-by-side artifact comparison to isolate mechanism and constraint-margin deltas.")
    render_mode_scope("compare")
    st.markdown("### Compare sources")
    st.caption("Compare uses either **session slots** (recommended) or uploaded JSON artifacts.")

    _slotA = st.session_state.get("cmp_slot_A")
    _slotB = st.session_state.get("cmp_slot_B")
    _metaA = st.session_state.get("cmp_slot_A_meta") or {}
    _metaB = st.session_state.get("cmp_slot_B_meta") or {}
    _have_slotA = isinstance(_slotA, dict)
    _have_slotB = isinstance(_slotB, dict)

    ca, cb, cc = st.columns([1.2, 1.2, 1.0])
    with ca:
        use_slotA = st.checkbox("Use session Slot A", value=bool(_have_slotA), key="cmp_use_slot_A")
        if _have_slotA:
            st.caption(f"Slot A: {str(_metaA.get('label',''))} | {str(_metaA.get('inputs_hash',''))[:8]}")
        else:
            st.caption("Slot A: (empty)")
    with cb:
        use_slotB = st.checkbox("Use session Slot B", value=bool(_have_slotB), key="cmp_use_slot_B")
        if _have_slotB:
            st.caption(f"Slot B: {str(_metaB.get('label',''))} | {str(_metaB.get('inputs_hash',''))[:8]}")
        else:
            st.caption("Slot B: (empty)")
    with cc:
        if st.button("Clear slots", use_container_width=True, key="cmp_clear_slots"):
            st.session_state.pop("cmp_slot_A", None)
            st.session_state.pop("cmp_slot_B", None)
            st.session_state.pop("cmp_slot_A_meta", None)
            st.session_state.pop("cmp_slot_B_meta", None)
            st.success("Cleared Compare slots.")

    with st.expander("Upload artifacts (optional)", expanded=False):
        colA, colB = st.columns(2)
        with colA:
            upA = st.file_uploader("Artifact A (JSON)", type=["json"], key="cmpA")
            if upA is not None:
                if st.button("Store upload as Slot A", use_container_width=True, key="cmp_store_upload_A"):
                    try:
                        _a = json.loads(upA.getvalue().decode("utf-8"))
                    except Exception:
                        _a = json.loads(upA.getvalue())
                    st.session_state["cmp_slot_A"] = _a
                    st.session_state["cmp_slot_A_meta"] = {"ts_unix": float(time.time()), "inputs_hash": str((_a.get("inputs_hash") or "")), "label": "Uploaded"}
                    st.success("Stored upload into Slot A.")
        with colB:
            upB = st.file_uploader("Artifact B (JSON)", type=["json"], key="cmpB")
            if upB is not None:
                if st.button("Store upload as Slot B", use_container_width=True, key="cmp_store_upload_B"):
                    try:
                        _b = json.loads(upB.getvalue().decode("utf-8"))
                    except Exception:
                        _b = json.loads(upB.getvalue())
                    st.session_state["cmp_slot_B"] = _b
                    st.session_state["cmp_slot_B_meta"] = {"ts_unix": float(time.time()), "inputs_hash": str((_b.get("inputs_hash") or "")), "label": "Uploaded"}
                    st.success("Stored upload into Slot B.")

    def _load_art(uploaded):
        if uploaded is None:
            return None
        try:
            return json.loads(uploaded.getvalue().decode("utf-8"))
        except Exception:
            try:
                return json.loads(uploaded.getvalue())
            except Exception:
                return None

    # Resolve artifacts from preferred sources
    artA = None
    artB = None
    if bool(use_slotA) and _have_slotA:
        artA = _slotA
    else:
        artA = _load_art(st.session_state.get("cmpA"))
    if bool(use_slotB) and _have_slotB:
        artB = _slotB
    else:
        artB = _load_art(st.session_state.get("cmpB"))

    if bool(use_slotA) and (not _have_slotA):
        st.warning("Slot A is selected but empty. Send a run from Point Designer (Export Bay) or upload an artifact.")
    if bool(use_slotB) and (not _have_slotB):
        st.warning("Slot B is selected but empty. Send a run from Point Designer (Export Bay) or upload an artifact.")

    if artA and artB:
        outA = artA.get("outputs", {}) or {}
        outB = artB.get("outputs", {}) or {}
        keys = ["Q", "Pfus_total_MW", "P_e_net_MW", "betaN", "q95", "Bpeak_TF_T", "q_div_MW_m2", "neutron_wall_load_MW_m2", "COE_proxy_USD_per_MWh"]
        rows = []
        for k in keys:
            a = outA.get(k, float("nan"))
            b = outB.get(k, float("nan"))
            try:
                da = float(a); db = float(b)
                d = db - da
            except Exception:
                d = ""
            rows.append({"metric": k, "A": a, "B": b, "B-A": d})
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

        consA = pd.DataFrame(artA.get("constraints", []) or [])
        consB = pd.DataFrame(artB.get("constraints", []) or [])
        st.markdown("### Constraints (worst margins first)")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Artifact A**")
            if len(consA):
                st.dataframe(consA.sort_values("residual", ascending=False).head(20), use_container_width=True)
        with c2:
            st.markdown("**Artifact B**")
            if len(consB):
                st.dataframe(consB.sort_values("residual", ascending=False).head(20), use_container_width=True)

        # simple markdown diff export
        diff_md = ["# SHAMS Artifact Comparison", "", "## Key metrics", ""]
        diff_md.append(df.to_markdown(index=False))
        diff_md.append("")
        diff_md.append("## Worst constraints (A)")
        diff_md.append("")
        if len(consA):
            diff_md.append(consA.sort_values("residual", ascending=False).head(20).to_markdown(index=False))
        diff_md.append("")
        diff_md.append("## Worst constraints (B)")
        diff_md.append("")
        if len(consB):
            diff_md.append(consB.sort_values("residual", ascending=False).head(20).to_markdown(index=False))
        st.download_button("Download comparison (markdown)", data="\n".join(diff_md), file_name="artifact_comparison.md", mime="text/markdown", use_container_width=True)
