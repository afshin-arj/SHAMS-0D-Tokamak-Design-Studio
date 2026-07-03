"""Reactor Design Forge deck -- extracted from ui/app.py (UI redesign batch 7).

Both original `if _deck == "Reactor Design Forge":` blocks (main UI + the
stateful multi-point operating-envelope check) are merged into this single
function, preserving execution order. Pure move + cosmetic de-emoji. No
physics, constraint, solver, evaluator, session-state key, or routing-ID
changes. Namespace bridge (including app.py's __file__) keeps path
computations and bare names resolving as before. Temporary tech debt; replace
with explicit imports/ctx in a later cleanup commit.
"""
from __future__ import annotations
import streamlit as st
import sys


def render_reactor_design_forge(_app_module) -> None:
    _g = globals()
    for _k, _v in vars(_app_module).items():
        if not _k.startswith('__'):
            _g[_k] = _v
    _g['__file__'] = _app_module.__file__

    st.header("Reactor Design Forge")
    st.caption("Concept assembly + candidate archives + traces. Feeds the frozen evaluator; does not replace it.")
    render_mode_scope("forge")

    # --- Legacy v93 stateful download compatibility (read-only) ---
    try:
        _v93_stateful_sandbox_panel()
    except Exception:
        pass

    st.subheader("Forge Bridgehead")
    # v208: Review Mode (review-room posture; no knobs/search actions)
    if "forge_review_mode"not in st.session_state:
        st.session_state["forge_review_mode"] = False
    st.session_state["forge_review_mode"] = st.toggle(
        "Review Mode (locks exploration controls)",
        value=bool(st.session_state.get("forge_review_mode")),
        key="forge_review_mode_toggle",
        help="Review Mode is a UI posture: inputs are locked; only review artifacts and comparisons are shown.",
    )

    if bool(st.session_state.get("forge_review_mode")):
        st.info(
            f"{_LANG.get('non_prescriptive_banner')}  \
{_LANG.get('margin_first')}",
        )
    else:
        st.caption("Candidate-generation workspace (external to truth): global pattern → surrogate acceleration → local refinement. All candidates are audited by the frozen evaluator. No relaxation; no auto-apply.")
    st.info(
        "Non-authoritative workspace: this mode produces **candidate archives** + **traces**. "
        "Truth remains in the frozen evaluator. Nothing is applied automatically.",
    )

    # v208: Review Mode locks exploration controls (read-only review posture).
    forge_lock = bool(st.session_state.get("forge_review_mode"))

    # --- Forge deck (no scroll walls) ---
    _forge_deck = st.radio(
        "Forge deck",
        options=["Intent Compiler", "Machine Finder", "Capsules"],
        index=0,
        horizontal=True,
        key="forge_deck",
        help="Deck-based navigation: render one Forge workspace at a time (no scroll walls).",
    )


    # --- Imports (local to keep UI start-up fast) ---
    from src.models.inputs import PointInputs
    from constraints.system import build_constraints_from_outputs
    from tools.process_compat.process_compat import (
        constraints_to_records,
        active_constraints,
        feasibility_flag,
        failure_mode,
    )
    from tools.sandbox.hybrid_engine import (
        Objective, VarSpec, run_hybrid_machine_finder,
        global_de_phase, surrogate_phase, local_refine_phase, surface_surf_phase,
        build_archive, resistance_atlas, variable_correlations, build_feasibility_skeleton,
    )
    from tools.sandbox.optimizer_engines import default_objective_packs
    from tools.sandbox.feasibility_ladder import classify_candidate
    from tools.sandbox.resistance_report import build_resistance_report
    from tools.sandbox.persistence import save_run_capsule_v2
    from tools.sandbox.export_capsule import export_run_capsule_zip
    from tools.sandbox.export_capsule import import_run_capsule_zip
    from tools.sandbox.persistence import load_run_capsule_v2, diff_capsules
    from tools.sandbox.advanced_features import constraint_surface_map
    from tools.sandbox.conflict_atlas import new_atlas, update_atlas, summarize_atlas
    from tools.sandbox.design_navigation import steering_cues_from_surface_map, filter_cues
    from tools.sandbox.lineage_graph import build_lineage_edges, compute_tree_layout
    from tools.sandbox.spend_map import build_spend_scatter
    from tools.sandbox.robustness_envelope import robustness_envelope_from_records
    from tools.sandbox.narrative_pack import build_narrative
    from tools.sandbox.design_card import build_design_card_md
    from tools.sandbox.existence_report import existence_report
    from tools.sandbox.archive_intelligence import ladder_histogram, regime_clusters_summary
    from tools.sandbox.confidence_sweep import confidence_sweep
    from tools.sandbox.design_packet import build_design_packet_files
    from tools.sandbox.review_room import build_review_trinity, build_attack_simulation

    # v203 Reactor Design Forge: PROCESS-independence instruments
    from tools.sandbox.closure_console import closure_console
    from tools.sandbox.margin_budget import margin_budget
    from tools.sandbox.reality_gates import reality_gates
    from tools.sandbox.report_pack import build_report_pack


    from src.economics.cost import cost_proxies
    # Tier 5–6 instruments
    from tools.sandbox.tier56 import (
        ConstraintCred,
        apply_credibility_overlay,
        counterfactual_gate,
        build_intent_trajectory,
        why_not_report,
        discovered_relations,
        export_relations_markdown,
        inverse_design_residual,
    )

    # Tier 7 + Epistemic guarantees (collaboration + standards)
    from tools.sandbox.tier7 import (
        repo_fingerprint,
        candidate_fingerprint,
        generate_cert_badge_svg,
        export_doi_ready_pack,
        new_review_session,
        default_sessions_dir,
        save_review_session,
        load_review_session,
        export_review_session_zip,
        import_review_session_zip,
        run_regression_suite,
    )

    # Tier 8–9: design-space jurisprudence, intent-conditional laws, genealogy, counter-optimization
    from tools.sandbox.tier89 import (
        feasibility_confidence_from_trace,
        candidate_verdict,
        region_verdict,
        intent_conditional_laws,
        reconstruct_genealogy,
        counter_optimization_report,
    )

    

    # -------------------------
    # Intent Compiler (v285.0)
    # -------------------------
    if _forge_deck == "Intent Compiler":
        st.markdown("### Intent Compiler")
        st.caption("Deterministic algebraic compilation from intent → candidate PointInputs. Produces candidates only; truth remains in Point Designer.")

        try:
            from tools.sandbox.intent_compiler import compile_intent_to_candidate
        except Exception as _e:
            st.error(f"Intent compiler import failed: {_e}")
            compile_intent_to_candidate = None  # type: ignore

        # Use last Point Designer inputs as base if available
        _base_obj = st.session_state.get('pd_last_inputs_obj')
        if _base_obj is None:
            _base_obj = st.session_state.get('base_point_inputs_obj')
        if not isinstance(_base_obj, PointInputs):
            # fall back to a safe, minimal default
            _base_obj = PointInputs(R0_m=3.0, a_m=1.0, kappa=1.8, Bt_T=12.0, Ip_MA=8.0, Ti_keV=10.0, fG=0.8, Paux_MW=20.0)

        c1, c2 = st.columns(2)
        Pfus = c1.number_input('Target fusion power P_fus (MW)', value=140.0, step=10.0, min_value=0.0)
        Q = c2.number_input('Target Q (proxy)', value=2.0, step=0.1, min_value=0.01)

        st.markdown('**Optional direct overrides (applied after compilation)**')
        o1, o2, o3, o4 = st.columns(4)
        o_R0 = o1.number_input('Override R0 (m) (0=ignore)', value=0.0, step=0.1)
        o_a  = o2.number_input('Override a (m) (0=ignore)', value=0.0, step=0.05)
        o_Bt = o3.number_input('Override Bt (T) (0=ignore)', value=0.0, step=0.5)
        o_Ip = o4.number_input('Override Ip (MA) (0=ignore)', value=0.0, step=0.5)

        overrides = {}
        if o_R0 > 0: overrides['R0_m'] = float(o_R0)
        if o_a  > 0: overrides['a_m']  = float(o_a)
        if o_Bt > 0: overrides['Bt_T'] = float(o_Bt)
        if o_Ip > 0: overrides['Ip_MA'] = float(o_Ip)

        if st.button('Compile candidate', type='primary', use_container_width=True, disabled=(compile_intent_to_candidate is None)):
            status, payload = compile_intent_to_candidate(_base_obj, Pfus_target_MW=float(Pfus), Q_target=float(Q), overrides=overrides)
            st.session_state['forge_intent_compiler_last'] = {'status': status, **payload}

        last = st.session_state.get('forge_intent_compiler_last')
        if isinstance(last, dict):
            st.info(f"Compiler status: **{last.get('status','?')}**")
            if last.get('reason'):
                st.error(str(last.get('reason')))
            if last.get('trace'):
                with st.expander('Compilation trace', expanded=False):
                    for ln in list(last.get('trace') or []):
                        st.markdown(f"- {ln}")
            cand = last.get('candidate_inputs')
            if isinstance(cand, dict):
                with st.expander('Candidate inputs (dict)', expanded=False):
                    st.json(cand)
                if st.button('Apply candidate in Point Designer', use_container_width=True):
                    st.session_state['pd_candidate_apply'] = dict(cand)
                    st.success('Candidate applied: go to "Point Designer"and press Evaluate.')

        # End Intent Compiler deck

