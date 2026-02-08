"""Robust Pareto Lab (Phase+UQ)

SHAMS law compliance:
- Truth remains frozen (uses Point Designer evaluator as a black box).
- No optimization; this is a robustness *interrogation* layer over candidate points.
- Deterministic corner enumeration (v281) and ordered quasi-static phases (v280).

v286.0: Robust / Fragile / Mirage frontier classification.
"""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

import pandas as pd

from src.models.inputs import PointInputs
from src.physics.hot_ion import hot_ion_point
from src.phase_envelopes import PhaseSpec, run_phase_envelope_for_point
from src.uq_contracts import UncertaintyContractSpec, Interval, run_uncertainty_contract_for_point


def _extract_default_json_literal(py_text: str, var_name: str) -> Optional[str]:
    """Extract a module-level string literal named var_name.

    This avoids importing UI modules (keeps import-guard safe).
    """
    import re

    # naive but stable: var_name = "..." or var_name = '''...'''
    pat = re.compile(rf"^{var_name}\s*=\s*(?P<q>'''|\"\"\"|'|\")(?P<body>.*?)(?P=q)", re.M | re.S)
    m = pat.search(py_text)
    if not m:
        return None
    return m.group("body")


def _load_phase_defaults() -> str:
    try:
        txt = (Path(__file__).resolve().parent / "phase_envelopes.py").read_text(encoding="utf-8")
        val = _extract_default_json_literal(txt, "_DEFAULT_PHASES_JSON")
        if isinstance(val, str) and val.strip():
            return val
    except Exception:
        pass
    # safe fallback: 2-phase minimal
    return json.dumps(
        [
            {"name": "Ramp", "input_overrides": {"Paux_MW": 0.0}, "notes": "cold start"},
            {"name": "Flat-top", "input_overrides": {}, "notes": "baseline"},
        ],
        indent=2,
    )


def _load_uq_defaults() -> str:
    try:
        txt = (Path(__file__).resolve().parent / "uncertainty_contracts.py").read_text(encoding="utf-8")
        val = _extract_default_json_literal(txt, "_DEFAULT_UQ_JSON")
        if isinstance(val, str) and val.strip():
            return val
    except Exception:
        pass
    # safe fallback: 2D tiny contract
    return json.dumps(
        {
            "name": "Default (fallback)",
            "intervals": {
                "fG": {"lo": 0.75, "hi": 0.85},
                "Paux_MW": {"lo": 0.0, "hi": 30.0},
            },
            "policy_overrides": {},
        },
        indent=2,
    )


def _parse_phases(phases_json: str) -> List[PhaseSpec]:
    raw = json.loads(phases_json)
    if not isinstance(raw, list) or not raw:
        raise ValueError("Phases JSON must be a non-empty list")
    phases: List[PhaseSpec] = []
    for item in raw:
        if not isinstance(item, dict) or "name" not in item:
            raise ValueError("Each phase must be an object with at least a 'name'")
        phases.append(
            PhaseSpec(
                name=str(item["name"]),
                input_overrides=dict(item.get("input_overrides") or {}),
                policy_overrides=dict(item.get("policy_overrides") or {}) if item.get("policy_overrides") is not None else None,
                notes=str(item.get("notes", "")),
            )
        )
    return phases


def _parse_uq(uq_json: str) -> UncertaintyContractSpec:
    raw = json.loads(uq_json)
    if not isinstance(raw, dict):
        raise ValueError("UQ JSON must be an object")
    name = str(raw.get("name", "UQ"))
    intervals_raw = raw.get("intervals")
    if not isinstance(intervals_raw, dict) or not intervals_raw:
        raise ValueError("UQ JSON must include non-empty 'intervals' dict")
    intervals: Dict[str, Interval] = {}
    for k, v in intervals_raw.items():
        if not isinstance(v, dict) or "lo" not in v or "hi" not in v:
            raise ValueError(f"Interval for '{k}' must be an object with lo/hi")
        intervals[str(k)] = Interval(lo=float(v["lo"]), hi=float(v["hi"]))
    pol = raw.get("policy_overrides")
    return UncertaintyContractSpec(name=name, intervals=intervals, policy_overrides=dict(pol or {}) if pol is not None else None)


def _robust_objective(orientation: str, vals: List[float]) -> float:
    """Worst-case objective aggregator.

    - for 'max': robust value is min(vals)
    - for 'min': robust value is max(vals)
    """
    v = [float(x) for x in vals if x is not None and float(x) == float(x)]
    if not v:
        return float("nan")
    if str(orientation).lower().startswith("max"):
        return float(min(v))
    return float(max(v))


