from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import json

try:
    import streamlit as st
    _HAVE_STREAMLIT = True
except Exception:
    st = None
    _HAVE_STREAMLIT = False

from src.governance.contract_validator import validate_contracts_dir, load_contract_json, sha256_canonical_json


def _json_preview(obj: Dict[str, Any]):
    st.json(obj, expanded=False)


def render_contract_studio(repo_root: Path, ui_key_prefix: str = "contract_studio"):
    """
    Contract Studio: browse/validate/export governance contracts.
    Truth-safe: read-only operations on contracts/*.json.
    """
    if not _HAVE_STREAMLIT:
        return

    contracts_dir = repo_root / "contracts"
    st.subheader("🧾 Contract Studio")
    st.caption("Browse and validate SHAMS governance contracts (read-only). Deterministic hashes are computed from canonical JSON.")

    recs, summary = validate_contracts_dir(contracts_dir)

    with st.expander("✅ Validation summary", expanded=True):
        st.write({
            "ok": summary.get("ok", False),
            "n_contracts": summary.get("n_contracts", 0),
            "n_ok": summary.get("n_ok", 0),
            "n_errors": summary.get("n_errors", 0),
            "n_warnings": summary.get("n_warnings", 0),
            "contracts_fingerprint_sha256": summary.get("contracts_fingerprint_sha256", ""),
        })

    with st.expander("📜 Contracts table", expanded=False):
        rows = []
        for r in recs:
            rows.append({
                "name": r.name,
                "ok": bool(r.ok),
                "sha256": r.sha256,
                "n_errors": len(r.errors),
                "n_warnings": len(r.warnings),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    names = [r.name for r in recs]
    if not names:
        st.warning("No contracts found.")
        return

    col1, col2 = st.columns(2)
    with col1:
        sel_a = st.selectbox("Contract A", names, index=0, key=f"{ui_key_prefix}_sel_a")
    with col2:
        sel_b = st.selectbox("Contract B (optional diff)", ["(none)"] + names, index=0, key=f"{ui_key_prefix}_sel_b")

    def load_obj(name: str) -> Optional[Dict[str, Any]]:
        if name == "(none)":
            return None
        p = contracts_dir / name
        obj, errs = load_contract_json(p)
        if errs:
            st.error(f"Failed to load {name}: {errs}")
            return None
        return obj

    obj_a = load_obj(sel_a)
    obj_b = load_obj(sel_b) if sel_b != "(none)" else None

    if obj_a is not None:
        with st.expander(f"🔎 {sel_a} (sha256={sha256_canonical_json(obj_a)[:12]}…)", expanded=True):
            _json_preview(obj_a)

    if obj_b is not None:
        with st.expander(f"🔎 {sel_b} (sha256={sha256_canonical_json(obj_b)[:12]}…)", expanded=False):
            _json_preview(obj_b)

    if obj_a is not None and obj_b is not None:
        with st.expander("🧩 Structural diff (keys)", expanded=False):
            keys_a = set(obj_a.keys())
            keys_b = set(obj_b.keys())
            st.write({
                "only_in_a": sorted(list(keys_a - keys_b)),
                "only_in_b": sorted(list(keys_b - keys_a)),
                "in_both": sorted(list(keys_a & keys_b)),
            })

    # Export contract bundle
    with st.expander("📦 Export contract bundle (ZIP)", expanded=False):
        import io, zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for r in recs:
                p = contracts_dir / r.name
                if p.exists():
                    z.write(p, arcname=f"contracts/{r.name}")
            # include summary manifest
            z.writestr("CONTRACTS_MANIFEST.json", json.dumps(summary, indent=2, sort_keys=True))
        buf.seek(0)
        st.download_button(
            "Download contracts bundle ZIP",
            data=buf.getvalue(),
            file_name="shams_contracts_bundle.zip",
            mime="application/zip",
            key=f"{ui_key_prefix}_dl_bundle",
        )
