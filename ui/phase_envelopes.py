from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import json
import streamlit as st

try:
    from src.models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore

from src.phase_envelopes import PhaseSpec, run_phase_envelope_for_point
from tools.phase_envelopes import export_phase_envelope_zip


_POINTINPUTS_FIELDS = {f.name for f in fields(PointInputs)}


def _field_group(name: str) -> str:
    """Best-effort expert grouping for PointInputs fields.

    This is UI-only; it does not change truth or semantics.
    """
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


def _is_numeric(v: Any) -> bool:
    return isinstance(v, (int, float)) and v is not None


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        if isinstance(v, bool):
            return float(int(v))
        if isinstance(v, (int, float)):
            return float(v)
        return float(str(v))
    except Exception:
        return None


def _make_point_inputs(inp_dict: Dict[str, Any]) -> PointInputs:
    filtered = {k: v for k, v in (inp_dict or {}).items() if k in _POINTINPUTS_FIELDS}
    return PointInputs(**filtered)


_DEFAULT_PHASES_JSON = json.dumps(
    [
        {"name": "ramp_up", "input_overrides": {}, "policy_overrides": {}, "notes": "Quasi-static check (no dynamics)."},
        {"name": "flat_top", "input_overrides": {}, "policy_overrides": {}, "notes": "Baseline operating point."},
        {"name": "ramp_down", "input_overrides": {}, "policy_overrides": {}, "notes": "Quasi-static check (no dynamics)."},
    ],
    indent=2,
    sort_keys=True,
)


