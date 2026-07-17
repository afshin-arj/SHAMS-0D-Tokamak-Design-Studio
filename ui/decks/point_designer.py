"""Point Designer deck -- extracted from ui/app.py (UI redesign batch 1).

Pure move: no logic change. The block runs with app.py module globals injected
so every bare name resolves exactly as it did inline. This namespace bridge is
temporary tech debt; it will be replaced with explicit imports/ctx in a later
cleanup commit. No physics, constraint, solver, evaluator, or golden changes.
"""
from __future__ import annotations

try:
    from ui.point_inputs_factory import (
        make_point_inputs,
        make_point_inputs_from,
        strip_point_input_knob_dupes,
    )
except ImportError:
    from point_inputs_factory import (
        make_point_inputs,
        make_point_inputs_from,
        strip_point_input_knob_dupes,
    )

from ._bridge import bridge_deck

def render_point_designer(_app_module) -> None:
    # Namespace bridge: borrow app.py module globals so this extracted block
    # resolves every bare name (st, pd, PD_KEYS, _num, REPO_ROOT, helpers, ...)
    # exactly as it did when it lived inline in app.py. Pure move, no behavior
    # change. To be replaced with explicit dependencies in a later commit.
    bridge_deck(_app_module, globals())
    # Verdict-first (UI redesign): hero strip renders above the fold before any
    # mode-contract copy. Frozen-truth info + mode contract are collapsed into an
    # "About this mode"expander below the sub-deck selector.
    render_point_designer_hero(st.session_state)

    # Studio default entry (Independence 3.4) — Streamlit parity of the NiceGUI
    # landing card: what SHAMS answers, NO-SOLUTION as first-class, onboarding docs.
    if st.session_state.get("last_point_out") is None:
        with st.expander("Start a systems study (getting started)", expanded=False):
            st.markdown(
                "Evaluate one operating point under frozen truth and read the certified "
                "verdict — feasible with margins, or **NO-SOLUTION** with the mechanism "
                "that blocks it. NO-SOLUTION is a first-class result, not an error.\n\n"
                "**What SHAMS answers**\n"
                "- Is this design admissible under the declared hard constraints?\n"
                "- Why did it fail — which mechanism and constraint dominate?\n"
                "- What breaks first under uncertainty?\n"
                "- Can I cite and reproduce this verdict without trusting an optimization path?\n\n"
                "**Starting points**\n"
                "- Champion templates (one-click load) live in the NiceGUI studio "
                "(`run_ui_nicegui.cmd` → Point Designer entry card) or via CLI: "
                "`python benchmarks/champions/run_champions.py` — see `docs/CHAMPION_CASES.md`.\n"
                "- Migrating from PROCESS? See `docs/PROCESS_TO_SHAMS_MIGRATION_GUIDE.md` "
                "(IN.DAT → PointInputs, MFILE → artifacts, propose-only optimizers).\n"
                "- Cite `VERSION` + artifact SHA-256 for any published verdict."
            )

    # Point Designer deck selector (v280+): Truth Console vs outer-loop envelopes/contracts.
    _pd_deck = st.radio(
        "Point Designer deck",
        ["Truth Console", "Phase Envelopes", "Uncertainty Contracts"],
        index=0,
        horizontal=True,
        help="Truth Console runs the frozen single-point evaluator. Phase Envelopes and Uncertainty Contracts are outer-loop diagnostics only (no solver, no dynamics).",
    )
    if _pd_deck != "Truth Console":
        _pd_art = st.session_state.get("pd_last_artifact", None)
        if not isinstance(_pd_art, dict):
            _pd_art = st.session_state.get("last_point_artifact", None)
        if _pd_deck == "Phase Envelopes":
            try:
                from ui.phase_envelopes import render_phase_envelopes_panel
                render_phase_envelopes_panel(
                    REPO_ROOT,
                    point_artifact=_pd_art,
                    ui_key_prefix="truth_phase_env",
                )
            except Exception as _e:
                st.error(f"Phase Envelopes panel import failed: {_e}")
        else:
            try:
                from ui.uncertainty_contracts import render_uncertainty_contracts_panel
                render_uncertainty_contracts_panel(
                    REPO_ROOT,
                    point_artifact=_pd_art,
                    ui_key_prefix="truth_uq_contracts",
                )
            except Exception as _e:
                st.error(f"Uncertainty Contracts panel import failed: {_e}")
        st.stop()


    with st.expander("About this mode", expanded=False):
        st.info(
            "**Point Designer is frozen** - It evaluates a single operating point in a constraint-authoritative, assumption-explicit 0‑D framework. "
            "No optimization, relaxation, or exploration occurs here. Exploration is performed in **Systems Mode**, which calls Point Designer as a fixed evaluator.",
        )
        st.markdown("#### Truth Console - mode contract (is / is not)")
        cA, cB = st.columns(2)
        with cA:
            st.markdown("""**What this mode does**
- Evaluates a single operating point using the frozen 0‑D evaluator
- Reports pass/fail margins and transparent intermediate outputs
- Produces reproducible, audit-ready artifacts""")
        with cB:
            st.markdown("""**What this mode does not do**
- Optimize, relax, or search for feasibility
- Suggest parameter changes or apply designs
- Modify physics, constraints, or policy""")
        st.caption("Provenance (read-only metadata for audits and screenshots).")
        st.write({"software": APP_NAME, "version": str(st.session_state.get("shams_version","unknown")), "author": APP_AUTHOR})

    tab_cfg, tab_tel, tab_con = st.tabs(["Configure", "Telemetry", "Constraints"])

    # IMPORTANT: Streamlit tabs are lazily executed; variables defined inside one tab
    # are NOT guaranteed to exist when another tab is selected. Keep shared flags
    # defined here at the parent scope.
    run_btn = False  # (global PD run button state)

    # Use the latest loaded preset / last point as the UI default for Point Designer.
    # This makes preset loads robust even if widget state keys change or are newly created.
    _base_pd = st.session_state.get("last_point_inp")
    # UI stability hardening: session state may contain a raw dict (e.g., legacy
    # cache formats or template imports). Normalize to PointInputs deterministically.
    if isinstance(_base_pd, dict):
        try:
            _pi_fields = {f.name for f in fields(PointInputs)}
            _base_pd = PointInputs(**{k: v for k, v in _base_pd.items() if k in _pi_fields})
            st.session_state["last_point_inp"] = _base_pd
        except Exception:
            _base_pd = None
    if _base_pd is None:
        _base_pd = PointInputs(R0_m=1.81, a_m=0.62, kappa=1.8, Bt_T=10.0, Ip_MA=8.0, Ti_keV=10.0, fG=0.8, Paux_MW=50.0)
        st.session_state["last_point_inp"] = _base_pd

    with tab_cfg:
        try:
            render_overlay_authority_dashboard(
                st.session_state,
                widget_key_prefix="pd_auth",
                design_intent=str(st.session_state.get("design_intent", "Power Reactor (net-electric)")),
            )
        except Exception:
            pass
        st.subheader("Control Deck")
        if st.button("New machine (clear Point Designer)", use_container_width=True, help="Clear Point Designer outputs/tables/plots so you can start a new machine."):
            for k in [
                "pd_last_artifact","pd_last_outputs","pd_last_radial_png_bytes","pd_last_log_lines","pd_last_run_ts","pd_last_inputs_hash",
                "last_point_out","last_point_inp","last_solver_log",
            ]:
                st.session_state.pop(k, None)
            st.rerun()

        with st.expander("Industrial scenario templates", expanded=False):
            st.caption("Deterministic intent templates that set *PointInputs defaults* (no optimization, no solvers).")
            try:
                from tools.industrial_scenario_templates_v354 import template_names, get_template_payload, get_template
                _tmpl_names = template_names()
                _sel_tmpl = st.selectbox("Industrial scenario template", ["(select)"] + _tmpl_names, index=0, key="pd_industrial_template_v354")
                if _sel_tmpl != "(select)":
                    _payload = get_template_payload(_sel_tmpl)
                    st.code(json.dumps(_payload, indent=2, sort_keys=True), language="json")
                    if st.button("Load template into Point Designer", use_container_width=True, key="pd_load_industrial_template_btn_v354"):
                        # Clear prior outputs and set a new base point for widget defaults.
                        for k in [
                            "pd_last_artifact","pd_last_outputs","pd_last_radial_png_bytes","pd_last_log_lines","pd_last_run_ts","pd_last_inputs_hash",
                            "last_point_out","last_point_inp","last_solver_log",
                        ]:
                            st.session_state.pop(k, None)
                        _ov = get_template(_sel_tmpl)
                        try:
                            _base = asdict(_base_pd) if _base_pd is not None else {}
                            _base.update({k: v for k, v in _ov.items() if k in _base})
                            st.session_state["last_point_inp"] = PointInputs(**_base)
                        except Exception:
                            # Fallback: apply only required keys
                            st.session_state["last_point_inp"] = PointInputs(**{**{
                                "R0_m": float(_ov.get("R0_m", 1.81)),
                                "a_m": float(_ov.get("a_m", 0.62)),
                                "kappa": float(_ov.get("kappa", 1.8)),
                                "Bt_T": float(_ov.get("Bt_T", 10.0)),
                                "Ip_MA": float(_ov.get("Ip_MA", 8.0)),
                                "Ti_keV": float(_ov.get("Ti_keV", 10.0)),
                                "fG": float(_ov.get("fG", 0.8)),
                                "Paux_MW": float(_ov.get("Paux_MW", 50.0)),
                            }, **{k:v for k,v in _ov.items() if k not in ("R0_m","a_m","kappa","Bt_T","Ip_MA","Ti_keV","fG","Paux_MW")}})
                        st.session_state["pd_loaded_template_name"] = str(_sel_tmpl)
                        st.rerun()
            except Exception as _e:
                st.warning(f"Scenario template library unavailable: {_e}")

        with st.expander("Plasma & geometry", expanded=False):
            R0 = _num("Major radius R₀ (m)", float(_base_pd.R0_m), 0.01, help="Distance from tokamak centerline to plasma magnetic axis (major radius).", key=PD_KEYS["R0_m"])
            a = _num("Minor radius a (m)", float(_base_pd.a_m), 0.01, min_value=0.1, help="Plasma minor radius (a). Together with R₀ sets aspect ratio.", key=PD_KEYS["a_m"])
            kappa = _num("Elongation κ (–)", float(_base_pd.kappa), 0.05, min_value=1.0, max_value=3.2, help="Plasma elongation κ. Used in volume/area and stability proxies.", key=PD_KEYS["kappa"])
            delta = _num("Triangularity δ (–)", float(getattr(_base_pd, "delta", 0.0) or 0.0), 0.02, min_value=0.0, max_value=0.8, help="Triangularity δ. Used only in the transparent inboard radial-build clearance proxy (stack closure). Default 0.0 preserves legacy behavior.", key=PD_KEYS["delta"])
            B0 = _num("Toroidal field on axis B₀ (T)", float(_base_pd.Bt_T), 0.1, min_value=0.5, max_value=25.0, help="Toroidal field at plasma axis (B₀). Drives confinement and magnet sizing.", key=PD_KEYS["Bt_T"])
            Ti = _num("Ion temperature Tᵢ (keV)", float(_base_pd.Ti_keV), 0.25, min_value=1.0, max_value=40.0, help="Core ion temperature proxy. Drives fusion reactivity and stored energy.", key=PD_KEYS["Ti_keV"])
            Ti_over_Te = _num("Ion-to-electron temperature ratio Tᵢ/Tₑ (–)", float(getattr(_base_pd, "Ti_over_Te", 1.0)), 0.1, min_value=0.5, help="Assumed ratio Tᵢ/Tₑ; sets electron temperature for radiation estimate.", key=PD_KEYS["Ti_over_Te"])

        with st.expander("TF magnets & technology", expanded=False):
                tech_opts = [
                    "HTS_REBCO",
                    "LTS_NB3SN",
                    "LTS_NBTI",
                    "COPPER",
                ]
                _base_tech = str(getattr(_base_pd, "magnet_technology", "HTS_REBCO") or "HTS_REBCO").strip().upper()
                if _base_tech not in tech_opts:
                    _base_tech = "HTS_REBCO"
                tech = st.selectbox(
                    "TF technology (tech-axis)",
                    options=tech_opts,
                    index=tech_opts.index(_base_tech),
                    key=PD_KEYS["magnet_technology"],
                    help=(
                        "Select the TF magnet technology. This controls the superconducting critical-surface margin proxy "
                        "(or disables it for copper) and is recorded in artifacts for reviewer traceability."
                    ),
                )
                Tcoil = _num(
                    "TF coil temperature T_coil (K)",
                    float(getattr(_base_pd, "Tcoil_K", 20.0)),
                    0.5,
                    min_value=3.5,
                    max_value=350.0,
                    help=(
                        "Operating temperature for the TF conductor. Typical anchors: ~4.2–4.5 K for NbTi/Nb3Sn, "
                        "~20 K for REBCO screening, ~300 K for copper (resistive)."
                    ),
                    key=PD_KEYS["Tcoil_K"],
                )

                with st.expander("Magnet technology authority — explicit ledger caps", expanded=False):
                    include_magnet_technology_authority_v400 = st.checkbox(
                        "Enable magnet margin ledger overlay",
                        value=bool(getattr(_base_pd, "include_magnet_technology_authority_v400", True)),
                        key=PD_KEYS["include_magnet_technology_authority_v400"],
                        help="Governance-only: computes explicit B/J/stress/SC/T-window (and Cu ohmic) margin ledger; does not mutate truth.",
                    )
                    st.caption("Optional explicit caps (set NaN to disable each). All are feasibility-first constraints when finite.")
                    magnet_margin_min_v400 = _num(
                        "Combined magnet margin min",
                        float(getattr(_base_pd, "magnet_margin_min_v400", float("nan"))),
                        0.01,
                        min_value=-2.0,
                        max_value=5.0,
                        key=PD_KEYS["magnet_margin_min_v400"],
                    )
                    b_margin_min_v400 = _num(
                        "B margin min: B_allow/B_peak - 1",
                        float(getattr(_base_pd, "b_margin_min_v400", float("nan"))),
                        0.01,
                        min_value=-2.0,
                        max_value=5.0,
                        key=PD_KEYS["b_margin_min_v400"],
                    )
                    j_margin_min_v400 = _num(
                        "J margin min: J_allow/J_req - 1",
                        float(getattr(_base_pd, "j_margin_min_v400", float("nan"))),
                        0.01,
                        min_value=-2.0,
                        max_value=5.0,
                        key=PD_KEYS["j_margin_min_v400"],
                    )
                    stress_margin_min_v400 = _num(
                        "Stress margin min: sigma_allow/sigma - 1",
                        float(getattr(_base_pd, "stress_margin_min_v400", float("nan"))),
                        0.01,
                        min_value=-2.0,
                        max_value=5.0,
                        key=PD_KEYS["stress_margin_min_v400"],
                    )
                    sc_margin_min_v400 = _num(
                        "SC operating margin min: (sc_margin/sc_min)-1",
                        float(getattr(_base_pd, "sc_margin_min_v400", float("nan"))),
                        0.01,
                        min_value=-2.0,
                        max_value=5.0,
                        key=PD_KEYS["sc_margin_min_v400"],
                    )
                    t_margin_min_v400 = _num(
                        "T-window margin min",
                        float(getattr(_base_pd, "t_margin_min_v400", float("nan"))),
                        0.01,
                        min_value=-2.0,
                        max_value=5.0,
                        key=PD_KEYS["t_margin_min_v400"],
                    )
                    p_tf_ohmic_margin_min_v400 = _num(
                        "Cu ohmic power margin min: P_max/P_ohmic - 1",
                        float(getattr(_base_pd, "p_tf_ohmic_margin_min_v400", float("nan"))),
                        0.01,
                        min_value=-2.0,
                        max_value=5.0,
                        key=PD_KEYS["p_tf_ohmic_margin_min_v400"],
                    )
        with st.expander("Model options (transparent (systems-code-inspired))", expanded=False):
                confinement_scaling_label = st.selectbox(
                    "H-factor reference scaling (for H_scaling)",
                    options=[
                        "IPB98(y,2) (H98 basis)",
                        "ITER89-P (L-mode)",
                        "Kaye–Goldston (L-mode)",
                        "Neo-Alcator (ohmic/L)",
                        "Mirnov (ohmic)",
                        "Shimomura (L-mode)",
                    ],
                    index=0,
                    help=(
                        "Controls the reference scaling used for the reported H_scaling = tauE_eff / tauScaling. "
                        "H98 remains defined relative to IPB98(y,2)."
                    ),
                )
                confinement_scaling_map = {
                    "IPB98(y,2) (H98 basis)": "IPB98y2",
                    "ITER89-P (L-mode)": "ITER89P",
                    "Kaye–Goldston (L-mode)": "KG",
                    "Neo-Alcator (ohmic/L)": "NEOALC",
                    "Mirnov (ohmic)": "MIRNOV",
                    "Shimomura (L-mode)": "SHIMOMURA",
                }
                confinement_scaling = confinement_scaling_map.get(confinement_scaling_label, "IPB98y2")

                # -----------------------------------------------------------------
                # v371.0: Transport contract library (governance-only)
                # -----------------------------------------------------------------
                with st.expander("Transport feasibility contracts", expanded=False):
                    include_transport_contracts_v371 = st.checkbox(
                        "Enable transport contract diagnostics",
                        value=bool(getattr(_base_pd, "include_transport_contracts_v371", False)),
                        key=PD_KEYS["include_transport_contracts_v371"],
                        help=(
                            "Regime-conditioned confinement-scaling envelope + explicit optimistic/robust caps on required confinement (H_required). "
                            "Governance-only: does not change frozen truth unless you set caps as constraints."
                        ),
                    )
                    _hopt_base = getattr(_base_pd, "H_required_max_optimistic", float("nan"))
                    _hrob_base = getattr(_base_pd, "H_required_max_robust", float("nan"))
                    cH1, cH2 = st.columns(2)
                    with cH1:
                        H_required_max_optimistic = st.number_input(
                            "H_required max (optimistic)",
                            min_value=0.5,
                            max_value=5.0,
                            value=float(_hopt_base) if (float(_hopt_base)==float(_hopt_base) and float(_hopt_base)>0) else 2.0,
                            step=0.05,
                            key=PD_KEYS["H_required_max_optimistic"],
                            disabled=not include_transport_contracts_v371,
                            help="If enabled, enforces H_required ≤ this cap (optimistic).",
                        )
                    with cH2:
                        H_required_max_robust = st.number_input(
                            "H_required max (robust)",
                            min_value=0.5,
                            max_value=5.0,
                            value=float(_hrob_base) if (float(_hrob_base)==float(_hrob_base) and float(_hrob_base)>0) else 1.5,
                            step=0.05,
                            key=PD_KEYS["H_required_max_robust"],
                            disabled=not include_transport_contracts_v371,
                            help="If enabled, enforces H_required ≤ this tighter cap (robust).",
                        )
                    st.caption("These caps are explicit constraints (no smoothing): if set, infeasible points are reported as transport-limited.")


                # -----------------------------------------------------------------
                # v396.0: Transport Envelope 2.0 (governance-only)
                # -----------------------------------------------------------------
                with st.expander("Multi-scaling confinement envelope", expanded=False):
                    include_transport_envelope_v396 = st.checkbox(
                        "Enable multi-scaling confinement envelope diagnostics",
                        value=bool(getattr(_base_pd, "include_transport_envelope_v396", True)),
                        key=PD_KEYS["include_transport_envelope_v396"],
                        help=(
                            "Computes τE envelope over IPB98(y,2) and ITER89-P (and optional user scaling), "
                            "then reports spread ratio and a deterministic credibility tier. "
                            "Governance-only: does not change frozen truth unless you set a spread cap as a constraint."
                        ),
                    )

                    _spread_base = getattr(_base_pd, "transport_spread_max_v396", float("nan"))
                    transport_spread_max_v396 = st.number_input(
                        "Max transport spread ratio (tauE_max/tauE_min) [optional constraint]",
                        min_value=1.0,
                        max_value=20.0,
                        value=float(_spread_base) if (float(_spread_base)==float(_spread_base) and float(_spread_base)>0) else 4.0,
                        step=0.1,
                        key=PD_KEYS["transport_spread_max_v396"],
                        disabled=not include_transport_envelope_v396,
                        help="If set (finite), enforces tauE_max/tauE_min ≤ cap as an explicit feasibility constraint.",
                    )
                    st.caption("Set to NaN in advanced inputs to disable as a feasibility constraint (diagnostics still computed).")

                    st.divider()
                    include_tauE_user_scaling_v396 = st.checkbox(
                        "Include user scaling vector (generic power-law) [optional]",
                        value=bool(getattr(_base_pd, "include_tauE_user_scaling_v396", False)),
                        key=PD_KEYS["include_tauE_user_scaling_v396"],
                        disabled=not include_transport_envelope_v396,
                        help="Adds custom USER τE scaling to the envelope. Provide C and exponents; otherwise it is ignored.",
                    )

                    cU1, cU2, cU3 = st.columns(3)
                    with cU1:
                        tauE_user_C_v396 = st.number_input("C", value=float(getattr(_base_pd, "tauE_user_C_v396", float("nan"))), step=0.01, key=PD_KEYS["tauE_user_C_v396"], disabled=not (include_transport_envelope_v396 and include_tauE_user_scaling_v396))
                        tauE_user_exp_Ip_v396 = st.number_input("exp_Ip", value=float(getattr(_base_pd, "tauE_user_exp_Ip_v396", float("nan"))), step=0.01, key=PD_KEYS["tauE_user_exp_Ip_v396"], disabled=not (include_transport_envelope_v396 and include_tauE_user_scaling_v396))
                        tauE_user_exp_Bt_v396 = st.number_input("exp_Bt", value=float(getattr(_base_pd, "tauE_user_exp_Bt_v396", float("nan"))), step=0.01, key=PD_KEYS["tauE_user_exp_Bt_v396"], disabled=not (include_transport_envelope_v396 and include_tauE_user_scaling_v396))
                    with cU2:
                        tauE_user_exp_ne_v396 = st.number_input("exp_ne", value=float(getattr(_base_pd, "tauE_user_exp_ne_v396", float("nan"))), step=0.01, key=PD_KEYS["tauE_user_exp_ne_v396"], disabled=not (include_transport_envelope_v396 and include_tauE_user_scaling_v396))
                        tauE_user_exp_Ploss_v396 = st.number_input("exp_Ploss", value=float(getattr(_base_pd, "tauE_user_exp_Ploss_v396", float("nan"))), step=0.01, key=PD_KEYS["tauE_user_exp_Ploss_v396"], disabled=not (include_transport_envelope_v396 and include_tauE_user_scaling_v396))
                        tauE_user_exp_R_v396 = st.number_input("exp_R", value=float(getattr(_base_pd, "tauE_user_exp_R_v396", float("nan"))), step=0.01, key=PD_KEYS["tauE_user_exp_R_v396"], disabled=not (include_transport_envelope_v396 and include_tauE_user_scaling_v396))
                    with cU3:
                        tauE_user_exp_eps_v396 = st.number_input("exp_eps", value=float(getattr(_base_pd, "tauE_user_exp_eps_v396", float("nan"))), step=0.01, key=PD_KEYS["tauE_user_exp_eps_v396"], disabled=not (include_transport_envelope_v396 and include_tauE_user_scaling_v396))
                        tauE_user_exp_kappa_v396 = st.number_input("exp_kappa", value=float(getattr(_base_pd, "tauE_user_exp_kappa_v396", float("nan"))), step=0.01, key=PD_KEYS["tauE_user_exp_kappa_v396"], disabled=not (include_transport_envelope_v396 and include_tauE_user_scaling_v396))
                        tauE_user_exp_M_v396 = st.number_input("exp_M", value=float(getattr(_base_pd, "tauE_user_exp_M_v396", float("nan"))), step=0.01, key=PD_KEYS["tauE_user_exp_M_v396"], disabled=not (include_transport_envelope_v396 and include_tauE_user_scaling_v396))

                # -----------------------------------------------------------------
                # v397.0: 1.5D Profile Proxy Authority (governance-only)
                # -----------------------------------------------------------------
                with st.expander("Kinetic profile peaking proxy", expanded=False):
                    include_profile_proxy_v397 = st.checkbox(
                        "Enable kinetic profile peaking proxy diagnostics",
                        value=bool(getattr(_base_pd, "include_profile_proxy_v397", False)),
                        key=PD_KEYS["include_profile_proxy_v397"],
                        help=(
                            "Deterministic analytic profile families (n,T,j) with derived proxy metrics: peaking factors, "
                            "q0/li proxies, and bootstrap localization index. Governance-only unless you set explicit caps."
                        ),
                    )

                    cP1, cP2, cP3 = st.columns(3)
                    with cP1:
                        profile_alpha_n_v397 = st.number_input(
                            "n profile α",
                            min_value=0.5,
                            max_value=6.0,
                            value=float(getattr(_base_pd, "profile_alpha_n_v397", 1.0)),
                            step=0.1,
                            key=PD_KEYS["profile_alpha_n_v397"],
                            disabled=not include_profile_proxy_v397,
                        )
                        profile_beta_n_v397 = st.number_input(
                            "n profile β",
                            min_value=0.5,
                            max_value=6.0,
                            value=float(getattr(_base_pd, "profile_beta_n_v397", 1.0)),
                            step=0.1,
                            key=PD_KEYS["profile_beta_n_v397"],
                            disabled=not include_profile_proxy_v397,
                        )
                    with cP2:
                        profile_alpha_T_v397 = st.number_input(
                            "T profile α",
                            min_value=0.5,
                            max_value=6.0,
                            value=float(getattr(_base_pd, "profile_alpha_T_v397", 1.5)),
                            step=0.1,
                            key=PD_KEYS["profile_alpha_T_v397"],
                            disabled=not include_profile_proxy_v397,
                        )
                        profile_beta_T_v397 = st.number_input(
                            "T profile β",
                            min_value=0.5,
                            max_value=6.0,
                            value=float(getattr(_base_pd, "profile_beta_T_v397", 1.0)),
                            step=0.1,
                            key=PD_KEYS["profile_beta_T_v397"],
                            disabled=not include_profile_proxy_v397,
                        )
                    with cP3:
                        profile_alpha_j_v397 = st.number_input(
                            "j profile α",
                            min_value=0.5,
                            max_value=8.0,
                            value=float(getattr(_base_pd, "profile_alpha_j_v397", 1.5)),
                            step=0.1,
                            key=PD_KEYS["profile_alpha_j_v397"],
                            disabled=not include_profile_proxy_v397,
                        )
                        profile_beta_j_v397 = st.number_input(
                            "j profile β",
                            min_value=0.5,
                            max_value=8.0,
                            value=float(getattr(_base_pd, "profile_beta_j_v397", 1.0)),
                            step=0.1,
                            key=PD_KEYS["profile_beta_j_v397"],
                            disabled=not include_profile_proxy_v397,
                        )

                    profile_shear_shape_v397 = st.slider(
                        "Shear-shape knob (0..1)",
                        min_value=0.0,
                        max_value=1.0,
                        value=float(getattr(_base_pd, "profile_shear_shape_v397", 0.5)),
                        step=0.05,
                        key=PD_KEYS["profile_shear_shape_v397"],
                        disabled=not include_profile_proxy_v397,
                        help="Higher values modestly increase q0_proxy (stabilizing) in the profile proxy mapping.",
                    )

                    st.divider()
                    st.caption("Optional explicit feasibility caps (set NaN to disable):")
                    cC1, cC2, cC3, cC4 = st.columns(4)
                    with cC1:
                        profile_peaking_p_max_v397 = st.number_input(
                            "Max pressure peaking f_p0",
                            min_value=1.0,
                            max_value=10.0,
                            value=float(getattr(_base_pd, "profile_peaking_p_max_v397", float("nan"))) if float(getattr(_base_pd, "profile_peaking_p_max_v397", float("nan")))==float(getattr(_base_pd, "profile_peaking_p_max_v397", float("nan"))) else 4.0,
                            step=0.1,
                            key=PD_KEYS["profile_peaking_p_max_v397"],
                            disabled=not include_profile_proxy_v397,
                        )
                    with cC2:
                        q95_proxy_min_v397 = st.number_input(
                            "Min q95_proxy",
                            min_value=1.0,
                            max_value=10.0,
                            value=float(getattr(_base_pd, "q95_proxy_min_v397", float("nan"))) if float(getattr(_base_pd, "q95_proxy_min_v397", float("nan")))==float(getattr(_base_pd, "q95_proxy_min_v397", float("nan"))) else 2.0,
                            step=0.1,
                            key=PD_KEYS["q95_proxy_min_v397"],
                            disabled=not include_profile_proxy_v397,
                        )
                    with cC3:
                        q0_proxy_min_v397 = st.number_input(
                            "Min q0_proxy (soft)",
                            min_value=0.5,
                            max_value=5.0,
                            value=float(getattr(_base_pd, "q0_proxy_min_v397", float("nan"))) if float(getattr(_base_pd, "q0_proxy_min_v397", float("nan")))==float(getattr(_base_pd, "q0_proxy_min_v397", float("nan"))) else 1.0,
                            step=0.1,
                            key=PD_KEYS["q0_proxy_min_v397"],
                            disabled=not include_profile_proxy_v397,
                        )
                    with cC4:
                        bootstrap_localization_max_v397 = st.number_input(
                            "Max bootstrap localization (soft)",
                            min_value=0.0,
                            max_value=1.0,
                            value=float(getattr(_base_pd, "bootstrap_localization_max_v397", float("nan"))) if float(getattr(_base_pd, "bootstrap_localization_max_v397", float("nan")))==float(getattr(_base_pd, "bootstrap_localization_max_v397", float("nan"))) else 0.6,
                            step=0.05,
                            key=PD_KEYS["bootstrap_localization_max_v397"],
                            disabled=not include_profile_proxy_v397,
                        )

                # -----------------------------------------------------------------
                # v372.0: Neutronics–Materials coupling (governance-only)
                # -----------------------------------------------------------------
                with st.expander("Neutronics–materials coupling", expanded=False):
                    include_neutronics_materials_coupling_v372 = st.checkbox(
                        "Enable neutronics–materials coupling diagnostics",
                        value=bool(getattr(_base_pd, "include_neutronics_materials_coupling_v372", False)),
                        key=PD_KEYS["include_neutronics_materials_coupling_v372"],
                        help=(
                            "Governance-only: material/spectrum-conditioned DPA-rate proxy, component damage partitions, and optional explicit DPA caps. "
                            "Does not modify frozen truth."
                        ),
                    )
                    _mat0 = str(getattr(_base_pd, "nm_material_class_v372", "RAFM"))
                    _spec0 = str(getattr(_base_pd, "nm_spectrum_class_v372", "nominal"))
                    cNM1, cNM2 = st.columns(2)
                    with cNM1:
                        nm_material_class_v372 = st.selectbox(
                            "Material class (governance)",
                            ["RAFM", "W", "SiC", "ODS"],
                            index=max(0, ["RAFM","W","SiC","ODS"].index(_mat0) if _mat0 in ["RAFM","W","SiC","ODS"] else 0),
                            disabled=not include_neutronics_materials_coupling_v372,
                            key=PD_KEYS["nm_material_class_v372"],
                        )
                    with cNM2:
                        nm_spectrum_class_v372 = st.selectbox(
                            "Spectrum class (governance)",
                            ["soft", "nominal", "hard"],
                            index=max(0, ["soft","nominal","hard"].index(_spec0) if _spec0 in ["soft","nominal","hard"] else 1),
                            disabled=not include_neutronics_materials_coupling_v372,
                            key=PD_KEYS["nm_spectrum_class_v372"],
                        )
                    _T0 = getattr(_base_pd, "nm_T_oper_C_v372", float('nan'))
                    use_T = st.checkbox(
                        "Use operating temperature window check",
                        value=bool(np.isfinite(_T0)),
                        disabled=not include_neutronics_materials_coupling_v372,
                        key=PD_KEYS["nm_T_oper_C_v372"] + "_use",
                    )
                    nm_T_oper_C_v372 = float('nan')
                    if use_T:
                        nm_T_oper_C_v372 = st.number_input(
                            "Operating temperature (°C)",
                            value=float(_T0) if np.isfinite(_T0) else 500.0,
                            min_value=0.0,
                            step=10.0,
                            disabled=not include_neutronics_materials_coupling_v372,
                            key=PD_KEYS["nm_T_oper_C_v372"],
                        )
                    _dpa0 = getattr(_base_pd, "dpa_rate_eff_max_v372", float('nan'))
                    use_dpa_cap = st.checkbox(
                        "Enable explicit DPA-rate cap constraint",
                        value=bool(np.isfinite(_dpa0)),
                        disabled=not include_neutronics_materials_coupling_v372,
                        key=PD_KEYS["dpa_rate_eff_max_v372"] + "_use",
                    )
                    dpa_rate_eff_max_v372 = float('nan')
                    if use_dpa_cap:
                        dpa_rate_eff_max_v372 = st.number_input(
                            "DPA-rate cap (DPA/FPY)",
                            value=float(_dpa0) if np.isfinite(_dpa0) else 20.0,
                            min_value=0.0,
                            step=1.0,
                            disabled=not include_neutronics_materials_coupling_v372,
                            key=PD_KEYS["dpa_rate_eff_max_v372"],
                        )
                    _m0 = getattr(_base_pd, "damage_margin_min_v372", float('nan'))
                    use_margin = st.checkbox(
                        "Enable minimum damage margin constraint",
                        value=bool(np.isfinite(_m0)),
                        disabled=not include_neutronics_materials_coupling_v372 or (not use_dpa_cap),
                        key=PD_KEYS["damage_margin_min_v372"] + "_use",
                    )
                    damage_margin_min_v372 = float('nan')
                    if use_margin:
                        damage_margin_min_v372 = st.number_input(
                            "Minimum damage margin (fraction)",
                            value=float(_m0) if np.isfinite(_m0) else 0.0,
                            step=0.05,
                            disabled=not include_neutronics_materials_coupling_v372 or (not use_dpa_cap),
                            key=PD_KEYS["damage_margin_min_v372"],
                        )

                st.caption("Tip: Use this for sensitivity studies (external systems codes-style). It does not change the solved operating point unless you also constrain power balance residuals.")
                profile_model = st.selectbox(
                    "Analytic profiles (½-D scaffold)",
                    options=["none", "parabolic", "pedestal"],
                    index=0,
                    help="If enabled, SHAMS computes simple analytic profiles and adds profile-integrated fusion diagnostics.",
                )
                profile_peaking_ne = _num("nₑ peaking (alpha)", 1.0, 0.1, min_value=0.0, help="Parabolic/pedestal core peaking control for density.")
                profile_peaking_T = _num("T peaking (alpha)", 1.5, 0.1, min_value=0.0, help="Parabolic/pedestal core peaking control for temperature.")

                # v318.0: 1.5D profile authority knobs (deterministic; no solvers)
                # v318.0: 1.5D profile authority knobs (deterministic; no solvers)
                profile_mode = st.checkbox(
                    "Enable 1.5D profile authority diagnostics",
                    value=bool(getattr(_base_pd, "profile_mode", False)),
                    key=PD_KEYS["profile_mode"],
                    help=(
                        "Enables analytic profile diagnostics + the algebraic 1.5D profile bundle. "
                        "This does NOT run transport, does NOT iterate, and does NOT modify the frozen operating point. "
                        "It only produces additional diagnostics and (bounded) bootstrap sensitivity when explicitly selected."
                    ),
                )

                # -----------------------------------------------------------------
                # v358.0: Profile Family Library Authority (transport proxy)
                # -----------------------------------------------------------------
                with st.expander("Profile family library", expanded=False):
                    include_profile_family_v358 = st.checkbox(
                        "Enable profile family transport proxy",
                        value=bool(getattr(_base_pd, "include_profile_family_v358", False)),
                        help="Deterministic profile-family tags and shape multipliers. No solvers, no iteration.",
                    )
                    _pf_opts = ["CORE_FLAT","CORE_PEAKED","PEDESTAL_MODERATE","PEDESTAL_STRONG","HYBRID_CORE_PEAKED_PED"]
                    _pf_base = str(getattr(_base_pd, "profile_family_v358", "CORE_FLAT")).upper().replace(" ", "_")
                    _pf_idx = _pf_opts.index(_pf_base) if _pf_base in _pf_opts else 0
                    profile_family_v358 = st.selectbox(
                        "Profile family",
                        options=_pf_opts,
                        index=_pf_idx,
                        help="Certified profile narratives used to derive bounded shape factors.",
                    )
                    profile_family_pedestal_frac = st.slider(
                        "Pedestal fraction (proxy)",
                        min_value=0.0, max_value=0.40, value=float(getattr(_base_pd, "profile_family_pedestal_frac", 0.0)), step=0.01,
                    )
                    profile_family_peaking_p = st.slider(
                        "Pressure peaking factor",
                        min_value=0.70, max_value=2.00, value=float(getattr(_base_pd, "profile_family_peaking_p", 1.0)), step=0.01,
                    )
                    profile_family_peaking_j = st.slider(
                        "Current peaking factor",
                        min_value=0.70, max_value=2.00, value=float(getattr(_base_pd, "profile_family_peaking_j", 1.0)), step=0.01,
                    )
                    profile_family_shear_shape = st.slider(
                        "Shear shape (0–1)",
                        min_value=0.0, max_value=1.0, value=float(getattr(_base_pd, "profile_family_shear_shape", 0.5)), step=0.01,
                    )
                    profile_family_confinement_mult = st.slider(
                        "Confinement multiplier (bounded)",
                        min_value=0.50, max_value=1.80, value=float(getattr(_base_pd, "profile_family_confinement_mult", 1.0)), step=0.01,
                    )
                    profile_family_bootstrap_mult = st.slider(
                        "Bootstrap multiplier (bounded)",
                        min_value=0.50, max_value=1.80, value=float(getattr(_base_pd, "profile_family_bootstrap_mult", 1.0)), step=0.01,
                    )
                    st.caption("Outputs: profile_family_* keys, tauE_profile_s, H98_profile, profile_f_bootstrap_profile")

                c1, c2, c3 = st.columns(3)
                with c1:
                    profile_alpha_T = _num(
                        "Core T exponent α_T",
                        float(getattr(_base_pd, "profile_alpha_T", 1.5)),
                        0.1,
                        min_value=0.0,
                        key=PD_KEYS["profile_alpha_T"],
                        help="Parabolic exponent for diagnostic T(r) used when profile diagnostics are enabled.",
                    )
                with c2:
                    profile_alpha_n = _num(
                        "Core n exponent α_n",
                        float(getattr(_base_pd, "profile_alpha_n", 1.0)),
                        0.1,
                        min_value=0.0,
                        key=PD_KEYS["profile_alpha_n"],
                        help="Parabolic exponent for diagnostic n(r) used when profile diagnostics are enabled.",
                    )
                with c3:
                    profile_shear_shape = st.slider(
                        "Shear shape (0..1)",
                        min_value=0.0,
                        max_value=1.0,
                        value=float(getattr(_base_pd, "profile_shear_shape", 0.5)),
                        step=0.05,
                        key=PD_KEYS["profile_shear_shape"],
                        help="Algebraic 1.5D bundle knob: higher values increase qmin_proxy (stabilizing) in the diagnostic profile bundle.",
                    )

                pedestal_enabled = st.checkbox(
                    "Enable pedestal shaping (diagnostic scaffold)",
                    value=bool(getattr(_base_pd, "pedestal_enabled", False)),
                    key=PD_KEYS["pedestal_enabled"],
                    help="If enabled, the analytic profile scaffold applies a simple pedestal edge transition for diagnostics.",
                )
                pedestal_width_a = _num(
                    "Pedestal width (a-units)",
                    float(getattr(_base_pd, "pedestal_width_a", 0.05)),
                    0.005,
                    min_value=0.01,
                    max_value=0.25,
                    key=PD_KEYS["pedestal_width_a"],
                    help="Pedestal width used by the analytic profile scaffold (diagnostic only).",
                )
                bootstrap_model = st.selectbox(
                    "Bootstrap proxy model",
                    options=["proxy", "improved"],
                    index=0,
                    help="Select bootstrap fraction proxy used for reporting and (if enabled) steady-state current fractions.",
                )

                include_bootstrap_pressure_selfconsistency = st.checkbox(
                    "Enable bootstrap–pressure self-consistency",
                    value=bool(getattr(_base_pd, "include_bootstrap_pressure_selfconsistency", False)),
                    key=PD_KEYS["include_bootstrap_pressure_selfconsistency"],
                    help="Deterministic check: compares f_bs proxy from the profile bundle vs a pressure-derived expectation under the selected bootstrap proxy model. No iteration.",
                )
                f_bootstrap_consistency_abs_max = float("nan")
                if include_bootstrap_pressure_selfconsistency:
                    f_bootstrap_consistency_abs_max = _num(
                        "Max |Δf_bs| (–)",
                        float(getattr(_base_pd, "f_bootstrap_consistency_abs_max", 0.08) or 0.08),
                        0.01,
                        min_value=0.0,
                        max_value=0.5,
                        key=PD_KEYS["f_bootstrap_consistency_abs_max"],
                        help="Hard cap for |f_bs(reported)-f_bs(expected)|. Enforced as a constraint when enabled.",
                    )



        with st.expander("Power & composition", expanded=False):
                Paux = _num("Auxiliary heating power P_aux (MW)", float(_base_pd.Paux_MW), 1.0, min_value=0.0, max_value=500.0, help="Auxiliary heating power delivered to the plasma (MW).", key=PD_KEYS["Paux_MW"])
                Paux_for_Q = _num("Aux power used in Q definition (MW)", float(getattr(_base_pd, "Paux_MW", 0.0)), 1.0, min_value=0.0, help="Denominator power for Q = P_fus,DT(adj)/P_aux_for_Q (MW).", key=PD_KEYS["Paux_for_Q"])

                with st.expander("Physics include/exclude", expanded=False):
                    st.caption("Disable a block to SKIP its related physics *and* its checks.")
                    include_radiation = st.checkbox("Include core radiation + impurities/dilution model", value=False, help="OFF by default (reviewer-safe). Enable explicitly for Research intent studies.")
                    include_alpha_loss = st.checkbox("Include alpha-loss fraction model", value=True)
                    include_hmode_physics = st.checkbox("Include H-mode access physics (P_LH / LH_ok)", value=True)
                    use_lambda_q = st.checkbox("Include SOL width (λq) proxy", value=True)

                # Defaults (used even when radiation is disabled, for deterministic artifacts)
                Zeff = 1.5
                dilution_fuel = 0.85
                f_rad_core = 0.20
                radiation_model = "fractional"
                radiation_db = "proxy_v1"
                impurity_species = "C"
                impurity_frac = 0.0
                include_synchrotron = True
                zeff_mode = "fixed"
                impurity_mix = ""

                # impurity + detachment authority contract defaults
                impurity_contract_species = "Ne"
                impurity_contract_f_z = 3e-4
                impurity_partition_core = 0.50
                impurity_partition_edge = 0.20
                impurity_partition_sol = 0.20
                impurity_partition_div = 0.10
                include_sol_radiation_control = False
                q_div_target_MW_m2 = float('nan')
                T_sol_keV = 0.08
                f_V_sol_div = 0.12
                detachment_fz_max = float('nan')
                # multi-species impurity mix authority defaults
                include_impurity_v399 = False
                impurity_mix_json_v399 = ""
                zeff_max_v399 = float('nan')
                prad_core_frac_max_v399 = float('nan')
                prad_total_frac_max_v399 = float('nan')
                detachment_margin_min_v399 = float('nan')
                include_edge_core_coupled_exhaust = False
                edge_core_coupling_chi_core = 0.25
                f_rad_core_edge_core_max = float('nan')

                if include_radiation:
                    Zeff = _num("Effective charge Z_eff (–)", 1.5, 0.1, min_value=1.0, help="Effective ion charge Z_eff; used for brems proxy (diagnostic) and radiation screens when enabled.")
                    dilution_fuel = _num("Fuel dilution fraction (DT-equivalent) (–)", 0.85, 0.01, min_value=0.0, max_value=1.0, help="Multiplicative penalty on DT-equivalent fusion power due to dilution/impurities.")
                    f_rad_core = _num("Core radiation fraction f_rad,core (–)", 0.20, 0.01, min_value=0.0, max_value=0.95, help="If enabled, Prad_core = f_rad_core * Pin (simple screening model).")
            
                    radiation_model = st.selectbox(
                        "Radiation model",
                        options=["fractional", "impurity_mix"],
                        index=0,
                        help="fractional: Prad_core = f_rad_core * Pin (legacy proxy). impurity_mix: brem + (optional) synchrotron + impurity line radiation using Lz(Te) tables."
                    )
                    radiation_db = st.selectbox(
                        "Lz(Te) database",
                        options=["proxy_v1","radas_openadas_v1","file:<path>"],
                        index=0,
                        help="Repo-local Lz tables with hash recorded in artifacts. Replace proxy_v1 with validated tables for publication claims.",
                    )

                    # One-line reviewer-safe warning: if the selected DB cannot be resolved,
                    # the frozen evaluator will fall back to builtin_proxy (no crash). We
                    # surface this *before* a run so the user is not misled.
                    try:
                        _db_raw = str(radiation_db or "").strip()
                        _db_ok = True
                        if _db_raw.lower().startswith("file:"):
                            _p = _db_raw[5:].strip()
                            _db_ok = bool(_p) and Path(_p).expanduser().exists()
                        else:
                            _fname = f"lz_tables_{_db_raw.lower()}.json"
                            _db_ok = (SRC / "data"/ "radiation"/ _fname).exists()
                        if not _db_ok:
                            st.warning("Selected Lz(Te) DB not found → will use builtin_proxy (no crash; provenance recorded).")
                    except Exception:
                        pass
                    if str(radiation_db).startswith('file:'):
                        radiation_db = st.text_input(
                            "Radiation DB file (JSON)",
                            value=radiation_db,
                            help="Provide as file:<path>. The JSON must contain {'species': {<SYM>: {'Te_keV': [...], 'Lz_W_m3': [...]}, ...}}. SHA256 will be recorded in artifacts.",
                        )
                    impurity_species = st.selectbox("Impurity species (for line radiation)", options=["C","N","Ne","Ar","W"], index=0)
                    impurity_frac = _num("Impurity fraction (rough)", 0.0, 0.001, min_value=0.0, help="Rough number fraction for line radiation placeholder model.")
                    include_synchrotron = st.checkbox("Include synchrotron radiation (rough)", value=True)

                    zeff_mode = st.selectbox(
                        "Z_eff handling",
                        options=["fixed", "from_impurity", "from_mix"],
                        index=0,
                        help="fixed: use Z_eff input directly. from_impurity: estimate Z_eff from (species, frac). from_mix: estimate Z_eff from impurity_mix dict.",
                    )
                    impurity_mix = st.text_input(
                        "Impurity mix (optional JSON dict)",
                        value="",
                        help="Optional multi-impurity number fractions, e.g. {\"C\":0.01, \"Ne\":0.002}. Used by the physics radiation model and (if selected) to estimate Z_eff.",
                    )

                    with st.expander("Impurity radiation & detachment authority", expanded=False):
                        st.caption(
                            "Algebraic contracts: (i) impurity radiation partitions using a bounded Lz envelope, "
                            "and (ii) detachment budget inversion from q_div target → required SOL+div radiation → implied f_z. "
                            "No time-domain modelling; no feedback into core power balance unless you add explicit constraints."
                        )
                        c1,c2 = st.columns(2)
                        with c1:
                            impurity_contract_species = st.selectbox(
                                "Contract species",
                                options=["C","N","Ne","Ar","W"],
                                index=2,
                                help="Species used by the contract envelope (separate from line-radiation mix model).",
                            )
                            impurity_contract_f_z = _num(
                                "Contract seeding fraction f_z = nZ/ne (–)",
                                float(impurity_contract_f_z),
                                1e-4,
                                min_value=0.0,
                                max_value=1e-2,
                                fmt="%.1e",
                                help="Declared seeding fraction for partition estimates (clamped to ≤1e-2 in truth).",
                            )
                        with c2:
                            detachment_fz_max = _num(
                                "Max allowed implied f_z (optional constraint)",
                                float(detachment_fz_max),
                                1e-4,
                                min_value=0.0,
                                fmt="%.1e",
                                help="If set (finite), SHAMS adds a soft feasibility cap: implied f_z_required ≤ this value.",
                            )

                        st.markdown("**Radiation partitions (fractions; sum ≤ 1; remainder → core)**")
                        p1,p2,p3,p4 = st.columns(4)
                        with p1:
                            impurity_partition_core = st.slider("core", 0.0, 1.0, float(impurity_partition_core), 0.01)
                        with p2:
                            impurity_partition_edge = st.slider("edge", 0.0, 1.0, float(impurity_partition_edge), 0.01)
                        with p3:
                            impurity_partition_sol = st.slider("SOL", 0.0, 1.0, float(impurity_partition_sol), 0.01)
                        with p4:
                            impurity_partition_div = st.slider("divertor", 0.0, 1.0, float(impurity_partition_div), 0.01)

                        st.markdown("**Detachment target (diagnostic transparency)**")
                        include_sol_radiation_control = st.checkbox(
                            "Enable q_div target inversion",
                            value=bool(include_sol_radiation_control),
                            help="Uses q_div_target to compute required SOL+div radiated fraction and implied impurity f_z.",
                        )
                        q_div_target_MW_m2 = _num(
                            "Requested q_div target (MW/m²)",
                            float(q_div_target_MW_m2) if q_div_target_MW_m2==q_div_target_MW_m2 else 10.0,
                            0.5,
                            min_value=0.1,
                            help="Technology goal. This does not change the operating point; it produces a required SOL+div radiation budget.",
                        ) if include_sol_radiation_control else float('nan')
                        c3,c4 = st.columns(2)
                        with c3:
                            T_sol_keV = _num("T_SOL proxy (keV)", float(T_sol_keV), 0.01, min_value=0.03, max_value=1.0)
                        with c4:
                            f_V_sol_div = _num("Effective radiating volume fraction V_SOL+div / V", float(f_V_sol_div), 0.01, min_value=0.005, max_value=0.5)

                        # --- Multi-species impurity & radiation authority ---
                        with st.expander("Multi-species impurity & radiation (Zeff + partitions)", expanded=False):
                            st.caption("Deterministic multi-species impurity mix → Zeff + Prad partitions (core/edge/SOL/div). "
                                       "This is a *proxy* authority: algebraic, bounded, audit-friendly.")
                            include_impurity_v399 = st.checkbox(
                                "Enable multi-species impurity mix authority",
                                value=bool(st.session_state.get("include_impurity_v399_default", False)),
                                help="When enabled, SHAMS computes multi-species Zeff and radiation partitions (no feedback into truth).",
                            )
                            default_json = '{"species_fz":{"Ne":3e-4,"Ar":0.0,"W":0.0},"f_core":0.50,"f_edge":0.20,"f_sol":0.20,"f_divertor":0.10}'
                            impurity_mix_json_v399 = st.text_area(
                                "Impurity mix JSON",
                                value=str(impurity_mix_json_v399).strip() if str(impurity_mix_json_v399).strip() else default_json,
                                height=90,
                                help="Fractions are f_z = n_z / n_e. Partitions apply to total impurity radiation. Unknown species map conservatively to Ne.",
                            )
                            st.markdown("**Optional feasibility caps (soft constraints; NaN disables)**")
                            cA, cB, cC, cD = st.columns(4)
                            with cA:
                                zeff_max_v399 = _num("Zeff max", float(zeff_max_v399) if zeff_max_v399==zeff_max_v399 else float('nan'),
                                                    0.1, min_value=1.0, max_value=10.0)
                            with cB:
                                prad_core_frac_max_v399 = _num("Prad_core/Pin max", float(prad_core_frac_max_v399) if prad_core_frac_max_v399==prad_core_frac_max_v399 else float('nan'),
                                                               0.01, min_value=0.0, max_value=1.0)
                            with cC:
                                prad_total_frac_max_v399 = _num("Prad_total/Pin max", float(prad_total_frac_max_v399) if prad_total_frac_max_v399==prad_total_frac_max_v399 else float('nan'),
                                                                0.01, min_value=0.0, max_value=1.0)
                            with cD:
                                detachment_margin_min_v399 = _num("Detachment margin min", float(detachment_margin_min_v399) if detachment_margin_min_v399==detachment_margin_min_v399 else float('nan'),
                                                                  0.05, min_value=-1.0, max_value=5.0,
                                                                  help="Margin = (Prad_SOL+div achieved)/(required) - 1 (>=0 means meets required budget).")

                        st.markdown('**Edge–core coupled exhaust**')
                        include_edge_core_coupled_exhaust = st.checkbox(
                            'Enable edge–core coupled exhaust re-evaluation',
                            value=bool(include_edge_core_coupled_exhaust),
                            help='One-pass: uses P_SOL,eff = P_SOL - chi_core·P_rad,req(SOL+div) to re-evaluate q_div. lambda_q is held fixed. Does not iterate.',
                        )
                        edge_core_coupling_chi_core = st.slider(
                            'Coupling coefficient chi_core (–)',
                            min_value=0.0, max_value=1.0, value=float(edge_core_coupling_chi_core), step=0.05,
                            help='Fraction of SOL+div radiation requirement mapped to additional core radiation penalty for exhaust budgeting.',
                        )
                        f_rad_core_edge_core_max = _num(
                            'Max allowed coupled core radiative fraction (optional)',
                            float(f_rad_core_edge_core_max),
                            0.05, min_value=0.0, max_value=2.0,
                            help='If set, enforces f_rad_core_edge_core ≤ max when edge-core coupling is enabled.',
                        )

                    st.markdown("**Power-channel bookkeeping (transparent; totals unchanged)**")
                    f_alpha_to_ion = st.slider("Alpha deposition to ions f_α→i", min_value=0.0, max_value=1.0, value=0.85, step=0.01)
                    f_aux_to_ion = st.slider("Aux deposition to ions f_aux→i", min_value=0.0, max_value=1.0, value=0.50, step=0.01)
                    include_P_ie = st.checkbox("Include ion↔electron equilibration P_ie (diagnostic)", value=True)

                    st.markdown("**Particle sustainability (optional diagnostic closure)**")
                    include_particle_balance = st.checkbox("Enable particle balance closure (diagnostic)", value=False)
                    tau_p_over_tauE = _num("τ_p / τ_E,eff (–)", 3.0, 0.2, min_value=0.0, help="Proxy: particle confinement time τ_p = (τ_p/τ_E,eff)·τ_E,eff.")
                    S_fuel_max_1e22_per_s = _num("Max fueling source S_max (1e22/s) (optional)", float('nan'), 0.1, min_value=0.0, help="If set, SHAMS enforces S_required ≤ S_max as a feasibility constraint (only when particle closure enabled).")

                    st.markdown("**Non-inductive & risk screens (optional; system-code)**")
                    cd_enable = st.checkbox("Enable current-drive closure (proxy)", value=False)
                    cd_method = st.selectbox("CD method", options=["NBI","EC","LH"], index=0)
                    cd_fraction_of_Paux = st.slider("Fraction of Paux allocated to CD", min_value=0.0, max_value=1.0, value=0.5, step=0.05)
                    f_NI_min = _num("Min non-inductive fraction f_NI,min (optional)", float("nan"), 0.05, min_value=0.0, max_value=1.0, help="If set, enforces (I_bootstrap+I_cd)/Ip ≥ f_NI,min.")
                    disruption_risk_max = _num("Max disruption risk proxy (optional)", float("nan"), 0.1, min_value=0.0, help="If set, enforces disruption_risk_proxy ≤ max.")
                    f_rad_core_max = _num("Max core radiative fraction (optional)", float("nan"), 0.05, min_value=0.0, max_value=2.0, help="If set, enforces Prad_core/Ploss ≤ max.")

                else:
                    Zeff = 1.0
                    dilution_fuel = 1.0
                    f_rad_core = 0.0
                    zeff_mode = "fixed"
                    impurity_species = "C"
                    impurity_frac = 0.0
                    impurity_mix = ""
                    include_synchrotron = False
                    f_alpha_to_ion = 0.85
                    f_aux_to_ion = 0.50
                    include_P_ie = True
                    include_particle_balance = False
                    tau_p_over_tauE = 3.0
                    S_fuel_max_1e22_per_s = float("nan")
                    cd_enable = False
                    cd_method = "NBI"
                    cd_fraction_of_Paux = 0.5
                    f_NI_min = float("nan")
                    disruption_risk_max = float("nan")
                    f_rad_core_max = float("nan")

                    impurity_contract_species = "Ne"
                    impurity_contract_f_z = 3e-4
                    impurity_partition_core = 0.50
                    impurity_partition_edge = 0.20
                    impurity_partition_sol = 0.20
                    impurity_partition_div = 0.10
                    include_sol_radiation_control = False
                    q_div_target_MW_m2 = float('nan')
                    T_sol_keV = 0.08
                    f_V_sol_div = 0.12
                    detachment_fz_max = float('nan')

                if include_alpha_loss:
                    alpha_loss_frac = _num("Alpha heating loss fraction (–)", 0.05, 0.01, min_value=0.0, max_value=1.0, help="If enabled, fraction of alpha heating assumed lost (not deposited in core).")
                else:
                    alpha_loss_frac = 0.0

                # Optional fast-particle / ash closures (transparent (systems-code-inspired); defaults preserve legacy behavior)
                with st.expander("Advanced fast-particle / ash closures (optional)", expanded=False):
                    st.caption("All options here are **opt-in**; defaults preserve current SHAMS behavior.")
                    alpha_loss_model = st.selectbox(
                        "Alpha prompt-loss model",
                        options=["fixed", "rho_star"],
                        index=0,
                        help="fixed: use alpha_loss_frac directly. rho_star: alpha_loss_frac_eff = alpha_loss_frac + k·rho* (transparent proxy).",
                    )
                    alpha_prompt_loss_k = _num(
                        "Prompt-loss slope k (–)",
                        0.0,
                        0.01,
                        min_value=0.0,
                        max_value=1.0,
                        help="Used only if alpha_loss_model='rho_star'. Effective alpha loss is clipped to [0,0.9].",
                    )
                    alpha_partition_model = st.selectbox(
                        "Alpha ion/electron partition proxy",
                        options=["fixed", "Te_ratio"],
                        index=0,
                        help="Bookkeeping only: affects Palpha_i/Palpha_e reporting (Pin unchanged).",
                    )
                    alpha_partition_k = _num(
                        "Partition slope k (–)",
                        0.0,
                        0.01,
                        min_value=0.0,
                        max_value=2.0,
                        help="Used only if alpha_partition_model='Te_ratio'.",
                    )

                    ash_dilution_mode = st.selectbox(
                        "Helium-ash dilution penalty",
                        options=["off", "fixed_fraction"],
                        index=0,
                        help="off: no additional penalty. fixed_fraction: Pfus_for_Q *= (1-f_He_ash)^2 (transparent proxy).",
                    )
                    f_He_ash = _num(
                        "Helium-ash fraction f_He_ash (–)",
                        0.0,
                        0.01,
                        min_value=0.0,
                        max_value=0.9,
                        help="Used only if ash_dilution_mode='fixed_fraction'.",
                    )
                if include_hmode_physics:
                    require_Hmode = st.checkbox("Require H-mode access (enforce P_aux ≥ (1+margin)·P_LH)", value=False)
                    PLH_margin = _num("P_LH margin (–)", 0.0, 0.05, min_value=0.0, max_value=5.0, help="If Require H-mode is enabled: require P_aux ≥ (1+margin)·P_LH.")
                else:
                    require_Hmode = False
                    PLH_margin = 0.0
        with st.expander("Operating targets (solver)", expanded=False):
                fuel_mode_label = st.radio(
                    "Fuel / design mode",
                    ["DT performance (targets Q & net electric)", "DD feasibility (includes secondary DT from DD-produced T)"],
                    index=0,
                )
                fuel_mode = "DT"if fuel_mode_label.startswith("DT") else "DD"
                if fuel_mode == "DD":
                    include_secondary_DT = st.checkbox("Include secondary DT from DD-produced tritium", value=True)
                    if include_secondary_DT:
                        tritium_retention = _num("Tritium retention fraction f_ret (–)", 0.5, 0.05, min_value=0.0, max_value=1.0,
                                                 help="Fraction of DD-produced tritium retained/available to burn in secondary DT.")
                        tau_T_loss_s = _num("Effective tritium loss time τ_T (s)", 5.0, 0.5, min_value=0.1,
                                            help="Effective confinement/retention time for produced tritium before loss/removal.")
                    else:
                        tritium_retention = 0.0
                        tau_T_loss_s = 1.0
                else:
                    include_secondary_DT = False
                    tritium_retention = 0.0
                    tau_T_loss_s = 1.0

                # Mode-specific safe defaults (DD mode prioritizes feasibility screens over performance)
                default_Q = 2.0 if fuel_mode == "DT"else 0.05
                default_H98 = 1.15 if fuel_mode == "DT"else 1.0
                Q_target = _num("Target Q (fusion gain proxy) [-]", default_Q, 0.05, min_value=0.0)
                H98_target = _num("Target H98 [-]", default_H98, 0.05, min_value=0.1, help="Required confinement factor H98. Solver adjusts Ip and f_G to meet this target.")
                use_envelope = st.checkbox("Design envelope solve (SPARC-like)", value=False, help="Use transparent (systems-code-inspired) bounded vector solve to hit targets by varying Ip, fG, and optionally Paux.")
                Pfus_target = None
                Pnet_target = None
                if use_envelope:
                    Pfus_target = _num("Target fusion power P_fus (MW)", 140.0, 10.0, min_value=0.0)
                    Pnet_target = _num("Target net electric power P_net (MW) (optional)", -1.0, 10.0, help="Set to <0 to ignore. If >0, solver will try to meet it by varying Paux as needed.", min_value=-1e6)

                # -------------------------------------------------------------
                # Optimization (transparent (systems-code-inspired)): search within bounds for a better design
                # -------------------------------------------------------------
                st.markdown("**Optimization (experimental)**")
                do_opt = st.checkbox("Run constrained optimization (random search)", value=False,
                                     help="Searches over (Ip, fG, Paux) within bounds to improve an objective while satisfying constraints.")
                opt_objective = st.selectbox("Objective", ["min_R0", "min_Bpeak", "max_Pnet", "min_recirc"], index=1)
                opt_iters = int(_num("Optimization iterations", 200, 10, min_value=20.0))
                opt_seed = int(_num("Optimization seed", 1, 1, min_value=0.0))
                st.divider()

                # Defaults track the currently loaded base point so preset loads immediately feel consistent.
                _ip0 = float(getattr(_base_pd, "Ip_MA", 8.0) or 8.0)
                _fg0 = float(getattr(_base_pd, "fG", 0.8) or 0.8)
                Ip_min = _num("Plasma current lower bound I_p,min (MA)", max(0.1, 0.80 * _ip0), 1.0, min_value=0.1, key=PD_KEYS["Ip_lo"])
                Ip_max = _num("Plasma current upper bound I_p,max (MA)", max(0.2, 1.20 * _ip0), 0.5, min_value=0.1, key=PD_KEYS["Ip_hi"])
                fG_min = _num("Greenwald fraction lower bound f_G,min (–)", max(0.0, _fg0 - 0.20), 0.01, min_value=0.0, max_value=2.0, key=PD_KEYS["fG_lo"])
                fG_max = _num("Greenwald fraction upper bound f_G,max (–)", min(2.0, _fg0 + 0.20), 0.01, min_value=0.0, max_value=2.0, key=PD_KEYS["fG_hi"])
                tol = _num("solver tol [-]", 1e-3, 1e-4, min_value=1e-6, fmt="%.1e")
                show_solver_live = st.checkbox(
                    "Show solver physics live (step-by-step)",
                    value=True,
                    help=(
                        "Visualize how the nested solver converges: outer bisection on Ip to hit the target H98, "
                        "with an inner solve on fG to match the target Q at each Ip evaluation."
                    ),
                )
        with st.expander("Engineering & plant feasibility (optional)", expanded=False):
                # These names are passed through via PointInputs **kwargs, so they must exist in your src version.
                # We keep them optional. If missing, they are simply ignored by PointInputs.
                tshield = _num("Neutron shield thickness (m)", 0.8, 0.01, min_value=0.0, help="Effective neutron shield thickness used for neutronics/HTS lifetime proxies.")
                # A small representative set; add more once you confirm exact fields in src/phase1_systems.py
                # We still allow user to run without them.

                # --- Engineering & plant feasibility (optional): per-subsystem toggles + confidence presets ---
                st.markdown("#### Engineering & plant feasibility (optional)")
                confidence = st.radio(
                    "Confidence level",
                    ["Conservative", "Nominal", "Aggressive"],
                    index=1,
                    horizontal=True,
                    help="Controls default assumptions and warning bands (WARN vs FAIL). Conservative is stricter; aggressive is more permissive."
                )
                warn_fracs = {
                    "Conservative": {"max": 0.85, "min": 1.20},
                    "Nominal":      {"max": 0.90, "min": 1.10},
                    "Aggressive":   {"max": 0.95, "min": 1.05},
                }[confidence]

                c1, c2 = st.columns(2)
                with c1:
                    include_build = st.checkbox("Build & radial build", value=True)
                    include_magnets = st.checkbox("Magnets & HTS", value=True)
                    include_divertor = st.checkbox("Divertor / SOL", value=True)
                with c2:
                    include_neutronics = st.checkbox("Neutronics (TBR, lifetime)", value=True)
                    include_net_power = st.checkbox("Net power / electrical balance", value=True)
                    include_fuelcycle = st.checkbox("Fuel-cycle (tritium throughput/inventory)", value=False)
                    include_economics = st.checkbox(
                        "Economics overlay (CAPEX proxy cap)",
                        value=False,
                        help="Enable optional PROCESS-like component CAPEX proxy knobs and an optional hard cap. Diagnostic only; does not change plasma truth.",
                    )


                defaults = _base_pd  # safe local defaults source for optional authority overlays

                # --- Availability & replacement ledger authority (optional) ---
                with st.expander("Component replacement ledger", expanded=False):
                    st.caption("Deterministic algebraic ledger: planned baseline + forced baseline (forced_outage_base) + replacement downtime + annualized replacement cost. Disabled by default.")
                    include_availability_replacement_v359 = st.checkbox(
                        "Enable component replacement ledger",
                        value=bool(getattr(defaults, "include_availability_replacement_v359", False)),
                        help="Adds availability_v359, replacement cost rate, and an optional LCOE cap. Does not modify plasma truth or legacy economics outputs.",
                    )
                    cA, cB = st.columns(2)
                    with cA:
                        planned_outage_base = st.number_input(
                            "Planned outage baseline (fraction)",
                            min_value=0.0,
                            max_value=0.50,
                            value=float(getattr(defaults, "planned_outage_base", 0.05) or 0.05),
                            step=0.01,
                        )
                        availability_v359_min = st.number_input(
                            "Min availability (NaN disables)",
                            value=float(getattr(defaults, "availability_v359_min", float('nan'))),
                        )
                        LCOE_max_USD_per_MWh = st.number_input(
                            "Max LCOE proxy (USD/MWh) (NaN disables)",
                            value=float(getattr(defaults, "LCOE_max_USD_per_MWh", float('nan'))),
                        )
                    with cB:
                        heating_cd_replace_interval_y = st.number_input(
                            "Heating/CD replacement interval (y)",
                            min_value=0.5,
                            max_value=50.0,
                            value=float(getattr(defaults, "heating_cd_replace_interval_y", 8.0) or 8.0),
                            step=0.5,
                        )
                        heating_cd_replace_duration_days = st.number_input(
                            "Heating/CD replacement duration (days)",
                            min_value=0.0,
                            max_value=365.0,
                            value=float(getattr(defaults, "heating_cd_replace_duration_days", 30.0) or 30.0),
                            step=1.0,
                        )
                        tritium_plant_replace_interval_y = st.number_input(
                            "Tritium plant replacement interval (y)",
                            min_value=0.5,
                            max_value=50.0,
                            value=float(getattr(defaults, "tritium_plant_replace_interval_y", 10.0) or 10.0),
                            step=0.5,
                        )
                        tritium_plant_replace_duration_days = st.number_input(
                            "Tritium plant replacement duration (days)",
                            min_value=0.0,
                            max_value=365.0,
                            value=float(getattr(defaults, "tritium_plant_replace_duration_days", 30.0) or 30.0),
                            step=1.0,
                        )

                # --- Maintenance Scheduling Authority 1.0 (optional) ---
                with st.expander("Maintenance scheduling model", expanded=False):
                    st.caption(
                        "Deterministic outage calendar proxy: planned+forced baselines plus a bundled replacement schedule derived from cadences and durations. "
                        "No time simulation; no optimization; does not modify plasma truth."
                    )
                    include_maintenance_scheduling_v368 = st.checkbox(
                        "Enable maintenance scheduling model",
                        value=bool(getattr(defaults, "include_maintenance_scheduling_v368", False)),
                        help="Adds availability_v368, outage_total_frac_v368, replacement_cost_MUSD_per_year_v368 and an explicit maintenance_events_v368 table.",
                    )
                    cM1, cM2 = st.columns(2)
                    with cM1:
                        _bp_opts = ["independent", "bundle_in_vessel", "bundle_all"]
                        _bp_def = str(getattr(defaults, "maintenance_bundle_policy", "independent"))
                        _bp_ix = _bp_opts.index(_bp_def) if _bp_def in _bp_opts else 0
                        maintenance_bundle_policy = st.selectbox(
                            "Bundling policy",
                            _bp_opts,
                            index=_bp_ix,
                            help="Bundling is a deterministic proxy: interval=min(intervals), duration=max(durations)+overhead.",
                        )
                        maintenance_bundle_overhead_days = st.number_input(
                            "Bundle overhead (days)",
                            min_value=0.0,
                            max_value=90.0,
                            value=float(getattr(defaults, "maintenance_bundle_overhead_days", 7.0) or 7.0),
                            step=1.0,
                        )
                        _fm_opts = ["max", "baseline", "trips"]
                        _fm_def = str(getattr(defaults, "forced_outage_mode_v368", "max"))
                        _fm_ix = _fm_opts.index(_fm_def) if _fm_def in _fm_opts else 0
                        forced_outage_mode_v368 = st.selectbox(
                            "Forced outage mode",
                            _fm_opts,
                            index=_fm_ix,
                            help="max = max(forced_outage_base, trips_per_year*trip_duration_days/365).",
                        )
                    with cM2:
                        availability_v368_min = st.number_input(
                            "Min availability (NaN disables)",
                            value=float(getattr(defaults, "availability_v368_min", float('nan'))),
                        )
                        outage_fraction_v368_max = st.number_input(
                            "Max total outage fraction (NaN disables)",
                            value=float(getattr(defaults, "outage_fraction_v368_max", float('nan'))),
                        )
                        maintenance_planning_horizon_yr = st.number_input(
                            "Planning horizon (yr) (NaN uses plant lifetime)",
                            min_value=1.0,
                            max_value=100.0,
                            value=float(getattr(defaults, "maintenance_planning_horizon_yr", float('nan'))),
                            step=1.0,
                        )

                # --- Availability 2.0 — Reliability Envelope Authority (optional) ---
                with st.expander("Availability & reliability envelope", expanded=False):
                    st.caption(
                        "Deterministic availability envelope driven by explicit MTBF/MTTR proxies plus planned and maintenance downtime. "
                        "Governance-only; OFF by default. No RAMI simulation (no Monte Carlo / Markov chains)."
                    )
                    include_availability_reliability_v391 = st.checkbox(
                        "Enable availability & reliability envelope",
                        value=bool(getattr(defaults, "include_availability_reliability_v391", False)),
                        help="Adds availability_cert_v391 plus explicit downtime decomposition and a subsystem ledger.",
                    )
                    planned_outage_days_per_y_v391 = st.number_input(
                        "Planned outage (days/year)",
                        min_value=0.0,
                        max_value=365.0,
                        value=float(getattr(defaults, "planned_outage_days_per_y_v391", 30.0) or 30.0),
                        step=1.0,
                        help="Deterministic planned outage allocation. Converted to planned_outage_frac_v391 = days/365.",
                    )
                    st.markdown("**MTBF/MTTR (hours) — subsystem proxies**")
                    cR1, cR2 = st.columns(2)
                    with cR1:
                        mtbf_tf_h_v391 = st.number_input("TF MTBF (h)", min_value=1.0, value=float(getattr(defaults, "mtbf_tf_h_v391", 80000.0) or 80000.0), step=1000.0)
                        mttr_tf_h_v391 = st.number_input("TF MTTR (h)", min_value=0.0, value=float(getattr(defaults, "mttr_tf_h_v391", 240.0) or 240.0), step=24.0)
                        mtbf_pfcs_h_v391 = st.number_input("PF/CS MTBF (h)", min_value=1.0, value=float(getattr(defaults, "mtbf_pfcs_h_v391", 60000.0) or 60000.0), step=1000.0)
                        mttr_pfcs_h_v391 = st.number_input("PF/CS MTTR (h)", min_value=0.0, value=float(getattr(defaults, "mttr_pfcs_h_v391", 168.0) or 168.0), step=24.0)
                        mtbf_cryo_h_v391 = st.number_input("Cryoplant MTBF (h)", min_value=1.0, value=float(getattr(defaults, "mtbf_cryo_h_v391", 40000.0) or 40000.0), step=1000.0)
                        mttr_cryo_h_v391 = st.number_input("Cryoplant MTTR (h)", min_value=0.0, value=float(getattr(defaults, "mttr_cryo_h_v391", 120.0) or 120.0), step=24.0)
                        mtbf_bop_h_v391 = st.number_input("BOP MTBF (h)", min_value=1.0, value=float(getattr(defaults, "mtbf_bop_h_v391", 50000.0) or 50000.0), step=1000.0)
                        mttr_bop_h_v391 = st.number_input("BOP MTTR (h)", min_value=0.0, value=float(getattr(defaults, "mttr_bop_h_v391", 72.0) or 72.0), step=24.0)
                    with cR2:
                        mtbf_divertor_h_v391 = st.number_input("Divertor MTBF (h)", min_value=1.0, value=float(getattr(defaults, "mtbf_divertor_h_v391", 20000.0) or 20000.0), step=1000.0)
                        mttr_divertor_h_v391 = st.number_input("Divertor MTTR (h)", min_value=0.0, value=float(getattr(defaults, "mttr_divertor_h_v391", 336.0) or 336.0), step=24.0)
                        mtbf_blanket_h_v391 = st.number_input("Blanket MTBF (h)", min_value=1.0, value=float(getattr(defaults, "mtbf_blanket_h_v391", 25000.0) or 25000.0), step=1000.0)
                        mttr_blanket_h_v391 = st.number_input("Blanket MTTR (h)", min_value=0.0, value=float(getattr(defaults, "mttr_blanket_h_v391", 504.0) or 504.0), step=24.0)
                        mtbf_hcd_h_v391 = st.number_input("HCD MTBF (h)", min_value=1.0, value=float(getattr(defaults, "mtbf_hcd_h_v391", 30000.0) or 30000.0), step=1000.0)
                        mttr_hcd_h_v391 = st.number_input("HCD MTTR (h)", min_value=0.0, value=float(getattr(defaults, "mttr_hcd_h_v391", 168.0) or 168.0), step=24.0)

                    st.markdown("**Optional caps/minima (NaN disables)**")
                    cR3, cR4 = st.columns(2)
                    with cR3:
                        availability_min_v391 = st.number_input(
                            "Min availability (NaN disables)",
                            value=float(getattr(defaults, "availability_min_v391", float('nan'))),
                        )
                        planned_outage_max_frac_v391 = st.number_input(
                            "Max planned outage fraction (NaN disables)",
                            value=float(getattr(defaults, "planned_outage_max_frac_v391", float('nan'))),
                        )
                    with cR4:
                        unplanned_downtime_max_frac_v391 = st.number_input(
                            "Max unplanned downtime fraction (NaN disables)",
                            value=float(getattr(defaults, "unplanned_downtime_max_frac_v391", float('nan'))),
                        )
                        maint_downtime_max_frac_v391 = st.number_input(
                            "Max maintenance downtime fraction (NaN disables)",
                            value=float(getattr(defaults, "maint_downtime_max_frac_v391", float('nan'))),
                        )
                # --- Plant Economics Authority 1.0 (optional) ---
                with st.expander("Plant economics (capital & LCOE)", expanded=False):
                    st.caption("Deterministic CAPEX+OPEX decomposition and availability-coupled LCOE proxy. Diagnostic overlay; OFF by default.")
                    include_economics_v360 = st.checkbox(
                        "Enable plant economics (capital & LCOE)",
                        value=bool(getattr(defaults, "include_economics_v360", False)),
                        help="Adds OPEX component breakdown and LCOE_proxy_v360_USD_per_MWh. Does not modify plasma truth or legacy economics unless enabled.",
                    )
                    cE1, cE2 = st.columns(2)
                    with cE1:
                        opex_fixed_MUSD_per_y = st.number_input(
                            "Fixed OPEX (MUSD/y)",
                            min_value=0.0,
                            value=float(getattr(defaults, "opex_fixed_MUSD_per_y", 0.0) or 0.0),
                            step=1.0,
                        )
                        tritium_processing_cost_USD_per_g = st.number_input(
                            "Tritium processing cost (USD/g)",
                            min_value=0.0,
                            value=float(getattr(defaults, "tritium_processing_cost_USD_per_g", 0.05) or 0.05),
                            step=0.01,
                        )
                    with cE2:
                        cryo_wallplug_multiplier = st.number_input(
                            "Cryo wall-plug multiplier (MW_e/MW@20K)",
                            min_value=0.0,
                            value=float(getattr(defaults, "cryo_wallplug_multiplier", 250.0) or 250.0),
                            step=10.0,
                        )
                        OPEX_max_MUSD_per_y = st.number_input(
                            "Max OPEX (MUSD/y) (NaN disables)",
                            value=float(getattr(defaults, "OPEX_max_MUSD_per_y", float('nan'))),
                        )

                # --- Plant Economics & Cost Authority 2.0 (optional) ---
                with st.expander("Plant economics depth model", expanded=False):
                    st.caption(
                        "Deterministic structured CAPEX+OPEX with availability-tiered capacity factor and LCOE-lite proxy. "
                        "Governance overlay only; OFF by default."
                    )
                    include_economics_v383 = st.checkbox(
                        "Enable plant economics depth model",
                        value=bool(getattr(defaults, "include_economics_v383", False)),
                        help="Adds CAPEX_structured_v383_MUSD, OPEX_structured_v383_MUSD_per_y, LCOE_lite_v383_USD_per_MWh, and tiered availability proxy.",
                        key="pd_include_economics_v383",
                    )
                    cE3, cE4 = st.columns(2)
                    with cE3:
                        CAPEX_structured_max_MUSD = st.number_input(
                            "Max structured CAPEX (MUSD) (NaN disables)",
                            value=float(getattr(defaults, "CAPEX_structured_max_MUSD", float('nan'))),
                            key="pd_CAPEX_structured_max_MUSD_v383",
                        )
                        OPEX_structured_max_MUSD_per_y = st.number_input(
                            "Max structured OPEX (MUSD/y) (NaN disables)",
                            value=float(getattr(defaults, "OPEX_structured_max_MUSD_per_y", float('nan'))),
                            key="pd_OPEX_structured_max_MUSD_per_y_v383",
                        )
                    with cE4:
                        LCOE_lite_max_USD_per_MWh = st.number_input(
                            "Max LCOE-lite (USD/MWh) (NaN disables)",
                            value=float(getattr(defaults, "LCOE_lite_max_USD_per_MWh", float('nan'))),
                            key="pd_LCOE_lite_max_USD_per_MWh_v383",
                        )



                # --- Cost Authority 3.0 — Industrial Depth (optional) ---
                with st.expander("Cost authority & escalation", expanded=False):
                    st.caption("Deterministic, engineering-driven subsystem cost scaling envelopes (industrial depth). Governance-only; OFF by default. Requires the Economics overlay toggle above so cost outputs are computed.")
                    include_cost_authority_v388 = st.checkbox(
                        "Enable cost authority & escalation",
                        value=bool(getattr(defaults, "include_cost_authority_v388", False)),
                        key="pd_include_cost_authority_v388",
                    )
                    cC1, cC2 = st.columns(2)
                    with cC1:
                        CAPEX_industrial_max_MUSD = st.number_input(
                            "Max industrial CAPEX (MUSD) (NaN disables)",
                            value=float(getattr(defaults, "CAPEX_industrial_max_MUSD", float('nan'))),
                            key="pd_CAPEX_industrial_max_MUSD_v388",
                        )
                        OPEX_industrial_max_MUSD_per_y = st.number_input(
                            "Max industrial OPEX (MUSD/y) (NaN disables)",
                            value=float(getattr(defaults, "OPEX_industrial_max_MUSD_per_y", float('nan'))),
                            key="pd_OPEX_industrial_max_MUSD_per_y_v388",
                        )
                    with cC2:
                        LCOE_lite_v388_max_USD_per_MWh = st.number_input(
                            "Max LCOE-lite (USD/MWh) (NaN disables)",
                            value=float(getattr(defaults, "LCOE_lite_v388_max_USD_per_MWh", float('nan'))),
                            key="pd_LCOE_lite_v388_max_USD_per_MWh_v388",
                        )




                # --- Structural stress limits (optional) ---
                with st.expander("Structural stress limits", expanded=False):
                    st.caption("Deterministic thin-shell structural stress proxies (TF / CS / vacuum vessel). Governance-only; OFF by default. When enabled, explicit margin-minima constraints are applied in feasibility-first mode.")
                    include_structural_stress_v389 = st.checkbox(
                        "Enable structural stress limits",
                        value=bool(getattr(defaults, "include_structural_stress_v389", False)),
                        key="pd_include_structural_stress_v389",
                    )
                    sS1, sS2 = st.columns(2)
                    with sS1:
                        tf_struct_margin_min_v389 = st.number_input(
                            "TF structural margin min (-)",
                            value=float(getattr(defaults, "tf_struct_margin_min_v389", 1.0)),
                            key="pd_tf_struct_margin_min_v389",
                        )
                        t_cs_struct_m_v389 = st.number_input(
                            "CS structural thickness proxy t_cs (m)",
                            value=float(getattr(defaults, "t_cs_struct_m_v389", 0.20)),
                            key="pd_t_cs_struct_m_v389",
                        )
                        sigma_cs_allow_MPa_v389 = st.number_input(
                            "CS allowable stress proxy (MPa)",
                            value=float(getattr(defaults, "sigma_cs_allow_MPa_v389", 300.0)),
                            key="pd_sigma_cs_allow_MPa_v389",
                        )
                        cs_struct_margin_min_v389 = st.number_input(
                            "CS/PF structural margin min (-)",
                            value=float(getattr(defaults, "cs_struct_margin_min_v389", 1.0)),
                            key="pd_cs_struct_margin_min_v389",
                        )
                    with sS2:
                        vv_ext_pressure_MPa_v389 = st.number_input(
                            "Vacuum vessel external pressure (MPa)",
                            value=float(getattr(defaults, "vv_ext_pressure_MPa_v389", 0.101)),
                            key="pd_vv_ext_pressure_MPa_v389",
                        )
                        sigma_vv_allow_MPa_v389 = st.number_input(
                            "Vacuum vessel allowable stress proxy (MPa)",
                            value=float(getattr(defaults, "sigma_vv_allow_MPa_v389", 200.0)),
                            key="pd_sigma_vv_allow_MPa_v389",
                        )
                        vv_struct_margin_min_v389 = st.number_input(
                            "Vacuum vessel structural margin min (-)",
                            value=float(getattr(defaults, "vv_struct_margin_min_v389", 1.0)),
                            key="pd_vv_struct_margin_min_v389",
                        )


                # --- Damage→Strength Coupling Authority (optional) ---
                with st.expander("Irradiation damage → strength coupling", expanded=False):
                    st.caption(
                        "Deterministic degradation envelope that couples activation DPA-rate proxy to structural allowables, "
                        "yielding *derived* degraded margins (truth remains immutable). OFF by default. "
                        "Optional degraded-margin minima are explicit; NaN disables."
                    )
                    include_damage_strength_coupling_v393 = st.checkbox(
                        "Enable irradiation damage → strength coupling",
                        value=bool(getattr(defaults, "include_damage_strength_coupling_v393", False)),
                        key="pd_include_damage_strength_coupling_v393",
                    )
                    dS1, dS2 = st.columns(2)
                    with dS1:
                        design_life_fpy_v393 = st.number_input(
                            "Design life for damage accumulation (FPY)",
                            min_value=0.0,
                            value=float(getattr(defaults, "design_life_fpy_v393", 10.0)),
                            key="pd_design_life_fpy_v393",
                        )
                        k_allow_deg_per_dpa_v393 = st.number_input(
                            "Degradation slope k (1/DPA)",
                            min_value=0.0,
                            value=float(getattr(defaults, "k_allow_deg_per_dpa_v393", 0.003)),
                            key="pd_k_allow_deg_per_dpa_v393",
                        )
                        min_allow_frac_v393 = st.number_input(
                            "Minimum allowable fraction floor (-)",
                            min_value=0.0,
                            max_value=1.0,
                            value=float(getattr(defaults, "min_allow_frac_v393", 0.50)),
                            key="pd_min_allow_frac_v393",
                        )
                        tf_struct_margin_degraded_min_v393 = st.number_input(
                            "TF degraded margin min (-) (NaN disables)",
                            value=float(getattr(defaults, "tf_struct_margin_degraded_min_v393", float('nan'))),
                            key="pd_tf_struct_margin_degraded_min_v393",
                        )
                        cs_struct_margin_degraded_min_v393 = st.number_input(
                            "CS degraded margin min (-) (NaN disables)",
                            value=float(getattr(defaults, "cs_struct_margin_degraded_min_v393", float('nan'))),
                            key="pd_cs_struct_margin_degraded_min_v393",
                        )
                        vv_struct_margin_degraded_min_v393 = st.number_input(
                            "VV degraded margin min (-) (NaN disables)",
                            value=float(getattr(defaults, "vv_struct_margin_degraded_min_v393", float('nan'))),
                            key="pd_vv_struct_margin_degraded_min_v393",
                        )
                    with dS2:
                        dpa_factor_tf_v393 = st.number_input(
                            "DPA shielding factor TF (-)",
                            min_value=0.0,
                            value=float(getattr(defaults, "dpa_factor_tf_v393", 0.05)),
                            key="pd_dpa_factor_tf_v393",
                            help="Proxy: DPA_TF = DPA_rate proxy × life × factor.",
                        )
                        dpa_factor_cs_v393 = st.number_input(
                            "DPA shielding factor CS/PF (-)",
                            min_value=0.0,
                            value=float(getattr(defaults, "dpa_factor_cs_v393", 0.05)),
                            key="pd_dpa_factor_cs_v393",
                        )
                        dpa_factor_vv_v393 = st.number_input(
                            "DPA shielding factor vacuum vessel (-)",
                            min_value=0.0,
                            value=float(getattr(defaults, "dpa_factor_vv_v393", 0.20)),
                            key="pd_dpa_factor_vv_v393",
                        )


                # --- Neutronics & Activation Authority 3.0 (optional) ---
                with st.expander("Activation & waste routing", expanded=False):
                    st.caption("Deterministic shielding envelope + activation index + FW damage proxies. Governance-only; OFF by default. Optional minima/caps are explicit; NaN disables.")
                    include_neutronics_activation_v390 = st.checkbox(
                        "Enable activation & waste routing",
                        value=bool(getattr(defaults, "include_neutronics_activation_v390", False)),
                        key="pd_include_neutronics_activation_v390",
                    )
                    blanket_class_v390 = st.selectbox(
                        "Blanket class",
                        options=["STANDARD", "DEMO", "PILOT", "COMPACT", "HEAVY_SHIELD"],
                        index=["STANDARD", "DEMO", "PILOT", "COMPACT", "HEAVY_SHIELD"].index(str(getattr(defaults, "blanket_class_v390", "STANDARD") or "STANDARD").upper()) if str(getattr(defaults, "blanket_class_v390", "STANDARD") or "STANDARD").upper() in ["STANDARD", "DEMO", "PILOT", "COMPACT", "HEAVY_SHIELD"] else 0,
                        key="pd_blanket_class_v390",
                        help="Selects conservative regime multipliers for shielding/activation envelope.",
                    )
                    nA1, nA2 = st.columns(2)
                    with nA1:
                        shield_req_Pfus_exp_v390 = st.number_input(
                            "Shield requirement exponent a for Pfus (-)",
                            value=float(getattr(defaults, "shield_req_Pfus_exp_v390", 0.25)),
                            key="pd_shield_req_Pfus_exp_v390",
                        )
                        shield_req_qwall_exp_v390 = st.number_input(
                            "Shield requirement exponent b for q_wall (-)",
                            value=float(getattr(defaults, "shield_req_qwall_exp_v390", 0.50)),
                            key="pd_shield_req_qwall_exp_v390",
                        )
                        fw_dpa_per_fpy_per_MWm2_v390 = st.number_input(
                            "FW DPA rate coefficient k (DPA/FPY per MW/m²)",
                            min_value=0.0,
                            value=float(getattr(defaults, "fw_dpa_per_fpy_per_MWm2_v390", 15.0)),
                            key="pd_fw_dpa_per_fpy_per_MWm2_v390",
                        )
                        fw_dpa_limit_v390 = st.number_input(
                            "FW DPA total limit (DPA)",
                            min_value=0.0,
                            value=float(getattr(defaults, "fw_dpa_limit_v390", 20.0)),
                            key="pd_fw_dpa_limit_v390",
                        )
                    with nA2:
                        shield_margin_min_cm_v390 = st.number_input(
                            "Min shield margin (t_eff - t_req) (cm) (NaN disables)",
                            value=float(getattr(defaults, "shield_margin_min_cm_v390", float('nan'))),
                            key="pd_shield_margin_min_cm_v390",
                        )
                        fw_life_min_fpy_v390 = st.number_input(
                            "Min FW lifetime (FPY) (NaN disables)",
                            value=float(getattr(defaults, "fw_life_min_fpy_v390", float('nan'))),
                            key="pd_fw_life_min_fpy_v390",
                        )
                        dpa_per_fpy_max_v390 = st.number_input(
                            "Max FW DPA rate (DPA/FPY) (NaN disables)",
                            value=float(getattr(defaults, "dpa_per_fpy_max_v390", float('nan'))),
                            key="pd_dpa_per_fpy_max_v390",
                        )
                        activation_index_max_v390 = st.number_input(
                            "Max activation index (-) (NaN disables)",
                            value=float(getattr(defaults, "activation_index_max_v390", float('nan'))),
                            key="pd_activation_index_max_v390",
                        )



                # --- Neutronics Shield Attenuation Authority (optional) ---
                with st.expander("Shield attenuation model", expanded=False):
                    st.caption(
                        "Deterministic attenuation-length envelope for ex-vessel fluence (TF case / cryostat) and outside-bioshield dose proxy. "
                        "Governance-only; OFF by default. Optional caps are explicit; NaN disables."
                    )
                    include_neutronics_shield_attenuation_v392 = st.checkbox(
                        "Enable shield attenuation model",
                        value=bool(getattr(defaults, "include_neutronics_shield_attenuation_v392", False)),
                        key="pd_include_neutronics_shield_attenuation_v392",
                    )
                    nS1, nS2 = st.columns(2)
                    with nS1:
                        gap_to_tf_case_m_v392 = st.number_input(
                            "Gap to TF case (m)",
                            min_value=0.0,
                            value=float(getattr(defaults, "gap_to_tf_case_m_v392", 0.20)),
                            key="pd_gap_to_tf_case_m_v392",
                        )
                        gap_to_cryostat_m_v392 = st.number_input(
                            "Gap to cryostat (m)",
                            min_value=0.0,
                            value=float(getattr(defaults, "gap_to_cryostat_m_v392", 0.80)),
                            key="pd_gap_to_cryostat_m_v392",
                        )
                        gap_to_bioshield_m_v392 = st.number_input(
                            "Gap to bioshield (m)",
                            min_value=0.0,
                            value=float(getattr(defaults, "gap_to_bioshield_m_v392", 1.20)),
                            key="pd_gap_to_bioshield_m_v392",
                        )
                        t_bioshield_m_v392 = st.number_input(
                            "Bioshield thickness (m)",
                            min_value=0.0,
                            value=float(getattr(defaults, "t_bioshield_m_v392", 1.20)),
                            key="pd_t_bioshield_m_v392",
                        )
                        use_inv_square_geom_v392 = st.checkbox(
                            "Use inverse-square geometric dilution",
                            value=bool(getattr(defaults, "use_inv_square_geom_v392", True)),
                            key="pd_use_inv_square_geom_v392",
                            help="Screening-only 1/r^2 dilution using R0 as reference; disable for conservative (no dilution) envelope.",
                        )
                    with nS2:
                        atten_len_stack_m_v392 = st.number_input(
                            "Attenuation length (stack) override (m) (NaN -> use atten_len_m)",
                            value=float(getattr(defaults, "atten_len_stack_m_v392", float('nan'))),
                            key="pd_atten_len_stack_m_v392",
                        )
                        atten_len_bioshield_m_v392 = st.number_input(
                            "Attenuation length (bioshield) (m)",
                            min_value=1e-6,
                            value=float(getattr(defaults, "atten_len_bioshield_m_v392", 0.35)),
                            key="pd_atten_len_bioshield_m_v392",
                        )
                        dose_uSv_h_per_flux_n_m2_s_v392 = st.number_input(
                            "Dose conversion proxy (uSv/h per n/m²/s)",
                            min_value=0.0,
                            value=float(getattr(defaults, "dose_uSv_h_per_flux_n_m2_s_v392", 1.0e-20)),
                            format="%.3e",
                            key="pd_dose_uSv_h_per_flux_n_m2_s_v392",
                        )
                        tf_case_fluence_max_n_m2_per_fpy_v392 = st.number_input(
                            "Max TF-case fluence (n/m²/FPY) (NaN disables)",
                            value=float(getattr(defaults, "tf_case_fluence_max_n_m2_per_fpy_v392", float('nan'))),
                            format="%.3e",
                            key="pd_tf_case_fluence_max_n_m2_per_fpy_v392",
                        )
                        cryostat_fluence_max_n_m2_per_fpy_v392 = st.number_input(
                            "Max cryostat fluence (n/m²/FPY) (NaN disables)",
                            value=float(getattr(defaults, "cryostat_fluence_max_n_m2_per_fpy_v392", float('nan'))),
                            format="%.3e",
                            key="pd_cryostat_fluence_max_n_m2_per_fpy_v392",
                        )
                        bioshield_dose_rate_max_uSv_h_v392 = st.number_input(
                            "Max bioshield dose rate (uSv/h) (NaN disables)",
                            value=float(getattr(defaults, "bioshield_dose_rate_max_uSv_h_v392", float('nan'))),
                            key="pd_bioshield_dose_rate_max_uSv_h_v392",
                        )



                # --- Neutronics & Materials Authority 4.0 — Library Stack (optional) ---
                with st.expander("Nuclear materials library", expanded=False):
                    st.caption(
                        "Deterministic governance overlay: explicit multi-layer shielding/blanket stack (material+thickness) with "
                        "3-group attenuation ledger and derived DPA/He/activation + TBR-lite proxy. OFF by default. "
                        "No Monte Carlo; no solvers; truth unchanged."
                    )
                    include_neutronics_materials_library_v403 = st.checkbox(
                        "Enable NM library stack authority",
                        value=bool(getattr(defaults, "include_neutronics_materials_library_v403", False)),
                        key="pd_include_neutronics_materials_library_v403",
                    )
                    cS1, cS2 = st.columns([1.0, 1.0])
                    with cS1:
                        nm_group_frac_fast_v403 = st.number_input(
                            "Incident fast-group fraction",
                            min_value=0.0,
                            max_value=1.0,
                            value=float(getattr(defaults, "nm_group_frac_fast_v403", 0.90)),
                            step=0.01,
                            key="pd_nm_group_frac_fast_v403",
                        )
                        nm_group_frac_epi_v403 = st.number_input(
                            "Incident epi-group fraction",
                            min_value=0.0,
                            max_value=1.0,
                            value=float(getattr(defaults, "nm_group_frac_epi_v403", 0.08)),
                            step=0.01,
                            key="pd_nm_group_frac_epi_v403",
                        )
                        nm_group_frac_therm_v403 = st.number_input(
                            "Incident thermal-group fraction",
                            min_value=0.0,
                            max_value=1.0,
                            value=float(getattr(defaults, "nm_group_frac_therm_v403", 0.02)),
                            step=0.01,
                            key="pd_nm_group_frac_therm_v403",
                        )
                    with cS2:
                        dpa_fw_max_v403 = st.number_input(
                            "FW DPA max (DPA/FPY) (NaN disables)",
                            value=float(getattr(defaults, "dpa_fw_max_v403", float('nan'))),
                            key="pd_dpa_fw_max_v403",
                        )
                        he_appm_fw_max_v403 = st.number_input(
                            "FW He max (appm/FPY) (NaN disables)",
                            value=float(getattr(defaults, "he_appm_fw_max_v403", float('nan'))),
                            key="pd_he_appm_fw_max_v403",
                        )
                        cooldown_burden_max_days_v403 = st.number_input(
                            "Cooldown burden max (days) (NaN disables)",
                            value=float(getattr(defaults, "cooldown_burden_max_days_v403", float('nan'))),
                            key="pd_cooldown_burden_max_days_v403",
                        )
                        tbr_proxy_min_v403 = st.number_input(
                            "TBR proxy min (-) (NaN disables)",
                            value=float(getattr(defaults, "tbr_proxy_min_v403", float('nan'))),
                            key="pd_tbr_proxy_min_v403",
                        )
                        fast_attenuation_min_v403 = st.number_input(
                            "Fast attenuation min (-) (NaN disables)",
                            value=float(getattr(defaults, "fast_attenuation_min_v403", float('nan'))),
                            key="pd_fast_attenuation_min_v403",
                        )

                    st.markdown("**Stack JSON (layers from plasma-side outward)**")
                    st.caption("Materials available in nuclear materials library: SS316, W, H2O, B4C, LiPb, FLiBe.")
                    nm_stack_json_v403 = st.text_area(
                        "nm_stack_json_v403",
                        value=str(getattr(defaults, "nm_stack_json_v403", "")),
                        height=180,
                        key="pd_nm_stack_json_v403",
                        help="JSON list of {material, thickness_m, density_factor}. Deterministic; parsed only when compute is pressed.",
                    )


                


                # --- Nuclear Data Authority Deepening (optional) ---
                with st.expander("Nuclear data authority", expanded=False):
                    st.caption(
                        "Governance-only overlay: multi-group attenuation through the NM stack using an explicitly versioned "
                        "dataset registry with SHA-256 provenance. Screening proxy only (no MC transport, no spectral iteration)."
                    )
                    include_nuclear_data_authority_v407 = st.checkbox(
                        "Enable nuclear data authority",
                        value=bool(getattr(defaults, "include_nuclear_data_authority_v407", False)),
                        key="pd_include_nuclear_data_authority_v407",
                    )
                    try:
                        from src.nuclear_data import list_dataset_ids

                        _dataset_ids_v407 = list_dataset_ids()
                    except Exception:
                        _dataset_ids_v407 = ["SCREENING_PROXY_V407"]
                    try:
                        from src.nuclear_data.group_structures import GROUP_STRUCTURES

                        _group_ids_v407 = sorted(GROUP_STRUCTURES.keys())
                    except Exception:
                        _group_ids_v407 = ["G6_V407"]

                    nuclear_dataset_id_v407 = st.selectbox(
                        "Dataset id",
                        options=_dataset_ids_v407,
                        index=_dataset_ids_v407.index("SCREENING_PROXY_V407") if "SCREENING_PROXY_V407"in _dataset_ids_v407 else 0,
                        key="pd_nuclear_dataset_id_v407",
                        help=(
                            "Built-in default is a screening-proxy table (not ENDF/TENDL-derived). "
                            "Dataset intake allows importing external datasets into data/nuclear_datasets with explicit provenance + SHA-256 pinning."
                        ),
                    )
                    nuclear_group_structure_id_v407 = st.selectbox(
                        "Group structure",
                        options=_group_ids_v407,
                        index=_group_ids_v407.index("G6_V407") if "G6_V407"in _group_ids_v407 else 0,
                        key="pd_nuclear_group_structure_id_v407",
                    )

                # --- Nuclear Dataset Intake & Provenance Builder (external, firewalled) ---
                with st.expander("Nuclear dataset intake & provenance builder", expanded=False):
                    st.caption(
                        "Imports external multi-group screening datasets into data/nuclear_datasets with strict schema validation and "
                        "SHA-256 pinning. This is a tooling layer only; it does not modify plasma truth physics." 
                    )
                    st.markdown("**Input options**")
                    st.markdown("1) Upload a single dataset JSON matching the NuclearDataset schema, or")
                    st.markdown("2) Upload metadata JSON + sigma-removal CSV and supply spectrum/response vectors.")

                    up_json = st.file_uploader(
                        "Dataset JSON (full schema)",
                        type=["json"],
                        accept_multiple_files=False,
                        key="v408_dataset_json_uploader",
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        up_meta = st.file_uploader(
                            "Metadata JSON (alternative path)",
                            type=["json"],
                            accept_multiple_files=False,
                            key="v408_metadata_json_uploader",
                        )
                    with c2:
                        up_sigma = st.file_uploader(
                            "Sigma-removal CSV (materials x groups)",
                            type=["csv"],
                            accept_multiple_files=False,
                            key="v408_sigma_csv_uploader",
                        )

                    st.markdown("**Vectors (only used for metadata+CSV path)**")
                    v_spectrum = st.text_input(
                        "Spectrum fractions (comma-separated; must sum to 1)",
                        value="0.65,0.20,0.08,0.04,0.02,0.01",
                        key="v408_spectrum_text",
                    )
                    v_tbrw = st.text_input(
                        "TBR response weights (comma-separated)",
                        value="1.0,0.9,0.6,0.3,0.15,0.05",
                        key="v408_tbrw_text",
                    )

                    build_btn = st.button("Build + validate dataset", key="v408_build_btn")
                    save_btn = st.button("Save dataset to registry (data/nuclear_datasets)", key="v408_save_btn")

                    if "v408_built_dataset"not in st.session_state:
                        st.session_state["v408_built_dataset"] = None
                        st.session_state["v408_built_dataset_error"] = ""

                    def _parse_vec_txt(txt: str) -> list[float]:
                        return [float(x.strip()) for x in txt.split(",") if x.strip()]

                    if build_btn:
                        try:
                            from src.nuclear_data.intake import (
                                dataset_from_json,
                                dataset_from_metadata_and_csv,
                                canonical_dataset_json,
                            )

                            ds = None
                            if up_json is not None:
                                ds = dataset_from_json(up_json.getvalue().decode("utf-8"))
                            else:
                                if up_meta is None or up_sigma is None:
                                    raise ValueError("Provide either dataset JSON, or metadata JSON + sigma CSV")
                                ds = dataset_from_metadata_and_csv(
                                    metadata_json_text=up_meta.getvalue().decode("utf-8"),
                                    sigma_removal_csv_text=up_sigma.getvalue().decode("utf-8"),
                                    spectrum_frac_fw=_parse_vec_txt(v_spectrum),
                                    tbr_response_weight=_parse_vec_txt(v_tbrw),
                                )
                            st.session_state["v408_built_dataset"] = ds
                            st.session_state["v408_built_dataset_error"] = ""

                            st.success("Dataset parsed and validated.")
                            st.code(canonical_dataset_json(ds), language="json")
                            st.markdown(f"**SHA-256:** `{ds.sha256}`")
                        except Exception as e:
                            st.session_state["v408_built_dataset"] = None
                            st.session_state["v408_built_dataset_error"] = str(e)
                            st.error(f"Intake failed: {e}")

                    if st.session_state.get("v408_built_dataset_error"):
                        st.warning(st.session_state["v408_built_dataset_error"])

                    if save_btn:
                        try:
                            ds = st.session_state.get("v408_built_dataset", None)
                            if ds is None:
                                raise ValueError("Build a dataset first.")
                            from src.nuclear_data.registry import save_external_dataset, build_dataset_evidence_card_md

                            p = save_external_dataset(ds)
                            (p.parent / f"{ds.dataset_id}.md").write_text(
                                build_dataset_evidence_card_md(ds), encoding="utf-8"
                            )
                            st.success(f"Saved: {p.name}")
                            st.info("Restart the app (or re-open this panel) to refresh the dataset list in selectors.")
                        except Exception as e:
                            st.error(f"Save failed: {e}")
# --- Neutronics & Materials Authority 3.0 — Contract Tiers (optional) ---
                with st.expander("Neutronics contract tiers", expanded=False):
                    st.caption(
                        "Governance-only overlay that applies explicit OPTIMISTIC/NOMINAL/ROBUST contracts to already-computed "
                        "neutronics/materials + activation + shield-attenuation proxies. Reports margins and dominant limiter; OFF by default."
                    )
                    include_neutronics_materials_authority_v401 = st.checkbox(
                        "Enable neutronics/materials contract tiers",
                        value=bool(getattr(defaults, "include_neutronics_materials_authority_v401", False)),
                        key="pd_include_neutronics_materials_authority_v401",
                    )
                    nm_contract_tier_v401 = st.selectbox(
                        "Contract tier",
                        options=["OPTIMISTIC", "NOMINAL", "ROBUST"],
                        index=["OPTIMISTIC", "NOMINAL", "ROBUST"].index(str(getattr(defaults, "nm_contract_tier_v401", "NOMINAL") or "NOMINAL").upper())
                        if str(getattr(defaults, "nm_contract_tier_v401", "NOMINAL") or "NOMINAL").upper() in ["OPTIMISTIC", "NOMINAL", "ROBUST"] else 1,
                        key="pd_nm_contract_tier_v401",
                    )
                    nm_fragile_margin_frac_v401 = st.number_input(
                        "Fragile threshold on min margin (-)",
                        min_value=0.0,
                        max_value=0.50,
                        value=float(getattr(defaults, "nm_fragile_margin_frac_v401", 0.10)),
                        step=0.01,
                        key="pd_nm_fragile_margin_frac_v401",
                        help="Min normalized margin below this is classified FRAGILE; below 0 is INFEASIBLE.",
                    )
                    st.markdown("**Optional per-item overrides (NaN disables override)**")
                    o1, o2 = st.columns(2)
                    with o1:
                        tf_case_fluence_max_n_m2_per_fpy_override_v401 = st.number_input(
                            "TF-case fluence max override (n/m²/FPY)",
                            value=float(getattr(defaults, "tf_case_fluence_max_n_m2_per_fpy_override_v401", float('nan'))),
                            format="%.3e",
                            key="pd_tf_case_fluence_max_n_m2_per_fpy_override_v401",
                        )
                        bioshield_dose_rate_max_uSv_h_override_v401 = st.number_input(
                            "Bioshield dose-rate max override (uSv/h)",
                            value=float(getattr(defaults, "bioshield_dose_rate_max_uSv_h_override_v401", float('nan'))),
                            key="pd_bioshield_dose_rate_max_uSv_h_override_v401",
                        )
                        P_nuc_TF_max_MW_override_v401 = st.number_input(
                            "TF nuclear heating max override (MW)",
                            value=float(getattr(defaults, "P_nuc_TF_max_MW_override_v401", float('nan'))),
                            key="pd_P_nuc_TF_max_MW_override_v401",
                        )
                        dpa_per_fpy_max_override_v401 = st.number_input(
                            "FW DPA-rate max override (DPA/FPY)",
                            value=float(getattr(defaults, "dpa_per_fpy_max_override_v401", float('nan'))),
                            key="pd_dpa_per_fpy_max_override_v401",
                        )
                    with o2:
                        fw_He_total_limit_appm_override_v401 = st.number_input(
                            "FW He total max override (appm)",
                            value=float(getattr(defaults, "fw_He_total_limit_appm_override_v401", float('nan'))),
                            key="pd_fw_He_total_limit_appm_override_v401",
                        )
                        activation_index_max_override_v401 = st.number_input(
                            "Activation index max override (-)",
                            value=float(getattr(defaults, "activation_index_max_override_v401", float('nan'))),
                            key="pd_activation_index_max_override_v401",
                        )
                        TBR_min_override_v401 = st.number_input(
                            "TBR min override (-)",
                            value=float(getattr(defaults, "TBR_min_override_v401", float('nan'))),
                            key="pd_TBR_min_override_v401",
                        )


                

                # --- Structural Life Authority 3.0 (optional) ---
                with st.expander("Structural life authority", expanded=False):
                    st.caption(
                        "Deterministic structural life envelopes: irradiation+temperature degraded allowables, "
                        "fatigue (Miner proxy), creep-rupture proxy, and optional buckling margins. "
                        "Governance-only overlay (no truth mutation)."
                    )
                    include_structural_life_v404 = st.checkbox(
                        "Enable structural life authority",
                        value=bool(getattr(defaults, "include_structural_life_v404", False)),
                        key="pd_include_structural_life_v404",
                    )
                    struct_min_margin_frac_v404 = st.number_input(
                        "Minimum structural life margin (NaN disables)",
                        value=float(getattr(defaults, "struct_min_margin_frac_v404", float('nan'))),
                        key="pd_struct_min_margin_frac_v404",
                    )
                    colA, colB, colC = st.columns(3)
                    with colA:
                        pulse_count_v404 = st.number_input(
                            "Pulse count (NaN -> default)",
                            value=float(getattr(defaults, "pulse_count_v404", float('nan'))),
                            key="pd_pulse_count_v404",
                        )
                    with colB:
                        hot_fraction_v404 = st.number_input(
                            "Hot fraction",
                            value=float(getattr(defaults, "hot_fraction_v404", 0.2)),
                            min_value=0.0, max_value=1.0,
                            key="pd_hot_fraction_v404",
                        )
                    with colC:
                        service_years_v404 = st.number_input(
                            "Service years",
                            value=float(getattr(defaults, "service_years_v404", 1.0)),
                            min_value=0.1, max_value=60.0,
                            key="pd_service_years_v404",
                        )

                    st.markdown("**Materials**")
                    colM1, colM2, colM3 = st.columns(3)
                    with colM1:
                        material_fw_v404 = st.selectbox(
                            "FW material",
                            options=["EUROFER","SS316","INCONEL","W","CuCrZr"],
                            index=["EUROFER","SS316","INCONEL","W","CuCrZr"].index(str(getattr(defaults,"material_fw_v404","EUROFER"))),
                            key="pd_material_fw_v404",
                        )
                    with colM2:
                        material_vv_v404 = st.selectbox(
                            "VV material",
                            options=["SS316","EUROFER","INCONEL","W","CuCrZr"],
                            index=["SS316","EUROFER","INCONEL","W","CuCrZr"].index(str(getattr(defaults,"material_vv_v404","SS316"))),
                            key="pd_material_vv_v404",
                        )
                    with colM3:
                        material_tf_v404 = st.selectbox(
                            "TF material",
                            options=["INCONEL","SS316","EUROFER","W","CuCrZr"],
                            index=["INCONEL","SS316","EUROFER","W","CuCrZr"].index(str(getattr(defaults,"material_tf_v404","INCONEL"))),
                            key="pd_material_tf_v404",
                        )

                    st.markdown("**Temperatures [K]**")
                    colT1, colT2, colT3 = st.columns(3)
                    with colT1:
                        T_fw_K_v404 = st.number_input(
                            "T_fw [K]",
                            value=float(getattr(defaults, "T_fw_K_v404", 700.0)),
                            key="pd_T_fw_K_v404",
                        )
                    with colT2:
                        T_vv_K_v404 = st.number_input(
                            "T_vv [K]",
                            value=float(getattr(defaults, "T_vv_K_v404", 450.0)),
                            key="pd_T_vv_K_v404",
                        )
                    with colT3:
                        T_tf_K_v404 = st.number_input(
                            "T_tf [K]",
                            value=float(getattr(defaults, "T_tf_K_v404", 350.0)),
                            key="pd_T_tf_K_v404",
                        )

                    st.markdown("**Buckling geometry proxies (optional)**")
                    colG1, colG2, colG3 = st.columns(3)
                    with colG1:
                        vv_t_m_v404 = st.number_input(
                            "VV thickness [m] (NaN disables)",
                            value=float(getattr(defaults, "vv_t_m_v404", float('nan'))),
                            key="pd_vv_t_m_v404",
                        )
                        vv_R_m_v404 = st.number_input(
                            "VV radius [m]",
                            value=float(getattr(defaults, "vv_R_m_v404", float('nan'))),
                            key="pd_vv_R_m_v404",
                        )
                    with colG2:
                        tf_t_m_v404 = st.number_input(
                            "TF case thickness [m]",
                            value=float(getattr(defaults, "tf_t_m_v404", float('nan'))),
                            key="pd_tf_t_m_v404",
                        )
                        tf_R_m_v404 = st.number_input(
                            "TF case radius [m]",
                            value=float(getattr(defaults, "tf_R_m_v404", float('nan'))),
                            key="pd_tf_R_m_v404",
                        )
                    with colG3:
                        fw_t_m_v404 = st.number_input(
                            "FW panel thickness [m]",
                            value=float(getattr(defaults, "fw_t_m_v404", float('nan'))),
                            key="pd_fw_t_m_v404",
                        )
                        fw_R_m_v404 = st.number_input(
                            "FW panel radius [m]",
                            value=float(getattr(defaults, "fw_R_m_v404", float('nan'))),
                            key="pd_fw_R_m_v404",
                        )

# --- Authority Dominance Engine 2.0 (global regime & ranking) ---
                with st.expander("Global authority dominance engine", expanded=False):
                    st.caption(
                        "Deterministic governance overlay: aggregates major authority margins into a global dominance ranking, "
                        "classifies the limiting regime (MAGNET/EXHAUST/CONTROL/TRANSPORT/PROFILE/NM), and flags feasibility mirages "
                        "(feasible but credibility-fragile). No solvers; truth is unchanged."
                    )
                    include_authority_dominance_v402 = st.checkbox(
                        "Enable global authority dominance engine",
                        value=bool(getattr(defaults, "include_authority_dominance_v402", True)),
                        key="pd_include_authority_dominance_v402",
                    )
                    cD1, cD2, cD3 = st.columns(3)
                    with cD1:
                        transport_spread_ref_v402 = st.number_input(
                            "Transport spread ref (τE_max/τE_min)",
                            min_value=1.1,
                            value=float(getattr(defaults, "transport_spread_ref_v402", 3.0) or 3.0),
                            step=0.1,
                            key="pd_transport_spread_ref_v402",
                        )
                    with cD2:
                        profile_peaking_p_ref_v402 = st.number_input(
                            "Profile p-peaking ref", min_value=1.1,
                            value=float(getattr(defaults, "profile_peaking_p_ref_v402", 3.0) or 3.0),
                            step=0.1,
                            key="pd_profile_peaking_p_ref_v402",
                        )
                    with cD3:
                        zeff_ref_max_v402 = st.number_input(
                            "Zeff ref max", min_value=1.1,
                            value=float(getattr(defaults, "zeff_ref_max_v402", 2.5) or 2.5),
                            step=0.1,
                            key="pd_zeff_ref_max_v402",
                        )



                # --- Materials & Lifetime Tightening (optional) ---
                with st.expander("Materials lifetime ledger", expanded=False):
                    st.caption(
                        "Deterministic governance overlay: adds divertor + magnet lifetime proxies, annualized replacement cost, "
                        "and replacement-downtime coupling to a capacity factor used by economics overlays. OFF by default; truth is unchanged."
                    )
                    include_materials_lifetime_v384 = st.checkbox(
                        "Enable materials & lifetime tightening",
                        value=bool(getattr(defaults, "include_materials_lifetime_v384", False)),
                        key="pd_include_materials_lifetime_v384",
                    )
                    cML1, cML2 = st.columns(2)
                    with cML1:
                        divertor_life_ref_yr = st.number_input(
                            "Divertor life ref (yr)",
                            min_value=0.1,
                            value=float(getattr(defaults, "divertor_life_ref_yr", 3.0) or 3.0),
                            step=0.1,
                            key="pd_divertor_life_ref_yr_v384",
                        )
                        divertor_q_ref_MW_m2 = st.number_input(
                            "Divertor q_ref (MW/m²)",
                            min_value=0.1,
                            value=float(getattr(defaults, "divertor_q_ref_MW_m2", 10.0) or 10.0),
                            step=0.5,
                            key="pd_divertor_q_ref_v384",
                        )
                        divertor_q_exp = st.number_input(
                            "Divertor q exponent", min_value=0.0,
                            value=float(getattr(defaults, "divertor_q_exp", 2.0) or 2.0),
                            step=0.1,
                            key="pd_divertor_q_exp_v384",
                        )
                        divertor_capex_fraction_of_total = st.number_input(
                            "Divertor CAPEX fraction of total", min_value=0.0, max_value=0.5,
                            value=float(getattr(defaults, "divertor_capex_fraction_of_total", 0.05) or 0.05),
                            step=0.01,
                            key="pd_divertor_capex_frac_v384",
                        )
                    with cML2:
                        magnet_life_ref_yr = st.number_input(
                            "Magnet life ref (yr)",
                            min_value=0.1,
                            value=float(getattr(defaults, "magnet_life_ref_yr", 30.0) or 30.0),
                            step=1.0,
                            key="pd_magnet_life_ref_yr_v384",
                        )
                        magnet_margin_ref = st.number_input(
                            "Magnet margin ref (fraction)",
                            min_value=0.001,
                            value=float(getattr(defaults, "magnet_margin_ref", 0.10) or 0.10),
                            step=0.01,
                            key="pd_magnet_margin_ref_v384",
                        )
                        magnet_margin_exp = st.number_input(
                            "Magnet margin exponent", min_value=0.0,
                            value=float(getattr(defaults, "magnet_margin_exp", 1.5) or 1.5),
                            step=0.1,
                            key="pd_magnet_margin_exp_v384",
                        )

                    st.markdown("**Downtime → capacity factor coupling**")
                    cML3, cML4 = st.columns(2)
                    with cML3:
                        base_capacity_factor = st.number_input(
                            "Base capacity factor (before replacements)",
                            min_value=0.0,
                            max_value=1.0,
                            value=float(getattr(defaults, "base_capacity_factor", 0.75) or 0.75),
                            step=0.01,
                            key="pd_base_cf_v384",
                        )
                        capacity_factor_max = st.number_input(
                            "Capacity factor max (cap)",
                            min_value=0.0,
                            max_value=1.0,
                            value=float(getattr(defaults, "capacity_factor_max", 0.95) or 0.95),
                            step=0.01,
                            key="pd_cf_max_v384",
                        )
                        fw_downtime_days = st.number_input(
                            "FW replacement downtime (days)",
                            min_value=0.0,
                            value=float(getattr(defaults, "fw_downtime_days", 30.0) or 30.0),
                            step=1.0,
                            key="pd_fw_dt_days_v384",
                        )
                        blanket_downtime_days = st.number_input(
                            "Blanket replacement downtime (days)",
                            min_value=0.0,
                            value=float(getattr(defaults, "blanket_downtime_days", 60.0) or 60.0),
                            step=1.0,
                            key="pd_blanket_dt_days_v384",
                        )
                    with cML4:
                        divertor_downtime_days = st.number_input(
                            "Divertor replacement downtime (days)",
                            min_value=0.0,
                            value=float(getattr(defaults, "divertor_downtime_days", 20.0) or 20.0),
                            step=1.0,
                            key="pd_divertor_dt_days_v384",
                        )
                        magnet_downtime_days = st.number_input(
                            "Magnet replacement downtime (days)",
                            min_value=0.0,
                            value=float(getattr(defaults, "magnet_downtime_days", 120.0) or 120.0),
                            step=5.0,
                            key="pd_magnet_dt_days_v384",
                        )
                        fw_capex_fraction_of_blanket = st.number_input(
                            "FW CAPEX fraction of blanket/shield CAPEX",
                            min_value=0.0,
                            max_value=1.0,
                            value=float(getattr(defaults, "fw_capex_fraction_of_blanket", 0.20) or 0.20),
                            step=0.01,
                            key="pd_fw_capex_frac_bs_v384",
                        )
                        blanket_capex_fraction_of_blanket = st.number_input(
                            "Blanket CAPEX fraction of blanket/shield CAPEX",
                            min_value=0.0,
                            max_value=2.0,
                            value=float(getattr(defaults, "blanket_capex_fraction_of_blanket", 1.00) or 1.00),
                            step=0.05,
                            key="pd_blanket_capex_frac_bs_v384",
                        )

                    st.markdown("**Feasibility caps (NaN disables)**")
                    cML5, cML6 = st.columns(2)
                    with cML5:
                        divertor_lifetime_min_yr_v384 = st.number_input(
                            "Min divertor lifetime (yr)",
                            value=float(getattr(defaults, "divertor_lifetime_min_yr_v384", float('nan'))),
                            key="pd_div_life_min_v384",
                        )
                        magnet_lifetime_min_yr_v384 = st.number_input(
                            "Min magnet lifetime (yr)",
                            value=float(getattr(defaults, "magnet_lifetime_min_yr_v384", float('nan'))),
                            key="pd_mag_life_min_v384",
                        )
                        capacity_factor_min_v384 = st.number_input(
                            "Min capacity factor (replacement-coupled)",
                            value=float(getattr(defaults, "capacity_factor_min_v384", float('nan'))),
                            key="pd_cf_min_v384",
                        )
                    with cML6:
                        fw_lifetime_min_yr_v384 = st.number_input(
                            "Min FW lifetime (yr)",
                            value=float(getattr(defaults, "fw_lifetime_min_yr_v384", float('nan'))),
                            key="pd_fw_life_min_v384",
                        )
                        blanket_lifetime_min_yr_v384 = st.number_input(
                            "Min blanket lifetime (yr)",
                            value=float(getattr(defaults, "blanket_lifetime_min_yr_v384", float('nan'))),
                            key="pd_blanket_life_min_v384",
                        )
                        replacement_cost_max_MUSD_per_y_v384 = st.number_input(
                            "Max annualized replacement cost (MUSD/y)",
                            value=float(getattr(defaults, "replacement_cost_max_MUSD_per_y_v384", float('nan'))),
                            key="pd_repl_cost_max_v384",
                        )



                preset = {
                    "Conservative": {
                        "tblanket_m": 0.60, "t_vv_m": 0.08, "t_gap_m": 0.03, "t_tf_struct_m": 0.18, "t_tf_wind_m": 0.12,
                        "Bpeak_factor": 1.30, "sigma_allow_MPa": 800.0, "Tcoil_K": 20.0, "hts_margin_min": 0.20, "Vmax_kV": 18.0,
                        "q_div_max_MW_m2": 7.0, "TBR_min": 1.10, "hts_lifetime_min_yr": 5.0, "P_net_min_MW": 0.0,
                    },
                    "Nominal": {
                        "tblanket_m": 0.50, "t_vv_m": 0.06, "t_gap_m": 0.02, "t_tf_struct_m": 0.15, "t_tf_wind_m": 0.10,
                        "Bpeak_factor": 1.25, "sigma_allow_MPa": 850.0, "Tcoil_K": 20.0, "hts_margin_min": 0.15, "Vmax_kV": 20.0,
                        "q_div_max_MW_m2": 10.0, "TBR_min": 1.05, "hts_lifetime_min_yr": 3.0, "P_net_min_MW": 0.0,
                    },
                    "Aggressive": {
                        "tblanket_m": 0.40, "t_vv_m": 0.05, "t_gap_m": 0.015, "t_tf_struct_m": 0.12, "t_tf_wind_m": 0.08,
                        "Bpeak_factor": 1.20, "sigma_allow_MPa": 900.0, "Tcoil_K": 20.0, "hts_margin_min": 0.10, "Vmax_kV": 25.0,
                        "q_div_max_MW_m2": 15.0, "TBR_min": 1.00, "hts_lifetime_min_yr": 1.0, "P_net_min_MW": 0.0,
                    },
                }[confidence]

                def _maybe(x: float, enabled: bool) -> float:
                    return float(x) if enabled else float("nan")

                clean_knobs = {
                    # Build & radial build
                    "tblanket_m": _maybe(float(_num("Blanket thickness (inboard) (m)", preset["tblanket_m"], 0.01, min_value=0.0)), include_build),
                    "t_vv_m": _maybe(float(_num("Vacuum vessel thickness (inboard) (m)", preset["t_vv_m"], 0.005, min_value=0.0)), include_build),
                    "t_gap_m": _maybe(float(_num("Inboard gap / clearance (m)", preset["t_gap_m"], 0.005, min_value=0.0)), include_build),
                    "t_tf_struct_m": _maybe(float(_num("TF structure thickness (inboard) (m)", preset["t_tf_struct_m"], 0.01, min_value=0.0)), include_build),
                    "t_tf_wind_m": _maybe(float(_num("TF winding pack thickness (inboard) (m)", preset["t_tf_wind_m"], 0.01, min_value=0.0)), include_build),

                    # Magnets & HTS
                    "Bpeak_factor": _maybe(float(_num("Peak-field mapping factor B_peak/B₀ (–)", preset["Bpeak_factor"], 0.01, min_value=1.0)), include_magnets),
                    "sigma_allow_MPa": _maybe(float(_num("Allowable coil hoop stress (MPa)", preset["sigma_allow_MPa"], 10.0, min_value=10.0)), include_magnets),
                    "Tcoil_K": _maybe(float(_num("HTS operating temperature (K)", preset["Tcoil_K"], 1.0, min_value=4.0)), include_magnets),
                    "hts_margin_min": _maybe(float(_num("Minimum HTS critical-current margin (–)", preset["hts_margin_min"], 0.01, min_value=0.0)), include_magnets),
                    "include_hts_critical_surface": bool(st.checkbox("Use HTS critical-surface model (Jc(B,T,ε))", value=False, disabled=not include_magnets, help="Off by default (legacy behavior). When enabled, computes hts_margin_cs using Jc(B,T,ε_tf)/Jop and applies the same hts_margin_min threshold.")),
                    "Vmax_kV": _maybe(float(_num("Max dump voltage limit (kV)", preset["Vmax_kV"], 1.0, min_value=1.0)), include_magnets),

                    # Magnet quench / protection authority
                    "quench_energy_density_max_MJ_m3": _maybe(float(_num("Max allowable quench energy density (MJ/m³)", float('nan'), 1.0, min_value=0.0, help="Used to normalize stored-energy proxy into magnet_quench_risk_proxy. Leave NaN to disable.")), include_magnets),
                    "magnet_quench_risk_max": _maybe(float(_num("Max magnet quench risk proxy (–)", float('nan'), 0.05, min_value=0.0, help="Optional cap on stored-energy/allowable proxy. Leave NaN to disable.")), include_magnets),

                    # Divertor / SOL
                    "q_div_max_MW_m2": _maybe(float(_num("Max divertor heat flux limit (MW/m²)", preset["q_div_max_MW_m2"], 0.5, min_value=0.1)), include_divertor),

                    # Exhaust authority
                    "detachment_index_min": _maybe(float(_num("Detachment index floor (proxy)", float('nan'), 0.01, help="Optional floor on P_SOL/(n_e^2 R). Leave NaN to disable.")), include_divertor),
                    "detachment_index_max": _maybe(float(_num("Detachment index cap (proxy)", float('nan'), 0.01, help="Optional cap on P_SOL/(n_e^2 R). Leave NaN to disable.")), include_divertor),
                    "f_rad_total_max": _maybe(float(_num("Max total radiated fraction f_rad,total (–)", float('nan'), 0.01, min_value=0.0, max_value=1.0, help="Optional cap on (f_rad_core+f_rad_div). Leave NaN to disable.")), include_divertor),
                    "fuel_ion_fraction_min": _maybe(float(_num("Min fuel ion fraction (dilution)", float('nan'), 0.01, min_value=0.0, max_value=1.0, help="Optional minimum fuel-ion fraction (proxy). Leave NaN to disable.")), include_divertor),
                    "Q_effective_min": _maybe(float(_num("Min effective Q (dilution-adjusted)", float('nan'), 0.05, min_value=0.0, help="Optional minimum on Q_eff = Q*fuel^2. Leave NaN to disable.")), include_divertor),

                    # Neutronics & Materials — fast optimistic knobs + explicit contracts
                    "TBR_min": _maybe(float(_num("Minimum tritium breeding ratio (TBR)", preset["TBR_min"], 0.01, min_value=0.0)), include_neutronics),
                    "port_fraction": _maybe(float(_num("Port/penetration fraction (coverage penalty)", float(preset.get("port_fraction", 0.08)), 0.01, min_value=0.0, max_value=0.8, help="Penalty to blanket coverage in the TBR proxy.")), include_neutronics),
                    "li6_enrichment": _maybe(float(_num("Li-6 enrichment fraction (0..1)", float(preset.get("li6_enrichment", 0.30)), 0.01, min_value=0.0, max_value=0.95)), include_neutronics),
                    "blanket_type": str(st.selectbox("Blanket archetype for TBR proxy", options=["LiPb","FLiBe"], index=0, disabled=not include_neutronics, help="Used by the TBR proxy only (transport-free).")),
                    "multiplier_material": str(st.selectbox("Neutron multiplier tag", options=["None","Be","Pb","Be2"], index=0, disabled=not include_neutronics, help="Simple multiplier factor used by the TBR proxy.")),
                    "neutronics_archetype": str(st.selectbox("Nuclear heating partition archetype", options=["standard","heavy_shield","compact"], index=0, disabled=not include_neutronics, help="Chooses a deterministic fraction table for in-vessel nuclear heating.")),
                    "neutronics_domain_enforce": bool(st.checkbox("Enforce neutronics proxy validity domain as HARD", value=False, disabled=not include_neutronics, help="If checked, out-of-range proxy usage (e.g., TBR thickness/coverage domains) becomes a HARD violation. Defaults off to preserve screening behavior.")),
                    "materials_domain_enforce": bool(st.checkbox("Enforce materials admissibility as HARD", value=False, disabled=not include_neutronics, help="If checked, materials window/stress screening constraints upgrade to HARD. Defaults off.")),
                    "hts_lifetime_min_yr": _maybe(float(_num("Minimum HTS lifetime (years)", preset["hts_lifetime_min_yr"], 0.5, min_value=0.0)), include_neutronics),

                    # Optional caps & material tags (NaN disables enforcement)
                    "neutron_wall_load_max_MW_m2": _maybe(float(_num("Max neutron wall load (MW/m²) (optional)", float('nan'), 0.1, min_value=0.0, help="Leave NaN to disable enforcement.")), include_neutronics),
                    "fw_dpa_max_per_year": _maybe(float(_num("Max first-wall dpa per year (optional)", float('nan'), 0.5, min_value=0.0, help="Order-of-magnitude proxy derived from wall load. Leave NaN to disable.")), include_neutronics),
                    "fw_lifetime_min_yr": _maybe(float(_num("Min first-wall replacement lifetime (yr) (optional)", float('nan'), 0.5, min_value=0.0, help="Uses DPA/He rate proxies + material limits. Leave NaN to disable.")), include_neutronics),
                    "blanket_lifetime_min_yr": _maybe(float(_num("Min blanket replacement lifetime (yr) (optional)", float('nan'), 0.5, min_value=0.0, help="Uses DPA/He rate proxies + material limits. Leave NaN to disable.")), include_neutronics),

                    # Materials lifetime closure: deterministic policy/cadence knobs
                    "plant_design_lifetime_yr": _maybe(float(_num(
                        "Plant design lifetime (yr) (materials policy)",
                        float(getattr(defaults, "plant_design_lifetime_yr", 30.0) or 30.0),
                        1.0,
                        min_value=1.0,
                        help="Used by materials lifetime closure to compute replacement counts/costs. No time-domain simulation.",
                    )), include_neutronics),
                    "materials_life_cover_plant_enforce": bool(st.checkbox(
                        "Enforce FW/blanket lifetime ≥ plant lifetime (HARD)",
                        value=bool(getattr(defaults, "materials_life_cover_plant_enforce", False)),
                        disabled=not include_neutronics,
                        help="Policy constraint: requires fw_lifetime_yr and blanket_lifetime_yr to cover plant_design_lifetime_yr when enabled.",
                    )),
                    "fw_replace_interval_min_yr": _maybe(float(_num(
                        "Min FW replacement cadence (yr) (optional)",
                        float(getattr(defaults, "fw_replace_interval_min_yr", float('nan'))),
                        0.5,
                        min_value=0.0,
                        help="Optional minimum on the FW replacement interval used by the replacement ledger. Leave NaN to disable.",
                    )), include_neutronics),
                    "blanket_replace_interval_min_yr": _maybe(float(_num(
                        "Min blanket replacement cadence (yr) (optional)",
                        float(getattr(defaults, "blanket_replace_interval_min_yr", float('nan'))),
                        0.5,
                        min_value=0.0,
                        help="Optional minimum on the blanket replacement interval used by the replacement ledger. Leave NaN to disable.",
                    )), include_neutronics),
                    "fw_capex_fraction_of_blanket": _maybe(float(_num(
                        "FW CAPEX fraction of blanket+shield (0..1)",
                        float(getattr(defaults, "fw_capex_fraction_of_blanket", 0.20) or 0.20),
                        0.01,
                        min_value=0.0,
                        max_value=1.0,
                        help="Used to estimate FW replacement CAPEX from capex_blanket_shield_MUSD (or a fallback).",
                    )), include_neutronics),
                    "blanket_capex_fraction_of_blanket": _maybe(float(_num(
                        "Blanket CAPEX fraction of blanket+shield (0..1)",
                        float(getattr(defaults, "blanket_capex_fraction_of_blanket", 1.00) or 1.00),
                        0.01,
                        min_value=0.0,
                        max_value=1.0,
                        help="Used to estimate blanket replacement CAPEX from capex_blanket_shield_MUSD (or a fallback).",
                    )), include_neutronics),
                    "P_nuc_total_max_MW": _maybe(float(_num("Max total nuclear heating (MW) (optional)", float('nan'), 1.0, min_value=0.0, help="Stack-based nuclear heating bookkeeping. Leave NaN to disable.")), include_neutronics),
                    "P_nuc_tf_max_MW": _maybe(float(_num("Max TF nuclear heating (MW) (optional)", float('nan'), 0.5, min_value=0.0, help="Stack-based nuclear heating in TF regions. Leave NaN to disable.")), include_neutronics),
                    "P_nuc_pf_max_MW": _maybe(float(_num("Max PF nuclear heating (MW) (optional)", float('nan'), 0.5, min_value=0.0, help="Leakage partition proxy to PF. Leave NaN to disable.")), include_neutronics),
                    "P_nuc_cryo_max_kW": _maybe(float(_num("Max cryo nuclear load (kW) (optional)", float('nan'), 10.0, min_value=0.0, help="Leakage partition proxy to cryoplant. Leave NaN to disable.")), include_neutronics),

                    "shield_material": str(st.selectbox("Shield material tag (attenuation)", options=["WC","B4C","SS316","EUROFER"], index=0, disabled=not include_neutronics, help="Used for stack attenuation and heating partitioning.")),
                    "blanket_material": str(st.selectbox("Blanket material tag (attenuation)", options=["LiPb","FLiBe"], index=0, disabled=not include_neutronics, help="Used for stack attenuation and materials proxies.")),
                    "fw_material": str(st.selectbox("First-wall material tag (materials)", options=["EUROFER","SS316","W","SiC"], index=0, disabled=not include_neutronics, help="Used for temperature window + DPA/He proxies.")),

                    # Materials admissibility: temperature windows & stress (proxy)
                    "T_fw_oper_C": _maybe(float(_num("FW operating temperature (°C) (optional)", float('nan'), 10.0, help="Used only for window checks; no thermal solver.")), include_neutronics),
                    "T_blanket_oper_C": _maybe(float(_num("Blanket operating temperature (°C) (optional)", float('nan'), 10.0, help="Used only for window checks; no thermal solver.")), include_neutronics),
                    "fw_T_enforce": bool(st.checkbox("Enforce FW temperature window as HARD", value=False, disabled=not include_neutronics)),
                    "blanket_T_enforce": bool(st.checkbox("Enforce blanket temperature window as HARD", value=False, disabled=not include_neutronics)),
                    "sigma_fw_oper_MPa": _maybe(float(_num("FW operating stress (MPa) (optional)", float('nan'), 10.0, min_value=0.0, help="Used with irradiation-adjusted allowable stress proxy. Leave NaN to disable.")), include_neutronics),
                    "sigma_blanket_oper_MPa": _maybe(float(_num("Blanket operating stress (MPa) (optional)", float('nan'), 10.0, min_value=0.0, help="Used with irradiation-adjusted allowable stress proxy. Leave NaN to disable.")), include_neutronics),



                    # Fuel-cycle / tritium ledger — optional tight closure
                    "T_reserve_days": _maybe(float(_num("Tritium reserve (days)", 3.0, 0.5, min_value=0.0,
                        help="Reserve inventory proxy: T_inventory_reserve = T_burn * reserve_days.")), include_fuelcycle),
                    "T_processing_margin": _maybe(float(_num("Tritium processing margin factor (–)", 1.25, 0.05, min_value=0.1,
                        help="Multiplies burn throughput to set required processing capacity.")), include_fuelcycle),
                    "T_processing_capacity_min_g_per_day": _maybe(float(_num("Min processing capacity (g/day) (optional)", float('nan'), 10.0, min_value=0.0,
                        help="Optional minimum capacity contract. Leave NaN to disable.")), include_fuelcycle),
                    "T_inventory_min_kg": _maybe(float(_num("Min on-site inventory (kg) (optional)", float('nan'), 0.1, min_value=0.0,
                        help="Optional minimum inventory contract. Leave NaN to disable.")), include_fuelcycle),

                    "include_tritium_tight_closure": bool(st.checkbox(
                        "Enable tight tritium closure (inventory+loss+self-sufficiency)",
                        value=bool(
                            st.session_state.get(
                                "include_tritium_tight_closure",
                                tritium_tight_closure_default(str(st.session_state.get("design_intent", "Power Reactor (net-electric)"))),
                            )
                        ),
                        disabled=not include_fuelcycle,
                        help="When enabled, SHAMS computes in-vessel and total tritium inventory proxies, applies optional loss tightening to TBR_eff, and enforces optional self-sufficiency margins (all algebraic; no iteration). Reactor intent defaults ON (PHYS-010).",
                    )),
                    "T_processing_delay_days": _maybe(float(_num("Processing delay (days) → in-vessel inventory proxy", 1.0, 0.2, min_value=0.0,
                        help="In-vessel inventory proxy: T_in_vessel = T_burn * delay_days.")), include_fuelcycle),
                    "T_in_vessel_max_kg": _maybe(float(_num("Max in-vessel tritium (kg) (optional)", float('nan'), 0.1, min_value=0.0,
                        help="Optional cap on in-vessel inventory proxy. Leave NaN to disable.")), include_fuelcycle),
                    "T_total_inventory_max_kg": _maybe(float(_num("Max total tritium inventory (kg) (optional)", float('nan'), 0.5, min_value=0.0,
                        help="Optional cap on total inventory proxy (reserve+in-vessel+startup). Leave NaN to disable.")), include_fuelcycle),
                    "T_startup_inventory_kg": _maybe(float(_num("Startup tritium inventory (kg) (optional)", float('nan'), 0.5, min_value=0.0,
                        help="Optional startup inventory proxy added to total inventory.")), include_fuelcycle),
                    "T_loss_fraction": _maybe(float(_num("Effective tritium loss fraction (0..0.2) (optional)", float('nan'), 0.01, min_value=0.0, max_value=0.2,
                        help="If set, effective TBR is reduced: TBR_eff = TBR*(1-loss).")), include_fuelcycle),
                    "TBR_self_sufficiency_margin": _maybe(float(_num("Self-sufficiency margin on TBR_eff (optional)", float('nan'), 0.01, min_value=0.0, max_value=0.5,
                        help="If set, requires TBR_eff ≥ 1 + margin (after declared losses).")), include_fuelcycle),

                    # Economics overlay — optional component CAPEX proxy cap (diagnostic)
                    "cost_k_heating_cd": _maybe(float(_num(
                        "Heating/CD CAPEX factor (MUSD per MW launched)",
                        25.0,
                        1.0,
                        min_value=0.0,
                        help="Used only for the component CAPEX proxy: capex_heating_cd = k * P_CD_launch_MW (fallback Paux).",
                    )), include_economics),
                    "cost_k_tritium_plant": _maybe(float(_num(
                        "Tritium plant CAPEX factor (MUSD per kg/day burn)",
                        40.0,
                        1.0,
                        min_value=0.0,
                        help="Used only for the component CAPEX proxy: capex_tritium_plant = k * T_burn_kg_per_day.",
                    )), include_economics),
                    "CAPEX_max_proxy_MUSD": _maybe(float(_num(
                        "Max component CAPEX proxy (MUSD) (optional)",
                        float('nan'),
                        50.0,
                        min_value=0.0,
                        help="Optional hard feasibility cap on CAPEX_component_proxy_MUSD. Leave NaN to disable.",
                    )), include_economics),

                    # Current drive + NI closure + channel caps
                    "include_current_drive": bool(st.checkbox(
                        "Current drive & NI closure (compute P_cd)",
                        value=False,
                        help="Enables deterministic non-inductive closure: choose actuator, CD efficiency model, and target f_NI; SHAMS computes required launched P_cd (capped by Pcd_max_MW).",
                    )),
                    "include_cd_library_v357": bool(st.checkbox(
                        "CD channel library caps",
                        value=False,
                        disabled=False,
                        help="Adds explicit channel feasibility diagnostics and optional hard caps for LH accessibility, ECCD launcher power density, and NBI shine-through.",
                    )),
                    "include_cd_library_v395": bool(st.checkbox(
                        "CD multi-channel actuator mix — ECCD/LHCD/NBI/ICRF mix",
                        value=False,
                        disabled=False,
                        help="Enables the multi-channel CD library (power split across actuators) when cd_model=channel_library_v395 and cd_mix_enable=True. Purely algebraic; no solvers.",
                    )),

                    "f_noninductive_target": float(_num(
                        "Target non-inductive fraction f_NI,target (–)",
                        1.0,
                        0.02,
                        min_value=0.0,
                        max_value=1.2,
                        help="Target f_NI = f_bs + I_cd/Ip. SHAMS computes I_cd and launched P_cd to reach this target (capped).",
                    )),
                    "Pcd_max_MW": float(_num(
                        "Max launched CD power P_cd,max (MW)",
                        200.0,
                        10.0,
                        min_value=0.0,
                        help="Hard cap on launched current-drive power used in the NI closure.",
                    )),
                    "eta_cd_wallplug": float(_num(
                        "CD wall-plug efficiency η_cd,wall (0..1)",
                        0.35,
                        0.02,
                        min_value=0.05,
                        max_value=0.9,
                        help="Wall-plug efficiency used in plant electric ledger.",
                    )),
                    "gamma_cd_A_per_W": float(_num(
                        "CD efficiency γ_cd (A/W) (legacy fixed model)",
                        0.05,
                        0.005,
                        min_value=1e-4,
                        max_value=0.2,
                        help="Used only when cd_model=fixed_gamma.",
                    )),
                    "cd_actuator": str(st.selectbox(
                        "CD actuator channel",
                        options=["ECCD", "LHCD", "NBI", "ICRF"],
                        index=0,
                        help="Actuator used for CD efficiency trends and channel diagnostics.",
                    )),
                    "cd_model": str(st.selectbox(
                        "CD efficiency model",
                        options=["fixed_gamma", "actuator_scaling", "channel_library_v357", "channel_library_v395"],
                        index=2,
                        help="Deterministic CD efficiency proxy model.",
                    )),

                    # multi-channel mix knobs (used only when cd_model=channel_library_v395)
                    "cd_mix_enable": bool(st.checkbox(
                        "Enable CD actuator mix",
                        value=False,
                        help="If enabled and cd_model=channel_library_v395, SHAMS splits launched P_cd across ECCD/LHCD/NBI/ICRF using the fractions below and computes a power-weighted effective γ_cd.",
                    )),
                    "cd_mix_frac_eccd": float(_num("Mix fraction: ECCD", 1.0, 0.05, min_value=0.0, max_value=1.0,
                        help="Fraction of launched P_cd assigned to ECCD (will be normalized with other fractions if their sum>0).")),
                    "cd_mix_frac_lhcd": float(_num("Mix fraction: LHCD", 0.0, 0.05, min_value=0.0, max_value=1.0,
                        help="Fraction of launched P_cd assigned to LHCD.")),
                    "cd_mix_frac_nbi": float(_num("Mix fraction: NBI", 0.0, 0.05, min_value=0.0, max_value=1.0,
                        help="Fraction of launched P_cd assigned to NBI.")),
                    "cd_mix_frac_icrf": float(_num("Mix fraction: ICRF", 0.0, 0.05, min_value=0.0, max_value=1.0,
                        help="Fraction of launched P_cd assigned to ICRF/FWCD.")),

                    "eta_cd_wallplug_eccd": float(_num("Wall-plug η: ECCD (optional)", float('nan'), 0.02, min_value=0.0, max_value=1.0,
                        help="Optional per-channel wall-plug efficiency. Leave NaN to use global η_cd,wall.")),
                    "eta_cd_wallplug_lhcd": float(_num("Wall-plug η: LHCD (optional)", float('nan'), 0.02, min_value=0.0, max_value=1.0,
                        help="Optional per-channel wall-plug efficiency. Leave NaN to use global η_cd,wall.")),
                    "eta_cd_wallplug_nbi": float(_num("Wall-plug η: NBI (optional)", float('nan'), 0.02, min_value=0.0, max_value=1.0,
                        help="Optional per-channel wall-plug efficiency. Leave NaN to use global η_cd,wall.")),
                    "eta_cd_wallplug_icrf": float(_num("Wall-plug η: ICRF (optional)", float('nan'), 0.02, min_value=0.0, max_value=1.0,
                        help="Optional per-channel wall-plug efficiency. Leave NaN to use global η_cd,wall.")),

                    # LHCD knobs + optional bounds (caps are disabled by default via NaN)
                    "lhcd_n_parallel": float(_num(
                        "LHCD n∥ (–)",
                        1.8,
                        0.05,
                        min_value=1.0,
                        max_value=4.0,
                        help="Used only when cd_actuator=LHCD and cd_model=channel_library_v357.",
                    )),
                    "lhcd_n_parallel_min": float(_num(
                        "LHCD n∥ min (optional)",
                        float('nan'),
                        0.05,
                        min_value=0.5,
                        help="Optional hard constraint lower bound on n∥. Leave NaN to disable.",
                    )),
                    "lhcd_n_parallel_max": float(_num(
                        "LHCD n∥ max (optional)",
                        float('nan'),
                        0.05,
                        min_value=0.5,
                        help="Optional hard constraint upper bound on n∥. Leave NaN to disable.",
                    )),

                    # ECCD knobs + optional launcher power-density cap
                    "eccd_launcher_area_m2": float(_num(
                        "ECCD launcher area A (m²)",
                        2.0,
                        0.1,
                        min_value=0.1,
                        help="Used to compute launcher power density P_cd/A for channel cap checks.",
                    )),
                    "eccd_launch_factor": float(_num(
                        "ECCD launch factor (–)",
                        1.0,
                        0.05,
                        min_value=0.2,
                        max_value=2.0,
                        help="Captures qualitative steering/optics effects as a declared multiplier on γ_cd for the channel library model.",
                    )),
                    "eccd_launcher_power_density_max_MW_m2": float(_num(
                        "ECCD launcher power density max (MW/m²) (optional)",
                        float('nan'),
                        1.0,
                        min_value=0.0,
                        help="Optional hard constraint. Leave NaN to disable.",
                    )),

                    # NBI knobs + optional shine-through cap
                    "nbi_beam_energy_keV": float(_num(
                        "NBI beam energy (keV)",
                        500.0,
                        25.0,
                        min_value=50.0,
                        max_value=5000.0,
                        help="Used only when cd_actuator=NBI in the channel library model (trend scaling + shine-through proxy).",
                    )),
                    "nbi_shinethrough_frac_max": float(_num(
                        "NBI shine-through max (fraction) (optional)",
                        float('nan'),
                        0.01,
                        min_value=0.0,
                        max_value=0.5,
                        help="Optional hard constraint on shine-through fraction proxy. Leave NaN to disable.",
                    )),

                    # Net power / electrical balance
                    "P_net_min_MW": _maybe(float(_num("Minimum net electric power (MW)", preset["P_net_min_MW"], 10.0, min_value=-1e6)), include_net_power),

                    # ---------------------------------------------------------
                    # Plant power ledger caps (v361.0 actuator authority hook)
                    # ---------------------------------------------------------
                    "f_recirc_max": float(_num(
                        "Max recirculating fraction f_recirc (optional)",
                        float('nan'),
                        0.02,
                        min_value=0.0,
                        max_value=1.0,
                        help="Optional cap on recirculating fraction Precirc/Pe_gross. Leave NaN to disable.",
                    )),
                    "P_pf_avg_max_MW": float(_num(
                        "Max average PF electric draw (MW) (optional)",
                        float('nan'),
                        10.0,
                        min_value=0.0,
                        help="Optional cap on average PF electric draw proxy (pf_E_pulse_MJ/(t_burn+t_dwell)). Leave NaN to disable.",
                    )),
                    "P_aux_max_MW": float(_num(
                        "Max aux+CD wallplug electric draw (MW) (optional)",
                        float('nan'),
                        10.0,
                        min_value=0.0,
                        help="Optional cap on auxiliary+CD wallplug electric draw proxy. Leave NaN to disable.",
                    )),
                    "P_supply_peak_max_MW": float(_num(
                        "Max peak power-supply draw (MW) (optional)",
                        float('nan'),
                        10.0,
                        min_value=0.0,
                        help="Optional cap on P_supply_peak_MW = max(PF_peak, Aux/CD_wallplug, VS_control, RWM_control). Leave NaN to disable.",
                    )),
                    "P_cryo_max_MW": float(_num(
                        "Max cryo wallplug electric draw (MW) (optional)",
                        float('nan'),
                        5.0,
                        min_value=0.0,
                        help="Optional cap on cryoplant wallplug electric draw proxy. Leave NaN to disable.",
                    )),

                    # ---------------------------------------------------------
                    # Control & stability authority — optional caps
                    # ---------------------------------------------------------
                    "include_control_contracts": bool(st.checkbox(
                        "Enable control contracts (deterministic envelopes)",
                        value=False,
                        help="When enabled, SHAMS computes VS/PF/RWM control requirements and checks optional caps (no physics mutation).",
                    )),

                    # ---------------------------------------------------------
                    # Control & Stability Ledger Authority (optional)
                    # ---------------------------------------------------------
                    "include_control_stability_authority_v398": bool(st.checkbox(
                        "Enable control ledger (VS budget + headroom + RWM proximity overlay)",
                        value=False,
                        help="Governance-only overlay that consolidates CS flux budget and VS/RWM headroom into explicit margins/tiers (no physics mutation).",
                    )),
                    "vs_budget_margin_min_v398": float(_num(
                        "Min VS budget margin (optional)",
                        float("nan"),
                        0.0,
                        help="Optional feasibility bound on VS/CS flux margin: (psi_av-psi_req)/psi_req >= min. Leave NaN to disable.",
                    )),
                    "vde_headroom_min_v398": float(_num(
                        "Min vertical control headroom (optional)",
                        float("nan"),
                        0.0,
                        help="Optional feasibility bound on min(VS power headroom, VS bandwidth headroom). Leave NaN to disable.",
                    )),
                    "rwm_proximity_index_max_v398": float(_num(
                        "Max RWM proximity index (optional)",
                        float("nan"),
                        0.66,
                        min_value=0.0,
                        max_value=1.0,
                        help="Optional feasibility cap on RWM proximity index (0 benign → 1 critical). Leave NaN to disable.",
                    )),

                    "cs_V_loop_max_V": float(_num(
                        "Max CS loop voltage during ramp V_loop,max (V) (optional)",
                        float("nan"),
                        50.0,
                        min_value=0.0,
                        help="Optional cap on CS loop voltage proxy during ramp. Leave NaN to disable.",
                    )),
                    "vs_bandwidth_max_Hz": float(_num(
                        "Max VS control bandwidth (Hz) (optional)",
                        float("nan"),
                        1.0,
                        min_value=0.0,
                        help="Optional cap on VS bandwidth requirement. Leave NaN to disable.",
                    )),
                    "vs_control_power_max_MW": float(_num(
                        "Max VS control power (MW) (optional)",
                        float("nan"),
                        1.0,
                        min_value=0.0,
                        help="Optional cap on VS control power requirement. Leave NaN to disable.",
                    )),
                    "pf_I_peak_max_MA": float(_num(
                        "Max PF peak current (MA) (optional)",
                        float("nan"),
                        0.5,
                        min_value=0.0,
                        help="Optional cap on PF peak current requirement from envelope contract. Leave NaN to disable.",
                    )),
                    "pf_dIdt_max_MA_s": float(_num(
                        "Max PF dI/dt (MA/s) (optional)",
                        float("nan"),
                        0.5,
                        min_value=0.0,
                        help="Optional cap on PF ramp-rate requirement. Leave NaN to disable.",
                    )),
                    "pf_V_peak_max_V": float(_num(
                        "Max PF peak voltage (V) (optional)",
                        float("nan"),
                        100.0,
                        min_value=0.0,
                        help="Optional cap on PF peak voltage requirement. Leave NaN to disable.",
                    )),
                    "pf_P_peak_max_MW": float(_num(
                        "Max PF peak power (MW) (optional)",
                        float("nan"),
                        5.0,
                        min_value=0.0,
                        help="Optional cap on PF peak electrical power requirement. Leave NaN to disable.",
                    )),
                    "pf_E_pulse_max_MJ": float(_num(
                        "Max PF pulse energy (MJ) (optional)",
                        float("nan"),
                        10.0,
                        min_value=0.0,
                        help="Optional cap on PF pulse energy proxy from envelope contract. Leave NaN to disable.",
                    )),
                    "include_rwm_screening": bool(st.checkbox(
                        "Enable RWM screening (optional)",
                        value=False,
                        help="If enabled, evaluates an RWM screening proxy and checks bandwidth/power against caps.",
                    )),
                    "rwm_bandwidth_max_Hz": float(_num(
                        "Max RWM bandwidth (Hz) (optional)",
                        float("nan"),
                        1.0,
                        min_value=0.0,
                        help="Optional cap on RWM required bandwidth; defaults to VS cap if NaN in the evaluator. Leave NaN to disable.",
                    )),
                    "rwm_control_power_max_MW": float(_num(
                        "Max RWM control power (MW) (optional)",
                        float("nan"),
                        1.0,
                        min_value=0.0,
                        help="Optional cap on RWM required control power; defaults to VS cap if NaN in the evaluator. Leave NaN to disable.",
                    )),

                    # propagate UI choices to output for check logic
                    "_warn_frac_max": float(warn_fracs["max"]),
                    "_warn_frac_min": float(warn_fracs["min"]),
                    "_subsystem_enabled": {
                        "build": bool(include_build),
                        "magnets": bool(include_magnets),
                        "divertor": bool(include_divertor),
                        "neutronics": bool(include_neutronics),
                        "net_power": bool(include_net_power),
                    },
                }

                # (Button moved outside this expander.)

            
        # Evaluate button is intentionally *outside* the optional engineering section so
        # users don't have to expand engineering knobs just to run Point Designer.
        run_btn = st.button("Evaluate Point", type="primary", use_container_width=True)
        # Quick bridge: trigger Systems Mode precheck using the current Point inputs.
        if st.button("Run Systems Precheck (in Systems Mode)", use_container_width=True, key="pd_to_systems_precheck"):
            # Schedule the action for Systems Mode and suggest the user switch tabs.
            st.session_state["_sys_action"] = "precheck"
            st.session_state["_pending_workflow_step"] = "Diagnose"
            st.success("Scheduled Systems Precheck. Switch to the **Systems Mode** tab to view the report.")
        
        
        # --- Execute: Point Designer evaluation (frozen truth) ---
        if run_btn:
            import time as _time
            # Acquire global run lock (UX/gov only; does not affect truth).
            _owner_tok = str(st.session_state.get("_shams_owner_token") or "PointDesigner")
            _task_label = "Point Designer: Evaluate Point"
            _ok_lock = bool(_shams_runlock.acquire(_task_label, _owner_tok, app_start_ts=st.session_state.get("_shams_app_start_ts")))
            if not _ok_lock:
                _locked, _task, _started, _is_owner = _shams_runlock.status(_owner_tok, app_start_ts=st.session_state.get("_shams_app_start_ts"))
                if _locked:
                    st.warning(f"Run lock busy: {_task or 'unknown task'} (another run is in progress).")
                else:
                    st.warning("Run lock busy (another run is in progress).")
            else:
                try:
                    with st.spinner("Evaluating frozen 0-D point…"):
                        # Defensive de-dup of fields that are passed explicitly below.
                        _ck = strip_point_input_knob_dupes(
                            clean_knobs,
                            "Tcoil_K", "magnet_technology", "Bt_T", "R0_m", "a_m", "kappa", "delta",
                            "Ip_MA", "fG", "Paux_MW", "Ti_keV",
                        )
        
                        base = make_point_inputs_from(
                            _ck,
                            R0_m=float(R0), a_m=float(a), kappa=float(kappa), delta=float(delta), Bt_T=float(B0),
                            magnet_technology=str(tech),
                            Tcoil_K=float(Tcoil),
                            Ip_MA=float(0.5*(Ip_min+Ip_max)),
                            Ti_keV=float(Ti),
                            fG=float(0.5*(fG_min+fG_max)),
                            t_shield_m=float(tshield),
                            Paux_MW=float(Paux),
                            Ti_over_Te=float(Ti_over_Te),
                            q95_enforcement=str(st.session_state.get("q95_enforcement","hard")),
                            greenwald_enforcement=str(st.session_state.get("greenwald_enforcement","hard")),
                            tech_tier=str(st.session_state.get("tech_tier","TRL7")),
                            confinement_scaling=confinement_scaling,
                            zeff=float(Zeff),
                            dilution_fuel=float(dilution_fuel),
                            f_rad_core=float(f_rad_core),
                            include_radiation=bool(include_radiation),
                            radiation_model=radiation_model,
                            radiation_db=radiation_db,
                            impurity_species=impurity_species,
                            impurity_frac=float(impurity_frac),
                            include_synchrotron=bool(include_synchrotron),
                            impurity_contract_species=impurity_contract_species,
                            impurity_contract_f_z=float(impurity_contract_f_z),
                            impurity_partition_core=float(impurity_partition_core),
                            impurity_partition_edge=float(impurity_partition_edge),
                            impurity_partition_sol=float(impurity_partition_sol),
                            impurity_partition_div=float(impurity_partition_div),
                            include_sol_radiation_control=bool(include_sol_radiation_control),
                            q_div_target_MW_m2=float(q_div_target_MW_m2),
                            T_sol_keV=float(T_sol_keV),
                            f_V_sol_div=float(f_V_sol_div),
                            detachment_fz_max=float(detachment_fz_max),
                            include_impurity_v399=bool(include_impurity_v399),
                            impurity_mix_json_v399=str(impurity_mix_json_v399),
                            zeff_max_v399=float(zeff_max_v399),
                            prad_core_frac_max_v399=float(prad_core_frac_max_v399),
                            prad_total_frac_max_v399=float(prad_total_frac_max_v399),
                            detachment_margin_min_v399=float(detachment_margin_min_v399),
                            include_edge_core_coupled_exhaust=bool(include_edge_core_coupled_exhaust and include_sol_radiation_control),
                            edge_core_coupling_chi_core=float(edge_core_coupling_chi_core),
                            f_rad_core_edge_core_max=float(f_rad_core_edge_core_max),
                            confinement_model=str(confinement_scaling).lower(),  # back-compat
                            include_transport_contracts_v371=bool(include_transport_contracts_v371),
                            H_required_max_optimistic=float(H_required_max_optimistic) if bool(include_transport_contracts_v371) else float("nan"),
                            H_required_max_robust=float(H_required_max_robust) if bool(include_transport_contracts_v371) else float("nan"),
                            include_transport_envelope_v396=bool(include_transport_envelope_v396),
                            transport_spread_max_v396=float(transport_spread_max_v396) if bool(include_transport_envelope_v396) else float("nan"),
                            include_tauE_user_scaling_v396=bool(include_tauE_user_scaling_v396) if bool(include_transport_envelope_v396) else False,
                            tauE_user_C_v396=float(tauE_user_C_v396),
                            tauE_user_exp_Ip_v396=float(tauE_user_exp_Ip_v396),
                            tauE_user_exp_Bt_v396=float(tauE_user_exp_Bt_v396),
                            tauE_user_exp_ne_v396=float(tauE_user_exp_ne_v396),
                            tauE_user_exp_Ploss_v396=float(tauE_user_exp_Ploss_v396),
                            tauE_user_exp_R_v396=float(tauE_user_exp_R_v396),
                            tauE_user_exp_eps_v396=float(tauE_user_exp_eps_v396),
                            tauE_user_exp_kappa_v396=float(tauE_user_exp_kappa_v396),
                            tauE_user_exp_M_v396=float(tauE_user_exp_M_v396),
                            include_profile_proxy_v397=bool(include_profile_proxy_v397),
                            profile_alpha_T_v397=float(profile_alpha_T_v397),
                            profile_beta_T_v397=float(profile_beta_T_v397),
                            profile_alpha_n_v397=float(profile_alpha_n_v397),
                            profile_beta_n_v397=float(profile_beta_n_v397),
                            profile_alpha_j_v397=float(profile_alpha_j_v397),
                            profile_beta_j_v397=float(profile_beta_j_v397),
                            profile_shear_shape_v397=float(profile_shear_shape_v397),
                            profile_peaking_p_max_v397=float(profile_peaking_p_max_v397) if bool(include_profile_proxy_v397) else float("nan"),
                            q95_proxy_min_v397=float(q95_proxy_min_v397) if bool(include_profile_proxy_v397) else float("nan"),
                            q0_proxy_min_v397=float(q0_proxy_min_v397) if bool(include_profile_proxy_v397) else float("nan"),
                            bootstrap_localization_max_v397=float(bootstrap_localization_max_v397) if bool(include_profile_proxy_v397) else float("nan"),
                            include_neutronics_materials_coupling_v372=bool(include_neutronics_materials_coupling_v372),
                            nm_material_class_v372=str(nm_material_class_v372) if bool(include_neutronics_materials_coupling_v372) else str(getattr(_base_pd, "nm_material_class_v372", "RAFM")),
                            nm_spectrum_class_v372=str(nm_spectrum_class_v372) if bool(include_neutronics_materials_coupling_v372) else str(getattr(_base_pd, "nm_spectrum_class_v372", "nominal")),
                            nm_T_oper_C_v372=float(nm_T_oper_C_v372) if bool(include_neutronics_materials_coupling_v372) else float("nan"),
                            dpa_rate_eff_max_v372=float(dpa_rate_eff_max_v372) if bool(include_neutronics_materials_coupling_v372) else float("nan"),
                            damage_margin_min_v372=float(damage_margin_min_v372) if bool(include_neutronics_materials_coupling_v372) else float("nan"),
                            profile_model=profile_model,
                            profile_peaking_ne=float(profile_peaking_ne),
                            profile_peaking_T=float(profile_peaking_T),
                            profile_mode=bool(profile_mode),
                            profile_alpha_T=float(profile_alpha_T),
                            profile_alpha_n=float(profile_alpha_n),
                            profile_shear_shape=float(profile_shear_shape),
                            pedestal_enabled=bool(pedestal_enabled),
                            pedestal_width_a=float(pedestal_width_a),
                            bootstrap_model=bootstrap_model,
                            include_bootstrap_pressure_selfconsistency=bool(include_bootstrap_pressure_selfconsistency),
                            f_bootstrap_consistency_abs_max=float(f_bootstrap_consistency_abs_max),
                            fuel_mode=fuel_mode,
                            include_secondary_DT=bool(include_secondary_DT),
                            tritium_retention=tritium_retention,
                            tau_T_loss_s=float(tau_T_loss_s),
                            alpha_loss_frac=float(alpha_loss_frac),
                            alpha_loss_model=alpha_loss_model,
                            alpha_prompt_loss_k=float(alpha_prompt_loss_k),
                            alpha_partition_model=alpha_partition_model,
                            alpha_partition_k=float(alpha_partition_k),
                            ash_dilution_mode=ash_dilution_mode,
                            f_He_ash=float(f_He_ash),
                            include_alpha_loss=bool(include_alpha_loss),
                            include_hmode_physics=bool(include_hmode_physics),
                            require_Hmode=bool(require_Hmode),
                            PLH_margin=float(PLH_margin),
                            use_lambda_q=bool(use_lambda_q),
                            cd_enable=bool(cd_enable),
                            cd_method=str(cd_method),
                            cd_fraction_of_Paux=float(cd_fraction_of_Paux),
                            f_NI_min=float(f_NI_min),
                            disruption_risk_max=float(disruption_risk_max),
                            include_availability_replacement_v359=bool(locals().get("include_availability_replacement_v359", False)),
                            planned_outage_base=float(locals().get("planned_outage_base", 0.05)),
                            unplanned_outage_base=float(locals().get("unplanned_outage_base", 0.05)),
                            replacement_rate_per_year=float(locals().get("replacement_rate_per_year", 0.0)),
                            include_maintenance_scheduling_v368=bool(locals().get("include_maintenance_scheduling_v368", False)),
                            maint_capacity_factor=float(locals().get("maint_capacity_factor", 1.0)),
                            include_availability_reliability_v391=bool(locals().get("include_availability_reliability_v391", False)),
                            planned_outage_days_per_y_v391=float(locals().get("planned_outage_days_per_y_v391", 30.0)),
                            mtbf_tf_h_v391=float(locals().get("mtbf_tf_h_v391", 80000.0)),
                            mttr_tf_h_v391=float(locals().get("mttr_tf_h_v391", 240.0)),
                            mtbf_pfcs_h_v391=float(locals().get("mtbf_pfcs_h_v391", 60000.0)),
                            mttr_pfcs_h_v391=float(locals().get("mttr_pfcs_h_v391", 168.0)),
                            mtbf_divertor_h_v391=float(locals().get("mtbf_divertor_h_v391", 20000.0)),
                            mttr_divertor_h_v391=float(locals().get("mttr_divertor_h_v391", 336.0)),
                            mtbf_blanket_h_v391=float(locals().get("mtbf_blanket_h_v391", 25000.0)),
                            mttr_blanket_h_v391=float(locals().get("mttr_blanket_h_v391", 504.0)),
                            mtbf_cryo_h_v391=float(locals().get("mtbf_cryo_h_v391", 40000.0)),
                            mttr_cryo_h_v391=float(locals().get("mttr_cryo_h_v391", 120.0)),
                            mtbf_hcd_h_v391=float(locals().get("mtbf_hcd_h_v391", 30000.0)),
                            mttr_hcd_h_v391=float(locals().get("mttr_hcd_h_v391", 168.0)),
                            mtbf_bop_h_v391=float(locals().get("mtbf_bop_h_v391", 50000.0)),
                            mttr_bop_h_v391=float(locals().get("mttr_bop_h_v391", 72.0)),
                            availability_min_v391=float(locals().get("availability_min_v391", float('nan'))),

                            include_control_stability_authority_v398=bool(locals().get("include_control_stability_authority_v398", False)),
                            vs_budget_margin_min_v398=float(locals().get("vs_budget_margin_min_v398", float('nan'))),
                            vde_headroom_min_v398=float(locals().get("vde_headroom_min_v398", float('nan'))),
                            rwm_proximity_index_max_v398=float(locals().get("rwm_proximity_index_max_v398", float('nan'))),
                            include_magnet_technology_authority_v400=bool(locals().get("include_magnet_technology_authority_v400", True)),
                            magnet_margin_min_v400=float(locals().get("magnet_margin_min_v400", float('nan'))),
                            b_margin_min_v400=float(locals().get("b_margin_min_v400", float('nan'))),
                            j_margin_min_v400=float(locals().get("j_margin_min_v400", float('nan'))),
                            stress_margin_min_v400=float(locals().get("stress_margin_min_v400", float('nan'))),
                            sc_margin_min_v400=float(locals().get("sc_margin_min_v400", float('nan'))),
                            t_margin_min_v400=float(locals().get("t_margin_min_v400", float('nan'))),
                            p_tf_ohmic_margin_min_v400=float(locals().get("p_tf_ohmic_margin_min_v400", float('nan'))),
                            planned_outage_max_frac_v391=float(locals().get("planned_outage_max_frac_v391", float('nan'))),
                            unplanned_downtime_max_frac_v391=float(locals().get("unplanned_downtime_max_frac_v391", float('nan'))),
                            maint_downtime_max_frac_v391=float(locals().get("maint_downtime_max_frac_v391", float('nan'))),
                            include_plant_economics_v360=bool(locals().get("include_plant_economics_v360", False)),
                            discount_rate=float(locals().get("discount_rate", 0.07)),
                            wallplug_eff=float(locals().get("wallplug_eff", 0.3)),
                        )

                        base = merge_overlay_session_into_inputs(base, st.session_state)
                        _warn_unrealistic_point_inputs(base, context="Point Designer")

                        _ev = _dsg_evaluator(origin="Point Designer", cache_enabled=True, cache_max=4096)
                        _res = _ev.evaluate(base, Paux_for_Q_MW=float(Paux_for_Q))
                        out = _res.out if (_res is not None and getattr(_res, "ok", True) and isinstance(getattr(_res, "out", None), dict)) else {}
        
                        # Cache under canonical keys (Telemetry/Constraints are read-only views).
                        st.session_state["pd_last_outputs"] = dict(out)
                        st.session_state["last_point_out"] = dict(out)
                        st.session_state["last_point_inp"] = base.to_dict() if hasattr(base, "to_dict") else {}
                        st.session_state["pd_last_run_ts"] = float(_time.time())
                        st.session_state["pd_last_inputs_hash"] = st.session_state.get("pd_current_inputs_hash")
                        st.session_state["pd_last_artifact"] = {"inputs": st.session_state["last_point_inp"], "outputs": dict(out), "constraints": []}
                        st.session_state["last_point_artifact"] = st.session_state["pd_last_artifact"]
        
                        st.success("Point evaluation complete. Open ** Telemetry** for results and ledgers.")
                except Exception as e:
                    st.error(f"Point evaluation failed: {e}")
                finally:
                    _shams_runlock.release(_owner_tok)
        
        # Point Designer usability: show cache status + last-eval timestamp + stale-input warning.
        try:
            import hashlib, json as _json
            from datetime import datetime
            import time as _time
        
            _pd_inputs_fingerprint = {
                "R0_m": float(R0), "a_m": float(a), "kappa": float(kappa), "delta": float(delta), "Bt_T": float(B0),
                "Paux_MW": float(Paux), "Ti_keV": float(Ti), "Ti_over_Te": float(Ti_over_Te),
                "fuel_mode": str(fuel_mode), "Q_target": float(Q_target), "H98_target": float(H98_target),
                "Ip_min": float(Ip_min), "Ip_max": float(Ip_max), "fG_min": float(fG_min), "fG_max": float(fG_max),
                "tshield": float(tshield),
                "magnet_technology": str(tech),
                "Tcoil_K": float(Tcoil),
                "confidence": str(confidence),
                "subsystem_enabled": dict(clean_knobs.get("_subsystem_enabled", {})),
            }
            _pd_inputs_hash = hashlib.sha1(_json.dumps(_pd_inputs_fingerprint, sort_keys=True).encode("utf-8")).hexdigest()
            _last_hash = st.session_state.get("pd_last_inputs_hash")
            _last_ts = st.session_state.get("pd_last_run_ts")
        
            if _last_ts:
                st.caption(f"Last evaluation: {datetime.fromtimestamp(float(_last_ts)).strftime('%Y-%m-%d %H:%M:%S')}")
            if (not run_btn) and ("pd_last_outputs"in st.session_state) and (_last_hash is not None) and (_pd_inputs_hash != _last_hash):
                st.warning("Inputs changed since last evaluation. Click **Evaluate Point** to refresh results.")
            # Keep current hash available to the run path below.
            st.session_state["pd_current_inputs_hash"] = _pd_inputs_hash
        except Exception:
            pass
        

        with tab_tel:
            st.subheader("Telemetry")
            # Telemetry is read-only: if no cached Point Designer results exist, guide the user.
            if "pd_last_outputs"not in st.session_state:
                st.info("No Point Designer results yet. Open ** Configure** and click **Evaluate Point**, then return here.")
                st.caption("Telemetry is read-only; nothing will execute here until a cached Point evaluation exists.")
            else:
                try:
                    render_point_designer_trace(st.session_state)
                    render_point_designer_export(st.session_state)
                except Exception:
                    pass
                # Verdict-first executive header (PASS/FAIL) before any tables.
                # IMPORTANT: derive from the cached *outputs* (pd_last_outputs) so that
                # Mission Snapshot / Plot Deck / Ledgers cannot disagree.
                _pd_art = st.session_state.get("pd_last_artifact") or {}
                _pd_out0 = st.session_state.get("pd_last_outputs") if isinstance(st.session_state.get("pd_last_outputs"), dict) else None
                _rs = {}
                try:
                    if _pd_out0 is not None:
                        _rs = _compute_run_summary_from_out(_pd_out0)
                        # Keep artifact in sync for exports and downstream panels.
                        if isinstance(_pd_art, dict):
                            _pd_art["run_summary"] = _rs
                            st.session_state["pd_last_artifact"] = _pd_art
                    else:
                        _rs = (_pd_art.get("run_summary") or {}) if isinstance(_pd_art, dict) else {}
                except Exception:
                    _rs = (_pd_art.get("run_summary") or {}) if isinstance(_pd_art, dict) else {}



                _tight = _rs.get("tightest_hard_constraints", []) if isinstance(_rs, dict) else []
                _tight = _tight or []

                # Policy-aware verdict: FAIL only if *blocking* constraints fail.
                _fb = []
                _fd = []
                # Detect whether we have a real evaluation payload (avoid PASS+NaN from empty dict).
                _outputs_present = bool(isinstance(_pd_out0, dict) and _pd_out0 and any(k in _pd_out0 for k in ("Pin_MW","P_fus_MW","P_net_e_MW","Ploss_MW")))
                try:
                    if isinstance(_pd_out0, dict):
                        _fb = list(_pd_out0.get("failed_blocking") or [])
                        _fd = list(_pd_out0.get("failed_diagnostic") or [])
                except Exception:
                    _fb, _fd = [], []

                def _find_entry(name: str):
                    for t in _tight:
                        if isinstance(t, dict) and str(t.get("name", "")) == str(name):
                            return t
                    return None

                if _fb:
                    _verdict = "FAIL"
                    _dom = str(_fb[0])
                    _ent = _find_entry(_dom) or {}
                    _b0 = f"Dominant constraint: {_dom}"
                    try:
                        _b1 = f"Tightest margin: {float(_ent.get('margin_frac', float('nan'))):.3g}"
                    except Exception:
                        _b1 = f"Tightest margin: {_ent.get('margin_frac','?')}"
                    _b2 = f"Power closure (MW): {_rs.get('power_closure_MW', 'n/a')}"
                elif _fd:
                    _verdict = "PASS (diagnostics)"
                    _dom = str(_fd[0])
                    _ent = _find_entry(_dom) or {}
                    _b0 = f"Diagnostic exceedance: {_dom}"
                    try:
                        _b1 = f"Margin (diagnostic): {float(_ent.get('margin_frac', float('nan'))):.3g}"
                    except Exception:
                        _b1 = f"Margin (diagnostic): {_ent.get('margin_frac','?')}"
                    _b2 = f"Power closure (MW): {_rs.get('power_closure_MW', 'n/a')}"
                else:
                    if not _outputs_present:
                        _verdict = "PASS + DIAG"
                        _b0 = "No evaluation outputs loaded"
                        _b1 = "Click Evaluate Point after changing intent/machine type/policy"
                        _b2 = "Net electric (MW): n/a"
                    else:
                        _verdict = "PASS"
                    if _tight and isinstance(_tight[0], dict):
                        _b0 = f"Tightest hard constraint: {_tight[0].get('name','(none)')}"
                        try:
                            _b1 = f"Margin (tightest): {float(_tight[0].get('margin_frac', float('nan'))):.3g}"
                        except Exception:
                            _b1 = f"Margin (tightest): {_tight[0].get('margin_frac','?')}"
                    else:
                        _b0, _b1 = "Tightest hard constraint: (none)", "Margin (tightest): n/a"
                    _headline = _rs.get("headline", {}) if isinstance(_rs, dict) else {}
                    _pnet = float(_headline.get("P_net_e_MW", float("nan"))) if isinstance(_headline, dict) else float("nan")
                    _b2 = f"Net electric (MW): {(_pnet if np.isfinite(_pnet) else 'n/a')}"

                _bullets = []



                for _x in (_b0, _b1, _b2):
                    if _x is None:
                        continue
                    _s = str(_x).strip()
                    if _s:
                        _bullets.append(html.escape(_s))
                _bullets_html = "\n".join([f"<li>{_s}</li>"for _s in _bullets]) or "<li>(no summary)</li>"

                st.markdown(
                    f"""<div style="padding:14px;border-radius:14px;border:1px solid #ddd;">
                    <div style="font-size:20px;font-weight:700;margin-bottom:6px;">{_verdict}</div>
                    <ul style="margin:0;padding-left:18px;line-height:1.6;">
                      {_bullets_html}
                    </ul>
                    </div>""",
                    unsafe_allow_html=True,
                )

                # v328.0: Magnet Technology Authority panel
                try:
                    _render_magnet_authority_panel(_pd_out0 or {})
                except Exception:
                    pass

                # Telemetry Deck navigation (reduces scrolling)
                _pd_tel_views = [
                    "Mission Snapshot",
                    "Plot Deck",
                    "Dominance & Closures",
                    "Control Contracts",
                    "Ledgers",
                    "Sensitivity Lab",
                    "Chronicle & Export",
                ]
                _pd_tel_view = st.radio(
                    "Telemetry deck",
                    _pd_tel_views,
                    horizontal=True,
                    label_visibility="collapsed",
                    key="pd_tel_view",
                )

                # Render live if button pressed, otherwise render cached results.
                if ("pd_last_outputs"in st.session_state):

                    # If we're just re-rendering after a Streamlit rerun (e.g., a download button),
                    # do NOT re-run the solver. Use cached outputs.
                    _use_cached = True  # Telemetry tab never re-runs the solver; always render cached outputs

                    # Activity log: user explicitly clicked Evaluate Point
                    if bool(run_btn) and (not _use_cached):
                        try:
                            _alog(
                                "Point Designer",
                                "EvaluatePoint",
                                {
                                    "inputs_hash": str(st.session_state.get("pd_current_inputs_hash", "")),
                                    "targets": {"H98": float(H98_target), "Q_DT_eqv": float(Q_target)},
                                    "bounds": {"Ip_MA": [float(Ip_min), float(Ip_max)], "fG": [float(fG_min), float(fG_max)]},
                                },
                            )
                        except Exception:
                            pass

                    if _use_cached:
                        # Cached render path (e.g., after download_button rerun)
                        try:
                            out = st.session_state.get("pd_last_outputs")
                        except Exception:
                            out = None
                        try:
                            artifact = st.session_state.get("pd_last_artifact")
                        except Exception:
                            artifact = None
                        try:
                            inputs_dict = (artifact or {}).get("inputs", {}) if isinstance(artifact, dict) else {}
                        except Exception:
                            inputs_dict = {}
                        try:
                            # mimic the original `base.__dict__` access pattern downstream
                            class _BaseObj: pass
                            base = _BaseObj()
                            for _k, _v in dict(inputs_dict).items():
                                setattr(base, _k, _v)
                        except Exception:
                            base = None
                        try:
                            log_lines = []
                        except Exception:
                            pass

                    # Solver log builder (used for both live runs and cached re-renders)
                    log_lines: List[str] = [] if not _use_cached else list(st.session_state.get("pd_last_log_lines", []) or [])

                    def _log(line: str) -> None:
                        """Append a single line to the expandable solver log."""
                        try:
                            log_lines.append(str(line))
                        except Exception:
                            pass

                    if _use_cached:
                        _log("Point Designer: cached render (solver not re-run)")
                    else:
                        _log("Point Designer solver log")

                    # NOTE: In Telemetry, the Configure tab may not have executed (Streamlit tabs are lazy).
                    # Only log what we can derive from cached artifacts.
                    try:
                        _R0 = float(getattr(base, 'R0_m')) if base is not None and hasattr(base,'R0_m') else float('nan')
                        _a  = float(getattr(base, 'a_m'))  if base is not None and hasattr(base,'a_m')  else float('nan')
                        _k  = float(getattr(base, 'kappa')) if base is not None and hasattr(base,'kappa') else float('nan')
                        _B  = float(getattr(base, 'Bt_T')) if base is not None and hasattr(base,'Bt_T') else float('nan')
                        _Ip = float(getattr(base, 'Ip_MA')) if base is not None and hasattr(base,'Ip_MA') else float('nan')
                        _Ti = float(getattr(base, 'Ti_keV')) if base is not None and hasattr(base,'Ti_keV') else float('nan')
                        _fG = float(getattr(base, 'fG')) if base is not None and hasattr(base,'fG') else float('nan')
                        _Paux = float(getattr(base, 'Paux_MW')) if base is not None and hasattr(base,'Paux_MW') else float('nan')
                        _log(f"Cached machine: R0={_R0:.6g} m, a={_a:.6g} m, kappa={_k:.6g}, Bt={_B:.6g} T; Ip={_Ip:.6g} MA; Ti={_Ti:.6g} keV; fG={_fG:.6g}; Paux={_Paux:.6g} MW")
                    except Exception:
                        pass

                    # Defensive de-dup: some UI knobs are passed explicitly below and may also live
                    # in clean_knobs depending on preset + sync pathways. Passing duplicates causes
                    # "got multiple values for keyword"errors.
                    if isinstance(clean_knobs, dict):
                        clean_knobs = strip_point_input_knob_dupes(
                            clean_knobs,
                            "Tcoil_K", "magnet_technology", "Bt_T", "R0_m", "a_m", "kappa", "delta",
                            "fixed_charge_rate", "capacity_factor", "capacity_factor_used",
                            "capex_structured_max_MUSD", "opex_structured_max_MUSD_per_y", "lcoe_lite_max_USD_per_MWh",
                            "fw_capex_fraction_of_blanket", "blanket_capex_fraction_of_blanket",
                            "divertor_capex_fraction_of_total", "base_capacity_factor", "capacity_factor_max",
                            "fw_downtime_days", "blanket_downtime_days", "divertor_downtime_days", "magnet_downtime_days",
                            "divertor_life_ref_yr", "divertor_q_ref_MW_m2", "divertor_q_exp",
                            "magnet_life_ref_yr", "magnet_margin_ref", "magnet_margin_exp",
                            "fw_lifetime_min_yr_v384", "blanket_lifetime_min_yr_v384", "divertor_lifetime_min_yr_v384",
                            "magnet_lifetime_min_yr_v384", "replacement_cost_max_MUSD_per_y_v384", "capacity_factor_min_v384",
                        )

                    base = make_point_inputs_from(
                        clean_knobs,
                        R0_m=R0, a_m=a, kappa=kappa, delta=delta, Bt_T=B0,
                        magnet_technology=str(tech),
                        Tcoil_K=float(Tcoil),
                        Ip_MA=0.5*(Ip_min+Ip_max),
                        Ti_keV=Ti, fG=0.8,
                        t_shield_m=tshield,
                        Paux_MW=Paux,
                        Ti_over_Te=Ti_over_Te,
                        q95_enforcement=str(st.session_state.get('q95_enforcement','hard')),
                        greenwald_enforcement=str(st.session_state.get('greenwald_enforcement','hard')),
                        tech_tier=str(st.session_state.get('tech_tier','TRL7')),
                        confinement_scaling=confinement_scaling,
                        zeff=Zeff,
                        dilution_fuel=dilution_fuel,
                        f_rad_core=f_rad_core,
                        include_radiation=include_radiation,
                        radiation_model=radiation_model,
                        radiation_db=radiation_db,
                        impurity_species=impurity_species,
                        impurity_frac=impurity_frac,
                        include_synchrotron=include_synchrotron,
                        impurity_contract_species=impurity_contract_species,
                        impurity_contract_f_z=float(impurity_contract_f_z),
                        impurity_partition_core=float(impurity_partition_core),
                        impurity_partition_edge=float(impurity_partition_edge),
                        impurity_partition_sol=float(impurity_partition_sol),
                        impurity_partition_div=float(impurity_partition_div),
                        include_sol_radiation_control=bool(include_sol_radiation_control),
                        q_div_target_MW_m2=float(q_div_target_MW_m2),
                        T_sol_keV=float(T_sol_keV),
                        f_V_sol_div=float(f_V_sol_div),
                        detachment_fz_max=float(detachment_fz_max),
                        include_edge_core_coupled_exhaust=bool(include_edge_core_coupled_exhaust and include_sol_radiation_control),
                        edge_core_coupling_chi_core=float(edge_core_coupling_chi_core),
                        f_rad_core_edge_core_max=float(f_rad_core_edge_core_max),
                        confinement_model=str(confinement_scaling).lower(),  # back-compat
                        include_transport_contracts_v371=bool(include_transport_contracts_v371),
                        H_required_max_optimistic=float(H_required_max_optimistic) if bool(include_transport_contracts_v371) else float('nan'),
                        H_required_max_robust=float(H_required_max_robust) if bool(include_transport_contracts_v371) else float('nan'),
                        include_neutronics_materials_coupling_v372=bool(include_neutronics_materials_coupling_v372),
                        nm_material_class_v372=str(nm_material_class_v372) if bool(include_neutronics_materials_coupling_v372) else str(getattr(_base_pd, 'nm_material_class_v372', 'RAFM')),
                        nm_spectrum_class_v372=str(nm_spectrum_class_v372) if bool(include_neutronics_materials_coupling_v372) else str(getattr(_base_pd, 'nm_spectrum_class_v372', 'nominal')),
                        nm_T_oper_C_v372=float(nm_T_oper_C_v372) if bool(include_neutronics_materials_coupling_v372) else float('nan'),
                        dpa_rate_eff_max_v372=float(dpa_rate_eff_max_v372) if bool(include_neutronics_materials_coupling_v372) else float('nan'),
                        damage_margin_min_v372=float(damage_margin_min_v372) if bool(include_neutronics_materials_coupling_v372) else float('nan'),
                        profile_model=profile_model,
                        profile_peaking_ne=profile_peaking_ne,
                        profile_peaking_T=profile_peaking_T,
                        profile_mode=bool(profile_mode),
                        profile_alpha_T=float(profile_alpha_T),
                        profile_alpha_n=float(profile_alpha_n),
                        profile_shear_shape=float(profile_shear_shape),
                        pedestal_enabled=bool(pedestal_enabled),
                        pedestal_width_a=float(pedestal_width_a),
                        bootstrap_model=bootstrap_model,
                        include_bootstrap_pressure_selfconsistency=bool(include_bootstrap_pressure_selfconsistency),
                        f_bootstrap_consistency_abs_max=float(f_bootstrap_consistency_abs_max),
                        fuel_mode=fuel_mode,
                        include_secondary_DT=include_secondary_DT,
                        tritium_retention=tritium_retention,
                        tau_T_loss_s=tau_T_loss_s,
                        alpha_loss_frac=alpha_loss_frac,
                        alpha_loss_model=alpha_loss_model,
                        alpha_prompt_loss_k=alpha_prompt_loss_k,
                        alpha_partition_model=alpha_partition_model,
                        alpha_partition_k=alpha_partition_k,
                        ash_dilution_mode=ash_dilution_mode,
                        f_He_ash=f_He_ash,
                        include_alpha_loss=include_alpha_loss,
                        include_hmode_physics=include_hmode_physics,
                        require_Hmode=require_Hmode,
                        PLH_margin=PLH_margin,
                        use_lambda_q=use_lambda_q,
                        cd_enable=bool(cd_enable),
                        cd_method=str(cd_method),
                        cd_fraction_of_Paux=float(cd_fraction_of_Paux),
                        f_NI_min=float(f_NI_min),
                        disruption_risk_max=float(disruption_risk_max),
                                        include_availability_replacement_v359=bool(locals().get('include_availability_replacement_v359', False)),
                        planned_outage_base=float(locals().get('planned_outage_base', 0.05)),
                        heating_cd_replace_interval_y=float(locals().get('heating_cd_replace_interval_y', 8.0)),
                        heating_cd_replace_duration_days=float(locals().get('heating_cd_replace_duration_days', 30.0)),
                        tritium_plant_replace_interval_y=float(locals().get('tritium_plant_replace_interval_y', 10.0)),
                        tritium_plant_replace_duration_days=float(locals().get('tritium_plant_replace_duration_days', 30.0)),
                        availability_v359_min=float(locals().get('availability_v359_min', float('nan'))),
                        LCOE_max_USD_per_MWh=float(locals().get('LCOE_max_USD_per_MWh', float('nan'))),

                        include_maintenance_scheduling_v368=bool(locals().get('include_maintenance_scheduling_v368', False)),
                        maintenance_planning_horizon_yr=float(locals().get('maintenance_planning_horizon_yr', float('nan'))),
                        maintenance_bundle_policy=str(locals().get('maintenance_bundle_policy', 'independent')),
                        maintenance_bundle_overhead_days=float(locals().get('maintenance_bundle_overhead_days', 7.0)),
                        forced_outage_mode_v368=str(locals().get('forced_outage_mode_v368', 'max')),
                        outage_fraction_v368_max=float(locals().get('outage_fraction_v368_max', float('nan'))),
                        availability_v368_min=float(locals().get('availability_v368_min', float('nan'))),

                        include_availability_reliability_v391=bool(locals().get('include_availability_reliability_v391', False)),
                        planned_outage_days_per_y_v391=float(locals().get('planned_outage_days_per_y_v391', 30.0)),
                        mtbf_tf_h_v391=float(locals().get('mtbf_tf_h_v391', 80000.0)),
                        mttr_tf_h_v391=float(locals().get('mttr_tf_h_v391', 240.0)),
                        mtbf_pfcs_h_v391=float(locals().get('mtbf_pfcs_h_v391', 60000.0)),
                        mttr_pfcs_h_v391=float(locals().get('mttr_pfcs_h_v391', 168.0)),
                        mtbf_divertor_h_v391=float(locals().get('mtbf_divertor_h_v391', 20000.0)),
                        mttr_divertor_h_v391=float(locals().get('mttr_divertor_h_v391', 336.0)),
                        mtbf_blanket_h_v391=float(locals().get('mtbf_blanket_h_v391', 25000.0)),
                        mttr_blanket_h_v391=float(locals().get('mttr_blanket_h_v391', 504.0)),
                        mtbf_cryo_h_v391=float(locals().get('mtbf_cryo_h_v391', 40000.0)),
                        mttr_cryo_h_v391=float(locals().get('mttr_cryo_h_v391', 120.0)),
                        mtbf_hcd_h_v391=float(locals().get('mtbf_hcd_h_v391', 30000.0)),
                        mttr_hcd_h_v391=float(locals().get('mttr_hcd_h_v391', 168.0)),
                        mtbf_bop_h_v391=float(locals().get('mtbf_bop_h_v391', 50000.0)),
                        mttr_bop_h_v391=float(locals().get('mttr_bop_h_v391', 72.0)),
                        availability_min_v391=float(locals().get('availability_min_v391', float('nan'))),
                        planned_outage_max_frac_v391=float(locals().get('planned_outage_max_frac_v391', float('nan'))),
                        unplanned_downtime_max_frac_v391=float(locals().get('unplanned_downtime_max_frac_v391', float('nan'))),
                        maint_downtime_max_frac_v391=float(locals().get('maint_downtime_max_frac_v391', float('nan'))),

                        include_economics_v360=bool(locals().get('include_economics_v360', False)),
                        opex_fixed_MUSD_per_y=float(locals().get('opex_fixed_MUSD_per_y', 0.0)),
                        tritium_processing_cost_USD_per_g=float(locals().get('tritium_processing_cost_USD_per_g', 0.05)),
                        cryo_wallplug_multiplier=float(locals().get('cryo_wallplug_multiplier', 250.0)),
                        OPEX_max_MUSD_per_y=float(locals().get('OPEX_max_MUSD_per_y', float('nan'))),

                        include_economics_v383=bool(locals().get('include_economics_v383', False)),
                        CAPEX_structured_max_MUSD=float(locals().get('CAPEX_structured_max_MUSD', float('nan'))),
                        OPEX_structured_max_MUSD_per_y=float(locals().get('OPEX_structured_max_MUSD_per_y', float('nan'))),
                        LCOE_lite_max_USD_per_MWh=float(locals().get('LCOE_lite_max_USD_per_MWh', float('nan'))),

                        include_cost_authority_v388=bool(locals().get('include_cost_authority_v388', False)),
                        CAPEX_industrial_max_MUSD=float(locals().get('CAPEX_industrial_max_MUSD', float('nan'))),
                        OPEX_industrial_max_MUSD_per_y=float(locals().get('OPEX_industrial_max_MUSD_per_y', float('nan'))),
                        LCOE_lite_v388_max_USD_per_MWh=float(locals().get('LCOE_lite_v388_max_USD_per_MWh', float('nan'))),

                        include_structural_stress_v389=bool(locals().get('include_structural_stress_v389', False)),
                        tf_struct_margin_min_v389=float(locals().get('tf_struct_margin_min_v389', 1.0)),
                        t_cs_struct_m_v389=float(locals().get('t_cs_struct_m_v389', 0.20)),
                        sigma_cs_allow_MPa_v389=float(locals().get('sigma_cs_allow_MPa_v389', 300.0)),
                        cs_struct_margin_min_v389=float(locals().get('cs_struct_margin_min_v389', 1.0)),
                        vv_ext_pressure_MPa_v389=float(locals().get('vv_ext_pressure_MPa_v389', 0.101)),
                        sigma_vv_allow_MPa_v389=float(locals().get('sigma_vv_allow_MPa_v389', 200.0)),
                        vv_struct_margin_min_v389=float(locals().get('vv_struct_margin_min_v389', 1.0)),

                        include_damage_strength_coupling_v393=bool(locals().get('include_damage_strength_coupling_v393', False)),
                        design_life_fpy_v393=float(locals().get('design_life_fpy_v393', 10.0)),
                        k_allow_deg_per_dpa_v393=float(locals().get('k_allow_deg_per_dpa_v393', 0.003)),
                        min_allow_frac_v393=float(locals().get('min_allow_frac_v393', 0.50)),
                        dpa_factor_tf_v393=float(locals().get('dpa_factor_tf_v393', 0.05)),
                        dpa_factor_cs_v393=float(locals().get('dpa_factor_cs_v393', 0.05)),
                        dpa_factor_vv_v393=float(locals().get('dpa_factor_vv_v393', 0.20)),
                        tf_struct_margin_degraded_min_v393=float(locals().get('tf_struct_margin_degraded_min_v393', float('nan'))),
                        cs_struct_margin_degraded_min_v393=float(locals().get('cs_struct_margin_degraded_min_v393', float('nan'))),
                        vv_struct_margin_degraded_min_v393=float(locals().get('vv_struct_margin_degraded_min_v393', float('nan'))),

                        include_neutronics_activation_v390=bool(locals().get('include_neutronics_activation_v390', False)),
                        blanket_class_v390=str(locals().get('blanket_class_v390', 'STANDARD')),
                        shield_req_Pfus_exp_v390=float(locals().get('shield_req_Pfus_exp_v390', 0.25)),
                        shield_req_qwall_exp_v390=float(locals().get('shield_req_qwall_exp_v390', 0.50)),
                        fw_dpa_per_fpy_per_MWm2_v390=float(locals().get('fw_dpa_per_fpy_per_MWm2_v390', 15.0)),
                        fw_dpa_limit_v390=float(locals().get('fw_dpa_limit_v390', 20.0)),
                        shield_margin_min_cm_v390=float(locals().get('shield_margin_min_cm_v390', float('nan'))),
                        fw_life_min_fpy_v390=float(locals().get('fw_life_min_fpy_v390', float('nan'))),
                        dpa_per_fpy_max_v390=float(locals().get('dpa_per_fpy_max_v390', float('nan'))),
                        activation_index_max_v390=float(locals().get('activation_index_max_v390', float('nan'))),

                        include_neutronics_shield_attenuation_v392=bool(locals().get('include_neutronics_shield_attenuation_v392', False)),
                        gap_to_tf_case_m_v392=float(locals().get('gap_to_tf_case_m_v392', 0.20)),
                        gap_to_cryostat_m_v392=float(locals().get('gap_to_cryostat_m_v392', 0.80)),
                        gap_to_bioshield_m_v392=float(locals().get('gap_to_bioshield_m_v392', 1.20)),
                        t_bioshield_m_v392=float(locals().get('t_bioshield_m_v392', 1.20)),
                        atten_len_stack_m_v392=float(locals().get('atten_len_stack_m_v392', float('nan'))),
                        atten_len_bioshield_m_v392=float(locals().get('atten_len_bioshield_m_v392', 0.35)),
                        use_inv_square_geom_v392=bool(locals().get('use_inv_square_geom_v392', True)),
                        dose_uSv_h_per_flux_n_m2_s_v392=float(locals().get('dose_uSv_h_per_flux_n_m2_s_v392', 1.0e-20)),
                        tf_case_fluence_max_n_m2_per_fpy_v392=float(locals().get('tf_case_fluence_max_n_m2_per_fpy_v392', float('nan'))),
                        cryostat_fluence_max_n_m2_per_fpy_v392=float(locals().get('cryostat_fluence_max_n_m2_per_fpy_v392', float('nan'))),
                        bioshield_dose_rate_max_uSv_h_v392=float(locals().get('bioshield_dose_rate_max_uSv_h_v392', float('nan'))),

                        include_neutronics_materials_library_v403=bool(locals().get('include_neutronics_materials_library_v403', False)),
                        nm_stack_json_v403=str(locals().get('nm_stack_json_v403', getattr(defaults, 'nm_stack_json_v403', ''))),
                        nm_group_frac_fast_v403=float(locals().get('nm_group_frac_fast_v403', 0.90)),
                        nm_group_frac_epi_v403=float(locals().get('nm_group_frac_epi_v403', 0.08)),
                        nm_group_frac_therm_v403=float(locals().get('nm_group_frac_therm_v403', 0.02)),
                        dpa_fw_max_v403=float(locals().get('dpa_fw_max_v403', float('nan'))),
                        he_appm_fw_max_v403=float(locals().get('he_appm_fw_max_v403', float('nan'))),
                        cooldown_burden_max_days_v403=float(locals().get('cooldown_burden_max_days_v403', float('nan'))),
                        tbr_proxy_min_v403=float(locals().get('tbr_proxy_min_v403', float('nan'))),
                        fast_attenuation_min_v403=float(locals().get('fast_attenuation_min_v403', float('nan'))),

                        include_nuclear_data_authority_v407=bool(locals().get('include_nuclear_data_authority_v407', False)),
                        nuclear_dataset_id_v407=str(locals().get('nuclear_dataset_id_v407', 'SCREENING_PROXY_V407')),
                        nuclear_group_structure_id_v407=str(locals().get('nuclear_group_structure_id_v407', 'G6_V407')),

                        include_neutronics_materials_authority_v401=bool(locals().get('include_neutronics_materials_authority_v401', False)),
                        nm_contract_tier_v401=str(locals().get('nm_contract_tier_v401', 'NOMINAL')),
                        nm_fragile_margin_frac_v401=float(locals().get('nm_fragile_margin_frac_v401', 0.10)),
                        tf_case_fluence_max_n_m2_per_fpy_override_v401=float(locals().get('tf_case_fluence_max_n_m2_per_fpy_override_v401', float('nan'))),
                        bioshield_dose_rate_max_uSv_h_override_v401=float(locals().get('bioshield_dose_rate_max_uSv_h_override_v401', float('nan'))),
                        P_nuc_TF_max_MW_override_v401=float(locals().get('P_nuc_TF_max_MW_override_v401', float('nan'))),
                        dpa_per_fpy_max_override_v401=float(locals().get('dpa_per_fpy_max_override_v401', float('nan'))),
                        fw_He_total_limit_appm_override_v401=float(locals().get('fw_He_total_limit_appm_override_v401', float('nan'))),
                        activation_index_max_override_v401=float(locals().get('activation_index_max_override_v401', float('nan'))),
                        TBR_min_override_v401=float(locals().get('TBR_min_override_v401', float('nan'))),

                        
                        include_structural_life_v404=bool(locals().get('include_structural_life_v404', False)),
                        pulse_count_v404=float(locals().get('pulse_count_v404', float('nan'))),
                        hot_fraction_v404=float(locals().get('hot_fraction_v404', 0.2)),
                        service_years_v404=float(locals().get('service_years_v404', 1.0)),
                        material_fw_v404=str(locals().get('material_fw_v404', 'EUROFER')),
                        material_vv_v404=str(locals().get('material_vv_v404', 'SS316')),
                        material_tf_v404=str(locals().get('material_tf_v404', 'INCONEL')),
                        T_fw_K_v404=float(locals().get('T_fw_K_v404', 700.0)),
                        T_vv_K_v404=float(locals().get('T_vv_K_v404', 450.0)),
                        T_tf_K_v404=float(locals().get('T_tf_K_v404', 350.0)),
                        fw_delta_sigma_MPa_v404=float(locals().get('fw_delta_sigma_MPa_v404', float('nan'))),
                        vv_delta_sigma_MPa_v404=float(locals().get('vv_delta_sigma_MPa_v404', float('nan'))),
                        tf_delta_sigma_MPa_v404=float(locals().get('tf_delta_sigma_MPa_v404', float('nan'))),
                        fw_t_m_v404=float(locals().get('fw_t_m_v404', float('nan'))),
                        fw_R_m_v404=float(locals().get('fw_R_m_v404', float('nan'))),
                        fw_panel_span_m_v404=float(locals().get('fw_panel_span_m_v404', float('nan'))),
                        vv_t_m_v404=float(locals().get('vv_t_m_v404', float('nan'))),
                        vv_R_m_v404=float(locals().get('vv_R_m_v404', float('nan'))),
                        vv_span_m_v404=float(locals().get('vv_span_m_v404', float('nan'))),
                        tf_t_m_v404=float(locals().get('tf_t_m_v404', float('nan'))),
                        tf_R_m_v404=float(locals().get('tf_R_m_v404', float('nan'))),
                        tf_span_m_v404=float(locals().get('tf_span_m_v404', float('nan'))),
                        struct_min_margin_frac_v404=float(locals().get('struct_min_margin_frac_v404', float('nan'))),

include_authority_dominance_v402=bool(locals().get('include_authority_dominance_v402', True)),
                        transport_spread_ref_v402=float(locals().get('transport_spread_ref_v402', 3.0)),
                        profile_peaking_p_ref_v402=float(locals().get('profile_peaking_p_ref_v402', 3.0)),
                        zeff_ref_max_v402=float(locals().get('zeff_ref_max_v402', 2.5)),


                        include_materials_lifetime_v384=bool(locals().get('include_materials_lifetime_v384', False)),
                        divertor_life_ref_yr=float(locals().get('divertor_life_ref_yr', 3.0)),
                        divertor_q_ref_MW_m2=float(locals().get('divertor_q_ref_MW_m2', 10.0)),
                        divertor_q_exp=float(locals().get('divertor_q_exp', 2.0)),
                        divertor_capex_fraction_of_total=float(locals().get('divertor_capex_fraction_of_total', 0.05)),
                        magnet_life_ref_yr=float(locals().get('magnet_life_ref_yr', 30.0)),
                        magnet_margin_ref=float(locals().get('magnet_margin_ref', 0.10)),
                        magnet_margin_exp=float(locals().get('magnet_margin_exp', 1.5)),
                        base_capacity_factor=float(locals().get('base_capacity_factor', 0.75)),
                        capacity_factor_max=float(locals().get('capacity_factor_max', 0.95)),
                        fw_downtime_days=float(locals().get('fw_downtime_days', 30.0)),
                        blanket_downtime_days=float(locals().get('blanket_downtime_days', 60.0)),
                        divertor_downtime_days=float(locals().get('divertor_downtime_days', 20.0)),
                        magnet_downtime_days=float(locals().get('magnet_downtime_days', 120.0)),
                        fw_capex_fraction_of_blanket=float(locals().get('fw_capex_fraction_of_blanket', 0.20)),
                        blanket_capex_fraction_of_blanket=float(locals().get('blanket_capex_fraction_of_blanket', 1.00)),
                        fw_lifetime_min_yr_v384=float(locals().get('fw_lifetime_min_yr_v384', float('nan'))),
                        blanket_lifetime_min_yr_v384=float(locals().get('blanket_lifetime_min_yr_v384', float('nan'))),
                        divertor_lifetime_min_yr_v384=float(locals().get('divertor_lifetime_min_yr_v384', float('nan'))),
                        magnet_lifetime_min_yr_v384=float(locals().get('magnet_lifetime_min_yr_v384', float('nan'))),
                        replacement_cost_max_MUSD_per_y_v384=float(locals().get('replacement_cost_max_MUSD_per_y_v384', float('nan'))),
                        capacity_factor_min_v384=float(locals().get('capacity_factor_min_v384', float('nan'))),
                    )

                    # UI-only guardrails: warn on obviously unrealistic knobs (does not block).
                    base = merge_overlay_session_into_inputs(base, st.session_state)
                    _warn_unrealistic_point_inputs(base, context="Point Designer")
                    if do_opt:
                        _log(f"Optimization enabled: objective={opt_objective}, iters={opt_iters}, seed={opt_seed}")
                        var_bounds = {"Ip_MA": (Ip_min, Ip_max), "fG": (fG_min, fG_max), "Paux_MW": (0.0, max(Paux, 1e-6)*2.0)}
                        best_inp, best_out = optimize_design(
                            base,
                            objective=opt_objective,
                            variables=var_bounds,
                            n_iter=opt_iters,
                            seed=opt_seed,
                        )
                        base = best_inp
                        _log(f"Optimization chose: Ip={best_inp.Ip_MA:.4g} MA, fG={best_inp.fG:.4g}, Paux={best_inp.Paux_MW:.4g} MW")
                        _log(f"Optimized outputs: Bpeak={best_out.get('B_peak_T', float('nan')):.4g} T, Pnet={best_out.get('P_e_net_MW', float('nan')):.4g} MW")
                    # Optional: show solver progress so the user can "see physics happening".
                    if show_solver_live:
                        status = None
                        prog = None
                        chart = None
                        table = None
                        latest = None
                        if _pd_tel_view == "Chronicle & Export":
                            with st.expander("Live Convergence", expanded=False):
                                status = st.empty()
                                prog = st.progress(0)
                                # Live convergence diagnostics
                                chart = st.empty()
                                table = st.empty()
                                latest = st.empty()
    
                        trace_rows = []
                        sol_inp, out, ok = None, {}, False

                        # Select solver iterator (legacy stream solver vs envelope solve)
                        if use_envelope:
                            tgt = {'Q_DT_eqv': Q_target, 'H98': H98_target}
                            sol_inp_env, out_env, ok_env, msg_env = solve_sparc_envelope(
                                base, tgt, vary=['Ip_MA','fG'],
                                bounds={'Ip_MA': (Ip_min, Ip_max), 'fG': (fG_min, fG_max)},
                                tol=tol, max_iter=40,
                            )
                            def _env_events():
                                yield {'event':'iter','it':0,'Ip_MA': sol_inp_env.Ip_MA, 'fG': sol_inp_env.fG, 'H98': out_env.get('H98', float('nan')), 'Q_DT_eqv': out_env.get('Q_DT_eqv', float('nan'))}
                                yield {'event':'done','sol': sol_inp_env, 'out': out_env, 'ok': ok_env, 'message': msg_env}
                            event_iter = _env_events()
                        else:
                            event_iter = solve_Ip_for_H98_with_Q_match_stream(
                            base=base,
                            target_H98=H98_target,
                            target_Q=Q_target,
                            Ip_min=Ip_min, Ip_max=Ip_max,
                            fG_min=fG_min, fG_max=fG_max,
                            tol=tol,
                            Paux_for_Q_MW=Paux_for_Q,
                        )
                        for ev in event_iter:
                            if ev.get("event") == "bracket":
                                okb = bool(ev.get("ok"))
                                try:
                                    _log(
                                        f"BRACKET: H98(Ip_lo={ev.get('Ip_lo'):.6g})={ev.get('H98_lo'):.6g}, H98(Ip_hi={ev.get('Ip_hi'):.6g})={ev.get('H98_hi'):.6g} -> {'OK' if okb else 'NO_BRACKET'}"
                                    )
                                except Exception:
                                    _log(f"BRACKET: ok={okb}")
                                if status is not None:
                                    status.info(
                                        f"Bracketing H98 target: H98(Ip_min={ev.get('Ip_lo'):.3g})={ev.get('H98_lo'):.3g}, "
                                        f"H98(Ip_max={ev.get('Ip_hi'):.3g})={ev.get('H98_hi'):.3g} → "
                                        f"{'OK' if okb else 'NO BRACKET'}"
                                    )
                            elif ev.get("event") == "iter":
                                try:
                                    _log(
                                        f"ITER {int(ev.get('iter', 0)):>3d}: Ip={ev.get('Ip_MA'):.8g} MA, fG={ev.get('fG'):.8g}, H98={ev.get('H98'):.8g}, Q={ev.get('Q'):.8g}, residual={ev.get('residual'):.8g}"
                                    )
                                except Exception:
                                    _log(f"ITER {ev.get('iter')}: {ev}")
                                trace_rows.append({
                                    "iter": ev.get("iter"),
                                    "Ip_MA": ev.get("Ip_MA"),
                                    "fG": ev.get("fG"),
                                    "H98": ev.get("H98"),
                                    "Q": ev.get("Q"),
                                    "residual": ev.get("residual"),
                                })
                                it = int(ev.get("iter", 0))
                                if prog is not None:
                                    prog.progress(min(1.0, (it + 1) / 80.0))
                                if latest is not None:
                                    latest.metric("Current guess Ip (MA)", f"{ev.get('Ip_MA', float('nan')):.4g}")
                                if trace_rows:
                                    df = pd.DataFrame(trace_rows)
                                    # Two quick plots: residual and key state variables
                                    if chart is not None:
                                        chart.line_chart(df.set_index("iter")[["residual"]])
                                    if table is not None:
                                        table.dataframe(df.tail(10), use_container_width=True)
                            elif ev.get("event") == "done":
                                sol_inp = ev.get("sol")
                                out = ev.get("out", {})
                                ok = True
                                try:
                                    _log(
                                        f"DONE: Ip={out.get('Ip_MA', float('nan')):.8g} MA, fG={out.get('fG', float('nan')):.8g}, H98={out.get('H98', float('nan')):.8g}, Q_DT_eqv={out.get('Q_DT_eqv', float('nan')):.8g}"
                                    )
                                except Exception:
                                    _log("DONE")
                                if bool(out.get("_solver_clamped")) or bool(out.get("_solver_clamped_Q")):
                                    if status is not None:
                                        status.warning("Solver returned a point by clamping to the nearest bound (target not achievable within bounds). See log/details below.")
                                else:
                                    if status is not None:
                                        status.success("Solver converged.")
                                # Live progress UI exists only when the Chronicle deck is active.
                                if prog is not None:
                                    prog.progress(1.0)
                                break
                            elif ev.get("event") == "fail":
                                reason = ev.get("reason", "solver_failed")
                                _log("FAIL EVENT: "+ json.dumps(ev, sort_keys=True))
                                it_fail = ev.get("it", None)
                                mi_fail = ev.get("max_iter", None)
                                extra = ""
                                if it_fail is not None and mi_fail is not None:
                                    extra = f"(it={it_fail}/{mi_fail})"
                                if status is not None:
                                    status.error(f"Solver failed ({reason}){extra}. Try widening Ip/fG bounds or relaxing targets.")
                                ok = False
                                break
                    else:
                        sol_inp, out, ok = solve_Ip_for_H98_with_Q_match(
                            base=base,
                            target_H98=H98_target,
                            target_Q=Q_target,
                            Ip_min=Ip_min, Ip_max=Ip_max,
                            fG_min=fG_min, fG_max=fG_max,
                            tol=tol,
                            Paux_for_Q_MW=Paux_for_Q,
                        )
                        # Minimal log summary when running in non-stream mode.
                        if ok:
                            try:
                                _log(
                                    f"DONE: Ip={out.get('Ip_MA', float('nan')):.8g} MA, fG={out.get('fG', float('nan')):.8g}, H98={out.get('H98', float('nan')):.8g}, Q_DT_eqv={out.get('Q_DT_eqv', float('nan')):.8g}"
                                )
                            except Exception:
                                _log("DONE")
                        else:
                            _log("FAIL: solver_failed")

                    # Always show expandable log for this run.
                    solver_log_text = "\n".join(log_lines).strip() + "\n"
                    st.session_state.last_solver_log = solver_log_text
                    if _pd_tel_view == "Chronicle & Export":
                        with st.expander("Chronicle - Solver Log", expanded=False):
                            st.download_button(
                                "Download log",
                                data=solver_log_text,
                                file_name="point_designer_solver.log",
                                mime="text/plain",
                                use_container_width=True,
                            )
                            st.code(solver_log_text)
                    if not ok:
                        # Provide best-effort diagnostics if available (e.g., H98 at bounds)
                        msg = "Solver failed to converge for (Ip, fG) at the requested (H98, Q) targets."
                        try:
                            if isinstance(out, dict) and ("H98_at_Ip_min"in out or "H98_at_Ip_max"in out):
                                msg += f"H98(Ip_min)={out.get('H98_at_Ip_min')}, H98(Ip_max)={out.get('H98_at_Ip_max')}"
                        except Exception:
                            pass
                        st.error(msg)
                        try:
                            _alog(
                                "Point Designer",
                                "EvaluatePointResult",
                                {
                                    "ok": False,
                                    "reason": "solver_failed",
                                    "inputs_hash": str(st.session_state.get("pd_current_inputs_hash", "")),
                                },
                            )
                        except Exception:
                            pass

                        # -----------------------------------------------------------------
                        # transparent (systems-code-inspired) feasibility frontier suggestion
                        # -----------------------------------------------------------------
                        with st.expander("Try to find nearest feasible point (frontier)", expanded=False):
                            st.markdown(
                                "If the solver cannot hit the requested (H98, Q) targets inside the bounds, "
                                "SHAMS can still search for the *nearest feasible* design within your (Ip,fG) bounds. "
                                "This does **not** change your inputs automatically; it only proposes a candidate."
                            )
                            if st.button("Search nearest feasible within bounds", key="pd_frontier_btn", use_container_width=True):
                                try:
                                    fr = find_nearest_feasible(
                                        base,
                                        levers={"Ip_MA": (Ip_min, Ip_max), "fG": (fG_min, fG_max)},
                                        targets={"H98": float(H98_target), "Q_DT_eqv": float(Q_target)},
                                        n_random=80,
                                        seed=0,
                                    )
                                    st.session_state["pd_frontier_last"] = fr.report
                                except Exception as e:
                                    st.session_state["pd_frontier_last"] = {"status": "error", "message": str(e)}

                            rep = st.session_state.get("pd_frontier_last")
                            if isinstance(rep, dict) and rep:
                                if rep.get("status") == "error":
                                    st.error(rep.get("message", "frontier error"))
                                else:
                                    cols = st.columns(3)
                                    cols[0].metric("Best Ip (MA)", f"{rep.get('best_levers', {}).get('Ip_MA', float('nan')):.4g}")
                                    cols[1].metric("Best fG", f"{rep.get('best_levers', {}).get('fG', float('nan')):.4g}")
                                    cols[2].metric("Feasible?", "YES"if rep.get("best_ok") else "NO")
                                    ach = rep.get("best_achieved", {}) or {}
                                    st.write("Best achieved targets at proposed point:")
                                    st.json(ach)
                                    st.caption("Tip: widen bounds or relax targets if the frontier is still infeasible.")
                    else:
                        # Attach UI-only meta for checks (not used by physics core)
                        try:
                            out['_warn_frac_max'] = float(clean_knobs.get('_warn_frac_max', 0.90))
                            out['_warn_frac_min'] = float(clean_knobs.get('_warn_frac_min', 1.10))
                            out['_subsystem_enabled'] = clean_knobs.get('_subsystem_enabled', {})
                        except Exception:
                            pass
                        st.session_state["last_point_out"] = out
                        # Persist cached Point Designer result across Streamlit reruns (downloads)
                        st.session_state['pd_last_outputs'] = out

                        # Mark cache freshness
                        try:
                            import time as _time
                            st.session_state["pd_last_run_ts"] = float(_time.time())
                            st.session_state["pd_last_inputs_hash"] = st.session_state.get("pd_current_inputs_hash")
                        except Exception:
                            pass

                        # Activity log: successful point evaluation (constraint-first summary)
                        try:
                            _failed_hard = []
                            try:
                                _failed_hard = [str(c.name) for c in (evaluate_constraints(out) or []) if str(getattr(c,'severity','soft'))=='hard' and (not bool(getattr(c,'passed', False)))]
                            except Exception:
                                _failed_hard = []

                            _cls = _classify_failed_constraints(_failed_hard)
                            _policy = _constraint_policy_snapshot()
                            _alog(
                                "Point Designer",
                                "EvaluatePointResult",
                                {
                                    "ok": True,
                                    "inputs_hash": str(st.session_state.get("pd_current_inputs_hash", "")),
                                    "design_intent": str(st.session_state.get("design_intent", "Power Reactor (net-electric)")),
                                    "constraint_policy": _policy,
                                    "failed_hard": _failed_hard,
                                    "failed_blocking": list(_cls.get('blocking', [])),
                                    "failed_diagnostic": list(_cls.get('diagnostic', [])),
                                    "failed_ignored": list(_cls.get('ignored', [])),
                                    "headline": {"H98": float(out.get("H98", float('nan'))), "Q_DT_eqv": float(out.get("Q_DT_eqv", float('nan')))},
        },
                            )
                        except Exception:
                            pass


                        # -----------------------------------------------------------------
                        # transparent (systems-code-inspired) canonical output artifact (SHAMS-native JSON)
                        # -----------------------------------------------------------------
                        try:
                            inputs_dict = dict(base.__dict__)
                        except Exception:
                            inputs_dict = {}
                        try:
                            constraints_list = evaluate_constraints(out)
                        except Exception:
                            constraints_list = []
                        try:
                            solver_meta = None
                            try:
                                solver_meta = dict(out.get("_solver")) if isinstance(out.get("_solver"), dict) else None
                            except Exception:
                                solver_meta = None
                            if solver_meta is not None:
                                # Attach UI log if available
                                try:
                                    solver_meta.setdefault("ui_log", st.session_state.get("last_solver_log", ""))
                                except Exception:
                                    pass
                            artifact = build_run_artifact(
                                inputs=inputs_dict,
                                outputs=dict(out),
                                constraints=constraints_list,
                                meta=None,
                                baseline_inputs=inputs_dict,
                                fidelity={"assumptions": _pd_assumptions_snapshot(), "config": st.session_state.get("fidelity_config", {})}, calibration={"confinement": float(st.session_state.get("calib_confinement",1.0)), "divertor": float(st.session_state.get("calib_divertor",1.0)), "bootstrap": float(st.session_state.get("calib_bootstrap",1.0))},
                                solver=solver_meta,
                            )
                        except Exception:
                            artifact = {"inputs": inputs_dict, "outputs": dict(out), "constraints": []}

                
                        # Attach intent-aware policy metadata (UI-only; does not affect physics core)
                        try:
                            artifact = _attach_common_metadata(artifact)
                            artifact["design_intent"] = str(st.session_state.get("design_intent", "Power Reactor (net-electric)"))
                            artifact["constraint_policy"] = _constraint_policy_snapshot()
                            # Authority contracts (deterministic metadata)
                            try:
                                from provenance.authority import authority_snapshot_from_outputs
                                artifact["authority_contracts"] = authority_snapshot_from_outputs(out if isinstance(out, dict) else {})
                            except Exception:
                                pass
                            # Human-readable run summary (audit / pasteable)
                            try:
                                artifact["run_summary"] = _compute_run_summary_from_out(out if isinstance(out, dict) else {})
                            except Exception:
                                pass
                        except Exception:
                            pass


                        # Optional: attach deterministic feasibility-forensics study output (if computed)
                        try:
                            ff = st.session_state.get("pd_last_forensics")
                            ff_h = st.session_state.get("pd_last_forensics_inputs_hash")
                            if isinstance(ff, dict) and ff and (ff_h == st.session_state.get("pd_current_inputs_hash")):
                                artifact.setdefault("studies", {})
                                artifact["studies"]["feasibility_forensics"] = ff
                        except Exception:
                            pass

                        # cache the last point artifact for cross-panel use and exports
                        st.session_state['pd_last_artifact'] = artifact

                        # Provide downloadable artifacts and reports (no side effects unless user clicks)
                        if _pd_tel_view == "Chronicle & Export":
                            with st.expander("Export Bay - Artifacts & Downloads", expanded=False):
                                st.download_button(
                                    "Download run artifact JSON",
                                    data=_shams_json_dumps(artifact, indent=2, sort_keys=True),
                                    file_name="shams_run_artifact.json",
                                    mime="application/json",
                                    use_container_width=True,
                                )

                                # Independence 4.2: Cite-SHAMS handoff pack (VERSION + hashes + citation)
                                try:
                                    from reports.cite_shams_handoff_pack import build_cite_shams_handoff_pack
                                    _cite_pack = build_cite_shams_handoff_pack(artifact)
                                    st.download_button(
                                        "Download cite-SHAMS handoff pack",
                                        data=_cite_pack["zip_bytes"],
                                        file_name=_cite_pack.get("suggested_filename") or "shams_cite_handoff.zip",
                                        mime="application/zip",
                                        use_container_width=True,
                                        key="pd_cite_shams_handoff_pack",
                                        help="VERSION + PointInputs + artifact SHA-256 + citation; PROCESS import optional.",
                                    )
                                except Exception as _cite_exc:
                                    st.caption(f"Cite-SHAMS handoff pack unavailable: {_cite_exc}")

                                # Quick interop: send this run artifact to Compare session slots (A/B)
                                st.caption("Quick interop: send the current run to Compare without downloading/uploading files.")
                                _c1, _c2, _c3 = st.columns([1, 1, 1])
                                with _c1:
                                    if st.button("Send to Compare Slot A", use_container_width=True, key="pd_send_cmp_A"):
                                        st.session_state["cmp_slot_A"] = artifact
                                        st.session_state["cmp_slot_A_meta"] = {
                                            "ts_unix": float(time.time()),
                                            "inputs_hash": str(st.session_state.get("pd_last_inputs_hash") or st.session_state.get("pd_current_inputs_hash") or ""),
                                            "label": "Point Designer (last run)",
                                        }
                                        st.success("Sent current run to Compare Slot A.")
                                with _c2:
                                    if st.button("Send to Compare Slot B", use_container_width=True, key="pd_send_cmp_B"):
                                        st.session_state["cmp_slot_B"] = artifact
                                        st.session_state["cmp_slot_B_meta"] = {
                                            "ts_unix": float(time.time()),
                                            "inputs_hash": str(st.session_state.get("pd_last_inputs_hash") or st.session_state.get("pd_current_inputs_hash") or ""),
                                            "label": "Point Designer (last run)",
                                        }
                                        st.success("Sent current run to Compare Slot B.")
                                with _c3:
                                    if st.button("Clear Compare Slots", use_container_width=True, key="pd_clear_cmp_slots"):
                                        st.session_state.pop("cmp_slot_A", None)
                                        st.session_state.pop("cmp_slot_B", None)
                                        st.session_state.pop("cmp_slot_A_meta", None)
                                        st.session_state.pop("cmp_slot_B_meta", None)
                                        st.info("Cleared Compare slots.")

    
                                # Radial build PNG
                                try:
                                    import tempfile
                                    tmpdir = tempfile.mkdtemp(prefix="shams_export_")
                                    radial_path = os.path.join(tmpdir, "radial_build.png")
                                    plot_radial_build_from_artifact(artifact, radial_path)
                                    with open(radial_path, "rb") as f:
                                        _rb_bytes = f.read()
                                    # cache bytes for reruns / PAM / other panels
                                    try:
                                        st.session_state["pd_last_radial_png_bytes"] = _rb_bytes
                                        _s = st.session_state.get('shams_state', None)
                                        if _s is not None:
                                            setattr(_s, 'last_point_radial_png', _rb_bytes)
                                    except Exception:
                                        pass
                                    if isinstance(_rb_bytes, (bytes, bytearray)) and len(_rb_bytes) > 0:
                                        st.download_button(
                                            "Download radial build PNG",
                                            data=_rb_bytes,
                                            file_name="shams_radial_build.png",
                                            mime="image/png",
                                            use_container_width=True,
                                        )
                                except Exception as _e:
                                    st.caption("Radial-build export unavailable for this point.")
    
                                # Summary PDF
                                try:
                                    import tempfile
                                    tmpdir2 = tempfile.mkdtemp(prefix="shams_export_")
                                    pdf_path = os.path.join(tmpdir2, "summary.pdf")
                                    plot_summary_pdf(artifact, pdf_path)
                                    with open(pdf_path, "rb") as f:
                                        _pdf_bytes = f.read()
                                    try:
                                        st.session_state["pd_last_summary_pdf_bytes"] = _pdf_bytes
                                        _s = st.session_state.get('shams_state', None)
                                        if _s is not None:
                                            setattr(_s, 'last_point_summary_pdf', _pdf_bytes)
                                    except Exception:
                                        pass
                                    if isinstance(_pdf_bytes, (bytes, bytearray)) and len(_pdf_bytes) > 0:
                                        st.download_button(
                                            "Download summary PDF",
                                            data=_pdf_bytes,
                                            file_name="shams_summary.pdf",
                                            mime="application/pdf",
                                            use_container_width=True,
                                        )
                                except Exception:
                                    st.caption("PDF summary export unavailable for this point.")
    
                        if _pd_tel_view == "Mission Snapshot":
                            with st.expander("Mission Snapshot - Key KPIs", expanded=False):
                                # Standardized KPI set shared with PDF (see decision.kpis.KPI_SET)
                                kpis = headline_kpis(out)
                                for i in range(0, len(kpis), 4):
                                    kpi_row(kpis[i:i+4])
                                    if i + 4 < len(kpis):
                                        st.divider()

                                # --- Deep physics cards (read-only; deterministic)
                                with st.expander("Physics Deepening - Regimes · Burn · Impurities · Edge · Neutronics", expanded=False):
                                    _deep_view = st.selectbox(
                                        "Select deck",
                                        options=[
                                            "Regime & Confinement",
                                            "Global dominance & regime",
                                            "Current Profile & Current Drive",
                                            "Bootstrap–Pressure Self-Consistency Authority",
                                            "Current Drive Tech Authority",
                                            "Non-Inductive Closure Authority",
                                            "Burn & Alpha Power",
                                            "Impurities & Core Radiation",
                                            "Edge/Divertor & Exhaust Control",
                                            "Neutronics & Nuclear Loads",
                                            "Coupling Narratives",
                                        ],
                                        index=0,
                                        key="pd_deep_physics_view",
                                    )

                                    def _safe_num(k: str) -> float:
                                        try:
                                            return float(out.get(k, float('nan')))
                                        except Exception:
                                            return float('nan')

                                    if _deep_view == "Regime & Confinement":
                                        cA, cB, cC, cD = st.columns([1.0, 1.0, 1.0, 1.0])
                                        cA.metric("Regime label", str(out.get("confinement_regime", "unknown")))
                                        cB.metric("H98", f"{_safe_num('H98'):.2f}"if _safe_num('H98') == _safe_num('H98') else "n/a")
                                        cC.metric("H_regime", f"{_safe_num('H_regime'):.2f}"if _safe_num('H_regime') == _safe_num('H_regime') else "n/a")
                                        cD.metric("P_LH (MW)", f"{_safe_num('P_LH_MW'):.1f}"if _safe_num('P_LH_MW') == _safe_num('P_LH_MW') else "n/a")
                                        st.caption("H_regime is reported only when couple_regime_to_confinement=True; it uses IPB98 for H-regime and ITER89P for L-regime.")

                                    elif _deep_view == "Global dominance & regime":
                                        st.caption(
                                            "Dominance engine aggregates governance-only authority margins into a global dominance ranking (worst→best), "
                                            "labels the limiting regime, and flags feasibility mirages (feasible but credibility-fragile)."
                                        )
                                        if not bool(out.get("include_authority_dominance_v402", False)):
                                            st.info("Dominance engine is OFF. Enable it in Point Designer → Global authority dominance engine.")
                                        else:
                                            g1, g2, g3, g4 = st.columns([1.0, 1.0, 1.0, 1.0])
                                            _m = _safe_num("global_min_margin_v402")
                                            g1.metric("Regime class", str(out.get("regime_class_v402", "unknown")))
                                            g2.metric("Dominant authority", str(out.get("global_dominant_authority_v402", "unknown")))
                                            g3.metric("Min margin (frac)", f"{_m:+.3f}"if _m == _m else "n/a")
                                            _gap = _safe_num("dominance_gap_to_second_v402")
                                            g4.metric("Gap to #2", f"{_gap:+.3f}"if _gap == _gap else "n/a")

                                            mir = bool(out.get("mirage_flag_v402", False))
                                            if mir:
                                                st.warning("Feasibility mirage flagged: credible-feasibility is fragile.")
                                                rs = out.get("mirage_reasons_v402", [])
                                                if isinstance(rs, list) and rs:
                                                    st.caption("Reasons: "+ ", ".join([str(x) for x in rs][:10]))
                                            else:
                                                st.success("No mirage flagged by dominance engine.")

                                            
                                            # v404.0.0: Structural Life Authority (summary)
                                            if bool(out.get("include_structural_life_v404", False)):
                                                with st.expander("Structural life summary", expanded=False):
                                                    st.caption(
                                                        f"**Global min margin:** {float(out.get('struct_global_min_margin_v404', float('nan'))):+.3f} | "
                                                        f"**Dominant:** {str(out.get('struct_dominant_component_v404','?'))} / {str(out.get('struct_dominant_mode_v404','?'))}"
                                                    )
                                                    tbl = out.get("struct_margin_table_v404", [])
                                                    if isinstance(tbl, list) and tbl:
                                                        st.dataframe(tbl, use_container_width=True, hide_index=True)
                                                    else:
                                                        st.info("No structural life table rows available.")
                                            else:
                                                # show hint only if user enabled dominance engine (they are here)
                                                pass

                                            with st.expander("Dominance ranking table", expanded=False):
                                                rows = out.get("dominance_order_v402", [])
                                                if isinstance(rows, list) and rows:
                                                    st.dataframe(rows, use_container_width=True, hide_index=True)
                                                else:
                                                    st.info("No dominance rows found (check that at least one authority produced finite margins).")

                                            refs = out.get("authority_dominance_refs_v402", {})
                                            if isinstance(refs, dict) and refs:
                                                st.caption(
                                                    f"Refs: transport_spread_ref={refs.get('transport_spread_ref', 'n/a')}, "
                                                    f"profile_peaking_p_ref={refs.get('profile_peaking_p_ref', 'n/a')}, "
                                                    f"zeff_ref_max={refs.get('zeff_ref_max', 'n/a')}"
                                                )
                                        # v336.0: plasma regime authority
                                        if str(out.get("plasma_regime", "")):
                                            st.divider()
                                            p1, p2, p3, p4 = st.columns([1.0, 1.0, 1.0, 1.0])
                                            p1.metric("Plasma regime", str(out.get("plasma_regime", "unknown")))
                                            p2.metric("Burn regime", str(out.get("burn_regime", "-")))
                                            p2.caption("ignited / alpha_assisted / aux_dominated")
                                            p3.metric("Fragility", str(out.get("plasma_fragility_class", "UNKNOWN")))
                                            _pm = _safe_num("plasma_min_margin_frac")
                                            p4.metric("Min margin (frac)", f"{_pm:.3f}"if _pm == _pm else "n/a")
                                            st.caption("Plasma regime authority is a deterministic classifier with signed fractional margins for H-mode access, Greenwald fraction, q95, betaN, and burn (M_ign_total). No solvers, no iteration.")

                                            # v337.0: impurity species & radiation partition authority
                                            if str(out.get("impurity_regime", "")):
                                                st.divider()
                                                i1, i2, i3, i4 = st.columns([1.0, 1.0, 1.0, 1.0])
                                                i1.metric("Impurity regime", str(out.get("impurity_regime", "unknown")))
                                                i2.metric("Species", str(out.get("impurity_species", "unknown")))
                                                i3.metric("Fragility", str(out.get("impurity_fragility_class", "UNKNOWN")))
                                                _im = _safe_num("impurity_min_margin_frac")
                                                i4.metric("Min margin (frac)", f"{_im:.3f}"if _im == _im else "n/a")
                                                st.caption("Impurity & radiation authority partitions core/SOL radiation and checks conservative thresholds on Zeff and radiated power fractions. Deterministic post-processing only; no solvers, no iteration.")

                            
                                    elif _deep_view == "Current Profile & Current Drive":
                                        cA, cB, cC, cD = st.columns([1.0, 1.0, 1.0, 1.0])
                                        cA.metric("Profile regime", str(out.get("current_profile_regime", "unknown")))
                                        cB.metric("Fragility", str(out.get("current_profile_fragility_class", "UNKNOWN")))
                                        mm = _safe_num("current_profile_min_margin_frac")
                                        cC.metric("Min margin (frac)", f"{mm:.3f}"if mm == mm else "n/a")
                                        cD.metric("Top limiter", str(out.get("current_profile_top_limiter", "UNKNOWN")))

                                        c1, c2, c3, c4 = st.columns([1.0, 1.0, 1.0, 1.0])
                                        c1.metric("q95 proxy", f"{_safe_num('q95_proxy'):.2f}"if _safe_num('q95_proxy') == _safe_num('q95_proxy') else "n/a")
                                        c2.metric("qmin proxy", f"{_safe_num('profile_qmin_proxy'):.2f}"if _safe_num('profile_qmin_proxy') == _safe_num('profile_qmin_proxy') else "n/a")
                                        c3.metric("f_bootstrap proxy", f"{_safe_num('profile_f_bootstrap_proxy'):.2f}"if _safe_num('profile_f_bootstrap_proxy') == _safe_num('profile_f_bootstrap_proxy') else (f"{_safe_num('f_bs_proxy'):.2f}"if _safe_num('f_bs_proxy') == _safe_num('f_bs_proxy') else "n/a"))
                                        c4.metric("f_NI", f"{_safe_num('f_NI'):.2f}"if _safe_num('f_NI') == _safe_num('f_NI') else "n/a")

                                        c5, c6, c7, c8 = st.columns([1.0, 1.0, 1.0, 1.0])
                                        c5.metric("I_cd (MA)", f"{_safe_num('I_cd_MA'):.2f}"if _safe_num('I_cd_MA') == _safe_num('I_cd_MA') else "n/a")
                                        c6.metric("P_cd (MW)", f"{_safe_num('P_cd_MW'):.1f}"if _safe_num('P_cd_MW') == _safe_num('P_cd_MW') else "n/a")
                                        c7.metric("η_CD (A/W)", f"{_safe_num('cd_eta_A_per_W'):.3e}"if _safe_num('cd_eta_A_per_W') == _safe_num('cd_eta_A_per_W') else "n/a")
                                        c8.metric("Contract hash", str(out.get("current_profile_contract_sha256", ""))[:12] + ("…"if str(out.get("current_profile_contract_sha256", "")) else ""))

                                        # Signed fractional margins (expandable)
                                        with st.expander("Current-profile authority margins (fractional, signed)", expanded=False):
                                            rows = []
                                            for k, v in sorted(out.items(), key=lambda kv: str(kv[0])):
                                                if str(k).startswith("current_profile_CP_"):
                                                    try:
                                                        rows.append({"check": str(k).replace("current_profile_", ""), "margin_frac": float(v)})
                                                    except Exception:
                                                        rows.append({"check": str(k).replace("current_profile_", ""), "margin_frac": float("nan")})
                                            if rows:
                                                st.dataframe(rows, use_container_width=True, hide_index=True)
                                            else:
                                                st.info("No current-profile margin fields found in this artifact.")
                                    elif _deep_view == "Bootstrap–Pressure Self-Consistency Authority":
                                        cA, cB, cC, cD = st.columns([1.0, 1.0, 1.0, 1.0])
                                        cA.metric("Regime", str(out.get("bsp_regime", "unknown")))
                                        cB.metric("Fragility", str(out.get("bsp_fragility_class", "UNKNOWN")))
                                        mm = _safe_num("bsp_min_margin_frac")
                                        cC.metric("Min margin (frac)", "—"if mm != mm else f"{mm:+.3f}")
                                        cD.metric("Top limiter", str(out.get("bsp_top_limiter", "UNKNOWN")))

                                        c1, c2, c3, c4 = st.columns([1.0, 1.0, 1.0, 1.0])
                                        c1.metric("|Δf_bs|", f"{_safe_num('bsp_abs_delta_f_bootstrap'):.3f}"if _safe_num('bsp_abs_delta_f_bootstrap') == _safe_num('bsp_abs_delta_f_bootstrap') else "n/a")
                                        c2.metric("Tol |Δf_bs|", f"{_safe_num('bsp_abs_delta_max'):.3f}"if _safe_num('bsp_abs_delta_max') == _safe_num('bsp_abs_delta_max') else "n/a")
                                        c3.metric("f_bs (reported)", f"{_safe_num('bsp_f_bootstrap_reported'):.2f}"if _safe_num('bsp_f_bootstrap_reported') == _safe_num('bsp_f_bootstrap_reported') else "n/a")
                                        c4.metric("f_bs (expected)", f"{_safe_num('bsp_f_bootstrap_expected'):.2f}"if _safe_num('bsp_f_bootstrap_expected') == _safe_num('bsp_f_bootstrap_expected') else "n/a")

                                        c5, c6, c7, c8 = st.columns([1.0, 1.0, 1.0, 1.0])
                                        c5.metric("β_p proxy", f"{_safe_num('bsp_beta_p_proxy'):.2f}"if _safe_num('bsp_beta_p_proxy') == _safe_num('bsp_beta_p_proxy') else "n/a")
                                        c6.metric("Model", str(out.get("bsp_model", out.get("bootstrap_model", "-"))))
                                        c7.metric("q95 proxy", f"{_safe_num('q95_proxy'):.2f}"if _safe_num('q95_proxy') == _safe_num('q95_proxy') else "n/a")
                                        sha = str(out.get("bsp_contract_sha256", "") or "")
                                        c8.metric("Contract hash", sha[:12] + ("…"if sha else ""))

                                        with st.expander("Bootstrap–pressure authority details", expanded=False):
                                            st.caption("Deterministic check: |f_bs(reported) − f_bs(expected)| under selected proxy model. No iteration; intended to flag pressure/bootstrap mirages.")
                                            st.json({k: out.get(k) for k in ["bsp_regime","bsp_fragility_class","bsp_min_margin_frac","bsp_top_limiter",'bsp_abs_delta_f_bootstrap','bsp_abs_delta_max','bsp_f_bootstrap_reported','bsp_f_bootstrap_expected',"bsp_delta_f_bootstrap",'bsp_beta_p_proxy',"bsp_model"] if k in out}, expanded=False)
                                    elif _deep_view == "Current Drive Tech Authority":
                                        cA, cB, cC, cD = st.columns([1.0, 1.0, 1.0, 1.0])
                                        cA.metric("CD tech regime", str(out.get("cd_tech_regime", "unknown")))
                                        cB.metric("Fragility", str(out.get("cd_fragility_class", "UNKNOWN")))
                                        mm = _safe_num("cd_min_margin_frac")
                                        cC.metric("Min margin (frac)", f"{mm:.3f}"if mm == mm else "n/a")
                                        cD.metric("Top limiter", str(out.get("cd_top_limiter", "UNKNOWN")))

                                        with st.expander("CD tech margins", expanded=False):
                                            rows = []
                                            for k, v in out.items():
                                                if isinstance(k, str) and k.startswith("cd_") and ("_margin_frac"in k):
                                                    try:
                                                        vv = float(v)
                                                    except Exception:
                                                        vv = float("nan")
                                                    rows.append({"metric": k, "value": vv})
                                            rows = sorted(rows, key=lambda r: (0 if (r["value"]==r["value"]) else 1, r["value"]))
                                            st.table(rows if rows else [{"metric": "(no margins available)", "value": float("nan")}])

                                        sha = str(out.get("cd_contract_sha256", "") or "")
                                        if sha:
                                            st.caption(f"Contract hash (SHA-256): {sha[:16]}…")

                            
                                    elif _deep_view == "Non-Inductive Closure Authority":
                                        cA, cB, cC, cD = st.columns([1.0, 1.0, 1.0, 1.0])
                                        cA.metric("NI regime", str(out.get("ni_closure_regime", "unknown")))
                                        cB.metric("Fragility", str(out.get("ni_fragility_class", "UNKNOWN")))
                                        mm = _safe_num("ni_min_margin_frac")
                                        cC.metric("Min margin (frac)", "—"if mm != mm else f"{mm:+.3f}")
                                        cD.metric("Top limiter", str(out.get("ni_top_limiter", "UNKNOWN")))
                                        # margins table
                                        rows = []
                                        for k, v in out.items():
                                            if isinstance(k, str) and k.startswith("ni_") and k.endswith("_margin_frac"):
                                                vv = float(v) if isinstance(v, (int, float)) else float('nan')
                                                rows.append({"margin_id": k, "margin_frac": vv})
                                        if rows:
                                            import pandas as pd
                                            df = pd.DataFrame(rows).sort_values("margin_frac")
                                            with st.expander("NI closure margins (signed fractional)", expanded=False):
                                                st.dataframe(df, use_container_width=True, hide_index=True)
                                        else:
                                            st.info("No NI closure margin fields found in this artifact.")
                                    elif _deep_view == "Burn & Alpha Power":
                                        cA, cB, cC, cD = st.columns([1.0, 1.0, 1.0, 1.0])
                                        cA.metric("Pα (MW)", f"{_safe_num('Palpha_MW'):.1f}")
                                        cB.metric("Ploss (MW)", f"{_safe_num('Ploss_MW'):.1f}")
                                        cC.metric("M_ign = Pα/Ploss", f"{_safe_num('M_ign'):.2f}"if _safe_num('M_ign') == _safe_num('M_ign') else "n/a")
                                        cD.metric("M_ign_total", f"{_safe_num('M_ign_total'):.2f}"if _safe_num('M_ign_total') == _safe_num('M_ign_total') else "n/a")
                                        st.caption("M_ign_total uses Ploss+Prad_core in the denominator. Constraints can optionally enforce M_ign ≥ ignition_margin_min.")

                                    elif _deep_view == "Impurities & Core Radiation":
                                        cA, cB, cC, cD = st.columns([1.0, 1.0, 1.0, 1.0])
                                        cA.metric("Radiation enabled", "YES"if bool(out.get("include_radiation", False)) else "NO")
                                        cB.metric("Prad_core (MW)", f"{_safe_num('Prad_core_MW'):.1f}")
                                        cC.metric("Zeff (input)", f"{_safe_num('zeff'):.2f}"if _safe_num('zeff') == _safe_num('zeff') else "n/a")
                                        cD.metric("Radiation model", str(out.get("radiation_model", "-")))
                                        st.caption("If using physics/line radiation, the Lz DB id + SHA256 are stamped into the artifact for auditability.")

                                    elif _deep_view == "Edge/Divertor & Exhaust Control":
                                        cA, cB, cC, cD = st.columns([1.0, 1.0, 1.0, 1.0])
                                        cA.metric("q_div (MW/m²)", f"{_safe_num('q_div_MW_m2'):.1f}"if _safe_num('q_div_MW_m2') == _safe_num('q_div_MW_m2') else "n/a")
                                        cB.metric("q_div limit", f"{_safe_num('q_div_max_MW_m2'):.1f}"if _safe_num('q_div_max_MW_m2') == _safe_num('q_div_max_MW_m2') else "n/a")
                                        cC.metric("f_rad_div", f"{_safe_num('f_rad_div'):.2f}"if _safe_num('f_rad_div') == _safe_num('f_rad_div') else "n/a")
                                        cD.metric("Divertor regime", str(out.get("div_regime", "unknown")))
                                        # v329.0: exhaust & radiation regime authority
                                        if str(out.get("exhaust_regime","")):
                                            st.divider()
                                            e1, e2, e3, e4 = st.columns([1.0, 1.0, 1.0, 1.0])
                                            e1.metric("Exhaust regime", str(out.get("exhaust_regime","unknown")))
                                            e2.metric("Fragility", str(out.get("exhaust_fragility_class","UNKNOWN")))
                                            _mr = _safe_num("exhaust_min_margin_frac")
                                            e3.metric("Min margin (frac)", f"{_mr:.3f}"if _mr == _mr else "n/a")
                                            _rad = _safe_num("exhaust_radiation_dominated")
                                            e4.metric("Radiation-dom", "YES"if (_rad == _rad and _rad >= 0.5) else ("NO"if _rad == _rad else "n/a"))
                                            st.caption("Exhaust regime is a deterministic classifier (attached / marginal_detach / detached / radiation_dominated / overheat) based on P_SOL/R overload, q_div margin, and (if enabled) required SOL+div radiation fraction. No solvers, no iteration.")
                                        if bool(getattr(base, "include_sol_radiation_control", False)):
                                            st.divider()
                                            c1, c2, c3, c4 = st.columns([1.0, 1.0, 1.0, 1.0])
                                            c1.metric("q_target", f"{_safe_num('q_div_target_MW_m2'):.1f}"if _safe_num('q_div_target_MW_m2') == _safe_num('q_div_target_MW_m2') else "n/a")
                                            c2.metric("f_SOL+div,req", f"{_safe_num('detachment_f_sol_div_required'):.2f}"if _safe_num('detachment_f_sol_div_required') == _safe_num('detachment_f_sol_div_required') else "n/a")
                                            c3.metric("P_rad,SOL+div req (MW)", f"{_safe_num('detachment_prad_sol_div_required_MW'):.1f}"if _safe_num('detachment_prad_sol_div_required_MW') == _safe_num('detachment_prad_sol_div_required_MW') else "n/a")
                                            c4.metric("f_z,required", f"{_safe_num('detachment_f_z_required'):.1e}"if _safe_num('detachment_f_z_required') == _safe_num('detachment_f_z_required') else "n/a")
                                            st.caption("Detachment authority is diagnostic-only unless you set a max f_z cap. It algebraically inverts q_div target → required SOL+div radiation → implied impurity seeding fraction.")

                                    elif _deep_view == "Neutronics & Nuclear Loads":
                                        cA, cB, cC, cD = st.columns([1.0, 1.0, 1.0, 1.0])
                                        cA.metric("n-wall load (MW/m²)", f"{_safe_num('neutron_wall_load_MW_m2'):.2f}"if _safe_num('neutron_wall_load_MW_m2') == _safe_num('neutron_wall_load_MW_m2') else "n/a")
                                        cB.metric("TBR", f"{_safe_num('TBR'):.2f}"if _safe_num('TBR') == _safe_num('TBR') else "n/a")
                                        cC.metric("HTS lifetime (yr)", f"{_safe_num('hts_lifetime_yr'):.1f}"if _safe_num('hts_lifetime_yr') == _safe_num('hts_lifetime_yr') else "n/a")
                                        cD.metric("FW dpa/y", f"{_safe_num('fw_dpa_per_year'):.2f}"if _safe_num('fw_dpa_per_year') == _safe_num('fw_dpa_per_year') else "n/a")
                                        st.caption(f"**Neutronics/Materials regime:** `{out.get('neutronics_materials_regime', 'unknown')}` | **Fragility:** `{out.get('neutronics_materials_fragility_class', 'UNKNOWN')}` | **Min margin:** {out.get('neutronics_materials_min_margin_frac', float('nan')):.3f} | **Contract:** `{str(out.get('neutronics_materials_contract_sha256', ''))[:10]}`")

                                        # v403.0.0: library-backed stack authority (governance-only)
                                        if bool(out.get("include_neutronics_materials_library_v403", False)):
                                            st.caption(
                                                f"**NM library tier:** `{out.get('nm_regime_tier_v403','UNKNOWN')}` | "
                                                f"**Min margin:** {float(out.get('nm_min_margin_frac_v403', float('nan'))):+.3f} | "
                                                f"**Dominant driver:** `{out.get('nm_dominant_driver_v403','unknown')}` | "
                                                f"**TBR proxy:** {float(out.get('tbr_proxy_v403', float('nan'))):.2f} | "
                                                f"**FW DPA:** {float(out.get('dpa_fw_v403', float('nan'))):.2f} | "
                                                f"**FW He:** {float(out.get('he_appm_fw_v403', float('nan'))):.1f}"
                                            )
                                            with st.expander("Nuclear materials stack ledger (layers, attenuation, contract items)", expanded=False):
                                                st.markdown("**Layers**")
                                                layers = out.get("nm_stack_layers_v403", [])
                                                if isinstance(layers, list) and layers:
                                                    st.dataframe(layers, use_container_width=True, hide_index=True)
                                                else:
                                                    st.info("No stack layers were found in this artifact.")
                                                st.markdown("**Attenuation factors**")
                                                st.json(out.get("nm_attenuation_factor_v403", {}))
                                                st.markdown("**Contract items (margins)**")
                                                rows = out.get("nm_contract_items_v403", [])
                                                if isinstance(rows, list) and rows:
                                                    st.dataframe(rows, use_container_width=True, hide_index=True)
                                                sha403 = str(out.get("nm_contract_sha256_v403", "") or "")
                                                if sha403:
                                                    st.caption(f"Contract hash (SHA-256): {sha403[:16]}…")



                                        # v407.0.0: nuclear data provenance + multi-group attenuation (screening-only)
                                        if bool(out.get("include_nuclear_data_authority_v407", False)):
                                            dsid = str(out.get("nuclear_dataset_id_v407", ""))
                                            dsha = str(out.get("nuclear_dataset_sha256_v407", ""))
                                            tf_flu = float(out.get("tf_case_fluence_n_m2_per_fpy_v407", float('nan')))
                                            tbrmg = float(out.get("tbr_mg_proxy_v407", float('nan')))
                                            st.caption(
                                                f"**Nuclear data:** dataset `{dsid}` | hash `{dsha[:12]}…` | "
                                                f"TF-case fluence {tf_flu:.3e} n/m²/FPY | TBR(mg proxy) {tbrmg:.2f}"
                                            )
                                            with st.expander("Multi-group nuclear ledger (edges, spectrum, attenuation, fluence)", expanded=False):
                                                st.markdown("**Group edges (MeV)**")
                                                st.write(out.get("group_edges_MeV_v407", []))
                                                st.markdown("**FW spectrum fractions (normalized)**")
                                                st.write(out.get("spectrum_frac_fw_v407", []))
                                                st.markdown("**Attenuation per group to TF-case**")
                                                st.write(out.get("attenuation_g_to_tf_v407", []))
                                                st.markdown("**Fluence per group to TF-case (n/m²/FPY)**")
                                                st.write(out.get("fluence_g_to_tf_n_m2_per_fpy_v407", []))
                                                st.markdown("**Layer ledger**")
                                                rows = out.get("nuclear_data_authority_ledger_v407", [])
                                                if isinstance(rows, list) and rows:
                                                    st.dataframe(rows, use_container_width=True, hide_index=True)
                                        # v401.0.0: contract-tier overlay (governance-only)
                                        if bool(out.get("include_neutronics_materials_authority_v401", False)):
                                            st.caption(
                                                f"**NM contract tier:** `{out.get('nm_contract_tier_v401','NOMINAL')}` | "
                                                f"**Fragility:** `{out.get('nm_fragility_class_v401','UNKNOWN')}` | "
                                                f"**Min margin:** {float(out.get('nm_min_margin_frac_v401', float('nan'))):+.3f} | "
                                                f"**Dominant driver:** `{out.get('nm_dominant_driver_v401','unknown')}`"
                                            )
                                            with st.expander("Neutronics contract items (margins)", expanded=False):
                                                rows = out.get("nm_contract_items_v401", [])
                                                if isinstance(rows, list) and rows:
                                                    st.dataframe(rows, use_container_width=True, hide_index=True)
                                                else:
                                                    st.info("Neutronics contract tiers enabled but no contract items were found in this artifact.")
                                            sha401 = str(out.get("nm_contract_sha256_v401", "") or "")
                                            if sha401:
                                                st.caption(f"Contract hash (SHA-256): {sha401[:16]}…")
                                        st.divider()
                                        d1, d2, d3, d4 = st.columns([1.0, 1.0, 1.0, 1.0])
                                        d1.metric("Stack attenuation", f"{_safe_num('neutron_attenuation_factor'):.3g}"if _safe_num('neutron_attenuation_factor') == _safe_num('neutron_attenuation_factor') else "n/a")
                                        # v309.0: expose fast/gamma split when available
                                        _af = _safe_num('neutron_attenuation_fast')
                                        _ag = _safe_num('neutron_attenuation_gamma')
                                        if _af == _af or _ag == _ag:
                                            st.caption(f"Attenuation (fast, gamma): {(_af if _af==_af else float('nan')):.3g} / {(_ag if _ag==_ag else float('nan')):.3g}")
                                        d2.metric("P_nuc,total (MW)", f"{_safe_num('P_nuc_total_MW'):.2f}"if _safe_num('P_nuc_total_MW') == _safe_num('P_nuc_total_MW') else "n/a")
                                        d3.metric("P_nuc,TF (MW)", f"{_safe_num('P_nuc_TF_MW'):.2f}"if _safe_num('P_nuc_TF_MW') == _safe_num('P_nuc_TF_MW') else "n/a")
                                        d4.metric("FW life (yr)", f"{_safe_num('fw_lifetime_yr'):.1f}"if _safe_num('fw_lifetime_yr') == _safe_num('fw_lifetime_yr') else "n/a")

                                        e1, e2, e3, e4 = st.columns([1.0, 1.0, 1.0, 1.0])
                                        e1.metric("Blanket life (yr)", f"{_safe_num('blanket_lifetime_yr'):.1f}"if _safe_num('blanket_lifetime_yr') == _safe_num('blanket_lifetime_yr') else "n/a")
                                        e2.metric("FW He/y (appm)", f"{_safe_num('fw_He_appm_per_year'):.0f}"if _safe_num('fw_He_appm_per_year') == _safe_num('fw_He_appm_per_year') else "n/a")
                                        e3.metric("FW T margin (°C)", f"{_safe_num('fw_T_margin_C'):.0f}"if _safe_num('fw_T_margin_C') == _safe_num('fw_T_margin_C') else "n/a")
                                        e4.metric("FW σ margin (MPa)", f"{_safe_num('fw_sigma_margin_MPa'):.0f}"if _safe_num('fw_sigma_margin_MPa') == _safe_num('fw_sigma_margin_MPa') else "n/a")

                                        f1, f2, f3, f4 = st.columns([1.0, 1.0, 1.0, 1.0])
                                        f1.metric("FW material", str(out.get("fw_material", "-")))
                                        f2.metric("Blanket material", str(out.get("blanket_material", "-")))
                                        f3.metric("Shield material", str(out.get("shield_material", "-")))
                                        f4.metric("TBR validity", "OK"if float(out.get("TBR_validity", 0.0)) < 0.5 else "out-of-range")

                                        st.caption("Neutronics/materials: all quantities are deterministic proxies. Fast/gamma attenuation and nuclear heating partitioning are parametric; DPA/He + temperature/stress checks are screening models. Constraints are enforced only when corresponding caps/flags are set.")

                                        # Materials lifetime closure (replacement cadence + cost-rate)
                                        if ("materials_lifetime_schema_version"in out) or ("fw_replace_interval_y_v367"in out) or ("replacement_cost_MUSD_per_year_v367_total"in out):
                                            st.divider()
                                            m1, m2, m3, m4 = st.columns([1.0, 1.0, 1.0, 1.0])
                                            m1.metric("Plant life (yr)", f"{_safe_num('plant_design_lifetime_yr'):.0f}"if _safe_num('plant_design_lifetime_yr') == _safe_num('plant_design_lifetime_yr') else "n/a")
                                            m2.metric("FW repl (count)", f"{int(_safe_num('fw_replacements_over_plant_life'))}"if _safe_num('fw_replacements_over_plant_life') == _safe_num('fw_replacements_over_plant_life') else "n/a")
                                            m3.metric("Blanket repl (count)", f"{int(_safe_num('blanket_replacements_over_plant_life'))}"if _safe_num('blanket_replacements_over_plant_life') == _safe_num('blanket_replacements_over_plant_life') else "n/a")
                                            m4.metric("Repl cost rate (MUSD/y)", f"{_safe_num('replacement_cost_MUSD_per_year_v367_total'):.2f}"if _safe_num('replacement_cost_MUSD_per_year_v367_total') == _safe_num('replacement_cost_MUSD_per_year_v367_total') else "n/a")

                                            n1, n2, n3, n4 = st.columns([1.0, 1.0, 1.0, 1.0])
                                            n1.metric("FW cadence (yr)", f"{_safe_num('fw_replace_interval_y_v367'):.2f}"if _safe_num('fw_replace_interval_y_v367') == _safe_num('fw_replace_interval_y_v367') else "n/a")
                                            n2.metric("Blanket cadence (yr)", f"{_safe_num('blanket_replace_interval_y_v367'):.2f}"if _safe_num('blanket_replace_interval_y_v367') == _safe_num('blanket_replace_interval_y_v367') else "n/a")
                                            n3.metric("FW cost (MUSD/y)", f"{_safe_num('fw_replacement_cost_MUSD_per_year'):.2f}"if _safe_num('fw_replacement_cost_MUSD_per_year') == _safe_num('fw_replacement_cost_MUSD_per_year') else "n/a")
                                            n4.metric("Blanket cost (MUSD/y)", f"{_safe_num('blanket_replacement_cost_MUSD_per_year'):.2f}"if _safe_num('blanket_replacement_cost_MUSD_per_year') == _safe_num('blanket_replacement_cost_MUSD_per_year') else "n/a")

                                            sha = str(out.get("materials_lifetime_contract_sha256", "") or "")
                                            if sha:
                                                st.caption(f"Materials lifetime contract hash (SHA-256): {sha[:16]}…")

                        

                                    elif _deep_view == "Coupling Narratives":
                                        st.caption("Deterministic coupling narratives derived from authority dominance + regime labels. No solvers, no iteration.")
                                        csum = str(out.get("coupling_summary", "") or "")
                                        if csum:
                                            st.info(csum)
                                        sev = out.get("coupling_severity_max", 0)
                                        try:
                                            sev_i = int(sev)
                                        except Exception:
                                            sev_i = 0
                                        st.metric("Max severity", f"{sev_i}/5")

                                        cn = out.get("coupling_narratives", {})
                                        items = []
                                        if isinstance(cn, dict):
                                            items = cn.get("coupling_narratives", []) or []
                                        if not items:
                                            st.caption("No coupling flags triggered for this evaluation.")
                                        else:
                                            for i, it in enumerate(items):
                                                if not isinstance(it, dict):
                                                    continue
                                                code = str(it.get("code", ""))
                                                title = str(it.get("title", "Coupling narrative"))
                                                sev = it.get("severity", "")
                                                header = f"{title} [{code}] (sev={sev})"
                                                with st.expander(header, expanded=False):
                                                    st.write(str(it.get("narrative", "")))


                                # --- Authority & validity contracts (verdict-first)
                                with st.expander("Authority & Validity - Contracts", expanded=False):
                                    try:
                                        from provenance.authority import authority_snapshot_from_outputs
                                        snap = authority_snapshot_from_outputs(out if isinstance(out, dict) else {})
                                        subs = (snap.get("subsystems", {}) or {})
                                        rows = []
                                        n_proxy = 0
                                        for k, v in subs.items():
                                            tier = str((v or {}).get("tier", ""))
                                            if tier.strip().lower() == "proxy":
                                                n_proxy += 1
                                            rows.append({
                                                "subsystem": str(k),
                                                "tier": tier,
                                                "validity": str((v or {}).get("validity_domain", "")),
                                            })
                                        if rows:
                                            _df = pd.DataFrame(rows)
                                            st.dataframe(_df, use_container_width=True, height=320, hide_index=True)
                                        if n_proxy > 0:
                                            st.warning(f"{n_proxy} subsystems are currently tagged as PROXY for this run. See table for details.")
                                        else:
                                            st.success("No subsystems flagged as pure PROXY in this run (some may still be semi-authoritative).")
                                        st.caption("Contracts are declarative metadata; they do not change physics.")
                                    except Exception as e:
                                        st.caption(f"Authority contracts unavailable: {e}")

                                # --- Fuel cycle / lifetime / availability realism
                                with st.expander("Fuel Cycle · Lifetime · Availability", expanded=False):
                                    def _m(k: str, fmt: str = "{:.3g}", suffix: str = ""):
                                        try:
                                            v = float(out.get(k, float('nan')))
                                        except Exception:
                                            v = float('nan')
                                        return (fmt.format(v) + suffix) if (v == v) else "n/a"

                                    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                                    c1.metric("T burn (g/day)", _m("T_burn_g_per_day", "{:.2f}"))
                                    c2.metric("T inventory proxy (g)", _m("T_inventory_proxy_g", "{:.2f}"))
                                    c3.metric("TBR", _m("TBR", "{:.2f}"))
                                    c4.metric("FW dpa/y", _m("fw_dpa_per_year", "{:.2f}"))

                                    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                                    c1.metric("Availability", _m("availability_model", "{:.2f}"))
                                    c2.metric("Annual net (MWh/y)", _m("annual_net_MWh", "{:.3g}"))
                                    c3.metric("FW interval (y)", _m("fw_replace_interval_y", "{:.2f}"))
                                    c4.metric("DIV interval (y)", _m("div_replace_interval_y", "{:.2f}"))

                                    # Availability & replacement ledger overlay (optional)
                                    try:
                                        _av359 = float(out.get("availability_v359", float('nan')))
                                    except Exception:
                                        _av359 = float('nan')
                                    if _av359 == _av359:
                                        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                                        c1.metric("Availability", _m("availability_v359", "{:.2f}"))
                                        c2.metric("Net MWh/y", _m("net_electric_MWh_per_year_v359", "{:.3g}"))
                                        c3.metric("LCOE (USD/MWh)", _m("LCOE_proxy_v359_USD_per_MWh", "{:.2f}"))
                                        c4.metric("Repl. cost (MUSD/y)", _m("replacement_cost_MUSD_per_year_v359", "{:.2f}"))
                                        st.caption("Component replacement ledger uses planned_outage_base + forced_outage_base + replacement downtime; it does not modify truth or legacy economics outputs.")

                                    # Maintenance scheduling authority quicklook (optional)
                                    try:
                                        _av368 = float(out.get("availability_v368", float('nan')))
                                    except Exception:
                                        _av368 = float('nan')
                                    if _av368 == _av368:
                                        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                                        c1.metric("Availability", _m("availability_v368", "{:.2f}"))
                                        c2.metric("Outage total", _m("outage_total_frac_v368", "{:.2f}"))
                                        c3.metric("Net MWh/y", _m("net_electric_MWh_per_year_v368", "{:.3g}"))
                                        c4.metric("Repl. cost (MUSD/y)", _m("replacement_cost_MUSD_per_year_v368", "{:.2f}"))
                                        st.caption("Maintenance scheduling adds a deterministic maintenance event ledger and schedule-dominated availability; no time simulation.")

                                    # Availability 2.0 — Reliability envelope (optional)
                                    try:
                                        _av391 = float(out.get("availability_cert_v391", float('nan')))
                                    except Exception:
                                        _av391 = float('nan')
                                    if _av391 == _av391:
                                        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                                        c1.metric("Availability", _m("availability_cert_v391", "{:.3f}"))
                                        c2.metric("Planned", _m("planned_outage_frac_v391", "{:.3f}"))
                                        c3.metric("Maint", _m("maint_downtime_frac_v391", "{:.3f}"))
                                        c4.metric("Unplanned", _m("unplanned_downtime_frac_v391", "{:.3f}"))
                                        drv = str(out.get("availability_driver_v391", ""))
                                        reg = str(out.get("availability_regime_v391", ""))
                                        if drv or reg:
                                            st.caption(f"Availability driver={drv or 'n/a'}; regime={reg or 'n/a'}. Uses MTBF/MTTR product proxy + planned outage + maintenance burden from scheduling, replacement, and activation overlays.")
                                        led = out.get("availability_ledger_v391")
                                        with st.expander("Availability reliability ledger", expanded=False):
                                            try:
                                                if isinstance(led, list) and led:
                                                    import pandas as _pd
                                                    _df = _pd.DataFrame(led)
                                                    st.dataframe(_df, use_container_width=True, height=320, hide_index=True)
                                                else:
                                                    st.info("No availability ledger found — enable the availability & reliability envelope and re-run.")
                                            except Exception as e:
                                                st.caption(f"Ledger render failed: {e}")


                                    lims = []
                                    for k in ["tritium_inventory_max_g", "fw_dpa_max_per_year", "availability_min", "annual_net_MWh_min"]:
                                        try:
                                            v = float(out.get(k, float('nan')))
                                        except Exception:
                                            v = float('nan')
                                        if v == v:
                                            lims.append(f"{k}={v:.3g}")
                                    if lims:
                                        st.caption("Active caps/requirements: "+ "; ".join(lims))
                                    else:
                                        st.caption("No explicit caps/requirements set for fuel-cycle/lifetime/annual-energy in this run.")

                                # --- Inboard build & coil stress/Jmargin quicklook
                                with st.expander("Build · Coils · Stress · Margin", expanded=False):
                                    def _m2(k: str, fmt: str = "{:.3g}"):
                                        try:
                                            v = float(out.get(k, float('nan')))
                                        except Exception:
                                            v = float('nan')
                                        return fmt.format(v) if (v == v) else "n/a"

                                    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                                    c1.metric("Inboard margin (m)", _m2("inboard_margin_m", "{:.3f}"))
                                    c2.metric("R_coil_inner (m)", _m2("R_coil_inner_m", "{:.3f}"))
                                    c3.metric("B_peak (T)", _m2("B_peak_T", "{:.2f}"))
                                    c4.metric("σ_vm (MPa)", _m2("sigma_vm_MPa", "{:.0f}"))

                                    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                                    c1.metric("HTS margin", _m2("hts_margin", "{:.2f}"))
                                    c2.metric("TF Jop (MA/mm²)", _m2("tf_Jop_MA_per_mm2", "{:.3f}"))
                                    c3.metric("TF strain", _m2("tf_strain", "{:.4f}"))
                                    c4.metric("Cryo power (MW)", _m2("cryo_power_MW", "{:.2f}"))

                                    enforce = out.get("enforce_radial_build", 0.0)
                                    if float(enforce) >= 0.5:
                                        st.info("Radial-build closure enforcement is ON (inboard_margin_m ≥ 0 is a hard constraint).")
                                    else:
                                        st.caption("Radial-build closure enforcement is OFF by default; enable in inputs if desired.")

                                # --- Feasibility Forensics (deterministic, local)
                                with st.expander("Feasibility Forensics - Local Sensitivity", expanded=False):
                                    st.caption(
                                        "Deterministic finite-difference sensitivities of constraint signed margins. "
                                        "This is *diagnostic only* (no optimization, no truth mutation)."
                                    )
                                    _intent = str(st.session_state.get("design_intent", ""))
                                    if st.button("Compute forensics", key="pd_forensics_btn", use_container_width=True):
                                        try:
                                            from src.analysis.forensics import local_sensitivity
                                            ff = local_sensitivity(base, design_intent=_intent)
                                            st.session_state["pd_last_forensics"] = ff
                                            st.session_state["pd_last_forensics_inputs_hash"] = st.session_state.get("pd_current_inputs_hash")
                                        except Exception as e:
                                            st.session_state["pd_last_forensics"] = {"status": "error", "message": str(e)}
                                            st.session_state["pd_last_forensics_inputs_hash"] = st.session_state.get("pd_current_inputs_hash")
                                    ff = st.session_state.get("pd_last_forensics")
                                    if isinstance(ff, dict) and ff:
                                        if ff.get("status") == "error":
                                            st.error(ff.get("message", "forensics error"))
                                        else:
                                            # --- Summary strip (verdict-first, compact)
                                            b = ff.get("base", {}) or {}
                                            dom = str(b.get("top_dominant", ""))
                                            frag = b.get("fragility_fraction", float("nan"))
                                            stab = str(b.get("stability_label", "unknown"))

                                            c1, c2, c3, c4 = st.columns([1.3, 0.9, 0.9, 0.9])
                                            c1.metric("Dominant blocker", dom if dom else "(none)")
                                            c2.metric("Stability", stab)
                                            c3.metric(
                                                "Fragility",
                                                f"{float(frag):.2f}"if frag == frag else "n/a",
                                                help="Fraction of ±1-step perturbations that change the dominant blocker. <=0.20 stable; >0.20 fragile.",
                                            )

                                            # Lever-confidence badge (deterministic; derived from fragility + slope consistency)
                                            lc = ff.get("lever_confidence", {}) or {}
                                            lc_score = lc.get("score", float("nan"))
                                            lc_label = str(lc.get("label", "unknown"))
                                            c4.metric(
                                                "Lever confidence",
                                                f"{lc_label}"if lc_label else "unknown",
                                                help="Heuristic quality indicator for the lever recipe: combines dominant-switch fragility with one-sided derivative consistency. 0..1 score stored in artifact.",
                                            )
                                            # --- Deterministic explanation (derived from computed sensitivities)
                                            notes = ff.get("notes", []) or []
                                            if notes:
                                                st.markdown("**Why this point is (un)stable**")
                                                for n in notes[:6]:
                                                    st.write(f"• {n}")

                                            # --- Tornado-style ranked table (no plots; expert-candy table)
                                            tornado = ff.get("tornado", {}) or {}
                                            focus = ff.get("focus_constraints", []) or []
                                            if tornado and focus:
                                                pick = st.selectbox(
                                                    "Constraint to inspect",
                                                    options=list(focus),
                                                    index=0,
                                                    key="pd_forensics_constraint_pick",
                                                )
                                                rows = list(tornado.get(pick, []) or [])
                                                if rows:
                                                    # Add a direction hint column: +dx increases margin? sign of dmargin/dx
                                                    for r in rows:
                                                        sgn = str(r.get("sign", "0"))
                                                        r["+dx effect"] = "margin ↑"if sgn == "+"else ("margin ↓"if sgn == "-"else "flat")
                                                    st.dataframe(
                                                        rows,
                                                        use_container_width=True,
                                                        hide_index=True,
                                                        column_config={
                                                            "knob": st.column_config.TextColumn("Knob"),
                                                            "dmargin_per_unit": st.column_config.NumberColumn("∂margin/∂x", format="%.4g"),
                                                            "step": st.column_config.NumberColumn("Δx (probe)", format="%.4g"),
                                                            "impact_abs": st.column_config.NumberColumn("|Δmargin| @ Δx", format="%.4g"),
                                                            "+dx effect": st.column_config.TextColumn("Local lever"),
                                                        },
                                                    )
                                                    st.caption(
                                                        "Table is sorted by |Δmargin| at the deterministic probe step Δx. "
                                                        "Use the sign (+/-) to see whether increasing the knob locally increases or decreases the margin."
                                                    )

                                            # --- Lever recipe (local-linear, no optimization)
                                            # Translate the dominant constraint's local sensitivities into directional levers.
                                            # This is intentionally conservative: read-only, no auto-application to inputs.
                                            try:
                                                dom_adv = ff.get("dominant_advice", {}) or {}
                                                dom_c = str(dom_adv.get("dominant_constraint", ""))
                                                if dom_c and isinstance(tornado, dict) and tornado.get(dom_c):
                                                    st.markdown("**Lever recipe (local-linear) - for the dominant blocker only**")
                                                    st.caption(
                                                        "Directional suggestions are derived from the local linearization at the deterministic probe step Δx. "
                                                        "They are *not* an optimizer and may not hold far from this point."
                                                    )

                                                    dom_rows = list(tornado.get(dom_c, []) or [])
                                                    help_rows = [r for r in dom_rows if float(r.get("dmargin_per_unit", 0.0)) > 0]
                                                    hurt_rows = [r for r in dom_rows if float(r.get("dmargin_per_unit", 0.0)) < 0]

                                                    # Build two compact tables: actions that increase margin (increase knob if dmdx>0; decrease knob if dmdx<0)
                                                    def _mk_actions(rows, *, action_when_positive: str) -> list:
                                                        out_rows = []
                                                        for r in rows[:5]:
                                                            dmdx = float(r.get("dmargin_per_unit", float("nan")))
                                                            dx = float(r.get("step", float("nan")))
                                                            if not (dmdx == dmdx and dx == dx):
                                                                continue
                                                            delta = dmdx * dx
                                                            out_rows.append(
                                                                {
                                                                    "knob": str(r.get("knob", "")),
                                                                    "action": action_when_positive,
                                                                    "Δx": dx,
                                                                    "Δmargin @ Δx": delta,
                                                                    "|Δmargin|": abs(delta),
                                                                }
                                                            )
                                                        out_rows.sort(key=lambda rr: (float("inf") if (rr["|Δmargin|"] != rr["|Δmargin|"]) else -rr["|Δmargin|"]))
                                                        return out_rows

                                                    actions_help = _mk_actions(help_rows, action_when_positive="increase")
                                                    actions_hurt = []
                                                    # For hurting knobs, the helpful direction is to decrease the knob by Δx.
                                                    for r in hurt_rows[:5]:
                                                        dmdx = float(r.get("dmargin_per_unit", float("nan")))
                                                        dx = float(r.get("step", float("nan")))
                                                        if not (dmdx == dmdx and dx == dx):
                                                            continue
                                                        delta_if_decrease = (-dmdx) * dx  # decreasing knob increases margin when dmdx<0
                                                        actions_hurt.append(
                                                            {
                                                                "knob": str(r.get("knob", "")),
                                                                "action": "decrease",
                                                                "Δx": dx,
                                                                "Δmargin @ Δx": delta_if_decrease,
                                                                "|Δmargin|": abs(delta_if_decrease),
                                                            }
                                                        )
                                                    actions_hurt.sort(key=lambda rr: (float("inf") if (rr["|Δmargin|"] != rr["|Δmargin|"]) else -rr["|Δmargin|"]))

                                                    cA, cB = st.columns([1, 1])
                                                    with cA:
                                                        st.markdown("**Increase-margin levers**")
                                                        if actions_help:
                                                            st.dataframe(
                                                                actions_help,
                                                                use_container_width=True,
                                                                hide_index=True,
                                                                column_config={
                                                                    "knob": st.column_config.TextColumn("Knob"),
                                                                    "action": st.column_config.TextColumn("Direction"),
                                                                    "Δx": st.column_config.NumberColumn("Δx", format="%.4g"),
                                                                    "Δmargin @ Δx": st.column_config.NumberColumn("Δmargin", format="%.4g"),
                                                                    "|Δmargin|": st.column_config.NumberColumn("|Δmargin|", format="%.4g"),
                                                                },
                                                            )
                                                        else:
                                                            st.info("No positive-slope levers found for this dominant blocker at the current probe set.")
                                                    with cB:
                                                        st.markdown("**Avoid/regression levers**")
                                                        st.caption("These knobs locally *decrease* the dominant margin when increased; decreasing them helps.")
                                                        if actions_hurt:
                                                            st.dataframe(
                                                                actions_hurt,
                                                                use_container_width=True,
                                                                hide_index=True,
                                                                column_config={
                                                                    "knob": st.column_config.TextColumn("Knob"),
                                                                    "action": st.column_config.TextColumn("Direction"),
                                                                    "Δx": st.column_config.NumberColumn("Δx", format="%.4g"),
                                                                    "Δmargin @ Δx": st.column_config.NumberColumn("Δmargin", format="%.4g"),
                                                                    "|Δmargin|": st.column_config.NumberColumn("|Δmargin|", format="%.4g"),
                                                                },
                                                            )
                                                        else:
                                                            st.info("No negative-slope (regression) levers found for this dominant blocker at the current probe set.")
                                            except Exception:
                                                # Forensics UI must never crash the Point Designer.
                                                pass

                                            # --- Optional raw dump (for audit)
                                            if st.toggle("Show raw forensics JSON", value=False, key="pd_forensics_raw_toggle"):
                                                st.json(ff)

                                st.divider()

                                # --- Capability badge (compact, non-expanding strip) ---
                                # Read-only, reviewer-friendly summary of which physics blocks are actually active.
                                try:
                                    _prof_model = str(out.get("profile_model", "none"))
                                    _prof_on = bool(out.get("profile_mode", False))
                                    _bs = str(out.get("bootstrap_model", "proxy"))
                                    _rad_on = bool(out.get("include_radiation", False))
                                    _rad_model = str(out.get("radiation_model", "off"))
                                    _rad_db_used = str(out.get("radiation_db_id_used", out.get("radiation_db", "")))
                                    _mag_tech = str(out.get("magnet_technology", "unknown"))
                                    _plant_on = bool(np.isfinite(float(out.get("P_net_e_MW", float("nan")))))

                                    _badge = (
                                        f"**Capability badge** - "
                                        f"Profiles: **{_prof_model}** ({'ON' if _prof_on else 'OFF'}) · "
                                        f"Bootstrap: **{_bs}** · "
                                        f"Radiation: **{'ON' if _rad_on else 'OFF'}**"
                                    )
                                    if _rad_on:
                                        _badge += f"({_rad_model}{' · '+_rad_db_used if _rad_db_used else ''})"
                                    _badge += f"· Magnets: **{_mag_tech}** · Plant closure: **{'ON' if _plant_on else 'OFF'}**"
                                    st.caption(_badge + " ")
                                    st.caption("See: More → Assumptions Ledger → Physics Capability Matrix.")
                                except Exception:
                                    pass

                                # --- Magnet Card (compact, reviewer-safe) ---
                                tech = str(out.get("magnet_technology", "unknown"))
                                tf_sc = float(out.get("tf_sc_flag", float("nan")))
                                sc_margin = out.get("sc_margin", out.get("hts_margin", float("nan")))
                                p_tf_ohm = out.get("P_tf_ohmic_MW", float("nan"))

                                # Policy note: whether TF_SC is treated as blocking/diagnostic under the active intent
                                try:
                                    _policy = out.get("constraint_policy", {}) or {}
                                    _hb = set(_policy.get("hard_blocking", []) or [])
                                    _diag = set(_policy.get("diagnostic_only", []) or [])
                                    if "TF_SC"in _hb:
                                        tf_note = "Blocking (reactor covenant)"
                                    elif "TF_SC"in _diag:
                                        tf_note = "Diagnostic (research)"
                                    else:
                                        tf_note = "(not used)"
                                except Exception:
                                    tf_note = ""

                                # Render as a small, no-scroll card
                                st.markdown("#### Magnet Card")
                                c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                                c1.metric("TF technology", tech)
                                c2.metric("TF superconducting", "YES"if (tf_sc == 1.0) else ("NO"if (tf_sc == 0.0) else "n/a"))
                                if tf_sc == 1.0:
                                    c3.metric("SC margin", f"{float(sc_margin):.3f}"if sc_margin == sc_margin else "n/a")
                                    c4.metric("Tcoil [K]", f"{float(out.get('Tcoil_K', float('nan'))):.1f}"if out.get('Tcoil_K', float('nan')) == out.get('Tcoil_K', float('nan')) else "n/a")
                                else:
                                    c3.metric("TF ohmic [MW]", f"{float(p_tf_ohm):.2f}"if p_tf_ohm == p_tf_ohm else "n/a")
                                    c4.metric("Tcoil [K]", f"{float(out.get('Tcoil_K', float('nan'))):.1f}"if out.get('Tcoil_K', float('nan')) == out.get('Tcoil_K', float('nan')) else "n/a")
                                if tf_note:
                                    st.caption(f"TF_SC policy: {tf_note}")

                        
                                # --- Model activation note (prevents 'I changed a model but nothing changed' confusion) ---
                                bs_mode = str(out.get("bootstrap_model", "proxy"))
                                prof_model = str(out.get("profile_model", "none"))
                                prof_on = bool(out.get("profile_mode", False))
                                rad_on = bool(out.get("include_radiation", False))
                                rad_mode = str(out.get("radiation_model", "off"))
                                rad_db = str(out.get("radiation_db_id_used", out.get("radiation_db", "")))

                                notes = []
                                notes.append(f"Bootstrap: **{bs_mode}**")
                                notes.append(f"Profiles: **{prof_model}** ({'ON' if prof_on else 'OFF'})")
                                notes.append(f"Radiation: **{'ON' if rad_on else 'OFF'}**"+ (f"({rad_mode}{' · '+rad_db if rad_on and rad_db else ''})"if rad_on else ""))

                                # Sauter proxy becomes profile-sensitive; if profiles are OFF, changes may be minimal.
                                if bs_mode.lower() in {"sauter", "sauter_proxy"} and not prof_on:
                                    st.caption("Model activation: Sauter bootstrap is enabled, but analytic profiles are OFF - the result reduces to a bounded global proxy, so the operating point may not change materially.")
                                if rad_on and (rad_db in {"builtin_proxy", "", "proxy_v1"}):
                                    st.caption("Radiation provenance: using built-in proxy Lz tables. For authoritative radiation, provide a RADAS/OpenADAS-derived database (see 'Radiation DB' model card).")

                                st.caption("· ".join(notes))

                                st.divider()
                                # Keep legacy KPI row, but make it tech-aware (avoid misleading 'HTS' wording)
                                m_lbl = "SC margin"if tf_sc == 1.0 else "TF ohmic [MW]"
                                m_val = (f"{float(sc_margin):.3f}"if (tf_sc == 1.0 and sc_margin == sc_margin) else (f"{float(p_tf_ohm):.2f}"if p_tf_ohm == p_tf_ohm else "n/a"))
                                kpi_row([
                                    (m_lbl, m_val),
                                    ("Lifetime [yr]", f"{out.get('hts_lifetime_yr', float('nan')):.2f}"),
                                    ("Vdump [kV]", f"{out.get('V_dump_kV', float('nan')):.1f}"),
                                    ("P_net_e [MW]", f"{out.get('P_net_e_MW', float('nan')):.1f}"),
                                ])
    
                        # -----------------------------------------------------------------
                        # Expert transparency: assumptions, power ledger, sanity dashboard
                        # -----------------------------------------------------------------
                        def _pd_assumptions_snapshot() -> Dict[str, Any]:
                            """UI-level model/assumption snapshot for expert auditability (does not affect physics)."""
                            try:
                                return {
                                    "design_intent": str(st.session_state.get("design_intent", "Power Reactor (net-electric)")),
                                    "confinement_scaling_ref": str(confinement_scaling),
                                    "profile_model": str(profile_model),
                                    "profile_peaking_ne": float(profile_peaking_ne),
                                    "profile_peaking_T": float(profile_peaking_T),
                                    "bootstrap_model": str(bootstrap_model),
                                    "include_radiation": bool(include_radiation),
                                    "radiation_model": str(radiation_model) if include_radiation else "disabled",
                                    "radiation_db": str(radiation_db) if include_radiation else "proxy_v1",
                                    "include_synchrotron": bool(include_synchrotron) if include_radiation else False,
                                    "Zeff_mode": str(zeff_mode) if include_radiation else "disabled",
                                    "Zeff": float(Zeff) if include_radiation else float("nan"),
                                    "dilution_fuel": float(dilution_fuel) if include_radiation else float("nan"),
                                    "f_rad_core": float(f_rad_core) if include_radiation else float("nan"),
                                    "impurity_species": str(impurity_species) if include_radiation else "disabled",
                                    "impurity_frac": float(impurity_frac) if include_radiation else float("nan"),
                                    "include_alpha_loss": bool(include_alpha_loss),
                                    "alpha_loss_model": str(alpha_loss_model) if include_alpha_loss else "disabled",
                                    "include_hmode_physics": bool(include_hmode_physics),
                                    "require_Hmode": bool(require_Hmode) if include_hmode_physics else False,
                                    "PLH_margin": float(PLH_margin) if include_hmode_physics else float("nan"),
                                    "use_lambda_q": bool(use_lambda_q),
                                    "particle_balance_enabled": bool(include_particle_balance) if 'include_particle_balance' in locals() else False,
                                    "ash_dilution_mode": str(ash_dilution_mode) if 'ash_dilution_mode' in locals() else "default",
                                    "fuel_mode": str(fuel_mode),
                                }
                            except Exception:
                                return {"design_intent": str(st.session_state.get("design_intent", "Power Reactor (net-electric)"))}

                        if _pd_tel_view == "Mission Snapshot":
                            with st.expander("Model Scope & Assumptions", expanded=False):
                                st.caption("Integrated view of what is *authoritative* vs *proxy* in this 0‑D point. Nothing here changes physics; it documents it.")
                                st.markdown("""**Badges:**  
        - **Authoritative** = used directly in feasibility/constraints  
        - **Proxy** = approximate model (informative unless explicitly constrained)  
        - **Diagnostic** = non‑blocking checks and tags""")

                                # User-request: keep these collapsed by default.
                                st.markdown("**Assumptions snapshot (UI-level):**")
                                st.json(_pd_assumptions_snapshot(), expanded=False)

                                try:
                                    mc = out.get("model_cards", {})
                                    if isinstance(mc, dict) and mc:
                                        st.markdown("**Model cards (provenance):**")
                                        st.json(mc, expanded=False)
                                except Exception:
                                    pass

                        if _pd_tel_view == "Ledgers":
                            with st.expander("Power Ledger - Closure Table", expanded=False):
                                st.caption("Transparent Pin/Pout bookkeeping at this point (0‑D proxies).")
                                try:
                                    rows = []
                                    def _add(lbl, key, badge):
                                        val = out.get(key, float("nan"))
                                        rows.append({"Item": lbl, "Key": key, "MW": val, "Type": badge})
                                    _add("Input power Pin", "Pin_MW", "Authoritative")
                                    _add("Aux heating", "Paux_MW", "Authoritative")
                                    _add("Ohmic", "Pohm_MW", "Proxy")
                                    _add("Fusion alpha (generated)", "Palpha_MW", "Authoritative")
                                    _add("Core radiation", "Prad_core_MW", "Proxy"if bool(include_radiation) else "Diagnostic")
                                    _add("SOL/Separatrix power", "P_SOL_MW", "Authoritative")
                                    _add("Total loss Ploss", "Ploss_MW", "Authoritative")
                                    _add("Net electric", "P_net_e_MW", "Proxy")
                                    dfp = pd.DataFrame(rows)
                                    st.dataframe(dfp, hide_index=True, use_container_width=True)
                                    try:
                                        pin = float(out.get("Pin_MW", float("nan")))
                                        ploss = float(out.get("Ploss_MW", float("nan")))
                                        if np.isfinite(pin) and np.isfinite(ploss):
                                            st.metric("Closure check: Pin − Ploss (MW)", f"{(pin - ploss):.3g}")
                                    except Exception:
                                        pass
                                except Exception:
                                    st.info("Power ledger unavailable (missing keys).")

                        if _pd_tel_view == "Dominance & Closures":
                            st.subheader("Dominance & Closures")
                            st.caption("Read-only decision telemetry: what limits this point, and how the closure converged. No physics is modified.")

                            art0 = st.session_state.get("pd_last_artifact") or {}
                            cons0 = (art0.get("constraints") or []) if isinstance(art0, dict) else []
                            led0 = (art0.get("constraint_ledger") or {}) if isinstance(art0, dict) else {}
                            solver0 = (art0.get("solver") or {}) if isinstance(art0, dict) else {}

                            t_dom, t_closure = st.tabs(["Dominance Compass", "Closure Trace"])

                            with t_dom:
                                # Dominant violated constraints (intent-agnostic; policy lens is applied elsewhere)
                                top = (led0.get("top_blockers") or []) if isinstance(led0, dict) else []
                                if isinstance(top, list) and top:
                                    st.markdown("**Dominant violated constraints (hard-weighted)**")
                                    rows = []
                                    for e in top[:12]:
                                        if not isinstance(e, dict):
                                            continue
                                        rows.append({
                                            "rank": int(e.get("dominance_rank") or 0) if e.get("dominance_rank") is not None else None,
                                            "name": e.get("name"),
                                            "group": e.get("group"),
                                            "severity": e.get("severity"),
                                            "margin_frac": e.get("margin_frac"),
                                            "value": e.get("value"),
                                            "limit": e.get("limit"),
                                            "units": e.get("units"),
                                            "violation_score": e.get("violation_score"),
                                        })
                                    try:
                                        import pandas as _pd
                                        st.dataframe(_pd.DataFrame(rows), use_container_width=True, hide_index=True, height=320)
                                    except Exception:
                                        st.json(rows, expanded=False)
                                else:
                                    st.info("No violated hard constraints detected → this point is hard-feasible under the frozen evaluator.")

                                # Tightest (active) hard constraints, even if PASS
                                try:
                                    hard = [c for c in (cons0 or []) if isinstance(c, dict) and str(c.get("severity","hard")).lower()=="hard"]
                                    def _mf(c):
                                        try:
                                            return float(c.get("margin_frac"))
                                        except Exception:
                                            return float("nan")
                                    hard2 = [c for c in hard if np.isfinite(_mf(c))]
                                    hard2.sort(key=lambda c: float(_mf(c)))
                                    if hard2:
                                        st.markdown("**Tightest hard constraints (active set, worst-first)**")
                                        rows2 = []
                                        for c in hard2[:12]:
                                            rows2.append({
                                                "name": c.get("name"),
                                                "passed": bool(c.get("passed", True)),
                                                "margin_frac": float(_mf(c)),
                                                "value": c.get("value"),
                                                "limit": c.get("limit"),
                                                "units": c.get("units",""),
                                                "group": c.get("group",""),
                                            })
                                        import pandas as _pd
                                        st.dataframe(_pd.DataFrame(rows2), use_container_width=True, hide_index=True, height=320)
                                except Exception:
                                    pass

                            with t_closure:
                                st.markdown("**Closure ledger (solver trace)**")
                                if isinstance(solver0, dict) and solver0.get("backend") and isinstance(solver0.get("trace"), list):
                                    tr = solver0.get("trace") or []
                                    rows = []
                                    for k, step in enumerate(tr[:200]):  # hard cap for UI stability
                                        if not isinstance(step, dict):
                                            continue
                                        row = {"iter": k}
                                        # common fields used by constraint_solver trace
                                        for kk in ["x","vars","residual_norm","target_errors","status","note","clamped","alpha","damping","trust_delta"]:
                                            if kk in step:
                                                row[kk] = step.get(kk)
                                        rows.append(row)
                                    try:
                                        import pandas as _pd
                                        st.dataframe(_pd.DataFrame(rows), use_container_width=True, hide_index=True, height=420)
                                    except Exception:
                                        st.json(rows[:50], expanded=False)
                                    st.caption(f"backend={solver0.get('backend')} • ok={solver0.get('ok')} • iters={solver0.get('iters')} • message={solver0.get('message')}")
                                else:
                                    st.info("No solver trace available for this run (e.g., direct evaluation without target solve, or legacy fallback path).")

                        if _pd_tel_view == "Control Contracts":
                            st.subheader("Control Contracts")
                            st.caption("Envelope-based, deterministic control feasibility. Computes requirements only; does not modify physics. Disabled by default.")

                            # Enabled?
                            try:
                                _enabled = bool(inputs_dict.get("include_control_contracts", False)) if isinstance(inputs_dict, dict) else False
                            except Exception:
                                _enabled = False

                            if not _enabled:
                                st.info("Control contracts are OFF for this run. Enable 'include_control_contracts' in inputs to compute envelopes and optional caps.")
                            else:


                                # v227.0: authority tags + control budget ledger (read-only)
                                auth = out.get("control_contracts_authority")
                                budg = out.get("control_budget_ledger")
                                cA, cB = st.columns([1,2])
                                with cA:
                                    st.markdown("**Authority tags**")
                                    if isinstance(auth, dict) and auth:
                                        st.json(auth, expanded=False)
                                    else:
                                        st.caption("Authority tags not available.")
                                with cB:
                                    st.markdown("**Control budget ledger**")
                                    if isinstance(budg, dict) and budg:
                                        try:
                                            import pandas as pd
                                            rows = [{"key": k, "value": v} for k, v in budg.items()]
                                            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=220)
                                        except Exception:
                                            st.json(budg, expanded=False)
                                    else:
                                        st.caption("No budget ledger available.")

                                t_vs, t_pf, t_sol, t_rwm = st.tabs(["VS Control", "PF Envelope", "SOL Control", "RWM (MHD)"])

                                with t_vs:
                                    c1, c2, c3 = st.columns(3)
                                    c1.metric("τ_VS (s)", _fmt(out.get("tau_VS_s")))
                                    c2.metric("γ_VS (1/s)", _fmt(out.get("gamma_VS_s_inv")))
                                    c3.metric("BW required (Hz)", _fmt(out.get("vs_bandwidth_req_Hz")))
                                    st.caption("Proxy mapping: vs_margin → τ_VS via vs_tau_nominal_s; BW ≈ vs_bw_factor·γ/(2π).")
                                    st.markdown("**Caps (optional)**")
                                    d = {
                                        "bw_req_Hz": out.get("vs_bandwidth_req_Hz"),
                                        "bw_max_Hz": out.get("vs_bandwidth_max_Hz"),
                                        "P_req_MW": out.get("vs_control_power_req_MW"),
                                        "P_max_MW": out.get("vs_control_power_max_MW"),
                                        "ok": out.get("vs_control_ok"),
                                    }
                                    st.dataframe(pd.DataFrame([d]), use_container_width=True, hide_index=True)
                                    m = out.get("control_contract_margins")
                                    if isinstance(m, dict) and m:
                                        st.markdown("**Signed margins (cap - required)**")
                                        try:
                                            mm = {"bw_margin_Hz": m.get("vs_bandwidth_margin_Hz"), "P_margin_MW": m.get("vs_control_power_margin_MW")}
                                            st.dataframe(pd.DataFrame([mm]), use_container_width=True, hide_index=True)
                                        except Exception:
                                            st.json(m, expanded=False)

                                with t_pf:
                                    c1, c2, c3, c4 = st.columns(4)
                                    c1.metric("I_peak (MA)", _fmt(out.get("pf_I_peak_MA")))
                                    c2.metric("dI/dt_peak (MA/s)", _fmt(out.get("pf_dIdt_peak_MA_s")))
                                    c3.metric("V_peak (V)", _fmt(out.get("pf_V_peak_V")))
                                    c4.metric("P_peak (MW)", _fmt(out.get("pf_P_peak_MW")))
                                    st.metric("Pulse energy proxy (MJ)", _fmt(out.get("pf_E_pulse_MJ")))
                                    # CS/Volt-seconds bookkeeping
                                    st.markdown("**CS / Volt-seconds (pulsed) bookkeeping**")
                                    _cs_row = {
                                        "cs_flux_required_Wb": out.get("cs_flux_required_Wb"),
                                        "cs_flux_available_Wb": out.get("cs_flux_available_Wb"),
                                        "cs_flux_margin": out.get("cs_flux_margin"),
                                        "V_loop_ramp_V": out.get("cs_V_loop_ramp_V"),
                                        "V_loop_max_V": out.get("cs_V_loop_max_V"),
                                    }
                                    st.dataframe(pd.DataFrame([_cs_row]), use_container_width=True, hide_index=True)
                                    st.caption("Canonical ramp–flat–ramp waveform; V ≈ L_eff·dI/dt + R_eff·I. L_eff is inferred from CS flux requirement if not provided.")
                                    with st.expander("Control ledger (VS budget + headroom + RWM overlay)", expanded=False):
                                        if bool(out.get("control_stability_v398_enabled", False)):
                                            c1, c2, c3 = st.columns(3)
                                            c1.metric("VS budget margin", _fmt(out.get("vs_budget_margin_v398")))
                                            c2.metric("VDE headroom", _fmt(out.get("vde_headroom_v398")))
                                            c3.metric("RWM proximity idx", _fmt(out.get("rwm_proximity_index_v398")))
                                            st.markdown("**Tiers**")
                                            st.write({
                                                "vde_headroom_tier": out.get("vde_headroom_tier_v398"),
                                                "rwm_proximity_tier": out.get("rwm_proximity_tier_v398"),
                                            })
                                            st.markdown("**Ledger table**")
                                            _v398_row = {
                                                "psi_req_Vs": out.get("psi_required_Vs_v398"),
                                                "psi_av_Vs": out.get("psi_available_Vs_v398"),
                                                "vs_budget_margin": out.get("vs_budget_margin_v398"),
                                                "vde_power_headroom": out.get("vde_power_headroom_v398"),
                                                "vde_bw_headroom": out.get("vde_bw_headroom_v398"),
                                                "rwm_index": out.get("rwm_proximity_index_v398"),
                                            }
                                            st.dataframe(pd.DataFrame([_v398_row]), use_container_width=True, hide_index=True)
                                            st.caption("Control ledger is a governance-only overlay: no PF circuit solve; no transport/equilibrium iteration.")
                                        else:
                                            st.info("Control ledger is disabled for this run (enable in inputs).")

                                    st.markdown("**Caps (optional)**")
                                    d2 = {
                                        "I_peak": out.get("pf_I_peak_MA"),
                                        "I_max": out.get("pf_I_peak_max_MA"),
                                        "V_peak": out.get("pf_V_peak_V"),
                                        "V_max": out.get("pf_V_peak_max_V"),
                                        "P_peak": out.get("pf_P_peak_MW"),
                                        "P_max": out.get("pf_P_peak_max_MW"),
                                        "dIdt": out.get("pf_dIdt_peak_MA_s"),
                                        "dIdt_max": out.get("pf_dIdt_max_MA_s"),
                                        "E_pulse": out.get("pf_E_pulse_MJ"),
                                        "E_max": out.get("pf_E_pulse_max_MJ"),
                                        "ok": out.get("pf_envelope_ok"),
                                    }
                                    st.dataframe(pd.DataFrame([d2]), use_container_width=True, hide_index=True)
                                    m = out.get("control_contract_margins")
                                    if isinstance(m, dict) and m:
                                        st.markdown("**Signed margins (cap - required)**")
                                        try:
                                            mm = {
                                                "I_margin_MA": m.get("pf_I_peak_margin_MA"),
                                                "dIdt_margin_MA_s": m.get("pf_dIdt_margin_MA_s"),
                                                "V_margin_V": m.get("pf_V_peak_margin_V"),
                                                "P_margin_MW": m.get("pf_P_peak_margin_MW"),
                                                "E_margin_MJ": m.get("pf_E_pulse_margin_MJ"),
                                            }
                                            st.dataframe(pd.DataFrame([mm]), use_container_width=True, hide_index=True)
                                        except Exception:
                                            st.json(m, expanded=False)
                                    wf = out.get("pf_waveform_decimated")
                                    if isinstance(wf, list) and wf:
                                        st.markdown("**Decimated waveform (t, I)**")
                                        st.dataframe(pd.DataFrame(wf), use_container_width=True, hide_index=True, height=220)

                                with t_sol:
                                    c1, c2, c3, c4 = st.columns(4)
                                    c1.metric("q_target", _fmt(out.get("q_div_target_MW_m2")))
                                    c2.metric("f_SOL+div required", _fmt(out.get("detachment_f_sol_div_required")))
                                    c3.metric("Prad_SOL+div required (MW)", _fmt(out.get("detachment_prad_sol_div_required_MW")))
                                    c4.metric("f_z required", _fmt(out.get("detachment_f_z_required")))
                                    st.caption(
                                        "Detachment authority is algebraic: q_div_target → required SOL+div radiation → implied impurity fraction using an Lz(T_SOL) envelope. "
                                        "It does not change the operating point unless you enforce caps."
                                    )
                                    m = out.get("control_contract_margins")
                                    if isinstance(m, dict) and m and (m.get("f_rad_SOL_margin") is not None):
                                        st.markdown("**Signed margin (cap - required)**")
                                        st.write({"f_rad_SOL_margin": m.get("f_rad_SOL_margin")})

                                with t_rwm:
                                    _rwm_enabled = bool(inputs_dict.get("include_rwm_screening", False)) if isinstance(inputs_dict, dict) else False
                                    if not _rwm_enabled:
                                        st.info("RWM screening is OFF for this run. Enable 'include_rwm_screening' to compute PROCESS-class RWM control requirements.")
                                    else:
                                        c1, c2, c3, c4 = st.columns(4)
                                        c1.metric("Regime", str(out.get("rwm_regime", "")))
                                        c2.metric("βN_NW", _fmt(out.get("rwm_betaN_no_wall")))
                                        c3.metric("βN_IW", _fmt(out.get("rwm_betaN_ideal_wall")))
                                        c4.metric("χ", _fmt(out.get("rwm_chi")))
                                        c5, c6, c7 = st.columns(3)
                                        c5.metric("τ_w (s)", _fmt(out.get("rwm_tau_w_s")))
                                        c6.metric("BW required (Hz)", _fmt(out.get("rwm_bandwidth_req_Hz")))
                                        c7.metric("P required (MW)", _fmt(out.get("rwm_control_power_req_MW")))
                                        st.caption("Screening: βN between no-wall and ideal-wall limits implies an active RWM requiring feedback. Exceeding βN_IW is flagged as non-operable.")

                                        st.markdown("**Caps (optional; default to VS caps if not provided)**")
                                        d3 = {
                                            "bw_req_Hz": out.get("rwm_bandwidth_req_Hz"),
                                            "bw_max_Hz": out.get("rwm_bandwidth_max_Hz"),
                                            "P_req_MW": out.get("rwm_control_power_req_MW"),
                                            "P_max_MW": out.get("rwm_control_power_max_MW"),
                                            "ok": out.get("rwm_control_ok"),
                                        }
                                        st.dataframe(pd.DataFrame([d3]), use_container_width=True, hide_index=True)
                                        m = out.get("control_contract_margins")
                                        if isinstance(m, dict) and m:
                                            st.markdown("**Signed margins (cap - required)**")
                                            st.dataframe(pd.DataFrame([{
                                                "bw_margin_Hz": m.get("rwm_bandwidth_margin_Hz"),
                                                "P_margin_MW": m.get("rwm_control_power_margin_MW"),
                                            }]), use_container_width=True, hide_index=True)
    

                                    with st.expander("Magnet technology authority (B–T–J–stress–quench ledger)", expanded=False):
                                        if bool(out.get("magnet_v400_enabled", False)):
                                            c1, c2, c3, c4 = st.columns(4)
                                            c1.metric("Combined margin", _fmt(out.get("magnet_v400_margin")))
                                            c2.metric("Tier", str(out.get("magnet_v400_tier", "unknown")))
                                            c3.metric("Dominant", str(out.get("magnet_v400_dominant_limiter", "unknown")))
                                            c4.metric("Dominant margin", _fmt(out.get("magnet_v400_dominant_margin")))
                                            st.markdown("**Per-aspect margins**")
                                            st.write({
                                                "B margin (allow/req - 1)": out.get("magnet_v400_b_margin"),
                                                "J margin (allow/req - 1)": out.get("magnet_v400_j_margin"),
                                                "Stress margin (allow/req - 1)": out.get("magnet_v400_stress_margin"),
                                                "SC operating margin ((sc/sc_min)-1)": out.get("magnet_v400_sc_oper_margin"),
                                                "T-window margin (normalized)": out.get("magnet_v400_t_window_margin"),
                                                "Cu ohmic power margin (Pmax/Pohmic - 1)": out.get("magnet_v400_p_tf_ohmic_margin"),
                                            })
                                            st.markdown("**Per-aspect tiers**")
                                            st.write({
                                                "B tier": out.get("magnet_v400_b_tier"),
                                                "J tier": out.get("magnet_v400_j_tier"),
                                                "Stress tier": out.get("magnet_v400_stress_tier"),
                                                "SC tier": out.get("magnet_v400_sc_tier"),
                                                "T-window tier": out.get("magnet_v400_t_window_tier"),
                                                "Cu ohmic tier": out.get("magnet_v400_p_tf_ohmic_tier"),
                                            })
                                        else:
                                            st.info("Magnet technology ledger is disabled or unavailable for this run.")
                        if _pd_tel_view == "Mission Snapshot":
                            with st.expander("Regime Compass - Sanity Dashboard", expanded=False):
                                st.caption("Expert quick-check panel. Values are diagnostic unless explicitly constrained.")
                                try:
                                    # Optional uncertainty bands for proxy quantities (nice-to-have; UI-only)
                                    show_unc = st.checkbox("Show proxy uncertainty bands (diagnostic)", value=False, key="pd_show_proxy_unc")
                                    unc_proxy = float(st.session_state.get("pd_unc_proxy_frac", 0.15))
                                    unc_neut = float(st.session_state.get("pd_unc_neut_frac", 0.20))
                                    if show_unc:
                                        c1, c2 = st.columns(2)
                                        unc_proxy = c1.slider("Proxy ±%", min_value=0.0, max_value=0.50, value=float(unc_proxy), step=0.01, key="pd_unc_proxy_frac")
                                        unc_neut = c2.slider("Neutronics/SOL proxy ±%", min_value=0.0, max_value=0.50, value=float(unc_neut), step=0.01, key="pd_unc_neut_frac")
    
                                    # Typical-range flags (non-blocking)
                                    typical = {
                                        "rho_star": (1e-4, 3e-2),
                                        "H98": (0.7, 1.5),
                                        "fG": (0.2, 1.2),
                                        "nGW": (0.1, 2.0),
                                        "betaN_proxy": (0.5, 4.0),
                                        'q95_proxy': (2.5, 6.0),
                                        "P_SOL_over_R_MW_m": (0.0, 50.0),
                                        "f_bs_proxy": (0.0, 1.0),
                                        "ne20": (0.0, 3.0),
                                        "Zeff": (1.0, 3.0),
                                        "lambda_q_mm": (0.1, 10.0),
                                        "q_div_MW_m2": (0.0, 50.0),
                                        "P_CD_MW": (0.0, 300.0),
                                        "eta_CD_A_W": (0.0, 5e-6),
                                        "TBR": (0.7, 1.4),
                                        "B_peak_T": (0.0, 30.0),
                                    }
    
                                    rows_s = [
                                        ("ρ*", "rho_star", "–", "Diagnostic"),
                                        ("H98", "H98", "–", "Authoritative"),
                                        ("fG", "fG", "–", "Authoritative"),
                                        ("nGW", "nGW", "×1e20 m⁻³", "Diagnostic"),
                                        ("βN", "betaN_proxy", "–", "Proxy"),
                                        ("q95", 'q95_proxy', "–", "Authoritative"),
                                        ("P_SOL/R", "P_SOL_over_R_MW_m", "MW/m", "Authoritative"),
                                        ("Bootstrap f_bs", "f_bs_proxy", "–", "Proxy"),
                                        ("n̄e", "ne20", "×1e20 m⁻³", "Authoritative"),
                                        ("Z_eff", "Zeff", "–", "Proxy"if bool(include_radiation) else "Diagnostic"),
                                        ("λq", "lambda_q_mm", "mm", "Proxy"if bool(use_lambda_q) else "Diagnostic"),
                                        ("q_div", "q_div_MW_m2", "MW/m²", "Authoritative"),
                                        ("P_CD", "P_CD_MW", "MW", "Proxy"),
                                        ("η_CD", "eta_CD_A_W", "A/W", "Proxy"),
                                        ("TBR", "TBR", "–", "Proxy"),
                                        ("B_peak", "B_peak_T", "T", "Authoritative"),
                                    ]
    
                                    data = []
                                    # NOTE: do not name the loop variable `badge` here.
                                    # This file also defines a `badge()` helper function.
                                    # Using `badge` as a top-level loop variable would shadow the
                                    # function and later calls like `badge(c)` would crash with:
                                    #   TypeError: 'str' object is not callable
                                    for label, key, unit, badge_type in rows_s:
                                        try:
                                            v = out.get(key, float("nan"))
                                        except Exception:
                                            v = float("nan")
                                        lo, hi = typical.get(key, (float("nan"), float("nan")))
                                        flag = ""
                                        try:
                                            if np.isfinite(v) and np.isfinite(lo) and np.isfinite(hi):
                                                if v < lo:
                                                    flag = "LOW"
                                                elif v > hi:
                                                    flag = "HIGH"
                                        except Exception:
                                            pass
                                        unc = ""
                                        if show_unc and (badge_type == "Proxy"):
                                            frac = unc_proxy
                                            if key in ("TBR", "lambda_q_mm"):
                                                frac = unc_neut
                                            try:
                                                if np.isfinite(v):
                                                    unc = f"±{(100*frac):.0f}%"
                                            except Exception:
                                                pass
                                        data.append({"Metric": label, "Key": key, "Value": v, "Units": unit, "Type": badge_type, "Typical": f"{lo:g}–{hi:g}"if np.isfinite(lo) and np.isfinite(hi) else "", "Flag": flag, "Unc": unc})
    
                                    dfs = pd.DataFrame(data)
                                    st.dataframe(dfs, hide_index=True, use_container_width=True)
                                    st.caption("Flags are non-blocking and intended as expert context. Typical ranges are heuristic defaults.")
                                except Exception:
                                    st.info("Sanity dashboard unavailable (missing keys).")
    
                        if _pd_tel_view == "Sensitivity Lab":
                            with st.expander("Perturbation Probe (±10%)", expanded=False):
                                st.caption("Perturb key inputs by ±10% and report which hard constraints flip. This is local intuition, not optimization.")
                                if st.button("Run ±10% perturbation scan", use_container_width=True, key="pd_run_pert_scan"):
                                    try:
                                        # Use the solved point if available; fall back to base
                                        try:
                                            pi0 = sol_inp if sol_inp is not None else base
                                        except Exception:
                                            pi0 = base
                                        base_out = _ui_evaluate(pi0, origin="Point Designer", Paux_for_Q_MW=Paux_for_Q)
                                        base_failed = [c.name for c in (evaluate_constraints(base_out) or []) if (getattr(c, 'severity', 'hard') == 'hard') and (not bool(getattr(c,'passed', False)))]
                                        keys = ["R0_m","a_m","kappa","Bt_T","Ip_MA","fG","Ti_keV","Paux_MW"]
                                        rows = []
                                        for k in keys:
                                            if not hasattr(pi0, k):
                                                continue
                                            x0 = float(getattr(pi0, k))
                                            if not np.isfinite(x0) or x0 == 0.0:
                                                continue
                                            for fac in (0.9, 1.1):
                                                # PointInputs is a frozen dataclass; use dataclasses.replace
                                                # instead of setattr.
                                                try:
                                                    from dataclasses import replace as _dc_replace
                                                    pi = _dc_replace(pi0, **{k: x0 * fac})
                                                except Exception:
                                                    # Fallback for older input types
                                                    pi = make_point_inputs(**dict(getattr(pi0, '__dict__', {})))
                                                    try:
                                                        setattr(pi, k, x0 * fac)
                                                    except Exception:
                                                        pass
                                                y = _ui_evaluate(pi, origin="Point Designer", Paux_for_Q_MW=Paux_for_Q)
                                                failed = [c.name for c in (evaluate_constraints(y) or []) if (getattr(c, 'severity', 'hard') == 'hard') and (not bool(getattr(c,'passed', False)))]
                                                rows.append({
                                                    "param": k,
                                                    "factor": fac,
                                                    "value": x0 * fac,
                                                    "hard_failed": ", ".join(failed),
                                                    "new_failures": ", ".join(sorted(set(failed) - set(base_failed))),
                                                    "resolved": ", ".join(sorted(set(base_failed) - set(failed))),
                                                })
                                        st.session_state["pd_pert_scan_rows"] = rows
                                    except Exception as e:
                                        st.warning(f"Perturbation scan failed: {e}")
                                rows = st.session_state.get("pd_pert_scan_rows", [])
                                if rows:
                                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                                else:
                                    st.caption("No scan results yet.")
    
    
    
    
                        # external systems codes-style local sensitivities (finite differences)

                        # -----------------------------------------------------------------
                        # Constraint dashboard (transparent (systems-code-inspired)) with margins + suggestions
                        # -----------------------------------------------------------------
                        if _pd_tel_view == "Mission Snapshot":
                            with st.expander("Constraint Radar - Pass/Fail & Margins", expanded=False):
                                if not constraints_list:
                                    st.info("No constraints evaluated (missing keys).")
                                else:
                                    rows_c = []
                                    for c in constraints_list:
                                        try:
                                            margin = float(getattr(c, "margin"))
                                        except Exception:
                                            margin = float("nan")
                                        rows_c.append({
                                            "constraint": c.name,
                                            "sense": c.sense,
                                            "value": c.value,
                                            "limit": c.limit,
                                            "units": c.units,
                                            "passed": bool(c.passed),
                                            "margin_frac": margin,
                                            "severity": getattr(c, "severity", "hard"),
                                            "note": c.note,
                                        })
                                    dfc = pd.DataFrame(rows_c)
                                    # sort: hard fails first, then smallest margin
                                    try:
                                        dfc = dfc.sort_values(by=["passed", "severity", "margin_frac"], ascending=[True, True, True])
                                    except Exception:
                                        pass
                                    st.dataframe(dfc, use_container_width=True)
    
                                    # --- Constraint provenance (expert trust) ---
                                    # Streamlit dataframes do not support per-row tooltips well; expose a focused detail view.
                                    _prov = {
                                        "q95": {"def": "Proxy q95 computed from geometry/Bt/Ip assumptions.", "drivers": "Ip, Bt, R0, a, κ", "sense": ">=", "notes": "Always hard in both intents."},
                                        "q_div": {"def": "Divertor peak heat flux proxy from P_SOL and wetted area / λq model.", "drivers": "P_SOL, R0, λq, f_rad", "sense": "<=", "notes": "Definition depends on SOL-width toggle."},
                                        "P_SOL/R": {"def": "Separatrix power normalized by major radius.", "drivers": "P_SOL, R0", "sense": "<=", "notes": "Often used as a heat-exhaust severity proxy."},
                                        "sigma_vm": {"def": "Von Mises stress proxy in TF structure from peak field + build.", "drivers": "B_peak, coil build, R0", "sense": "<=", "notes": "Engineering screening, not a full FEA."},
                                        "HTS margin": {"def": "HTS current-density/temperature margin proxy.", "drivers": "B_peak, Top, Jop, conductor assumption", "sense": ">=", "notes": "Screening margin; label as proxy if conductor model simplified."},
                                        "TBR": {"def": "Tritium breeding ratio proxy from blanket/shield thickness + coverage assumptions.", "drivers": "t_blanket, t_shield, coverage", "sense": ">=", "notes": "Proxy unless driven by external neutronics."},
                                        "NWL": {"def": "Neutron wall loading proxy from fusion power and surface area.", "drivers": "Pfus, R0, a, κ", "sense": "<=", "notes": "Screening metric."},
                                        "beta": {"def": "Beta or normalized beta proxy guardrail.", "drivers": "pressure, Bt, Ip", "sense": "<=", "notes": "Proxy stability screen."},
                                    }
    
                                    with st.expander("Constraint details (definitions + drivers)", expanded=False):
                                        names = [r["constraint"] for r in rows_c]
                                        pick = st.selectbox("Select a constraint", options=names, index=0, key="pd_pick_constraint")
                                        rec = next((r for r in rows_c if r["constraint"] == pick), None) or {}
                                        st.markdown(f"**{pick}**")
                                        st.write({"sense": rec.get("sense"), "value": rec.get("value"), "limit": rec.get("limit"), "units": rec.get("units"), "passed": rec.get("passed"), "margin_frac": rec.get("margin_frac"), "severity": rec.get("severity"), "note": rec.get("note")})
                                        # Best-effort provenance lookup by substring match
                                        key_l = str(pick).lower()
                                        prov = None
                                        for k, v in _prov.items():
                                            if k.lower() in key_l:
                                                prov = v
                                                break
                                        if prov:
                                            st.write({"definition": prov.get("def"), "drivers": prov.get("drivers"), "sense": prov.get("sense"), "notes": prov.get("notes")})
                                        else:
                                            st.caption("No additional provenance notes registered for this constraint yet.")
    
                                    failed = [r for r in rows_c if not r["passed"] and r.get("severity","hard") == "hard"]
                                    if failed:
                                        st.error(f"{len(failed)} hard constraint(s) failed. See suggestions below.")
                                    soft_failed = [r for r in rows_c if not r["passed"] and r.get("severity") == "soft"]
                                    if soft_failed:
                                        st.warning(f"{len(soft_failed)} soft constraint(s) failed (screening only).")
    
                                    # Dominant limiter (tightest hard margin) - plain language
                                    try:
                                        hard_rows = [r for r in rows_c if str(r.get("severity","hard")) == "hard"]
                                        hard_rows = [r for r in hard_rows if r.get("margin_frac") == r.get("margin_frac")]
                                        hard_rows_sorted = sorted(hard_rows, key=lambda r: float(r.get("margin_frac", float('inf'))))
                                        if hard_rows_sorted:
                                            dom = hard_rows_sorted[0]
                                            st.info(
                                                f"**Dominant limiter:** {dom.get('constraint')} (margin {float(dom.get('margin_frac')):.3g}). "
                                                f"This is the tightest hard constraint at this point."
                                            )
                                    except Exception:
                                        pass
    
                                    def _suggest(name: str) -> str:
                                        n = name.lower()
                                        if "q_div"in n or "p_sol"in n:
                                            return "Reduce P_SOL (increase radiation, reduce aux), increase R0, or increase lambda_q (design/multiplier)."
                                        if "hts"in n or "b_peak"in n or "sigma"in n:
                                            return "Reduce B_peak (increase coil build/R0, reduce Bt), reduce stress (increase thickness, reduce B_peak), or raise HTS margin (lower Top or improve conductor)."
                                        if "tbr"in n:
                                            return "Increase blanket/shield thickness or improve breeding/coverage assumptions."
                                        if "nwl"in n:
                                            return "Reduce fusion power density (increase size R0 or reduce performance targets) or improve shielding."
                                        if "beta"in n:
                                            return "Increase size R0 or reduce Ip/pressure (lower Ti or fG) to bring beta below limit."
                                        if "q95"in n:
                                            return "Increase q95 (reduce Ip or increase Bt/R0) for stability margin."
                                        if "fg"in n:
                                            return "Reduce density target (lower fG) or increase Ip to raise Greenwald limit."
                                        if "p_net"in n:
                                            return "Increase Pfus (within constraints), increase thermal efficiency, or reduce recirculating loads."
                                        if "t_flat"in n:
                                            return "Increase available flux swing (CS design), reduce loop voltage (improve resistivity/current profile), or allow lower Ip."
                                        return "Adjust major radius / field / current / aux power to recover feasibility."
    
                                    if failed or soft_failed:
                                        st.markdown("**Actionable suggestions (rule-of-thumb):**")
                                        for r in failed + soft_failed:
                                            st.write("- **{}**: {}".format(r["constraint"], _suggest(r["constraint"])))
    
                        # --- Compare to baseline (delta view) ---
                        if _pd_tel_view == "Sensitivity Lab":
                            with st.expander("Delta View - Compare to Baseline", expanded=False):
                                st.caption("Set a baseline (e.g., preset or previous run) and view deltas for key KPIs and tightest constraints.")
                                if st.button("Set baseline = current point", key="pd_set_baseline", use_container_width=True):
                                    try:
                                        st.session_state["pd_baseline_artifact"] = st.session_state.get("pd_last_artifact")
                                    except Exception:
                                        pass
                                base_art = st.session_state.get("pd_baseline_artifact")
                                cur_art = st.session_state.get("pd_last_artifact")
                                if isinstance(base_art, dict) and isinstance(cur_art, dict):
                                    bo = base_art.get("outputs", {}) or {}
                                    co = cur_art.get("outputs", {}) or {}
                                    kpis = [
                                        ("Q_DT_eqv", "Q_DT_eqv", "–"),
                                        ("H98", "H98", "–"),
                                        ("P_net_e", "P_net_e_MW", "MW(e)"),
                                        ("q95", 'q95_proxy', "–"),
                                        ("betaN", "betaN_proxy", "–"),
                                        ("q_div", "q_div_MW_m2", "MW/m²"),
                                        ("P_SOL", "P_SOL_MW", "MW"),
                                        ("TBR", "TBR", "–"),
                                    ]
                                    rows = []
                                    for label, key, unit in kpis:
                                        vb = bo.get(key, float("nan"))
                                        vc = co.get(key, float("nan"))
                                        dlt = float("nan")
                                        try:
                                            if np.isfinite(vb) and np.isfinite(vc):
                                                dlt = float(vc) - float(vb)
                                        except Exception:
                                            pass
                                        rows.append({"KPI": label, "baseline": vb, "current": vc, "delta": dlt, "unit": unit})
                                    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
                                else:
                                    st.caption("No baseline set yet.")
                        if _pd_tel_view == "Sensitivity Lab":
                            with st.expander("Local Sensitivities - Finite Difference", expanded=False):
                                st.caption("Local derivatives around the current point. Useful for design intuition; not a global optimization result.")
                                try:
                                    params = ["R0_m","a_m","kappa","B0_T","Ip_MA","fG","H98","eta_CD","n_neu_frac","Zeff"]
                                    outs = ["Q_DT_eqv","P_net_e_MW","betaN","q_div_MW_m2","B_peak_T"]
                                    def _eval(pi):
                                        return _ui_evaluate(pi, origin="Point Designer")
                                    sens = finite_difference_sensitivities(base, _eval, params=params, outputs=outs, rel_step=1e-3)
                                    # Show a compact table: normalized sensitivities (per 1% change), where possible
                                    rows = []
                                    for o in outs:
                                        base_y = float(sens.get("_base", {}).get(o, float("nan")))
                                        for p in params:
                                            if p not in sens.get(o, {}):
                                                continue
                                            dydx = float(sens[o][p])
                                            x0 = float(getattr(base, p)) if hasattr(base, p) and getattr(base, p) is not None else float("nan")
                                            # normalized: (dY/Y) / (dX/X)  = (dY/dX) * (X/Y)
                                            norm = float("nan")
                                            if x0 == x0 and base_y == base_y and x0 != 0.0 and base_y != 0.0:
                                                norm = dydx * (x0 / base_y)
                                            rows.append({"output": o, "param": p, "dY/dX": dydx, "elasticity": norm})
                                    if rows:
                                        df_s = pd.DataFrame(rows)
                                        st.dataframe(df_s.sort_values(["output","param"]), use_container_width=True)
                                    else:
                                        st.info("Sensitivities unavailable for this point (missing keys or non-finite outputs).")
    
                                except Exception as e:
                                    st.warning(f"Sensitivity calculation failed: {e}")
    
                        # --- Point summary (compact table) ---
                        st.markdown("### Point summary")
                        try:
                            _sum_rows = [
                                {"KPI":"Q_DT_eqv","value": out.get("Q_DT_eqv"), "unit":"-"},
                                {"KPI":"H98","value": out.get("H98"), "unit":"-"},
                                {"KPI":"H_scaling","value": out.get("H_scaling"), "unit":"-"},
                                {"KPI":"tauE_eff","value": out.get("tauE_eff_s"), "unit":"s"},
                                {"KPI":"Pfus_DT_adj","value": out.get("Pfus_DT_adj_MW"), "unit":"MW"},
                                {"KPI":"P_net_e","value": out.get("P_net_e_MW"), "unit":"MW(e)"},
                                {"KPI":"q95","value": out.get('q95_proxy'), "unit":"-"},
                                {"KPI":"betaN","value": out.get("betaN_proxy"), "unit":"-"},
                                {"KPI":"f_bs","value": out.get("f_bs_proxy"), "unit":"-"},
                                {"KPI":"q_div","value": out.get("q_div_MW_m2"), "unit":"MW/m²"},
                                {"KPI":"sigma_vm","value": out.get("sigma_vm_MPa"), "unit":"MPa"},
                                {"KPI":"HTS margin","value": out.get("hts_margin"), "unit":"-"},
                                {"KPI":"TBR","value": out.get("TBR"), "unit":"-"},
                            ]
                            _df_sum = pd.DataFrame(_sum_rows)
                            st.dataframe(_df_sum, hide_index=True, use_container_width=True)
                        except Exception:
                            pass

                        # --- Run summary (copy/paste; publication-friendly) ---
                        with st.expander("Run summary (copy/paste)", expanded=False):
                            try:
                                rs = (st.session_state.get('pd_last_artifact', {}) or {}).get('run_summary', {}) or {}
                                tight = rs.get('tightest_hard_constraints', []) or []
                                lines = []
                                lines.append(f"Design intent: {str(st.session_state.get('design_intent',''))}")
                                try:
                                    ver = (REPO_ROOT / 'VERSION').read_text(encoding='utf-8').strip().splitlines()[0]
                                except Exception:
                                    ver = 'unknown'
                                lines.append(f"SHAMS version: {ver}")
                                h = rs.get('headline', {}) or {}
                                _q = float(h.get('Q_DT_eqv', float('nan')))
                                _h98 = float(h.get('H98', float('nan')))
                                _pnet = float(h.get('P_net_e_MW', float('nan')))
                                lines.append(f"Headline: Q={_q:.3g} | H98={_h98:.3g} | P_net_e={_pnet:.3g} MW(e)")
                                if rs.get('power_closure_MW') == rs.get('power_closure_MW'):
                                    lines.append(f"Power closure: Pin−Ploss = {rs.get('power_closure_MW'):.3g} MW")
                                if tight:
                                    lines.append("Tightest hard constraints:")
                                    for c in tight:
                                        lines.append(f"- {c.get('name')}: passed={c.get('passed')} margin={c.get('margin_frac'):.3g} ({c.get('sense')} {c.get('limit')} {c.get('units')})")
                                st.code("\n".join(lines), language="text")
                            except Exception as e:
                                st.caption(f"Run summary unavailable: {e}")

                        if _pd_tel_view == "Plot Deck":
                            with st.expander("Plot Deck", expanded=False):
                                st.markdown("#### Plot Deck - quick-look engineering visuals")
                                st.caption("Visuals are screening-level (0‑D proxies). No ranking; just visibility.")
                                try:
                                    import matplotlib.pyplot as _plt
                                except Exception:
                                    _plt = None

                                def _sf(x):
                                    try:
                                        return float(x)
                                    except Exception:
                                        return float('nan')

                                o = out if isinstance(locals().get('out'), dict) else (st.session_state.get('pd_last_outputs') or {})
                                a = st.session_state.get('pd_last_artifact') or {}

                                c1, c2 = st.columns(2)

                                with c1:
                                    if _plt is not None:
                                        Pfus = _sf(o.get('P_fus_MW', o.get('Pfus_MW', float('nan'))))
                                        Paux = _sf(o.get('Paux_MW', float('nan')))
                                        Prec = _sf(o.get('P_recirc_MW', o.get('P_e_recirc_MW', float('nan'))))
                                        Pnet = _sf(o.get('P_e_net_MW', o.get('P_net_e_MW', float('nan'))))
                                        vals, labels = [], []
                                        for lab, v in [('Fusion', Pfus), ('Aux', Paux), ('Recirc', Prec), ('Net', Pnet)]:
                                            if v == v:
                                                labels.append(lab)
                                                vals.append(v)
                                        if len(vals) >= 2:
                                            fig = _plt.figure()
                                            _plt.bar(labels, vals)
                                            _plt.ylabel('MW')
                                            _plt.title('Power Stack (screening)')
                                            st.pyplot(fig, use_container_width=True)
                                        else:
                                            st.caption('Power stack unavailable for this point.')
                                    else:
                                        st.caption('Matplotlib unavailable.')

                                with c2:
                                    tight = (a.get('run_summary') or {}).get('tightest_hard_constraints', []) if isinstance(a, dict) else []
                                    tight = [t for t in (tight or []) if isinstance(t, dict)]
                                    tight = sorted(tight, key=lambda t: _sf(t.get('margin_frac', float('inf'))))[:10]
                                    if _plt is not None and tight:
                                        names = [t.get('name','?') for t in tight][::-1]
                                        mfs = [_sf(t.get('margin_frac', float('nan'))) for t in tight][::-1]
                                        fig = _plt.figure()
                                        _plt.barh(names, mfs)
                                        _plt.axvline(1.0, linestyle='--')
                                        _plt.xlabel('Margin fraction (>=1 pass)')
                                        _plt.title('Tightest Hard Constraints')
                                        st.pyplot(fig, use_container_width=True)
                                    else:
                                        st.caption('Constraint margin plot unavailable (no run summary yet).')

                                c3, c4 = st.columns(2)
                                with c3:
                                    if _plt is not None:
                                        q95 = _sf(o.get('q95_proxy', o.get('q95', float('nan'))))
                                        betaN = _sf(o.get('betaN_proxy', o.get('betaN', float('nan'))))
                                        fG = _sf(o.get('fG', float('nan')))
                                        labs, ys = [], []
                                        for lab, v in [('q95', q95), ('βN', betaN), ('fG', fG)]:
                                            if v == v:
                                                labs.append(lab)
                                                ys.append(v)
                                        if ys:
                                            fig = _plt.figure()
                                            _plt.bar(labs, ys)
                                            _plt.title('Regime Dials (dimensionless)')
                                            st.pyplot(fig, use_container_width=True)
                                        else:
                                            st.caption('Regime dials unavailable.')

                                with c4:
                                    if _plt is not None:
                                        Bpk = _sf(o.get('B_peak_T', float('nan')))
                                        qdiv = _sf(o.get('q_div_MW_m2', float('nan')))
                                        nwl = _sf(o.get('NWL_MW_m2', o.get('nwl_MW_m2', float('nan'))))
                                        labs, vals = [], []
                                        for lab, v in [('Bpeak (T)', Bpk), ('qdiv (MW/m²)', qdiv), ('NWL (MW/m²)', nwl)]:
                                            if v == v:
                                                labs.append(lab)
                                                vals.append(v)
                                        if vals:
                                            fig = _plt.figure()
                                            _plt.bar(labs, vals)
                                            _plt.title('Engineering Severity (screening)')
                                            st.pyplot(fig, use_container_width=True)
                                        else:
                                            st.caption('Engineering severity plot unavailable.')
                                st.markdown("### Plot dashboard")
                                ptab1, ptab2, ptab3, ptab4 = st.tabs(["Power balance", "Stability & limits", "Geometry / build", "Confinement"])
    
                                with ptab1:
                                    st.caption(
                                        "Quick visual breakdown of where power is going in this 0‑D point (all Phase‑1 proxies)."
                                    )
                                    power_vals = {
                                        "Paux [MW]": out.get("Paux_MW"),
                                        "Pfus (DT-eqv) [MW]": out.get("Pfus_DT_adj_MW"),
                                        "Pα dep [MW]": out.get("Palpha_dep_MW"),
                                        "Prad_core [MW]": out.get("Prad_core_MW"),
                                        "P_SOL [MW]": out.get("P_SOL_MW"),
                                        "P_net_e [MW]": out.get("P_net_e_MW"),
                                    }
                                    plot_bars(power_vals, "Power balance (MW)")
                                    with st.expander("Physical meaning (with literature)", expanded=False):
                                        st.markdown(
                                            """
            **Q (fusion gain proxy)** is defined as fusion power divided by auxiliary heating power (here the UI uses *Paux_for_Q* as the denominator).  
            **H98** is a confinement multiplier relative to the empirical **IPB98(y,2)** ELMy H‑mode scaling used as an ITER physics-basis reference. citeturn1view0turn0search16

            **P_LH / H‑mode access** comparisons in this app follow the multi‑machine ITPA threshold scaling (often referred to as “Martin‑2008 / PLH‑08”). citeturn3search18

            If you enable SOL-width physics, the app’s λq proxy is motivated by the multi‑machine H‑mode power‑falloff width scaling (Eich‑2013). citeturn2search3
                                        """
                                    )

                            with ptab2:
                                st.caption("Screening metrics vs common operational ‘guardrails’ (Phase‑1 proxies).")
                                stab_vals = {
                                    "q95": out.get('q95_proxy'),
                                    "βN": out.get("betaN_proxy"),
                                    "f_bs": out.get("f_bs_proxy"),
                                }
                                plot_bars(stab_vals, "Stability / operational metrics")
                                with st.expander("Physical meaning (with literature)", expanded=False):
                                    st.markdown(
                                        """
            **q95** (safety factor near 95% flux) is a standard operational metric used as a proxy for MHD margin; lower q tends to reduce kink/tearing stability margin.

            **Normalized beta βN** is a widely used performance/stability figure of merit that scales pressure relative to magnetic field and current (often discussed in terms of the “Troyon” aB/I scaling). citeturn0search19

            **Bootstrap fraction f_bs** indicates how much of the plasma current is self‑driven by pressure gradients (important for steady‑state operation). This UI uses a simple proxy coefficient (C_bs) rather than a full neoclassical calculation.
                                        """
                                    )

                            with ptab3:
                                st.caption("A few geometry/build proxies that drive magnet and shield feasibility checks.")
                                geom_vals = {
                                    "R0 [m]": out.get("R0_m"),
                                    "a [m]": out.get("a_m"),
                                    "B0 [T]": out.get("Bt_T"),
                                    "Bpeak [T]": out.get("Bpeak_T"),
                                    "σ_hoop [MPa]": out.get("sigma_hoop_MPa"),
                                    "t_shield [m]": out.get("t_shield_m"),
                                }
                                plot_bars(geom_vals, "Key geometry/build scalars")
                                with st.expander("Physical meaning (with literature)", expanded=False):
                                    st.markdown(
                                        """
                **Greenwald fraction fG** (used internally by the solver) expresses density as a fraction of the empirical tokamak density limit scaling with I_p and minor radius (often called the Greenwald limit).

            The *radial build* and **Bpeak/B0** mapping are engineering proxies; they’re not meant to replace detailed coil/stress finite‑element analysis.
                                        """
                                    )

                            with ptab4:
                                st.caption("Energy confinement and empirical H-factor comparators.")
                                conf_vals = {
                                    "tauE_eff [s]": out.get("tauE_eff_s"),
                                    "tauE_scaling [s]": out.get("tauScaling_s") if "tauScaling_s"in out else out.get("tauIPB_s"),
                                    "H98": out.get("H98"),
                                    "H_scaling": out.get("H_scaling"),
                                    "H_required": out.get("H_required"),
                                    "tauE_env_min [s]": out.get("tauE_envelope_min_s"),
                                    "tauE_env_max [s]": out.get("tauE_envelope_max_s"),
                                    "tauE_env_min_v396 [s]": out.get("tauE_envelope_min_s_v396"),
                                    "tauE_env_max_v396 [s]": out.get("tauE_envelope_max_s_v396"),
                                    "spread_v396": out.get("transport_spread_ratio_v396"),
                                    "tier_v396": out.get("transport_credibility_tier_v396"),
                                    "transport_pass_opt": out.get("transport_pass_optimistic"),
                                    "transport_pass_rob": out.get("transport_pass_robust"),
                                    "power_balance_residual [MW]": out.get("power_balance_residual_MW"),
                                    "fp0_v397": out.get("profile_peaking_p_v397"),
                                    "q0_proxy_v397": out.get("q0_proxy_v397"),
                                    "li_proxy_v397": out.get("li_proxy_v397"),
                                    "boot_loc_v397": out.get("bootstrap_localization_index_v397"),
                                }
                                plot_bars(conf_vals, "Confinement / H metrics")
                                with st.expander("Multi-scaling confinement envelope scalings", expanded=False):
                                    d = out.get("tauE_scalings_v396", {}) if isinstance(out, dict) else {}
                                    if isinstance(d, dict) and len(d) > 0:
                                        try:
                                            import pandas as pd
                                            df = pd.DataFrame([{"scaling": k, "tauE_s": v} for k, v in d.items()])
                                            st.dataframe(df, use_container_width=True, hide_index=True)
                                        except Exception:
                                            st.json(d)
                                    else:
                                        st.caption("No multi-scaling confinement dictionary available for this run (module disabled or invalid inputs).")
                                with st.expander("Notes", expanded=False):
                                    st.markdown("H98 is defined as tauE_eff / tauE_IPB98(y,2). H_scaling compares against the selected reference scaling. See also the IPB98(y,2) and ITER89-P scaling references.")

                                with st.expander("Kinetic profile peaking proxy", expanded=False):
                                    if bool(out.get("profile_proxy_v397_enabled", False)):
                                        st.caption("Deterministic 1.5D proxy diagnostics (no solvers).")
                                        st.write(
                                            {
                                                "peaking_n": out.get("profile_peaking_n_v397"),
                                                "peaking_T": out.get("profile_peaking_T_v397"),
                                                "peaking_p": out.get("profile_peaking_p_v397"),
                                                "peaking_j": out.get("profile_peaking_j_v397"),
                                                "q95_proxy": out.get("q95_proxy_v397"),
                                                "q0_proxy": out.get("q0_proxy_v397"),
                                                "li_proxy": out.get("li_proxy_v397"),
                                                "bootstrap_localization": out.get("bootstrap_localization_index_v397"),
                                            }
                                        )
                                        samp = out.get("profile_proxy_v397_sample", {})
                                        if isinstance(samp, dict) and len(samp) > 0:
                                            try:
                                                import pandas as pd
                                                df = pd.DataFrame(samp)
                                                st.dataframe(df, use_container_width=True, hide_index=True)
                                            except Exception:
                                                st.json(samp)
                                    else:
                                        st.caption("Profile proxy is disabled for this run (enable in Point Designer).")

                            st.markdown("### Raw telemetry")
                            st.dataframe(pd.DataFrame([out]).T.rename(columns={0: "value"}), use_container_width=True)

        with tab_con:
            st.subheader("Constraint Briefing")
            try:
                from ui.verdict_ui import render_constraint_table_sorted
                from constraints.unified import build_all_constraints

                _out_con = st.session_state.get("pd_last_outputs")
                if isinstance(_out_con, dict) and _out_con:
                    with st.expander("Constraint pipeline diff (registry vs legacy)", expanded=False):
                        render_point_designer_constraint_diff(st.session_state)
                    with st.expander("NO-SOLUTION mechanism atlas", expanded=False):
                        render_point_designer_no_solution_atlas(st.session_state)
                    with st.expander("Constraint ledger (sorted by residual)", expanded=False):
                        _bundle = build_all_constraints(_out_con)
                        render_constraint_table_sorted(_bundle.governance, use_governance=True)
            except Exception:
                pass
            st.markdown(f"**Design intent:** {st.session_state.get('design_intent', 'Power Reactor (net-electric)')}")
            _pol = _constraint_policy_snapshot()
            st.caption(
                "Policy: "+ ("Reactor hard constraints enforced."if _pol.get("intent_key")=="reactor"else "Research intent: only q95 is blocking; engineering limits are diagnostic; TBR ignored.")
            )
            with st.expander("Constraint notebook", expanded=False):
                out = st.session_state.last_point_out
                if out is None:
                    st.info("Run **Evaluate Point** to see constraint checks.")
                else:
                    try:
                        _failed_hard = [str(c.name) for c in (evaluate_constraints(out) or []) if str(getattr(c,'severity','soft'))=='hard' and (not bool(getattr(c,'passed', False)))]
                    except Exception:
                        _failed_hard = []
                    _cls = _classify_failed_constraints(_failed_hard)
                    if _cls.get('blocking') or _cls.get('diagnostic') or _cls.get('ignored'):
                        st.markdown('**Intent-aware constraint summary**')
                        if _cls.get('blocking'):
                            st.markdown('**Blocking (per intent):** ' + ', '.join([f'`{x}`' for x in _cls.get('blocking')]))
                        if _cls.get('diagnostic'):
                            st.markdown('**Diagnostics:** ' + ', '.join([f'`{x}`' for x in _cls.get('diagnostic')]))
                        if _cls.get('ignored'):
                            st.markdown('**Ignored:** ' + ', '.join([f'`{x}`' for x in _cls.get('ignored')]))
                    checks = compute_checks(out)
                    for c in _dedupe_checks(checks):
                        with st.expander(f"{c.get('name', 'Check')}", expanded=False):
                            st.write(f"**{c['name']}** - {badge(c)}")
                            v = c.get("value")
                            lim = c.get("limit")
                            wl = c.get("warn_limit")
                            if isinstance(v, (int, float)) and isinstance(lim, (int, float)) and math.isfinite(v) and math.isfinite(lim):
                                if isinstance(wl, (int, float)) and math.isfinite(wl):
                                    st.caption(f"value={v:.4g} warn={wl:.4g} limit={lim:.4g} ({c.get('sense','')})")
                                else:
                                    st.caption(f"value={v:.4g} limit={lim:.4g} ({c.get('sense','')})")
                            if c.get("notes"):
                                st.caption(c["notes"])
                            st.divider()

                    with st.expander("Check summary", expanded=False):
                        bad = top_violations(checks, 3)
                        if bad:
                            st.markdown("### Top violations")
                            for c in bad:
                                st.write(f"- **{c['name']}**: value={c.get('value')} vs limit={c.get('limit')}")
                        else:
                            st.success("All enabled checks passed for this point (per Phase‑1 proxy models).")


    # -----------------------------
    # Scan Lab
    # -----------------------------
    # -----------------------------
    # Systems Mode (transparent (systems-code-inspired) coupled targeting)
    # -----------------------------

    # --- v92: Stateful Results ---
    if _deck == "Point Designer":
        try:
            st.subheader("Stateful Results")
            s = _v92_state_get()
            c1, c2 = st.columns([1,3])
            with c1:
                if st.button("Clear point state", key="v92_clear_point_state"):
                    _v92_state_clear_point()
                    st.success("Cleared point state.")
                    st.stop()
            with c2:
                st.caption("Results persist across reruns/downloads. This panel renders from session state.")

            if s.has_point():
                if isinstance(s.last_point_radial_png, (bytes, bytearray)) and len(s.last_point_radial_png) > 0:
                    st.image(s.last_point_radial_png, caption="Radial build (stateful preview)", use_container_width=True)

                import json as _json
                st.download_button(
                    "Download run artifact JSON (stateful)",
                    data=_json.dumps(s.last_point_artifact, indent=2, sort_keys=True),
                    file_name="shams_run_artifact.json",
                    mime="application/json",
                    use_container_width=True,
                    key="v92_dl_artifact_stateful",
                )
                if isinstance(s.last_point_radial_png, (bytes, bytearray)) and len(s.last_point_radial_png) > 0:
                    st.download_button(
                        "Download radial build PNG (stateful)",
                        data=s.last_point_radial_png,
                        file_name="shams_radial_build.png",
                        mime="image/png",
                        use_container_width=True,
                        key="v92_dl_png_stateful",
                    )
            else:
                st.info("No stateful Point result yet. Click 'Evaluate Point' to compute one.")
        except Exception:
            pass

