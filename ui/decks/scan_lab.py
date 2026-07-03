"""Scan Lab deck -- extracted from ui/app.py (UI redesign batch 5).

Pure move + cosmetic de-emoji. No physics, constraint, solver, evaluator,
session-state key, or routing-ID changes. Namespace bridge (including app.py's
__file__) keeps path computations and bare names resolving as before. Temporary
tech debt; replace with explicit imports/ctx in a later cleanup commit.
"""
from __future__ import annotations
import streamlit as st
import sys


def render_scan_lab(_app_module) -> None:
    _g = globals()
    for _k, _v in vars(_app_module).items():
        if not _k.startswith('__'):
            _g[_k] = _v
    _g['__file__'] = _app_module.__file__

    from ui.components import kpi_row, empty_state

    # DSG: auto edge-kind tagging by active panel (exploration only)
    if bool(st.session_state.get("dsg_edge_kind_auto", True)):
        st.session_state["dsg_context_edge_kind"] = "scan"

    st.header("Scan Lab")
    st.caption("Cartography over the frozen evaluator: map feasibility, emptiness, fragility, and dominant mechanisms. Deterministic; no internal optimizer.")
    render_mode_scope("scan")

    # ---- Verdict-first banner (UI redesign): show the latest scan's one-glance
    # truth above the scan controls. Read-only from the cached cartography report;
    # triggers no scan and modifies no state. The detailed result section below
    # remains the full view.
    try:
        _scan_vf_rep = st.session_state.get("scan_cartography_report")
        if isinstance(_scan_vf_rep, dict):
            _scan_vf_nar_all = _scan_vf_rep.get("narrative") or {}
            _scan_vf_nar_int = (_scan_vf_nar_all.get("intents") or {}) if isinstance(_scan_vf_nar_all, dict) else {}
            _scan_vf_intents = _scan_vf_rep.get("intents") or []
            if not _scan_vf_intents:
                _scan_vf_intents = ["Reactor"]
            _scan_vf_it = str(_scan_vf_intents[0])
            _scan_vf_n0 = _scan_vf_nar_int.get(_scan_vf_it, {}) if isinstance(_scan_vf_nar_int, dict) else {}
            _scan_vf_feas = float(_scan_vf_n0.get("blocking_feasible_rate", 0.0)) if isinstance(_scan_vf_n0, dict) else 0.0
            _scan_vf_top = (_scan_vf_n0.get("dominance_ranked") or []) if isinstance(_scan_vf_n0, dict) else []
            _scan_vf_dom = (_scan_vf_top[0].get("constraint") if _scan_vf_top else None) or "(none)"
            _scan_vf_cliff = float(_scan_vf_n0.get("cliffiness_proxy", 0.0)) if isinstance(_scan_vf_n0, dict) else 0.0
            if _scan_vf_feas >= 0.85:
                _scan_vf_rb = "Robust"
            elif _scan_vf_feas >= 0.55:
                _scan_vf_rb = "Balanced"
            elif _scan_vf_feas >= 0.25:
                _scan_vf_rb = "Brittle"
            else:
                _scan_vf_rb = "Knife-edge"
            st.markdown("### One-glance truth")
            kpi_row([
                ("Dominant constraint", str(_scan_vf_dom)),
                (f"Feasible fraction ({_scan_vf_it})", f"{_scan_vf_feas*100:.0f}%"),
                ("Robustness verdict", _scan_vf_rb),
                ("Cliffiness proxy", f"{_scan_vf_cliff:.2f}"),
            ])
        else:
            empty_state("No cartography scan results yet. Run a scan below to populate the verdict.", kind="info")
    except Exception:
        st.caption("Verdict banner unavailable (non-fatal).")


    # --- World-class Scan Lab (v188) ---
    # NOTE: Scan Lab should remain usable even if optional features fail to import.
    # Import errors are captured and surfaced explicitly (freeze-readiness requirement).
    _scan_import_errors = []

    try:
        # Fix: evaluator lives under src/ in the merged repo layout.
        from src.evaluator.core import Evaluator  # type: ignore
    except Exception as _e:
        Evaluator = None  # type: ignore
        _scan_import_errors.append(f"Evaluator import failed: {_e}")

    try:
        from tools.scan_cartography import build_cartography_report
    except Exception as _e:
        build_cartography_report = None  # type: ignore
        _scan_import_errors.append(f"scan_cartography import failed: {_e}")

    try:
        from tools.golden_scans import build_golden_scan_presets
    except Exception as _e:
        build_golden_scan_presets = None  # type: ignore
        _scan_import_errors.append(f"golden_scans import failed: {_e}")

    try:
        from tools.canonical_questions import build_canonical_questions
    except Exception as _e:
        build_canonical_questions = None  # type: ignore
        _scan_import_errors.append(f"canonical_questions import failed: {_e}")

    try:
        from tools.scan_insights import (
            build_causality_trace,
            uncertainty_stress_test,
            time_to_failure_along_knob,
            null_direction_2d,
        )
    except Exception as _e:
        build_causality_trace = None  # type: ignore
        uncertainty_stress_test = None  # type: ignore
        time_to_failure_along_knob = None  # type: ignore
        null_direction_2d = None  # type: ignore
        _scan_import_errors.append(f"scan_insights import failed: {_e}")

    try:
        from tools.scan_next_tier import (
            local_powerlaw_fit,
            label_regime,
            explain_impossible_region,
            detect_irrelevant_constraints,
            projection_stability_check,
            path_follow_scan,
            assumption_stress_hotspots,
            counterfactual_lens,
            guided_steps,
            build_scan_atlas_pdf_bytes,
            surprise_detector,
        )
    except Exception as _e:
        local_powerlaw_fit = None  # type: ignore
        label_regime = None  # type: ignore
        explain_impossible_region = None  # type: ignore
        detect_irrelevant_constraints = None  # type: ignore
        projection_stability_check = None  # type: ignore
        path_follow_scan = None  # type: ignore
        assumption_stress_hotspots = None  # type: ignore
        counterfactual_lens = None  # type: ignore
        guided_steps = None  # type: ignore
        build_scan_atlas_pdf_bytes = None  # type: ignore
        surprise_detector = None  # type: ignore
        _scan_import_errors.append(f"scan_next_tier import failed: {_e}")


    try:
        from tools.scan_v1p1_worldclass import (
            build_constraint_dictionary,
            build_reproducibility_capsule,
            monotonicity_sanity_overlay,
            boundary_thickness_metric,
            explain_uncertainty_disagreement,
            to_json_bytes,
        )
    except Exception as _e:
        build_constraint_dictionary = None  # type: ignore
        build_reproducibility_capsule = None  # type: ignore
        monotonicity_sanity_overlay = None  # type: ignore
        boundary_thickness_metric = None  # type: ignore
        explain_uncertainty_disagreement = None  # type: ignore
        to_json_bytes = None  # type: ignore
        _scan_import_errors.append(f"scan_v1p1_worldclass import failed: {_e}")

    try:
        from tools.scan_expert_features import (
            SCAN_LAB_CONTRACT,
            compute_fingerprints,
            ScanClaim,
            build_claim_evidence,
            build_claim_pdf_bytes,
            falsify_claim,
        )
    except Exception as _e:
        SCAN_LAB_CONTRACT = ""# type: ignore
        compute_fingerprints = None  # type: ignore
        ScanClaim = None  # type: ignore
        build_claim_evidence = None  # type: ignore
        build_claim_pdf_bytes = None  # type: ignore
        falsify_claim = None  # type: ignore
        _scan_import_errors.append(f"scan_expert_features import failed: {_e}")

    try:
        from tools.reports.scan_signature_atlas import build_signature_atlas_pdf_bytes
    except Exception as _e:
        build_signature_atlas_pdf_bytes = None  # type: ignore
        _scan_import_errors.append(f"scan_signature_atlas import failed: {_e}")

    try:
        from tools.design_family_governance_v394 import build_design_families_from_scan_cartography
    except Exception as _e:
        build_design_families_from_scan_cartography = None  # type: ignore
        _scan_import_errors.append(f"design_family_governance_v394 import failed: {_e}")

    try:
        from tools.scan_artifact_schema import (
            build_scan_artifact,
            upgrade_scan_artifact,
            SCAN_SCHEMA_VERSION,
            stable_hash,
        )
    except Exception as _e:
        build_scan_artifact = None  # type: ignore
        upgrade_scan_artifact = None  # type: ignore
        SCAN_SCHEMA_VERSION = 0  # type: ignore
        stable_hash = None  # type: ignore
        _scan_import_errors.append(f"scan_artifact_schema import failed: {_e}")

    # Persist import errors so the UI can show them near the run buttons.
    st.session_state["scan_import_errors"] = _scan_import_errors

    def _v188_scan_lab_panel() -> None:
        import streamlit as st
        import numpy as np
        import pandas as pd
        import io
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
        import matplotlib.patches as mpatches

        st.subheader("Cartography Deck")
        _scan_deck = st.radio(
            "Scan Lab deck",
            options=["Cartography", "Orientation"],
            index=0,
            horizontal=True,
            key="scan_deck",
            help="Deck-based navigation: render one Scan workspace at a time (no scroll walls).",
        )
        if _scan_deck == "Orientation":
            with st.expander("Orientation Deck (optional, read-only helpers)", expanded=False):
                st.caption("These helpers are read-only. Switch back to Cartography to run scans.")
                st.info("Scan Lab orientation only (no scan executed).")
            st.stop()

        st.info("Scan Lab is **frozen**: deterministic cartography/interpretability over the frozen evaluator. No optimization, no relaxation, no recommendations.")

        st.caption("A microscope, not an engine: map feasibility structure and failure mechanisms across a parameter space.")

        # --- Pre-Cartography orientation (freeze-compliant; UI-only) ---
        with st.expander("Orientation Deck (optional, read-only helpers)", expanded=False):
            st.caption("These sections are optional. Cartography controls are below.")
            st.markdown("### Orientation Deck (read-only)")
            st.caption("These helpers are **read-only**. They do not change the evaluator, physics, or scan results.")
    
            with st.expander("Scan Lab is frozen - freeze statement (read-only)", expanded=False):
                c1, c2 = st.columns([1.0, 1.0])
                with c1:
                    st.markdown("**Freeze statement**: `docs/SCANLAB_FREEZE.md`")
                    st.caption("Semantics are frozen; Scan Lab is cartography/insight only.")
                with c2:
                    try:
                        from pathlib import Path
                        _sf = (Path(__file__).resolve().parent.parent / "docs"/ "SCANLAB_FREEZE.md").read_text(encoding="utf-8")
                    except Exception:
                        _sf = "(missing docs/SCANLAB_FREEZE.md)"
                    st.download_button(
                        "Download freeze statement",
                        data=_sf,
                        file_name="SCANLAB_FREEZE.md",
                        mime="text/markdown",
                        use_container_width=False,
                        key="scan_freeze_dl_pre",
                    )
                    with st.expander("View freeze statement", expanded=False):
                        st.markdown(_sf)
    
            # --- Legacy scan + stateful download (kept for backward compatibility) ---
            with st.expander("Legacy Grid Scan + stateful download (archived)", expanded=False):
                try:
                    _v93_stateful_scan_panel()
                except Exception:
                    pass
                st.markdown(
                    """
    This legacy scan performs a **nested solver grid** over (Ti, H98, a, Q, g_conf). It remains available for older workflows,
    but the recommended Scan Lab path is now the **Cartography** scan below.
                    """
                )
    
            with st.expander("Parameter guide (units, meaning, min/max)", expanded=False):
                st.markdown(
                    """
    Below are the **recommended** ranges used for input validation in this UI.  
    They are intentionally broad to avoid over‑constraining early exploration.
    
    | Parameter | Meaning | Recommended min | Recommended max |
    |---|---|---:|---:|
    | R₀ (m) | Major radius | 0.5 | 10 |
    | B₀ (T) | Toroidal field on axis | 1 | 25 |
    | Shield (m) | Neutron shield thickness | 0 | 2 |
    | P_aux (MW) | External heating power | 0 | 200 |
    | P_aux for Q (MW) | Power used in Q = P_fus / P_aux_for_Q | 0 | 200 |
    | Tᵢ/Tₑ (–) | Ion/electron temperature ratio | 0.5 | 5 |
    | Ti_start/stop (keV) | Ion temperature scan bounds | 1 | 40 |
    | Ti_step (keV) | Ion temperature step | 0.05 | 5 |
    | H98_start/stop (–) | H98y2 confinement multiplier bounds | 0.5 | 3 |
    | H98_step (–) | H98 step | 0.01 | 0.5 |
    | a_min/a_max (m) | Minor radius scan bounds | 0.2 | 5 |
    | a_step (m) | Minor radius step | 0.001 | 1 |
    | Q_start/stop (–) | Target Q scan bounds (screening target) | 0.1 | 100 |
    | Q_step (–) | Q step | 0.05 | 20 |
    | g_conf start/stop (–) | Additional confinement gain factor | 0.5 | 5 |
    | g_conf step (–) | g_conf step | 0.01 | 1 |
    | Iₚ bounds (MA) | Solver search bounds for plasma current | 1 | 50 |
    | fG bounds (–) | Greenwald fraction screening bounds | 0.01 | 1.5 |
    | tol (–) | Numerical tolerance for the solver | 1e-6 | 1e-2 |
    | Zeff (–) | Effective charge | 1.0 | 4.0 |
    | dilution_fuel (–) | Fuel dilution factor (≤1) | 0.2 | 1.0 |
    | extra_rad_factor (–) | Extra radiation multiplier | 0 | 2 |
    | alpha_loss_frac (–) | Fraction of alpha power lost | 0 | 0.5 |
    | kappa (–) | Elongation | 1.0 | 3.0 |
    | q95_min (–) | Minimum q95 constraint | 1.5 | 10 |
    | betaN_max (–) | Maximum normalized beta constraint | 1.0 | 8 |
    | C_bs (–) | Bootstrap coefficient proxy | 0 | 1 |
    | f_bs_max (–) | Max bootstrap fraction | 0 | 1 |
    | PSOL/R max (MW/m) | SOL power per major radius limit | 0 | 200 |
    | PLH_margin (–) | Extra margin over PLH if H‑mode required | 0 | 1 |
                    """
                )
    
            with st.expander("Scan Lab → Physics block mapping (what each parameter affects)", expanded=False):
                st.caption("UI-only helper: shows which Phase‑1 physics/systems blocks each Scan Lab parameter feeds.")
                rows = []
                # Keep the ordering aligned with the form layout.
                ordered = [
                    ("R0", "Major radius R₀ (m)"),
                    ("B0", "Toroidal field on axis B₀ (T)"),
                    ("tshield", "Neutron shield thickness (m)"),
                    ("Paux", "Auxiliary heating power P_aux (MW)"),
                    ("Paux_for_Q", "Aux power used in Q definition (MW)"),
                    ("Ti_over_Te", "Ion-to-electron temperature ratio Tᵢ/Tₑ (–)"),
                    ("Ti", "Ti axis (Ti_start/stop/step)"),
                    ("H98", "H98 axis (H98_start/stop/step)"),
                    ("a", "a axis (a_min/a_max/a_step)"),
                    ("Q", "Q axis (Q_start/stop/Q_step)"),
                    ("g_conf", "g_conf axis (start/stop/step)"),
                    ("Ip_bounds", "Iₚ bounds (I_p,min / I_p,max)"),
                    ("fG_bounds", "fG bounds (fG_min / fG_max)"),
                    ("tol", "tol"),
                    ("Zeff", "Zeff"),
                    ("dilution_fuel", "dilution_fuel"),
                    ("extra_rad_factor", "extra_rad_factor"),
                    ("alpha_loss_frac", "alpha_loss_frac"),
                    ("kappa", "kappa"),
                    ("q95_min", "q95_min"),
                    ("betaN_max", "betaN_max"),
                    ("C_bs", "C_bs"),
                    ("f_bs_max", "f_bs_max"),
                    ("PSOL_over_R_max", "PSOL/R max"),
                    ("require_Hmode", "Require H-mode access"),
                    ("PLH_margin", "PLH_margin"),
                    ("tblanket_m", "Blanket thickness (inboard)"),
                    ("t_vv_m", "Vacuum vessel thickness (inboard)"),
                    ("t_gap_m", "Inboard gap / clearance"),
                    ("t_tf_struct_m", "TF structure thickness (inboard)"),
                    ("t_tf_wind_m", "TF winding pack thickness (inboard)"),
                    ("Bpeak_factor", "Bpeak_factor"),
                    ("sigma_allow_MPa", "Allowable coil hoop stress"),
                    ("Tcoil_K", "HTS operating temperature"),
                    ("hts_margin_min", "HTS margin min"),
                    ("Vmax_kV", "Max dump voltage limit"),
                    ("q_div_max_MW_m2", "Max divertor heat flux limit"),
                    ("TBR_min", "TBR_min"),
                    ("hts_lifetime_min_yr", "Minimum HTS lifetime"),
                    ("P_net_min_MW", "Minimum net electric power"),
                ]
                for k, label in ordered:
                    blocks = _scan_blocks(k)
                    rows.append(
                        {
                            "Parameter": label,
                            "Badge": _scan_badge(k),
                            "Physics blocks": ", ".join(blocks) if blocks else "(unmapped)",
                        }
                    )
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    
            # Teaching Mode (UI-only). Adds gentle guidance without changing results.
            teaching_mode = st.checkbox("Teaching Mode (adds gentle guidance)", value=bool(st.session_state.get("scan_teaching_mode", False)), key="scan_teaching_mode")
            if teaching_mode:
                st.info("Teaching Mode is ON: Scan Lab will add small callouts explaining what you’re seeing. No physics or results change.")
    
    
    
            st.markdown("### Cartography Deck - mode contract (is / is not)")
            cA, cB = st.columns(2)
            with cA:
                st.markdown("""**What this mode does**
    - Maps the frozen Point Designer truth across a chosen parameter plane
    - Reveals dominant constraints, cliffs, intent splits, and robustness categories
    - Exports replayable scan artifacts (schema v1) and a fixed Scan Lab Atlas""")
            with cB:
                st.markdown("""**What this mode does not do**
    - Optimize, relax constraints, or recommend a best design
    - Apply changes to your base point automatically
    - Redefine physics or hide empty regions""")
    
            # How to think with Scan Lab (philosophy)
            with st.expander("How to think with Scan Lab", expanded=False):
                st.markdown(
                    "**Scan Lab is a microscope, not an engine.**\n"
                    "- It maps the frozen Point Designer truth across a space.\n"
                    "- It does not search for 'best' designs.\n"
                    "- If a region is empty, nature (given assumptions) said *no*.\n\n"
                    "Use it to answer: *What limits me? Where are the cliffs? Which direction helps most?*"
                )
    
            # Contract (always visible, collapsible)
            with st.expander("Scan Lab Contract", expanded=False):
                st.markdown(SCAN_LAB_CONTRACT)
                try:
                    from tools.scan_visual_identity import VISUAL_IDENTITY
                    st.caption(f"Visual semantics frozen: **{VISUAL_IDENTITY.version}**")
                except Exception:
                    st.caption("Visual semantics frozen (Scan Lab v1.0)")
    
            # Restore (artifact -> full UI state)
            with st.expander("Restore Scan Artifact (JSON)", expanded=False):
                st.caption("Upload a previously exported Scan Lab artifact. SHAMS will auto-upgrade it to schema v1 and restore the Scan Lab state.")
                up = st.file_uploader("Upload scan artifact", type=["json"], key="scan_restore_upl")
                if up is not None:
                    try:
                        payload = json.loads(up.getvalue().decode("utf-8"))
                    except Exception as e:
                        payload = None
                        st.error(f"Invalid JSON: {e}")
                    if isinstance(payload, dict) and st.button("Restore this artifact", use_container_width=True, key="scan_restore_btn"):
                        try:
                            art = payload
                            if callable(upgrade_scan_artifact):
                                art = upgrade_scan_artifact(payload)
                            rep = art.get("report") if isinstance(art, dict) else None
                            settings = art.get("settings") if isinstance(art, dict) else None
    
                            if not isinstance(rep, dict):
                                raise ValueError("Artifact missing 'report'")
    
                            # Restore report + artifact
                            st.session_state["scan_cartography_report"] = rep
                            st.session_state["scan_cartography_artifact"] = art
    
                            # Restore scan settings (best effort)
                            if isinstance(settings, dict):
                                st.session_state["scan_cart_x_key"] = settings.get("x_key")
                                st.session_state["scan_cart_y_key"] = settings.get("y_key")
                                st.session_state["scan_cart_x_lo"] = settings.get("x_lo")
                                st.session_state["scan_cart_x_hi"] = settings.get("x_hi")
                                st.session_state["scan_cart_y_lo"] = settings.get("y_lo")
                                st.session_state["scan_cart_y_hi"] = settings.get("y_hi")
                                st.session_state["scan_cart_nx"] = settings.get("nx")
                                st.session_state["scan_cart_ny"] = settings.get("ny")
                                st.session_state["scan_cart_intents"] = settings.get("intents")
                                st.session_state["scan_cart_inc_out"] = settings.get("include_outputs")
    
                            st.success("Restored Scan Lab state from artifact.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Restore failed: {e}")
    
            # Citation-grade provenance / fingerprints
            with st.expander("Provenance (fingerprints)", expanded=False):
                import os
                repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                fps = {}
                try:
                    if callable(compute_fingerprints):
                        fps = compute_fingerprints(repo_root)
                except Exception:
                    fps = {}
                if fps:
                    st.code(f"fingerprint: {fps.get('fingerprint','n/a')}")
                    st.json(fps, expanded=False)
                else:
                    st.info("Fingerprints unavailable.")
    
            # Freeze readiness (determinism + regression)
            with st.expander("Freeze readiness tools", expanded=False):
                st.caption("These checks do not change physics. They validate determinism and export plumbing.")
                if Evaluator is None or not callable(build_cartography_report) or not callable(stable_hash):
                    st.warning("Freeze readiness checks unavailable (imports missing).")
                else:
                    if st.button("Run quick replay determinism audit", use_container_width=True, key="scan_replay_audit_btn"):
                        try:
                            import numpy as _np
                            ev = _dsg_evaluator(origin="UI", cache_enabled=True)
                            # Small deterministic neighborhood around the current base point
                            base0 = st.session_state.get("last_point_inp")
                            if base0 is None:
                                raise ValueError("No baseline point available.")
                            xk = st.session_state.get("scan_cart_x_key", "Ip_MA")
                            yk = st.session_state.get("scan_cart_y_key", "R0_m")
                            bx = float(getattr(base0, xk, 1.0) or 1.0)
                            by = float(getattr(base0, yk, 1.0) or 1.0)
                            xv = list(_np.linspace(0.95 * bx, 1.05 * bx, 11))
                            yv = list(_np.linspace(0.95 * by, 1.05 * by, 9))
                            intents0 = list(st.session_state.get("scan_cart_intents") or ["Reactor"])
                            rep_a = build_cartography_report(evaluator=ev, base_inputs=base0, x_key=str(xk), y_key=str(yk), x_vals=xv, y_vals=yv, intents=intents0, include_outputs=False)
                            rep_b = build_cartography_report(evaluator=ev, base_inputs=base0, x_key=str(xk), y_key=str(yk), x_vals=xv, y_vals=yv, intents=intents0, include_outputs=False)
                            ha = {
                                "report": stable_hash(rep_a),
                                "dominance": stable_hash(rep_a.get("dominance", {})),
                                "intent_stats": stable_hash(rep_a.get("intent_stats", {})),
                            }
                            hb = {
                                "report": stable_hash(rep_b),
                                "dominance": stable_hash(rep_b.get("dominance", {})),
                                "intent_stats": stable_hash(rep_b.get("intent_stats", {})),
                            }
                            if ha == hb:
                                st.success("Replay determinism audit: PASS")
                            else:
                                st.error("Replay determinism audit: FAIL (hash mismatch)")
                            st.json({"runA": ha, "runB": hb}, expanded=False)
                        except Exception as e:
                            st.error(f"Replay audit failed: {e}")
    
                st.caption("For full freeze gating, run: python scripts/run_scanlab_freeze_qa.py")
    
            # Keyboard quick-jump (expert)
            with st.expander("Expert quick-jump (keyboard)", expanded=False):
                st.caption("Type a letter and press Enter: D=Dominance, F=First-failure, I=Intent split, C=Causality trace")
                cmd = st.text_input("Jump", value="", key="scan_cmd_jump").strip().upper()
                if cmd in ["D","F","I","C"]:
                    st.session_state["scan_view_mode"] = cmd
                    st.success(f"View set to {cmd}.")
    
            base = st.session_state.get("last_point_inp")
            if base is None:
                st.info("Run **Point Designer** first (Scan Lab uses the last evaluated point as the baseline).")
                return
    
            # Canonical questions (teaching / onboarding)
            with st.expander("Canonical questions (teaching)", expanded=False):
                st.caption("A small library of physics questions that Scan Lab can answer. These load scan settings or suggest a view - no designs are applied.")
                qs = []
                try:
                    if callable(build_canonical_questions):
                        qs = build_canonical_questions()
                except Exception:
                    qs = []
                if not qs:
                    st.info("Canonical questions unavailable.")
                else:
                    q_labels = [q.get('question') for q in qs]
                    qpick = st.selectbox("Pick a question", options=q_labels, index=0, key="scan_canon_pick")
                    q = qs[q_labels.index(qpick)]
                    st.write({"hint": q.get("hint"), "suggested_golden_label": q.get("suggested_golden_label")})
                    if q.get("suggested_golden_label"):
                        st.info("Tip: load the suggested golden scan below, then run Cartography.")
    
            # Golden scans (institutional memory)
            with st.expander("Golden scans (teaching + QA)", expanded=False):
                st.caption("One-click canonical landscapes. These load scan settings only; they do not apply designs.")
                presets = []
                try:
                    if callable(build_golden_scan_presets):
                        presets = build_golden_scan_presets(base_inputs=base)
                except Exception:
                    presets = []
                if not presets:
                    st.warning("Golden presets unavailable.")
                else:
                    labels = [p["label"] for p in presets]
                    pick = st.selectbox("Preset", options=labels, index=0, key="scan_golden_pick")
                    gp = presets[labels.index(pick)]
                    st.write({"note": gp.get("note"), "intents": gp.get("intents"), "x": gp.get("x_key"), "y": gp.get("y_key")})
                    if st.button("Load this golden scan", use_container_width=True, key="scan_load_golden"):
                        st.session_state["scan_cart_x_key"] = gp.get("x_key")
                        st.session_state["scan_cart_y_key"] = gp.get("y_key")
                        st.session_state["scan_cart_intents"] = gp.get("intents")
                        st.session_state["scan_cart_x_lo"] = float(gp.get("x_range")[0])
                        st.session_state["scan_cart_x_hi"] = float(gp.get("x_range")[1])
                        st.session_state["scan_cart_y_lo"] = float(gp.get("y_range")[0])
                        st.session_state["scan_cart_y_hi"] = float(gp.get("y_range")[1])
                        st.session_state["scan_cart_nx"] = int(gp.get("n_x"))
                        st.session_state["scan_cart_ny"] = int(gp.get("n_y"))
                        st.session_state["scan_cart_base_override"] = asdict(gp.get("base_inputs")) if gp.get("base_inputs") is not None else None
                        st.success("Loaded golden scan settings.")
    
        st.markdown("---")
        st.markdown("### Cartography")
        st.caption("Produces: constraint-dominance maps, first-failure order, intent-split overlays, robustness labels, and a narrative summary.")

        # Variable pickers
        # Keep list tight and meaningful; these must exist on PointInputs.
        vars2d = [
            ("R0_m", "R0 (m)"),
            ("a_m", "a (m)"),
            ("Bt_T", "B0 (T)"),
            ("Ip_MA", "Ip (MA)"),
            ("fG", "fG (-)"),
            ("Paux_MW", "Paux (MW)"),
            ("kappa", "kappa (-)"),
            ("Ti_keV", "Ti (keV)"),
        ]
        key_to_label = {k: v for k, v in vars2d}
        klist = [k for k, _ in vars2d]

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            x_key = st.selectbox("x-axis", options=klist, index=klist.index(st.session_state.get("scan_cart_x_key", "Ip_MA")) if st.session_state.get("scan_cart_x_key", "Ip_MA") in klist else 0, format_func=lambda k: f"{k} - {key_to_label.get(k,k)}", key="scan_cart_x")
        with c2:
            y_key = st.selectbox("y-axis", options=klist, index=klist.index(st.session_state.get("scan_cart_y_key", "R0_m")) if st.session_state.get("scan_cart_y_key", "R0_m") in klist else 1, format_func=lambda k: f"{k} - {key_to_label.get(k,k)}", key="scan_cart_y")
        with c3:
            intents = st.multiselect("Intent lenses", options=["Research", "Reactor"], default=st.session_state.get("scan_cart_intents", ["Reactor"]), key="scan_cart_intents")

            # Always-visible intent badge (clarity; no logic change)
            _sel_intents = intents or []
            st.markdown(f"**Intent badge:** {' / '.join([str(x) for x in _sel_intents]) if _sel_intents else '(none)'}")
            st.caption('Projection note: Scan Lab shows a 2D slice. Off-axis constraints may dominate outside this plane.')

        # Ranges + resolution
        def _g(attr: str, default: float) -> float:
            try:
                return float(getattr(base, attr))
            except Exception:
                return float(default)

        bx = _g(x_key, 1.0)
        by = _g(y_key, 1.0)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            x_lo = st.number_input("x min", value=float(st.session_state.get("scan_cart_x_lo", 0.7 * bx)), step=0.1, key="scan_cart_x_lo")
        with c2:
            x_hi = st.number_input("x max", value=float(st.session_state.get("scan_cart_x_hi", 1.3 * bx)), step=0.1, key="scan_cart_x_hi")
        with c3:
            y_lo = st.number_input("y min", value=float(st.session_state.get("scan_cart_y_lo", 0.7 * by)), step=0.1, key="scan_cart_y_lo")
        with c4:
            y_hi = st.number_input("y max", value=float(st.session_state.get("scan_cart_y_hi", 1.3 * by)), step=0.1, key="scan_cart_y_hi")

        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            nx = int(st.slider("Nx", 11, 61, int(st.session_state.get("scan_cart_nx", 31)), 2, key="scan_cart_nx"))
        with c2:
            ny = int(st.slider("Ny", 11, 61, int(st.session_state.get("scan_cart_ny", 25)), 2, key="scan_cart_ny"))
        with c3:
            include_outputs = st.checkbox("Include compact outputs in report", value=False, key="scan_cart_inc_out")

        # Optional base override (loaded from golden scan)
        base_override = st.session_state.get("scan_cart_base_override")
        if isinstance(base_override, dict) and base_override:
            with st.expander("Baseline override (from golden scan)", expanded=False):
                st.json(base_override)

        # Run
        if st.button("Run cartography scan", type="primary", use_container_width=True, key="scan_cart_run"):
            if Evaluator is None or not callable(build_cartography_report):
                st.error("Scan cartography engine unavailable (import error).")
                errs = st.session_state.get("scan_import_errors") or []
                if errs:
                    st.caption("Import details")
                    st.code("\n".join([str(e) for e in errs])
                            [:2000])
                return
            if float(x_hi) <= float(x_lo) or float(y_hi) <= float(y_lo):
                st.error("Invalid bounds: max must be greater than min for both axes.")
                return
            else:
                try:
                    from dataclasses import replace
                    base2 = base
                    if isinstance(base_override, dict) and base_override:
                        try:
                            base2 = replace(base2, **{k: base_override[k] for k in base_override if k in base2.__dict__})
                        except Exception:
                            pass
                    ev = _dsg_evaluator(origin="UI", cache_enabled=True)
                    x_vals = list(np.linspace(float(x_lo), float(x_hi), int(nx)))
                    y_vals = list(np.linspace(float(y_lo), float(y_hi), int(ny)))
                    import time
                    _t0 = time.time()
                    total_pts = max(int(nx) * int(ny), 1)
                    prog = st.progress(0.0, text=f"Stage 1/2 - Evaluating {total_pts} points (frozen evaluator)…")

                    def _cb(done, total):
                        try:
                            dt = max(time.time() - _t0, 1e-6)
                            rate = float(done) / dt
                            eta = (float(total) - float(done)) / max(rate, 1e-6)
                            frac = float(done) / max(float(total), 1.0)
                            prog.progress(min(1.0, max(0.0, frac)), text=f"{done}/{total} pts - {rate:.1f} pt/s - ETA {eta:.0f}s")
                        except Exception:
                            pass

                    rep = build_cartography_report(
                        evaluator=ev,
                        base_inputs=base2,
                        x_key=str(x_key),
                        y_key=str(y_key),
                        x_vals=x_vals,
                        y_vals=y_vals,
                        intents=list(intents or ["Reactor"]),
                        include_outputs=bool(include_outputs),
                        progress_cb=_cb,
                    )
                    try:
                        prog.progress(1.0, text='Stage 2/2 - Computing narrative/topology/artifact…')
                    except Exception:
                        pass
                    rep['run_seconds'] = float(time.time() - _t0)
                    # Attach common metadata and record
                    rep = _attach_common_metadata(rep)
                    st.session_state["scan_cartography_report"] = rep

                    # Freeze-grade Scan Artifact (schema v1)
                    settings = {
                        "x_key": str(x_key),
                        "y_key": str(y_key),
                        "x_lo": float(x_lo),
                        "x_hi": float(x_hi),
                        "y_lo": float(y_lo),
                        "y_hi": float(y_hi),
                        "nx": int(nx),
                        "ny": int(ny),
                        "intents": list(intents or ["Reactor"]),
                        "include_outputs": bool(include_outputs),
                    }
                    artifact = None
                    if callable(build_scan_artifact):
                        try:
                            artifact = build_scan_artifact(
                                report=rep,
                                settings=settings,
                                metadata=dict(rep.get("metadata") or {}),
                                reason_code="run_ok",
                                freeze_statement=f"Scan Lab frozen (schema v{int(SCAN_SCHEMA_VERSION or 1)})",
                            )
                        except Exception:
                            artifact = None
                    if isinstance(artifact, dict):
                        st.session_state["scan_cartography_artifact"] = artifact
                        try:
                            _v98_record_run("scan_cartography", artifact, mode="scan_lab")
                        except Exception:
                            pass
                    else:
                        try:
                            _v98_record_run("scan_cartography", rep, mode="scan_lab")
                        except Exception:
                            pass
                    st.success(f"Scan complete: {rep.get('n_points')} points")
                except Exception as e:
                    st.error(f"Scan failed: {e}")

        rep = st.session_state.get("scan_cartography_report")
        if not isinstance(rep, dict):
            st.info("No cartography scan results yet.")
            return

        # (One-glance truth + intentional emptiness messaging are rendered below.)

        # One-glance truth strip (radical clarity)
        nar_all = rep.get("narrative") or {}
        nar_int = (nar_all.get("intents") or {}) if isinstance(nar_all, dict) else {}
        intents_strip = rep.get("intents") or []
        if not intents_strip:
            intents_strip = ["Reactor"]

        # derive summary for primary intent (first in list)
        it_primary = str(intents_strip[0])
        n0 = nar_int.get(it_primary, {}) if isinstance(nar_int, dict) else {}
        feasible0 = float(n0.get("blocking_feasible_rate", 0.0)) if isinstance(n0, dict) else 0.0
        top0 = (n0.get("dominance_ranked") or []) if isinstance(n0, dict) else []
        dom0 = (top0[0].get("constraint") if top0 else None) or "(none)"
        cliff0 = float(n0.get("cliffiness_proxy", 0.0)) if isinstance(n0, dict) else 0.0

        # robustness verdict (simple, honest): use feasible fraction bands
        if feasible0 >= 0.85:
            rb0 = "Robust"
        elif feasible0 >= 0.55:
            rb0 = "Balanced"
        elif feasible0 >= 0.25:
            rb0 = "Brittle"
        else:
            rb0 = "Knife-edge"

        st.markdown("### One‑glance truth")
        a, b, c, d = st.columns(4)
        a.metric("Dominant constraint", str(dom0))
        b.metric(f"Feasible fraction ({it_primary})", f"{feasible0*100:.0f}%")
        c.metric("Robustness verdict", rb0)
        d.metric("Cliffiness proxy", f"{cliff0:.2f}")

        # The final test: can a user learn something fundamental from one scan?
        with st.expander("One-scan benchmark", expanded=False):
            st.caption("A lightweight self-check for freeze readiness. This is optional and does not affect results.")
            st.checkbox("After one scan, I learned something fundamental about what limits this design space.", key="scan_benchmark_learned")
            st.text_area("If yes: what was it? (optional)", value="", height=90, key="scan_benchmark_note")

        # --- Design Family Governance Engine (v394.0.0) ---
        # Exploration-only: does not affect truth. Deterministic labeling + connected components.
        with st.expander("Design family governance (v394.0.0)", expanded=False):
            st.caption("Extract deterministic design families from the current cartography report (regime-signature labeling + connected components).")
            it_opts = list(intents_strip or ["Reactor"])
            it_sel = st.selectbox("Intent lens", options=it_opts, index=0, key="scan_df_intent_v394")
            min_pts = int(st.slider("Minimum points per family", 4, 80, int(st.session_state.get("scan_df_min_pts_v394", 12)), 1, key="scan_df_min_pts_v394"))
            c1, c2 = st.columns(2)
            with c1:
                run_df = st.button("Build families", type="secondary", use_container_width=True, key="scan_df_build_v394")
            with c2:
                clear_df = st.button("Clear", use_container_width=True, key="scan_df_clear_v394")
            if clear_df:
                st.session_state.pop("scan_design_families_v394", None)
                st.session_state.pop("scan_design_families_v394_cert", None)
                st.success("Cleared design family artifacts.")

            if run_df:
                if not callable(build_design_families_from_scan_cartography):
                    st.error("Design family engine unavailable (import error).")
                else:
                    try:
                        art = build_design_families_from_scan_cartography(rep, intent=str(it_sel), min_points=int(min_pts))
                        # Attach common metadata and record
                        art = _attach_common_metadata(art)
                        st.session_state["scan_design_families_v394"] = art
                        try:
                            from src.certification.design_family_governance_certification_v394 import certify_design_families_v394
                            cert = certify_design_families_v394(artifact=art)
                        except Exception:
                            cert = {"name": "design_family_governance_v394", "verdict": "UNKNOWN"}
                        st.session_state["scan_design_families_v394_cert"] = cert
                        try:
                            _v98_record_run("scan_design_families_v394", {"artifact": art, "cert": cert}, mode="scan_lab")
                        except Exception:
                            pass
                        st.success(f"Built {len(art.get('families') or [])} families.")
                    except Exception as e:
                        st.error(f"Family build failed: {e}")

            art = st.session_state.get("scan_design_families_v394")
            if isinstance(art, dict) and (art.get("families") is not None):
                cert = st.session_state.get("scan_design_families_v394_cert")
                if isinstance(cert, dict):
                    st.markdown("**Certification**")
                    st.json(cert)
                fams = art.get("families") or []
                if isinstance(fams, list) and fams:
                    # Compact table view (avoid scroll walls; default collapsed via expander)
                    rows = []
                    for f in fams:
                        if not isinstance(f, dict):
                            continue
                        rows.append({
                            "family_id": f.get("family_id"),
                            "label": f.get("label"),
                            "n_points": f.get("n_points"),
                            "feasible_frac": f.get("feasible_frac"),
                            "x_range": f"[{f.get('x_min'):.3g}, {f.get('x_max'):.3g}]"if isinstance(f.get('x_min'), (int,float)) and isinstance(f.get('x_max'), (int,float)) else "",
                            "y_range": f"[{f.get('y_min'):.3g}, {f.get('y_max'):.3g}]"if isinstance(f.get('y_min'), (int,float)) and isinstance(f.get('y_max'), (int,float)) else "",
                        })
                    try:
                        import pandas as pd
                        df = pd.DataFrame(rows)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    except Exception:
                        st.json(rows[:20])
                st.download_button(
                    "Download families JSON",
                    data=json.dumps(art, indent=2, default=str).encode("utf-8"),
                    file_name="shams_scan_design_families_v394.json",
                    mime="application/json",
                    use_container_width=True,
                    key="scan_df_dl_v394",
                )
            else:
                st.info("No design family artifact yet. Run ‘Build families’ after a cartography scan.")

        # Make absence intentional (no-feasible region)
        try:
            all_zero = True
            worst = {}
            for it in intents_strip:
                nn = nar_int.get(str(it), {}) if isinstance(nar_int, dict) else {}
                ff = float(nn.get("blocking_feasible_rate", 0.0)) if isinstance(nn, dict) else 0.0
                if ff > 0.0:
                    all_zero = False
                rk = (nn.get("dominance_ranked") or []) if isinstance(nn, dict) else []
                if rk:
                    worst[str(it)] = rk[0].get("constraint")
            if all_zero:
                st.warning(
                    "No blocking-feasible region exists in this X–Y space (under the selected assumptions)."
                )
                st.markdown(
                    "**Why this is empty (most likely):**\n"
                    + "\n".join([f"- Under **{k}** intent, **{v}** limits essentially everywhere."for k, v in worst.items()])
                )
                st.caption("Try widening bounds, changing axes, or switching intent to test whether this is a structural limit or a policy lens.")
        except Exception:
            pass

        
        
        # --- Post-run Cartography Workbench (v196.3) ---
        # Goal: eliminate scroll-fatigue by treating the map as the center of gravity.
        # This is UI-only; it does not change evaluator truth or scan semantics.

        intents2 = rep.get("intents") or []
        x_vals = rep.get("x_vals") or []
        y_vals = rep.get("y_vals") or []
        pts = rep.get("points") or []
        try:
            grid = {(int(p["i"]), int(p["j"])): p for p in pts if isinstance(p, dict) and "i"in p and "j"in p}
        except Exception:
            grid = {}

        if not intents2:
            intents2 = ["Reactor"]

        # --- Sticky-ish truth bar (best-effort in Streamlit) ---
        try:
            st.markdown(
                """
<style>
/* Make the next container behave like a lightweight "truth bar"*/
div[data-testid="stVerticalBlockBorderWrapper"].shams_truthbar { position: sticky; top: 0.5rem; z-index: 50; background: white; }
</style>
                """,
                unsafe_allow_html=True,
            )
        except Exception:
            pass

        # We keep your One‑glance truth metrics above; now we add a compact context line.
        st.caption(f"Post‑run workspace: **{rep.get('x_key')}** vs **{rep.get('y_key')}** · intents: **{' / '.join([str(i) for i in intents2])}** · n={int(rep.get('n_points') or 0)}")

        st.markdown("### Cartography workbench")
        st.caption("Orient → look → probe → explain → compare. (Cartography/interpretability only; no optimization.)")

        # ---------- helpers ----------
        def _cell(intent: str, i: int, j: int) -> dict:
            c = grid.get((int(i), int(j)), {}) if isinstance(grid, dict) else {}
            return ((c.get("intent") or {}).get(str(intent)) or {}) if isinstance(c, dict) else {}

        def _dominance_labels(intent: str):
            labels = set()
            for j in range(len(y_vals)):
                for i in range(len(x_vals)):
                    s = _cell(intent, i, j)
                    if bool(s.get("blocking_feasible")):
                        labels.add("PASS")
                    else:
                        labels.add(str(s.get("dominant_blocking") or "FAIL (unknown)"))
            lab = sorted(list(labels))
            if "PASS"in lab:
                lab = ["PASS"] + [x for x in lab if x != "PASS"]
            return lab

        def _render_dominance_map(intent: str):
            dom = np.empty((len(y_vals), len(x_vals)), dtype=object)
            for j in range(len(y_vals)):
                for i in range(len(x_vals)):
                    s = _cell(intent, i, j)
                    if bool(s.get("blocking_feasible")):
                        dom[j, i] = "PASS"
                    else:
                        dom[j, i] = s.get("dominant_blocking") or "FAIL (unknown)"
            labels = _dominance_labels(intent)
            lut = {lab: k for k, lab in enumerate(labels)}
            z = np.vectorize(lambda s: lut.get(str(s), 0))(dom)

            fig, ax = plt.subplots(figsize=(7.6, 4.4))
            try:
                from tools.scan_visual_identity import build_palette
                palette = build_palette(labels)
            except Exception:
                palette = ['#E0E0E0', '#4C78A8', '#F58518', '#54A24B', '#E45756', '#72B7B2', '#B279A2', '#FF9DA6', '#9D755D', '#BAB0AC', '#2F4B7C', '#7A5195', '#EF5675', '#FFA600']
            if labels and labels[0] == 'PASS':
                palette[0] = '#E0E0E0'
            cmap = ListedColormap(palette[:max(len(labels), 1)])
            ax.imshow(z, origin='lower', aspect='auto', cmap=cmap, vmin=-0.5, vmax=len(labels)-0.5)
            ax.set_xlabel(f"{rep.get('x_key')} - {str(rep.get('x_label') or '')}")
            ax.set_ylabel(f"{rep.get('y_key')} - {str(rep.get('y_label') or '')}")
            ax.set_title(f"Dominant blocking constraint - intent: {intent}")
            return fig, labels

        def _render_feasible_map(intent: str):
            z = np.zeros((len(y_vals), len(x_vals)), dtype=float)
            for j in range(len(y_vals)):
                for i in range(len(x_vals)):
                    s = _cell(intent, i, j)
                    z[j, i] = 1.0 if bool(s.get("blocking_feasible")) else 0.0
            fig, ax = plt.subplots(figsize=(7.6, 4.4))
            ax.imshow(z, origin='lower', aspect='auto')
            ax.set_xlabel(f"{rep.get('x_key')}")
            ax.set_ylabel(f"{rep.get('y_key')}")
            ax.set_title(f"Blocking feasibility (1=feasible, 0=infeasible) - intent: {intent}")
            return fig

        def _render_robustness_proxy(intent: str):
            z = np.full((len(y_vals), len(x_vals)), float("nan"))
            for j in range(len(y_vals)):
                for i in range(len(x_vals)):
                    s = _cell(intent, i, j)
                    try:
                        z[j, i] = float(s.get("local_p_feasible"))
                    except Exception:
                        z[j, i] = float("nan")
            fig, ax = plt.subplots(figsize=(7.6, 4.4))
            ax.imshow(z, origin='lower', aspect='auto')
            ax.set_xlabel(f"{rep.get('x_key')}")
            ax.set_ylabel(f"{rep.get('y_key')}")
            ax.set_title(f"Robustness proxy (local p-feasible) - intent: {intent}")
            return fig

        def _render_operating_contours(intent: str, field: str):
            fc = rep.get("field_cube") if isinstance(rep, dict) else None
            arr = None
            try:
                arr = (fc.get("vars") or {}).get(str(field)) if isinstance(fc, dict) else None
            except Exception:
                arr = None
            if not isinstance(arr, list):
                # fallback: build from per-point outputs (sparse)
                z = np.full((len(y_vals), len(x_vals)), float("nan"))
                for j in range(len(y_vals)):
                    for i in range(len(x_vals)):
                        cell = grid.get((i, j), {}) if isinstance(grid, dict) else {}
                        outs = cell.get("outputs") or {}
                        if isinstance(outs, dict) and field in outs:
                            try:
                                z[j, i] = float(outs.get(field))
                            except Exception:
                                z[j, i] = float("nan")
            else:
                z = np.array(arr, dtype=float)
            fig, ax = plt.subplots(figsize=(7.6, 4.4))
            # Filled contours + feasibility overlay
            try:
                ax.contourf(z, levels=12, origin="lower")
            except Exception:
                ax.imshow(z, origin="lower", aspect="auto")
            ax.set_xlabel(f"{rep.get('x_key')}")
            ax.set_ylabel(f"{rep.get('y_key')}")
            ax.set_title(f"Operating contours: {field} - intent context: {intent}")
            return fig

        # ---------- layout ----------
        nav, mapcol, insp = st.columns([1.05, 2.2, 1.15], gap="large")

        with nav:
            st.markdown("**Navigate**")
            it_active = st.selectbox("Primary intent (view)", options=intents2, index=0, key="scan_wb_intent_active")

            view = st.radio(
                "View",
                options=[
                    "Dominance (blocking)",
                    "Feasibility (blocking)",
                    "Robustness (proxy)",
                    "Operating contours (outputs)",
                ],
                index=0,
                key="scan_wb_view",
            )

            
            out_key = None
            if str(view).startswith("Operating"):
                # Requires include_outputs=True when running the scan
                fc = rep.get("field_cube") if isinstance(rep, dict) else None
                keys = []
                try:
                    keys = sorted(list((fc.get("vars") or {}).keys())) if isinstance(fc, dict) else []
                except Exception:
                    keys = []
                if not keys:
                    st.warning("No output fields found. Re-run the scan with **Include outputs** enabled.")
                else:
                    out_key = st.selectbox("Contour field", options=keys, index=0, key="scan_wb_out_key")
            compare = False
            if len(intents2) >= 2:
                compare = st.checkbox("Compare intents (side-by-side)", value=False, key="scan_wb_compare")

            with st.expander("Legend / meaning", expanded=False):
                st.caption("PASS means blocking-feasible at that cell. Failures are colored by the dominant blocking constraint (worst margin).")
                try:
                    labs = _dominance_labels(it_active)
                    st.write(labs)
                    if labs == ["PASS"]:
                        st.info("All cells are feasible in this slice → dominance map is intentionally neutral/gray.")
                except Exception:
                    pass

            with st.expander("Trust & export", expanded=False):
                st.write({
                    "n_points": rep.get("n_points"),
                    "run_seconds": rep.get("run_seconds"),
                    "report_id": rep.get("id"),
                    "version": rep.get("shams_version"),
                })
                # Downloads (report + artifact) if present
                rep_dl = _shams_json_dumps(rep, indent=2).encode("utf-8")
                st.download_button("Download cartography report (JSON)", data=rep_dl, file_name="shams_cartography_report.json", mime="application/json", use_container_width=True, key="scan_wb_dl_rep")
                art = st.session_state.get("scan_cartography_artifact")
                if isinstance(art, dict):
                    art_dl = _shams_json_dumps(art, indent=2).encode("utf-8")
                    st.download_button("Download scan artifact (JSON, schema v1)", data=art_dl, file_name="shams_scan_artifact_v1.json", mime="application/json", use_container_width=True, key="scan_wb_dl_art")

                    # Optional: boundary segments + field-cube exports (Scan Lab v218 additions)
                    try:
                        bnd = rep.get("boundaries") if isinstance(rep, dict) else None
                        if isinstance(bnd, dict) and bnd:
                            bnd_dl = _shams_json_dumps(bnd, indent=2).encode("utf-8")
                            st.download_button(
                                "Download boundaries (segments JSON)",
                                data=bnd_dl,
                                file_name="shams_scan_boundaries_segments.json",
                                mime="application/json",
                                use_container_width=True,
                                key="scan_wb_dl_boundaries",
                            )
                        fc = rep.get("field_cube") if isinstance(rep, dict) else None
                        if isinstance(fc, dict) and fc:
                            fc_dl = _shams_json_dumps(fc, indent=2).encode("utf-8")
                            st.download_button(
                                "Download field-cube (labelled arrays JSON)",
                                data=fc_dl,
                                file_name="shams_scan_field_cube_v1.json",
                                mime="application/json",
                                use_container_width=True,
                                key="scan_wb_dl_field_cube",
                            )
                    except Exception:
                        pass

        with mapcol:
            if compare and len(intents2) >= 2:
                a, b = st.columns(2)
                for col, it in [(a, intents2[0]), (b, intents2[1])]:
                    with col:
                        if view.startswith("Dominance"):
                            fig, _labs = _render_dominance_map(str(it))
                            st.pyplot(fig, use_container_width=True)
                        elif view.startswith("Feasibility"):
                            fig = _render_feasible_map(str(it))
                            st.pyplot(fig, use_container_width=True)
                        else:
                            if view.startswith("Operating") and out_key:
                                fig = _render_operating_contours(str(it), str(out_key))
                            else:
                                fig = _render_robustness_proxy(str(it))
                            st.pyplot(fig, use_container_width=True)
            else:
                if view.startswith("Dominance"):
                    fig, _labs = _render_dominance_map(str(it_active))
                    st.pyplot(fig, use_container_width=True)
                elif view.startswith("Feasibility"):
                    fig = _render_feasible_map(str(it_active))
                    st.pyplot(fig, use_container_width=True)
                else:
                    if view.startswith("Operating") and out_key:
                        fig = _render_operating_contours(str(it_active), str(out_key))
                    else:
                        fig = _render_robustness_proxy(str(it_active))
                    st.pyplot(fig, use_container_width=True)

            st.caption("Tip: use the Inspector on the right to probe a cell and see the full constraint stack (descriptive only).")

        with insp:
            st.markdown("**Probe / Inspector**")

            if len(x_vals) == 0 or len(y_vals) == 0:
                st.warning("No grid values found in report.")
            else:
                # Probe controls (index-based, reliable across render backends)
                ii = int(st.slider("i (x index)", 0, max(0, len(x_vals) - 1), int(st.session_state.get("scan_wb_i", 0)), 1, key="scan_wb_i"))
                jj = int(st.slider("j (y index)", 0, max(0, len(y_vals) - 1), int(st.session_state.get("scan_wb_j", 0)), 1, key="scan_wb_j"))

                cell0 = grid.get((ii, jj), {}) if isinstance(grid, dict) else {}
                if not cell0:
                    st.warning("Selected cell not found in grid.")
                else:
                    st.write({"x": cell0.get("x"), "y": cell0.get("y"), "i": ii, "j": jj})

                    def _show_intent_block(it: str):
                        s = ((cell0.get("intent") or {}).get(str(it)) or {})
                        st.markdown(f"**Intent:** {it}")
                        st.write({
                            "blocking_feasible": bool(s.get("blocking_feasible")),
                            "dominant_blocking": s.get("dominant_blocking"),
                            "min_blocking_margin": s.get("min_blocking_margin"),
                            "robustness": s.get("robustness"),
                            "local_p_feasible (proxy)": s.get("local_p_feasible"),
                        })
                        fb = s.get("failed_blocking") or []
                        if fb:
                            st.caption("Failed blocking constraints")
                            st.write(list(fb)[:15])
                        mh = (cell0.get("margins_hard") or {}) if isinstance(cell0, dict) else {}
                        if isinstance(mh, dict) and mh:
                            rows = [{"constraint": k, "margin_frac": float(v)} for k, v in mh.items()]
                            rows.sort(key=lambda r: r["margin_frac"])
                            st.caption("Hard-constraint margins (fractional, worst first)")
                            try:
                                import pandas as _pd
                                st.dataframe(_pd.DataFrame(rows), use_container_width=True, height=210)
                            except Exception:
                                st.json(rows[:25], expanded=False)

                    if compare and len(intents2) >= 2:
                        itA, itB = intents2[0], intents2[1]
                        _show_intent_block(str(itA))
                        st.markdown("---")
                        _show_intent_block(str(itB))
                    else:
                        _show_intent_block(str(it_active))

                    # Canonical promotion hook: probe-cell -> Point Designer
                    with st.expander("Promote this probed cell to Point Designer", expanded=False):
                        st.caption("Reconstructs a PointInputs candidate from the scan base_inputs + the probed x/y cell and promotes it into Point Designer.")
                        try:
                            base_inputs_dict = rep.get("base_inputs") if isinstance(rep, dict) else None
                            if not isinstance(base_inputs_dict, dict):
                                base_inputs_dict = {}
                            cand = dict(base_inputs_dict)
                            cand[str(rep.get('x_key'))] = float(cell0.get('x'))
                            cand[str(rep.get('y_key'))] = float(cell0.get('y'))
                            st.write({"x_key": str(rep.get('x_key')), "y_key": str(rep.get('y_key')), "x": cand.get(str(rep.get('x_key'))), "y": cand.get(str(rep.get('y_key')))} )
                            if st.button("Promote to Point Designer", use_container_width=True, key="scan_wb_promote_pd"):
                                stage_pd_candidate_apply(cand, source="Scan Lab / Workbench Probe", note="Probed scan cell")
                                st.success("Promoted probed cell to Point Designer. Switch to Point Designer to review/evaluate.")
                        except Exception as _e:
                            st.info(f"Promotion unavailable: {_e}")

                    fo = cell0.get("failure_order_any") or []
                    if fo:
                        with st.expander("Failure order (hard, worst-first)", expanded=False):
                            st.write(list(fo))

        st.markdown("---")
        with st.expander("Advanced / deep dives (optional)", expanded=False):
            st.caption("Everything below is optional. The workbench above is the primary post-run experience.")
            show_deep = st.checkbox("Show deep dives", value=False, key="scan_show_deep")
        if not bool(show_deep):
            return