def render_phase_envelopes_panel(repo_root: Path, *, point_artifact: Optional[Dict[str, Any]]):
    st.subheader("🗺️ Phase Envelopes")
    st.caption("Ordered quasi-static phases (ramp/flat-top/ramp-down). Each phase is evaluated independently with frozen truth. Worst-phase determines the envelope verdict.")

    if not isinstance(point_artifact, dict) or not isinstance(point_artifact.get("inputs"), dict):
        st.info("Run **Point Designer** first to populate Phase Envelopes.")
        return

    base_inputs = _make_point_inputs(point_artifact["inputs"])

    # --- Cockpit editor (writes JSON spec deterministically) ---
    _raw_json = st.session_state.get("phase_envelopes_phases_json", _DEFAULT_PHASES_JSON)
    try:
        _parsed = json.loads(_raw_json)
        _parsed = _parsed if isinstance(_parsed, list) else []
    except Exception:
        _parsed = []

    # Candidate fields for overrides (numeric first, then others).
    _base_dict = dict(point_artifact.get("inputs") or {})
    _numeric_fields = [k for k in sorted(_POINTINPUTS_FIELDS) if _is_numeric(_base_dict.get(k))]
    _other_fields = [k for k in sorted(_POINTINPUTS_FIELDS) if k not in set(_numeric_fields)]

    with st.expander("🧭 Cockpit editor (recommended)", expanded=False):
        st.caption(
            "Build phase overrides using structured controls. This editor **writes** the JSON spec used for the deterministic run. "
            "It does not modify the frozen evaluator."
        )

        # Phase list (name only) — keep ordered.
        _phase_names = []
        for i, it in enumerate(_parsed or []):
            if isinstance(it, dict) and it.get("name"):
                _phase_names.append(str(it.get("name")))
        if not _phase_names:
            _phase_names = ["ramp_up", "flat_top", "ramp_down"]

        _group = st.selectbox(
            "Variable group",
            options=["PLASMA", "GEOMETRY", "HEATING", "EXHAUST", "MAGNETS", "CONTROL/PF", "NEUTRONICS", "OTHER", "ALL"],
            index=0,
            help="UI-only grouping to reduce cognitive load.",
        )

        _candidate = _numeric_fields + _other_fields
        if _group != "ALL":
            _candidate = [k for k in _candidate if _field_group(k) == _group]

        _sel = st.multiselect(
            "Override variables (PointInputs fields)",
            options=_candidate,
            default=st.session_state.get("phase_env_override_vars", []),
            help="Select inputs to override per phase. Numeric fields get number inputs; others use text.",
        )
        st.session_state["phase_env_override_vars"] = _sel

        # Build per-phase overrides.
        _overrides: Dict[str, Dict[str, Any]] = {pn: {} for pn in _phase_names}
        _n_nonempty = 0

        if _sel:
            st.markdown("**Per-phase overrides**")
            _cols = st.columns(len(_phase_names))
            for c, pn in zip(_cols, _phase_names):
                with c:
                    st.markdown(f"**{pn}**")
                    for k in _sel:
                        base_v = _base_dict.get(k)
                        if _is_numeric(base_v):
                            dv = _safe_float(base_v)
                            val = st.number_input(
                                k,
                                value=float(dv) if dv is not None else 0.0,
                                key=f"phase_env_{pn}_{k}",
                            )
                            if dv is None or float(val) != float(dv):
                                _overrides[pn][k] = float(val)
                        else:
                            sval = st.text_input(
                                k,
                                value=str(base_v) if base_v is not None else "",
                                key=f"phase_env_txt_{pn}_{k}",
                            )
                            if str(sval) != (str(base_v) if base_v is not None else ""):
                                _overrides[pn][k] = sval

            _n_nonempty = sum(len(v) for v in _overrides.values())

        st.info(f"🧾 Override dimension budget: **{_n_nonempty}** non-baseline overrides across **{len(_phase_names)}** phases.")

        if st.button("Update JSON spec from cockpit", use_container_width=True):
            spec = []
            for pn in _phase_names:
                spec.append(
                    {
                        "name": pn,
                        "input_overrides": dict(_overrides.get(pn) or {}),
                        "policy_overrides": {},
                        "notes": "Quasi-static check (no dynamics).",
                    }
                )
            st.session_state["phase_envelopes_phases_json"] = json.dumps(spec, indent=2, sort_keys=True)
            st.success("JSON spec updated.")

    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("### Phase specification (JSON)")
        st.caption(
            "This is the **authoritative** phase spec used for execution and exported artifacts. "
            "Overrides map to PointInputs fields. Policy overrides affect constraint tier semantics only (no physics changes)."
        )
        phases_json = st.text_area(
            "Phases JSON",
            value=st.session_state.get("phase_envelopes_phases_json", _DEFAULT_PHASES_JSON),
            height=240,
            label_visibility="collapsed",
        )
    with c2:
        st.markdown("### Run controls")
        label_prefix = st.text_input("Label prefix", value="phase", help="Prefix used in per-phase artifact labels.")
        st.session_state["phase_envelopes_phases_json"] = phases_json

        run_btn = st.button("Run Phase Envelope", use_container_width=True)
        st.caption("Deterministic. No iteration. No time integration.")

    if run_btn:
        try:
            raw = json.loads(phases_json)
            if not isinstance(raw, list) or not raw:
                raise ValueError("Phases JSON must be a non-empty list.")
            phases: List[PhaseSpec] = []
            for item in raw:
                if not isinstance(item, dict) or "name" not in item:
                    raise ValueError("Each phase must be an object with at least a 'name'.")
                phases.append(
                    PhaseSpec(
                        name=str(item["name"]),
                        input_overrides=dict(item.get("input_overrides") or {}),
                        policy_overrides=dict(item.get("policy_overrides") or {}) if item.get("policy_overrides") is not None else None,
                        notes=str(item.get("notes", "")),
                    )
                )
            env = run_phase_envelope_for_point(base_inputs, phases, label_prefix=label_prefix)
            st.session_state["phase_envelopes_last"] = env
            st.success("Phase envelope complete.")
        except Exception as e:
            st.error(f"Phase envelope failed: {e}")

    env = st.session_state.get("phase_envelopes_last")
    if not isinstance(env, dict):
        st.info("No phase envelope results yet.")
        return

    summ = env.get("envelope_summary") if isinstance(env.get("envelope_summary"), dict) else {}
    st.markdown("### Envelope verdict")
    cA, cB, cC = st.columns(3)
    cA.metric("Envelope verdict", str(summ.get("envelope_verdict", "UNKNOWN")))
    cB.metric("Worst phase", str(summ.get("worst_phase", "")))
    cC.metric("Worst hard margin", str(summ.get("worst_phase_worst_hard_margin_frac", "")))

    with st.expander("Envelope summary (JSON)", expanded=False):
        st.json(summ)

    st.markdown("### Phase table")
    phases = env.get("phases_ordered") or []
    rows = []
    if isinstance(phases, list):
        for art in phases:
            if not isinstance(art, dict):
                continue
            ph = art.get("phase") or {}
            cs = art.get("constraints_summary") or {}
            rows.append(
                {
                    "phase": (ph.get("name") if isinstance(ph, dict) else ""),
                    "feasible": bool(cs.get("feasible", False)),
                    "n_hard_failed": cs.get("n_hard_failed"),
                    "worst_hard": cs.get("worst_hard"),
                    "worst_margin": cs.get("worst_hard_margin_frac"),
                }
            )
    st.dataframe(rows, use_container_width=True, hide_index=True)

    out_dir = repo_root / "ui_runs" / "phase_envelopes"
    out_zip = out_dir / "phase_envelopes.zip"

    cX, cY = st.columns([1, 1])
    with cX:
        if st.button("Export Phase Envelopes ZIP", use_container_width=True):
            try:
                export_phase_envelope_zip(env, out_zip)
                st.session_state["phase_envelopes_zip_path"] = str(out_zip)
                st.success("ZIP exported.")
            except Exception as e:
                st.error(f"Export failed: {e}")
    with cY:
        p = st.session_state.get("phase_envelopes_zip_path")
        if isinstance(p, str) and p:
            zp = Path(p)
            if zp.exists():
                st.download_button(
                    "Download Phase Envelopes ZIP",
                    data=zp.read_bytes(),
                    file_name=zp.name,
                    mime="application/zip",
                    use_container_width=True,
                )
