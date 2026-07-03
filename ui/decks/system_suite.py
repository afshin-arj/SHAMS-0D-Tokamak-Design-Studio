"""System Suite deck -- extracted from ui/app.py (UI redesign batch 2).

Read-only system-code diagnostics overlaid on the frozen Point Designer truth.
Redesign changes (authorized):
  - 11 top-level tabs collapsed to 6 verdict-first tabs; merged sections are
    preserved as sub-tabs so no content is lost and no scroll wall is created.
  - emojis removed from all labels.
  - repeated metric-column blocks use the shared ``kpi_row`` component and
    "unavailable"/"no data" placeholders use ``empty_state``.

No physics, constraint, solver, evaluator, session-state key, or routing-ID
changes. Widget keys are preserved verbatim. The block runs with app.py's
module globals injected (namespace bridge) so every bare name resolves exactly
as it did inline; this bridge is temporary tech debt to be replaced with
explicit imports/ctx in a later cleanup commit.
"""
from __future__ import annotations
import streamlit as st
import sys


from ._bridge import bridge_deck

def render_system_suite(_app_module) -> None:
    # Namespace bridge: borrow app.py module globals so this extracted block
    # resolves every bare name (st, pd, math, json, REPO_ROOT, render_mode_scope,
    # render_system_suite_header, ...) exactly as it did when it lived inline in
    # app.py. Pure move + authorized UI redesign. To be replaced with explicit
    # dependencies in a later commit.
    bridge_deck(_app_module, globals())

    from ui.components import kpi_row, empty_state

    st.header("System Suite")
    st.caption("System-code diagnostics as *read-only overlays* on the frozen Point Designer truth.")
    render_mode_scope("suite")
    render_system_suite_header(st.session_state)

    # Pull the most recent Point Designer artifact from Streamlit session state.
    # (Do not depend on later-defined internal state helpers; keep this block early-safe.)
    _point_art = st.session_state.get("pd_last_artifact", None)
    if not isinstance(_point_art, dict):
        _point_art = st.session_state.get("last_point_artifact", None)

    _point_inp = None
    _point_out = None
    if isinstance(_point_art, dict):
        _point_inp = _point_art.get("inputs")
        _point_out = _point_art.get("outputs")
    if not isinstance(_point_out, dict):
        _point_out = st.session_state.get("last_point_out", None)
    if not isinstance(_point_inp, dict):
        _point_inp = st.session_state.get("last_point_inp", None)

    if not isinstance(_point_out, dict):
        empty_state("Run **Point Designer** first to populate System Suite diagnostics.", kind="info")
    else:
        try:
            from tools.system_suite import (
                power_closure_overlay,
                trajectory_diagnostics_client,
                lifetime_and_fuel_overlay,
                ops_availability_overlay,
                thermal_network_diagnostics_client,
            )
        except Exception as _e:
            st.error(f"System Suite import failed: {_e}")
            power_closure_overlay = None  # type: ignore
            trajectory_diagnostics_client = None  # type: ignore
            lifetime_and_fuel_overlay = None  # type: ignore
            ops_availability_overlay = None  # type: ignore
            thermal_network_diagnostics_client = None  # type: ignore

        # 11 original tabs collapsed to 6 verdict-first tabs.
        # Merged sections are preserved as sub-tabs (no content loss, no scroll wall).
        t_closure, t_ops, t_life, t_phase, t_prof, t_aux = st.tabs([
            "Closure & Power",
            "Ops · Thermal · Trajectory",
            "Lifetime · Fuel · Regimes",
            "Phase Envelopes",
            "Profile Contracts",
            "Authority · Exports · UQ",
        ])

        # ---- Tab 1: Closure & Power (was "Closure Ledger") -----------------
        with t_closure:
            st.subheader("Closure Ledger")
            if power_closure_overlay is None:
                empty_state("Power closure overlay unavailable.", kind="warning")
            else:
                rep = power_closure_overlay(_point_out, _point_inp if isinstance(_point_inp, dict) else None)
                kpi_row([
                    ("Gross electric (MW)", f"{rep.Pe_gross_MW:.2f}" if math.isfinite(rep.Pe_gross_MW) else "-"),
                    ("Recirc (MW)", f"{rep.Precirc_MW:.2f}" if math.isfinite(rep.Precirc_MW) else "-"),
                    ("Net electric (MW)", f"{rep.Pe_net_MW:.2f}" if math.isfinite(rep.Pe_net_MW) else "-"),
                    ("Recirc fraction", f"{100.0*rep.recirc_frac:.1f}%" if math.isfinite(rep.recirc_frac) else "-"),
                ])
                st.caption(f"Stamp: {rep.stamp_sha256[:12]}…")
                with st.expander("Breakdown (diagnostic)", expanded=False):
                    st.json(rep.breakdown, expanded=False)

        # ---- Tab 2: Ops · Thermal · Trajectory (was "Ops & Thermal" + "Trajectory Lab")
        with t_ops:
            st.subheader("Operations, Thermal & Trajectory")
            st.caption("System operations overlays (duty cycle, availability), thermal envelope diagnostics, and pulse-envelope trajectory. Read-only.")
            t_ops_duty, t_ops_therm, t_ops_traj = st.tabs(["Duty & Availability", "Thermal Network", "Trajectory Lab"])

            with t_ops_duty:
                if ops_availability_overlay is None:
                    empty_state("Operations overlay unavailable.", kind="warning")
                else:
                    # Expert-friendly: user-controlled availability, with deterministic defaults shown.
                    default_av = None
                    av = st.slider("Availability (fraction)", 0.0, 1.0, 0.75, 0.01, key="ops_availability_slider_v253")
                    rep = ops_availability_overlay(_point_out, _point_inp if isinstance(_point_inp, dict) else None, availability=float(av))
                    kpi_row([
                        ("Duty cycle", f"{100.0*rep.duty_cycle:.1f}%"),
                        ("Availability", f"{100.0*rep.availability:.1f}%"),
                        ("Avg delivered (MW)", f"{rep.avg_delivered_MW:.2f}"),
                        ("Annual energy (GWh)", f"{rep.annual_energy_GWh:.1f}"),
                    ])
                    st.caption(f"Stamp: {rep.stamp_sha256[:12]}…")
                    with st.expander("Breakdown (diagnostic)", expanded=False):
                        st.json(rep.breakdown, expanded=False)

            with t_ops_therm:
                if thermal_network_diagnostics_client is None:
                    empty_state("Thermal diagnostics unavailable.", kind="warning")
                else:
                    tr = thermal_network_diagnostics_client(_point_out, _point_inp if isinstance(_point_inp, dict) else None)
                    st.caption(f"Stamp: {tr.stamp_sha256[:12]}…")
                    df = pd.DataFrame({"t_s": tr.t_s})
                    for k, v in tr.nodes_K.items():
                        df[f"T_{k}_K"] = v
                    st.line_chart(df, x="t_s", y=[c for c in df.columns if c != "t_s"], height=220)
                    if tr.violations:
                        st.error("Thermal violations detected (diagnostic).")
                        st.dataframe(pd.DataFrame(tr.violations), use_container_width=True, hide_index=True)
                    else:
                        st.success("No thermal violations detected (within available limits).")
                    with st.expander("Thermal meta", expanded=False):
                        st.json(tr.meta, expanded=False)

            with t_ops_traj:
                st.caption("Deterministic envelope trajectory diagnostic (not a control solver).")
                if trajectory_diagnostics_client is None:
                    empty_state("Trajectory diagnostics unavailable.", kind="warning")
                else:
                    tr = trajectory_diagnostics_client(_point_out, _point_inp if isinstance(_point_inp, dict) else None)
                    kpi_row([
                        ("Net peak (MW)", f"{tr.meta.get('Pnet_peak_MW', 0.0):.2f}"),
                        ("Net avg (MW)", f"{tr.meta.get('Pnet_avg_MW', 0.0):.2f}"),
                        ("Recirc peak (MW)", f"{tr.meta.get('Precirc_peak_MW', 0.0):.2f}"),
                        ("Recirc energy (MJ)", f"{tr.meta.get('Erecirc_MJ', 0.0):.1f}"),
                    ])
                    st.caption(f"Stamp: {tr.stamp_sha256[:12]}…")
                    df_tr = pd.DataFrame({"t_s": tr.t_s, "P_net_MW": tr.Pe_net_MW, "P_recirc_MW": tr.Precirc_MW})
                    st.line_chart(df_tr, x="t_s", y=["P_net_MW", "P_recirc_MW"], height=220)

                    if tr.violations:
                        st.error("Trajectory violations detected (diagnostic).")
                        st.dataframe(pd.DataFrame(tr.violations), use_container_width=True, hide_index=True)
                    else:
                        st.success("No trajectory violations detected (within available limits).")

        # ---- Tab 3: Lifetime · Fuel · Regimes (was "Lifetime & Fuel" + "Regime Transitions")
        with t_life:
            t_life_lf, t_life_reg = st.tabs(["Lifetime & Fuel", "Regime Transitions"])

            with t_life_lf:
                st.subheader("Lifetime & Fuel")
                st.caption("Static feasibility overlays: lifetime budgets, pulsed fatigue proxy, and tritium closure.")
                if lifetime_and_fuel_overlay is None:
                    empty_state("Lifetime/fuel overlay unavailable.", kind="warning")
                else:
                    lr = lifetime_and_fuel_overlay(_point_out, _point_inp if isinstance(_point_inp, dict) else None)
                    kpi_row([
                        ("FW dpa/yr", f"{lr.fw_dpa_per_year:.2f}" if math.isfinite(lr.fw_dpa_per_year) else "-"),
                        ("FW dpa max", f"{lr.fw_dpa_max_per_year:.2f}" if math.isfinite(lr.fw_dpa_max_per_year) else "-"),
                        ("FW margin", f"{lr.fw_dpa_margin:.2f}" if math.isfinite(lr.fw_dpa_margin) else "-"),
                    ])
                    kpi_row([
                        ("Cycles/yr", f"{lr.cycles_per_year:.0f}" if math.isfinite(lr.cycles_per_year) else "-"),
                        ("Cycles max", f"{lr.cycles_max:.0f}" if math.isfinite(lr.cycles_max) else "-"),
                        ("Cycle margin", f"{lr.cycles_margin:.2f}" if math.isfinite(lr.cycles_margin) else "-"),
                    ])
                    kpi_row([
                        ("TBR", f"{lr.tbr:.3f}" if math.isfinite(lr.tbr) else "-"),
                        ("TBR min", f"{lr.tbr_min:.3f}" if math.isfinite(lr.tbr_min) else "-"),
                        ("TBR margin", f"{lr.tbr_margin:.3f}" if math.isfinite(lr.tbr_margin) else "-"),
                    ])

                    st.caption(f"Stamp: {lr.stamp_sha256[:12]}…")
                    with st.expander("Raw overlay JSON", expanded=False):
                        st.json({"fw": {"dpa_per_year": lr.fw_dpa_per_year, "dpa_max": lr.fw_dpa_max_per_year, "margin": lr.fw_dpa_margin},
                                 "cycles": {"per_year": lr.cycles_per_year, "max": lr.cycles_max, "margin": lr.cycles_margin},
                                 "tbr": {"tbr": lr.tbr, "min": lr.tbr_min, "margin": lr.tbr_margin},
                                 "stamp": lr.stamp_sha256}, expanded=False)

            with t_life_reg:
                st.subheader("Regime Transitions")
                st.caption("Deterministic labels and near-boundary flags derived from the last Point Designer artifact. Read-only.")

                _rt = None
                if isinstance(_point_art, dict):
                    _rt = _point_art.get("regime_transitions")
                if not isinstance(_rt, dict):
                    try:
                        from src.analysis.regime_transition_detector_v353 import evaluate_regime_transitions
                    except Exception:
                        try:
                            from analysis.regime_transition_detector_v353 import evaluate_regime_transitions  # type: ignore
                        except Exception:
                            evaluate_regime_transitions = None  # type: ignore
                    if evaluate_regime_transitions is not None:
                        try:
                            _rt = evaluate_regime_transitions(
                                inputs=_point_inp if isinstance(_point_inp, dict) else {},
                                outputs=_point_out if isinstance(_point_out, dict) else {},
                            )
                        except Exception:
                            _rt = None

                if not isinstance(_rt, dict):
                    empty_state("Regime transition detector unavailable.", kind="warning")
                else:
                    st.info(str(_rt.get("regime_summary", "")) or "")
                    labels = _rt.get("labels", {}) if isinstance(_rt.get("labels"), dict) else {}
                    kpi_row([
                        ("Confinement", str(labels.get("confinement_regime", "-"))),
                        ("Exhaust", str(labels.get("exhaust_regime", "-"))),
                        ("Magnet", str(labels.get("magnet_regime", "-"))),
                        ("Greenwald", str(labels.get("greenwald_state", "-"))),
                        ("βN", str(labels.get("betaN_state", "-"))),
                    ])

                    with st.expander("Near-boundary flags", expanded=False):
                        st.json(_rt.get("near_boundaries", []), expanded=False)
                    with st.expander("Detector context", expanded=False):
                        st.json(_rt.get("context", {}), expanded=False)

        # ---- Tab 4: Phase Envelopes (kept) ---------------------------------
        with t_phase:
            st.subheader("Phase Envelopes")
            st.caption("Outer-loop quasi-static phases evaluated against the frozen truth. Worst-phase determines verdict.")
            try:
                from ui.phase_envelopes import render_phase_envelopes_panel
                render_phase_envelopes_panel(
                    REPO_ROOT,
                    point_artifact=_point_art if isinstance(_point_art, dict) else None,
                    ui_key_prefix="pd_phase_env",
                )
            except Exception as _e:
                st.error(f"Phase Envelopes panel import failed: {_e}")

        # ---- Tab 5: Profile Contracts (kept) -------------------------------
        with t_prof:
            st.subheader("Profile Contracts 2.0")
            st.caption("Robust vs optimistic feasibility under certified profile/transport envelopes (finite corners).")
            render_mode_scope("profile_contracts")

            try:
                from src.analysis.profile_contracts_v362 import evaluate_profile_contracts_v362
            except Exception:
                try:
                    from analysis.profile_contracts_v362 import evaluate_profile_contracts_v362  # type: ignore
                except Exception:
                    evaluate_profile_contracts_v362 = None  # type: ignore

            if evaluate_profile_contracts_v362 is None:
                empty_state("Profile Contracts module unavailable.", kind="error")
            elif not isinstance(_point_inp, dict):
                empty_state("Run **Point Designer** first (inputs required).", kind="info")
            else:
                try:
                    from src.models.inputs import PointInputs
                except Exception:
                    from models.inputs import PointInputs  # type: ignore

                c1, c2, c3 = st.columns(3)
                preset = c1.selectbox("Corner preset", ["C8", "C16", "C32"], index=0, key="pc_preset_v362")
                tier = c2.selectbox("Contract tier", ["both", "optimistic", "robust"], index=0, key="pc_tier_v362")
                include_disabled = c3.checkbox(
                    "Force-enable v358 profile family", value=False, key="pc_force_enable_v358_v362"
                )

                st.caption("Tip: robust-feasible implies envelope-certified; optimistic-feasible but robust-infeasible is a MIRAGE.")

                run_btn = st.button("Run Profile Contracts", key="pc_run_v362")
                if run_btn:
                    # Ensure profile family library is active if user requests.
                    d = dict(_point_inp)
                    if include_disabled:
                        d["include_profile_family_v358"] = True
                    inp = PointInputs.from_dict(d)
                    rep = evaluate_profile_contracts_v362(inp, preset=str(preset), tier=str(tier))
                    rep_d = rep.to_dict()
                    st.session_state["profile_contracts_v362_last"] = rep_d

                rep_d = st.session_state.get("profile_contracts_v362_last", None)
                if isinstance(rep_d, dict):
                    v_rob = bool(rep_d.get("robust_feasible"))
                    v_opt = bool(rep_d.get("optimistic_feasible"))
                    mir = bool(rep_d.get("mirage"))

                    kpi_row([
                        ("Optimistic feasible", "YES" if v_opt else "NO"),
                        ("Robust feasible", "YES" if v_rob else "NO"),
                        ("MIRAGE", "YES" if mir else "NO"),
                        ("Corners", str(rep_d.get("corner_count", "-"))),
                    ])

                    st.caption(f"Contract SHA-256: {str(rep_d.get('contract_sha256',''))[:12]}… | Run fingerprint: {str(rep_d.get('run_fingerprint_sha256',''))[:12]}…")

                    with st.expander("Summary", expanded=False):
                        st.json(rep_d.get("summary", {}), expanded=False)

                    with st.expander("Corners (expandable)", expanded=False):
                        # Light table: omit heavy constraints payload by default.
                        rows = []
                        for c in rep_d.get("corners", []) or []:
                            if not isinstance(c, dict):
                                continue
                            rows.append({
                                "tier": c.get("tier"),
                                "corner": c.get("corner_index"),
                                "hard_feasible": c.get("hard_feasible"),
                                "min_margin_frac": c.get("min_margin_frac"),
                                **{f"ax_{k}": v for k, v in (c.get("axes") or {}).items()},
                            })
                        try:
                            st.dataframe(rows, use_container_width=True)
                        except Exception:
                            st.json(rows, expanded=False)

                    with st.expander("Full report JSON", expanded=False):
                        st.json(rep_d, expanded=False)

                    # Optional ZIP export (deterministic)
                    try:
                        from tools.profile_contracts_v362 import export_profile_contracts_zip
                        from pathlib import Path
                        import tempfile
                        if st.button("Export Profile Contracts ZIP", key="pc_export_zip_v362"):
                            td = Path(tempfile.gettempdir()) / "shams_profile_contracts"
                            td.mkdir(parents=True, exist_ok=True)
                            out_zip = td / "profile_contracts_v362_report.zip"
                            export_profile_contracts_zip(rep_d, out_zip)
                            st.download_button(
                                "Download ZIP",
                                data=out_zip.read_bytes(),
                                file_name="profile_contracts_v362_report.zip",
                                mime="application/zip",
                                key="pc_dl_zip_v362",
                            )
                    except Exception:
                        pass

        # ---- Tab 6: Authority · Exports · UQ (was Authority Vault + Campaign Pack + Parity + UQ)
        with t_aux:
            t_aux_auth, t_aux_camp, t_aux_par, t_aux_uq = st.tabs([
                "Authority Vault", "Campaign Pack", "Benchmark & Parity", "Uncertainty Contracts",
            ])

            with t_aux_auth:
                st.subheader("Authority Vault")
                st.caption("Deterministic, versioned scenario libraries. These affect *robustness screening* only.")
                try:
                    from tools.scenario_library import preset_names, get_preset
                    presets = preset_names()
                    sel = st.selectbox("Scenario preset", ["(select)"] + presets, index=0, key="system_suite_scen_preset_v250")
                    if sel != "(select)":
                        st.code(json.dumps(get_preset(sel), indent=2, sort_keys=True), language="json")
                except Exception as _e:
                    st.warning(f"Scenario library unavailable: {_e}")

                with st.expander("Authority ladder (policy)", expanded=False):
                    st.markdown(
                        """
                        **Proxy** → conservative screening models\
                        **Parametric** → PROCESS-style regressions/closures\
                        **External (hashed)** → imported authoritative results with SHA-256 stamping\

                        SHAMS rule: *authority changes never modify feasibility truth silently; they are stamped and visible.*
                        """
                    )

            with t_aux_camp:
                st.subheader("Campaign Pack")
                st.caption("Deterministic campaign exports for external optimizers (firewalled).")
                render_mode_scope("campaign_pack")

                try:
                    from tools.campaign_pack_v363 import render_campaign_pack_panel
                except Exception as _e:
                    render_campaign_pack_panel = None  # type: ignore
                    st.error(f"Campaign Pack import failed: {_e}")

                if render_campaign_pack_panel is None:
                    empty_state("Campaign Pack panel unavailable.", kind="info")
                else:
                    render_campaign_pack_panel(
                        repo_root=REPO_ROOT,
                        point_inputs=_point_inp if isinstance(_point_inp, dict) else None,
                    )

            with t_aux_par:
                st.subheader("Benchmark & Parity Harness 3.0")
                st.caption("Deterministic parity study harness. PROCESS results are optional user-supplied references.")
                render_mode_scope("parity_harness")
                try:
                    from tools.benchmark_parity_harness_v364 import render_benchmark_parity_harness_v364
                except Exception as _e:
                    render_benchmark_parity_harness_v364 = None  # type: ignore
                    st.warning(f"Parity harness unavailable: {_e}")
                if render_benchmark_parity_harness_v364 is None:
                    empty_state("Parity harness module not available.", kind="info")
                else:
                    render_benchmark_parity_harness_v364()

            with t_aux_uq:
                st.subheader("Uncertainty Contracts")
                st.caption("Outer-loop deterministic interval corners (2^N). Verdict: ROBUST_PASS / FRAGILE / FAIL.")
                try:
                    from ui.uncertainty_contracts import render_uncertainty_contracts_panel
                    render_uncertainty_contracts_panel(
                        REPO_ROOT,
                        point_artifact=_point_art if isinstance(_point_art, dict) else None,
                        ui_key_prefix="pd_uq_contracts",
                    )
                except Exception as _e:
                    st.error(f"Uncertainty Contracts panel import failed: {_e}")
