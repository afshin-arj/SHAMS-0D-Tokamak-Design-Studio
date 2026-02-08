from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st

try:
    from src.models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore

from src.uq_contracts import Interval, UncertaintyContractSpec, run_uncertainty_contract_for_point
from tools.uncertainty_contracts import export_uncertainty_contract_zip


_POINTINPUTS_FIELDS = {f.name for f in fields(PointInputs)}


def _field_group(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["r0", "a0", "kappa", "delta", "triang", "aspect", "elong", "shape", "major", "minor"]):
        return "GEOMETRY"
    if any(k in n for k in ["bt", "b0", "btor", "ip", "q", "beta", "li", "wth", "tau", "greenwald", "ne", "ni", "te", "ti"]):
        return "PLASMA"
    if any(k in n for k in ["paux", "pnbi", "pech", "icrh", "lhcd", "power", "heat"]):
        return "HEATING"
    if any(k in n for k in ["pf", "cs", "oh", "rwm", "vertical", "ctrl", "control"]):
        return "CONTROL/PF"
    if any(k in n for k in ["psep", "exhaust", "detachment", "div", "target", "lambda", "sol", "radiat"]):
        return "EXHAUST"
    if any(k in n for k in ["neutron", "blanket", "shield", "tbr", "wall", "fw", "dose"]):
        return "NEUTRONICS"
    if any(k in n for k in ["tf", "coil", "stress", "jcrit", "hts", "magnet"]):
        return "MAGNETS"
    return "OTHER"


def _make_point_inputs(inp_dict: Dict[str, Any]) -> PointInputs:
    filtered = {k: v for k, v in (inp_dict or {}).items() if k in _POINTINPUTS_FIELDS}
    return PointInputs(**filtered)


def render_uncertainty_contracts_panel(repo_root: Path, *, point_artifact: Optional[Dict[str, Any]]):
    st.subheader("🛡️ Uncertainty Contracts")
    st.caption("Declare interval uncertainty on selected inputs. SHAMS enumerates all corners deterministically (2^N). Verdict: ROBUST_PASS / FRAGILE / FAIL. No probability, no Monte Carlo.")

    if not isinstance(point_artifact, dict) or not isinstance(point_artifact.get("inputs"), dict):
        st.info("Run **Point Designer** first to populate Uncertainty Contracts.")
        return

    base_inp = point_artifact["inputs"]
    base_inputs = _make_point_inputs(base_inp)

    # Candidate uncertain fields: numeric scalars only (best-effort).
    numeric_fields = []
    for k in sorted(_POINTINPUTS_FIELDS):
        v = base_inp.get(k)
        if isinstance(v, (int, float)) and v is not None:
            numeric_fields.append(k)

    st.markdown("### Contract builder")
    st.caption("Tip: keep N small enough to remain audit-tractable; corners scale as 2^N.")
    c1, c2, c3 = st.columns([1.6, 1, 1])
    with c1:
        name = st.text_input("Contract name", value=str(st.session_state.get("uq_contract_name", "uq_contract")))

        _group = st.selectbox(
            "Variable group",
            options=["PLASMA", "GEOMETRY", "HEATING", "EXHAUST", "MAGNETS", "CONTROL/PF", "NEUTRONICS", "OTHER", "ALL"],
            index=0,
            help="UI-only grouping to reduce cognitive load.",
        )
        _opts = list(numeric_fields)
        if _group != "ALL":
            _opts = [k for k in _opts if _field_group(k) == _group]

        dims = st.multiselect(
            "Uncertain variables (PointInputs fields)",
            options=_opts,
            default=st.session_state.get("uq_contract_dims", []),
            help="Select the inputs you want to treat as uncertain intervals.",
        )
        st.session_state["uq_contract_name"] = name
        st.session_state["uq_contract_dims"] = dims

    with c2:
        mode = st.selectbox("Interval mode", ["±% around baseline", "absolute [lo,hi]"], index=0)
        pct = st.slider("± percent", min_value=0.0, max_value=30.0, value=float(st.session_state.get("uq_contract_pct", 5.0)), step=0.5)
        st.session_state["uq_contract_pct"] = pct

    with c3:
        max_dims = st.number_input("Max dims", min_value=1, max_value=20, value=int(st.session_state.get("uq_contract_max_dims", 12)), step=1)
        _n = int(len(dims) if dims else 0)
        _corners = 2 ** _n if _n >= 0 else 0
        st.metric("Corner count", f"{_corners:,}" if _n > 0 else "0")
        if _n >= 16:
            st.warning("High N: corner count may become unwieldy for interactive use.")
        run_btn = st.button("Run Uncertainty Contract", use_container_width=True)
        st.caption("Deterministic corner enumeration. No probability.")

    # Build intervals
    intervals: Dict[str, Interval] = {}
    if dims:
        for k in dims:
            v = base_inp.get(k)
            if not isinstance(v, (int, float)) or v is None:
                continue
            v = float(v)
            if mode.startswith("±%"):
                lo = v * (1.0 - float(pct) / 100.0)
                hi = v * (1.0 + float(pct) / 100.0)
                intervals[k] = Interval(lo=lo, hi=hi)
            else:
                # absolute mode: let user set per-variable bounds compactly
                with st.expander(f"Bounds for {k} (baseline {v})", expanded=False):
                    lo = st.number_input(f"{k} lo", value=v, key=f"uq_{k}_lo")
                    hi = st.number_input(f"{k} hi", value=v, key=f"uq_{k}_hi")
                    intervals[k] = Interval(lo=float(lo), hi=float(hi))

    if run_btn:
        try:
            spec = UncertaintyContractSpec(name=str(name), intervals=intervals, policy_overrides=None, notes="")
            con = run_uncertainty_contract_for_point(base_inputs, spec, label_prefix="uq", max_dims=int(max_dims))
            st.session_state["uq_contract_last"] = con
            st.success("Uncertainty contract complete.")
        except Exception as e:
            st.error(f"Uncertainty contract failed: {e}")

    con = st.session_state.get("uq_contract_last")
    if not isinstance(con, dict):
        st.info("No uncertainty contract results yet.")
        return

    summ = con.get("summary") if isinstance(con.get("summary"), dict) else {}
    st.markdown("### Contract verdict")
    cA, cB, cC, cD = st.columns(4)
    cA.metric("Verdict", str(summ.get("verdict", "UNKNOWN")))
    cB.metric("Dims", str(summ.get("n_dims", "")))
    cC.metric("Corners", str(summ.get("n_corners", "")))
    cD.metric("Feasible", str(summ.get("n_feasible", "")))

    with st.expander("Contract summary (JSON)", expanded=False):
        st.json(summ)

    out_dir = repo_root / "ui_runs" / "uncertainty_contracts"
    out_zip = out_dir / "uncertainty_contracts.zip"

    cX, cY = st.columns([1, 1])
    with cX:
        if st.button("Export Uncertainty Contract ZIP", use_container_width=True):
            try:
                export_uncertainty_contract_zip(con, out_zip)
                st.session_state["uq_contract_zip_path"] = str(out_zip)
                st.success("ZIP exported.")
            except Exception as e:
                st.error(f"Export failed: {e}")

    with cY:
        p = st.session_state.get("uq_contract_zip_path")
        if isinstance(p, str) and p:
            zp = Path(p)
            if zp.exists():
                st.download_button(
                    "Download Uncertainty Contract ZIP",
                    data=zp.read_bytes(),
                    file_name=zp.name,
                    mime="application/zip",
                    use_container_width=True,
                )
