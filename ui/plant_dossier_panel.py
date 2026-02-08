from __future__ import annotations
from pathlib import Path
import streamlit as st

from src.plant.accounting import compute_plant_ledger, ledger_to_json
from tools.plant_dossier import export_plant_dossier_zip, build_plant_dossier

def render_plant_dossier_panel(repo_root: Path, *, artifact: dict):
    st.markdown("## 🧾 Plant Dossier")
    st.caption("Plant-level accounting derived from the current run artifact. Read-only; does not affect truth.")

    if not isinstance(artifact, dict) or not artifact:
        st.warning("No current run artifact available. Run Point Designer first or load an artifact.")
        return

    ledger = compute_plant_ledger(artifact)
    st.markdown("### Plant power ledger")
    st.json(ledger_to_json(ledger))

    dossier = build_plant_dossier(artifact)
    st.markdown("### Plant dossier object")
    st.json(dossier)

    out_dir = repo_root / "ui_runs" / "plant_dossier"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_zip = out_dir / "plant_dossier.zip"

    if st.button("Export plant dossier ZIP", use_container_width=True):
        export_plant_dossier_zip(artifact, out_zip)
        st.session_state["plant_dossier_zip_path"] = str(out_zip)

    p = st.session_state.get("plant_dossier_zip_path")
    if isinstance(p, str) and p:
        zp = Path(p)
        if zp.exists():
            st.download_button(
                "Download plant dossier ZIP",
                data=zp.read_bytes(),
                file_name=zp.name,
                mime="application/zip",
                use_container_width=True,
            )
