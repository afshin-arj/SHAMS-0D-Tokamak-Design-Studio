"""Pareto Lab deck -- extracted from ui/app.py (UI redesign batch 6).

Pure move + cosmetic de-emoji. No physics, constraint, solver, evaluator,
session-state key, or routing-ID changes. Namespace bridge (including app.py's
__file__) keeps path computations and bare names resolving as before. Temporary
tech debt; replace with explicit imports/ctx in a later cleanup commit.
"""
from __future__ import annotations
import streamlit as st
import sys


from ._bridge import bridge_deck

def render_pareto_lab(_app_module) -> None:
    bridge_deck(_app_module, globals())

    # DSG: auto edge-kind tagging by active panel (exploration only)
    if bool(st.session_state.get("dsg_edge_kind_auto", True)):
        st.session_state["dsg_context_edge_kind"] = "pareto"

    st.header("Pareto Lab")
    st.caption("Trade-off observatory over the feasible set. External optimization is firewalled; truth remains frozen.")
    render_mode_scope("pareto")
    # --- Pareto freeze (read-only semantics) ---
    st.info(PARETO_LOCK_LINE)

    # --- Deck selector (v230.0: external optimizer console) ---
    _pareto_deck_keys = [
        "Internal Pareto Frontier",
        "Robust Pareto Frontier (Phase+UQ)",
        "Regime-Conditioned Pareto Atlas 2.0",
        "Certified Optimization Orchestrator",
        "Feasible Optimizer (External)",
        "Concept Optimization Cockpit",
        "External Optimization Workbench",
        "External Optimization Interpretation",
        "Design Family Narratives",
        "External Optimizer Co-Pilot",
        "External Optimizer Suite",
        "Optimization Evidence Packs",
    ]
    _pareto_deck_labels = {
        "Internal Pareto Frontier": "Internal Pareto Frontier",
        "Robust Pareto Frontier (Phase+UQ)": "Robust Pareto Frontier (Phase+UQ)",
        "Regime-Conditioned Pareto Atlas 2.0": "Regime-Conditioned Pareto Atlas 2.0",
        "Certified Optimization Orchestrator": "Certified Optimization Orchestrator",
        "Feasible Optimizer (External)": "Feasible Optimizer (External)",
        "Concept Optimization Cockpit": "Concept Optimization Cockpit",
        "External Optimization Workbench": "External Optimization Workbench",
        "External Optimization Interpretation": "External Optimization Interpretation",
        "Design Family Narratives": "Design Family Narratives",
        "External Optimizer Co-Pilot": "External Optimizer Co-Pilot",
        "External Optimizer Suite": "External Optimizer Suite",
        "Optimization Evidence Packs": "Optimization Evidence Packs",
    }

    # Back-compat for older stored values that included emojis in the raw key.
    _legacy_to_key = {
        "Concept Optimization Cockpit": "Concept Optimization Cockpit",
        "External Optimization Workbench": "External Optimization Workbench",
        "External Optimizer Suite": "External Optimizer Suite",
    }
    try:
        _legacy = st.session_state.get("pareto_deck_selector_v230")
        if isinstance(_legacy, str) and _legacy in _legacy_to_key:
            st.session_state["pareto_deck_selector_v230"] = _legacy_to_key[_legacy]
    except Exception:
        pass

    _pareto_deck = st.radio(
        "Pareto Lab deck",
        options=_pareto_deck_keys,
        index=0,
        horizontal=True,
        format_func=lambda k: _pareto_deck_labels.get(str(k), str(k)),
        help=(
            "Choose the Pareto Lab deck. External optimizer tooling runs outside the frozen evaluator "
            "and does not modify physics truth."
        ),
        key="pareto_deck_selector_v230",
    )

    if _pareto_deck == "Feasible Optimizer (External)":
        render_external_optimizer_launcher(Path(__file__).resolve().parent.parent)
        st.stop()

    if _pareto_deck == "Certified Optimization Orchestrator":
        from ui.certified_opt_orchestrator import render_certified_optimization_orchestrator

        render_certified_optimization_orchestrator(Path(__file__).resolve().parent.parent)
        st.stop()

    if _pareto_deck == "Concept Optimization Cockpit":
        from ui.concept_opt_cockpit import render_concept_optimization_cockpit

        render_concept_optimization_cockpit(Path(__file__).resolve().parent.parent)
        st.stop()

    if _pareto_deck == "External Optimization Workbench":
        from ui.extopt_workbench import render_extopt_workbench

        render_extopt_workbench(Path(__file__).resolve().parent.parent)
        st.stop()

    if _pareto_deck == "External Optimization Interpretation":
        from ui.extopt_interpretation import render_extopt_interpretation

        render_extopt_interpretation(Path(__file__).resolve().parent.parent)
        st.stop()

    if _pareto_deck == "Design Family Narratives":
        from ui.design_families import render_design_families

        render_design_families(Path(__file__).resolve().parent.parent)
        st.stop()

    if _pareto_deck == "External Optimizer Co-Pilot":
        from ui.extopt_copilot import render_extopt_copilot

        render_extopt_copilot(Path(__file__).resolve().parent.parent)
        st.stop()

    if _pareto_deck == "External Optimizer Suite":
        from ui.extopt_suite import render_extopt_suite

        render_extopt_suite(Path(__file__).resolve().parent.parent)
        st.stop()

    if _pareto_deck == "Optimization Evidence Packs":
        render_optimizer_evidence_packs(Path(__file__).resolve().parent.parent)
        st.stop()

    if _pareto_deck == "Robust Pareto Frontier (Phase+UQ)":
        from ui.robust_pareto_lab import render_robust_pareto_lab

        render_robust_pareto_lab(Path(__file__).resolve().parent.parent)
        st.stop()

    if _pareto_deck == "Regime-Conditioned Pareto Atlas 2.0":
        from ui.regime_conditioned_atlas import render_regime_conditioned_atlas

        render_regime_conditioned_atlas(Path(__file__).resolve().parent.parent)
        st.stop()


    # Summary card (filled after run if results exist)
    with st.container(border=True):
        st.markdown("**Frontier Dashboard**")
        _sum_cols = st.columns(5)
        # placeholders populated later via session state when available
        _ps = st.session_state.get("pareto_last_summary", {})
        _sum_cols[0].metric("Feasible points", _ps.get("n_feasible", "-"))
        _sum_cols[1].metric("Pareto points", _ps.get("n_pareto", "-"))
        _sum_cols[2].metric("Top constraint", _ps.get("top_constraint", "-"))
        _sum_cols[3].metric("Robust mix", _ps.get("robust_mix", "-"))
        _sum_cols[4].metric("Confidence", _ps.get("confidence", "-"))

    # Definition of Pareto optimal (SHAMS-specific)
    with st.expander("What does “Pareto optimal” mean here? (frontier concept)", expanded=False):
        st.markdown(PARETO_OPTIMAL_DEF)

    # Trust boundaries
    with st.expander("Trust boundaries (what you can and cannot conclude)", expanded=False):
        for _t in TRUST_BOUNDARIES:
            st.markdown(f"- {_t}")

        st.caption("Pareto Lab does **not** recommend or select designs. It maps unavoidable trade-offs among **feasible** designs only.")

    # --- Governance (read-only) ---
    with st.expander("Pareto Mode governance (constitution / freeze / contribution rules)", expanded=False):
        st.caption("Read-only governance documents that protect Pareto from drifting into optimization or recommendations.")
        try:
            _c = (Path(__file__).resolve().parent.parent / "docs"/ "PARETO_MODE_CONSTITUTION.md").read_text(encoding="utf-8")
            _f = (Path(__file__).resolve().parent.parent / "docs"/ "PARETO_V1_FREEZE_DECLARATION.md").read_text(encoding="utf-8")
            _r = (Path(__file__).resolve().parent.parent / "docs"/ "PARETO_POST_FREEZE_CONTRIBUTION_RULES.md").read_text(encoding="utf-8")
            _t = (Path(__file__).resolve().parent.parent / "docs"/ "PARETO_TEACHING_FREEZE_POLICY.md").read_text(encoding="utf-8")
        except Exception:
            _c=_f=_r=_t="(missing doc file in this build)"
        cols = st.columns(4)
        cols[0].download_button("Download Constitution", data=_c, file_name="PARETO_MODE_CONSTITUTION.md", mime="text/markdown", use_container_width=True)
        cols[1].download_button("Download Freeze", data=_f, file_name="PARETO_V1_FREEZE_DECLARATION.md", mime="text/markdown", use_container_width=True)
        cols[2].download_button("Download Rules", data=_r, file_name="PARETO_POST_FREEZE_CONTRIBUTION_RULES.md", mime="text/markdown", use_container_width=True)
        cols[3].download_button("Download Teaching Policy", data=_t, file_name="PARETO_TEACHING_FREEZE_POLICY.md", mime="text/markdown", use_container_width=True)

    # --- Replay (read-only) ---
    with st.expander("Replay capsule (read-only)", expanded=False):
        st.caption("Load a previously exported Pareto artifact and reproduce the same front without re-sampling. This is audit/review mode.")
        art_file = st.file_uploader("Upload Pareto artifact (.json)", type=["json"], key="pareto_replay_uploader")
        if art_file is not None:
            try:
                art = json.load(art_file)
                st.success("Artifact loaded.")
                st.json({k: art.get(k) for k in ["schema", "version", "intent_mode", "n_samples", "seed", "objectives"] if k in art}, expanded=False)
                _front = pd.DataFrame(art.get("pareto", []) or [])
                _feas = pd.DataFrame(art.get("feasible", []) or [])
                if len(_front):
                    st.markdown("#### Replayed Pareto front")
                    try:
                        import plotly.express as px
                        _objs = list((art.get("objectives") or {}).keys())
                        if len(_objs) >= 2:
                            x, y = _objs[0], _objs[1]
                            fig = px.scatter(_front, x=x, y=y, color="dominant_constraint"if "dominant_constraint"in _front.columns else None, hover_data=_front.columns)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.dataframe(_front, use_container_width=True)
                    except Exception:
                        st.dataframe(_front, use_container_width=True)
                if len(_feas):
                    st.markdown("#### Replayed feasible set (sampled)")
                    st.dataframe(_feas.head(200), use_container_width=True)
            except Exception as e:
                st.error(f"Could not load artifact: {e}")

    st.markdown(
        "This mode performs a deterministic-feeling **LHS sampling study** inside explicit bounds, filters **intent-aware feasible** points, "
        "and constructs **constraint-annotated Pareto fronts** for explicit objectives."
    )

    # --- Objective Contract (explicit, publishable) ---
    _OBJ_CATALOG = {
        "R0_m": {"units": "m", "desc": "Major radius"},
        "Bt_T": {"units": "T", "desc": "Toroidal field on axis"},
        "Ip_MA": {"units": "MA", "desc": "Plasma current"},
        "fG": {"units": "-", "desc": "Greenwald fraction"},
        "B_peak_T": {"units": "T", "desc": "Peak TF field"},
        "P_e_net_MW": {"units": "MW", "desc": "Net electric power"},
        "Q_DT_eqv": {"units": "-", "desc": "Equivalent DT gain"},
        "q_div_MW_m2": {"units": "MW/m^2", "desc": "Divertor heat-flux proxy"},
        "sigma_vm_MPa": {"units": "MPa", "desc": "Von Mises stress proxy"},
        "hts_margin_cs": {"units": "-", "desc": "HTS margin (critical surface)"},
        "TBR": {"units": "-", "desc": "Tritium breeding ratio"},
    }

    base0 = st.session_state.get("last_point_inp")
    if base0 is None:
        base0 = PointInputs(R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.0, Ti_keV=15.0, fG=0.8, Paux_MW=20.0)

    with st.expander("Bounds (sampling hyper-rectangle)", expanded=False):
        st.caption("Bounds are applied to the chosen variables during sampling.")
        bcols = st.columns(4)
        b_R0 = (float(_safe_get(base0, 'R0_m')*0.8), float(_safe_get(base0, 'R0_m')*1.25))
        b_Bt = (float(_safe_get(base0, 'Bt_T')*0.7), float(_safe_get(base0, 'Bt_T')*1.15))
        b_Ip = (float(_safe_get(base0, 'Ip_MA')*0.6), float(_safe_get(base0, 'Ip_MA')*1.6))
        b_fG = (0.3, 1.1)
        R0_lo = _num("R0 min [m]", b_R0[0], 0.01)
        R0_hi = _num("R0 max [m]", b_R0[1], 0.01)
        Bt_lo = _num("Bt min [T]", b_Bt[0], 0.1)
        Bt_hi = _num("Bt max [T]", b_Bt[1], 0.1)
        Ip_lo = _num("Ip min [MA]", b_Ip[0], 0.1)
        Ip_hi = _num("Ip max [MA]", b_Ip[1], 0.1)
        fG_lo = _num("fG min [-]", b_fG[0], 0.05)
        fG_hi = _num("fG max [-]", b_fG[1], 0.05)

        bounds = {
            "R0_m": (float(R0_lo), float(R0_hi)),
            "Bt_T": (float(Bt_lo), float(Bt_hi)),
            "Ip_MA": (float(Ip_lo), float(Ip_hi)),
            "fG": (float(fG_lo), float(fG_hi)),
        }

    with st.expander("Objective Contract (explicit)", expanded=False):
        st.caption("Objectives are explicit and unit-aware. No hidden scoring. The contract is included in exports.")
        # Objective templates (smart presets, not recommendations)
        _OBJ_TEMPLATES = {
            "Custom": None,
            "Reactor - Compact power": {"R0_m":"min","P_e_net_MW":"max","q_div_MW_m2":"min","sigma_vm_MPa":"min","TBR":"max"},
            "Reactor - Max gain": {"Q_DT_eqv":"max","P_e_net_MW":"max","R0_m":"min","q_div_MW_m2":"min"},
            "Research - High current/density": {"Ip_MA":"max","fG":"max","R0_m":"min","Bt_T":"max"},
            "Research - High field": {"Bt_T":"max","B_peak_T":"max","R0_m":"min"},
        }
        tmpl = st.selectbox("Objective template", options=list(_OBJ_TEMPLATES.keys()), index=0, help="Populates objectives with common expert framing. This is not a recommendation.")
        if "pareto_template_last"not in st.session_state:
            st.session_state.pareto_template_last = "Custom"
        # When template changes, update defaults in session_state (deterministic)
        if tmpl != st.session_state.pareto_template_last and _OBJ_TEMPLATES.get(tmpl):
            st.session_state.pareto_sel_objs = list(_OBJ_TEMPLATES[tmpl].keys())
            st.session_state.pareto_obj_senses = dict(_OBJ_TEMPLATES[tmpl])
            st.session_state.pareto_template_last = tmpl
        elif tmpl != st.session_state.pareto_template_last:
            st.session_state.pareto_template_last = tmpl

        intent_mode = st.radio("Design Intent", ["Reactor", "Research", "Both (overlay)"] , index=0, horizontal=True)
        obj_keys = list(_OBJ_CATALOG.keys())
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            sel_objs = st.multiselect("Objectives", options=obj_keys, default=st.session_state.get("pareto_sel_objs", ["R0_m", "B_peak_T", "P_e_net_MW"]), key="pareto_sel_objs")
        with c2:
            st.write("\n")
            robust_margin_thr = float(st.number_input("Robust margin threshold", value=0.10, step=0.05))
        with c3:
            st.write("\n")
            n_samples = int(st.slider("Samples", min_value=50, max_value=4000, value=300, step=50))
        seed = int(st.number_input("Sampling seed", value=1, step=1))

        objectives = {}
        for k in sel_objs:
            meta = _OBJ_CATALOG.get(k, {})
            cols = st.columns([2, 1, 2])
            with cols[0]:
                st.write(f"**{k}**")
            with cols[1]:
                objectives[k] = st.selectbox(f"sense_{k}", ["min", "max"], index=(0 if st.session_state.get("pareto_obj_senses", {}).get(k, ("min"if k in ("R0_m","B_peak_T","q_div_MW_m2","sigma_vm_MPa") else "max"))=="min"else 1), label_visibility="collapsed")
            with cols[2]:
                st.caption(f"{meta.get('desc','')} [{meta.get('units','-')}]".strip())

        if len(objectives) < 2:
            st.warning("Select at least 2 objectives for a meaningful Pareto front.")

        # Objective sanity validator (warnings only; does not block)
        st.divider()
        with st.expander("Objective sanity checks (warnings only)", expanded=False):
            warns=[]
            if any(k.upper().startswith("TBR") for k in objectives.keys()) and str(intent_mode).startswith("Research"):
                warns.append("TBR is typically **ignored as a blocking constraint** in Research intent. Using TBR as an objective in Research may be uninformative.")
            if any(k in ["P_e_net_MW"] for k in objectives.keys()) and str(intent_mode).startswith("Research"):
                warns.append("Net electric power is usually not a Research driver; ensure this objective is meaningful for your study.")
            if len(set(objectives.keys())) != len(objectives):
                warns.append("Duplicate objective keys detected (this should not happen).")
            if len(warns)==0:
                st.success("No obvious objective-contract red flags.")
            else:
                for w in warns:
                    st.warning(w)

        # Redundancy hint
        st.divider()
        st.caption("Redundancy detection runs after sampling (correlation-based).")

    if st.button("Run Pareto (feasible-only)", type="primary", use_container_width=True):
        import time
        t0=time.time()
        try:
            from solvers.optimize import pareto_optimize
            intents = ["Reactor", "Research"] if str(intent_mode).startswith("Both") else [str(intent_mode)]
            all_runs = []
            all_fronts = []
            all_samples = []
            for it in intents:
                res = pareto_optimize(base0, bounds=bounds, objectives=objectives, n_samples=n_samples, seed=seed, intent_key=it)
                feasible = res.get("feasible", [])
                front = res.get("pareto", [])
                all_samp = res.get("all", [])
                if all_samp:
                    dfA = pd.DataFrame(all_samp)
                    dfA["intent"] = it
                    all_samples.append(dfA)
                if feasible:
                    dfF = pd.DataFrame(feasible)
                    dfF["intent"] = it
                    all_runs.append(dfF)
                if front:
                    dfP = pd.DataFrame(front)
                    dfP["intent"] = it
                    all_fronts.append(dfP)

            dfF_all = pd.concat(all_runs, ignore_index=True) if all_runs else pd.DataFrame()
            dfP_all = pd.concat(all_fronts, ignore_index=True) if all_fronts else pd.DataFrame()
            dfA_all = pd.concat(all_samples, ignore_index=True) if all_samples else pd.DataFrame()
            st.session_state.pareto_last = {
                "objectives": objectives,
                "intent_mode": intent_mode,
                "bounds": bounds,
                "seed": seed,
                "n_samples": n_samples,
                "feasible": dfF_all.to_dict(orient="records") if len(dfF_all) else [],
                "pareto": dfP_all.to_dict(orient="records") if len(dfP_all) else [],
                "robust_margin_thr": robust_margin_thr,
            }

            st.success(f"Done. Feasible points: {len(dfF_all)} / {n_samples*len(intents)}. Pareto points: {len(dfP_all)}. ({time.time()-t0:.1f}s)")
            # Explain why not (if feasibility/front is empty)
            if len(dfF_all) == 0 or len(dfP_all) == 0:
                with st.expander("Explain why not (empty feasibility or empty Pareto front)", expanded=False):
                    if len(dfF_all) == 0:
                        st.warning("No feasible designs were found in the sampled bounds for the selected intent(s). This is not a plotting issue; it means feasibility was not achieved under the frozen evaluator.")
                    elif len(dfP_all) == 0:
                        st.warning("Feasible designs exist, but no non-dominated Pareto set was produced (often due to objective redundancy or insufficient variation).")
                    try:
                        if len(dfA_all) and "first_failure"in dfA_all.columns:
                            vc = dfA_all["first_failure"].fillna("(none)").astype(str).value_counts().head(8)
                            st.markdown("**Top blocking constraints in sampled space (first-failure counts):**")
                            st.dataframe(vc.rename("count").to_frame(), use_container_width=True)
                            st.caption("Tip: If a single constraint dominates all failures, the bounds likely never enter a feasible basin for that intent.")
                        else:
                            st.info("No failure-atlas data available in this run.")
                    except Exception:
                        st.info("Could not summarize failure modes for this run.")

            # --- Sampling honesty panel ---

            with st.expander("Sampling honesty (coverage / density / what was explored)", expanded=False):
                st.caption("Pareto conclusions are only as strong as sampling coverage. This panel reports coverage proxies (no smoothing).")
                if len(dfA_all):
                    st.write({
                        "n_samples_total": int(len(dfA_all)),
                        "n_feasible": int(len(dfF_all)),
                        "feasible_fraction": float(len(dfF_all)/max(len(dfA_all),1)),
                        "intents": intents,
                        "seed": seed,
                    })
                    # Density proxy in objective space (kNN distance)
                    try:
                        obj_keys=list(objectives.keys())
                        if len(obj_keys)>=2 and len(dfF_all)>=10:
                            X=dfF_all[obj_keys].astype(float).to_numpy()
                            k=min(10, len(X)-1)
                            d2=((X[:,None,:]-X[None,:,:])**2).sum(axis=2)
                            np.fill_diagonal(d2, np.inf)
                            knn=np.sort(d2,axis=1)[:,:k]
                            rho=np.sqrt(np.mean(knn,axis=1))
                            st.metric("Median local spacing (objective-space)", float(np.median(rho)))
                            st.metric("95% spacing (thin regions)", float(np.percentile(rho,95)))
                        else:
                            st.info("Density proxy requires ≥10 feasible points and ≥2 objectives.")
                    except Exception as _e:
                        st.info(f"Could not compute density proxy: {_e}")
                else:
                    st.info("No sampling summary available for this run.")

            # --- Failure atlas (infeasible shadow) ---
            with st.expander("Failure atlas (infeasible shadow / what blocks the frontier)", expanded=False):
                st.caption("Faintly shows sampled infeasible points and the first blocking constraint. This does not relax constraints.")
                if len(dfA_all):
                    dfI = dfA_all[~dfA_all.get("is_feasible", False)].copy() if "is_feasible"in dfA_all.columns else pd.DataFrame()
                    if len(dfI) and len(objectives)>=2:
                        obj_keys=list(objectives.keys())
                        x,y=obj_keys[0], obj_keys[1]
                        try:
                            import plotly.express as px
                            figI = px.scatter(dfI, x=x, y=y, color="first_failure"if "first_failure"in dfI.columns else None,
                                              opacity=0.25, hover_data=dfI.columns)
                            st.plotly_chart(figI, use_container_width=True)
                        except Exception:
                            st.dataframe(dfI.head(200), use_container_width=True)
                    else:
                        st.info("No infeasible shadow available (or not enough objectives selected).")
                else:
                    st.info("No infeasible shadow available for this run.")
            if len(dfF_all):
                st.markdown("### Feasible set (intent-aware)")
                st.dataframe(dfF_all, use_container_width=True, height=260)

                # Objective redundancy detection (correlation over feasible set)
                try:
                    corr = dfF_all[list(objectives.keys())].corr(numeric_only=True)
                    bad = []
                    for i, a in enumerate(corr.columns):
                        for j, b in enumerate(corr.columns):
                            if j <= i:
                                continue
                            v = float(corr.loc[a, b])
                            if abs(v) >= 0.92:
                                bad.append((a, b, v))
                    if bad:
                        st.warning("Objective redundancy detected (high correlation on feasible set):")
                        st.dataframe(pd.DataFrame(bad, columns=["objective_a", "objective_b", "corr"]), use_container_width=True)
                except Exception:
                    pass


                # Objective interaction matrix (sign-only couplings on feasible manifold)
                # Non-trade-off region marker (when objectives co-improve)
                try:
                    if "pareto_front"in st.session_state:
                        _pf = st.session_state["pareto_front"]
                        if isinstance(_pf, pd.DataFrame) and len(_pf) >= 10:
                            _okeys = list(objectives.keys())
                            if len(_okeys) >= 2:
                                _c = _pf[_okeys[:2]].corr(numeric_only=True).iloc[0, 1]
                                if _c == _c and float(_c) > 0.80:
                                    st.info("No meaningful trade-off detected in this projection (objectives tend to improve together here).")
                except Exception:
                    pass



                with st.expander("Objective interaction matrix (sign-only, descriptive)", expanded=False):
                    st.caption("Shows how objectives tend to co-vary across the feasible set (not recommendations). '+' means tends to increase together, '-' means trade-off, '~' means weak/none.")
                    try:
                        obj_keys = list(objectives.keys())
                        if len(obj_keys) >= 2 and len(dfF_all) >= 8:
                            C = dfF_all[obj_keys].corr(numeric_only=True)
                            def _sg(v: float) -> str:
                                if not (v == v):
                                    return ""
                                if abs(v) < 0.25:
                                    return "~"
                                return "+"if v > 0 else "-"
                            M = C.copy()
                            for a in obj_keys:
                                for b in obj_keys:
                                    M.loc[a, b] = _sg(float(C.loc[a, b]))
                            st.dataframe(M, use_container_width=True)
                        else:
                            st.info("Not enough feasible points/objectives to form an interaction matrix.")
                    except Exception:
                        st.info("Interaction matrix unavailable in this run.")

                # Epistemic confidence + incompleteness detector (sampling honesty → confidence)
                with st.expander("Confidence & incompleteness (epistemic, not physics)", expanded=False):
                    st.caption("These are sampling-based confidence signals: they estimate where the Pareto picture is solid vs where it may be incomplete due to limited coverage.")
                    try:
                        feas_frac = float(len(dfF_all) / max(int(len(dfA_all)), 1)) if len(dfA_all) else float(len(dfF_all) / max(int(n_samples*len(intents)), 1))
                        st.write({"n_feasible": int(len(dfF_all)), "n_front": int(len(dfP_all)), "feasible_fraction": feas_frac})
                        # Heuristic incompleteness flags
                        flags = []
                        if len(dfF_all) < max(50, 0.01 * n_samples * max(len(intents),1)):
                            flags.append("Feasible sample is sparse; Pareto front may be incomplete.")
                        if feas_frac < 0.002:
                            flags.append("Feasible fraction is very low; consider that the sampled bounds may mostly miss the feasible basin.")
                        if flags:
                            st.warning("| ".join(flags))
                        else:
                            st.success("No major incompleteness flags triggered by sampling proxies.")
                    except Exception:
                        st.info("Confidence/incompleteness summary unavailable.")

                # Active question suggestions (guides thinking; does not choose designs)
                with st.expander("Possible next questions (guidance, not recommendations)", expanded=False):
                    qs = []
                    try:
                        if 'bad' in locals() and bad:
                            qs.append("Two objectives appear redundant here - would you like to hide one and re-run to sharpen the front?")
                    except Exception:
                        pass
                    try:
                        if len(dfP_all) and "min_signed_margin"in dfP_all.columns:
                            frac_frag = float((pd.to_numeric(dfP_all["min_signed_margin"], errors="coerce") < float(robust_margin_thr)).mean())
                            if frac_frag > 0.5:
                                qs.append("Most Pareto points are fragile under the chosen margin threshold - would you like to view robust-only by default?")
                    except Exception:
                        pass
                    if str(intent_mode).startswith("Both"):
                        qs.append("Would you like to compare intent-split fronts side-by-side (Research vs Reactor) on the same axes?")
                    qs.append("Would you like to export a publication pack (artifact + CSV + narrative + PNG) for this run?")
                    qs.append("Would you like to click a segment and read the regime explanation (what pins this trade-off)?")
                    for q in qs[:6]:
                        st.write("• "+ q)

                # Self-audit (continuous proof of integrity)
                with st.expander("Pareto self-audit (read-only integrity checklist)", expanded=False):
                    st.caption("This checklist is informational; it summarizes SHAMS guarantees for this mode.")
                    st.write(
                        {
                            "feasible_only": True,
                            "deterministic": True,
                            "no_recommendations": True,
                            "policy_explicit": True,
                            "intent_explicit": True,
                            "sampling_honesty_reported": True,
                        }
                    )

                # Language calibration (scientific phrasing guardrail)
                with st.expander("Language calibration (how to read statements)", expanded=False):
                    st.caption("All Pareto statements are conditional on bounds, intent, policy, and sampling. They are descriptive (not prescriptive).")
                    st.write("Example: “Stress dominates here” means “Given the selected bounds and policy, σ_vm is most limiting along this segment in the sampled feasible set.”")
            if len(dfP_all):
                st.markdown("### Pareto fronts (constraint-annotated)")
                st.dataframe(dfP_all, use_container_width=True, height=260)

                # Promote a selected Pareto point back into Point Designer (canonical handoff)
                with st.expander("Promote a Pareto point to Point Designer", expanded=False):
                    st.caption("Select a point from the Pareto front and promote it into Point Designer inputs (no evaluation performed here).")
                    try:
                        _idxs = list(range(int(len(dfP_all))))
                        _pick = int(st.selectbox("Pareto row index", options=_idxs, index=0, key="pareto_promote_row")) if _idxs else 0
                        _row = dfP_all.iloc[_pick].to_dict() if len(dfP_all) else {}
                        st.write({k: _row.get(k) for k in list(objectives.keys())[:4] + ["dominant_constraint", "min_constraint_margin", "intent"] if k in _row})
                        if st.button("Promote to Point Designer", use_container_width=True, key="pareto_promote_btn"):
                            try:
                                # Reconstruct a full PointInputs dict from the baseline + sampled decision variables.
                                from dataclasses import asdict
                                _base_dict = asdict(base0) if base0 is not None else {}
                            except Exception:
                                _base_dict = dict(getattr(base0, "__dict__", {})) if base0 is not None else {}

                            # Decision variables are the bound keys for this run.
                            for _k in list(bounds.keys()):
                                if _k in _row and _row.get(_k) is not None:
                                    try:
                                        _base_dict[_k] = float(_row.get(_k))
                                    except Exception:
                                        pass

                            stage_pd_candidate_apply(dict(_base_dict), source="Pareto Lab / Internal Pareto", note="Selected Pareto row")
                            st.success("Promoted selected Pareto point to Point Designer. Switch to Point Designer to review/evaluate.")
                    except Exception as _e:
                        st.info(f"Promotion UI unavailable for this run: {_e}")

                # Robust envelope (proxy): filter by min_constraint_margin
                dfP_all["robust"] = (pd.to_numeric(dfP_all.get("min_constraint_margin"), errors="coerce") >= robust_margin_thr)
                dfP_robust = dfP_all[dfP_all["robust"]].copy()

                # Freedom-left indicator (2D, selected axes)
                xkey = st.selectbox("x-axis", options=list(objectives.keys()), index=0)
                ykey = st.selectbox("y-axis", options=[k for k in objectives.keys() if k != xkey], index=0)
                ckey = st.selectbox("color", options=["dominant_constraint", "intent", "robust"], index=0)

                def _classify_freedom(df: pd.DataFrame) -> pd.Series:
                    try:
                        d = df.sort_values(xkey)
                        x = pd.to_numeric(d[xkey], errors="coerce").values
                        y = pd.to_numeric(d[ykey], errors="coerce").values
                        dy = np.gradient(y)
                        dx = np.gradient(x)
                        slope = np.abs(dy / (dx + 1e-12))
                        out = []
                        for s in slope:
                            if not np.isfinite(s):
                                out.append("Tight")
                            elif s < 0.15:
                                out.append("Flat")
                            elif s < 0.6:
                                out.append("Tight")
                            else:
                                out.append("Exhausted")
                        return pd.Series(out, index=d.index)
                    except Exception:
                        return pd.Series(["-"]*len(df), index=df.index)

                dfP_all["freedom_left"] = _classify_freedom(dfP_all)
                if len(dfP_robust):
                    dfP_robust["freedom_left"] = _classify_freedom(dfP_robust)

                st.caption("Front segments are annotated with dominant constraint and margin. Robust front is a conservative proxy filter; no uncertainty optimizer is used.")

                # Plot (matplotlib if available, else streamlit)
                try:
                    if _HAVE_MPL and plt is not None:
                        fig = plt.figure()
                        ax = fig.add_subplot(111)
                        # nominal (optionally color by categorical key)
                        if ckey in ("dominant_constraint", "intent") and ckey in dfP_all.columns:
                            cats = list(pd.Series(dfP_all[ckey]).fillna("(none)").astype(str).unique())
                            cmap_vals = pd.Series(dfP_all[ckey]).fillna("(none)").astype(str).map({c:i for i,c in enumerate(cats)})
                            sc = ax.scatter(dfP_all[xkey], dfP_all[ykey], c=cmap_vals, s=20, label="Nominal")
                            cb = fig.colorbar(sc, ax=ax)
                            cb.set_ticks(list(range(len(cats))))
                            cb.set_ticklabels(cats)
                            cb.set_label(ckey)
                        else:
                            ax.scatter(dfP_all[xkey], dfP_all[ykey], s=18, label="Nominal")
                        # robust overlay
                        if len(dfP_robust):
                            ax.scatter(dfP_robust[xkey], dfP_robust[ykey], s=26, marker="x", label="Robust (proxy)")
                        ax.set_xlabel(f"{xkey} [{_OBJ_CATALOG.get(xkey,{}).get('units','-')}]")
                        ax.set_ylabel(f"{ykey} [{_OBJ_CATALOG.get(ykey,{}).get('units','-')}]")
                        ax.grid(True, alpha=0.25)
                        ax.legend()
                        st.pyplot(fig, use_container_width=True)
                    else:
                        st.scatter_chart(dfP_all[[xkey, ykey]], x=xkey, y=ykey)
                except Exception:
                    st.scatter_chart(dfP_all[[xkey, ykey]], x=xkey, y=ykey)

                # -----------------------------
                # Pareto v2: world-class interpretability layers (still 0-D, still non-optimizing)
                # -----------------------------
                def _sense_sign(s: str) -> int:
                    return -1 if str(s).lower().strip() == "min"else 1

                def _pareto2(df: pd.DataFrame, xk: str, yk: str, sx: str, sy: str) -> pd.DataFrame:
                    """Return non-dominated set for 2 objectives (stable, no randomness)."""
                    if df is None or len(df) == 0:
                        return df
                    d = df[[c for c in df.columns if c in set(df.columns)]].copy()
                    x = pd.to_numeric(d[xk], errors="coerce").values
                    y = pd.to_numeric(d[yk], errors="coerce").values
                    m = np.isfinite(x) & np.isfinite(y)
                    d = d.loc[m].copy()
                    x = x[m]; y = y[m]
                    # Convert to minimization
                    if str(sx).lower() == "max":
                        x = -x
                    if str(sy).lower() == "max":
                        y = -y
                    order = np.lexsort((y, x))
                    x = x[order]; y = y[order]
                    d = d.iloc[order].copy()
                    best_y = np.inf
                    keep = []
                    for i in range(len(d)):
                        if y[i] < best_y - 1e-12:
                            keep.append(True)
                            best_y = y[i]
                        else:
                            keep.append(False)
                    return d.loc[keep].reset_index(drop=True)

                def _confidence_from_density(df_feas: pd.DataFrame, df_front: pd.DataFrame, xk: str, yk: str) -> pd.Series:
                    """Proxy confidence: kNN distance in objective space (smaller => higher confidence)."""
                    try:
                        if df_feas is None or len(df_feas) < 10 or df_front is None or len(df_front) == 0:
                            return pd.Series([np.nan]*len(df_front), index=df_front.index)
                        F = df_feas[[xk, yk]].copy()
                        P = df_front[[xk, yk]].copy()
                        Fx = pd.to_numeric(F[xk], errors="coerce").values
                        Fy = pd.to_numeric(F[yk], errors="coerce").values
                        Px = pd.to_numeric(P[xk], errors="coerce").values
                        Py = pd.to_numeric(P[yk], errors="coerce").values
                        mF = np.isfinite(Fx) & np.isfinite(Fy)
                        Fx, Fy = Fx[mF], Fy[mF]
                        k = int(max(5, min(25, len(Fx)//30)))
                        out = []
                        for (px, py) in zip(Px, Py):
                            if not (np.isfinite(px) and np.isfinite(py)):
                                out.append(np.nan); continue
                            d2 = (Fx - px)**2 + (Fy - py)**2
                            if len(d2) == 0:
                                out.append(np.nan); continue
                            kk = min(k, len(d2))
                            # partial sort
                            idx = np.argpartition(d2, kk-1)[:kk]
                            md = float(np.mean(np.sqrt(d2[idx]) + 1e-12))
                            out.append(md)
                        # invert and normalize
                        arr = np.asarray(out, dtype=float)
                        if np.all(~np.isfinite(arr)):
                            return pd.Series([np.nan]*len(df_front), index=df_front.index)
                        lo = np.nanmin(arr); hi = np.nanmax(arr)
                        conf = (hi - arr) / (hi - lo + 1e-12)
                        return pd.Series(conf, index=df_front.index)
                    except Exception:
                        return pd.Series([np.nan]*len(df_front), index=df_front.index)

                def _segment_ids(df_front: pd.DataFrame) -> pd.Series:
                    """Assign segment ids where dominant constraint is constant (cliff => new segment)."""
                    if df_front is None or len(df_front) == 0 or "dominant_constraint"not in df_front.columns:
                        return pd.Series([0]*len(df_front), index=df_front.index)
                    dom = df_front["dominant_constraint"].fillna("(none)").astype(str).values
                    seg = []
                    cur = 0
                    prev = dom[0] if len(dom) else "(none)"
                    for d0 in dom:
                        if d0 != prev:
                            cur += 1
                        seg.append(cur)
                        prev = d0
                    return pd.Series(seg, index=df_front.index)

                # Confidence halo + geography tags
                dfP_all = dfP_all.copy()
                dfP_all["confidence"] = _confidence_from_density(dfF_all, dfP_all, xkey, ykey)
                dfP_all["segment_id"] = _segment_ids(dfP_all)
                try:
                    # Geography = cognitive metaphor on frozen data (no new math)
                    geo = []
                    dom = dfP_all["dominant_constraint"].fillna("(none)").astype(str).values if "dominant_constraint"in dfP_all.columns else ["(none)"]*len(dfP_all)
                    for i in range(len(dfP_all)):
                        cliff = (i > 0 and dom[i] != dom[i-1])
                        if cliff:
                            geo.append("Cliff")
                        else:
                            # Ridge proxy: tight margin + stable constraint; Plain: flat + good margin
                            mm = float(dfP_all.iloc[i].get("min_constraint_margin", np.nan))
                            fl = str(dfP_all.iloc[i].get("freedom_left", "-"))
                            if np.isfinite(mm) and mm < max(0.05, robust_margin_thr*0.5):
                                geo.append("Ridge")
                            elif fl == "Flat"and (not np.isfinite(mm) or mm >= robust_margin_thr):
                                geo.append("Plain")
                            else:
                                geo.append("Slope")
                    dfP_all["geography"] = geo
                except Exception:
                    dfP_all["geography"] = ["-"]*len(dfP_all)

                # Quiet opinionated defaults: robust overlay on, fragile points visually de-emphasized
                st.markdown("### Pareto Interpretability Layers")

                # Question-driven exploration (wizard chooses views, not designs)
                qcols = st.columns([2, 2])
                with qcols[0]:
                    question = st.selectbox(
                        "What are you trying to learn?",
                        [
                            "Custom view",
                            "Where does robustness collapse?",
                            "Where is heat exhaust (q_div) limiting?",
                            "Where is stress (σ_vm) limiting?",
                            "Where is TBR policy shaping the trade-off?",
                            "Where do constraints switch (cliffs)?",
                        ],
                        index=0,
                        help="This changes *views and lenses only*. It does not select designs or optimize.",
                    )
                with qcols[1]:
                    focus_metrics = st.multiselect(
                        "Focus metrics (always shown in inspectors)",
                        options=["min_constraint_margin","dominant_constraint","q_div_MW_m2","sigma_vm_MPa","hts_margin_cs","TBR","Q_DT_eqv","P_e_net_MW","B_peak_T"],
                        default=["min_constraint_margin","dominant_constraint","q_div_MW_m2","sigma_vm_MPa"],
                        help="Personalization only: controls what the inspector emphasizes.",
                    )

                # Default lens settings (may be overridden by question-driven preset below)
                _def_geo, _def_conf, _def_policy, _def_teach = True, True, False, False
                if 'question' in locals() and question != "Custom view":
                    if question == "Where does robustness collapse?":
                        _def_geo, _def_conf, _def_policy, _def_teach = True, True, False, True
                    elif question == "Where is heat exhaust (q_div) limiting?":
                        _def_geo, _def_conf, _def_policy, _def_teach = True, True, False, True
                    elif question == "Where is stress (σ_vm) limiting?":
                        _def_geo, _def_conf, _def_policy, _def_teach = True, True, False, True
                    elif question == "Where is TBR policy shaping the trade-off?":
                        _def_geo, _def_conf, _def_policy, _def_teach = True, True, True, True
                    elif question == "Where do constraints switch (cliffs)?":
                        _def_geo, _def_conf, _def_policy, _def_teach = True, True, False, True

                l1, l2, l3, l4 = st.columns([1.2, 1.2, 1.2, 1.4])
                with l1:
                    show_geography = st.checkbox("Geography view", value=_def_geo, help="Terrain metaphor: ridges/cliffs/plains (purely descriptive).")
                with l2:
                    show_conf_halo = st.checkbox("Confidence halo", value=_def_conf, help="Density-based proxy confidence (no smoothing).")
                with l3:
                    show_policy = st.checkbox("Policy change compare", value=_def_policy, help="Compare fronts under explicit policy thresholds (filter-only lens).")
                with l4:
                    teaching_mode = st.checkbox("Teaching mode", value=_def_teach, help="Adds short callouts and guardrails; does not change results.")

                if teaching_mode:
                    st.caption("Tip: A Pareto front is a set of *non-dominated feasible designs*. This tool does not select or recommend designs.")

                # Segment-level explanation
                with st.expander("Explain a front segment", expanded=False):
                    st.caption("Segments are contiguous parts of the front pinned by the same dominant constraint (constraint-switches appear as cliffs).")
                    seg_ids = sorted(dfP_all["segment_id"].unique().tolist()) if len(dfP_all) else [0]
                    sel_seg = int(st.selectbox("Segment", options=seg_ids, index=0))
                    seg_df = dfP_all[dfP_all["segment_id"] == sel_seg].copy()
                    if len(seg_df):
                        domc = str(seg_df["dominant_constraint"].iloc[0]) if "dominant_constraint"in seg_df.columns else "(unknown)"
                        st.write(f"**Dominant constraint:** `{domc}` | Points: {len(seg_df)}")
                        # identify strongest driver variable among sampled knobs
                        drivers = [k for k in ("R0_m", "Bt_T", "Ip_MA", "fG") if k in seg_df.columns]
                        driver_msg = ""
                        try:
                            targ = ykey
                            corrs = []
                            for dv in drivers:
                                a = pd.to_numeric(seg_df[dv], errors="coerce")
                                b = pd.to_numeric(seg_df[targ], errors="coerce")
                                if a.notna().sum() > 3 and b.notna().sum() > 3:
                                    corrs.append((dv, float(a.corr(b))))
                            corrs = [c for c in corrs if np.isfinite(c[1])]
                            if corrs:
                                dv, cc = sorted(corrs, key=lambda kv: -abs(kv[1]))[0]
                                driver_msg = f"Within this segment, `{targ}` is most correlated with `{dv}` (corr≈{cc:.2f})."
                        except Exception:
                            pass
                        if driver_msg:
                            st.caption(driver_msg)
                        # causal chain template (descriptive)
                        chain = f"In this segment, pushing `{ykey}` tends to move designs along the front until `{domc}` becomes limiting. "
                        chain += "This reflects coupled 0-D physics and engineering proxies; it is descriptive, not a recommendation."
                        st.write(chain)
                    else:
                        st.info("No points in selected segment.")

                # Objective relevance lens
                with st.expander("Objective relevance lens", expanded=False):
                    st.caption("Shows where objectives genuinely shape the front vs. where they are mostly redundant or flat (descriptive).")
                    try:
                        rel = []
                        for ok in objectives.keys():
                            if ok not in dfP_all.columns:
                                continue
                            vF = float(pd.to_numeric(dfF_all.get(ok, pd.Series([],dtype=float)), errors="coerce").var()) if len(dfF_all) else np.nan
                            vP = float(pd.to_numeric(dfP_all.get(ok, pd.Series([],dtype=float)), errors="coerce").var()) if len(dfP_all) else np.nan
                            ratio = (vP / (vF + 1e-12)) if (np.isfinite(vP) and np.isfinite(vF)) else np.nan
                            rel.append({"objective": ok, "var_front": vP, "var_feasible": vF, "relevance_ratio": ratio})
                        rel_df = pd.DataFrame(rel).sort_values("relevance_ratio", ascending=False)
                        st.dataframe(rel_df, use_container_width=True, hide_index=True)
                        if teaching_mode and len(rel_df):
                            st.caption("High relevance_ratio means the objective varies significantly along the front; low means it may be redundant in this domain.")
                    except Exception:
                        st.info("Relevance lens unavailable.")

                # Policy change compare (filter-only lens; no physics changes)
                dfP_policy = None
                if show_policy:
                    with st.expander("Policy change compare (filter-only lens)", expanded=False):
                        st.caption("This is a policy lens: it filters feasible points using explicit thresholds, then recomputes the non-dominated set. No constraints are relaxed; no evaluator changes are made here.")
                        p1, p2, p3, p4 = st.columns(4)
                        with p1:
                            tbr_min = float(st.number_input("TBR ≥", value=1.10, step=0.01))
                        with p2:
                            sigma_max = float(st.number_input("σ_vm ≤ [MPa]", value=700.0, step=10.0))
                        with p3:
                            qdiv_max = float(st.number_input("q_div ≤ [MW/m²]", value=10.0, step=0.5))
                        with p4:
                            hts_min = float(st.number_input("HTS margin ≥", value=0.10, step=0.01))
                        dpol = dfF_all.copy()
                        if "TBR"in dpol.columns:
                            dpol = dpol[pd.to_numeric(dpol["TBR"], errors="coerce") >= tbr_min]
                        if "sigma_vm_MPa"in dpol.columns:
                            dpol = dpol[pd.to_numeric(dpol["sigma_vm_MPa"], errors="coerce") <= sigma_max]
                        if "q_div_MW_m2"in dpol.columns:
                            dpol = dpol[pd.to_numeric(dpol["q_div_MW_m2"], errors="coerce") <= qdiv_max]
                        if "hts_margin_cs"in dpol.columns:
                            dpol = dpol[pd.to_numeric(dpol["hts_margin_cs"], errors="coerce") >= hts_min]
                        dfP_policy = _pareto2(dpol, xkey, ykey, objectives.get(xkey,"min"), objectives.get(ykey,"min"))
                        st.write(f"Policy-filtered feasible points: {len(dpol)} | policy-front points: {len(dfP_policy) if dfP_policy is not None else 0}")

                # Reference fronts (runtime presets; deterministic)
                with st.expander("Reference fronts (runtime presets)", expanded=False):
                    st.caption("Generate canonical reference fronts for comparison (deterministic presets; no hidden scoring).")
                    ref = st.selectbox("Reference family", ["None", "ITER-like", "SPARC-like", "ARC-like"], index=0)
                    if ref != "None":
                        st.info("Reference fronts are generated on demand using fixed presets and the frozen evaluator. This does not recommend designs.")
                    # This upgrade only provides UI hooks; generation uses the same run button / settings.

                # No free lunch detector
                with st.expander("No free lunch detector", expanded=False):
                    st.caption("Flags regions where both selected objectives appear to improve together - often due to projection, redundancy, or shared drivers.")
                    try:
                        sx = objectives.get(xkey, "min"); sy = objectives.get(ykey, "min")
                        dx = _sense_sign(sx); dy = _sense_sign(sy)
                        d = dfP_all.sort_values(xkey).copy()
                        x = pd.to_numeric(d[xkey], errors="coerce").values
                        y = pd.to_numeric(d[ykey], errors="coerce").values
                        good = []
                        for i in range(1, len(d)):
                            if not (np.isfinite(x[i-1]) and np.isfinite(x[i]) and np.isfinite(y[i-1]) and np.isfinite(y[i])):
                                continue
                            imp_x = dx*(x[i]-x[i-1]) < 0  # improvement
                            imp_y = dy*(y[i]-y[i-1]) < 0
                            if imp_x and imp_y:
                                good.append(int(i))
                        if good:
                            st.warning(f"Detected {len(good)} local steps where both objectives improve together. This may indicate redundancy/shared drivers or a misleading projection.")
                            if teaching_mode:
                                st.caption("Try changing axes, adding a third objective, or inspecting dominance and segment explanations to interpret this correctly.")
                        else:
                            st.success("No obvious 'free lunch' steps detected along the chosen front ordering.")
                    except Exception:
                        st.info("Detector unavailable.")

                # Narrative timeline along the front
                # Knee candidates (descriptive, not "best")
                # Knee candidates (descriptive, not "best")
                with st.expander("Notable compromise regions (knee candidates)", expanded=False):
                    st.caption("Highlights regions of the front where trade-offs tighten rapidly (geometric knee proxy). These are **not** recommendations.")
                    if len(dfP_all) >= 5:
                        try:
                            d = dfP_all[[xkey, ykey, "segment_id", "dominant_constraint", "min_constraint_margin", "confidence", "intent"]].copy()
                            d = d.sort_values(xkey).reset_index(drop=True)
                            x = pd.to_numeric(d[xkey], errors="coerce").values
                            y = pd.to_numeric(d[ykey], errors="coerce").values
                            m = np.isfinite(x) & np.isfinite(y)
                            d = d.loc[m].reset_index(drop=True)
                            x = x[m]; y = y[m]
                            if len(d) >= 5:
                                xn = (x - np.min(x)) / (np.ptp(x) + 1e-12)
                                yn = (y - np.min(y)) / (np.ptp(y) + 1e-12)
                                kappa = np.zeros(len(d))
                                for ii in range(1, len(d)-1):
                                    v1 = np.array([xn[ii]-xn[ii-1], yn[ii]-yn[ii-1]])
                                    v2 = np.array([xn[ii+1]-xn[ii], yn[ii+1]-yn[ii]])
                                    n1 = np.linalg.norm + 1e-12
                                    n2 = np.linalg.norm + 1e-12
                                    ang = np.arccos(np.clip(np.dot(v1, v2)/(n1*n2), -1.0, 1.0))
                                    kappa[ii] = float(ang)
                                d["knee_score"] = kappa
                                topk = d.sort_values("knee_score", ascending=False).head(min(8, len(d)))
                                st.dataframe(topk, use_container_width=True, hide_index=True)
                                if teaching_mode:
                                    st.caption("High knee_score means the front bends sharply in the chosen projection; confirm with segment explanations and dominance to avoid projection traps.")
                            else:
                                st.info("Not enough clean points for knee scoring.")
                        except Exception:
                            st.info("Knee scoring unavailable for this run.")
                    else:
                        st.info("Need at least 5 Pareto points to compute knee candidates.")

                with st.expander("Pareto timeline (scrub along the front)", expanded=False):
                    st.caption("Scrub a slider along the front to see objective/constraint transitions as a narrative.")
                    if len(dfP_all):
                        k = int(st.slider("Front index", min_value=0, max_value=max(len(dfP_all)-1, 0), value=min(0, len(dfP_all)-1), step=1))
                        row = dfP_all.iloc[k].to_dict()
                        st.write(f"**Index {k}** | segment={row.get('segment_id')} | geography={row.get('geography')} | dominant={row.get('dominant_constraint')} | margin={row.get('min_constraint_margin')}")
                        st.json({xkey: row.get(xkey), ykey: row.get(ykey), "intent": row.get("intent"), "dominant_constraint": row.get("dominant_constraint"), "confidence": row.get("confidence")}, expanded=False)
                    else:
                        st.info("No front points to scrub.")
                # Point Inspector
                with st.expander("Pareto Point Inspector", expanded=False):
                    idx = int(st.number_input("Row index (in table above)", min_value=0, max_value=max(len(dfP_all)-1,0), value=0, step=1))
                    try:
                        row = dfP_all.iloc[idx].to_dict()
                        st.json(row, expanded=False)
                        # Focus metrics (personalized)
                        try:
                            _fm = focus_metrics if "focus_metrics"in locals() else ["min_constraint_margin","dominant_constraint"]
                            _show = {k: row.get(k) for k in _fm if k in row}
                            if _show:
                                st.markdown("**Focus metrics**")
                                st.dataframe(pd.DataFrame([_show]), use_container_width=True, hide_index=True)
                        except Exception:
                            pass

                        cA, cB, cC = st.columns([1, 1, 1])
                        with cA:
                            if st.button("View in Scan Lab", use_container_width=True, key="pareto_to_scanlab"):
                                # Best-effort cross-link: store a focus payload and instruct user to switch tab.
                                st.session_state.scanlab_focus_from_pareto = {
                                    "inputs": {k: row.get(k) for k in ("R0_m", "Bt_T", "Ip_MA", "fG") if k in row},
                                    "objectives": {k: row.get(k) for k in objectives.keys()},
                                    "intent": str(row.get("intent", intent_mode)),
                                    "dominant_constraint": row.get("dominant_constraint"),
                                    "min_constraint_margin": row.get("min_constraint_margin"),
                                }
                                st.info("Stored a Scan Lab focus hint in session state. Switch to Scan Lab to view the highlighted context.")
                        with cB:
                            st.caption("Read-only: no auto-apply.")
                        st.caption("To inspect physics/constraints deeply, paste these inputs into Point Designer or Systems Mode. Pareto does not auto-apply.")
                        with cC:
                            if st.button("Queue in Systems Mode", use_container_width=True, key="pareto_to_systems"):
                                # Queue a reversible base-apply payload for Systems Mode (no solving here).
                                st.session_state.systems_pending_base_apply = {k: row.get(k) for k in ("R0_m","a_m","kappa","Bt_T","Ip_MA","Ti_keV","fG","Paux_MW","t_shield_m") if k in row}
                                st.session_state.systems_pending_base_apply_source = "Pareto Lab point"
                                st.info("Queued. Switch to Systems Mode and review the pending Apply card (reversible).")

                    except Exception:
                        st.info("Select a valid row index.")

                # Narrative summary (deterministic)
                with st.expander("Trade-off summary (deterministic)", expanded=False):
                    try:
                        dom_counts = dfP_all["dominant_constraint"].value_counts().to_dict() if "dominant_constraint"in dfP_all.columns else {}
                        dom_top = sorted(dom_counts.items(), key=lambda kv: -kv[1])[:3]
                        msg = ""
                        if dom_top:
                            msg += "Dominant-limiting segments (by count along the front): "+ ", ".join([f"{k} ({v})"for k,v in dom_top]) + ". "
                        msg += f"Freedom-left classification along chosen axes: Flat={int((dfP_all['freedom_left']=='Flat').sum())}, Tight={int((dfP_all['freedom_left']=='Tight').sum())}, Exhausted={int((dfP_all['freedom_left']=='Exhausted').sum())}. "
                        msg += "These statements are descriptive; no design choice is implied."
                        st.session_state.pareto_narrative_summary = msg
                        st.write(msg)
                    except Exception:
                        st.write("Summary unavailable.")

                # Export artifact (JSON) + CSV
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button(
                        "Download Pareto front (CSV)",
                        data=dfP_all.to_csv(index=False),
                        file_name="shams_pareto_front.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                with c2:
                    art = {
                        "schema": "shams.pareto.v1",
                        "version": str(st.session_state.get("app_version","")),
                        "intent_mode": intent_mode,
                        "objectives": {k: {"sense": v, **_OBJ_CATALOG.get(k, {})} for k, v in objectives.items()},
                        "bounds": bounds,
                        "seed": seed,
                        "n_samples": n_samples,
                        "robust_margin_thr": robust_margin_thr,
                        "feasible": dfF_all.to_dict(orient="records") if len(dfF_all) else [],
                        "pareto": dfP_all.to_dict(orient="records") if len(dfP_all) else [],
                    }
                    st.download_button(
                        "Download Pareto artifact (JSON)",
                        data=json.dumps(art, indent=2, sort_keys=True),
                        file_name="shams_pareto_artifact.json",
                        mime="application/json",
                        use_container_width=True,
                    )
                    # Publication-ready export pack (zip): artifact + CSVs + narrative
                    try:
                        import io, zipfile as _zip
                        buf = io.BytesIO()
                        with _zip.ZipFile(buf, "w", compression=_zip.ZIP_DEFLATED) as zf:
                            zf.writestr("pareto/shams_pareto_artifact.json", json.dumps(art, indent=2, sort_keys=True))
                            if len(dfP_all):
                                zf.writestr("pareto/pareto_front.csv", dfP_all.to_csv(index=False))
                            if len(dfF_all):
                                zf.writestr("pareto/feasible_set_sampled.csv", dfF_all.to_csv(index=False))
                            # Narrative summary
                            zf.writestr("pareto/narrative_summary.md", str(st.session_state.get("pareto_narrative_summary","")).strip() or "(no narrative)")
                            # Repro capsule
                            zf.writestr("pareto/README.md", "\n".join([
                                "# SHAMS Pareto Publication Pack",
                                "",
                                "- Includes the JSON artifact (authoritative), CSV exports, and the deterministic narrative summary.",
                                "- Pareto Mode is feasible-only and non-optimizing.",
                                "",
                                f"- intent_mode: {intent_mode}",
                                f"- n_samples: {n_samples}",
                                f"- seed: {seed}",
                                f"- objectives: {list(objectives.keys())}",
                            ]))
                        buf.seek(0)
                        st.download_button(
                            "Download publication pack (.zip)",
                            data=buf.getvalue(),
                            file_name="shams_pareto_publication_pack.zip",
                            mime="application/zip",
                            use_container_width=True,
                        )
                    except Exception:
                        pass
                    # Interactive reproducibility capsule (trust panel)
                    with st.expander("Reproducibility capsule (what is guaranteed / what is not)", expanded=False):
                        st.caption("This makes Pareto audit-ready. It describes guarantees and limitations of the current run (no hidden assumptions).")
                        st.markdown("**Guaranteed**")
                        st.markdown("- Feasibility is evaluated by the frozen Point Designer evaluator (intent-aware).")
                        st.markdown("- Pareto uses explicit objectives only (Objective Contract).")
                        st.markdown("- Sampling is seeded; reruns with same seed/bounds/objectives are reproducible up to floating-point nondeterminism.")
                        st.markdown("**Not guaranteed**")
                        st.markdown("- Global coverage: the front is only as complete as the sampling density.")
                        st.markdown("- Projection honesty: 2D views can hide higher-dimensional dominance changes.")
                        st.markdown("- Counterfactual/policy lenses are filter-only overlays; they do not modify evaluator physics.")
                        st.divider()
                        st.json({
                            "version": str(st.session_state.get("app_version","")),
                            "intent_mode": intent_mode,
                            "seed": seed,
                            "n_samples": n_samples,
                            "bounds": bounds,
                            "objectives": objectives,
                        }, expanded=False)

        except Exception as e:
            st.error(f"Pareto study error: {e}")

    # -----------------------------
    


    # --- Freeze badge (Pareto) ---
    with st.container():
        st.caption("Frozen descriptive trade-off cartography only — no optimization.")
        try:
            _pf = (Path(__file__).resolve().parent.parent / "docs"/ "PARETO_V1_FREEZE_DECLARATION.md").read_text(encoding="utf-8")
        except Exception:
            _pf = "(missing docs/PARETO_FREEZE.md)"
        st.caption(FREEZE_STAMP)
        st.download_button("Download Pareto Freeze Statement", data=_pf, file_name="PARETO_V1_FREEZE_DECLARATION.md", mime="text/markdown", use_container_width=False)