def _classify(nominal_feasible: bool, env_verdict: str, uq_verdict: str) -> str:
    if not nominal_feasible:
        return "FAIL"
    ev = str(env_verdict)
    uv = str(uq_verdict)
    if ev == "PASS" and uv == "ROBUST_PASS":
        return "ROBUST"
    if ev == "PASS" and uv == "FRAGILE":
        return "FRAGILE"
    # nominal feasible but fails under worst-phase or worst-corner
    return "MIRAGE"


def render_robust_pareto_lab(repo_root: Path) -> None:
    st.markdown("### 🛡️ Robust Pareto Frontier (Phase+UQ)")
    st.caption(
        "Re-interrogates candidate points under quasi-static phase envelopes (v280) and deterministic uncertainty corners (v281). "
        "Outputs a ROBUST / FRAGILE / MIRAGE classification. No optimization occurs here."
    )


    # Candidate source: Robust Pareto can interrogate either
    #  (a) Pareto Lab last run (pareto_last) or
    #  (b) Trade Study Studio active study capsule (active_study_capsule)
    # Source selection: use either last Pareto Lab run or the active Trade Study capsule.
    pareto_last = st.session_state.get("pareto_last")
    study_cap = st.session_state.get("active_study_capsule")

    sources = []
    if isinstance(pareto_last, dict) and isinstance(pareto_last.get("pareto"), list) and len(pareto_last.get("pareto") or []) > 0:
        sources.append("📈 Pareto Lab — last internal Pareto run")
    if isinstance(study_cap, dict) and isinstance(study_cap.get("pareto"), list) and len(study_cap.get("pareto") or []) > 0:
        sources.append("🧪 Trade Study Studio — active study capsule")

    if not sources:
        st.info("Provide candidate points first: run an Internal Pareto Frontier or a Trade Study (to generate a Pareto subset), then return here.")
        return

    if len(sources) == 1:
        src = sources[0]
    else:
        src = st.selectbox("Candidate source", sources, index=0, key="robust_pareto_source")

    if src.startswith("📈"):
        last = pareto_last
        source_mode = "pareto_lab"
    else:
        # Normalize the Study Capsule into the minimal shape expected by this view.
        cap = study_cap
        last = {
            "pareto": list(cap.get("pareto") or []),
            "bounds": (cap.get("knob_set") or {}).get("bounds"),
            "seed": (cap.get("meta") or {}).get("seed"),
            "n_samples": (cap.get("meta") or {}).get("n_samples"),
            "objectives": {k: {"sense": (cap.get("objective_senses") or {}).get(k, "min")} for k in (cap.get("objectives") or [])},
        }
        source_mode = "trade_study"

    objectives = last.get("objectives") or {}
    if not isinstance(objectives, dict) or not objectives:
        st.warning("No objective contract found in last Pareto run. Robust view can still classify feasibility, but cannot compute robust objective degradation.")
        objectives = {}

    # Base inputs: prefer last point anchor; else infer from defaults.
    base_inputs = st.session_state.get("last_point_inp")
    if not isinstance(base_inputs, PointInputs):
        base_inputs = PointInputs(R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.0, Ti_keV=15.0, fG=0.8, Paux_MW=20.0)

    st.markdown("#### Robustness specifications")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Phase envelope spec (JSON)")
        phases_json = st.text_area(
            "Phases JSON",
            value=st.session_state.get("robust_pareto_phases_json", _load_phase_defaults()),
            height=220,
            key="robust_pareto_phases_json",
            label_visibility="collapsed",
        )
    with c2:
        st.caption("Uncertainty contract (JSON)")
        uq_json = st.text_area(
            "UQ JSON",
            value=st.session_state.get("robust_pareto_uq_json", _load_uq_defaults()),
            height=220,
            key="robust_pareto_uq_json",
            label_visibility="collapsed",
        )

    run_cols = st.columns([1, 1, 2])
    with run_cols[0]:
        n_take = int(st.number_input("Max points", min_value=1, max_value=1000, value=min(60, len(last.get("pareto") or [])), step=5))
    with run_cols[1]:
        label_prefix = st.text_input("Label prefix", value="robust", help="Used in per-point artifacts")
    with run_cols[2]:
        st.caption("Tip: keep Max points modest; each point runs phases + 2^N corners.")

    run_btn = st.button("Run Robust Frontier", use_container_width=True)
    if not run_btn:
        # If we already have results, show them.
        _res = st.session_state.get("robust_pareto_last")
        if isinstance(_res, dict) and isinstance(_res.get("rows"), list) and len(_res.get("rows") or []):
            _render_results(_res)
        return

    # Parse specs (fail fast)
    try:
        phases = _parse_phases(phases_json)
        uq_spec = _parse_uq(uq_json)
    except Exception as e:
        st.error(f"Spec parse failed: {e}")
        return

    pareto_pts = list(last.get("pareto") or [])[: int(n_take)]
    bounds = last.get("bounds") or {}
    bound_keys = list(bounds.keys()) if isinstance(bounds, dict) else []

    rows: List[Dict[str, Any]] = []
    point_arts: List[Dict[str, Any]] = []

    prog = st.progress(0.0)
    for i, row in enumerate(pareto_pts):
        # reconstruct PointInputs from base + bound keys present in record
        d = asdict(base_inputs)
        if isinstance(row, dict):
            for k in bound_keys:
                if k in row:
                    try:
                        d[k] = float(row[k])
                    except Exception:
                        pass
        inp = PointInputs(**d)

        # Nominal
        out0 = hot_ion_point(inp)
        nominal_feasible = bool(row.get("is_feasible", True)) if isinstance(row, dict) else True

        # Phase envelope
        env = run_phase_envelope_for_point(inp, phases, label_prefix=f"{label_prefix}:p{i:04d}")
        env_s = (env.get("envelope_summary") or {}) if isinstance(env, dict) else {}
        env_verdict = str(env_s.get("envelope_verdict", "UNKNOWN"))
        env_worst_margin = env_s.get("worst_phase_worst_hard_margin_frac")
        try:
            env_worst_margin_f = float(env_worst_margin) if env_worst_margin is not None else float("nan")
        except Exception:
            env_worst_margin_f = float("nan")

        # UQ contract
        uq = run_uncertainty_contract_for_point(inp, uq_spec, label_prefix=f"{label_prefix}:u{i:04d}")
        uq_sum = (uq.get("summary") or {}) if isinstance(uq, dict) else {}
        uq_verdict = str(uq_sum.get("verdict", "UNKNOWN"))
        uq_worst_margin = uq_sum.get("worst_hard_margin_frac")
        try:
            uq_worst_margin_f = float(uq_worst_margin) if uq_worst_margin is not None else float("nan")
        except Exception:
            uq_worst_margin_f = float("nan")

        tier = _classify(nominal_feasible, env_verdict, uq_verdict)

        # Robust objective aggregation (conservative and cheap):
        # evaluate objectives at (nominal, worst-phase, worst-corner) and aggregate worst-case.
        robust_obj: Dict[str, float] = {}
        degrade: Dict[str, float] = {}

        # pull nominal objective values from hot_ion_point output
        def _val_from_out(o: Dict[str, Any], k: str) -> float:
            try:
                v = o.get(k)
                return float(v) if v is not None else float("nan")
            except Exception:
                return float("nan")

        # worst-phase outputs
        worst_phase_idx = int(env.get("worst_phase_index", 0) or 0) if isinstance(env, dict) else 0
        worst_phase_art = None
        try:
            phs = env.get("phases_ordered") if isinstance(env, dict) else None
            if isinstance(phs, list) and 0 <= worst_phase_idx < len(phs):
                worst_phase_art = phs[worst_phase_idx]
        except Exception:
            worst_phase_art = None
        worst_phase_out = (worst_phase_art.get("outputs") if isinstance(worst_phase_art, dict) else None) or {}

        # worst-corner outputs
        worst_corner_idx = uq_sum.get("worst_corner_index")
        worst_corner_art = None
        try:
            ci = int(worst_corner_idx) if worst_corner_idx is not None else None
            corners = uq.get("corners") if isinstance(uq, dict) else None
            if isinstance(ci, int) and isinstance(corners, list) and 0 <= ci < len(corners):
                worst_corner_art = corners[ci]
        except Exception:
            worst_corner_art = None
        worst_corner_out = (worst_corner_art.get("outputs") if isinstance(worst_corner_art, dict) else None) or {}

        for ok, sense in objectives.items():
            try:
                nom = _val_from_out(out0, ok)
                wph = _val_from_out(worst_phase_out, ok)
                wco = _val_from_out(worst_corner_out, ok)
                rob = _robust_objective(str(sense), [nom, wph, wco])
                robust_obj[ok] = rob
                if nom == nom and nom != 0 and rob == rob:
                    degrade[ok] = float((rob - nom) / abs(nom))
                else:
                    degrade[ok] = float("nan")
            except Exception:
                robust_obj[ok] = float("nan")
                degrade[ok] = float("nan")

        rec: Dict[str, Any] = {
            "idx": int(i),
            "tier": tier,
            "nominal_feasible": bool(nominal_feasible),
            "env_verdict": env_verdict,
            "env_worst_margin": env_worst_margin_f,
            "uq_verdict": uq_verdict,
            "uq_worst_margin": uq_worst_margin_f,
        }
        # include the bound variables for plotting
        if isinstance(row, dict):
            for k in bound_keys:
                if k in row:
                    rec[k] = row.get(k)
        # include objectives
        for k, v in robust_obj.items():
            rec[f"robust_{k}"] = v
        for k, v in degrade.items():
            rec[f"degrade_{k}"] = v

        rows.append(rec)
        point_arts.append({
            "index": int(i),
            "inputs": dict(inp.__dict__),
            "nominal_outputs": dict(out0),
            "phase_envelope": env,
            "uncertainty_contract": uq,
        })

        prog.progress((i + 1) / max(1, len(pareto_pts)))

    artifact = {
        "schema": "robust_pareto.v1",
        "shams_version": (repo_root / "VERSION").read_text(encoding="utf-8").strip() if (repo_root / "VERSION").exists() else "unknown",
        "source": {
            "mode": str(source_mode),
            "objectives": objectives,
            "bounds": last.get("bounds"),
            "seed": last.get("seed"),
            "n_samples": last.get("n_samples"),
        },
        "phase_spec_json": phases_json,
        "uq_spec_json": uq_json,
        "rows": rows,
        "points": point_arts,
    }

    st.session_state["robust_pareto_last"] = artifact
    st.success(f"Robust frontier complete. Points evaluated: {len(rows)}")
    _render_results(artifact)