# -------------------------
    # Replay / Diff (capsules)
    # -------------------------
    if _forge_deck == "Capsules":
        with st.expander("Replay & Diff — Run Capsules", expanded=False):
            st.caption("Load a previously exported Optimization Run Capsule (.zip or .json) to restore the Workbench. "
                       "This is metadata replay; truth remains the frozen evaluator.")
    
            c1, c2 = st.columns(2)
            up1 = c1.file_uploader("Restore capsule", type=["zip", "json"], key="opt_restore_capsule")
            if up1 is not None:
                try:
                    # zip capsule
                    if str(up1.name).lower().endswith(".zip"):
                        tmp = Path(".shams_state") / "_uploads"
                        tmp.mkdir(parents=True, exist_ok=True)
                        p = tmp / str(up1.name)
                        p.write_bytes(up1.getbuffer())
                        data = import_run_capsule_zip(p)
                        capsule = data.get("capsule") or {}
                    else:
                        capsule = json.loads(up1.getvalue().decode("utf-8"))
                    if str(capsule.get("schema")) != "shams.opt_sandbox.run_capsule.v2":
                        st.error(f"Unsupported capsule schema: {capsule.get('schema')}")
                    else:
                        st.session_state["opt_workbench_run"] = {
                            "kind": "optimization_sandbox_replay",
                            "intent": capsule.get("intent"),
                            "seed": capsule.get("seed", 1),
                            "objectives": capsule.get("lens", {}).get("objectives", []),
                            "var_specs": capsule.get("var_specs", []),
                            "budgets": {"bounds": capsule.get("bounds", {})},
                            "archive": capsule.get("archive", []),
                            "trace": capsule.get("trace", []),
                            "telemetry": capsule.get("telemetry", {}),
                            "resistance_report": capsule.get("resistance_report"),
                            "capsule_v2": capsule,
                            "non_authoritative_notice": "Replayed from capsule. Truth remains the frozen evaluator.",
                        }
                        st.success("Capsule restored into the Workbench.")
                except Exception as e:
                    st.error(f"Failed to restore capsule: {e}")
    
            st.markdown("---")
            st.caption("Diff two capsules (lens/bounds/counts/ladder histogram).")
            upA = c1.file_uploader("Capsule A", type=["json"], key="opt_diff_a")
            upB = c2.file_uploader("Capsule B", type=["json"], key="opt_diff_b")
            if upA is not None and upB is not None:
                try:
                    ca = json.loads(upA.getvalue().decode("utf-8"))
                    cb = json.loads(upB.getvalue().decode("utf-8"))
                    d = diff_capsules(ca, cb)
                    st.json(d)
                except Exception as e:
                    st.error(f"Diff failed: {e}")
    
        st.stop()

    # -------------------------
    # Evaluator (frozen truth)
    # -------------------------
    def _evaluate_candidate(inp: dict, intent: str) -> dict:
        """Audit a candidate with frozen evaluator. Returns a rich dict for archive/trace."""
        # Build PointInputs (fills defaults and validates)
        pi = PointInputs(**inp)
        outputs = _ui_evaluate(pi, origin="audit_candidate")
        cons = build_constraints_from_outputs(outputs, design_intent=intent)
        records = constraints_to_records(cons)
        feas = feasibility_flag(records, design_intent=intent)
        act = active_constraints(records, design_intent=intent)
        fm = failure_mode(records, design_intent=intent)
        # compute min margin
        min_sm = None
        for r in records:
            try:
                sm = float(r.get("signed_margin"))
            except Exception:
                continue
            if min_sm is None or sm < min_sm:
                min_sm = sm
        # optional cost proxies (pure outputs->cost)
        cost = cost_proxies(outputs) if isinstance(outputs, dict) else {}
        closure_bundle = closure_console(outputs=outputs, cost_proxy=cost) if isinstance(outputs, dict) else {"ok": False, "reason": "outputs_not_dict"}
        mb = margin_budget(records)
        rg = reality_gates(records, closure_bundle if isinstance(closure_bundle, dict) else None)
        rp = build_report_pack(intent=str(intent), inputs=dict(inp), outputs=outputs, constraints=records, closure_bundle=closure_bundle if isinstance(closure_bundle, dict) else None, margin_budget=mb, reality_gates=rg)

        return {
            "inputs": dict(inp),
            "outputs": outputs,
            "constraints": records,
            "feasible": bool(feas),
            "active_constraints": act,
            "failure_mode": fm,
            "min_signed_margin": float(min_sm) if min_sm is not None else float("nan"),
            "cost": cost,
            "closure_bundle": closure_bundle,
            "margin_budget": mb,
            "reality_gates": rg,
            "report_pack": rp,
            "closure_certificate": (rp.get("json") or {}).get("closure_certificate"),
            "design_class": (rp.get("json") or {}).get("design_class"),
            "citation_blocks": (rp.get("json") or {}).get("citation_blocks"),
            "reference_context": (rp.get("json") or {}).get("reference_context"),

        }

    # -------------------------
    # Guided runs (user friendly)
    # -------------------------
    st.markdown("### Intent & Lens (explicit contract)")
    st.caption("Pick a goal pack; SHAMS will *show the exact objectives and bounds* before running.")

    # Intent selection
    intent_label = st.selectbox("Design intent", ["Power Reactor (net-electric)", "Experimental Device (research)"], index=0, key="opt_intent")

    # Internal canonical intent key (feeds constraint policy)
    intent = "Reactor"if intent_label.lower().startswith("power") else "Research"

    # Objective packs (explicit)
    packs = default_objective_packs(intent)
    pack_names = [p.name for p in packs] + ["Custom (manual objectives)"]
    pack_choice = st.selectbox("Objective pack", pack_names, index=0, key="opt_pack_choice")

    # Anchor: either current Point Designer inputs (if available) or a sensible baseline
    anchor_default = {}
    if "point_inputs_last"in st.session_state and isinstance(st.session_state["point_inputs_last"], dict):
        anchor_default = dict(st.session_state["point_inputs_last"])
    # fallback: minimal anchor (PointInputs will fill defaults)
    if not anchor_default:
        anchor_default = {"R0_m": 6.2, "a_m": 2.0, "kappa": 1.8, "delta": 0.33, "Bt_T": 5.3, "Ip_MA": 15.0, "Paux_MW": 50.0}

    # Choose variables + bounds (table-style)
    st.markdown("### Degrees of Freedom (search space)")
    st.caption("You control what the machine finder is allowed to change. Frozen variables never move.")

    default_vars = ["R0_m", "Bt_T", "Ip_MA", "Paux_MW"]
    all_keys = list(anchor_default.keys())
    # Add common knobs even if absent
    for k in ["R0_m","a_m","kappa","delta","Bt_T","Ip_MA","Paux_MW","nbar_1e20_m3","Ti_keV"]:
        if k not in all_keys:
            all_keys.append(k)

    var_keys = st.multiselect("Variables to optimize", options=all_keys, default=default_vars, key="opt_var_keys")
    st.caption("Tip: start with 3–5 variables for stability; expand later.")

    # Bounds helper
    bound_mode = st.radio("Bounds mode", ["Tight (±10%)", "Medium (±20%)", "Wide (±35%)", "Custom"], index=1, horizontal=True, key="opt_bound_mode")
    frac = {"Tight (±10%)":0.10, "Medium (±20%)":0.20, "Wide (±35%)":0.35}.get(bound_mode, 0.20)

    bounds = {}
    for k in var_keys:
        v0 = float(anchor_default.get(k, 0.0))
        if bound_mode != "Custom":
            lo, hi = v0*(1-frac), v0*(1+frac)
        else:
            lo, hi = v0*(1-0.2), v0*(1+0.2)
        bounds[k] = (lo, hi)

    with st.expander("Edit bounds (table)", expanded=False):
        cols = st.columns([2,2,2])
        cols[0].markdown("**Variable**")
        cols[1].markdown("**Min**")
        cols[2].markdown("**Max**")
        for k in var_keys:
            lo, hi = bounds[k]
            c1, c2, c3 = st.columns([2,2,2])
            c1.write(k)
            lo2 = c2.number_input(f"{k}_lo", value=float(lo), key=f"b_lo_{k}")
            hi2 = c3.number_input(f"{k}_hi", value=float(hi), key=f"b_hi_{k}")
            if hi2 < lo2:
                hi2 = lo2
            bounds[k] = (float(lo2), float(hi2))

    # Objectives display + custom editor
    if pack_choice != "Custom (manual objectives)":
        pack = next(p for p in packs if p.name == pack_choice)
        objectives = [Objective(**o.__dict__) for o in pack.objectives]
        st.info(f"**Pack:** {pack.description}")
    else:
        st.caption("Custom objectives: add 1–3 objectives. Sense: max/min. Weight: explicit.")
        obj_rows = st.number_input("Number of objectives", 1, 3, 2, key="opt_n_obj")
        objectives = []
        for i in range(int(obj_rows)):
            c1, c2, c3 = st.columns([3,1,1])
            key = c1.text_input(f"Objective {i+1} key", value=["P_e_net_MW","Q_DT_eqv","q_div_MW_m2"][i] if i<3 else "Q_DT_eqv", key=f"obj_key_{i}")
            sense = c2.selectbox(f"Sense {i+1}", ["max","min"], index=0, key=f"obj_sense_{i}")
            weight = c3.number_input(f"Weight {i+1}", value=1.0, key=f"obj_w_{i}")
            objectives.append(Objective(key=key, sense=sense, weight=float(weight)))


    # Program Lens (objective contract) - explicit, exported (no hidden ranking)
    lens_contract = {
        "name": str(pack_choice),
        "description": str(pack.description) if pack_choice != "Custom (manual objectives)"else "Custom objectives (manual)",
        "intent": str(intent),
        "objectives": [{"key": o.key, "sense": o.sense, "weight": float(o.weight)} for o in (objectives or [])],
    }
    st.session_state["opt_lens_contract"] = lens_contract

    # Optional costing layer
    st.markdown("### Transparent costing layer (optional)")
    use_cost = st.checkbox("Enable cost proxies in objectives/filters (transparent)", value=False, key="opt_use_cost")
    if use_cost:
        st.caption("Cost proxies are computed from outputs; assumptions are explicit and exported with the run.")

    # Budgets / engine tuning (simple)
    st.markdown("### Run budget (fast-first → deeper)")
    cA,cB,cC,cD = st.columns(4)
    pop_size = cA.number_input("Pop size", 20, 200, 64, key="opt_pop")
    generations = cB.number_input("Global generations", 5, 200, 40, key="opt_gens")
    surrogate_rounds = cC.number_input("Surrogate rounds", 0, 30, 6, key="opt_surr")
    local_steps = cD.number_input("Local steps", 0, 300, 70, key="opt_local")
    archive_topk = st.slider("Archive size (top-k diverse)", 20, 200, 60, key="opt_topk")

    # Guardrails
    st.markdown("### Guardrails (feasibility governance)")
    min_margin = st.number_input("Require min signed margin ≥ (optional)", value=0.0, step=0.01, key="opt_min_margin")
    require_feasible_only = st.checkbox("Archive: keep feasible only (recommended)", value=True, key="opt_feas_only")

    # Advanced capabilities (Tier 1–4)
    st.markdown("### Advanced instruments (Tier 1–4)")
    c1, c2, c3 = st.columns(3)
    enable_surface = c1.checkbox("Constraint-surface surfing", value=True, key="opt_adv_surface")
    enable_skeleton = c2.checkbox("Feasibility skeleton", value=True, key="opt_adv_skeleton")
    enable_memory = c3.checkbox("Active learning across runs (opt-in)", value=False, key="opt_adv_memory")
    c4, c5 = st.columns(2)
    enable_multi_intent = c4.checkbox("Track distance to the other Intent", value=False, key="opt_adv_multi_intent")
    staged = c5.checkbox("Staged run (human-in-the-loop phases)", value=False, key="opt_adv_staged")
    if staged:
        st.caption("Staged run executes phases one-by-one (Global → Surrogate → Local → Surf). Useful for steering and learning.")

    # Build an evaluator closure for this panel so post-run instruments (cartography/UQ)
    # can reuse it even when the UI reruns.
    def _make_eval_fn():
        def _fn(cand_inputs: dict):
            res = _evaluate_candidate(cand_inputs, intent=intent)
            # Expose cost proxies as objective keys (transparent, explicit)
            try:
                if isinstance(res.get("outputs"), dict) and isinstance(res.get("cost"), dict):
                    for ck, cv in res["cost"].items():
                        if ck not in res["outputs"]:
                            res["outputs"][ck] = cv
            except Exception:
                pass

            # Multi-intent instrumentation (distance-to-other)
            if enable_multi_intent:
                other_intent = "Research"if str(intent) == "Reactor"else "Reactor"
                try:
                    oth = _evaluate_candidate(cand_inputs, intent=other_intent)
                    oth_v = 0.0
                    for rr in (oth.get("constraints") or []):
                        try:
                            sm = float(rr.get("signed_margin", float("nan")))
                            if sm < 0:
                                oth_v += (-sm)
                        except Exception:
                            continue
                    res["other_intent"] = other_intent
                    res["other_feasible"] = bool(oth.get("feasible", False))
                    res["other_violation"] = float(oth_v)
                    res["other_min_signed_margin"] = float(oth.get("min_signed_margin", float("nan")))
                    res["other_failure_mode"] = oth.get("failure_mode")
                except Exception:
                    pass

            # Guardrails (do not change evaluator truth; mark infeasible for archive filtering)
            if min_margin and float(min_margin) > 0:
                try:
                    if float(res.get("min_signed_margin", float("nan"))) < float(min_margin):
                        res["feasible"] = False
                        res["failure_mode"] = res.get("failure_mode") or "min_margin_guardrail"
                except Exception:
                    pass
            return res
        return _fn

    eval_fn = _make_eval_fn()

    # Run control
    run_now = st.button("Run machine finder", type="primary", use_container_width=True, key="opt_run_button")

    if run_now:
        # Build VarSpecs
        var_specs = [VarSpec(key=k, lo=bounds[k][0], hi=bounds[k][1]) for k in var_keys]
        budgets = {
            "pop_size": int(pop_size),
            "generations": int(generations),
            "surrogate_rounds": int(surrogate_rounds),
            "propose_per_round": 36,
            "local_steps": int(local_steps),
            "archive_topk": int(archive_topk),
            "resistance_window": 250,
            "enable_surface_surf": bool(enable_surface),
            "enable_skeleton": bool(enable_skeleton),
            "use_knowledge_store": bool(enable_memory),
        }
        if staged:
            # Human-in-the-loop staged run (no background execution): phases are executed
            # one at a time and stored in session_state.
            st.session_state["opt_stage_state"] = {
                "intent": intent,
                "anchor": dict(anchor_default),
                "var_specs": [v.__dict__ for v in var_specs],
                "objectives": [o.__dict__ for o in objectives],
                "budgets": dict(budgets),
                "all_points": [],
                "trace": [],
                "done": {"global": False, "surrogate": False, "local": False, "surf": False},
                "seed": 1,
            }
            st.info("Staged run initialized. Use the phase controls below in the Workbench.")
            run = None
        else:
            run = run_hybrid_machine_finder(
                evaluate_fn=eval_fn,
                intent=intent,
                anchor_inputs=anchor_default,
                var_specs=var_specs,
                objectives=objectives,
                budgets=budgets,
                seed=1,
            )

        if isinstance(run, dict):
            # Post-filter archive if requested
            if require_feasible_only:
                run["archive"] = [a for a in run.get("archive", []) if a.get("feasible", False)]

            # vNext: rebuild archive with diversity + dominance annotation (explicit objectives)
            try:
                run["archive"] = build_archive(run.get("archive", []) or [], var_specs, topk=int(archive_topk), objectives=objectives)
            except Exception:
                pass

            # vNext: feasibility ladder classification (archive + trace)
            try:
                for c in (run.get("archive") or []):
                    c.update(classify_candidate(c, dominant=bool(c.get("is_dominant", False))))
                for t in (run.get("trace") or []):
                    t.update(classify_candidate(t))
            except Exception:
                pass

            # vNext: resistance report (descriptive)
            try:
                lens_contract = st.session_state.get("opt_lens_contract") or {}
                bounds_dict = {k: list(bounds[k]) for k in var_keys if k in bounds}
                var_specs_dicts = [v.__dict__ for v in var_specs]
                run["resistance_report"] = build_resistance_report(
                    trace=run.get("trace") or [],
                    archive=run.get("archive") or [],
                    intent=intent,
                    lens_contract=lens_contract,
                    bounds=bounds_dict,
                    var_specs=var_specs_dicts,
                )
            except Exception:
                pass

            st.session_state["opt_workbench_run"] = run
            st.success("Run complete. Workbench updated below.")

    # -------------------------
    # Post-run Workbench
    # -------------------------
    stage_state = st.session_state.get("opt_stage_state")
    run = st.session_state.get("opt_workbench_run")

    # If staged run is active, provide phase controls and build a live workbench run view
    if stage_state is not None and isinstance(stage_state, dict):
        st.markdown("---")
        st.markdown("## Forge Workbench (Staged run)")
        st.caption("Execute phases one-by-one. Nothing runs in the background.")

        # Rehydrate
        _intent = stage_state.get("intent")
        _anchor = stage_state.get("anchor") or {}
        _seed = int(stage_state.get("seed", 1))
        _var_specs = [VarSpec(**v) for v in (stage_state.get("var_specs") or [])]
        _objectives = [Objective(**o) for o in (stage_state.get("objectives") or [])]
        _budgets = stage_state.get("budgets") or {}

        done = stage_state.get("done") or {}
        ph1, ph2, ph3, ph4 = st.columns(4)
        if ph1.button("Run Global", use_container_width=True, disabled=forge_lock or bool(done.get("global"))):
            pts, tr = global_de_phase(
                evaluate_fn=eval_fn,
                anchor_inputs=_anchor,
                var_specs=_var_specs,
                objectives=_objectives,
                pop_size=int(_budgets.get("pop_size", 64)),
                generations=int(_budgets.get("generations", 40)),
                seed=_seed,
            )
            stage_state["all_points"] = (stage_state.get("all_points") or []) + pts
            stage_state["trace"] = (stage_state.get("trace") or []) + tr
            stage_state["done"]["global"] = True
            st.session_state["opt_stage_state"] = stage_state
            st.success("Global phase complete.")
        if ph2.button("Run Surrogate", use_container_width=True, disabled=forge_lock or (not bool(done.get("global")) or bool(done.get("surrogate")))):
            pts, tr = surrogate_phase(
                evaluate_fn=eval_fn,
                anchor_inputs=_anchor,
                var_specs=_var_specs,
                objectives=_objectives,
                seed=_seed,
                history=list(stage_state.get("all_points") or []),
                rounds=int(_budgets.get("surrogate_rounds", 6)),
                propose_per_round=int(_budgets.get("propose_per_round", 36)),
            )
            stage_state["all_points"] = (stage_state.get("all_points") or []) + pts
            stage_state["trace"] = (stage_state.get("trace") or []) + tr
            stage_state["done"]["surrogate"] = True
            st.session_state["opt_stage_state"] = stage_state
            st.success("Surrogate phase complete.")
        if ph3.button("Run Local", use_container_width=True, disabled=forge_lock or (not bool(done.get("global")) or bool(done.get("local")))):
            pts, tr = local_refine_phase(
                evaluate_fn=eval_fn,
                anchor_inputs=_anchor,
                var_specs=_var_specs,
                objectives=_objectives,
                seed=_seed,
                seeds=list(stage_state.get("all_points") or []),
                steps=int(_budgets.get("local_steps", 70)),
            )
            stage_state["all_points"] = (stage_state.get("all_points") or []) + pts
            stage_state["trace"] = (stage_state.get("trace") or []) + tr
            stage_state["done"]["local"] = True
            st.session_state["opt_stage_state"] = stage_state
            st.success("Local phase complete.")
        if ph4.button("Run Surf", use_container_width=True, disabled=forge_lock or (not bool(done.get("local")) or bool(done.get("surf")))):
            pts, tr = surface_surf_phase(
                evaluate_fn=eval_fn,
                anchor_inputs=_anchor,
                var_specs=_var_specs,
                objectives=_objectives,
                seed=_seed,
                seeds=list(stage_state.get("all_points") or []),
                steps=int(_budgets.get("surf_steps", 80)),
            )
            stage_state["all_points"] = (stage_state.get("all_points") or []) + pts
            stage_state["trace"] = (stage_state.get("trace") or []) + tr
            stage_state["done"]["surf"] = True
            st.session_state["opt_stage_state"] = stage_state
            st.success("Surf phase complete.")

        # Build a live run view from staged state
        _archive = build_archive(list(stage_state.get("all_points") or []), _var_specs, topk=int(_budgets.get("archive_topk", 60)))
        _trace = list(stage_state.get("trace") or [])
        _resist = resistance_atlas(_trace, last_n=int(_budgets.get("resistance_window", 250)))
        _corr = variable_correlations(_archive, _var_specs)
        _skel = build_feasibility_skeleton(_archive, _var_specs) if enable_skeleton else None
        run = {
            "kind": "optimization_sandbox_hybrid_run_staged",
            "intent": str(_intent),
            "seed": int(_seed),
            "objectives": [o.__dict__ for o in _objectives],
            "var_specs": [v.__dict__ for v in _var_specs],
            "budgets": dict(_budgets),
            "archive": _archive,
            "trace": _trace,
            "resistance": _resist,
            "variable_correlations": _corr,
            "feasibility_skeleton": _skel,
        }
        st.session_state["opt_workbench_run"] = run

    if isinstance(run, dict) and run.get("archive") is not None:
        st.markdown("---")
        st.markdown("## Forge Workbench")

        # -------------------------
        # Run Dashboard (workflow view)
        # -------------------------
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            st.markdown("**Run Contract**")
            st.write({
                "intent": run.get("intent"),
                "lens": (run.get("capsule_v2") or {}).get("lens", st.session_state.get("opt_lens_contract")),
                "seed": run.get("seed"),
            })
        with d2:
            st.markdown("**Live Trace**")
            tr = run.get("trace") or []
            n_t = len(tr)
            n_f = sum(1 for t in tr if bool(t.get("feasible", False)))
            st.write({"n_evaluated": int(n_t), "n_feasible": int(n_f)})
            # top failure mode snapshot
            fm = {}
            for t in tr[-250:]:
                k = str(t.get("failure_mode") or "")
                if not k:
                    continue
                fm[k] = fm.get(k, 0) + 1
            if fm:
                top = sorted(fm.items(), key=lambda x: x[1], reverse=True)[:3]
                st.caption("Recent failure modes")
                st.write({k: int(v) for k, v in top})
        with d3:
            st.markdown("**Candidate Archive**")
            ar = run.get("archive") or []
            n_a = len(ar)
            n_af = sum(1 for a in ar if bool(a.get("feasible", False)))
            n_dom = sum(1 for a in ar if bool(a.get("is_dominant", False)))
            st.write({"n_archive": int(n_a), "n_feasible": int(n_af), "n_dominant": int(n_dom)})
        with d4:
            st.markdown("**Resistance**")
            rr = run.get("resistance_report")
            if isinstance(rr, dict):
                topb = rr.get("primary_blockers") or rr.get("blockers") or []
                if isinstance(topb, list) and topb:
                    st.write({"top_blocker": topb[0].get("name", topb[0]) if isinstance(topb[0], dict) else topb[0]})
                else:
                    st.write("(no blockers reported)")
            else:
                st.write("(no resistance report)")

        # Budget allocation (transparent scheduler)
        ba = run.get("budget_allocation")
        if isinstance(ba, dict):
            with st.expander("Budget allocation (feasibility-first scheduler)", expanded=False):
                st.json(ba)

        # Conflict atlas (accumulates across runs in-session)
        rr = run.get("resistance_report")
        if "opt_conflict_atlas"not in st.session_state or not isinstance(st.session_state.get("opt_conflict_atlas"), dict):
            st.session_state["opt_conflict_atlas"] = new_atlas()
        if isinstance(rr, dict):
            try:
                st.session_state["opt_conflict_atlas"] = update_atlas(st.session_state["opt_conflict_atlas"], rr)
            except Exception:
                pass
        with st.expander("Conflict atlas (across runs, descriptive)", expanded=False):
            st.caption("Accumulated from Resistance Reports. Descriptive only - not causal, not prescriptive.")
            rows = summarize_atlas(st.session_state.get("opt_conflict_atlas") or {}, top_n=25)
            if rows:
                import pandas as _pd
                st.dataframe(_pd.DataFrame(rows), use_container_width=True)
            else:
                st.info("No conflicts accumulated yet. Run optimization at least once.")
            st.download_button(
                "Download conflict atlas (json)",
                data=json.dumps(st.session_state.get("opt_conflict_atlas") or {}, indent=2, sort_keys=True),
                file_name="shams_opt_conflict_atlas.json",
                mime="application/json",
                use_container_width=True,
                key="opt_dl_conflict_atlas",
            )

        # vNext: Run capsule (v2) + resistance report (descriptive, exportable)
        with st.expander("Run capsule + resistance report (export)", expanded=False):
            lens_contract = st.session_state.get("opt_lens_contract") or {}
            rr = run.get("resistance_report")
            if isinstance(rr, dict):
                st.caption("Resistance report (descriptive)")
                st.json(rr, expanded=False)
            else:
                st.info("Resistance report not available for this run.")

            if st.button("Build capsule zip (v2)", use_container_width=True, key="opt_build_capsule_zip"):
                try:
                    import time, os, json
                    run_id = f"run_{int(time.time())}"
                    settings = {
                        "bounds": {k: list(v) for k, v in (st.session_state.get("opt_bounds") or {}).items()} if isinstance(st.session_state.get("opt_bounds"), dict) else {},
                        "var_specs": run.get("var_specs") or [],
                        "objectives": run.get("objectives") or [],
                    }
                    evaluator_hash = str(run.get("fingerprint") or "")
                    cap_path = save_run_capsule_v2(
                        run,
                        run_id=run_id,
                        settings=settings,
                        evaluator_hash=evaluator_hash,
                        archive=run.get("archive") or [],
                        trace=run.get("trace") or [],
                        lens_contract=lens_contract,
                        resistance_report=rr if isinstance(rr, dict) else None,
                    )
                    # Also export a compact zip with manifest
                    from pathlib import Path
                    out_zip = Path(cap_path).with_suffix(".zip")
                    export_run_capsule_zip(
                        capsule=json.loads(Path(cap_path).read_text(encoding="utf-8")),
                        archive={"schema":"shams.opt_sandbox.archive_snapshot.v1","archive": run.get("archive") or []},
                        resistance_report=rr if isinstance(rr, dict) else None,
                        out_path=out_zip,
                    )
                    st.session_state["opt_capsule_zip_bytes"] = out_zip.read_bytes()
                    st.session_state["opt_capsule_zip_name"] = out_zip.name
                    st.success("Capsule zip built.")
                except Exception as e:
                    st.error(f"Capsule build failed: {e}")

            if st.session_state.get("opt_capsule_zip_bytes") is not None:
                st.download_button(
                    "Download capsule zip",
                    data=st.session_state["opt_capsule_zip_bytes"],
                    file_name=str(st.session_state.get("opt_capsule_zip_name","opt_capsule.zip")),
                    mime="application/zip",
                    use_container_width=True,
                    key="opt_dl_capsule_zip",
                )

        # Sticky truth bar (simple CSS)
        st.markdown(
            """
            <style>
            div[data-testid="stVerticalBlock"] div:has(> div.shams-sticky) { position: sticky; top: 0; z-index: 999; background: white; }
            .shams-sticky { border: 1px solid rgba(49,51,63,0.15); padding: 10px; border-radius: 10px; }
            </style>
            """,
            unsafe_allow_html=True
        )

        best = run.get("best_feasible")
        feas_rate = run.get("resistance", {}).get("feasible_rate")
        dom = run.get("resistance", {}).get("dominant_constraints", {})
        dom_top = sorted(dom.items(), key=lambda kv: kv[1], reverse=True)[:1]
        dom_txt = dom_top[0][0] if dom_top else "-"

        with st.container():
            st.markdown('<div class="shams-sticky">', unsafe_allow_html=True)
            t1,t2,t3,t4,t5 = st.columns([1,1,1,1,2])
            t1.metric("Intent", run.get("intent","-"))
            t2.metric("Feasible rate (recent)", f"{(float(feas_rate)*100.0):.1f}%"if feas_rate is not None else "-")
            # Keep score strictly labeled as non-authoritative (legacy search utility).
            t3.metric("Archive score (non-authoritative)", f"{float(best.get('_score')):.3g}"if isinstance(best, dict) else "-")
            t4.metric("Archive size", str(len(run.get("archive") or [])))
            t5.write(f"**Dominant resistance:** {dom_txt}")
            st.markdown('</div>', unsafe_allow_html=True)

        left, center, right = st.columns([1.2, 2.2, 1.4], vertical_alignment="top")

        # LEFT: nav/setup for post-run views
        with left:
            st.markdown("### Navigate")

            # v206: reduce scrolling fatigue for experts by using a searchable selectbox
            # and a "Cockpit mode"that keeps the most-used instruments on one screen.
            cockpit_mode = st.toggle(
                "Forge Cockpit Mode",
                value=True,
                help="Compact, low-scroll layout for experts. Keeps the core instruments together.",
                key="rdf_cockpit_mode",
                disabled=forge_lock,
            )
            if forge_lock:
                cockpit_mode = True

            _views_core = [
                "Casebook",
                "Candidate Archive",
                "Forge Timeline",
                "Machine Dossier",
                "Review Trinity",
                "Attack Simulation",
                "Resistance Brief",
                "Scan ↔ Forge Grounding",
                "Conflict Atlas",
                "Boundary Navigator",
                "Constraint Spend Map",
                "Reactor Accounting Console",
                "Margin Ledger",
                "Reality Gates",
                "Closure Certificate",
                "Provenance Graph",
                "Engineering Reality Budget",
                "Failure-Mode Canon",
                "Design Class",
                "Citation Blocks",
                "Reference Reproduction",
                "Economics Deck",
                "Robustness Envelope",
                "Design Narrative",
                "Design Card",
                "Design Packet",
                "Confidence Sweep",
                "Expert Compare (no ranking)",
                "Exposure Readiness",
                "Epistemic Gap Map",
                "Constraint Personas",
                "Design Genealogy",
                "Do‑Not‑Build Brief",
                "Process of Elimination",
                "Paper‑Ready Signals",
                "Silence Mode"
                "Sensitivity Fingerprint",
                "Reviewer Packet"
            ]
            _views_full = _views_core + [
                "Archive regimes & coverage",
                "Machine existence report",
                "Design navigation (steering)",
                "Pareto (if multi-objective)",
                "Report Pack",
                "Trace Telemetry",
                "Feasibility skeleton",
                "Local cartography (adaptive)",
                "Uncertainty (Monte Carlo)",
                "Intent trajectories (Research→Reactor)",
                "Inverse design / Why not?",
                "Discovered relations (laws)",
                "Counterfactual lens",
                "PROCESS parity benchmarks",
                "Parity validation packs (PASS/WARN/FAIL)",
                "Parity calibration (reference deltas)",
                "Decision scenarios (program lens)",
                "Collaboration (review sessions)",
                "Epistemic guarantees (regression suite)",
                "Standards & DOI export",
                "Design-space verdicts (Allowed/Forbidden)",
                "Epistemic confidence bounds",
                "Intent-conditional design laws",
                "Machine genealogy",
                "Counter-optimization (no interior optimum)",
                "Reproducibility",
            ]

            _views = _views_core if cockpit_mode else _views_full
            _default_view = st.session_state.get("opt_view") or ("Review Trinity"if forge_lock else "Casebook")
            if _default_view not in _views:
                _default_view = "Review Trinity"if forge_lock else "Casebook"
            view = st.selectbox(
                "Main view",
                options=_views,
                index=int(_views.index(_default_view)),
                key="opt_view",
                help="Type to search. Cockpit mode shows the core instruments first.",
            )

            # Back-compat: keep internal handlers stable while we improve naming for fusion experts.
            _view_alias = {
                "Casebook": "Casebook Runner",
                "Candidate Archive": "Archive Bay",
                "Forge Timeline": "Timeline Strip",
                "Review Trinity": "Review Trinity",
                "Attack Simulation": "Attack Simulation",
                "Scan ↔ Forge Grounding": "Scan ↔ Forge Grounding",
                "Exposure Readiness": "Exposure Readiness",
            }
            view = _view_alias.get(str(view), str(view))
            st.markdown("### Archive filters")
            only_robust = st.checkbox("Keep only margin≥0", value=False, key="opt_filter_robust")
            min_score = st.number_input("Min score (optional)", value=float("-inf"), key="opt_filter_minscore")
            if use_cost:
                st.markdown("### Cost filter")
                max_coe = st.number_input("Max COE proxy (optional)", value=float("inf"), key="opt_filter_coe")



            # ------------------------------
            # Review Bench (Compare Tray)
            # ------------------------------
            with st.expander("Review Bench (compare tray)", expanded=False):
                st.caption("Pin a handful of candidates for side-by-side review. Descriptive only - no ranking.")

                # Current candidate (filtered archive index)
                _cur = None
                try:
                    if filt:
                        _i = int(st.session_state.get("opt_inspect_idx", 0) or 0)
                        _i = max(0, min(len(filt)-1, _i))
                        _cur = filt[_i]
                except Exception:
                    _cur = None

                if "opt_review_bench"not in st.session_state or not isinstance(st.session_state.get("opt_review_bench"), list):
                    st.session_state["opt_review_bench"] = []

                cA, cB = st.columns([1,1])
                with cA:
                    if st.button("Pin current candidate", use_container_width=True, key="opt_pin_current"):
                        if _cur is None:
                            st.warning("No current candidate to pin.")
                        else:
                            try:
                                _fid = candidate_fingerprint(_cur)
                            except Exception:
                                _fid = f"idx:{int(st.session_state.get('opt_inspect_idx',0) or 0)}"
                            # avoid duplicates
                            if not any(str(x.get("id")) == str(_fid) for x in st.session_state["opt_review_bench"]):
                                inp = _cur.get("inputs") or {}
                                out = _cur.get("outputs") or {}
                                st.session_state["opt_review_bench"].append({
                                    "id": str(_fid),
                                    "idx": int(st.session_state.get("opt_inspect_idx", 0) or 0),
                                    "R0_m": inp.get("R0_m"),
                                    "Bt_T": inp.get("Bt_T"),
                                    "Ip_MA": inp.get("Ip_MA"),
                                    "P_e_net_MW": out.get("P_e_net_MW"),
                                    "Pfus_total_MW": out.get("Pfus_total_MW"),
                                    "first_failure": _cur.get("first_failure"),
                                    "min_signed_margin": _cur.get("min_signed_margin"),
                                })
                                st.success("Pinned.")
                            else:
                                st.info("Already pinned.")
                with cB:
                    if st.button("Clear bench", use_container_width=True, key="opt_clear_bench"):
                        st.session_state["opt_review_bench"] = []
                        st.success("Cleared.")

                bench = st.session_state.get("opt_review_bench") or []
                if bench:
                    import pandas as _pd
                    dfb = _pd.DataFrame(bench)
                    st.dataframe(dfb, use_container_width=True, hide_index=True)

                    # Exports
                    csv_bytes = dfb.to_csv(index=False).encode("utf-8")
                    st.download_button("Download Review Bench (CSV)", data=csv_bytes, file_name="review_bench.csv", mime="text/csv", use_container_width=True)
                    md = "|"+ "|".join(dfb.columns) + "|\n"
                    md += "|"+ "|".join(["---"]*len(dfb.columns)) + "|\n"
                    for _, r in dfb.iterrows():
                        md += "|"+ "|".join(str(r[c]) for c in dfb.columns) + "|\n"
                    st.download_button("Download Review Bench (Markdown)", data=md.encode("utf-8"), file_name="review_bench.md", mime="text/markdown", use_container_width=True)
                else:
                    st.info("Bench is empty. Pin 2–5 candidates during review.")

            # ------------------------------
            # Tier 5–6 controls (integrated)
            # ------------------------------
            with st.expander("Tier 5–6 instruments (optional)", expanded=False):
                st.caption(
                    "These are advanced instruments that PROCESS cannot provide. "
                    "They never modify frozen truth; they add explanatory lenses and workflows."
                )

                # Counterfactual constraint gate
                st.markdown("**Counterfactual gate (hypothetical)**")
                st.caption("Disable a constraint only in the feasibility *gate* for analysis. Raw constraints remain unchanged.")
                _all_names = []
                try:
                    if (run.get("archive") or []) and (run.get("archive")[0].get("constraints") or []):
                        _all_names = [str(r.get("name")) for r in (run.get("archive")[0].get("constraints") or []) if r.get("name")]
                        _all_names = sorted(list(dict.fromkeys(_all_names)))
                except Exception:
                    _all_names = []
                disabled_cons = st.multiselect(
                    "Disable constraints (hypothetical)",
                    options=_all_names,
                    default=[],
                    key="opt_cf_disable",
                )

                # Credibility overlay
                st.markdown("**Constraint credibility overlay**")
                st.caption("Optional epistemic lens: maturity/uncertainty adjusts *displayed* margins and filters. Does not change feasibility truth.")
                use_cred = st.checkbox("Enable credibility overlay", value=False, key="opt_use_cred")
                cred_map = {}
                if use_cred and _all_names:
                    # Keep a small editable set (top 8 by occurrence in archive)
                    top = _all_names[:8]
                    for nm in top:
                        c1,c2,c3 = st.columns([2,1,1])
                        with c1:
                            st.write(nm)
                        with c2:
                            mat = st.slider(f"maturity_{nm}", 0.0, 1.0, 0.7, 0.05, key=f"cred_m_{nm}")
                        with c3:
                            unc = st.slider(f"uncertainty_{nm}", 0.0, 0.5, 0.10, 0.01, key=f"cred_u_{nm}")
                        cred_map[nm] = ConstraintCred(name=nm, maturity=float(mat), uncertainty_frac=float(unc), conservative=True)
                # Persist for center/inspector usage
                st.session_state["opt_cred_map"] = {
                    k: {"name": v.name, "maturity": float(v.maturity), "uncertainty_frac": float(v.uncertainty_frac), "conservative": bool(v.conservative)}
                    for k, v in cred_map.items()
                }

                # Trajectory settings
                st.markdown("**Intent trajectories**")
                st.caption("Build a simple Research→Reactor highway from the current archive (and current variable list).")
                traj_steps = st.slider("Max path steps", 2, 10, 5, key="opt_traj_steps")
                if st.button("Build trajectory", use_container_width=True, key="opt_traj_build"):
                    st.session_state["opt_traj"] = None
                    try:
                        # Use current archive (pre-filter) to keep it deterministic
                        cands = run.get("archive") or []
                        st.session_state["opt_traj"] = build_intent_trajectory(
                            evaluate_fn=_evaluate_candidate,
                            candidates=cands,
                            var_keys=var_keys,
                            from_intent="Research",
                            to_intent="Reactor",
                            k_steps=int(traj_steps),
                            seed=int(run.get("seed", 0)),
                        )
                    except Exception as _e:
                        st.session_state["opt_traj"] = {"ok": False, "reason": str(_e)}

                # Inverse design target capture (used in center view)
                st.markdown("**Inverse design targets**")
                st.caption("Define desired outputs; SHAMS finds the closest feasible candidate *within your declared bounds*. No relaxation.")
                inv_cols = st.columns(2)
                inv_k = inv_cols[0].text_input("Target key", value="P_e_net_MW", key="opt_inv_key")
                inv_v = inv_cols[1].number_input("Target value", value=500.0, key="opt_inv_val")
                st.session_state["opt_inv_targets"] = {str(inv_k): float(inv_v)}

        archive = run.get("archive") or []
        # Apply filters
        filt = []
        for a in archive:
            if only_robust and float(a.get("min_signed_margin", float("nan"))) < 0:
                continue
            if float(a.get("_score", -1e30)) < float(min_score):
                continue
            if use_cost:
                coe = (a.get("cost") or {}).get("COE_proxy")
                if coe is not None and float(coe) > float(max_coe):
                    continue
            filt.append(a)

        # -------------------------
        # v206: expert signals (descriptive)
        # -------------------------
        def _regime_signature(_cand: dict) -> list:
            """Fusion-expert friendly regime tags (descriptive only)."""
            tags = []
            inp = _cand.get("inputs") or {}
            out = _cand.get("outputs") or {}

            def _get_num(d, k):
                try:
                    v = d.get(k)
                    return None if v is None else float(v)
                except Exception:
                    return None

            R0 = _get_num(inp, "R0_m") or _get_num(out, "R0_m")
            a = _get_num(inp, "a_m") or _get_num(out, "a_m")
            Ip = _get_num(inp, "Ip_MA") or _get_num(out, "Ip_MA")
            B0 = _get_num(inp, "B0_T") or _get_num(out, "B0_T") or _get_num(out, "Bt_T")
            Pf = _get_num(out, "Pfus_total_MW")

            # Geometry regime
            if R0 is not None:
                if R0 < 2.5:
                    tags.append("compact")
                elif R0 > 6.0:
                    tags.append("large-R")
            if R0 is not None and a is not None and a > 0:
                A = R0 / a
                if A < 2.2:
                    tags.append("spherical")
                elif A > 3.2:
                    tags.append("high-aspect")

            # Field/current regimes (heuristic, descriptive)
            if B0 is not None:
                if B0 >= 10.0:
                    tags.append("high-field")
                elif B0 <= 4.0:
                    tags.append("low-field")
            if Ip is not None:
                if Ip >= 12.0:
                    tags.append("high-current")

            # Power density proxy
            if Pf is not None and R0 is not None and R0 > 0:
                pd = Pf / (R0 ** 3)
                if pd >= 20.0:
                    tags.append("power-dense")

            # Feasibility state
            fs = _cand.get("feasibility_state")
            if fs:
                tags.append(str(fs).replace("feasible_", ""))
            return tags[:8]

        def _first_kill(_cand: dict) -> dict:
            """Return the tightest constraint (first-kill) from margin ledger rows."""
            mb = _cand.get("margin_budget") or {}
            rows = mb.get("rows") or []
            if not rows:
                return {"name": _cand.get("first_failure") or _cand.get("failure_mode") or "-", "signed_margin": _cand.get("min_signed_margin")}
            best = None
            for r in rows:
                try:
                    sm = float(r.get("signed_margin"))
                except Exception:
                    continue
                if best is None or sm < best[0]:
                    best = (sm, r)
            if best is None:
                return {"name": _cand.get("first_failure") or "-", "signed_margin": _cand.get("min_signed_margin")}
            rr = best[1]
            return {"name": rr.get("name") or rr.get("constraint") or "-", "signed_margin": float(best[0])}

        def _constraint_spend_rate(_cand: dict) -> dict:
            """Local heuristic: margin change per objective change vs parent (if lineage exists)."""
            pid = _cand.get("parent_id") or _cand.get("parent")
            if not pid:
                return {"ok": False, "reason": "no parent link"}
            parent = None
            for c in (run.get("archive") or []):
                if (c.get("_id") or c.get("fingerprint")) == pid:
                    parent = c
                    break
            if parent is None:
                return {"ok": False, "reason": "parent not found in archive"}

            # choose one objective if available
            obj = None
            lens = run.get("lens") or {}
            objs = lens.get("objectives") if isinstance(lens, dict) else None
            if isinstance(objs, list) and objs:
                obj = objs[0].get("key") if isinstance(objs[0], dict) else None
            if not obj:
                obj = "P_e_net_MW"if "P_e_net_MW"in (_cand.get("outputs") or {}) else None
            if not obj:
                return {"ok": False, "reason": "no objective key"}

            def _val(c, key):
                try:
                    return float((c.get("outputs") or {}).get(key))
                except Exception:
                    return None

            d_obj = None
            c_obj = _val(_cand, obj)
            p_obj = _val(parent, obj)
            if c_obj is not None and p_obj is not None:
                d_obj = c_obj - p_obj

            try:
                d_m = float(_cand.get("min_signed_margin")) - float(parent.get("min_signed_margin"))
            except Exception:
                d_m = None

            if d_obj is None or d_m is None or abs(d_obj) < 1e-12:
                return {"ok": False, "reason": "insufficient delta"}

            return {
                "ok": True,
                "objective": obj,
                "delta_objective": d_obj,
                "delta_min_margin": d_m,
                "margin_spend_per_objective": (d_m / d_obj),
                "note": "Local heuristic vs parent only (descriptive).",
            }

        # --- v208: Scan ↔ Forge grounding (descriptive topology context) ---
        def _scan_grounding(_cand: dict, _scan_artifact: dict, *, intent: str) -> dict:
            """Attach nearest-point scan context to a candidate (descriptive only)."""
            try:
                art = _scan_artifact or {}
                rep = (art.get("report") or {}) if isinstance(art, dict) else {}
                pts = rep.get("points") or []
                xk = rep.get("x_key"); yk = rep.get("y_key")
                if not pts or not xk or not yk:
                    return {"ok": False, "reason": "scan artifact missing points/x_key/y_key"}
                cin = _cand.get("inputs") or {}
                if xk not in cin or yk not in cin:
                    return {"ok": False, "reason": "candidate lacks scan axes", "x_key": xk, "y_key": yk}
                cx = float(cin.get(xk)); cy = float(cin.get(yk))
                best = None
                best_d = None
                for p in pts:
                    try:
                        dx = float(p.get("x")) - cx
                        dy = float(p.get("y")) - cy
                        d = (dx*dx + dy*dy) ** 0.5
                    except Exception:
                        continue
                    if best is None or (best_d is not None and d < best_d) or (best_d is None):
                        best = p; best_d = d
                if best is None:
                    return {"ok": False, "reason": "no valid scan points"}
                it = str(intent or "Reactor")
                it_sum = ((best.get("intent") or {}).get(it) if isinstance(best.get("intent"), dict) else None) or {}
                top = ((rep.get("topology") or {}).get(it) if isinstance(rep.get("topology"), dict) else None) or {}
                return {
                    "ok": True,
                    "scan_id": (rep.get("id") or art.get("report_hash") or art.get("artifact_hash")),
                    "x_key": xk,
                    "y_key": yk,
                    "candidate_xy": {"x": cx, "y": cy},
                    "nearest": {
                        "i": int(best.get("i", -1)),
                        "j": int(best.get("j", -1)),
                        "x": float(best.get("x")),
                        "y": float(best.get("y")),
                        "robustness": it_sum.get("robustness"),
                        "dominant_blocking": it_sum.get("dominant_blocking"),
                        "min_blocking_margin": it_sum.get("min_blocking_margin"),
                    },
                    "distance": float(best_d) if best_d is not None else None,
                    "topology": top,
                    "note": "Descriptive grounding only. Does not modify evaluator truth.",
                }
            except Exception as e:
                return {"ok": False, "reason": f"grounding_error: {e}"}

        # CENTER: main canvas
        with center:
            st.markdown("### Canvas")

            # v208: Margin-first framing (always-on summary for the inspected candidate)
            try:
                if filt:
                    _i = int(st.session_state.get("opt_inspect_idx", 0) or 0)
                    _i = max(0, min(len(filt) - 1, _i))
                    _c = filt[_i]
                    _mb = _c.get("margin_budget")
                    if not isinstance(_mb, dict):
                        _mb = margin_budget(_c.get("constraints") or [])
                        _c["margin_budget"] = _mb
                    _rows = _mb.get("rows") or []
                    _tight = []
                    for r in _rows:
                        if isinstance(r, dict) and r.get("name"):
                            _tight.append(r)
                    _tight = sorted(_tight, key=lambda rr: float(rr.get("margin_frac", 1e30) or 1e30))[:5]
                    with st.expander(f"{_LANG.get('margin_first')}", expanded=False if forge_lock else False):
                        c1,c2,c3 = st.columns(3)
                        c1.metric("Min signed margin", str(_c.get("min_signed_margin")))
                        c2.metric("Dominant resistance", str(_c.get("first_failure") or _c.get("failure_mode") or "-"))
                        c3.metric("Feasible", str(bool(_c.get("feasible"))))
                        if _tight:
                            st.write({str(r.get("name")): r.get("margin_frac") for r in _tight})
            except Exception:
                pass

            # v206: dedicated Conflict Atlas view (also shown in the right rail in cockpit mode)
            if view == "Conflict Atlas":
                st.caption("Constraint Conflict Atlas (descriptive, accumulated across runs).")
                rows = summarize_atlas(st.session_state.get("opt_conflict_atlas") or {}, top_n=50)
                if rows:
                    import pandas as _pd
                    st.dataframe(_pd.DataFrame(rows), use_container_width=True, height=520)
                else:
                    st.info("No conflicts accumulated yet. Run at least one case.")
                st.stop()

            # --- v204–v205: Design intelligence + confidence instruments ---
            if view == "Timeline Strip":
                st.caption("v204: Timeline strip of the current run (phases + evaluations).")
                tr = run.get("trace") or []
                if not tr:
                    st.info("No trace available.")
                else:
                    try:
                        import pandas as _pd
                        rows = []
                        for i, t in enumerate(tr):
                            rows.append({
                                "i": i,
                                "phase": t.get("phase") or t.get("step") or "",
                                "feasible": bool(t.get("feasible")) if t.get("feasible") is not None else None,
                                "failure": t.get("failure_mode") or t.get("failure") or "",
                                "score": t.get("score") or t.get("_score"),
                            })
                        df = _pd.DataFrame(rows)
                        st.dataframe(df, use_container_width=True, height=420)
                    except Exception:
                        st.json(tr[:200])
                st.stop()

            if view == "Lineage Graph":
                st.caption("v204: Design lineage graph based on recorded parents (audit-clean).")
                if not (run.get("archive") or []):
                    st.info("No archive available.")
                    st.stop()
                edges = build_lineage_edges(run.get("archive") or [])
                if not edges:
                    st.info("No explicit parent links found in archive candidates. (Fallback: use 'Machine genealogy' for reconstructed ancestry.)")
                    st.stop()
                layout = compute_tree_layout(edges)
                try:
                    import pandas as _pd
                    import plotly.graph_objects as _go

                    # Edges as segments
                    xs = []
                    ys = []
                    for p, c in edges:
                        if p not in layout or c not in layout:
                            continue
                        xs += [layout[p]["x"], layout[c]["x"], None]
                        ys += [layout[p]["y"], layout[c]["y"], None]
                    fig = _go.Figure()
                    fig.add_trace(_go.Scatter(x=xs, y=ys, mode="lines", name="lineage"))

                    # Nodes
                    ndf = _pd.DataFrame([
                        {"id": nid, "x": v["x"], "y": v["y"], "depth": v["depth"]}
                        for nid, v in layout.items()
                    ])
                    fig.add_trace(_go.Scatter(x=ndf["x"], y=ndf["y"], mode="markers+text", text=ndf["id"], textposition="top center", name="nodes"))
                    fig.update_layout(height=520, margin=dict(l=10, r=10, t=30, b=10), title="Lineage Graph")
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    st.write({"edges": edges[:200], "layout": layout})
                st.stop()

            if view == "Constraint Spend Map":
                st.caption("v204: Spend map - where feasibility margin is being spent.")
                if not filt:
                    st.info("No candidates available.")
                    st.stop()
                xk, yk = st.columns(2)
                x_key = xk.text_input("X axis input key", value=var_keys[0] if var_keys else "Ip_MA", key="spend_x")
                y_key = yk.text_input("Y axis input key", value=var_keys[1] if len(var_keys) > 1 else "R0_m", key="spend_y")
                mode = st.selectbox("Color by", ["min_margin", "feasibility_state", "constraint_margin"], index=0, key="spend_color")
                con_key = None
                if mode == "constraint_margin":
                    con_key = st.text_input("Constraint key", value="q_div", key="spend_ck")
                scat = build_spend_scatter(filt, x_key=str(x_key), y_key=str(y_key), color_by=str(mode), constraint_key=str(con_key) if con_key else None)
                try:
                    import pandas as _pd
                    import plotly.express as _px
                    df = _pd.DataFrame({"x": scat["x"], "y": scat["y"], "c": scat["c"], "id": scat["ids"]})
                    fig = _px.scatter(df, x="x", y="y", hover_data=["id"], color="c")
                    fig.update_layout(height=520, margin=dict(l=10, r=10, t=20, b=10))
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    st.json(scat)
                st.stop()

            if view == "Robustness Envelope":
                st.caption("v205: Robustness envelope (first-order margin perturbation sweep).")
                if not filt:
                    st.info("No candidates available.")
                    st.stop()
                idx_sel = int(st.session_state.get("opt_inspect_idx", 0))
                cand = filt[int(max(0, min(idx_sel, len(filt)-1)))]
                env = robustness_envelope_from_records(cand.get("constraints") or [])
                if not env.get("ok"):
                    st.info(env.get("reason"))
                else:
                    try:
                        import pandas as _pd
                        st.line_chart(_pd.DataFrame({"pass_fraction": env["pass_fraction"]}, index=[str(p) for p in env["perturbations"]]))
                    except Exception:
                        st.write(env)
                st.json(env, expanded=False)
                st.stop()

            if view == "Design Narrative":
                st.caption("v205: Design narrative pack (review-grade, no recommendations).")
                if not filt:
                    st.info("No candidates available.")
                    st.stop()
                idx_sel = int(st.session_state.get("opt_inspect_idx", 0))
                cand = filt[int(max(0, min(idx_sel, len(filt)-1)))]
                nar = build_narrative(cand)
                st.markdown(nar.get("markdown") or "")
                st.download_button("Download narrative (md)", data=(nar.get("markdown") or "").encode("utf-8"), file_name="design_narrative.md", mime="text/markdown")
                st.json(nar, expanded=False)
                st.stop()

            if view == "Design Card":
                st.caption("v205: One-page design card (printable, reviewer-friendly).")
                if not filt:
                    st.info("No candidates available.")
                    st.stop()
                idx_sel = int(st.session_state.get("opt_inspect_idx", 0))
                cand = filt[int(max(0, min(idx_sel, len(filt)-1)))]
                card = build_design_card_md(cand)
                st.markdown(card)
                st.download_button("Download Design Card (md)", data=card.encode("utf-8"), file_name="design_card.md", mime="text/markdown")
                st.stop()

            if view == "Design Packet":
                st.caption("v207: Design Packet - narrative + card + key tables (PDF best-effort).")
                if not filt:
                    st.info("No candidates available.")
                    st.stop()
                idx_sel = int(st.session_state.get("opt_inspect_idx", 0))
                cand = filt[int(max(0, min(idx_sel, len(filt)-1)))]
                nar = build_narrative(cand)
                card = build_design_card_md(cand)
                title = f"SHAMS Design Packet - Candidate {idx_sel}"
                pkt = build_design_packet_files(title=title, card_md=card, narrative_md=(nar.get('markdown') or ''), candidate=cand)
                md = pkt.get('markdown') or ''
                st.markdown(md)
                st.download_button("Download Design Packet (md)", data=md.encode('utf-8'), file_name="design_packet.md", mime="text/markdown", use_container_width=True)
                pdfb = pkt.get('pdf_bytes')
                if pdfb:
                    st.download_button("Download Design Packet (pdf)", data=pdfb, file_name="design_packet.pdf", mime="application/pdf", use_container_width=True)
                else:
                    st.info("PDF rendering unavailable (markdown export is authoritative).")
                with st.expander("Packet metadata (json)", expanded=False):
                    st.json({k: v for k, v in pkt.items() if k not in ('markdown','pdf_bytes')}, expanded=False)
                st.stop()

            if view == "Confidence Sweep":
                st.caption("v207: Confidence Sweep - explicit declared perturbations (no hidden penalties, no recommendations).")
                if not filt:
                    st.info("No candidates available.")
                    st.stop()
                idx_sel = int(st.session_state.get("opt_inspect_idx", 0))
                cand = filt[int(max(0, min(idx_sel, len(filt)-1)))]
                recs = cand.get('constraints') or []
                cb = cand.get('closure_bundle') or {}
                cs = confidence_sweep(records=recs, closure_bundle=cb)
                if not cs.get('ok'):
                    st.warning(cs.get('reason'))
                else:
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Verdict", cs.get('verdict'))
                    c2.metric("Min pass fraction", f"{float(cs.get('min_pass_fraction',0.0))*100:.1f}%")
                    fk = cs.get('first_kill_tally') or {}
                    top = sorted(fk.items(), key=lambda kv: kv[1], reverse=True)[:1]
                    c3.metric("Most common first-kill", top[0][0] if top else '-')
                    try:
                        import pandas as _pd
                        df = _pd.DataFrame({"pass_fraction": cs.get('pass_fraction') or []}, index=[str(x) for x in (cs.get('margin_deltas') or [])])
                        st.line_chart(df)
                    except Exception:
                        pass
                    with st.expander("First-kill tally", expanded=False):
                        st.write(fk)
                    with st.expander("Proxy headlines", expanded=False):
                        st.write(cs.get('proxy_headlines') or [])
                st.json(cs, expanded=False)
                st.download_button("Download Confidence Sweep (json)", data=json.dumps(cs, indent=2, sort_keys=True), file_name="confidence_sweep.json", mime="application/json", use_container_width=True)
                st.stop()

            # --- v208: Review-room instruments ---
            if view == "Scan ↔ Forge Grounding":
                st.caption("Ground the current candidate in Scan Lab topology (descriptive).")
                sa = st.session_state.get("scan_cartography_artifact")
                if not isinstance(sa, dict):
                    st.info("No Scan Lab artifact found in session. Run Scan Lab or upload a scan artifact there first.")
                    st.stop()
                if not filt:
                    st.info("No candidates available.")
                    st.stop()
                idx_sel = int(st.session_state.get("opt_inspect_idx", 0))
                cand = filt[int(max(0, min(idx_sel, len(filt)-1)))]
                sg = _scan_grounding(cand, sa, intent=str(run.get("intent") or "Reactor"))
                if not sg.get("ok"):
                    st.warning(str(sg.get("reason")))
                st.json(sg, expanded=False)
                st.download_button("Download grounding (json)", data=json.dumps(sg, indent=2, sort_keys=True), file_name="scan_forge_grounding.json", mime="application/json", use_container_width=True)
                st.stop()

            # ---- Supremacy Instruments (descriptive, review-room)
            if view == "Epistemic Gap Map":
                from tools.sandbox import forge_supremacy_plus as fsp
                st.caption("Epistemic Gap Map: make model limits explicit (honesty signaling, not UQ).")
                ctx = {
                    "assumptions_ledger": st.session_state.get("assumptions_ledger_text") or "",
                    "model_ledger": st.session_state.get("model_ledger_text") or "",
                    "notes": st.session_state.get("run_notes") or "",
                }
                gaps = fsp.epistemic_gap_map(ctx)
                for k, items in gaps.items():
                    with st.expander(k, expanded=False):
                        for it in items:
                            st.write(f"- {it}")
                st.download_button("Download Gap Map (JSON)",
                                   data=json.dumps(gaps, indent=2).encode("utf-8"),
                                   file_name="epistemic_gap_map.json",
                                   mime="application/json")
                st.stop()

            if view == "Constraint Personas":
                from tools.sandbox import forge_supremacy_plus as fsp
                st.caption("Constraint Personas: memorable behavioral profiles (descriptive).")
                personas = fsp.constraint_personas()
                for cname, prof in personas.items():
                    with st.expander(cname, expanded=False):
                        for kk, vv in prof.items():
                            st.write(f"**{kk}:** {vv}")
                st.download_button("Download Personas (JSON)",
                                   data=json.dumps(personas, indent=2).encode("utf-8"),
                                   file_name="constraint_personas.json",
                                   mime="application/json")
                st.stop()

            if view == "Design Genealogy":
                from tools.sandbox import forge_supremacy_plus as fsp
                st.caption("Design Genealogy: lineage view (when lineage metadata exists).")
                cand_list = st.session_state.get("opt_archive_filtered") or st.session_state.get("opt_archive") or []
                md = fsp.genealogy_markdown(list(cand_list) if isinstance(cand_list, list) else [])
                st.markdown(md)
                st.download_button("Download Genealogy (MD)",
                                   data=md.encode("utf-8"),
                                   file_name="design_genealogy.md",
                                   mime="text/markdown")
                st.stop()

            if view == "Do‑Not‑Build Brief":
                from tools.sandbox import forge_supremacy_plus as fsp
                st.caption("Do‑Not‑Build Brief: reasons *not* to build (trust ledger).")
                filt = st.session_state.get("opt_archive_filtered") or st.session_state.get("opt_archive") or []
                if not filt:
                    st.info("No candidates available.")
                    st.stop()
                idx_sel = int(st.session_state.get("opt_inspect_idx", 0))
                cand = filt[int(max(0, min(idx_sel, len(filt)-1)))]
                ctx = {
                    "margin_ledger": st.session_state.get("opt_margin_ledger"),
                    "conflicts": st.session_state.get("opt_conflicts"),
                    "first_kill_under_uncertainty": st.session_state.get("opt_first_kill_uncertainty"),
                }
                brief = fsp.do_not_build_brief(cand, ctx)
                st.subheader(brief["title"])
                st.caption(brief.get("posture", ""))
                for r in brief["reasons"]:
                    st.write(f"- {r}")
                st.download_button("Download Do‑Not‑Build Brief (JSON)",
                                   data=json.dumps(brief, indent=2).encode("utf-8"),
                                   file_name="do_not_build_brief.json",
                                   mime="application/json")
                st.stop()

            if view == "Process of Elimination":
                from tools.sandbox import forge_supremacy_plus as fsp
                st.caption("Process of Elimination: why most machines cannot exist (constraint narrative).")
                ctx = {
                    "first_failure_histogram": st.session_state.get("scan_first_failure_hist"),
                    "dominant_killers": st.session_state.get("scan_dominant_killers"),
                }
                md = fsp.elimination_narrative(ctx)
                st.markdown(md)
                st.download_button("Download Elimination Narrative (MD)",
                                   data=md.encode("utf-8"),
                                   file_name="process_of_elimination.md",
                                   mime="text/markdown")
                st.stop()

            if view == "Paper‑Ready Signals":
                from tools.sandbox import forge_supremacy_plus as fsp
                st.caption("Paper‑Ready Signals: stable figure/table IDs for deterministic replay.")
                filt = st.session_state.get("opt_archive_filtered") or st.session_state.get("opt_archive") or []
                if not filt:
                    st.info("No candidates available.")
                    st.stop()
                idx_sel = int(st.session_state.get("opt_inspect_idx", 0))
                cand = filt[int(max(0, min(idx_sel, len(filt)-1)))]
                sig = fsp.paper_ready_signals(cand)
                for item in sig["paper_ready_signals"]:
                    st.write(f"**{item['id']}** - {item['title']} · `{item['ref']}`")
                st.download_button("Download Paper‑Ready Signals (JSON)",
                                   data=json.dumps(sig, indent=2).encode("utf-8"),
                                   file_name="paper_ready_signals.json",
                                   mime="application/json")
                st.stop()

            if view == "Silence Mode":
                st.caption("Silence Mode: review-room calm. Suppresses celebratory UI noise (no effect on physics).")
                st.session_state["silence_mode"] = st.toggle("Enable Silence Mode", value=bool(st.session_state.get("silence_mode", False)))
                if st.session_state.get("silence_mode"):
                    st.info("Silence Mode is ON. Prefer artifacts over narration.")
                else:
                    st.info("Silence Mode is OFF.")
                st.stop()
            if view == "Sensitivity Fingerprint":
                st.caption("Constraint Sensitivity Fingerprint: small perturbation fragility tags (screening-level).")
                from tools.sandbox import sensitivity_fingerprint as sf
                filt = st.session_state.get("opt_archive_filtered") or st.session_state.get("opt_archive") or []
                if not filt:
                    st.info("No candidates available.")
                    st.stop()
                idx_sel = int(st.session_state.get("opt_inspect_idx", 0))
                cand = filt[int(max(0, min(idx_sel, len(filt)-1)))]
                # Use existing point evaluator wrapper if available; otherwise show info only.
                evaluator = st.session_state.get("_frozen_point_evaluator")
                if evaluator is None:
                    st.warning("No evaluator wrapper found in session. Run any evaluation to enable fingerprints.")
                    st.stop()
                fp = sf.build_fingerprint(cand, evaluator=evaluator)
                for t in fp.get("tags", []):
                    st.write(f"- {t}")
                if fp.get("notes"):
                    with st.expander("Notes", expanded=False):
                        for n in fp["notes"]:
                            st.write(f"- {n}")
                st.download_button("Download Fingerprint (JSON)",
                                   data=json.dumps(fp, indent=2).encode("utf-8"),
                                   file_name="sensitivity_fingerprint.json",
                                   mime="application/json")
                st.stop()

            if view == "Reviewer Packet":
                st.caption("One-click Reviewer Packet: Markdown bundle + key artifacts (descriptive, deterministic).")
                filt = st.session_state.get("opt_archive_filtered") or st.session_state.get("opt_archive") or []
                if not filt:
                    st.info("No candidates available.")
                    st.stop()
                idx_sel = int(st.session_state.get("opt_inspect_idx", 0))
                cand = filt[int(max(0, min(idx_sel, len(filt)-1)))]
                from tools.sandbox.reviewer_packet_builder import ReviewerPacketOptions, build_reviewer_packet_zip
                with st.expander("Packet composition", expanded=False):
                    c1, c2, c3 = st.columns(3)
                    include_report = c1.checkbox("Include Report Pack", value=True, key="v322_rp_inc_report")
                    include_trinity = c2.checkbox("Include Review Trinity", value=True, key="v322_rp_inc_trinity")
                    include_attack = c3.checkbox("Include Attack Simulation", value=True, key="v322_rp_inc_attack")
                    c4, c5, c6 = st.columns(3)
                    include_scan = c4.checkbox("Include Scan Grounding", value=True, key="v322_rp_inc_scan")
                    include_capsule = c5.checkbox("Include Run Capsule", value=True, key="v322_rp_inc_capsule")
                    include_manifests = c6.checkbox("Include Repo Manifests", value=True, key="v322_rp_inc_manif")

                cap = run.get("capsule_v2") if isinstance(run, dict) else None
                sa = st.session_state.get("scan_cartography_artifact")
                sg = _scan_grounding(cand, sa, intent=str(run.get("intent") or "Reactor")) if isinstance(sa, dict) else None
                dnb = st.session_state.get("do_not_build_brief_latest")
                opts = ReviewerPacketOptions(
                    include_core_docs=True,
                    include_candidate_snapshot=True,
                    include_report_pack=bool(include_report),
                    include_review_trinity=bool(include_trinity),
                    include_attack_simulation=bool(include_attack),
                    include_scan_grounding=bool(include_scan),
                    include_run_capsule=bool(include_capsule),
                    include_do_not_build_brief=True,
                    include_repo_manifests=bool(include_manifests),
                )
                zip_bytes, summary = build_reviewer_packet_zip(
                    candidate=cand,
                    repo_root=Path(__file__).resolve().parent.parent,
                    run_capsule=cap if isinstance(cap, dict) else None,
                    scan_grounding=sg if isinstance(sg, dict) else None,
                    do_not_build_brief=dnb if isinstance(dnb, dict) else None,
                    options=opts,
                )
                st.download_button(
                    "Download Reviewer Packet (ZIP)",
                    data=zip_bytes,
                    file_name="shams_reviewer_packet.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
                with st.expander("Packet manifest (preview)", expanded=False):
                    st.json(summary.get("manifest") or {}, expanded=False)
                st.stop()
            if view == "Review Trinity":
                st.caption("Review Trinity: Existence Proof → Stress Story → Positioning.")
                if not filt:
                    st.info("No candidates available.")
                    st.stop()
                idx_sel = int(st.session_state.get("opt_inspect_idx", 0))
                cand = filt[int(max(0, min(idx_sel, len(filt)-1)))]
                sa = st.session_state.get("scan_cartography_artifact")
                sg = _scan_grounding(cand, sa, intent=str(run.get("intent") or "Reactor")) if isinstance(sa, dict) else {}
                tri = build_review_trinity(candidate=cand, scan_grounding=sg if isinstance(sg, dict) else {})
                st.markdown(tri.get("markdown") or "")
                st.download_button("Download Review Trinity (md)", data=(tri.get("markdown") or "").encode("utf-8"), file_name="review_trinity.md", mime="text/markdown", use_container_width=True)
                st.download_button("Download Review Trinity (json)", data=json.dumps(tri, indent=2, sort_keys=True), file_name="review_trinity.json", mime="application/json", use_container_width=True)
                st.stop()

            if view == "Attack Simulation":
                st.caption("Hostile review rehearsal scaffold (no invented answers).")
                if not filt:
                    st.info("No candidates available.")
                    st.stop()
                idx_sel = int(st.session_state.get("opt_inspect_idx", 0))
                cand = filt[int(max(0, min(idx_sel, len(filt)-1)))]
                cap = run.get("capsule_v2") if isinstance(run, dict) else None
                atk = build_attack_simulation(candidate=cand, run_capsule=cap if isinstance(cap, dict) else None)
                st.markdown(atk.get("markdown") or "")
                st.download_button("Download Attack Simulation (md)", data=(atk.get("markdown") or "").encode("utf-8"), file_name="attack_simulation.md", mime="text/markdown", use_container_width=True)
                st.download_button("Download Attack Simulation (json)", data=json.dumps(atk, indent=2, sort_keys=True), file_name="attack_simulation.json", mime="application/json", use_container_width=True)
                st.stop()

            if view == "Exposure Readiness":
                st.caption(_LANG.get("external_exposure_gate"))
                try:
                    _chk = (Path(__file__).resolve().parent.parent / "docs"/ "EXTERNAL_EXPOSURE_CHECKLIST.md").read_text(encoding="utf-8")
                except Exception:
                    _chk = "(missing docs/EXTERNAL_EXPOSURE_CHECKLIST.md)"
                st.markdown(_chk)
                st.download_button("Download exposure checklist (md)", data=_chk.encode("utf-8"), file_name="EXTERNAL_EXPOSURE_CHECKLIST.md", mime="text/markdown", use_container_width=True)
                st.stop()
            if view in ("Reactor Accounting Console","Margin Ledger","Reality Gates","Economics Deck","Report Pack","Closure Certificate","Provenance Graph","Engineering Reality Budget","Failure-Mode Canon","Design Class","Citation Blocks","Reference Reproduction"):
                if not filt:
                    st.info("No candidates available in the archive (after filters).")
                else:
                    import pandas as _pd
                    def _lab(i):
                        a = filt[i]
                        ms = a.get("min_signed_margin")
                        try:
                            ms = float(ms)
                        except Exception:
                            ms = float('nan')
                        return f"{i:03d} | min_margin={ms:.3g} | {str(a.get('failure_mode') or '')}".strip()
                    idx = st.selectbox("Candidate", options=list(range(len(filt))), format_func=_lab, key="v203_rdf_candidate_pick")
                    a = filt[int(idx)]
                    if view == "Reactor Accounting Console":
                        st.caption("Explicit plant closure (derived). No hidden penalties.")
                        st.json(a.get("closure_bundle") or {}, expanded=False)
                    elif view == "Margin Ledger":
                        mb = a.get("margin_budget") or {}
                        rows = mb.get("rows") or []
                        if rows:
                            st.dataframe(_pd.DataFrame(rows), use_container_width=True)
                        else:
                            st.json(mb, expanded=False)
                    elif view == "Reality Gates":
                        st.json(a.get("reality_gates") or {}, expanded=False)
                    elif view == "Economics Deck":
                        cb = a.get("closure_bundle") or {}
                        env = (cb.get("economics_envelopes") if isinstance(cb, dict) else None) or []
                        if env:
                            st.dataframe(_pd.DataFrame(env), use_container_width=True)
                        else:
                            st.json(cb, expanded=False)
                    elif view == "Report Pack":
                        rp = a.get("report_pack") or {}
                        md = rp.get("markdown") or "(no report)"
                        st.markdown(md)
                        st.download_button("Download report JSON", data=json.dumps(rp.get("json") or {}, indent=2, sort_keys=True), file_name="shams_reactor_design_forge_report.json", mime="application/json", use_container_width=True, key="v203_dl_rdf_json")
                        st.download_button("Download report Markdown", data=str(md), file_name="shams_reactor_design_forge_report.md", mime="text/markdown", use_container_width=True, key="v203_dl_rdf_md")
                        st.download_button("Download report CSV", data=str(rp.get("csv") or ""), file_name="shams_reactor_design_forge_report.csv", mime="text/csv", use_container_width=True, key="v203_dl_rdf_csv")

                    elif view == "Closure Certificate":
                        from tools.sandbox.closure_certificate import build_closure_certificate
                        cert = a.get("closure_certificate") or build_closure_certificate(a)
                        st.subheader(f"Feasibility Closure Certificate - {cert.get('verdict')}")
                        st.json(cert, expanded=False)
                        st.download_button("Download Closure Certificate (JSON)",
                                           data=json.dumps(cert, indent=2, sort_keys=True),
                                           file_name="shams_closure_certificate.json",
                                           mime="application/json",
                                           use_container_width=True,
                                           key="rdf_dl_fcc")
                    elif view == "Provenance Graph":
                        from tools.sandbox.constraint_provenance_graph import build_cpg_for_constraint
                        st.caption("Constraint Provenance Graph: where each limit comes from (structure, not new physics).")
                        cname = st.text_input("Constraint name (e.g., q_div, sigma_vm, HTS margin, TBR, net_electric)", value=str(a.get("failure_mode") or "q_div"))
                        cpg = build_cpg_for_constraint(cname, intent=str(run.get("intent") or ""))
                        st.json(cpg, expanded=False)
                        st.download_button("Download CPG (JSON)",
                                           data=json.dumps(cpg, indent=2, sort_keys=True),
                                           file_name="shams_constraint_provenance_graph.json",
                                           mime="application/json",
                                           use_container_width=True,
                                           key="rdf_dl_cpg")
                    elif view == "Engineering Reality Budget":
                        st.caption("Engineering Reality Budget: grouped margin currency (descriptive).")
                        mb = a.get("margin_budget") or {}
                        rows = mb.get("rows") or []
                        groups = {"plasma": [], "materials": [], "thermal": [], "economics": [], "other": []}
                        for r in rows:
                            nm = str(r.get("name") or "").lower()
                            if any(k in nm for k in ["q95","bet","greenwald","h98","kappa","delta","stability","plasma"]):
                                groups["plasma"].append(r)
                            elif any(k in nm for k in ["sigma","stress","strain","tf","structure","hts","coil"]):
                                groups["materials"].append(r)
                            elif any(k in nm for k in ["q_div","heat","divert","sol","thermal","wall"]):
                                groups["thermal"].append(r)
                            elif any(k in nm for k in ["coe","cost","econ","net","recirc","electric"]):
                                groups["economics"].append(r)
                            else:
                                groups["other"].append(r)
                        for g,rs in groups.items():
                            with st.expander(f"{g.title()} budget", expanded=(g in ["plasma","materials","thermal"])):
                                if rs:
                                    import pandas as _pd
                                    st.dataframe(_pd.DataFrame(rs), use_container_width=True)
                                else:
                                    st.write("(no rows in this bucket)")
                        st.download_button("Download Reality Budget (JSON)",
                                           data=json.dumps(groups, indent=2, sort_keys=True),
                                           file_name="shams_engineering_reality_budget.json",
                                           mime="application/json",
                                           use_container_width=True,
                                           key="rdf_dl_erb")
                    elif view == "Failure-Mode Canon":
                        st.caption("Failure-Mode Canon: standardized non-prescriptive archetypes.")
                        canon = {
                            "heat-flux dominated": ["q_div", "divertor", "sol"],
                            "stress-limited": ["sigma", "stress", "vm"],
                            "hts-margin collapse": ["hts", "margin"],
                            "breeding-limited": ["tbr", "breed"],
                            "recirculation-trapped": ["recirc", "net", "electric"],
                            "coupled failure": ["+", "and", "coupled"],
                        }
                        fm_now = str(a.get("failure_mode") or "")
                        tag = "unclassified"
                        fml = fm_now.lower()
                        for k, toks in canon.items():
                            if any(t in fml for t in toks):
                                tag = k
                                break
                        st.write({"failure_mode": fm_now, "canonical_tag": tag})
                        st.json(canon, expanded=False)
                        st.download_button("Download Failure-Mode Canon (JSON)",
                                           data=json.dumps({"canonical_tag": tag, "canon": canon}, indent=2, sort_keys=True),
                                           file_name="shams_failure_mode_canon.json",
                                           mime="application/json",
                                           use_container_width=True,
                                           key="rdf_dl_fmc")
                    elif view == "Design Class":
                        dc = a.get("design_class") or {}
                        st.subheader(f"{dc.get('code','')} - {dc.get('name','')}")
                        st.json(dc, expanded=False)
                        st.download_button("Download Design Class (JSON)",
                                           data=json.dumps(dc, indent=2, sort_keys=True),
                                           file_name="shams_design_class.json",
                                           mime="application/json",
                                           use_container_width=True,
                                           key="rdf_dl_dc")
                    elif view == "Citation Blocks":
                        cb = a.get("citation_blocks") or {}
                        st.caption("Paste-ready Methods + citation scaffold (local repo content).")
                        st.text_area("Methods block", value=str(cb.get("methods_block") or ""), height=200)
                        if cb.get("citation_cff"):
                            with st.expander("CITATION.cff", expanded=False):
                                st.code(cb.get("citation_cff"))
                        st.download_button("Download Citation Blocks (JSON)",
                                           data=json.dumps(cb, indent=2, sort_keys=True),
                                           file_name="shams_citation_blocks.json",
                                           mime="application/json",
                                           use_container_width=True,
                                           key="rdf_dl_cb")
                    elif view == "Reference Reproduction":
                        rc = a.get("reference_context") or {}
                        st.caption("Historical reproduction: compare candidate to reference presets (anchors, not targets).")
                        refs = rc.get("refs") or []
                        if refs:
                            for ref in refs:
                                with st.expander(str(ref.get("ref")), expanded=False):
                                    st.json(ref.get("comparison") or {}, expanded=False)
                        else:
                            st.info("No reference context available for this candidate.")
                        st.download_button("Download Reference Context (JSON)",
                                           data=json.dumps(rc, indent=2, sort_keys=True),
                                           file_name="shams_reference_context.json",
                                           mime="application/json",
                                           use_container_width=True,
                                           key="rdf_dl_ref")

                st.stop()

            # --- v203 Reactor Design Forge panels (PROCESS-independence) ---
            def _pick_candidate(_cands):
                if not _cands:
                    return None
                opts = []
                for idx,a in enumerate(_cands):
                    ms = a.get('min_signed_margin')
                    try:
                        msf = float(ms)
                    except Exception:
                        msf = None
                    fp = a.get('fingerprint') or a.get('_id') or str(idx)
                    opts.append((f"{idx:03d} | min_margin={msf if msf is not None else 'na'} | {fp}", idx))
                label_to_i = {l:i for l,i in opts}
                lab = st.selectbox('Select candidate', options=[l for l,_ in opts], index=0, key='rdf_pick')
                return _cands[int(label_to_i.get(lab,0))]

            if view in ["Reactor Accounting Console","Margin Ledger","Reality Gates","Economics Deck","Report Pack"]:
                sel = _pick_candidate(filt)
                if sel is None:
                    st.info('Archive is empty. Run a case first.')
                else:
                    if view == "Reactor Accounting Console":
                        st.caption('Explicit plant/accounting closure derived from frozen truth outputs. No hidden assumptions.')
                        cb = sel.get('closure_bundle')
                        if not isinstance(cb, dict):
                            cb = closure_console(outputs=sel.get('outputs') or {}, cost_proxy=sel.get('cost') or {})
                        st.json(cb, expanded=False)
                    elif view == "Margin Ledger":
                        st.caption('Constraint margin budget (engineering accounting). Not a score.')
                        mb = sel.get('margin_budget')
                        if not isinstance(mb, dict):
                            mb = margin_budget(sel.get('constraints') or [])
                        import pandas as _pd
                        st.dataframe(_pd.DataFrame(mb.get('rows') or []), use_container_width=True)
                        st.write({'min_signed_margin': mb.get('min_signed_margin'), 'tight_constraints': mb.get('tight_constraints')})
                    elif view == "Reality Gates":
                        st.caption('Declared buildability gates (toggleable, descriptive).')
                        rg = sel.get('reality_gates')
                        if not isinstance(rg, dict):
                            rg = reality_gates(sel.get('constraints') or [], sel.get('closure_bundle') if isinstance(sel.get('closure_bundle'), dict) else None)
                        st.json(rg, expanded=False)
                    elif view == "Economics Deck":
                        st.caption('Explicit economics envelopes (Optimistic / Nominal / Conservative).')
                        cb = sel.get('closure_bundle')
                        if not isinstance(cb, dict):
                            cb = closure_console(outputs=sel.get('outputs') or {}, cost_proxy=sel.get('cost') or {})
                        env = (cb.get('economics_envelopes') or []) if isinstance(cb, dict) else []
                        import pandas as _pd
                        st.dataframe(_pd.DataFrame(env), use_container_width=True)
                    elif view == "Report Pack":
                        st.caption('PROCESS-recognizable report pack (audit-clean). No ranking, no recommendations.')
                        rp = sel.get('report_pack')
                        if not isinstance(rp, dict):
                            rp = build_report_pack(intent=str(run.get('intent')), inputs=sel.get('inputs') or {}, outputs=sel.get('outputs') or {}, constraints=sel.get('constraints') or [], closure_bundle=sel.get('closure_bundle') if isinstance(sel.get('closure_bundle'), dict) else None, margin_budget=sel.get('margin_budget') if isinstance(sel.get('margin_budget'), dict) else None, reality_gates=sel.get('reality_gates') if isinstance(sel.get('reality_gates'), dict) else None)
                        st.download_button('Download report JSON', data=json.dumps(rp.get('json') or {}, indent=2, sort_keys=True), file_name='shams_report_pack.json', mime='application/json', use_container_width=True)
                        st.download_button('Download report markdown', data=str(rp.get('markdown') or ''), file_name='shams_report_pack.md', mime='text/markdown', use_container_width=True)
                        st.download_button('Download report CSV', data=str(rp.get('csv') or ''), file_name='shams_report_pack.csv', mime='text/csv', use_container_width=True)
                        with st.expander('Preview markdown', expanded=False):
                            st.markdown(str(rp.get('markdown') or ''))

            if view == "Design navigation (steering)":
                st.caption("Steering cues are derived from a local linear surface map built from evaluated archive data. Descriptive only.")
                # derive variable keys from var_specs
                vs = run.get("var_specs") or []
                var_k = [str(v.get("key")) for v in vs if isinstance(v, dict) and v.get("key")]
                # constraint list
                cnames = []
                try:
                    if (run.get("archive") or []) and ((run.get("archive")[0].get("constraints") or [])):
                        cnames = sorted(list({str(c.get("name")) for c in (run.get("archive")[0].get("constraints") or []) if c.get("name")}))
                except Exception:
                    cnames = []
                if not cnames:
                    st.info("No constraint names available in archive.")
                else:
                    csel = st.selectbox("Constraint to navigate", options=cnames, index=0, key="opt_nav_constraint")
                    fam = st.selectbox("Lever family", options=["All","Geometry","Plasma","Power","Magnets","Other"], index=0, key="opt_nav_family")
                    smap = constraint_surface_map(archive=run.get("archive") or [], var_keys=var_k, constraint_name=str(csel))
                    if not smap.get("ok"):
                        st.warning(f"Surface map not available: {smap.get('reason')}")
                        st.json(smap)
                    else:
                        cues = steering_cues_from_surface_map(smap)
                        cues = filter_cues(cues, family=fam, top_n=15)
                        st.markdown("#### Steering cues (local, descriptive)")
                        if cues:
                            import pandas as _pd
                            st.dataframe(_pd.DataFrame(cues)[["family","lever","cue","signed","strength"]], use_container_width=True)
                        else:
                            st.info("No cues available (insufficient gradient data).")
                        with st.expander("Surface map details", expanded=False):
                            st.json(smap, expanded=False)

            elif view == "Machine existence report":
                st.caption("Explains why the currently selected candidate exists (or how close it is). No recommendations.")
                idx2 = int(st.session_state.get("opt_inspect_idx", 0))
                cand = filt[idx2] if filt and idx2 < len(filt) else (filt[0] if filt else None)
                if cand is None:
                    st.info("No candidate available.")
                else:
                    rep = existence_report(cand)
                    st.info(rep.get("narrative"))
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Tight constraints**")
                        st.write(rep.get("tight", []))
                    with c2:
                        st.markdown("**Slack constraints**")
                        st.write(rep.get("slack", []))
                    with st.expander("Full existence report (json)", expanded=False):
                        st.json(rep, expanded=False)

            elif view == "Archive regimes & coverage":
                st.caption("Descriptive regime clustering and coverage cues for the feasible archive.")
                ar0 = run.get("archive") or []
                vs = run.get("var_specs") or []
                var_k = [str(v.get("key")) for v in vs if isinstance(v, dict) and v.get("key")]
                h = ladder_histogram(ar0)
                st.markdown("#### Feasibility ladder histogram")
                st.write(h)
                summ = regime_clusters_summary(archive=ar0, var_keys=var_k, max_k=10, seed=int(run.get("seed", 0) or 0))
                if not summ.get("ok"):
                    st.warning(summ.get("reason"))
                else:
                    import pandas as _pd
                    st.markdown("#### Regime clusters (feasible points)")
                    st.dataframe(_pd.DataFrame(summ.get("clusters") or []), use_container_width=True)
                    st.caption("Clusters are descriptive only; they do not imply optimality.")

            elif view == "Machine Dossier":
                st.caption("A structured, exportable dossier for the selected candidate. Descriptive only - no recommendations.")
                # Select candidate
                cand = None
                if filt:
                    try:
                        idx = int(st.session_state.get("opt_inspect_idx", 0) or 0)
                        idx = max(0, min(len(filt)-1, idx))
                        cand = filt[idx]
                    except Exception:
                        cand = filt[0]
                if cand is None:
                    st.info("No candidate available. Run the Machine Finder to populate the archive.")
                else:
                    # Tabs: Truth, Closure, Margins, Costs, Existence, Neighborhood
                    t_truth, t_close, t_marg, t_cost, t_exist, t_neigh = st.tabs([
                        "Truth",
                        "Closure",
                        "Margins",
                        "Economics",
                        "Why it exists",
                        "Neighborhood",
                    ])
                    with t_truth:
                        st.markdown("#### Inputs")
                        st.json(cand.get("inputs") or {}, expanded=False)
                        st.markdown("#### Key outputs")
                        out = cand.get("outputs") or {}
                        # show a compact subset if present
                        keys = ["Pfus_total_MW","P_e_net_MW","Q_DT_eqv","q_div_MW_m2","min_signed_margin"]
                        st.write({k: out.get(k) for k in keys if k in out} or out)
                        st.markdown("#### Constraint ladder")
                        st.write({
                            "feasibility_state": cand.get("feasibility_state"),
                            "robustness_class": cand.get("robustness_class"),
                            "first_failure": cand.get("first_failure"),
                            "failure_mode": cand.get("failure_mode"),
                        })

                        st.markdown("#### Expert signals (descriptive)")
                        tags = _regime_signature(cand)
                        fk = _first_kill(cand)
                        st.write({
                            "regime_signature": tags,
                            "first_kill": fk,
                        })
                        sr = _constraint_spend_rate(cand)
                        if isinstance(sr, dict) and sr.get("ok"):
                            with st.expander("Constraint spend rate vs parent (heuristic)", expanded=False):
                                st.json(sr, expanded=False)
                        with st.expander("Constraint records", expanded=False):
                            st.json(cand.get("constraints") or [], expanded=False)

                    with t_close:
                        st.caption("Plant closure and accounting are computed explicitly (parity layer). They do not modify frozen truth.")
                        try:
                            from src.parity import parity_plant_closure, parity_magnets, parity_cryo
                            from src.models.inputs import PointInputs
                            pi = cand.get("_point_inputs_obj")
                            if pi is None:
                                pi = PointInputs(**(cand.get("inputs") or {}))
                            outputs = cand.get("outputs") or {}
                            plant = parity_plant_closure(pi, outputs)
                            magnets = parity_magnets(pi, outputs)
                            cryo = parity_cryo(pi, outputs)
                            c1,c2,c3 = st.columns(3)
                            c1.metric("Net electric (MW)", f"{plant.get('derived',{}).get('P_e_net_MW', float('nan')):.3g}")
                            c2.metric("Recirc electric (MW)", f"{plant.get('derived',{}).get('P_recirc_e_MW', float('nan')):.3g}")
                            c3.metric("Qe", f"{plant.get('derived',{}).get('Qe', float('nan')):.3g}")
                            with st.expander("Plant closure", expanded=False):
                                st.json(plant, expanded=False)
                            with st.expander("Magnets", expanded=False):
                                st.json(magnets, expanded=False)
                            with st.expander("Cryogenics", expanded=False):
                                st.json(cryo, expanded=False)
                        except Exception as e:
                            st.error(f"Closure console unavailable for this candidate: {e}")

                    with t_marg:
                        st.caption("Margin budget view: tight vs slack constraints (descriptive).")
                        rows=[]
                        for r in (cand.get("constraints") or []):
                            try:
                                rows.append({
                                    "name": r.get("name"),
                                    "ok": bool(r.get("ok")),
                                    "signed_margin": r.get("signed_margin"),
                                    "value": r.get("value"),
                                    "limit": r.get("limit"),
                                })
                            except Exception:
                                pass
                        if rows:
                            import pandas as _pd
                            df=_pd.DataFrame(rows)
                            df=df.sort_values(by="signed_margin", ascending=True, na_position="last")
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        else:
                            st.info("No constraint margin records for this candidate.")

                    with t_cost:
                        st.caption("Economics envelopes are explicit lenses (optimistic/nominal/conservative).")
                        try:
                            from src.parity import parity_costing_envelope, parity_costing
                            from src.models.inputs import PointInputs
                            pi = cand.get("_point_inputs_obj")
                            if pi is None:
                                pi = PointInputs(**(cand.get("inputs") or {}))
                            outputs = cand.get("outputs") or {}
                            env = parity_costing_envelope(pi, outputs)
                            base = parity_costing(pi, outputs)
                            c1,c2,c3 = st.columns(3)
                            c1.metric("CAPEX (MUSD)", f"{base.get('derived',{}).get('CAPEX_MUSD', float('nan')):.3g}")
                            c2.metric("LCOE (USD/MWh)", f"{base.get('derived',{}).get('LCOE_USD_per_MWh', float('nan')):.3g}")
                            # show envelope headline
                            if isinstance(env, dict) and env.get("nominal"):
                                st.caption(
                                    f"Envelope LCOE - Opt {env.get('optimistic',{}).get('LCOE_USD_per_MWh', float('nan')):.3g} | "
                                    f"Nom {env.get('nominal',{}).get('LCOE_USD_per_MWh', float('nan')):.3g} | "
                                    f"Con {env.get('conservative',{}).get('LCOE_USD_per_MWh', float('nan')):.3g}"
                                )
                            with st.expander("Economics envelope", expanded=False):
                                st.json(env, expanded=False)
                            with st.expander("Base costing (proxy)", expanded=False):
                                st.json(base.get("raw", base), expanded=False)
                        except Exception as e:
                            st.error(f"Economics deck unavailable: {e}")

                    with t_exist:
                        try:
                            rep = existence_report(cand)
                            st.json(rep, expanded=False)
                        except Exception as e:
                            st.error(f"Existence report failed: {e}")

                    with t_neigh:
                        st.caption("Bridge to Scan Lab: open a local slice around this candidate (no auto-run).")
                        try:
                            if st.button("Set Scan Lab slice around candidate (Ip vs R0)", use_container_width=True, key="opt_set_scan_slice"):
                                inp = cand.get("inputs") or {}
                                st.session_state["scan_x"] = "R0_m"
                                st.session_state["scan_y"] = "Ip_MA"
                                R0=float(inp.get("R0_m", 1.0))
                                Ip=float(inp.get("Ip_MA", 1.0))
                                st.session_state["scan_bounds"] = {
                                    "R0_m": [max(0.2, 0.7*R0), 1.3*R0],
                                    "Ip_MA": [max(0.1, 0.7*Ip), 1.3*Ip],
                                }
                                st.success("Scan Lab slice parameters set in session state. Switch to Scan Lab to run.")
                        except Exception as e:
                            st.error(f"Could not set Scan Lab slice: {e}")

            elif view == "Expert Compare (no ranking)":
                st.caption("Compare a handful of candidates side-by-side. No ranking, no recommendation - just numbers and margins.")
                ar0 = filt or (run.get("archive") or [])
                if not ar0:
                    st.info("No archive available.")
                else:
                    max_n = min(12, len(ar0))
                    idxs = st.multiselect(
                        "Select candidate indices (from filtered archive order)",
                        options=list(range(len(ar0))),
                        default=list(range(min(3, len(ar0)))),
                        key="opt_compare_idxs",
                    )
                    rows=[]
                    for idx in idxs[:max_n]:
                        a=ar0[int(idx)]
                        out=a.get("outputs") or {}
                        inp=a.get("inputs") or {}
                        rows.append({
                            "idx": int(idx),
                            "feasibility_state": a.get("feasibility_state"),
                            "robustness": a.get("robustness_class"),
                            "first_failure": a.get("first_failure"),
                            "R0_m": inp.get("R0_m"),
                            "a_m": inp.get("a_m"),
                            "Bt_T": inp.get("Bt_T"),
                            "Ip_MA": inp.get("Ip_MA"),
                            "Pfus_total_MW": out.get("Pfus_total_MW"),
                            "P_e_net_MW": out.get("P_e_net_MW"),
                            "Q_DT_eqv": out.get("Q_DT_eqv"),
                            "q_div_MW_m2": out.get("q_div_MW_m2"),
                            "min_signed_margin": out.get("min_signed_margin", a.get("min_signed_margin")),
                        })
                    if rows:
                        import pandas as _pd
                        st.dataframe(_pd.DataFrame(rows), use_container_width=True, hide_index=True)
                    st.caption("Tip: use the Inspector index to sync with Machine Dossier.")

            elif view == "Casebook Runner":
                st.caption("Run a small set of declared cases (intent+lens+bounds) and compare feasibility distributions. No recommendations.")

                # Optional: load the packaged flagship casebook (review-room demo)
                if st.button("Load flagship casebook (packaged)", use_container_width=True, key="opt_load_flagship_casebook", disabled=forge_lock):
                    try:
                        from pathlib import Path as _P
                        _p = _P("scenarios") / "flagship_casebook.json"
                        if _p.exists():
                            st.session_state["opt_casebook"] = json.loads(_p.read_text(encoding="utf-8"))
                            st.success("Flagship casebook loaded.")
                        else:
                            st.warning("flagship_casebook.json not found in scenarios/.")
                    except Exception as _e:
                        st.warning(f"Could not load flagship casebook: {_e}")
                if "opt_casebook"not in st.session_state or not isinstance(st.session_state.get("opt_casebook"), list):
                    st.session_state["opt_casebook"] = []
                # Case definition UI
                c1,c2,c3 = st.columns([2,2,1])
                with c1:
                    case_name = st.text_input("Case name", value=f"Case {len(st.session_state['opt_casebook'])+1}", key="opt_case_name")
                with c2:
                    case_lens = st.selectbox("Lens", list((default_objective_packs(_design_intent_key()) or {}).keys()) or ["default"], key="opt_case_lens")
                with c3:
                    case_seed = st.number_input("Seed", value=int(run.get("seed", 0) or 0), step=1, key="opt_case_seed")
                if st.button("Add case to casebook", use_container_width=True, key="opt_add_case", disabled=forge_lock):
                    st.session_state["opt_casebook"].append({"name": case_name, "lens": case_lens, "seed": int(case_seed)})
                    st.success("Case added.")
                # Display current casebook
                if st.session_state["opt_casebook"]:
                    import pandas as _pd
                    st.dataframe(_pd.DataFrame(st.session_state["opt_casebook"]), use_container_width=True, hide_index=True)
                else:
                    st.info("Casebook is empty. Add 2–5 cases to run.")
                # Run cases (small budgets unless expert toggles)
                budget = int(st.number_input("Per-case evaluation budget", value=120, min_value=20, max_value=5000, step=20, key="opt_case_budget"))
                if st.button("Run casebook", use_container_width=True, key="opt_run_casebook", disabled=forge_lock):
                    results=[]
                    for case in (st.session_state["opt_casebook"] or [])[:10]:
                        try:
                            # Reuse current bounds and var specs from session if present
                            _packs = default_objective_packs(_design_intent_key()) or {}
                            pack = _packs.get(case["lens"]) or next(iter(_packs.values())) if _packs else {}
                            # minimal var specs: use session var specs if present
                            var_specs = run.get("var_specs") or st.session_state.get("opt_var_specs") or []
                            bounds = st.session_state.get("opt_bounds") or {}
                            rcase = run_hybrid_machine_finder(
                                seed=int(case.get("seed",0)),
                                intent=_design_intent_key(),
                                objective_pack=pack,
                                bounds=bounds,
                                var_specs=var_specs,
                                budget=int(budget),
                                cache_enabled=bool(st.session_state.get("opt_cache_enabled", True)),
                                cache_max=int(st.session_state.get("opt_cache_max", 256)),
                            )
                            tr = rcase.get("trace") or []
                            n=len(tr); nf=sum(1 for t in tr if bool(t.get("feasible")))
                            results.append({"case": case["name"], "lens": case["lens"], "seed": case["seed"], "n_eval": n, "n_feasible": nf})
                        except Exception as e:
                            results.append({"case": case["name"], "lens": case["lens"], "seed": case["seed"], "n_eval": 0, "n_feasible": 0, "error": str(e)})
                    st.session_state["opt_casebook_results"] = results
                res = st.session_state.get("opt_casebook_results") or []
                if res:
                    import pandas as _pd
                    st.markdown("#### Casebook results (summary)")
                    st.dataframe(_pd.DataFrame(res), use_container_width=True, hide_index=True)
        

            elif view == "Archive Bay":
                # pick axes
                xkey = st.selectbox("x-axis", ["R0_m","Bt_T","Ip_MA","P_e_net_MW","Pfus_total_MW","q_div_MW_m2","min_signed_margin","_score"], index=0, key="opt_scatter_x")
                ykey = st.selectbox("y-axis", ["P_e_net_MW","Pfus_total_MW","Q_DT_eqv","q_div_MW_m2","min_signed_margin","_score"], index=0, key="opt_scatter_y")
                rows=[]
                for a in filt:
                    o=a.get("outputs") or {}
                    i=a.get("inputs") or {}
                    def get(k):
                        if k in ("_score",):
                            return float(a.get("_score",-1e30))
                        if k in i:
                            return float(i.get(k, float("nan")))
                        return float(o.get(k, float("nan")))
                    rows.append({"x": get(xkey), "y": get(ykey), "feasible": bool(a.get("feasible", False)), "idx": len(rows)})
                if rows:
                    import pandas as _pd
                    df=_pd.DataFrame(rows)
                    st.scatter_chart(df, x="x", y="y")
                    st.caption("Use the Inspector to select a candidate by index from the filtered archive.")
                else:
                    st.info("No points after filtering. Relax filters or rerun with wider bounds/budget.")
            elif view == "Reactor Accounting Console":
                st.caption(
                    "Optional PROCESS-parity accounting: plant closure + magnets + cryo + costing. "
                    "This is a *lens* and does not change frozen evaluator truth."
                )
                # choose candidate
                cand = None
                if filt:
                    cand = filt[int(min(len(filt)-1, int(st.session_state.get("opt_inspect_idx", 0))))]
                elif isinstance(run.get("best_feasible"), dict):
                    cand = run.get("best_feasible")
                if cand is None:
                    st.info("No candidate available. Run the Machine Finder to populate the archive.")
                else:
                    try:
                        from src.parity import parity_plant_closure, parity_magnets, parity_cryo, parity_costing, parity_costing_envelope
                        from src.parity.calibration import economics_local_sensitivity
                        from src.parity.report_pack import build_parity_report_pack, report_pack_to_csv_rows, report_pack_to_markdown
                        pi = cand.get("_point_inputs_obj")
                        if pi is None:
                            # reconstruct PointInputs if present
                            from src.models.inputs import PointInputs
                            pi = PointInputs(**(cand.get("inputs") or {}))
                        outputs = cand.get("outputs") or {}
                        parity = {
                            "plant": parity_plant_closure(pi, outputs),
                            "magnets": parity_magnets(pi, outputs),
                            "cryo": parity_cryo(pi, outputs),
                            "costing": parity_costing(pi, outputs),
                            "costing_envelope": parity_costing_envelope(pi, outputs),
                        }
                        # summary cards
                        c1,c2,c3,c4 = st.columns(4)
                        c1.metric("Net electric (MW)", f"{parity['plant']['derived'].get('P_e_net_MW', float('nan')):.3g}")
                        c2.metric("Qe", f"{parity['plant']['derived'].get('Qe', float('nan')):.3g}")
                        c3.metric("CAPEX (MUSD)", f"{parity['costing']['derived'].get('CAPEX_MUSD', float('nan')):.3g}")
                        c4.metric("LCOE (USD/MWh)", f"{parity['costing']['derived'].get('LCOE_USD_per_MWh', float('nan')):.3g}")
                        # Cost envelope (Phase-2)
                        env = parity.get('costing_envelope', {})
                        posture = st.session_state.get('ppl_cost_posture', 'Nominal')
                        if isinstance(env, dict) and env.get('nominal'):
                            nom = env.get('nominal', {})
                            opt = env.get('optimistic', {})
                            con = env.get('conservative', {})
                            st.caption(
                                f"Economics envelope - Optimistic {opt.get('LCOE_USD_per_MWh', float('nan')):.3g} | "
                                f"Nominal {nom.get('LCOE_USD_per_MWh', float('nan')):.3g} | "
                                f"Conservative {con.get('LCOE_USD_per_MWh', float('nan')):.3g} (posture: {posture})"
                            )
                        with st.expander("Plant closure", expanded=False):
                            st.json(parity["plant"], expanded=False)
                        with st.expander("Magnets", expanded=False):
                            st.json(parity["magnets"], expanded=False)
                        with st.expander("Cryogenics", expanded=False):
                            st.json(parity["cryo"], expanded=False)
                        with st.expander("Costing (proxy)", expanded=False):
                            st.json(parity["costing"].get("raw", parity["costing"]), expanded=False)

                        # --- v2 additions: CAPEX breakdown + local sensitivities ---
                        st.markdown("#### Economics breakdown")
                        bd = (parity.get("costing") or {}).get("derived", {}).get("breakdown_MUSD", {}) or {}
                        if bd:
                            import pandas as _pd
                            df = _pd.DataFrame({"component": list(bd.keys()), "CAPEX_MUSD": [float(bd[k]) for k in bd.keys()]})
                            st.bar_chart(df, x="component", y="CAPEX_MUSD")
                            st.caption("CAPEX proxy breakdown (component bars). Total CAPEX is the sum of these components.")
                        else:
                            st.info("No CAPEX breakdown available for this candidate.")

                        with st.expander("Local sensitivity (economics knobs)", expanded=False):
                            sens = economics_local_sensitivity(inputs=pi, outputs=outputs, perturb_frac=0.10)
                            st.json(sens.get("base", {}), expanded=False)
                            rows = sens.get("rows") or []
                            if rows:
                                import pandas as _pd
                                st.dataframe(_pd.DataFrame(rows), use_container_width=True)
                            st.caption("Finite-difference lens (+10% knob perturbation). Not a gradient; used for intuition.")

                        import json as _json
                        pack = build_parity_report_pack(
                            inputs=pi,
                            outputs=outputs,
                            parity=parity,
                            run_id=str(run.get("run_id", "")),
                            version=str(run.get("version", "")),
                        )
                        md = report_pack_to_markdown(pack)
                        header, row = report_pack_to_csv_rows(pack)
                        csv = ",".join(header) + "\n"+ ",".join([str(x) for x in row]) + "\n"
                        st.download_button(
                            "Download parity report (JSON)",
                            data=_json.dumps(pack, indent=2).encode("utf-8"),
                            file_name="shams_parity_report_pack.json",
                            mime="application/json",
                            use_container_width=True,
                        )
                        st.download_button(
                            "Download parity report (Markdown)",
                            data=md.encode("utf-8"),
                            file_name="shams_parity_report_pack.md",
                            mime="text/markdown",
                            use_container_width=True,
                        )
                        st.download_button(
                            "Download parity flat row (CSV)",
                            data=csv.encode("utf-8"),
                            file_name="shams_parity_report_pack.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )
                    except Exception as _e:
                        st.error(f"Parity layer failed: {_e}")
            elif view == "Parity validation packs (PASS/WARN/FAIL)":

                st.caption("Named validation packs with explicit tolerances. Load your own reference values to certify parity.")
                from pathlib import Path
                from src.parity.validation_packs import load_validation_packs, evaluate_pack_candidate, compare_to_reference

                packs_path = Path("benchmarks/ppl_validation_packs_v3.json")
                refs_path = Path("benchmarks/ppl_validation_refs_v3.json")
                packs = load_validation_packs(packs_path)

                st.markdown("#### Validation pack selection")
                pack_titles = [f"{p.title} - ({p.pack_id})"for p in packs]
                sel = st.selectbox("Pack", pack_titles, index=0, key="ppl_pack_sel")
                pack = packs[pack_titles.index(sel)]

                st.markdown("#### Reference table")
                use_builtin = st.checkbox("Use built-in reference (placeholder)", value=True, key="ppl_use_builtin_refs")
                ref_dict = {}
                if use_builtin and refs_path.exists():
                    try:
                        ref_dict = __import__("json").loads(refs_path.read_text(encoding="utf-8")).get("refs", {}).get(pack.pack_id, {})
                    except Exception as _e:
                        st.warning(f"Could not read built-in refs: {_e}")

                up = st.file_uploader("Or upload reference JSON (expects {'refs': {pack_id: {metric_key: value}}})", type=["json"], key="ppl_ref_upload")
                if up is not None:
                    try:
                        payload = __import__("json").loads(up.read().decode("utf-8"))
                        ref_dict = payload.get("refs", {}).get(pack.pack_id, {})
                        st.success("Loaded uploaded reference table.")
                    except Exception as _e:
                        st.error(f"Could not parse reference JSON: {_e}")

                tol_scale = st.slider("Tolerance scale (multiplies per-metric tolerances)", 0.25, 3.0, 1.0, 0.05, key="ppl_tol_scale")

                if st.button("Run validation pack", key="ppl_run_pack"):
                    try:
                        preset, outputs, metrics, meta = evaluate_pack_candidate(pack)
                        # apply tol scaling on-the-fly
                        scaled_pack = type(pack)(
                            pack_id=pack.pack_id,
                            title=pack.title,
                            preset_key=pack.preset_key,
                            design_intent=pack.design_intent,
                            compare_keys=pack.compare_keys,
                            tolerances_rel={k: float(v) * float(tol_scale) for k, v in pack.tolerances_rel.items()},
                            severities=pack.severities,
                        )
                        res = compare_to_reference(pack=scaled_pack, metrics=metrics, reference=ref_dict or {})
                        st.session_state["ppl_last_validation"] = {"pack": pack.pack_id, "res": res, "meta": meta, "metrics": metrics, "reference": ref_dict}
                    except Exception as _e:
                        st.error(f"Validation run failed: {_e}")

                last = st.session_state.get("ppl_last_validation")
                if last and last.get("pack") == pack.pack_id:
                    res = last["res"]
                    st.markdown("#### Verdict")
                    if res["status"] == "PASS":
                        st.success(f"PASS - worst relative error: {res['worst_rel_err']:.3f}")
                    elif res["status"] == "WARN":
                        st.warning(f"WARN - worst relative error: {res['worst_rel_err']:.3f}")
                    else:
                        st.error(f"FAIL - worst relative error: {res['worst_rel_err']:.3f}")

                    st.markdown("#### Deltas")
                    rows = res["rows"]
                    # render as a small table
                    import pandas as _pd
                    df = _pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    with st.expander("Assumptions & constraints context", expanded=False):
                        st.json(last.get("meta", {}))
                        st.json({"metrics": last.get("metrics", {}), "reference": last.get("reference", {})})


            elif view == "Parity calibration (reference deltas)":
                st.caption(
                    "Compare SHAMS Parity outputs against a reference table (e.g., published study values). "
                    "Built-in references are placeholders; upload your program's reference JSON to calibrate."
                )
                up = st.file_uploader("Optional reference JSON (same schema as benchmarks/parity_v2_refs.json)", type=["json"], key="opt_parity_ref_upload")
                ref_path = None
                if up is not None:
                    try:
                        tmp = Path(ROOT) / ".tmp_parity_refs.json"
                        tmp.write_bytes(up.getvalue())
                        ref_path = str(tmp)
                    except Exception:
                        ref_path = None
                if st.button("Run calibration", use_container_width=True, key="opt_parity_calib_run"):
                    try:
                        from tools.parity_calibrate import run_parity_calibration
                        st.session_state["opt_parity_calib_res"] = run_parity_calibration(refs_path=ref_path)
                    except Exception as _e:
                        st.session_state["opt_parity_calib_res"] = {"ok": False, "reason": str(_e)}
                res = st.session_state.get("opt_parity_calib_res")
                if res:
                    st.json({k: res.get(k) for k in ["ok", "n_cases", "refs_path", "note"]}, expanded=False)
                    for case in res.get("results", [])[:50]:
                        nm = case.get("name")
                        ok = bool(case.get("ok"))
                        with st.expander(f"{nm} - {'PASS' if ok else 'CHECK'}", expanded=not ok):
                            st.caption(str(case.get("notes") or ""))
                            rows = case.get("rows") or []
                            if rows:
                                import pandas as _pd
                                st.dataframe(_pd.DataFrame(rows), use_container_width=True)
                            else:
                                st.info("No reference metrics defined for this case.")
            elif view == "PROCESS parity benchmarks":
                st.caption("Run the internal parity regression suite (local, deterministic).")
                upd = st.checkbox("Update golden (developer)", value=False, key="opt_parity_update_golden")
                if st.button("Run parity benchmarks", key="opt_parity_bench", use_container_width=True):
                    try:
                        from tools.parity_bench import run_parity_benchmarks
                        st.session_state["opt_parity_bench_res"] = run_parity_benchmarks(update_golden=bool(upd))
                    except Exception as _e:
                        st.session_state["opt_parity_bench_res"] = {"ok": False, "reason": str(_e)}
                if st.session_state.get("opt_parity_bench_res"):
                    st.json(st.session_state.get("opt_parity_bench_res"), expanded=False)
            
            elif view == "Decision scenarios (program lens)":
                st.caption(
                    "Scenario presets that bundle objective intent, economics conservatism, and credibility lens. "
                    "They do not change frozen truth; they set *study posture*."
                )
                scenarios = {
                    "Conservative engineering": {
            "opt_intent": "Reactor",
            "opt_pack_choice": "Compact feasible reactor",
            "ppl_cost_posture": "Conservative",
            "credibility": "Conservative",
            "note": "Bias toward margin and conservative economics; useful for program-safe screening.",
                    },
                    "Nominal program baseline": {
            "opt_intent": "Reactor",
            "opt_pack_choice": "Compact feasible reactor",
            "ppl_cost_posture": "Nominal",
            "credibility": "Nominal",
            "note": "Default posture for comparisons and internal benchmarking.",
                    },
                    "Aggressive HTS / high-field": {
            "opt_intent": "Reactor",
            "opt_pack_choice": "High-field HTS stress frontier",
            "ppl_cost_posture": "Optimistic",
            "credibility": "Aggressive",
            "note": "Exploration posture; expect fragility and tighter trust boundaries.",
                    },
                    "Research toward Reactor": {
            "opt_intent": "Research",
            "opt_pack_choice": "Closest-to-reactor feasibility",
            "ppl_cost_posture": "Nominal",
            "credibility": "Nominal",
            "note": "Use Research intent but track distance-to-reactor; strategic R&D planning.",
                    },
                }

                names = list(scenarios.keys())
                sel = st.selectbox("Scenario", names, index=1, key="ppl_scenario_sel")
                s = scenarios[sel]
                st.info(s["note"])

                colA, colB = st.columns([1, 1])
                with colA:
                    st.markdown("**Scenario settings**")
                    st.json({k: v for k, v in s.items() if k != "note"})
                with colB:
                    st.markdown("**Apply**")
                    if st.button("Apply scenario to session", key="ppl_apply_scenario"):
                        # apply to optimization setup controls
                        st.session_state["opt_intent"] = s["opt_intent"]
                        st.session_state["opt_pack_choice"] = s["opt_pack_choice"]
                        st.session_state["ppl_cost_posture"] = s["ppl_cost_posture"]
                        st.session_state["ppl_credibility"] = s["credibility"]
                        st.success("Scenario applied. Return to Setup and run Machine Finder, or inspect Parity Workbench.")
                    st.markdown("**Economics posture**")
                    posture = st.selectbox(
            "Cost envelope posture",
            ["Optimistic", "Nominal", "Conservative"],
            index=["Optimistic","Nominal","Conservative"].index(st.session_state.get("ppl_cost_posture","Nominal")),
            key="ppl_cost_posture",
                    )
                    st.caption("Used for economics envelope display and scenario labeling (nominal truth is unchanged).")

            elif view == "Trace Telemetry":
                tr = run.get("trace") or []
                if tr:
                    import pandas as _pd
                    df=_pd.DataFrame(tr)
                    st.line_chart(df[["score"]])
                    st.caption("Trace shows score progression; feasibility and resistance are summarized in the atlas.")
                else:
                    st.info("No trace recorded.")
            elif view == "Resistance Brief":
                st.json(run.get("resistance", {}))
                st.json(run.get("variable_correlations", {}))
            elif view == "Boundary Navigator":
                st.caption(
                    "Local linear surface model for a single constraint, fitted from near-boundary points in the archive. "
                    "This is an instrument to understand geometry; it does not recommend designs."
                )
                vs = run.get("var_specs") or []
                vkeys = []
                for v in vs:
                    if isinstance(v, dict) and v.get("key"):
                        vkeys.append(str(v.get("key")))
                    else:
                        try:
                            vkeys.append(str(getattr(v, "key")))
                        except Exception:
                            pass
                # available constraints
                names = []
                sample = None
                for a in (run.get("archive") or []):
                    if (a.get("constraints") or []):
                        sample = a
                        break
                if sample is not None:
                    for c in (sample.get("constraints") or []):
                        nm = str(c.get("name"))
                        if nm and nm not in names:
                            names.append(nm)
                if not vkeys:
                    st.info("No optimized variables found in this run.")
                elif not names:
                    st.info("No constraint records found in archive candidates.")
                else:
                    cn = st.selectbox("Constraint", options=names, index=0, key="opt_surface_constraint")
                    use_archive = st.checkbox("Use filtered archive", value=True, key="opt_surface_use_filtered")
                    data_src = filt if (use_archive and isinstance(filt, list) and filt) else (run.get("archive") or [])
                    m = constraint_surface_map(archive=data_src, var_keys=vkeys, constraint_name=cn)
                    st.json(m)
            elif view == "Feasibility skeleton":
                sk = run.get("feasibility_skeleton") or {}
                if not sk:
                    st.info("Skeleton not available (need feasible points).")
                else:
                    st.metric("Feasible points", str(sk.get("n_feasible", "-")))
                    st.metric("Components", str(sk.get("n_components", "-")))
                    st.write({"component_sizes": sk.get("components", [])})
                    with st.expander("Bottleneck edges (longest kNN edges)", expanded=False):
                        st.write(sk.get("bottleneck_edges", []))
                    st.caption("Use this to see whether feasible truth is one connected basin or multiple islands.")
            elif view == "Local cartography (adaptive)":
                st.caption("A small 2D scan around the selected/ best candidate. This is cartography, not optimization.")
                base = None
                if isinstance(run.get("best_feasible"), dict):
                    base = run.get("best_feasible")
                if filt:
                    base = filt[int(min(len(filt)-1, int(st.session_state.get("opt_inspect_idx", 0))))]
                if base is None:
                    st.info("No candidate to center local cartography on.")
                else:
                    vs = run.get("var_specs") or []
                    vkeys = [v.get("key") for v in vs if isinstance(v, dict) and v.get("key")]
                    if len(vkeys) < 2:
                        st.info("Need at least two optimized variables.")
                    else:
                        xk = st.selectbox("x variable", vkeys, index=0, key="opt_localcart_x")
                        yk = st.selectbox("y variable", vkeys, index=min(1, len(vkeys)-1), key="opt_localcart_y")
                        span = st.slider("Span (±% of local bounds)", 5, 60, 20, key="opt_localcart_span")
                        ngrid = st.slider("Grid", 9, 41, 21, step=2, key="opt_localcart_ng")
                        if st.button("Run local cartography", key="opt_localcart_run"):
                            import numpy as _np
                            import pandas as _pd
                            bx = (base.get("inputs") or {}).get(xk)
                            by = (base.get("inputs") or {}).get(yk)
                            # bounds
                            bmap = {v.get("key"):(float(v.get("lo")), float(v.get("hi"))) for v in vs if isinstance(v, dict) and v.get("key")}
                            xlo,xhi = bmap.get(xk,(float(bx)*0.8,float(bx)*1.2))
                            ylo,yhi = bmap.get(yk,(float(by)*0.8,float(by)*1.2))
                            xmid = float(bx) if bx is not None else 0.5*(xlo+xhi)
                            ymid = float(by) if by is not None else 0.5*(ylo+yhi)
                            dx = (xhi-xlo)*float(span)/100.0
                            dy = (yhi-ylo)*float(span)/100.0
                            xs = _np.linspace(max(xlo, xmid-dx), min(xhi, xmid+dx), int(ngrid))
                            ys = _np.linspace(max(ylo, ymid-dy), min(yhi, ymid+dy), int(ngrid))
                            rows=[]
                            for xv in xs:
                                for yv in ys:
                                    cand_in = dict(base.get("inputs") or {})
                                    cand_in[xk] = float(xv)
                                    cand_in[yk] = float(yv)
                                    r = eval_fn(cand_in)
                                    rows.append({"x":float(xv),"y":float(yv),"feasible":bool(r.get("feasible",False)),"score":float(r.get("_score",-1e30)),"violation":float(r.get("_violation",1e30)),"min_margin":float(r.get("min_signed_margin",float("nan")))})
                            df=_pd.DataFrame(rows)
                            st.session_state["opt_localcart_df"] = df
                        df = st.session_state.get("opt_localcart_df")
                        if df is not None:
                            try:
                                import numpy as _np
                                import matplotlib.pyplot as _plt
                                dff = df.pivot(index="y", columns="x", values="feasible")
                                fig = _plt.figure()
                                _plt.imshow(dff.values[::-1, :], aspect="auto")
                                _plt.title("Feasibility map (local)")
                                st.pyplot(fig)
                                st.caption("Heatmap shows feasible (1) vs infeasible (0). Use Inspector for details.")
                            except Exception:
                                st.dataframe(df)
            elif view == "Uncertainty (Monte Carlo)":
                st.caption("Monte Carlo robustness is optional. It does **not** change feasibility truth; it samples around a candidate.")
                if not filt:
                    st.info("No candidates available.")
                else:
                    cand = filt[int(min(len(filt)-1, int(st.session_state.get("opt_inspect_idx", 0))))]
                    ns = st.number_input("Samples", 20, 2000, 200, step=20, key="opt_uq_ns")
                    pct = st.slider("Perturbation (±% on optimized vars)", 1, 25, 5, key="opt_uq_pct")
                    if st.button("Run robustness Monte Carlo", key="opt_uq_run"):
                        import numpy as _np
                        rng = _np.random.default_rng(1)
                        vs = run.get("var_specs") or []
                        vkeys = [v.get("key") for v in vs if isinstance(v, dict) and v.get("key")]
                        base_in = dict(cand.get("inputs") or {})
                        feas=0
                        scores=[]
                        for _ in range(int(ns)):
                            ci = dict(base_in)
                            for k in vkeys:
                                v0 = float(base_in.get(k, 0.0))
                                dv = v0 * float(pct)/100.0
                                ci[k] = float(rng.uniform(v0-dv, v0+dv))
                            r = eval_fn(ci)
                            if r.get("feasible", False):
                                feas += 1
                                scores.append(float(r.get("_score", -1e30)))
                        st.session_state["opt_uq_res"] = {
                            "samples": int(ns),
                            "pct": float(pct),
                            "feasible_rate": float(feas)/float(ns),
                            "mean_score_feasible": float(_np.mean(scores)) if scores else None,
                            "n_feasible": int(feas),
                        }
                    if st.session_state.get("opt_uq_res"):
                        st.json(st.session_state.get("opt_uq_res"))
            elif view == "Intent trajectories (Research→Reactor)":
                st.caption(
                    "Tier-5: a simple *intent trajectory* instrument. "
                    "It tries to build a Research→Reactor 'highway' using the current archive and the currently selected variables. "
                    "This does not optimize; it organizes what you already found."
                )
                traj = st.session_state.get("opt_traj")
                if not traj:
                    st.info("Click **Build trajectory** in the left Tier 5–6 expander to compute a path.")
                else:
                    if not traj.get("ok", False):
                        st.warning(f"Trajectory unavailable: {traj.get('reason')}")
                        st.json(traj, expanded=False)
                    else:
                        st.success(f"Trajectory built: {traj.get('from_intent')} → {traj.get('to_intent')} (steps={len(traj.get('nodes') or [])})")
                        nodes = traj.get("nodes") or []
                        edges = traj.get("edges") or []
                        import pandas as _pd
                        rows = []
                        for i, n in enumerate(nodes):
                            rows.append({
                                "step": i,
                                "from_feasible": bool(n.get("from_feasible")),
                                "to_feasible": bool(n.get("to_feasible")),
                                "from_score": float(n.get("from_score", -1e30)),
                                "to_score": float(n.get("to_score", -1e30)),
                            })
                        st.dataframe(_pd.DataFrame(rows), use_container_width=True)
                        with st.expander("Step inputs", expanded=False):
                            for i, n in enumerate(nodes):
                                st.markdown(f"**Step {i} inputs**")
                                st.json(n.get("inputs") or {}, expanded=False)
                                if i < len(edges):
                                    st.caption(f"Δ to next (L2 dist ≈ {float(edges[i].get('dist', 0.0)):.4g})")
                                    st.json(edges[i].get("delta") or {}, expanded=False)
                        import json as _json
                        st.download_button(
                            "Download trajectory (json)",
                            data=_json.dumps(traj, indent=2).encode("utf-8"),
                            file_name="shams_intent_trajectory.json",
                            mime="application/json",
                            use_container_width=True,
                        )

            elif view == "Inverse design / Why not?":
                st.caption(
                    "Tier-5: inverse design (closest feasible to a target) + 'why not' explanation. "
                    "This never relaxes constraints; it searches only within your declared bounds."
                )
                targets = st.session_state.get("opt_inv_targets") or {}
                st.markdown("**Targets**")
                st.json(targets, expanded=False)

                n_samples = st.number_input("Inverse search samples", 50, 5000, 600, step=50, key="opt_inv_ns")
                if st.button("Run inverse search (closest feasible)", key="opt_inv_run", use_container_width=True):
                    # Sample uniformly in declared bounds and pick feasible with min residual.
                    import numpy as _np
                    rng = _np.random.default_rng(int(run.get("seed", 0)) + 17)
                    vs = run.get("var_specs") or []
                    vkeys = [v.get("key") for v in vs if isinstance(v, dict) and v.get("key")]
                    # If var_specs not present, fall back to current var_keys + bounds
                    if not vkeys:
                        vkeys = list(bounds.keys())
                    best_res = None
                    best_eval = None
                    best_inputs = None
                    for _ in range(int(n_samples)):
                        cand_in = dict(anchor_default)
                        for k in vkeys:
                            lo, hi = bounds.get(k, (float(cand_in.get(k, 0.0)), float(cand_in.get(k, 0.0))))
                            cand_in[k] = float(rng.uniform(float(lo), float(hi)))
                        r = _evaluate_candidate(cand_in, intent)
                        if not r.get("feasible", False):
                            continue
                        resid = inverse_design_residual(r.get("outputs") or {}, targets)
                        if best_res is None or resid < best_res:
                            best_res = float(resid)
                            best_eval = r
                            best_inputs = cand_in
                    st.session_state["opt_inv_best"] = {"residual": best_res, "eval": best_eval, "inputs": best_inputs}

                inv_best = st.session_state.get("opt_inv_best")
                if inv_best and inv_best.get("eval"):
                    st.success(f"Best feasible inverse match residual: {float(inv_best.get('residual')):.4g}")
                    st.json(inv_best.get("inputs") or {}, expanded=False)
                    st.json((inv_best.get("eval") or {}).get("outputs") or {}, expanded=False)
                    with st.expander("Why-not style report (for this candidate)", expanded=False):
                        st.json(why_not_report(eval_res=inv_best.get("eval") or {}, disabled_constraints=st.session_state.get("opt_cf_disable") or []), expanded=False)
                else:
                    st.info("Run inverse search to find the closest feasible candidate to your targets.")

                # Why-not for selected candidate in inspector
                st.divider()
                st.markdown("**Why not for the currently selected candidate (Inspector index)**")
                if filt:
                    cand = filt[int(min(len(filt)-1, int(st.session_state.get("opt_inspect_idx", 0))))]
                    wr = why_not_report(
                        eval_res=cand,
                        disabled_constraints=st.session_state.get("opt_cf_disable") or [],
                    )
                    st.json(wr, expanded=False)
                else:
                    st.info("No candidate selected.")

            elif view == "Discovered relations (laws)":
                st.caption(
                    "Tier-6: mine simple, explainable relations from the feasible archive. "
                    "This is not a physics claim; it's a data-derived hint to guide exploration."
                )
                import pandas as _pd
                x_opts = ["R0_m","a_m","Bt_T","Ip_MA","Paux_MW","kappa","delta","nbar_1e20_m3","Ti_keV"]
                y_opts = ["P_e_net_MW","Pfus_total_MW","Q_DT_eqv","q_div_MW_m2","min_signed_margin"]
                x_sel = st.multiselect("x variables", x_opts, default=["R0_m","Bt_T","Ip_MA"], key="opt_rel_x")
                y_sel = st.multiselect("y metrics", y_opts, default=["P_e_net_MW","q_div_MW_m2"], key="opt_rel_y")
                feas_only = st.checkbox("Use feasible candidates only", value=True, key="opt_rel_feas")
                if st.button("Compute discovered relations", key="opt_rel_run", use_container_width=True):
                    st.session_state["opt_rel"] = discovered_relations(
                        candidates=archive,
                        x_keys=x_sel,
                        y_keys=y_sel,
                        feasible_only=bool(feas_only),
                        top_k=8,
                    )
                rel = st.session_state.get("opt_rel")
                if rel and rel.get("ok"):
                    st.success(f"Computed relations from n={rel.get('n')} candidates")
                    st.markdown("**Top linear fits**")
                    st.write(rel.get("top_linear_fits"))
                    st.markdown("**Top correlations**")
                    st.write(rel.get("top_corrs"))
                    md = export_relations_markdown(rel)
                    st.download_button(
                        "Download relations report (markdown)",
                        data=md.encode("utf-8"),
                        file_name="shams_discovered_relations.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )
                else:
                    st.info("Compute relations to see the strongest correlations and simple fits.")

            elif view == "Counterfactual lens":
                st.caption(
                    "Tier-6: counterfactual lens. You can disable one or more constraints in the **feasibility gate** only. "
                    "Raw constraints stay unchanged; this is a hypothetical planning tool."
                )
                disabled = st.session_state.get("opt_cf_disable") or []
                if not disabled:
                    st.info("Select constraints to disable in the left Tier 5–6 expander.")
                else:
                    st.warning(f"Counterfactual disabled constraints: {disabled}")
                    cf_feas = 0
                    cf_best = None
                    cf_best_score = -1e30
                    for c in filt:
                        cf = counterfactual_gate(c, disabled).get("counterfactual") or {}
                        if cf.get("feasible", False):
                            cf_feas += 1
                            sc = float(c.get("_score", -1e30))
                            if sc > cf_best_score:
                                cf_best_score = sc
                                cf_best = c
                    st.metric("Counterfactual feasible (filtered)", f"{cf_feas} / {len(filt)}")
                    if cf_best is not None:
                        st.markdown("**Best (by score) among counterfactual-feasible**")
                        st.json(cf_best.get("inputs") or {}, expanded=False)
                        st.json((cf_best.get("outputs") or {}), expanded=False)
                        with st.expander("Counterfactual gate details", expanded=False):
                            st.json(counterfactual_gate(cf_best, disabled).get("counterfactual"), expanded=False)
                    st.divider()
                    st.markdown("**Inspector candidate under counterfactual**")
                    if filt:
                        cand = filt[int(min(len(filt)-1, int(st.session_state.get("opt_inspect_idx", 0))))]
                        st.json(counterfactual_gate(cand, disabled).get("counterfactual"), expanded=False)

            elif view == "Collaboration (review sessions)":
                st.caption(
                    "Tier-7: multi-user deliberation without external services. "
                    "Create a review session to attach comments/votes/tags to candidates, then export a session bundle."
                )
                _repo_root = Path(__file__).resolve().parent.parent
                _eval_fp = repo_fingerprint(_repo_root)
                sessions_dir = default_sessions_dir()
                st.markdown(f"**Local sessions dir:** `{sessions_dir}`")

                colA, colB = st.columns(2)
                with colA:
                    title = st.text_input("New session title", value=st.session_state.get("opt_review_title", "Optimization review"), key="opt_review_title")
                    notes = st.text_area("Session notes (optional)", value=st.session_state.get("opt_review_notes", ""), key="opt_review_notes")
                    if st.button("Create new session", key="opt_review_create", use_container_width=True):
                        sess = new_review_session(title=title, evaluator_fp=_eval_fp, intent=run.get("intent", ""), notes=notes)
                        path = sessions_dir / f"{sess.session_id}.json"
                        save_review_session(sess, path)
                        st.session_state["opt_review_path"] = str(path)
                        st.success(f"Created session: {sess.session_id}")

                with colB:
                    existing = sorted([p.name for p in sessions_dir.glob("*.json")])
                    pick = st.selectbox("Load existing session", options=[""] + existing, index=0, key="opt_review_pick")
                    if pick:
                        path = sessions_dir / pick
                        try:
                            sess = load_review_session(path)
                            st.session_state["opt_review_path"] = str(path)
                            st.success(f"Loaded session: {sess.session_id}")
                        except Exception as e:
                            st.error(f"Failed to load session: {e}")

                # Load active session
                sess = None
                sp = st.session_state.get("opt_review_path")
                if sp:
                    try:
                        sess = load_review_session(Path(sp))
                    except Exception:
                        sess = None

                if sess is None:
                    st.info("Create or load a review session to start commenting/voting.")
                else:
                    st.markdown("### Session")
                    st.json({
                        "session_id": sess.session_id,
                        "title": sess.title,
                        "created_at": sess.created_at,
                        "intent": sess.intent,
                        "evaluator_fp": sess.evaluator_fp[:12],
                        "n_candidates": len(sess.candidates or []),
                        "n_comments": len(sess.comments or []),
                        "n_votes": len(sess.votes or []),
                    }, expanded=False)

                    # Add current inspector candidate
                    if filt:
                        idx = int(st.session_state.get("opt_inspect_idx", 0))
                        idx = int(max(0, min(len(filt)-1, idx)))
                        cand = filt[idx]
                        if st.button("Add current inspector candidate to session", key="opt_review_add", use_container_width=True):
                            _c_fp = candidate_fingerprint(cand.get("inputs", {}) or {}, intent=run.get("intent", ""), evaluator_fp=_eval_fp)
                            # de-dup
                            if not any((c.get("candidate_fp") == _c_fp) for c in (sess.candidates or [])):
                                sess.candidates.append({
                                    "candidate_fp": _c_fp,
                                    "score": cand.get("_score"),
                                    "feasible": cand.get("feasible"),
                                    "min_signed_margin": cand.get("min_signed_margin"),
                                    "inputs": cand.get("inputs", {}),
                                    "failure_mode": cand.get("failure_mode"),
                                })
                                save_review_session(sess, Path(sp))
                                st.success("Added.")
                            else:
                                st.info("Candidate already in session.")

                    st.divider()
                    st.markdown("### Comment / vote")
                    cand_opts = [c.get("candidate_fp", "")[:12] + "…"for c in (sess.candidates or [])]
                    if not cand_opts:
                        st.info("Add candidates to the session to enable comments and votes.")
                    else:
                        sel = st.selectbox("Candidate", options=list(range(len(cand_opts))), format_func=lambda i: cand_opts[i], key="opt_review_cand_sel")
                        comment = st.text_area("Comment", key="opt_review_comment")
                        vote = st.slider("Vote (1–5)", 1, 5, 3, key="opt_review_vote")
                        tag = st.text_input("Tag (optional)", value="", key="opt_review_tag")
                        cols = st.columns(3)
                        if cols[0].button("Add comment", key="opt_review_add_comment"):
                            sess.comments.append({
                                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                "candidate_fp": sess.candidates[int(sel)].get("candidate_fp"),
                                "text": comment,
                            })
                            save_review_session(sess, Path(sp))
                            st.success("Comment added.")
                        if cols[1].button("Cast vote", key="opt_review_add_vote"):
                            sess.votes.append({
                                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                "candidate_fp": sess.candidates[int(sel)].get("candidate_fp"),
                                "vote": int(vote),
                            })
                            save_review_session(sess, Path(sp))
                            st.success("Vote recorded.")
                        if cols[2].button("Add tag", key="opt_review_add_tag"):
                            if tag.strip():
                                sess.tags.append({
                                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                    "candidate_fp": sess.candidates[int(sel)].get("candidate_fp"),
                                    "tag": tag.strip(),
                                })
                                save_review_session(sess, Path(sp))
                                st.success("Tag added.")

                    with st.expander("Session data", expanded=False):
                        st.json(sess.to_dict(), expanded=False)

                    st.divider()
                    st.markdown("### Export / import")
                    st.download_button(
                        "Download review session bundle (.zip)",
                        data=export_review_session_zip(sess),
                        file_name=f"shams_review_session_{sess.session_id}.zip",
                        mime="application/zip",
                        use_container_width=True,
                    )
                    up = st.file_uploader("Import review session bundle", type=["zip"], key="opt_review_import")
                    if up is not None:
                        try:
                            sess2 = import_review_session_zip(up.read())
                            path = sessions_dir / f"{sess2.session_id}.json"
                            save_review_session(sess2, path)
                            st.session_state["opt_review_path"] = str(path)
                            st.success(f"Imported session: {sess2.session_id}")
                        except Exception as e:
                            st.error(f"Import failed: {e}")

            elif view == "Epistemic guarantees (regression suite)":
                st.caption(
                    "Ultimate differentiator: epistemic guarantees. Run the golden regression suite to detect unintended semantic drift. "
                    "This does not validate against reality; it enforces stability of the frozen evaluator and artifact contracts."
                )
                _repo_root = Path(__file__).resolve().parent.parent
                _eval_fp = repo_fingerprint(_repo_root)
                st.markdown(f"**Evaluator fingerprint:** `{_eval_fp}`")
                rtol = st.number_input("Relative tolerance", value=0.01, min_value=0.0, max_value=0.2, step=0.005, key="opt_reg_rtol")
                atol = st.number_input("Absolute tolerance", value=1e-6, min_value=0.0, max_value=1e-2, step=1e-6, format="%.1e", key="opt_reg_atol")
                if st.button("Run regression suite now", key="opt_reg_run", use_container_width=True):
                    st.session_state["opt_reg_report"] = run_regression_suite(_repo_root, rtol=float(rtol), atol=float(atol))
                rep = st.session_state.get("opt_reg_report")
                if rep:
                    if rep.get("ok"):
                        st.success("Regression suite PASSED.")
                    else:
                        st.error("Regression suite FAILED.")
                    with st.expander("Runner output", expanded=False):
                        st.code(rep.get("output", ""))
                    d = rep.get("diff") or {}
                    if d:
                        st.markdown("### Diff summary")
                        try:
                            st.json({
                                "numeric_failures": d.get("numeric", {}).get("summary"),
                                "structural": d.get("structural", {}).get("severity"),
                            }, expanded=False)
                        except Exception:
                            st.json(d, expanded=False)
                else:
                    st.info("Run the suite to get a pass/fail report + structured diffs.")

            elif view == "Standards & DOI export":
                st.caption(
                    "Tier-7 standards: export DOI-ready packs + SHAMS-certified feasibility badges (descriptive, non-ranking)."
                )
                _repo_root = Path(__file__).resolve().parent.parent
                _eval_fp = repo_fingerprint(_repo_root)
                version = str(st.session_state.get("app_version", ""))
                best = run.get("best_feasible")
                if not isinstance(best, dict):
                    st.info("No feasible best candidate yet. Run the machine finder first.")
                else:
                    cfp = candidate_fingerprint(best.get("inputs", {}) or {}, intent=run.get("intent", ""), evaluator_fp=_eval_fp)
                    svg = generate_cert_badge_svg(
                        candidate_fp=cfp,
                        intent=run.get("intent", ""),
                        feasible=bool(best.get("feasible", False)),
                        version=version,
                        evaluator_fp=_eval_fp,
                        note="audited by frozen evaluator",
                    )
                    st.download_button(
                        "Download SHAMS-certified badge (SVG)",
                        data=svg.encode("utf-8"),
                        file_name=f"shams_cert_badge_{cfp[:12]}.svg",
                        mime="image/svg+xml",
                        use_container_width=True,
                    )

                    # DOI-ready export pack (includes archive + trace)
                    archive_rows = run.get("archive") or []
                    trace_rows = run.get("trace") or []
                    run_meta = {
                        "schema": "shams.optimization_pack.v1",
                        "version": version,
                        "intent": run.get("intent"),
                        "seed": run.get("seed"),
                        "fingerprint": run.get("fingerprint"),
                        "evaluator_fp": _eval_fp,
                        "objectives": run.get("objectives"),
                        "var_specs": run.get("var_specs"),
                        "budgets": run.get("budgets"),
                        "notes": "Export pack is descriptive. No hidden preferences.",
                    }
                    extra = [(f"badges/shams_cert_badge_{cfp[:12]}.svg", svg.encode("utf-8"))]
                    # Attach review session if loaded
                    sp = st.session_state.get("opt_review_path")
                    if sp:
                        try:
                            sess = load_review_session(Path(sp))
                            extra.append(("review_session.json", json.dumps(sess.to_dict(), indent=2, sort_keys=True).encode("utf-8")))
                        except Exception:
                            pass
                    pack = export_doi_ready_pack(
                        repo_root=_repo_root,
                        run_meta=run_meta,
                        archive_rows=archive_rows,
                        trace_rows=trace_rows,
                        extra_files=extra,
                    )
                    st.download_button(
                        "Download DOI-ready publication pack (.zip)",
                        data=pack,
                        file_name=f"shams_optimization_publication_pack_{run.get('fingerprint','')[:12]}.zip",
                        mime="application/zip",
                        use_container_width=True,
                    )

            elif view == "Design-space verdicts (Allowed/Forbidden)":
                st.caption(
                    "Tier-8: Design-space jurisprudence. This is not a recommendation engine - it classifies what is supported by evidence in the explored region. "
                    "Forbidden here means *locally forbidden within the explored neighborhood*, not a universal impossibility theorem."
                )
                ci = feasibility_confidence_from_trace(run.get("trace") or [], window=500)
                rv = region_verdict(run.get("trace") or [], window=500)
                st.markdown("#### Region verdict (recent window)")
                st.write({
                    "verdict": rv.label,
                    "confidence": f"{rv.confidence:.2f}",
                    "rate": ci.get("rate"),
                    "ci_95": [ci.get("ci_lo"), ci.get("ci_hi")],
                    "rationale": rv.rationale,
                })
                st.markdown("#### Candidate verdict (selected)")
                if filt:
                    cand = filt[int(st.session_state.get("opt_inspect_idx", 0))]
                    vv = candidate_verdict(cand, archive=run.get("archive") or [], var_keys=var_keys, robust_margin=float(min_margin) if min_margin else 0.0)
                    st.write({"verdict": vv.label, "confidence": f"{vv.confidence:.2f}", "rationale": vv.rationale})
                else:
                    st.info("No candidates available.")

            elif view == "Epistemic confidence bounds":
                st.caption(
                    "Tier-8: Epistemic confidence bounds on feasibility rates (Wilson interval). This quantifies how strongly the *recent search evidence* supports feasibility/infeasibility."
                )
                w = st.slider("Window (last N evaluations)", 50, 2000, 500, 50, key="opt_ci_window")
                ci = feasibility_confidence_from_trace(run.get("trace") or [], window=int(w))
                st.write(ci)
                st.markdown("**Interpretation**")
                st.write(
                    "- If `k=0` and the upper CI is very small, the explored region is strongly supported as locally infeasible.\n"
                    "- If `k>0`, feasibility is established for the explored region; the CI describes how often feasibility occurs under the current proposal distribution." 
                )

            elif view == "Intent-conditional design laws":
                st.caption(
                    "Tier-8: Intent-conditional design laws. We take top feasible candidates under the current intent and re-evaluate them under the other intent, then compare correlations."
                )
                if not filt:
                    st.info("No candidates available.")
                else:
                    other_intent = "Research"if run.get("intent") == "Reactor"else "Reactor"
                    key_y = st.text_input("Output key to analyze", value="P_e_net_MW", key="opt_laws_keyy")
                    topn = st.slider("Top feasible candidates to compare", 10, 120, 40, 5, key="opt_laws_topn")
                    def _eval_other(inp: dict) -> dict:
                        return _evaluate_candidate(inp, intent=other_intent)
                    laws = intent_conditional_laws(_eval_other, archive=run.get("archive") or [], var_keys=var_keys, key_y=str(key_y), top_n=int(topn))
                    st.write({"primary_intent": run.get("intent"), "other_intent": other_intent, "n_primary": laws.get("n_primary"), "n_other": laws.get("n_other")})
                    try:
                        import pandas as _pd
                        df = _pd.DataFrame(laws.get("rows") or [])
                        st.dataframe(df, use_container_width=True)
                    except Exception:
                        st.json(laws)

            elif view == "Machine genealogy":
                st.caption(
                    "Tier-9: Machine genealogy. When engines do not record parents explicitly, SHAMS reconstructs a conservative ancestry graph: each candidate's parent is its nearest better neighbor in variable space."
                )
                if not filt:
                    st.info("No candidates available.")
                else:
                    maxch = st.slider("Max children per parent (for readability)", 3, 30, 12, 1, key="opt_gene_maxch")
                    g = reconstruct_genealogy(run.get("archive") or [], var_keys=var_keys, max_children_per_parent=int(maxch))
                    st.write({"roots": g.get("roots"), "num_nodes": len(g.get("parents") or {})})
                    # Render a small textual tree for the top few roots
                    roots = list(g.get("roots") or [])[:5]
                    parents = g.get("parents") or {}
                    children = g.get("children") or {}
                    def _node_label(i: int) -> str:
                        try:
                            a = (run.get("archive") or [])[int(i)]
                            return f"#{i} | feas={bool(a.get('feasible'))} | score={float(a.get('_score', -1e30)):.3g} | m={float(a.get('min_signed_margin', float('nan'))):.3g}"
                        except Exception:
                            return f"#{i}"
                    def _render(i: int, depth: int = 0, maxd: int = 3):
                        lines = [" "*depth + "- "+ _node_label(i)]
                        if depth >= maxd:
                            return lines
                        for ch in (children.get(i) or [])[:10]:
                            lines.extend(_render(int(ch), depth+1, maxd))
                        return lines
                    with st.expander("Genealogy tree (top roots)", expanded=False):
                        text = []
                        for r in roots:
                            text.extend(_render(int(r), 0, 3))
                        st.code("\n".join(text))

            elif view == "Counter-optimization (no interior optimum)":
                st.caption(
                    "Tier-9: Counter-optimization. This does not claim mathematical proofs; it reports evidence that improvement is boundary-limited (no interior optimum) under the current search space."
                )
                key_obj = st.text_input("Objective key (default: _score)", value="_score", key="opt_counter_key")
                rep = counter_optimization_report(run.get("archive") or [], key_obj=str(key_obj))
                if rep.get("status") == "ok":
                    if rep.get("boundary_limited"):
                        st.warning(rep.get("message"))
                    else:
                        st.info(rep.get("message"))
                else:
                    st.info(rep.get("message"))
                st.json(rep, expanded=False)

            elif view == "Reproducibility":
                st.caption("Audit capsule: fingerprint + config + optional citation.")
                st.json({
                    "fingerprint": run.get("fingerprint"),
                    "intent": run.get("intent"),
                    "seed": run.get("seed"),
                    "objectives": run.get("objectives"),
                    "var_specs": run.get("var_specs"),
                    "budgets": run.get("budgets"),
                }, expanded=False)
                try:
                    from pathlib import Path as _Path
                    cff = (_Path(__file__).resolve().parent.parent / "CITATION.cff").read_text(encoding="utf-8")
                    with st.expander("CITATION.cff", expanded=False):
                        st.code(cff, language="yaml")
                    try:
                        pm_path = _Path(__file__).resolve().parent.parent / "examples"/ "published_machines.json"
                        if pm_path.exists():
                            import json as _json
                            pm = _json.loads(pm_path.read_text(encoding="utf-8"))
                            with st.expander("Published machine overlay (optional)", expanded=False):
                                st.json(pm)
                    except Exception:
                        pass
                except Exception:
                    pass
            else:
                st.info("Pareto view: available when ≥2 objectives are configured.")

        # RIGHT: inspector
        with right:
            st.markdown("### Inspector")
            idx = st.number_input("Candidate index (in filtered archive)", 0, max(0, len(filt)-1), 0, key="opt_inspect_idx")
            if filt:
                cand = filt[int(idx)]
                st.markdown("**Candidate summary**")
                st.write({
                    "feasible": bool(cand.get("feasible", False)),
                    "score": float(cand.get("_score", -1e30)),
                    "min_signed_margin": float(cand.get("min_signed_margin", float("nan"))),
                    "failure_mode": cand.get("failure_mode"),
                    "dominant_constraints": cand.get("active_constraints", [])[:5],
                })
                with st.expander("Inputs", expanded=False):
                    st.json(cand.get("inputs", {}))
                with st.expander("Key outputs", expanded=False):
                    outs = cand.get("outputs", {}) or {}
                    keys_show = ["P_e_net_MW","Pfus_total_MW","Q_DT_eqv","q_div_MW_m2","B_peak_T","Ti_keV","nbar_1e20_m3"]
                    st.json({k: outs.get(k) for k in keys_show if k in outs})
                with st.expander("Constraint margins (blocking/diagnostic/ignored)", expanded=False):
                    _cons = cand.get("constraints", []) or []
                    # Optional credibility overlay (display-only)
                    try:
                        if st.session_state.get("opt_use_cred") and st.session_state.get("opt_cred_map"):
                            _cm = {
                                k: ConstraintCred(
                                    name=v.get("name", k),
                                    maturity=float(v.get("maturity", 0.7)),
                                    uncertainty_frac=float(v.get("uncertainty_frac", 0.10)),
                                    conservative=bool(v.get("conservative", True)),
                                )
                                for k, v in (st.session_state.get("opt_cred_map") or {}).items()
                            }
                            _cons = apply_credibility_overlay(_cons, _cm)
                    except Exception:
                        pass
                    st.write(_cons[:80])
                if enable_multi_intent and cand.get("other_intent"):
                    with st.expander("Other Intent distance (instrumentation)", expanded=False):
                        st.write({
                            "other_intent": cand.get("other_intent"),
                            "other_feasible": cand.get("other_feasible"),
                            "other_violation": cand.get("other_violation"),
                            "other_min_signed_margin": cand.get("other_min_signed_margin"),
                            "other_failure_mode": cand.get("other_failure_mode"),
                        })
                if use_cost:
                    with st.expander("Cost proxies (transparent)", expanded=False):
                        st.json(cand.get("cost", {}))

                st.markdown("**Actions (explicit, reversible)**")
                if st.button("Send to Systems Mode (as starting point)", key="opt_send_systems"):
                    st.session_state["systems_seed_inputs"] = dict(cand.get("inputs", {}))
                    st.success("Sent to Systems Mode seed (session-only).")
                if st.button("Open in Point Designer (read-only)", key="opt_send_point"):
                    st.session_state["point_inputs_last"] = dict(cand.get("inputs", {}))
                    st.success("Loaded into Point Designer inputs (session-only).")

                if st.button("Open Scan Lab slice around this candidate", key="opt_send_scan"):
                    try:
                        inp = cand.get("inputs") or {}
                        # Default axes chosen for expert usefulness
                        xk, yk = "Ip_MA", "R0_m"
                        x0 = float(inp.get(xk, 0.0)); y0 = float(inp.get(yk, 0.0))
                        # ±10% local neighborhood (bounded away from zero)
                        def _band(v: float) -> tuple[float,float]:
                            dv = max(0.05*abs(v), 0.01)
                            return (v - dv, v + dv)
                        xlo, xhi = _band(x0)
                        ylo, yhi = _band(y0)
                        st.session_state["scan_cart_x_key"] = xk
                        st.session_state["scan_cart_y_key"] = yk
                        st.session_state["scan_cart_x_lo"] = float(xlo)
                        st.session_state["scan_cart_x_hi"] = float(xhi)
                        st.session_state["scan_cart_y_lo"] = float(ylo)
                        st.session_state["scan_cart_y_hi"] = float(yhi)
                        st.session_state["scan_cart_nx"] = 31
                        st.session_state["scan_cart_ny"] = 25
                        st.session_state["scan_cart_intents"] = [str(run.get("intent") or "Reactor")]
                        st.session_state["scan_cart_inc_out"] = False
                        st.success("Scan Lab settings prepared. Click the Scan Lab tab and press Run cartography scan.")
                    except Exception as e:
                        st.error(f"Failed to prepare Scan Lab slice: {e}")

            else:
                st.info("No candidates to inspect.")
    # --- Stateful: operating envelope check (multi-point) ---
    st.subheader("Operating envelope check (multi-point)")
    st.caption("Evaluates startup / nominal / end-of-life proxy points and reports the worst constraint.")
    colA, colB = st.columns([1,3])
    with colA:
        run_env = st.button("Run envelope check", use_container_width=True)
    if run_env:
        try:
            from envelope.points import default_envelope_points
            from constraints.system import build_constraints_from_outputs, summarize_constraints
            base_inp = st.session_state.get("last_point_inp", None)
            if base_inp is None:
                st.warning("No current point inputs available.")
            else:
                _warn_unrealistic_point_inputs(base_inp, context="Envelope check")
                pts = default_envelope_points(base_inp)
                env_rows = []
                worst = None
                for i, p in enumerate(pts):
                    out = _ui_evaluate(p, origin="envelope_scan")
                    cs = build_constraints_from_outputs(out)
                    summ = summarize_constraints(cs)
                    dom = summ.get("dominant", {})
                    row = {
                        "point": i,
                        "all_ok": bool(summ.get("all_ok", False)),
                        "dominant": dom.get("name", ""),
                        "residual": dom.get("residual", float("nan")),
                        "margin": dom.get("margin", float("nan")),
                    }
                    env_rows.append(row)
                    if worst is None or (row["residual"] == row["residual"] and row["residual"] > worst["residual"]):
                        worst = row
                st.dataframe(env_rows, use_container_width=True)
                if worst:
                    st.info(f"Worst point: #{worst['point']} - {worst['dominant']} (residual={worst['residual']:.3g})")
        except Exception as e:
            st.error(f"Envelope check failed: {e}")
