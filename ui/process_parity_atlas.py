from __future__ import annotations
from pathlib import Path
import json
import streamlit as st

from tools.plant_dossier import build_plant_dossier

def render_process_parity_atlas(repo_root: Path):
    st.markdown("## 📚 PROCESS Parity Atlas")
    st.caption("Compare SHAMS outputs against user-supplied PROCESS reference values. No assumptions.")

    default_path = repo_root / "benchmarks" / "parity" / "process_reference_cases.json"
    use_upload = st.toggle("Upload reference JSON", value=False)

    ref = None
    if use_upload:
        up = st.file_uploader("Upload process_reference_cases.json", type=["json"])
        if up is not None:
            ref = json.loads(up.read().decode("utf-8"))
    else:
        if default_path.exists():
            ref = json.loads(default_path.read_text(encoding="utf-8"))
        else:
            st.error("Default reference file not found.")
            return

    if not isinstance(ref, dict) or "cases" not in ref:
        st.error("Invalid reference schema.")
        return

    cases = ref.get("cases", [])
    if not cases:
        st.info("No cases found in reference file.")
        return

    case_ids = [c.get("case_id","(no id)") for c in cases]
    sel = st.selectbox("Case", options=list(range(len(cases))), format_func=lambda i: case_ids[i])
    case = cases[int(sel)]

    inputs = case.get("inputs", {})
    evaluator_label = st.text_input("Evaluator label", value="hot_ion_point")

    st.markdown("### Inputs (used for SHAMS evaluation)")
    st.json(inputs)

    if st.button("Evaluate SHAMS for this case", use_container_width=True):
        try:
            from src.evaluator.core import Evaluator
            from src.inputs.point_inputs import PointInputs
            ev = Evaluator(label=str(evaluator_label))
            pi = PointInputs(**inputs)
            out = ev.evaluate(pi)
            outputs = out.__dict__ if hasattr(out, "__dict__") else dict(out)
            art = {"inputs": inputs, "outputs": outputs, "verdict": "UNKNOWN"}
            dossier = build_plant_dossier(art)
            st.session_state["parity_last_dossier"] = dossier
        except Exception as e:
            st.error(f"Evaluation failed: {e}")
            return

    dossier = st.session_state.get("parity_last_dossier")
    if isinstance(dossier, dict):
        st.markdown("### SHAMS-derived plant metrics")
        st.json(dossier.get("plant_ledger", {}))

        st.markdown("### PROCESS reference (user-supplied)")
        st.json(case.get("process_reference", {}))

        st.markdown("### Delta (SHAMS - PROCESS) for provided fields")
        sh = dossier.get("plant_ledger", {})
        pr = case.get("process_reference", {})
        delta = {}
        for k, v in pr.items():
            if v is None:
                continue
            try:
                delta[k] = float(sh.get(k, 0.0)) - float(v)
            except Exception:
                pass
        st.json(delta)
