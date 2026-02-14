from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

import streamlit as st


def _safe_hash(obj: Any) -> str:
    """Best-effort stable hash string for UI provenance (non-authoritative)."""
    try:
        import json
        import hashlib
        s = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(s).hexdigest()[:12]
    except Exception:
        return ""


def _summarize_point_inputs(pi: Any) -> Dict[str, Any]:
    if pi is None:
        return {}
    if isinstance(pi, dict):
        d = dict(pi)
    else:
        try:
            d = asdict(pi)  # dataclass
        except Exception:
            d = dict(getattr(pi, "__dict__", {}) or {})
    # Keep the trace compact.
    keep = [
        "R0_m",
        "a_m",
        "kappa",
        "delta",
        "Bt_T",
        "Ip_MA",
        "f_GW",
        "P_aux_MW",
        "q95",
    ]
    out: Dict[str, Any] = {}
    for k in keep:
        if k in d:
            out[k] = d.get(k)
    out["_hash"] = _safe_hash(d)
    return out


def _summarize_last_outputs(po: Any) -> Dict[str, Any]:
    if po is None:
        return {}
    if isinstance(po, dict):
        d = dict(po)
    else:
        d = dict(getattr(po, "__dict__", {}) or {})
    keep = [
        "verdict",
        "dominant_mechanism",
        "Q_DT_eqv",
        "P_net_e_MW",
        "H98",
        "betaN",
        "q95",
    ]
    out: Dict[str, Any] = {k: d.get(k) for k in keep if k in d}
    out["_hash"] = _safe_hash(d)
    return out


def render_workflow_trace(expanded: bool = False) -> None:
    """Global, read-only provenance card for cross-panel workflow coherence."""

    with st.expander("🧾 Workflow Trace & Provenance", expanded=expanded):
        # Active point inputs
        last_inp = st.session_state.get("last_point_inp")
        cand = st.session_state.get("pd_candidate_apply")
        promo = st.session_state.get("last_promotion_event")

        st.markdown("#### Active Point")
        if last_inp is None:
            st.info("No active point in workspace yet.")
        else:
            st.dataframe([_summarize_point_inputs(last_inp)], use_container_width=True)

        if isinstance(promo, dict) and promo:
            st.markdown("#### Last Promotion Event")
            st.dataframe([{
                "source": promo.get("source", ""),
                "note": promo.get("note", ""),
                "ts": promo.get("ts", ""),
            }], use_container_width=True)
        elif cand is not None:
            st.caption("A candidate is staged for Point Designer (pending apply).")

        # Last truth evaluation
        st.markdown("#### Last Truth Evaluation")
        last_out = st.session_state.get("last_point_out")
        if last_out is None:
            st.info("No truth evaluation recorded yet (run 🧭 Point Designer).")
        else:
            st.dataframe([_summarize_last_outputs(last_out)], use_container_width=True)

        # Study capsule
        st.markdown("#### Active Study Capsule")
        cap = st.session_state.get("active_study_capsule")
        if isinstance(cap, dict) and cap:
            st.dataframe([{
                "schema": cap.get("schema", ""),
                "id": cap.get("id", ""),
                "lane": cap.get("lane", ""),
                "knob_set": cap.get("knob_set", cap.get("knobs", "")),
            }], use_container_width=True)
        else:
            st.info("No active study capsule.")

        # External optimizer context
        st.markdown("#### External Optimizer Context")
        ext = st.session_state.get("active_extopt_run")
        if isinstance(ext, dict) and ext:
            st.dataframe([{
                "kit": ext.get("kit", ""),
                "run_id": ext.get("run_id", ""),
                "cfg": ext.get("config", ""),
                "status": ext.get("status", ""),
                "ts": ext.get("ts", ""),
            }], use_container_width=True)
        else:
            # Show live kit process if present (Trade Study Studio)
            proc = st.session_state.get("ts_kit_proc")
            if proc is not None:
                st.info("Optimizer kit process is running (see Trade Study Studio log).")
            else:
                st.info("No active external optimizer run.")
