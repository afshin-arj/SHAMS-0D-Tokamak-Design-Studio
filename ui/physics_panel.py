
import streamlit as st
from src.physics.physics_registry import PHYSICS_REGISTRY, MODE_PHYSICS

def render_physics_panel(mode_name: str):
    st.markdown("### Physics & Models Executed")
    ids = MODE_PHYSICS.get(mode_name, [])
    for pid in ids:
        pm = PHYSICS_REGISTRY[pid]
        with st.expander(f"{pm.id} — {pm.domain}"):
            st.markdown(f"**Authority:** {pm.authority}")
            st.markdown("**Equations:**")
            for eq in pm.equations:
                st.code(eq)
            st.markdown("**Closures:**")
            for cl in pm.closures:
                st.markdown(f"- {cl}")
            st.markdown("**Validity domain:**")
            for k,v in pm.validity.items():
                st.markdown(f"- {k}: {v}")


def render_constraint_trace_panel(artifact: dict):
    import streamlit as st
    st.markdown("### Constraint to Physics Traceability")
    trace = artifact.get("constraint_physics_trace", {})
    if not trace:
        st.info("No constraint traceability data available.")
        return
    for c, phys in trace.items():
        st.markdown(f"**{c}** → {', '.join(phys) if phys else 'UNMAPPED'}")
