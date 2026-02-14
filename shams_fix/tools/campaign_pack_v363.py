from __future__ import annotations

"""Campaign Pack UI panel (v363.0).

This panel produces deterministic campaign exports for external optimizers and
supports deterministic local batch evaluation.

© 2026 Afshin Arjhangmehr
"""

from pathlib import Path
from typing import Any, Dict, Optional
import json
import tempfile

import streamlit as st


def _default_campaign_template(point_inputs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    # Keep minimal and deterministic. Users may edit bounds and variable list.
    base = dict(point_inputs or {})
    # Heuristic: suggest a few common knobs if present
    suggested = []
    for k in [
        "R0_m",
        "a_m",
        "B0_T",
        "Ip_MA",
        "P_aux_MW",
        "kappa",
        "delta",
    ]:
        if k in base:
            suggested.append(k)
    if not suggested:
        # fallback: first numeric-ish keys
        for k, v in base.items():
            if isinstance(v, (int, float)):
                suggested.append(k)
            if len(suggested) >= 5:
                break

    variables = []
    for k in suggested:
        v = base.get(k)
        try:
            fv = float(v)
        except Exception:
            continue
        # conservative default: ±15% around nominal, clamped away from zero
        span = 0.15 * (abs(fv) if abs(fv) > 1e-12 else 1.0)
        variables.append({"name": k, "kind": "float", "lo": fv - span, "hi": fv + span})

    return {
        "schema": "shams_campaign.v1",
        "name": "campaign_v363",
        "intent": "concept",
        "evaluator_label": "hot_ion_point",
        "variables": variables,
        "fixed_inputs": {},
        "generator": {"mode": "sobol", "n": 64, "seed": 123},
        "profile_contracts": {"tier": "both", "preset": "C16"},
        "include_full_artifact": False,
    }


def render_campaign_pack_panel(*, repo_root: Path, point_inputs: Optional[Dict[str, Any]] = None) -> None:
    """Render Campaign Pack panel.

    Parameters
    ----------
    repo_root:
        Repo root for consistent temp exports.
    point_inputs:
        Optional latest point inputs used to seed a template.
    """
    st.caption("External optimizers propose candidate inputs; SHAMS evaluates deterministically and returns evidence.")

    # v366.0: show global fidelity tier (reviewer-facing metadata).
    try:
        from src.provenance.authority import authority_snapshot_from_outputs
        from src.provenance.fidelity_tiers import global_fidelity_from_registry
    except Exception:
        from provenance.authority import authority_snapshot_from_outputs  # type: ignore
        from provenance.fidelity_tiers import global_fidelity_from_registry  # type: ignore
    try:
        _auth = authority_snapshot_from_outputs({})
        _fl = global_fidelity_from_registry(_auth)
        if _fl:
            st.markdown(f"**Fidelity tier:** `{_fl}`")
    except Exception:
        pass

    try:
        from src.campaign.spec import CampaignSpec, validate_campaign_spec
        from src.campaign.generate import generate_candidates
        from src.campaign.export import export_campaign_bundle
        from src.campaign.eval import evaluate_campaign_candidates
    except Exception:
        from campaign.spec import CampaignSpec, validate_campaign_spec  # type: ignore
        from campaign.generate import generate_candidates  # type: ignore
        from campaign.export import export_campaign_bundle  # type: ignore
        from campaign.eval import evaluate_campaign_candidates  # type: ignore

    tmpl = _default_campaign_template(point_inputs)

    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("**Campaign spec (JSON)**")
        spec_text = st.text_area(
            "Edit campaign JSON",
            value=json.dumps(tmpl, indent=2, sort_keys=True),
            height=320,
            key="campaign_spec_json_v363",
            label_visibility="collapsed",
        )
    with c2:
        st.markdown("**Actions**")
        gen_preview = st.button("Generate candidates", key="campaign_gen_v363")
        export_btn = st.button("Export Campaign ZIP", key="campaign_export_v363")
        run_local_btn = st.button("Run batch locally", key="campaign_run_local_v363")

    # Parse and validate
    spec_obj: Optional[CampaignSpec] = None
    err = None
    try:
        d = json.loads(spec_text)
        spec_obj = CampaignSpec.from_dict(d)
        validate_campaign_spec(spec_obj)
    except Exception as e:
        err = str(e)

    if err:
        st.error(f"Campaign spec invalid: {err}")
        return

    assert spec_obj is not None

    if gen_preview:
        cands = generate_candidates(spec_obj)
        st.session_state["campaign_candidates_v363"] = cands

    cands = st.session_state.get("campaign_candidates_v363", None)
    if isinstance(cands, list):
        with st.expander("Candidates preview (expandable)", expanded=False):
            try:
                st.dataframe(cands[: min(len(cands), 200)], use_container_width=True)
            except Exception:
                st.json(cands[: min(len(cands), 50)], expanded=False)

    if export_btn:
        td = Path(tempfile.gettempdir()) / "shams_campaigns"
        td.mkdir(parents=True, exist_ok=True)
        out_zip = td / f"{spec_obj.name}_campaign_bundle_v363.zip"
        export_campaign_bundle(spec_obj, repo_root=repo_root, out_zip=out_zip)
        st.success(f"Campaign bundle exported: {out_zip.name}")
        st.download_button(
            "Download Campaign ZIP",
            data=out_zip.read_bytes(),
            file_name=out_zip.name,
            mime="application/zip",
            key="campaign_dl_zip_v363",
        )

    if run_local_btn:
        # If no candidates cached, generate now.
        if not isinstance(cands, list):
            cands = generate_candidates(spec_obj)
        td = Path(tempfile.gettempdir()) / "shams_campaigns"
        td.mkdir(parents=True, exist_ok=True)
        out_jsonl = td / f"{spec_obj.name}_results_v363.jsonl"
        summary, rows = evaluate_campaign_candidates(spec_obj, candidates=cands, out_jsonl=out_jsonl)

        k1, k2, k3 = st.columns(3)
        k1.metric("N", str(summary.get("n_total", "-")))
        k2.metric("Feasible", str(summary.get("n_feasible", "-")))
        try:
            k3.metric("Pass rate", f"{100.0*float(summary.get('pass_rate',0.0)):.1f}%")
        except Exception:
            k3.metric("Pass rate", "-")

        with st.expander("Summary JSON", expanded=False):
            st.json(summary, expanded=False)

        with st.expander("Results preview (expandable)", expanded=False):
            try:
                st.dataframe(rows[: min(len(rows), 200)], use_container_width=True)
            except Exception:
                st.json(rows[: min(len(rows), 50)], expanded=False)

        st.download_button(
            "Download results.jsonl",
            data=out_jsonl.read_bytes(),
            file_name=out_jsonl.name,
            mime="application/json",
            key="campaign_dl_jsonl_v363",
        )