# Expert argument tools (claim builder + falsification)
        with st.expander("Expert argument tools (Claim Builder + Falsification)", expanded=False):
            st.caption("Turn scan results into audit-grade, evidence-backed claims. Includes a falsification lens.")

            intents2 = rep.get('intents') or []
            it0 = st.selectbox("Intent", options=intents2 if intents2 else ["Reactor"], index=0, key="scan_claim_intent")
            claim_type = st.selectbox("Claim type", options=["Dominance", "Robustness"], index=0, key="scan_claim_type")

            # Suggested expected value from narrative
            nar = ((rep.get("narrative") or {}).get("intents") or {}).get(it0, {})
            expected_default = ""
            if claim_type == "Dominance":
                expected_default = str((nar.get("dominance_ranked") or [{}])[0].get("constraint") or nar.get("dominant") or "")
            if claim_type == "Robustness":
                expected_default = "Balanced"

            expected = st.text_input("Expected (for falsification)", value=expected_default, key="scan_claim_expected")
            title = st.text_input("Claim title", value=f"Scan claim - {claim_type}", key="scan_claim_title")
            statement = st.text_area(
                "Claim statement",
                value=(
                    f"Under intent {it0}, the scan is dominated by {expected_default or '[constraint]'} across most of the X–Y space."
                    if claim_type == "Dominance"else
                    f"Under intent {it0}, this landscape is {expected_default} in the local neighborhood sense."
                ),
                height=120,
                key="scan_claim_statement",
            )
            notes = st.text_input("Notes (optional)", value="", key="scan_claim_notes")

            # Build evidence and show a stability badge (assumption-sensitivity)
            ev_blob = {}
            try:
                if callable(build_claim_evidence):
                    ev_blob = build_claim_evidence(rep, str(it0))
            except Exception:
                ev_blob = {}

            # Conclusion stability badge (heuristic): if feasible fraction is low or many components -> sensitive
            stability = "Stable"
            try:
                ff = float((ev_blob.get("stats") or {}).get("blocking_feasible_fraction"))
                comps = float((ev_blob.get("cliffs") or {}).get("n_components") or 1)
                if ff < 0.25 or comps >= 3:
                    stability = "Assumption‑sensitive"
                elif ff < 0.5:
                    stability = "Conditionally stable"
            except Exception:
                stability = "Conditionally stable"
            st.info(f"Conclusion stability: **{stability}**")

            # Why nature forces this (synthesis)
            try:
                dom_top = ((ev_blob.get('stats') or {}).get('dominance_top') or [])
                dom_name = dom_top[0][0] if dom_top else (nar.get('dominant') or 'PASS')
                why = (
                    f"Nature forces this landscape to cluster along the **{dom_name}** boundary because it is the dominant blocking limiter across the scan. "
                    f"Where dominance flips, you are crossing a regime boundary: the leverage of {rep.get('x_key')} vs {rep.get('y_key')} changes sign in terms of minimum margin."
                )
                st.caption("Why nature forces this")
                st.write(why)
            except Exception:
                pass

            # Falsification (counterexamples)
            if st.button("Try to falsify this claim", use_container_width=True, key="scan_claim_falsify"):
                try:
                    ct = "dominance"if claim_type == "Dominance"else "robustness"
                    fx = falsify_claim(rep, intent=str(it0), claim_type=ct, expected=str(expected)) if callable(falsify_claim) else {"ok": False, "reason": "falsify_unavailable"}
                    st.session_state["scan_claim_falsify_last"] = fx
                except Exception as e:
                    st.session_state["scan_claim_falsify_last"] = {"ok": False, "reason": str(e)}

            fx = st.session_state.get("scan_claim_falsify_last")
            if isinstance(fx, dict) and fx:
                st.write({"counterexamples": fx.get("n_counterexamples"), "note": fx.get("note")})
                ex = fx.get("examples") or []
                if ex:
                    try:
                        import pandas as pd
                        st.dataframe(pd.DataFrame(ex), use_container_width=True)
                    except Exception:
                        st.json(ex[:10], expanded=False)

            # Export claim as a 1-page PDF slide
            if st.button("Export Claim (1-page PDF)", use_container_width=True, key="scan_claim_export"):
                try:
                    cl = ScanClaim(title=str(title), statement=str(statement), intent=str(it0), claim_type=str(claim_type), notes=str(notes))
                    mp = st.session_state.get("scan_cart_map_pngs") or {}
                    map_png = mp.get(str(it0))
                    import os
                    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                    fps = compute_fingerprints(repo_root) if callable(compute_fingerprints) else {}
                    pdfb = build_claim_pdf_bytes(claim=cl, evidence=ev_blob, map_png=bytes(map_png) if isinstance(map_png, (bytes, bytearray)) else None, fingerprint=fps) if callable(build_claim_pdf_bytes) else b""
                    st.session_state["scan_claim_pdf_bytes"] = pdfb
                    st.session_state["scan_claim_last"] = {"title": str(title), "statement": str(statement), "intent": str(it0), "type": str(claim_type)}
                except Exception as e:
                    st.error(f"Claim export failed: {e}")

            pdfb = st.session_state.get("scan_claim_pdf_bytes")
            if isinstance(pdfb, (bytes, bytearray)) and len(pdfb) > 100:
                st.download_button("Download claim PDF", data=pdfb, file_name="shams_scan_claim.pdf", mime="application/pdf", use_container_width=True, key="scan_claim_dl")

        # Curated scan library (institutional memory)
        with st.expander("Curated scan library (local)", expanded=False):
            st.caption("Save notable scans locally to build a personal reference library.")
            tag = st.text_input("Tag", value="interesting", key="scan_lib_tag")
            note = st.text_area("Why this scan mattered (one paragraph)", value="", height=90, key="scan_lib_note")
            if st.button("Save scan + note", use_container_width=True, key="scan_lib_save"):
                try:
                    import os, json
                    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                    lib_path = os.path.join(repo_root, "docs", "scan_library.json")
                    lib = []
                    if os.path.exists(lib_path):
                        lib = json.loads(open(lib_path, "r", encoding="utf-8").read() or "[]")
                    lib.append({
                        "id": rep.get("id"),
                        "tag": str(tag),
                        "note": str(note).strip(),
                        "x": rep.get("x_key"),
                        "y": rep.get("y_key"),
                        "intents": rep.get("intents"),
                        "shams_version": rep.get("shams_version"),
                        "fingerprint": (rep.get("metadata") or {}).get("fingerprints", {}).get("fingerprint") if isinstance(rep.get("metadata"), dict) else None,
                    })
                    with open(lib_path, "w", encoding="utf-8") as f:
                        f.write(_shams_json_dumps(lib, indent=2))
                    st.success(f"Saved to {lib_path}")
                except Exception as e:
                    st.error(f"Save failed: {e}")

        # Next-tier 0-D insight suite (v191)
        with st.expander("Next‑tier insights (0‑D, no optimization)", expanded=False):
            st.caption("These tools turn scans into understanding (laws, regimes, impossibility). They never modify Point Designer truth.")

            insight = st.selectbox(
                "Pick an insight",
                options=[
                    "Local scaling law near a cell",
                    "Regime label at a cell",
                    "Explain impossible / infeasible region",
                    "Constraint irrelevance (never active)",
                    "Assumption stress hotspots (near-threshold)",
                    "Counterfactual lens (drop one constraint)",
                    "Projection stability (vary 3rd variable)",
                    "Path-follow scan (hold a target output)",
                    "Surprise detector (high-entropy neighborhoods)",
                    "Guided insight mode (10‑minute walkthrough)",
                    "Export reference atlas (PDF)",
                    "Export SHAMS Signature Atlas (10 pages)",
                ],
                index=0,
                key="scan_next_tier_pick",
            )

            # point picker shared across views
            try:
                ii = int(st.number_input("Cell i", min_value=0, max_value=max(0, len(x_vals)-1), value=0, step=1, key="scan_nt_i"))
                jj = int(st.number_input("Cell j", min_value=0, max_value=max(0, len(y_vals)-1), value=0, step=1, key="scan_nt_j"))
            except Exception:
                ii, jj = 0, 0

            picked = grid.get((ii, jj), {})

            if insight == "Local scaling law near a cell":
                if not callable(local_powerlaw_fit):
                    st.warning("Local scaling fit unavailable.")
                else:
                    intent_fit = st.selectbox("Intent lens", options=intents2, index=0, key="scan_nt_scal_int")
                    yvar = st.selectbox(
                        "Quantity to fit",
                        options=["min_blocking_margin", "local_p_feasible"] + ["q_div_MW_m2", "sigma_vm_MPa", "B_peak_T", "q95", "TBR", "P_fus_MW"],
                        index=0,
                        key="scan_nt_scal_yvar",
                    )
                    out = local_powerlaw_fit(report=rep, intent=intent_fit, i0=ii, j0=jj, yvar=yvar, radius=2)
                    if out.get("ok"):
                        st.write(out)
                    else:
                        st.warning(out.get("reason"))

            elif insight == "Regime label at a cell":
                if not callable(label_regime):
                    st.warning("Regime labeling unavailable.")
                else:
                    it0 = st.selectbox("Intent lens", options=intents2, index=0, key="scan_nt_reg_int")
                    st.write(label_regime(report=rep, intent=it0, i0=ii, j0=jj))

            elif insight == "Explain impossible / infeasible region":
                if not callable(explain_impossible_region):
                    st.warning("Region explanation unavailable.")
                else:
                    it0 = st.selectbox("Intent lens", options=intents2, index=0, key="scan_nt_imp_int")
                    st.write(explain_impossible_region(report=rep, intent=it0))

            elif insight == "Constraint irrelevance (never active)":
                if not callable(detect_irrelevant_constraints):
                    st.warning("Irrelevance detection unavailable.")
                else:
                    st.write(detect_irrelevant_constraints(report=rep))

            elif insight == "Assumption stress hotspots (near-threshold)":
                if not callable(assumption_stress_hotspots):
                    st.warning("Hotspot detection unavailable.")
                else:
                    it0 = st.selectbox("Intent lens", options=intents2, index=0, key="scan_nt_hot_int")
                    st.write(assumption_stress_hotspots(report=rep, intent=it0, topk=20))

            elif insight == "Counterfactual lens (drop one constraint)":
                if not callable(counterfactual_lens):
                    st.warning("Counterfactual lens unavailable.")
                else:
                    drop = st.text_input("Constraint name to drop (visualization only)", value="TBR", key="scan_nt_drop")
                    it0 = st.selectbox("Intent lens", options=intents2, index=0, key="scan_nt_cf_int")
                    cf = counterfactual_lens(report=rep, intent=it0, drop_constraint=drop)
                    st.write({"removed_constraint": cf.get("removed_constraint"), "ok": cf.get("ok"), "note": cf.get("note")})
                    # basic map: feasible grid under counterfactual
                    try:
                        cf_ok = np.array(cf.get("grid"))
                        fig_cf, ax_cf = plt.subplots(figsize=(7.6, 4.0))
                        ax_cf.imshow(cf_ok.astype(float), origin='lower', aspect='auto')
                        ax_cf.set_title(f"Counterfactual feasible map (drop={drop})")
                        ax_cf.set_xlabel(f"{x_key}")
                        ax_cf.set_ylabel(f"{y_key}")
                        st.pyplot(fig_cf, use_container_width=True)
                    except Exception:
                        pass

            elif insight == "Projection stability (vary 3rd variable)":
                if not callable(projection_stability_check) or Evaluator is None:
                    st.warning("Projection stability check unavailable.")
                else:
                    z_key = st.selectbox("3rd variable (z)", options=klist, index=0, key="scan_nt_z")
                    it0 = st.selectbox("Intent lens", options=intents2, index=0, key="scan_nt_proj_int")
                    rel = float(st.slider("z variation ±%", 1, 20, 5, 1, key="scan_nt_zrel")) / 100.0
                    ev_local = _dsg_evaluator(origin="UI", cache_enabled=True)
                    st.write(projection_stability_check(evaluator=ev_local, base_inputs=base, report=rep, intent=it0, i0=ii, j0=jj, z_key=z_key, rel_step=rel))

            elif insight == "Path-follow scan (hold a target output)":
                if not callable(path_follow_scan) or Evaluator is None:
                    st.warning("Path-follow scan unavailable.")
                else:
                    it0 = st.selectbox("Intent lens", options=intents2, index=0, key="scan_nt_path_int")
                    target_key = st.selectbox("Target output to hold", options=["q95", "B_peak_T", "q_div_MW_m2", "P_fus_MW"], index=0, key="scan_nt_tgt")
                    st.caption("This follows a trajectory by adjusting y to hold the target output approximately constant as x varies.")
                    if st.button("Run path-follow", use_container_width=True, key="scan_nt_run_path"):
                        ev_local = _dsg_evaluator(origin="UI", cache_enabled=True)
                        out = path_follow_scan(evaluator=ev_local, base_inputs=base, x_key=x_key, y_key=y_key, x_vals=list(x_vals), target_output=target_key)
                        st.session_state["scan_path_follow_last"] = out
                    out = st.session_state.get("scan_path_follow_last")
                    if isinstance(out, dict):
                        st.write(out.get("summary"))
                        try:
                            dfp = pd.DataFrame(out.get("path") or [])
                            st.dataframe(dfp, use_container_width=True)
                        except Exception:
                            pass

            elif insight == "Surprise detector (high-entropy neighborhoods)":
                if not callable(surprise_detector):
                    st.warning("Surprise detector unavailable.")
                else:
                    it0 = st.selectbox("Intent lens", options=intents2, index=0, key="scan_nt_sur_int")
                    rad = int(st.slider("Neighborhood radius", 1, 3, 1, 1, key="scan_nt_sur_rad"))
                    st.write(surprise_detector(report=rep, intent=it0, radius=rad))

            elif insight == "Guided insight mode (10‑minute walkthrough)":
                if not callable(guided_steps):
                    st.warning("Guided mode unavailable.")
                else:
                    st.markdown("**Walkthrough steps**")
                    for s in guided_steps():
                        st.write(f"{s.get('step')}. {s.get('title')} - {s.get('hint')}")
                    st.caption("Tip: start with a Golden scan, then follow steps 1→5.")

            elif insight == "Export reference atlas (PDF)":
                if not callable(build_scan_atlas_pdf_bytes):
                    st.warning("Atlas export unavailable.")
                else:
                    st.caption("Build a multi-page PDF atlas from the current scan (one page per intent).")
                    title = st.text_input("Atlas title", value="SHAMS - Scan Lab Atlas", key="scan_nt_atlas_title")
                    if st.button("Build atlas PDF", use_container_width=True, key="scan_nt_build_atlas"):
                        map_pngs = st.session_state.get("scan_cart_map_pngs") or {}
                        pages = []
                        for it0 in intents2:
                            png = map_pngs.get(str(it0))
                            if isinstance(png, (bytes, bytearray)):
                                pages.append({
                                    "report": rep,
                                    "intent": str(it0),
                                    "map_png": bytes(png),
                                    "page_title": f"{title} - {it0}",
                                })
                        pdfb = build_scan_atlas_pdf_bytes(pages=pages, title=str(title))
                        st.session_state["scan_atlas_pdf_bytes"] = pdfb
                    pdfb = st.session_state.get("scan_atlas_pdf_bytes")
                    if isinstance(pdfb, (bytes, bytearray)) and len(pdfb) > 100:
                        st.download_button("Download atlas (PDF)", data=pdfb, file_name="shams_scan_atlas.pdf", mime="application/pdf", use_container_width=True, key="scan_nt_dl_atlas")

            elif insight == "Export SHAMS Signature Atlas (10 pages)":
                if not callable(build_signature_atlas_pdf_bytes):
                    st.warning("Signature atlas export unavailable.")
                else:
                    st.caption("Build the fixed 10-page SHAMS Signature Atlas (contract + provenance + key scan views).")
                    title = st.text_input("Atlas title", value="SHAMS - Scan Lab Signature Atlas", key="scan_sig_atlas_title")
                    if st.button("Build Signature Atlas (10 pages)", use_container_width=True, key="scan_sig_build"):
                        # Map PNGs for intents (from rendered dominance maps)
                        map_pngs = st.session_state.get("scan_cart_map_pngs") or {}
                        # Intent split map PNG (generated when both intents exist)
                        split_png = st.session_state.get("scan_intent_split_png")

                        # Fingerprints (citation-grade)
                        import os
                        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                        fps = {}
                        try:
                            if callable(compute_fingerprints):
                                fps = compute_fingerprints(repo_root)
                        except Exception:
                            fps = {}

                        # Optional claim to embed
                        cl = st.session_state.get("scan_claim_last")
                        pdfb = build_signature_atlas_pdf_bytes(
                            report=rep,
                            title=str(title),
                            contract_md=str(SCAN_LAB_CONTRACT),
                            fingerprints=fps,
                            map_png_by_intent={str(k): bytes(v) for k, v in map_pngs.items() if isinstance(v, (bytes, bytearray))},
                            intent_split_png=bytes(split_png) if isinstance(split_png, (bytes, bytearray)) else None,
                            claim=cl if isinstance(cl, dict) else None,
                        )
                        st.session_state["scan_signature_atlas_pdf_bytes"] = pdfb

                        # Publish into docs as SHAMS signature artifact (best-effort)
                        try:
                            out_path = os.path.join(repo_root, "docs", "SHAMS_Scan_Lab_Atlas_Signature.pdf")
                            with open(out_path, "wb") as f:
                                f.write(pdfb)
                            st.success("Published signature atlas into docs/SHAMS_Scan_Lab_Atlas_Signature.pdf")
                        except Exception:
                            pass

                    pdfb = st.session_state.get("scan_signature_atlas_pdf_bytes")
                    if isinstance(pdfb, (bytes, bytearray)) and len(pdfb) > 100:
                        st.download_button("Download Signature Atlas (PDF)", data=pdfb, file_name="shams_scan_signature_atlas.pdf", mime="application/pdf", use_container_width=True, key="scan_sig_dl")

        # PDF one-page summary + PNG map exports per intent
        try:
            from tools.reports.scan_summary import build_scan_summary_pdf_bytes
        except Exception:
            build_scan_summary_pdf_bytes = None  # type: ignore


        # Render maps
        intents2 = rep.get("intents") or []
        x_vals = rep.get("x_vals") or []
        y_vals = rep.get("y_vals") or []
        pts = rep.get("points") or []

        # Build quick lookup
        grid = {(int(p["i"]), int(p["j"])): p for p in pts if isinstance(p, dict) and "i"in p and "j"in p}

        it_primary = str(intents2[0]) if intents2 else 'Reactor'
        # Secondary intent lenses (collapsible) - reduces scroll fatigue.
        for it in intents2:
            if str(it) == str(it_primary):
                continue
            with st.expander(f"Intent lens: {it}", expanded=False):
                nar = ((rep.get("narrative") or {}).get("intents") or {}).get(it, {})
                if nar:
                    st.info(nar.get("plain_language", ""))

            # Topology change alerts (disconnected islands / holes)
                try:
                    topo = (rep.get('topology') or {}).get(it, {})
                    if isinstance(topo, dict) and topo:
                        if int(topo.get('n_components', 1)) > 1:
                            st.warning(f"Topology: {topo.get('n_components')} disconnected feasible islands detected (intent {it}).")
                        if bool(topo.get('has_holes')):
                            st.warning(f"Topology: hole-like infeasible pockets detected (count={topo.get('hole_count')}).")
                except Exception:
                    pass

                # arrays
                dom = np.empty((len(y_vals), len(x_vals)), dtype=object)
                ok = np.zeros((len(y_vals), len(x_vals)), dtype=float)
                mm = np.zeros((len(y_vals), len(x_vals)), dtype=float)
                rb = np.empty((len(y_vals), len(x_vals)), dtype=object)
                for j in range(len(y_vals)):
                    for i in range(len(x_vals)):
                        p = grid.get((i, j), {})
                        s = ((p.get("intent") or {}).get(it) or {})
                        ok[j, i] = 1.0 if bool(s.get("blocking_feasible")) else 0.0
                        # Prevent “all gray” ambiguity when dominance labels are missing.
                        if ok[j, i] > 0.5:
                            dom[j, i] = "PASS"
                        else:
                            dom[j, i] = s.get("dominant_blocking") or "FAIL (unknown)"
                        mm[j, i] = float(s.get("min_blocking_margin") or float("nan"))
                        rb[j, i] = s.get("robustness") or "Unknown"

            # Categorical dominance to integer map
            labels = sorted(list({str(x) for x in dom.flatten().tolist()}))
            lut = {lab: idx for idx, lab in enumerate(labels)}
            z = np.vectorize(lambda s: lut.get(str(s), 0))(dom)

            fig, ax = plt.subplots(figsize=(7.6, 4.4))
            # Stable categorical colormap (PASS is neutral)
            labs = labels
            if 'PASS' in labs:
                labs = ['PASS'] + [x for x in labs if x != 'PASS']
                labels = labs
                lut = {lab: idx for idx, lab in enumerate(labels)}
                z = np.vectorize(lambda s: lut.get(str(s), 0))(dom)
            # Frozen visual semantics: constraint→color mapping (PASS is neutral)
            try:
                from tools.scan_visual_identity import build_palette
                palette = build_palette(labels)
            except Exception:
                palette = ['#E0E0E0', '#4C78A8', '#F58518', '#54A24B', '#E45756', '#72B7B2', '#B279A2', '#FF9DA6', '#9D755D', '#BAB0AC', '#2F4B7C', '#7A5195', '#EF5675', '#FFA600']
            # Guarantee PASS stays neutral even if the mapping changes
            if labels and labels[0] == 'PASS':
                palette[0] = '#E0E0E0'
            cmap = ListedColormap(palette[:max(len(labels), 1)])
            im = ax.imshow(z, origin='lower', aspect='auto', cmap=cmap, vmin=-0.5, vmax=len(labels)-0.5)
            ax.set_xlabel(f"{x_key} - {key_to_label.get(x_key,x_key)}")
            ax.set_ylabel(f"{y_key} - {key_to_label.get(y_key,y_key)}")
            ax.set_title("Constraint‑Dominance Cartography (blocking)")
            # Dominance boundary emphasis
            try:
                b = np.zeros_like(z, dtype=float)
                b[1:, :] |= (z[1:, :] != z[:-1, :])
                b[:, 1:] |= (z[:, 1:] != z[:, :-1])
                ax.contour(b, levels=[0.5], colors='k', linewidths=0.7, origin='lower')
            except Exception:
                pass
            # ticks: keep sparse
            ax.set_xticks([0, len(x_vals)//2, len(x_vals)-1])
            ax.set_xticklabels([f"{x_vals[0]:.3g}", f"{x_vals[len(x_vals)//2]:.3g}", f"{x_vals[-1]:.3g}"])
            ax.set_yticks([0, len(y_vals)//2, len(y_vals)-1])
            ax.set_yticklabels([f"{y_vals[0]:.3g}", f"{y_vals[len(y_vals)//2]:.3g}", f"{y_vals[-1]:.3g}"])
            st.pyplot(fig, use_container_width=True)

            # If everything is PASS, the map is intentionally neutral/gray.
            try:
                if labels == ['PASS']:
                    st.info("This map is neutral/gray because **all sampled points are blocking-feasible** in this slice (dominant constraint = PASS everywhere).")
            except Exception:
                pass

            # Capture a high-DPI PNG for exports (summary PDF / atlas)
            try:
                _buf = io.BytesIO()
                fig.savefig(_buf, format="png", dpi=220, bbox_inches="tight")
                mp = st.session_state.get("scan_cart_map_pngs")
                if not isinstance(mp, dict):
                    mp = {}
                mp[str(it)] = _buf.getvalue()
                st.session_state["scan_cart_map_pngs"] = mp
            except Exception:
                pass

            # Intent-split map: hatched region = Research-feasible but Reactor-infeasible
            if it == 'Reactor' and 'Research' in intents2 and 'Reactor' in intents2:
                try:
                    ok_r = ok
                    ok_s = np.zeros_like(ok)
                    for j in range(len(y_vals)):
                        for i in range(len(x_vals)):
                            p = grid.get((i, j), {})
                            ok_s[j, i] = 1.0 if bool(((p.get('intent') or {}).get('Research') or {}).get('blocking_feasible')) else 0.0
                    only_research = (ok_s > 0.5) & (ok_r < 0.5)
                    if only_research.any():
                        fig_os, ax_os = plt.subplots(figsize=(7.6, 4.4))
                        ax_os.imshow(z, origin='lower', aspect='auto', cmap=cmap, vmin=-0.5, vmax=len(labels)-0.5)
                        ax_os.contourf(only_research.astype(float), levels=[0.5, 1.5], colors='none', hatches=['////'], origin='lower')
                        ax_os.set_title('Intent-split overlay (hatched = Research-only feasible)')
                        st.pyplot(fig_os, use_container_width=True)

                        # Capture PNG for signature atlas
                        try:
                            _buf2 = io.BytesIO()
                            fig_os.savefig(_buf2, format="png", dpi=220, bbox_inches="tight")
                            st.session_state["scan_intent_split_png"] = _buf2.getvalue()
                        except Exception:
                            pass
                except Exception:
                    pass

            with st.expander("Legend (dominant blocking constraint)", expanded=False):
                # Export map for this intent
                try:
                    import io
                    _buf = io.BytesIO()
                    fig.savefig(_buf, format='png', dpi=200, bbox_inches='tight')
                    _buf.seek(0)
                    st.download_button(f'Download map (PNG) - {it}', data=_buf.getvalue(), file_name=f'shams_scan_map_{it.lower()}.png', mime='image/png', use_container_width=True, key=f'scan_map_png_{it}')
                    if callable(build_scan_summary_pdf_bytes):
                        _pdf = build_scan_summary_pdf_bytes(report=rep, intent=str(it), map_png=_buf.getvalue())
                        st.download_button(f'Download 1-page PDF - {it}', data=_pdf, file_name=f'shams_scan_summary_{it.lower()}.pdf', mime='application/pdf', use_container_width=True, key=f'scan_map_pdf_{it}')
                except Exception:
                    pass
                st.write([{"id": int(lut[k]), "constraint": k} for k in labels])

            # Iso-constraint manifolds (margin=0 contours)
            with st.expander("Iso-constraint manifolds (margin=0)", expanded=False):
                st.caption("Shows contour lines where a selected hard-constraint margin crosses zero (approx feasibility boundary).")
                # gather constraint names
                names = set()
                for p in pts:
                    mh = p.get('margins_hard') if isinstance(p, dict) else None
                    if isinstance(mh, dict):
                        for nm in mh.keys():
                            names.add(str(nm))
                names = sorted([n for n in names if n])
                if not names:
                    st.info("Hard-constraint margins not present in this report.")
                else:
                    pick_nm = st.selectbox("Constraint", options=names, index=0, key=f"scan_iso_pick_{it}")
                    M = np.full((len(y_vals), len(x_vals)), np.nan)
                    for j in range(len(y_vals)):
                        for i in range(len(x_vals)):
                            p = grid.get((i, j), {})
                            mh = p.get('margins_hard') if isinstance(p, dict) else None
                            if isinstance(mh, dict) and pick_nm in mh:
                                try:
                                    M[j, i] = float(mh[pick_nm])
                                except Exception:
                                    pass
                    if np.isfinite(M).any():
                        figc, axc = plt.subplots(figsize=(7.6, 4.4))
                        axc.imshow(ok, origin='lower', aspect='auto')
                        try:
                            axc.contour(M, levels=[0.0], colors='k', linewidths=1.0, origin='lower')
                        except Exception:
                            st.info("No margin=0 contour found in the current bounds.")
                        axc.set_title(f"Iso-contour: {pick_nm} margin = 0")
                        st.pyplot(figc, use_container_width=True)
                    else:
                        st.info("No finite margin data for this constraint in the scanned region.")

            # First‑failure topology: show the failure order at a selected point
            with st.expander("First‑Failure Topology (pick a cell)", expanded=False):
                ci, cj = st.columns(2)
                with ci:
                    ii = int(st.slider("i (x index)", 0, max(0, len(x_vals)-1), len(x_vals)//2, 1, key=f"scan_pick_i_{it}"))
                with cj:
                    jj = int(st.slider("j (y index)", 0, max(0, len(y_vals)-1), len(y_vals)//2, 1, key=f"scan_pick_j_{it}"))
                p = grid.get((ii, jj), {})
                st.write({"x": float(p.get("x", float('nan'))), "y": float(p.get("y", float('nan'))), "blocking_feasible": bool(((p.get('intent') or {}).get(it) or {}).get('blocking_feasible'))})
                st.write("Failure order (hard constraints, worst margin first):")
                st.write(p.get("failure_order_any") or [])
                st.write("Intent summary:")
                st.json(((p.get("intent") or {}).get(it) or {}), expanded=False)
                if st.button("Push this point to Point Designer", key=f"scan_push_pd_{it}"):
                    try:
                        # Canonical cross-panel handoff: set pd_candidate_apply.
                        # Point Designer will consume this payload and push it into widget keys.
                        from dataclasses import replace
                        _inp = replace(base, **{x_key: float(p.get("x")), y_key: float(p.get("y"))})
                        try:
                            from dataclasses import asdict
                            stage_pd_candidate_apply(asdict(_inp), source="Scan Lab / Topology Picker", note="Picked scan cell")
                        except Exception:
                            stage_pd_candidate_apply(dict(getattr(_inp, "__dict__", {})), source="Scan Lab / Topology Picker", note="Picked scan cell")
                        st.session_state["last_point_inp"] = _inp
                        st.success("Promoted this cell to Point Designer. Switch to Point Designer to review/evaluate.")
                    except Exception as e:
                        st.error(f"Could not apply point: {e}")

                st.markdown("---")
                st.markdown("##### Local insight tools")
                tabs = st.tabs(["Causality", "Time-to-failure", "Uncertainty", "Null direction"])

                # Build point overrides for this cell
                point_overrides = {x_key: float(p.get("x")), y_key: float(p.get("y"))}

                with tabs[0]:
                    st.caption("Local sensitivity trace for the currently dominant blocking constraint (finite differences).")
                    domc = (((p.get('intent') or {}).get(it) or {}).get('dominant_blocking') or '').strip()
                    if not domc or domc.upper() == 'PASS':
                        st.info("This cell passes blocking constraints; causality trace is most useful on a failing cell.")
                    elif not callable(build_causality_trace) or Evaluator is None:
                        st.info("Causality engine unavailable.")
                    else:
                        knobs = [x_key, y_key, 'R0_m', 'Bt_T', 'Ip_MA', 'fG', 'Paux_MW', 'a_m']
                        knobs = list(dict.fromkeys([k for k in knobs if hasattr(base, k)]))
                        rel_step = st.slider("Sensitivity step (relative)", 0.005, 0.05, 0.01, 0.005, key=f"scan_caus_step_{it}")
                        if st.button("Compute causality trace", key=f"scan_caus_run_{it}", use_container_width=True):
                            try:
                                ev_local = _dsg_evaluator(origin="UI", cache_enabled=True)
                                tr = build_causality_trace(
                                    evaluator=ev_local,
                                    base_inputs=base,
                                    point_overrides=point_overrides,
                                    constraint_name=domc,
                                    knobs=knobs,
                                    rel_step=float(rel_step),
                                )
                                st.json(tr, expanded=False)
                            except Exception as e:
                                st.error(f"Causality trace failed: {e}")

                with tabs[1]:
                    st.caption("How much you can push a knob before the point becomes blocking-infeasible.")
                    if not callable(time_to_failure_along_knob) or Evaluator is None:
                        st.info("Time-to-failure engine unavailable.")
                    else:
                        knob = st.selectbox("Knob", options=[x_key, y_key], index=0, key=f"scan_ttf_knob_{it}")
                        direction = st.radio("Direction", options=["Increase", "Decrease"], horizontal=True, key=f"scan_ttf_dir_{it}")
                        d = 1.0 if direction == "Increase"else -1.0
                        max_rel = st.slider("Max relative push", 0.05, 1.0, 0.5, 0.05, key=f"scan_ttf_max_{it}")
                        if st.button("Compute push-to-fail", key=f"scan_ttf_run_{it}", use_container_width=True):
                            try:
                                ev_local = _dsg_evaluator(origin="UI", cache_enabled=True)
                                rel = time_to_failure_along_knob(
                                    evaluator=ev_local,
                                    base_inputs=base,
                                    point_overrides=point_overrides,
                                    intent=str(it),
                                    knob=str(knob),
                                    direction=float(d),
                                    max_rel=float(max_rel),
                                )
                                if rel is None:
                                    st.info("No failure found within bounds (or point not feasible).")
                                else:
                                    st.success(f"Fails after ≈ {100.0*rel:.1f}% {direction.lower()} in {knob}.")
                            except Exception as e:
                                st.error(f"Time-to-failure failed: {e}")

                with tabs[2]:
                    st.caption("Stress-test this cell under small uncertainty on nuisance inputs. Reports worst-case margin and dominant-constraint probabilities.")
                    if not callable(uncertainty_stress_test) or Evaluator is None:
                        st.info("Uncertainty engine unavailable.")
                    else:
                        nuis_all = [k for k in ['R0_m','a_m','Bt_T','Ip_MA','fG','Paux_MW','kappa','Ti_keV'] if hasattr(base, k)]
                        nuis = st.multiselect("Nuisance keys", options=nuis_all, default=nuis_all[:3], key=f"scan_unc_keys_{it}")
                        rel_unc = st.slider("Relative uncertainty", 0.0, 0.15, 0.03, 0.01, key=f"scan_unc_rel_{it}")
                        n_samples = int(st.slider("Samples", 10, 200, 60, 10, key=f"scan_unc_n_{it}"))
                        seed = int(st.number_input("Seed", value=7, step=1, key=f"scan_unc_seed_{it}"))
                        if st.button("Run uncertainty stress-test", key=f"scan_unc_run_{it}", use_container_width=True):
                            try:
                                ev_local = _dsg_evaluator(origin="UI", cache_enabled=True)
                                u = uncertainty_stress_test(
                                    evaluator=ev_local,
                                    base_inputs=base,
                                    point_overrides=point_overrides,
                                    intent=str(it),
                                    nuisance_keys=list(nuis),
                                    rel_unc=float(rel_unc),
                                    n_samples=int(n_samples),
                                    seed=int(seed),
                                )
                                st.json(u, expanded=False)
                            except Exception as e:
                                st.error(f"Uncertainty test failed: {e}")

                with tabs[3]:
                    st.caption("Null direction = locally flat direction in scan space (perpendicular to margin gradient).")
                    if not callable(null_direction_2d):
                        st.info("Null-direction helper unavailable.")
                    else:
                        try:
                            # local gradient of min margin from neighbors
                            gx = 0.0
                            gy = 0.0
                            if 0 < ii < len(x_vals)-1 and 0 < jj < len(y_vals)-1:
                                gx = (mm[jj, ii+1] - mm[jj, ii-1]) / max((x_vals[ii+1]-x_vals[ii-1]), 1e-12)
                                gy = (mm[jj+1, ii] - mm[jj-1, ii]) / max((y_vals[jj+1]-y_vals[jj-1]), 1e-12)
                            nd = null_direction_2d(gx, gy)
                            st.write({"grad_dir": nd.get('grad_dir'), "flat_dir": nd.get('flat_dir')})
                            st.caption("Interpretation: moving along flat_dir tends to keep min margin nearly constant locally.")
                        except Exception as e:
                            st.error(f"Null direction unavailable: {e}")

            # Optional vector field
            with st.expander("Margin vector field (optional)", expanded=False):
                st.caption("Arrows point toward increasing min blocking margin (local safety direction).")
                if len(x_vals) >= 3 and len(y_vals) >= 3:
                    # finite differences
                    gx = np.zeros_like(mm)
                    gy = np.zeros_like(mm)
                    for j in range(1, len(y_vals)-1):
                        for i in range(1, len(x_vals)-1):
                            gx[j,i] = (mm[j,i+1] - mm[j,i-1]) / max((x_vals[i+1]-x_vals[i-1]), 1e-12)
                            gy[j,i] = (mm[j+1,i] - mm[j-1,i]) / max((y_vals[j+1]-y_vals[j-1]), 1e-12)
                    fig2, ax2 = plt.subplots(figsize=(7.6, 4.4))
                    ax2.imshow(ok, origin="lower", aspect="auto")
                    step = max(1, int(max(len(x_vals), len(y_vals)) / 20))
                    X, Y = np.meshgrid(np.arange(len(x_vals)), np.arange(len(y_vals)))
                    ax2.quiver(X[::step,::step], Y[::step,::step], gx[::step,::step], gy[::step,::step], angles='xy', scale_units='xy', scale=None)
                    ax2.set_title("Vector field over blocking feasibility (background)")
                    ax2.set_xlabel(f"{x_key}")
                    ax2.set_ylabel(f"{y_key}")
                    st.pyplot(fig2, use_container_width=True)
                else:
                    st.info("Increase Nx/Ny to at least 3 for a vector field.")

            # Robustness map (labels)
            with st.expander("Robustness (brutally honest)", expanded=False):
                # summarize counts
                flat = [str(x) for x in rb.flatten().tolist()]
                counts = {k: flat.count(k) for k in sorted(set(flat))}
                st.write({k: f"{v} ({v/len(flat):.0%})"for k, v in counts.items()})

        # Constraint interaction map (coupling view)
        with st.expander("Constraint interaction map (coupling)", expanded=False):
            st.caption("Matrix: how often constraint A appears before B in the local failure order. Descriptive only.")
            inter = rep.get('interaction') or {}
            if isinstance(inter, dict):
                iit = st.selectbox("Intent", options=intents2, index=0, key="scan_inter_intent")
                blob = (inter.get('intents') or {}).get(iit, {}) if isinstance(inter.get('intents'), dict) else {}
                names = blob.get('names') if isinstance(blob, dict) else None
                mat = blob.get('before_counts') if isinstance(blob, dict) else None
                if isinstance(names, list) and isinstance(mat, dict):
                    import pandas as pd
                    dfm = pd.DataFrame(mat)
                    dfm = dfm.reindex(index=names, columns=names)
                    st.dataframe(dfm, use_container_width=True)
                else:
                    st.info("Interaction data unavailable in this report.")
            else:
                st.info("Interaction data unavailable.")

        # Intent split overlay guidance
        if len(intents2) >= 2:
            st.markdown("### Intent-split insight")
            st.caption("Run the same scan with both intents to see how Research-feasible regions differ from Reactor-feasible regions.")

    # Render world-class scan panel
    try:
        _v188_scan_lab_panel()
    except Exception as _e:
        st.error(f"Scan Lab error: {_e}")

    # NOTE: Scan Lab freeze/legacy/parameter-guide/mapping panels are rendered inside Scan Lab
    # (before Cartography) to reduce scroll fatigue and keep the instrument literacy in one place.
