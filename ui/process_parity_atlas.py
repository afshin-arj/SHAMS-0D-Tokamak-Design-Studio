from __future__ import annotations
from pathlib import Path
import json
import streamlit as st

from tools.plant_dossier import build_plant_dossier

def render_process_parity_atlas(repo_root: Path):
    st.markdown("## 📚 PROCESS Parity Atlas")
    st.caption(
        "Compare SHAMS outputs against user-supplied PROCESS reference values. "
        "METHOD-ONLY cases never invent MFILE numbers."
    )

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

    corpus_status = str(ref.get("corpus_status") or "METHOD-ONLY")
    honesty = ref.get("honesty") if isinstance(ref.get("honesty"), dict) else {}
    st.info(f"Corpus status: **{corpus_status}** — {honesty.get('statement', 'No invented PROCESS KPIs.')}")

    cases = ref.get("cases", [])
    if not cases:
        st.info("No cases found in reference file.")
        return

    case_ids = [c.get("case_id","(no id)") for c in cases]
    sel = st.selectbox("Case", options=list(range(len(cases))), format_func=lambda i: case_ids[i])
    case = cases[int(sel)]
    case_status = str(case.get("dossier_status") or corpus_status)
    st.caption(f"Case dossier status: `{case_status}`")
    dd = case.get("delta_dossier") if isinstance(case.get("delta_dossier"), dict) else {}
    if dd.get("sha256"):
        st.caption(f"Hashed delta dossier: `{dd.get('path','')}` · sha256 `{str(dd.get('sha256'))[:16]}…`")

    inputs = case.get("inputs", {})
    evaluator_label = st.text_input("Evaluator label", value="hot_ion_point")

    st.markdown("### Inputs (used for SHAMS evaluation)")
    st.json(inputs)

    if st.button("Evaluate SHAMS for this case", use_container_width=True):
        try:
            from evaluator.core import Evaluator
            try:
                from models.inputs import PointInputs
            except ImportError:
                from src.models.inputs import PointInputs
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
        if case_status == "METHOD-ONLY":
            st.warning(
                "METHOD-ONLY — PROCESS KPI fields are null by design. "
                "Do not treat empty deltas as numeric parity."
            )
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
        if case_status == "METHOD-ONLY" and not delta:
            st.json({"status": "METHOD-ONLY", "message": "No numeric PROCESS fields to delta."})
        else:
            st.json(delta)
