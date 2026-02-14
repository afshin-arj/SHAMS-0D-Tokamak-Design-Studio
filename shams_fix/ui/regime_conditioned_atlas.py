"""UI panel: v365.0 Regime-Conditioned Pareto Atlas 2.0

This is a Pareto Lab deck that consumes previously-evaluated candidate records
and builds regime-conditioned buckets and per-bucket Pareto sets.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import asdict
import io
import json
from pathlib import Path
import time
import zipfile
from typing import Any, Dict, Iterable, List, Mapping, Optional

import streamlit as st
import pandas as pd

from analysis.regime_conditioned_atlas_v365 import AtlasConfig, MetricSpec, build_regime_conditioned_atlas
from ui.icons import label, render_mode_scope


def _read_jsonl_bytes(data: bytes) -> List[Dict[str, Any]]:
    lines = [ln for ln in data.splitlines() if ln.strip()]
    out: List[Dict[str, Any]] = []
    for ln in lines:
        try:
            obj = json.loads(ln.decode("utf-8"))
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    return out


def _load_records_from_upload(upload) -> List[Dict[str, Any]]:
    if upload is None:
        return []
    name = str(getattr(upload, "name", ""))
    raw = upload.read()
    if name.lower().endswith(".jsonl"):
        return _read_jsonl_bytes(raw)
    if name.lower().endswith(".json"):
        try:
            obj = json.loads(raw.decode("utf-8"))
            if isinstance(obj, list):
                return [x for x in obj if isinstance(x, dict)]
            if isinstance(obj, dict) and isinstance(obj.get("records"), list):
                return [x for x in obj["records"] if isinstance(x, dict)]
        except Exception:
            return []
    if name.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
                # common campaign outputs
                for cand in ("results.jsonl", "results.json", "candidates_eval.jsonl"):
                    if cand in zf.namelist():
                        return _read_jsonl_bytes(zf.read(cand))
        except Exception:
            return []
    return []


def _sha256_bytes(b: bytes) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _build_evidence_pack_zip(repo_root: Path, atlas_obj: Mapping[str, Any]) -> bytes:
    """Create a deterministic-ish evidence pack zip in memory."""
    ts = time.strftime("%Y%m%d_%H%M%S")
    base = f"atlas_v365_{ts}"
    files: Dict[str, bytes] = {}

    buckets = pd.DataFrame(atlas_obj.get("buckets", []) or [])
    pareto = pd.DataFrame(atlas_obj.get("pareto_sets", []) or [])

    files[f"{base}/atlas.json"] = json.dumps(atlas_obj, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")
    files[f"{base}/buckets.csv"] = buckets.to_csv(index=False).encode("utf-8")
    files[f"{base}/pareto_sets.csv"] = pareto.to_csv(index=False).encode("utf-8")

    # per-file manifest
    manifest_lines = []
    for path, content in sorted(files.items(), key=lambda kv: kv[0]):
        manifest_lines.append(f"{_sha256_bytes(content)}  {path}")
    files[f"{base}/MANIFEST_SHA256.txt"] = ("\n".join(manifest_lines) + "\n").encode("utf-8")

    # zip
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, content in sorted(files.items(), key=lambda kv: kv[0]):
            zf.writestr(path, content)
    return bio.getvalue()


def render_regime_conditioned_atlas(repo_root: Path) -> None:
    st.subheader("🧭 Regime-Conditioned Pareto Atlas 2.0")
    render_mode_scope("regime_atlas")

    # v366.0: show global fidelity tier (reviewer-facing metadata).
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

    with st.expander(label("info", "Input expectations"), expanded=False):
        st.markdown(
            "Upload candidate evaluation records from SHAMS (recommended: v363 Campaign Pack `results.jsonl`). "
            "The atlas uses any of these fields if present: `plasma_regime`, `exhaust_regime`, `magnet_regime`, "
            "`dominance_label`, `optimistic_feasible`, `robust_feasible`, plus reporting metrics.")

    up = st.file_uploader(
        "Upload candidate records (.jsonl / .json / campaign zip)",
        type=["jsonl", "json", "zip"],
        key="v365_atlas_uploader",
    )
    recs = _load_records_from_upload(up)
    st.caption(f"Loaded records: {len(recs)}")
    if not recs:
        st.info("Upload a records file to build an atlas.")
        return

    # Controls
    with st.container(border=True):
        st.markdown("**Conditioning axes**")
        c1, c2, c3, c4, c5 = st.columns(5)
        ax_plasma = c1.checkbox("plasma_regime", value=True, key="v365_ax_plasma")
        ax_exhaust = c2.checkbox("exhaust_regime", value=True, key="v365_ax_exhaust")
        ax_magnet = c3.checkbox("magnet_regime", value=False, key="v365_ax_magnet")
        ax_dom = c4.checkbox("dominance_label", value=True, key="v365_ax_dom")
        ax_rob = c5.checkbox("robustness_class", value=True, key="v365_ax_rob")

        axes: List[str] = []
        if ax_plasma:
            axes.append("plasma_regime")
        if ax_exhaust:
            axes.append("exhaust_regime")
        if ax_magnet:
            axes.append("magnet_regime")
        if ax_dom:
            axes.append("dominance_label")
        if ax_rob:
            axes.append("robustness_class")

        min_bucket = st.number_input("Min bucket size", min_value=1, value=8, step=1, key="v365_min_bucket")
        gate = st.selectbox(
            "Feasibility gate", 
            options=["any_feasible", "optimistic", "robust", "robust_only"],
            index=3,
            help="Which feasibility class to treat as admissible for Pareto extraction.",
            key="v365_gate",
        )

        st.markdown("**Pareto metrics**")
        default_metric_keys = [
            ("P_e_net_MW", "max"),
            ("f_recirc", "min"),
            ("CoE_USD_MWh", "min"),
        ]
        mcols = st.columns(3)
        m1 = mcols[0].text_input("Metric 1 key", value=default_metric_keys[0][0], key="v365_m1")
        d1 = mcols[0].selectbox("dir", options=["max", "min"], index=0, key="v365_d1")
        m2 = mcols[1].text_input("Metric 2 key", value=default_metric_keys[1][0], key="v365_m2")
        d2 = mcols[1].selectbox("dir", options=["max", "min"], index=1, key="v365_d2")
        m3 = mcols[2].text_input("Metric 3 key", value=default_metric_keys[2][0], key="v365_m3")
        d3 = mcols[2].selectbox("dir", options=["max", "min"], index=1, key="v365_d3")

    cfg = AtlasConfig(
        conditioning_axes=tuple(axes) if axes else ("dominance_label",),
        min_bucket_size=int(min_bucket),
        feasibility_gate=str(gate),
        metrics=(MetricSpec(m1, d1), MetricSpec(m2, d2), MetricSpec(m3, d3)),
    )

    if st.button("Build Atlas", type="primary", key="v365_build_atlas"):
        atlas = build_regime_conditioned_atlas(recs, cfg)
        st.session_state["v365_atlas_last"] = atlas
        st.success("Atlas built.")

    atlas = st.session_state.get("v365_atlas_last")
    if not atlas:
        return

    # Views
    bdf = pd.DataFrame(atlas.get("buckets", []) or [])
    pdf = pd.DataFrame(atlas.get("pareto_sets", []) or [])

    with st.expander("Buckets", expanded=False):
        st.dataframe(bdf, use_container_width=True)

    with st.expander("Pareto sets (per bucket)", expanded=False):
        st.dataframe(pdf, use_container_width=True)

    with st.expander("Atlas JSON (audit)", expanded=False):
        st.json({k: atlas.get(k) for k in ["schema", "config", "fingerprint_sha256"]}, expanded=False)

    # Export evidence pack
    pack = _build_evidence_pack_zip(repo_root, atlas)
    st.download_button(
        "Export Atlas Evidence Pack (ZIP)",
        data=pack,
        file_name="SHAMS_AtlasEvidencePack_v365.zip",
        mime="application/zip",
        use_container_width=True,
    )
