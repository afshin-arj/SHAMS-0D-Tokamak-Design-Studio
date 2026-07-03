"""NO-SOLUTION mechanism atlas UI (PROPOSAL-028)."""
from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

try:
    from diagnostics.no_solution_atlas import build_no_solution_atlas
except ImportError:
    from src.diagnostics.no_solution_atlas import build_no_solution_atlas


def render_no_solution_atlas_panel(
    out: Dict[str, Any],
    *,
    design_intent: Optional[str] = None,
    key_prefix: str = "nsatlas",
) -> None:
    """Render mechanism atlas for infeasible point designs."""
    if not isinstance(out, dict) or not out:
        st.caption("Evaluate a point to build the NO-SOLUTION mechanism atlas.")
        return
    atlas = build_no_solution_atlas(out, design_intent=design_intent)
    verdict = str(atlas.get("verdict", "UNKNOWN"))
    color = "#1b7f3a" if verdict == "FEASIBLE" else "#c0392b"
    st.markdown(
        f'<div style="font-weight:600;color:{color}">Atlas verdict: {verdict}</div>',
        unsafe_allow_html=True,
    )
    dom_c = atlas.get("dominant_constraint") or "(none)"
    dom_m = atlas.get("dominant_mechanism") or "GENERAL"
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Dominant mechanism", dom_m)
    with c2:
        st.metric("Dominant constraint", dom_c)

    mech_map = atlas.get("mechanism_map") or {}
    if mech_map:
        import pandas as pd

        rows = []
        for mech, names in sorted(mech_map.items()):
            for nm in names:
                rows.append({"mechanism": mech, "constraint": nm})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    elif verdict == "FEASIBLE":
        st.caption("No hard constraint failures — mechanism map empty.")
