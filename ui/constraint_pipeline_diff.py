"""Constraint pipeline diff UI (PROPOSAL-027)."""
from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

try:
    from constraints.pipeline_diff import build_pipeline_diff_dossier
except ImportError:
    from src.constraints.pipeline_diff import build_pipeline_diff_dossier


def render_constraint_pipeline_diff(
    out: Dict[str, Any],
    *,
    design_intent: Optional[str] = None,
    key_prefix: str = "cpdiff",
) -> None:
    """Side-by-side registry vs legacy constraint pipeline dossier."""
    if not isinstance(out, dict) or not out:
        st.caption("Run Point Designer to compare constraint pipelines.")
        return

    dossier = build_pipeline_diff_dossier(out, design_intent=design_intent)
    parity = dossier.get("parity") or {}
    aligned = bool(parity.get("pipelines_aligned", True))
    status = "aligned" if aligned else "misaligned"
    st.markdown(f"**Pipeline parity:** {status}")
    st.caption(
        f"Registry specs: {parity.get('registry_n_specs', 0)} | "
        f"Gov {parity.get('n_governance', 0)} / Ledger {parity.get('n_ledger', 0)} | "
        f"Mismatches: {parity.get('n_pass_mismatch', 0)}"
    )

    import pandas as pd

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Registry governance**")
        st.dataframe(
            pd.DataFrame(dossier["registry_governance"]),
            use_container_width=True,
            hide_index=True,
        )
    with c2:
        st.markdown("**Legacy governance**")
        st.dataframe(
            pd.DataFrame(dossier["legacy_governance"]),
            use_container_width=True,
            hide_index=True,
        )
    with c3:
        st.markdown("**Merged governance**")
        st.dataframe(
            pd.DataFrame(dossier["merged_governance"]),
            use_container_width=True,
            hide_index=True,
        )

    if parity.get("only_governance") or parity.get("only_ledger") or parity.get("pass_mismatches"):
        with st.expander("Parity details", expanded=not aligned):
            st.json(
                {
                    "only_governance": parity.get("only_governance", []),
                    "only_ledger": parity.get("only_ledger", []),
                    "pass_mismatches": parity.get("pass_mismatches", []),
                }
            )