def _render_results(artifact: Dict[str, Any]) -> None:
    rows = artifact.get("rows") or []
    if not isinstance(rows, list) or not rows:
        st.info("No robust results yet.")
        return
    df = pd.DataFrame(rows)

    st.markdown("#### Robust mix")
    vc = df["tier"].astype(str).value_counts()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ROBUST", int(vc.get("ROBUST", 0)))
    c2.metric("FRAGILE", int(vc.get("FRAGILE", 0)))
    c3.metric("MIRAGE", int(vc.get("MIRAGE", 0)))
    c4.metric("FAIL", int(vc.get("FAIL", 0)))

    # Scatter plot (first two objectives if available)
    objectives = (artifact.get("source") or {}).get("objectives") if isinstance(artifact.get("source"), dict) else {}
    if isinstance(objectives, dict) and len(objectives) >= 2:
        obj_keys = list(objectives.keys())
        xk, yk = obj_keys[0], obj_keys[1]
        rx, ry = f"robust_{xk}", f"robust_{yk}"
        if rx in df.columns and ry in df.columns:
            st.markdown("#### Robust frontier view")
            try:
                import plotly.express as px

                fig = px.scatter(df, x=rx, y=ry, color="tier", hover_data=[c for c in df.columns if c not in {"tier"}])
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass

    st.markdown("#### Robust results table")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Promote a robust-interrogated point back into Point Designer workspace
    try:
        pts = artifact.get("points") or []
        if isinstance(pts, list) and len(pts) > 0:
            st.markdown("#### Promote to 🧭 Point Designer")
            idxs = [int(p.get("index", i)) for i, p in enumerate(pts) if isinstance(p, dict)]
            sel = st.selectbox("Select robust point index", options=idxs, index=0, key="robust_promote_idx")
            if st.button("Promote selected point to 🧭 Point Designer", use_container_width=True, key="robust_promote_btn"):
                pick = None
                for p in pts:
                    if isinstance(p, dict) and int(p.get("index", -9999)) == int(sel):
                        pick = p
                        break
                if isinstance(pick, dict) and isinstance(pick.get("inputs"), dict):
                    st.session_state["pd_candidate_apply"] = dict(pick.get("inputs"))
                    from datetime import datetime
                    st.session_state["last_promotion_event"] = {
                        "source": "📈 Pareto Lab / Robust Pareto Promote",
                        "note": "Selected robust Pareto point",
                        "ts": datetime.now().isoformat(timespec="seconds"),
                    }
                    st.session_state["pd_needs_sync"] = True
                    st.success("Promoted. Open 🧭 Point Designer to evaluate the point.")
    except Exception:
        pass
    st.markdown("#### Export")
    data = json.dumps(artifact, indent=2)
    st.download_button(
        "Download Robust Pareto Artifact (.json)",
        data=data.encode("utf-8"),
        file_name="robust_pareto_artifact.json",
        mime="application/json",
        use_container_width=True,
    )
