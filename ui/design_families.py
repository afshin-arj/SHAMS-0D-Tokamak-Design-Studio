"""SHAMS v332.0 — Design Family Narratives (UI).

Deterministic, audit-ready clustering of evaluated designs into interpretable
"design families".

Interpretation-only:
  - does not modify frozen truth
  - consumes previously evaluated records
  - no solvers, no ML
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import streamlit as st


def _canon_family_narrative(fk: Mapping[str, str]) -> str:
    """Deterministic narrative text assembled from family key."""
    intent = fk.get("intent", "(no-intent)")
    mag = fk.get("magnet_regime", "(unknown)")
    exh = fk.get("exhaust_regime", "(unknown)")
    dom = fk.get("dominant_authority", "(unknown)")
    domc = fk.get("dominant_constraint", "(unknown)")
    R0c = fk.get("R0_class", "(unknown)")
    B0c = fk.get("B0_class", "(unknown)")
    Ac = fk.get("A_class", "(unknown)")

    lines = [
        f"**Intent:** {intent}",
        f"**Magnet regime:** {mag}",
        f"**Exhaust regime:** {exh}",
        f"**Dominant killer:** {dom} (constraint: {domc})",
        f"**Geometry class:** R0={R0c}, B0={B0c}, A={Ac}",
        "",
        "**Interpretation:** This family groups designs that share the same declared magnet technology regime, exhaust regime label, and dominant feasibility killer, with coarse geometric bucketing for interpretability. It is not an optimizer result; it is a governance-level narrative over evaluated points.",
    ]
    return "\n".join(lines)


def render_design_families(repo_root: Path) -> None:
    """Render the v332.0 Design Family Narratives deck."""

    st.subheader("🧬 Design Family Narratives")
    st.caption(
        "Clusters evaluated designs into interpretable families (deterministic; no ML). "
        "Families are defined by authority/regime labels and coarse geometry buckets."
    )

    with st.expander("🧭 What this does / does not do", expanded=False):
        st.markdown(
            """
**What this does**
- Groups already-evaluated designs into stable, interpretable **families**.
- Produces a deterministic **archetype** (representative design) per family.
- Generates reviewer-ready narratives **from labels and margins**, not from optimization.

**What this does not do**
- Does **not** run optimization or search.
- Does **not** modify the frozen evaluator.
- Does **not** use ML clustering or stochastic methods.
"""
        )

    pareto_last = st.session_state.get("pareto_last")
    if not isinstance(pareto_last, dict):
        st.info("No Pareto Lab run found in this session. Run Pareto Lab first to populate evaluated points.")
        return

    src_choice = st.radio(
        "Source points",
        options=["Pareto points", "All feasible points"],
        horizontal=True,
        index=0,
        help="Families can be built from the non-dominated set (Pareto) or the full feasible set.",
        key="design_family_source_v332",
    )

    recs: List[Mapping[str, Any]] = []
    if src_choice == "Pareto points":
        recs = pareto_last.get("pareto") or []
    else:
        recs = pareto_last.get("feasible") or []

    if not isinstance(recs, list) or len(recs) == 0:
        st.warning("No records available for the selected source.")
        return

    # Build families
    try:
        from src.narratives.design_families import FamilyConfig, build_design_families
    except Exception as e:
        st.error(f"Design families module import failed: {e}")
        return

    cfg = FamilyConfig()
    fams = build_design_families(recs, cfg=cfg)

    max_show = st.number_input(
        "Max families to show",
        min_value=5,
        max_value=200,
        value=min(cfg.max_families_default, max(len(fams), 1)),
        step=5,
        help="UI limit only; does not change family construction.",
        key="design_family_max_show_v332",
    )

    fams_show = fams[: int(max_show)]

    # Summary table
    import pandas as pd

    rows: List[Dict[str, Any]] = []
    for f in fams_show:
        k = f.key
        rows.append(
            {
                "family_id": f.family_id,
                "n": f.n,
                "intent": k.get("intent"),
                "magnet_regime": k.get("magnet_regime"),
                "exhaust_regime": k.get("exhaust_regime"),
                "dominant_authority": k.get("dominant_authority"),
                "R0_class": k.get("R0_class"),
                "B0_class": k.get("B0_class"),
                "A_class": k.get("A_class"),
                "min_margin_p50": f.summaries.get("min_margin_p50"),
                "min_margin_min": f.summaries.get("min_margin_min"),
            }
        )

    df = pd.DataFrame(rows)

    with st.expander("Families (summary table)", expanded=False):
        st.dataframe(df, use_container_width=True)
        st.caption("Tip: Choose a family below to view its archetype and member distribution.")

    # Select family
    fam_ids = [f.family_id for f in fams_show]
    sel = st.selectbox("Select a family", options=fam_ids, index=0, key="design_family_select_v332")
    fam = next((f for f in fams_show if f.family_id == sel), None)
    if fam is None:
        st.warning("Selected family not found.")
        return

    st.markdown("### Family narrative")
    st.markdown(_canon_family_narrative(fam.key))

    # Archetype
    st.markdown("### Archetype (deterministic representative)")
    arch = fam.archetype

    # Render a compact table of key fields if present
    key_fields = [
        "eval_hash",
        "intent",
        "magnet_regime",
        "exhaust_regime",
        "dominant_authority",
        "dominant_constraint_id",
        "R0_m",
        "B0_T",
        "A",
        "Q",
        "P_fus_MW",
        "P_e_net_MW",
        "margin_min",
        "dominant_margin_min",
    ]
    arch_rows = []
    for k in key_fields:
        if k in arch:
            arch_rows.append({"field": k, "value": arch.get(k)})
    if len(arch_rows) == 0:
        arch_rows = [{"field": k, "value": v} for k, v in list(arch.items())[:25]]
    dfA = pd.DataFrame(arch_rows)
    with st.expander("Archetype fields", expanded=False):
        st.dataframe(dfA, use_container_width=True)

    # Member distribution
    st.markdown("### Member distribution")
    with st.expander("Dominant authority distribution (within family)", expanded=False):
        da = [str(m.get("dominant_authority", "(unknown)")) for m in fam.members]
        vc = pd.Series(da).value_counts()
        st.dataframe(vc.rename("count").to_frame(), use_container_width=True)

    with st.expander("Dominant constraint distribution (within family)", expanded=False):
        dc = [str(m.get("dominant_constraint_id", "(unknown)")) for m in fam.members]
        vc = pd.Series(dc).value_counts().head(25)
        st.dataframe(vc.rename("count").to_frame(), use_container_width=True)
