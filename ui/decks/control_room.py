"""Control Room deck -- extracted from ui/app.py (UI redesign, Control Room
incremental extraction).

The Control Room deck was fragmented across ~40 top-level
`if _deck == "Control Room":` blocks in app.py, interleaved with module-level
helper defs and the other deck routers. This module merges those block bodies
(into one render_control_room function, in original order) using the
namespace-bridge router pattern (with app.py's __file__ injected so all
Path(__file__).resolve().parent.parent / .parents[1] path computations still
resolve to the SHAMS-0D root, and so all app.py module-level names -- the
interleaved helper defs and the _v* panel defs -- resolve as before).

Pure move + cosmetic de-emoji (already done in app.py batch 8). No physics,
constraint, solver, evaluator, session-state key, or routing-ID changes.
Widget keys preserved. Temporary tech debt; replace the namespace bridge with
explicit imports/ctx in a later cleanup commit.
"""
from __future__ import annotations
import streamlit as st
import sys


def render_control_room(_app_module) -> None:
    _g = globals()
    for _k, _v in vars(_app_module).items():
        if not _k.startswith('__'):
            _g[_k] = _v
    _g['__file__'] = _app_module.__file__

    # --- Control Room block 0 (was app.py lines 2831..3409) ---
    st.header("Control Room")
    st.caption("Governance, provenance, exports, and expert diagnostics - organized as compact decks (no scroll walls).")

    deck_orient, deck_const, deck_prov, deck_art, deck_diag, deck_chron = st.tabs([
        "Orientation",
        "Constitution",
        "Provenance",
        "Artifacts",
        "Diagnostics",
        "Chronicle",
    ])

    with deck_orient:
        st.subheader("Orientation")
        st.caption("Quick-start workflows and reviewer-facing scope anchors (UI-only; does not modify truth).")
        o_launch, o_vocab, o_gallery, o_scope = st.tabs(["Launchpad", "Vocabulary", "Reference Gallery", "Scope"])

        with o_launch:
            st.subheader("Launchpad - First 30 Minutes")
            st.caption("A guided entry path for fusion experts: choose intent, then follow a minimal, honest workflow. UI scaffolding only.")
            _path = st.radio(
                "I want to…",
                [
                    "Understand feasibility limits (cartography)",
                    "Explore reactor concepts (Forge)",
                    "Review a finished case (Review Room)",
                    "Compare designs (Artifacts)",
                ],
                index=0,
                key="launchpad_path",
                horizontal=False,
            )
            if _path == "Understand feasibility limits (cartography)":
                st.info("Recommended: Scan Lab → build Scan Atlas → inspect first-failure topology.")
                st.markdown("""
- Start with **Scan Lab - Cartography Deck**
- Choose a compact 2D scan
- Export the Scan Atlas capsule for review-room replay.
""")
            elif _path == "Explore reactor concepts (Forge)":
                st.info("Recommended: Reactor Design Forge → Casebook → Candidate Archive → Machine Dossier.")
                st.markdown("""
- Use **Forge Cockpit** with the **Helm Console**
- Keep **Margins-first** framing
- Save capsules for deterministic replay.
""")
            elif _path == "Review a finished case (Review Room)":
                st.info("Recommended: Reactor Design Forge → Review Mode → Review Trinity → Do‑Not‑Build Brief.")
                st.markdown("""
- Turn on **Review Mode**
- Use **Review Trinity** and **Conflict Atlas**
- Generate a **Reviewer Packet**.
""")
            else:
                st.info("Recommended: Compare → upload two artifacts → inspect deltas.")
                st.markdown("""
- Use **Compare artifacts** to check reproducibility
- Prefer capsule replay over manual edits.
""")

        with o_vocab:
            st.subheader("Vocabulary Ledger")
            st.caption("Fusion-native terminology mapping (SHAMS ↔ common literature ↔ PROCESS-style language).")
            try:
                _vocab = (Path(__file__).resolve().parent.parent / "docs"/ "VOCABULARY_LEDGER.md").read_text(encoding="utf-8")
            except Exception:
                _vocab = "(missing docs/VOCABULARY_LEDGER.md)"
            st.markdown(_vocab)

        with o_gallery:
            st.subheader("Reference Study Gallery")
            st.caption("Recognizable anchors for the community. These are reference contexts, not targets.")
            _gallery = [
                ("ITER-like", "Large, conservative, physics-demonstration anchor; often stress and divertor constraints dominate."),
                ("SPARC-like", "Compact high-field concept; often HTS margin and structural stress dominate."),
                ("ARC-like", "HTS reactor class; often net-electric closure and blanket/TBR proxies dominate."),
                ("DEMO-like", "Plant realism anchor; often recirculating power and availability assumptions dominate."),
            ]
            for name, note in _gallery:
                with st.expander(name, expanded=False):
                    st.write(note)
            st.info("Tip: use these as *discussion anchors* when presenting SHAMS outputs to reviewers.")

        with o_scope:
            st.subheader("Model Scope Card")
            st.caption("Always-visible scope declaration for review rooms.")
            try:
                _scope = (Path(__file__).resolve().parent.parent / "docs"/ "MODEL_SCOPE_CARD.md").read_text(encoding="utf-8")
            except Exception:
                _scope = "(missing docs/MODEL_SCOPE_CARD.md)"
            st.markdown(_scope)

    with deck_const:
        st.subheader("Constitution")
        st.caption("Frozen truth boundary, constraint constitution, and assumption ledger (read-only).")
        c_model, c_pcm, c_assump, c_docs, c_cc, c_ci, c_cp = st.tabs([
            "Model Ledger",
            "Capability Matrix",
            "Assumptions",
            "Docs",
            "Constraint Cockpit",
            "Constraint Inspector",
            "Constraint Provenance",
        ])
        tab_model = c_model
        tab_pcm = c_pcm
        tab_assumptions = c_assump
        tab_docs = c_docs
        tab_constraints = c_cc
        tab_constraint_inspector = c_ci
        tab_cprov = c_cp

    with deck_prov:
        st.subheader("Provenance")
        st.caption("Study protocol, repro lock, regression visibility, and replay tools.")
        p_studies, p_deck, p_auth, p_dec, p_dom, p_epoch, p_delta, p_regress, p_dash = st.tabs([
            "Studies",
            "Case Deck Runner",
            "Authority & Confidence",
            "Decision Consequences",
            "Authority Dominance",
            "Epoch Feasibility",
            "Scenario Delta",
            "Regression Viewer",
            "Study Dashboard",
        ])
        tab_studies = p_studies
        tab_deck = p_deck
        tab_authority_conf = p_auth
        tab_decision_conseq = p_dec
        tab_authority_dominance = p_dom
        tab_epoch_feas = p_epoch
        tab_delta = p_delta
        tab_regress = p_regress
        tab_study_dash = p_dash

    with deck_art:
        st.subheader("Artifacts")
        st.caption("Exports, evidence packs, and benchmark bundles (deterministic).")
        a_art, a_lib, a_export, a_bench = st.tabs([
            "Artifacts Explorer",
            "Run Library",
            "Export / Share",
            "Benchmarks",
        ])
        tab_artifacts = a_art
        tab_library = a_lib
        tab_export = a_export
        tab_bench = a_bench

    with deck_diag:
        st.subheader("Diagnostics")
        st.caption("Deep tools for debugging and reviewer verification (kept off the main workflow by default).")
        d_pam, d_val, d_comp, d_gate, d_nonfeas, d_solver, d_decision, d_session = st.tabs([
            "Panel Map",
            "Validation",
            "Compliance",
            "Gatechecks",
            "Non-Feasibility Guide",
            "Solver Introspection",
            "Decision Builder",
            "Session",
        ])
        tab_pam = d_pam
        tab_validation = d_val
        tab_compliance = d_comp
        tab_gatechecks = d_gate
        tab_nonfeas = d_nonfeas
        tab_solver = d_solver
        tab_decision = d_decision

        with d_gate:
            st.subheader("Gatechecks")
            st.caption("Local build integrity checks. UI-only; does not modify truth.")
            st.markdown("""
Run these from a terminal at the repo root:

- `python -m compileall -q .`
- `pytest -q`
- `streamlit run ui/app.py`

This panel also performs a lightweight hygiene scan of the working tree.
""")

            from pathlib import Path as _Path
            _root = (_Path(__file__).resolve().parent.parent)
            _forbidden = [
                '__pycache__',
                '.pytest_cache',
                'gspulse_ui',
            ]
            _hits = []
            for name in _forbidden:
                for h in _root.rglob(name):
                    _hits.append(str(h))
            # Also flag stray run_st* launchers
            for h in _root.glob('run_st*'):
                _hits.append(str(h))
            if _hits:
                st.error("Hygiene violations detected (should be removed before packaging):")
                with st.expander("Show paths", expanded=False):
                    for h in sorted(set(_hits)):
                        st.write(h)
            else:
                st.success("No hygiene violations detected in this tree.")

            st.divider()
            st.subheader("Interoperability self-check")
            st.caption("Verifies that main panels can exchange the canonical design state (no truth modifications).")

            st.divider()
            st.subheader("Interoperability contract validator (v326)")
            st.caption("Static + runtime wiring audit: declared panel contracts vs discoverable subpanels in ui/app.py.")

            def _run_contract_validator() -> dict:
                """Deterministic contract validator.

                Does not run physics or mutate truth.
                """
                from pathlib import Path as _Path
                from ui.panel_contracts import get_panel_contracts
                from tools.interoperability.contract_validator import validate_ui_contracts

                _root = (_Path(__file__).resolve().parent.parent)
                _contracts = get_panel_contracts()
                return validate_ui_contracts(_root, _contracts, session_state=dict(st.session_state))

            if st.button('Run contract validator', use_container_width=True, key='v326_contract_validator_btn'):
                st.session_state['v326_last_contract_validator_report'] = _run_contract_validator()

            _cr = st.session_state.get('v326_last_contract_validator_report')
            if isinstance(_cr, dict):
                if bool(_cr.get('ok')):
                    st.success('Contract validator: OK')
                else:
                    st.warning('Contract validator: issues detected')
                with st.expander('Contract validator report', expanded=False):
                    st.json(_cr)

            def _interop_check() -> dict:
                """Lightweight, deterministic UI-state interoperability audit.

                This is intentionally conservative: it only checks for existence and
                basic schema/type sanity of the canonical promotion keys. It does not
                run physics, solvers, or optimization.
                """
                rep = {'ok': True, 'checks': []}
                def _add(name: str, ok: bool, detail: str = ''):
                    rep['checks'].append({'name': name, 'ok': bool(ok), 'detail': str(detail)})
                    if not ok:
                        rep['ok'] = False

                # Core canonical artifacts used across modes
                for k in ['workspace_candidate', 'last_point_result', 'compare_left', 'compare_right']:
                    _add(f'session_key:{k}', k in st.session_state, 'present' if k in st.session_state else 'missing')

                # Systems mode canonical keys
                _t = st.session_state.get('systems_targets')
                _v = st.session_state.get('systems_variables')
                _add('systems_targets_type', isinstance(_t, dict) and len(_t) > 0, f"type={type(_t).__name__} len={len(_t) if isinstance(_t, dict) else 'n/a'}")
                _add('systems_variables_type', isinstance(_v, dict) and len(_v) > 0, f"type={type(_v).__name__} len={len(_v) if isinstance(_v, dict) else 'n/a'}")

                # Evidence / provenance hooks
                for k in ['last_precheck_report', 'last_systems_solution', 'last_evidence_pack_path', 'provenance_global']:
                    _add(f'provenance_key:{k}', k in st.session_state, 'present' if k in st.session_state else 'missing')

                return rep

            if st.button('Run interoperability check', use_container_width=True, key='v323_interop_check_btn'):
                st.session_state['v323_last_interop_report'] = _interop_check()

            _ir = st.session_state.get('v323_last_interop_report')
            if isinstance(_ir, dict):
                if bool(_ir.get('ok')):
                    st.success('Interoperability check: OK')
                else:
                    st.warning('Interoperability check: issues detected')
                with st.expander('Interoperability report', expanded=False):
                    st.json(_ir)

        with d_session:
            with st.expander("Session state (debug)", expanded=False):
                st.write({k: type(v).__name__ for k, v in st.session_state.items()})
            with st.expander("Version", expanded=False):
                try:
                    st.code((BASE_DIR / "VERSION").read_text().strip())
                except Exception:
                    st.code("unknown")

    with deck_chron:
        st.subheader("Chronicle")
        st.caption("Expert instruments and exploration aids (read-only; never modifies truth).")
        ch_reg, ch_sens, ch_knobs, ch_fmap, ch_mat, ch_maint, ch_prof, ch_imp, ch_disr, ch_stab, ch_solve, ch_repair, ch_refine, ch_narrow, ch_surr, ch_al = st.tabs([
            "Variable Registry",
            "Sensitivity Explorer",
            "Knob Trade-Space",
            "Feasibility Map",
            "Maturity Heatmap",
            "Maintenance & Availability",
            "Profile Authority",
            "Impurity & Radiation",
            "Disruption Risk",
            "Stability Risk",
            "Certified Search",
            "Repair Suggestions",
            "Interval Refinement",
            "Interval Narrowing",
            "Surrogate Overlay",
            "Active Learning",
        ])
        tab_registry = ch_reg
        tab_sensitivity = ch_sens
        tab_knobs = ch_knobs
        tab_feasmap = ch_fmap
        tab_maturity = ch_mat
        tab_maintenance = ch_maint
        tab_profile_auth = ch_prof
        tab_impurity = ch_imp
        tab_disruption = ch_disr
        tab_stability = ch_stab
        tab_cert_search = ch_solve
        tab_repair = ch_repair
        tab_refine = ch_refine
        tab_narrowing = ch_narrow
        tab_surrogate = ch_surr
        tab_active_learning = ch_al

    # Populate Control Room sections (ensure they are never empty)
    with tab_pam:
        _v175_panel_availability_map_panel()
    
    with tab_studies:
        st.markdown("### Study authority & publishability")
        st.write("Generate protocol → lock/replay → authority pack → citation → export.")
        try:
            _render_with_contract("_v165_study_protocol_panel", _v165_study_protocol_panel)
        except Exception:
            st.info('Panel unavailable in this build.')
        st.divider()
        try:
            _render_with_contract("_v166_repro_lock_panel", _v166_repro_lock_panel)
        except Exception:
            st.info('Panel unavailable in this build.')
        st.divider()
        try:
            _render_with_contract("_v167_authority_pack_panel", _v167_authority_pack_panel)
        except Exception:
            st.info('Panel unavailable in this build.')
        st.divider()
        try:
            _render_with_contract("_v168_citation_panel", _v168_citation_panel)
        except Exception:
            st.info('Panel unavailable in this build.')
        st.divider()
        try:
            _render_with_contract("_v170_process_export_panel", _v170_process_export_panel)
        except Exception:
            st.info('Panel unavailable in this build.')
    st.divider()
    with st.expander("Studies manager", expanded=False):
        st.header("Studies manager")
        st.write("Save, load, and organize study configurations (scan/pareto) as JSON. This keeps studies reproducible across sessions.")
        if "studies"not in st.session_state:
            st.session_state.studies = []

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Save current PointInputs as study", use_container_width=True):
                if st.session_state.get("last_point_inp") is not None:
                    try:
                        inp_obj = st.session_state.last_point_inp
                        # dataclass -> dict
                        d = {k: getattr(inp_obj, k) for k in inp_obj.__dataclass_fields__.keys()}  # type: ignore
                        st.session_state.studies.append({"type": "point", "created": datetime.datetime.now().isoformat(), "inputs": d})
                        st.success("Saved.")
                    except Exception as e:
                        st.error(f"Could not save: {e}")
                else:
                    st.warning("Run a point first so `last_point_inp` exists.")

        with c2:
            up = st.file_uploader("Import studies JSON", type=["json"], key="studies_import")
            if up is not None:
                try:
                    imported = json.loads(up.getvalue().decode("utf-8"))
                    if isinstance(imported, list):
                        st.session_state.studies.extend(imported)
                    elif isinstance(imported, dict):
                        st.session_state.studies.append(imported)
                    st.success("Imported.")
                except Exception as e:
                    st.error(f"Import failed: {e}")

        with c3:
            if st.session_state.studies:
                st.download_button(
                    "Download studies JSON",
                    data=json.dumps(st.session_state.studies, indent=2, sort_keys=True),
                    file_name="shams_studies.json",
                    mime="application/json",
                    use_container_width=True,
                )

        st.markdown("### Saved studies")
        if st.session_state.studies:
            df = pd.DataFrame([{"i": i, "type": s.get("type","?"), "created": s.get("created",""), "notes": s.get("notes","")} for i,s in enumerate(st.session_state.studies)])
            st.dataframe(df, use_container_width=True)
            idx = st.number_input("Select index to view", min_value=0, max_value=max(0, len(st.session_state.studies)-1), value=0, step=1)
            st.json(st.session_state.studies[int(idx)])
            if st.button("Delete selected", use_container_width=True):
                try:
                    st.session_state.studies.pop(int(idx))
                    st.experimental_rerun()
                except Exception:
                    pass
        else:
            st.info("No studies saved yet.")


    
    with tab_model:
        # Render with proper scientific notation (MathJax) to avoid “ASCII-looking” formulas.
        st.markdown(
            """
    This section documents the **0‑D (global) physics + engineering surrogate** used by SHAMS for rapid point design.
    It is intentionally transparent: the goal is to show the **model structure**, **assumptions**, and **where each number comes from**.
    
    #### Symbol key (as used below)
    - $R_0$ major radius, $a$ minor radius, $\\kappa$ elongation, $\\delta$ triangularity
    - $B_t$ toroidal field on axis, $I_p$ plasma current
    - $n$ density, $T$ temperature, $V$ plasma volume, $W$ stored energy
    - $P_{fus}$ fusion power, $P_{\\alpha}$ alpha power, $P_{aux}$ auxiliary power, $P_{SOL}$ power crossing the separatrix
    - $\\tau_E$ energy confinement time, $H$ confinement multiplier (H‑factor)
    """
        )
    
        st.markdown("#### High‑level flow (per point evaluation)")
        st.markdown(
            """
    1. **Geometry:** $(R_0, a, \\kappa, \\delta) \\rightarrow$ volumes/areas.
    2. **Plasma state:** choose targets/intent $\\rightarrow$ infer a consistent $(T, n, B_t, I_p)$ under constraints.
    3. **Power balance:** $P_{fus}, P_{\\alpha}, P_{aux}$ and losses $\\rightarrow$ steady‑state balance.
    4. **Confinement:** $\\tau_E$ from selected scaling (ITER98y2 / others) with $H$; enforce $Q$ consistency.
    5. **Current & stability:** $q_{95}$, $\\beta_N$, Greenwald fraction $f_G$.
    6. **Engineering proxies:** TF peak field / hoop stress, HTS margin.
    7. **Blanket/shield/TBR proxy:** thickness & coverage $\\rightarrow$ TBR screening.
    8. **Divertor proxy:** heat‑flux screening from $P_{SOL}$ and geometry.
    9. **Radial build closure:** inboard stack fits (gap + FW + blanket + shield + VV + TF).
    """
        )
    
        st.markdown("#### Core relationships (representative)")
        st.latex(
            r"""
    \begin{aligned}
    P_{fus} &\propto n^2\,\langle\sigma v\rangle(T)\,V \\
    \tau_E &= H\,\tau_{\mathrm{ITER98y2}}(I_p, B_t, n, P, R_0, a, \kappa, \ldots) \\
    P_{heat} &= P_{\alpha} + P_{aux} \\
    P_{loss} &\approx \frac{W}{\tau_E}\;\; (\text{plus radiation terms where enabled}) \\
    q_{95} &\approx \frac{5\,a^2\,B_t}{R_0\,I_p}\,f(\kappa,\delta) \\
    \beta_N &\approx \beta\,\frac{a\,B_t}{I_p} \\
    q_{div} &\approx \frac{P_{SOL}}{2\pi R_0\,\lambda_q}\,g_{exh}(\text{geometry}) \\
    \sigma_{TF} &\propto \frac{B_{peak}^2\,R_{coil}}{\mu_0}
    \end{aligned}
    """
        )
        st.caption(
            "These are screening/closure relationships to support feasibility-first iteration. Exact authoritative pass/fail logic lives in SHAMS constraints and margins."
        )
    
    
    with tab_pcm:
        st.markdown("### Physics Capability Matrix")
        st.caption(
            "Read-only audit map: subsystems → equations/closures → authority tier (proxy/parametric/external) → intended validity domain."
        )
        try:
            # v228+: prefer generator-derived snapshot if present (still read-only).
            p_gen = (BASE_DIR / "docs"/ "PHYSICS_CAPABILITY_MATRIX_GENERATED.md")
            p_src = (BASE_DIR / "docs"/ "PHYSICS_CAPABILITY_MATRIX.md")
            if p_gen.exists():
                _pcm = p_gen.read_text(encoding="utf-8", errors="ignore")
            else:
                _pcm = p_src.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            _pcm = "(missing docs/PHYSICS_CAPABILITY_MATRIX*.md)"
        st.markdown(_pcm)
        st.info(
            "Bluemira-inspired lessons are adopted for provenance and capability clarity - without introducing optimization loops or CAD-level coupling.",
        )
    with tab_bench:
    
        st.markdown("### Benchmarks")
        st.write("Benchmark runners (validation/regression) are available via the advanced panels once you have run artifacts.")
    
        st.markdown("#### Reference superconducting tokamaks (quick lookup)")
        st.markdown(
            """
    | Tokamak | Country / Org | Status | SC type | Major R (m) | Minor a (m) | B₀ on axis (T) | Ip (MA) | Primary role |
    |---|---|---|---|---:|---:|---:|---:|---|
    | **ITER** | Intl (EU/JP/US/etc.) | Under construction | **Nb₃Sn / NbTi (LTS)** | 6.2 | 2.0 | 5.3 | 15 | Burning plasma, Q≈10 |
    | **JT-60SA** | Japan–EU | Commissioning | **NbTi (LTS)** | 2.96 | 1.18 | 2.25 | 5.5 | Advanced plasma physics |
    | **WEST** | France | Operating | **NbTi (LTS)** | 2.5 | 0.5 | 3.7 | ≤1 | Long-pulse, PFC/divertor |
    | **EAST** | China | Operating | **NbTi (LTS)** | 1.8–1.9 | 0.4–0.45 | ≤3.5 | ≤1 | Long-pulse operation |
    | **KSTAR** | Korea | Operating | **NbTi-based (LTS)** | ~1.8 | ~0.5 | 3.5 | ≤2 | Advanced tokamak scenarios |
    | **SST-1** | India | Operating | **NbTi (LTS)** | ~1.1 | ~0.2 | ≤3 | ≤0.1 | SC tokamak development |
    | **TRIAM-1M** | Japan | Historical | **Nb₃Sn (LTS)** | ~0.8 | ~0.12–0.18 | 8 | - | High-field SC operation |
    | **SPARC** | USA (MIT/CFS) | Under construction | **REBCO (HTS)** | 1.85 | 0.57 | 12.2 | 8.7 | Q>1, high-field compact |
    """
        )
        st.caption(
            "Values are typical/design-point numbers collected from public summaries. For rigorous comparison, cite primary machine parameter sheets."
        )
        st.write("Below is a quick reference table of major superconducting tokamaks used as comparison anchors.")
    
        try:
            import pandas as _pd
            _bench_rows = [
                {"Tokamak":"ITER","Country / Org":"Intl (EU/JP/US/etc.)","Status":"Under construction","SC type":"Nb₃Sn / NbTi (LTS)","Major R (m)":6.2,"Minor a (m)":2.0,"B₀ on axis (T)":5.3,"Ip (MA)":15.0,"Primary role":"Burning plasma, Q≈10"},
                {"Tokamak":"JT-60SA","Country / Org":"Japan–EU","Status":"Commissioning","SC type":"NbTi (LTS)","Major R (m)":3.0,"Minor a (m)":1.0,"B₀ on axis (T)":2.3,"Ip (MA)":5.5,"Primary role":"Advanced plasma physics"},
                {"Tokamak":"WEST","Country / Org":"France","Status":"Operating","SC type":"NbTi (LTS)","Major R (m)":2.5,"Minor a (m)":0.5,"B₀ on axis (T)":3.7,"Ip (MA)":1.0,"Primary role":"Long-pulse, PFC/divertor"},
                {"Tokamak":"EAST","Country / Org":"China","Status":"Operating","SC type":"NbTi (LTS)","Major R (m)":1.9,"Minor a (m)":0.5,"B₀ on axis (T)":3.5,"Ip (MA)":1.0,"Primary role":"Long-pulse operation"},
                {"Tokamak":"KSTAR","Country / Org":"Korea","Status":"Operating","SC type":"NbTi-based (LTS)","Major R (m)":1.8,"Minor a (m)":0.5,"B₀ on axis (T)":3.5,"Ip (MA)":2.0,"Primary role":"Advanced tokamak scenarios"},
                {"Tokamak":"SST-1","Country / Org":"India","Status":"Operating","SC type":"NbTi (LTS)","Major R (m)":1.1,"Minor a (m)":0.2,"B₀ on axis (T)":3.0,"Ip (MA)":0.1,"Primary role":"SC tokamak development"},
                {"Tokamak":"TRIAM-1M","Country / Org":"Japan","Status":"Historical","SC type":"Nb₃Sn (LTS)","Major R (m)":0.8,"Minor a (m)":0.15,"B₀ on axis (T)":8.0,"Ip (MA)":None,"Primary role":"High-field SC operation"},
                {"Tokamak":"HT-7","Country / Org":"China","Status":"Historical","SC type":"LTS","Major R (m)":1.22,"Minor a (m)":0.27,"B₀ on axis (T)":2.0,"Ip (MA)":0.2,"Primary role":"Precursor to EAST"},
                {"Tokamak":"SPARC","Country / Org":"USA (MIT/CFS)","Status":"Under construction","SC type":"REBCO (HTS)","Major R (m)":1.85,"Minor a (m)":0.57,"B₀ on axis (T)":12.2,"Ip (MA)":8.7,"Primary role":"Q>1, high-field compact"},
                {"Tokamak":"HH70","Country / Org":"China (Energy Singularity)","Status":"Operating","SC type":"REBCO (HTS)","Major R (m)":0.7,"Minor a (m)":0.28,"B₀ on axis (T)":0.6,"Ip (MA)":None,"Primary role":"Full-HTS integration demo"},
                {"Tokamak":"HH170","Country / Org":"China (Energy Singularity)","Status":"Planned","SC type":"REBCO (HTS)","Major R (m)":None,"Minor a (m)":None,"B₀ on axis (T)":None,"Ip (MA)":None,"Primary role":"Reactor-relevant HTS tokamak"},
            ]
            _df = _pd.DataFrame(_bench_rows)
            st.dataframe(_df, use_container_width=True, hide_index=True)
            st.caption("Notes: Some entries are approximate screening values (as shown). Replace with cited values if you enable web-backed references.")
        except Exception:
            st.info("Benchmark reference table unavailable in this environment.")
    
    with tab_docs:
        st.markdown("### Documentation")
        st.write("Offline docs are included in the package. Review-room and exposure guardrails are included as dedicated docs pages. Key references live in the `docs/` folder when present.")
        st.caption("Note: The **Model Ledger (0‑D Physics)** panel renders equations using LaTeX/MathJax for scientific typography.")
    
        try:
            from pathlib import Path as _P
    
            _readme = _P("README.md")
            if _readme.exists():
                with st.expander("README (excerpt)", expanded=False):
                    st.code(_readme.read_text(encoding="utf-8")[:3000])
    
            _docs_dir = _P("docs")
            _mds = []
            if _docs_dir.exists():
                _mds = sorted([pp for pp in _docs_dir.rglob("*.md") if pp.is_file()])
    
            if _mds:
                st.markdown("#### Docs library")
                _labels = [str(pp.relative_to(_docs_dir)) for pp in _mds]
                _sel = st.selectbox("Open a doc (read‑only)", _labels, index=0)
                _path = _docs_dir / _sel
                with st.expander(f"docs/{_sel}", expanded=False):
                    st.markdown(_path.read_text(encoding="utf-8"))
            else:
                st.info("No `docs/` folder was found in this build.")
        except Exception:
            pass
    
    with tab_artifacts:
        st.markdown("### Artifacts")
        st.write("Artifacts appear after you run Point Designer / Systems Mode.")
        st.write("Use Run Library / Export tools to download bundles.")
    
    # For remaining expanders, ensure a minimal non-empty body
    for _exp in [tab_registry, tab_validation, tab_compliance, tab_deck, tab_delta, tab_library, tab_constraints,
                tab_constraint_inspector, tab_sensitivity, tab_feasmap, tab_decision, tab_nonfeas, tab_cprov,
                tab_knobs, tab_regress, tab_study_dash, tab_maturity, tab_assumptions, tab_export, tab_solver]:
        with _exp:
            st.write("This tool becomes active when required upstream artifacts exist (run history, packs, or reports).")
            st.write("If you need something here, run a study first, then return to More.")



    # --- Control Room block 1 (was app.py lines 3462..3674) ---
    with tab_model:
        st.header("0-D Tokamak Physics Model (Phase‑1)")

        with st.expander("0‑D Physical Models - explanations", expanded=False):
            _pm = os.path.join(ROOT, "docs", "PHYSICAL_MODELS_0D.md")
            try:
                with open(_pm, "r", encoding="utf-8") as _f:
                    st.markdown(_f.read())
            except Exception as _e:
                st.error(f"Failed to load physical model doc: {_e}")


        st.markdown(r"""
        This tab is written to be **actionable**: each section maps to code in `src/physics/`, `src/phase1_models.py`,
        `src/phase1_systems.py`, and `src/solvers/`.

        SHAMS remains a **0‑D / volume‑averaged / steady‑state** point-design model at its core, intended for *fast feasibility scanning*.
        Over time we have added several **external systems codes‑inspired** upgrades that remain lightweight and Windows‑friendly:

        - **Optional analytic profiles ("½‑D")** for $n_e(\rho)$, $T_i(\rho)$, $T_e(\rho)$ with **normalization to the chosen volume averages**,
          plus derived averages like peaking factors and $\langle n_e^2 \rangle/\langle n_e \rangle^2$.
        - **Radiation options:** legacy fractional radiation (stable for scans) and a physics‑based path (brem + synchrotron + simple impurity line radiation).
        - **Constraint system:** engineering and plasma constraints are represented as reusable objects (external systems codes‑like), usable by scans and vector solvers.
        - **Solvers:** classic nested 1‑D solves are still available, plus a more general bounded "targets → variables"solve primitive.

        It is **not** a full transport / equilibrium / neutronics code, but it is designed to grow in that direction while staying usable.
        """)

        st.caption("Tip: expand only the models you care about - each block is independent.")

        # --- Geometry ---
        with st.expander("Geometry: volume and surface area (implemented)", expanded=False):
            st.markdown(r"""
            Implemented helpers:

            **Plasma volume** (`tokamak_volume`)
            $$
            V \approx 2\pi^2\,R\,a^2\,\kappa
            $$

            **Plasma surface area** (`tokamak_surface_area`)
            $$
            S \approx 4\pi^2\,R\,a\,\kappa
            $$

            Notes:
            - These are **engineering approximations** intended to preserve correct monotonic trends.
            - Units: $R,a$ in m, $V$ in m$^3$, $S$ in m$^2$.
            """)

        # --- Confinement ---
        with st.expander("Energy confinement: IPB98(y,2) (implemented)"):
            st.markdown(r"""
            Implemented model: `tauE_ipb98y2`.

            $$
            \tau_E = 0.0562\, I_p^{0.93} B_t^{0.15} \bar{n}^{0.41} P_{loss}^{-0.69} R^{1.97} \epsilon^{0.58} \kappa^{0.78} M^{0.19}
            $$
            where $\epsilon=a/R$.

            **Units (must match the implementation):**
            - $I_p$ in MA
            - $B_t$ in T
            - $\bar{n}$ in units of $10^{20}\,\mathrm{m^{-3}}$ (i.e. `ne20`)
            - $P_{loss}$ in MW
            - $R,a$ in m
            - $M$ in amu (default 2.5)

            Output: $\tau_E$ in seconds.
            """)

        # --- L-H threshold ---
        with st.expander("H-mode access: Martin-2008 L–H threshold (implemented)"):
            st.markdown(r"""
            Implemented model: `p_LH_martin08`.

            $$
            P_{LH} = 0.0488\, \bar{n}^{0.717} B_t^{0.803} S^{0.941}\,\left(\frac{2}{A_{eff}}\right)
            $$

            **Units:**
            - $\bar{n}$ in $10^{20}\,\mathrm{m^{-3}}$ (line-averaged)
            - $B_t$ in T
            - $S$ in m$^2$ (uses the same proxy as the geometry block)
            - $A_{eff}$ dimensionless (defaults to 2.0)

            Output: $P_{LH}$ in MW.
            """)

        # --- Greenwald ---
        with st.expander("Density limit: Greenwald (implemented)"):
            st.markdown(r"""
            Implemented helper: `greenwald_density_20`.

            $$
            n_{GW}\,[10^{20}\,\mathrm{m^{-3}}] = \frac{I_p\,[\mathrm{MA}]}{\pi a^2\,[\mathrm{m^2}]}
            $$

            In scans, an operating fraction is typically applied:
            $$
            \bar{n} = f_{nG}\,n_{GW},\qquad 0 < f_{nG} \le 1.
            $$
            """)

        # --- Screening proxies ---
        with st.expander("Screening proxies: q95, βN, bootstrap fraction (implemented proxies)"):
            st.markdown(r"""
            These are explicitly labeled **proxies** (trend-correct, not equilibrium/transport solutions).

            **q95 proxy** (`q95_proxy_cyl`)
            $$
            q_{95} \approx \left(\frac{2\pi R B_t}{\mu_0 I_p}\right)\left(\frac{a}{R}\right)\frac{1}{\kappa}
            $$
            with $I_p$ converted to amperes internally.

            **Normalized beta** (`betaN_from_beta`)
            $$
            \beta_N = \beta(\%)\,\frac{a\,B_t}{I_p}
            \qquad\text{with}\qquad \beta(\%)=100\,\beta
            $$
            where $\beta$ is the *fractional* beta.

            **Bootstrap fraction proxy** (`bootstrap_fraction_proxy`)
            $$
            f_{bs} \approx C_{bs}\,\frac{\beta_N}{q_{95}}
            $$
            then clamped to a configured range (default 0 to 0.95).
            """)

        # --- Fusion reactivity ---
        with st.expander("Fusion reactivity: Bosch–Hale ⟨σv⟩ (implemented)"):
            st.markdown(r"""
            Implemented function: `bosch_hale_sigmav(T_i, reaction)`.

            This uses the Bosch–Hale parameterization for Maxwellian-averaged reactivity:
            $$
            \langle\sigma v\rangle(T_i)\;[\mathrm{m^3/s}]
            $$

            Internally, the implementation computes intermediate variables ($\theta$, $\xi$) from a
            reaction-specific coefficient set and returns a strictly non-negative value.

            **Important for UI users:**
            - Input $T_i$ is in **keV**.
            - Output is in **m$^3$/s**.
            """)

            # Bosch–Hale coefficient values used by the implementation (from `BH_COEFFS`)
            _bh_rows = []
            for _rxn in ["DT", "DD_Tp", "DD_He3n"]:
                _c = BH_COEFFS[_rxn]
                _bh_rows.append({"Reaction": _rxn, **asdict(_c)})
            _bh_df = pd.DataFrame(_bh_rows).set_index("Reaction")
            st.caption("Bosch–Hale coefficients used for DT and DD channels (exact values as implemented).")
            st.dataframe(_bh_df, use_container_width=True)

        # --- Fusion power / gain symbols (fixing the screenshot issue) ---
        with st.expander("Fusion power & gain definitions: P_f, P_α, Q (notation)"):
            st.markdown(r"""
            **What these symbols mean (and how they relate):**

            **Fusion power, $P_f$**  
            Total thermal power released by fusion reactions occurring in the plasma:
            $$
            P_f \;=\; \dot{N}_{\text{fus}}\,E_{\text{fus}}
            $$
            where $\dot{N}_{\text{fus}}$ is the fusion reaction rate [1/s] and $E_{\text{fus}}$ is the energy released per reaction.
            For D‑T, $E_{\text{fus}} = 17.6\,\mathrm{MeV}$.

            **Alpha heating power, $P_{\alpha}$**  
            Part of $P_f$ carried by *charged* alpha particles and deposited back into the plasma (self‑heating):
            $$
            P_{\alpha} \;=\; f_\alpha\,P_f
            $$
            For D‑T, $f_\alpha = \frac{3.5}{17.6} \approx 0.199$, so $P_{\alpha} \approx 0.20\,P_f$.
            (The rest is mainly neutron power: $P_n \approx 0.80\,P_f$.)

            **Fusion gain, $Q$**  
            In this UI, $Q$ is the standard *plasma gain*:
            $$
            Q \;=\; \frac{P_f}{P_{\mathrm{aux}}}
            $$
            where $P_{\mathrm{aux}}$ is the **externally applied** auxiliary heating power (e.g., NBI/RF) required to sustain the operating point.
            This is distinct from “wall‑plug” gain, which would include plant efficiencies and non‑plasma power draws.

            **How to interpret in scans**
            - Increasing $P_f$ increases $P_{\alpha}$ proportionally (more self‑heating).  
            - $Q$ improves only when $P_f$ grows faster than the required $P_{\mathrm{aux}}$.
            """)

        # --- SOL width metric ---
        with st.expander("Optional divertor/SOL risk metric: Eich λq (implemented)"):
            st.markdown(r"""
            Implemented metric: `lambda_q_eich14_mm`.

            $$
            \lambda_q\,[\mathrm{mm}] \approx \text{factor}\times 0.63\,B_{pol}^{-1.19}
            $$

            with $B_{pol}$ approximated by:
            $$
            B_{pol} \approx \frac{\mu_0 I_p}{2\pi a}
            $$

            This is **not** a self‑consistent divertor / edge power‑exhaust model - it’s a compact, order‑of‑magnitude **screening proxy** for quickly comparing design points.
            """)

        st.info(
            "If you want the *full* step-by-step closure shown here (power balance → temperatures → Pf/Q), "
            "tell me which exact function in `src/phase1_core.py` you want treated as the single source of truth, "
            "and I’ll mirror it line-for-line in this tab."
        )



    # --- Control Room block 2 (was app.py lines 3679..3942) ---
    with tab_bench:
        st.subheader("Regression Benchmarks")
        st.write("Run a small suite of SPARC-like cases to ensure recent physics/solver changes haven't broken behavior.")

        import json
        from pathlib import Path

        bench_dir = Path(__file__).resolve().parent.parent / "benchmarks"
        cases_path = bench_dir / "cases.json"
        golden_path = bench_dir / "golden.json"

        diff_path = bench_dir / "last_diff_report.json"
        with st.expander("Latest diff report (from last run)", expanded=False):
            if diff_path.exists():
                try:
                    rep = json.loads(diff_path.read_text(encoding="utf-8"))
                    st.caption(f"Generated at unix={rep.get('created_unix'):.0f} | failures={rep.get('n_failed',0)}")
                    rows = rep.get("rows", [])
                    if rows:
                        import pandas as pd

                        df_rep = pd.DataFrame(rows)
                        # show worst first
                        if "ok"in df_rep.columns and "rel_err"in df_rep.columns:
                            df_rep = df_rep.sort_values(by=["ok","rel_err"], ascending=[True, False])
                        st.dataframe(df_rep, use_container_width=True, height=260)
                    # Structural diffs (constraints/model cards) vs golden artifacts, if present
                    ss = rep.get("structural_summary")
                    if ss:
                        st.markdown("**Structural diffs vs golden artifacts**")
                        st.write({k: ss.get(k) for k in ["n_cases","n_with_changes","total_added_constraints","total_removed_constraints","total_changed_constraints","total_modelcard_changes"]})
                    structural = rep.get("structural") or {}
                    if structural:
                        with st.expander("Show structural diffs by case", expanded=False):
                            for cname, d in structural.items():
                                cadd = d.get("constraints", {}).get("added", [])
                                crem = d.get("constraints", {}).get("removed", [])
                                cchg = d.get("constraints", {}).get("changed_meta", [])
                                mc = d.get("model_cards", {})
                                mcchg = (mc.get("added", []) or []) + (mc.get("removed", []) or []) + (mc.get("changed", []) or [])
                                if not (cadd or crem or cchg or mcchg or (d.get("schema_version", {}).get("new") != d.get("schema_version", {}).get("old"))):
                                    continue
                                with st.expander(f"{cname}", expanded=False):
                                    if cadd: st.write({"constraints_added": cadd})
                                    if crem: st.write({"constraints_removed": crem})
                                    if cchg: st.write({"constraint_meta_changes": cchg})
                                    if mc.get("added"): st.write({"model_cards_added": mc.get("added")})
                                    if mc.get("removed"): st.write({"model_cards_removed": mc.get("removed")})
                                    if mc.get("changed"): st.write({"model_cards_changed": mc.get("changed")})

                    st.download_button("Download diff report JSON", data=diff_path.read_bytes(), file_name="last_diff_report.json")
                except Exception as e:
                    st.warning(f"Could not read diff report: {e}")
            else:
                st.info("No diff report yet. Run benchmarks to generate one.")


        # Release notes (auto-generated)
        with st.expander("Release notes (auto)", expanded=False):
            import subprocess, sys
            from pathlib import Path

            repo_root = Path(__file__).resolve().parent.parent
            out_md = repo_root / "RELEASE_NOTES.md"
            old_default = str((repo_root.parent / "SHAMS_old").resolve()) if (repo_root.parent / "SHAMS_old").exists() else r"..\SHAMS_old"
            old_path = st.text_input("Old SHAMS repo path", value=st.session_state.get("release_notes_old", old_default))
            st.session_state["release_notes_old"] = old_path

            auto = st.checkbox("Auto-generate if missing/out-of-date", value=True, key="release_notes_auto")
            run_now_rn = st.button("Generate release notes now", key="btn_release_notes_now")

            def _needs_rn() -> bool:
                if not out_md.exists():
                    return True
                try:
                    m_out = out_md.stat().st_mtime
                    # regenerate if diff report is newer, or tool changed
                    tool_p = repo_root / "tools"/ "release_notes.py"
                    diff_p = repo_root / "benchmarks"/ "last_diff_report.json"
                    newest = max([p.stat().st_mtime for p in [tool_p, diff_p] if p.exists()] + [0])
                    return newest > m_out
                except Exception:
                    return False

            if (auto and _needs_rn() and not st.session_state.get("_rn_ran_this_session", False)) or run_now_rn:
                cmd = [sys.executable, str(repo_root / "tools"/ "release_notes.py"), "--old", old_path, "--new", str(repo_root), "--out", str(out_md)]
                st.caption("Running: "+ " ".join(cmd))
                try:
                    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(repo_root))
                    st.session_state["_rn_last_stdout"] = p.stdout
                    st.session_state["_rn_last_stderr"] = p.stderr
                    st.session_state["_rn_last_rc"] = p.returncode
                    st.session_state["_rn_ran_this_session"] = True
                except Exception as e:
                    st.session_state["_rn_last_stderr"] = str(e)
                    st.session_state["_rn_last_rc"] = 1

            rc = st.session_state.get("_rn_last_rc")
            if rc is not None:
                if rc == 0:
                    st.success("Release notes generated.")
                else:
                    st.warning("Release notes generation had issues (see logs).")
                with st.expander("Logs", expanded=False):
                    st.code((st.session_state.get("_rn_last_stdout") or "") + "\n"+ (st.session_state.get("_rn_last_stderr") or ""))

            if out_md.exists():
                st.markdown(out_md.read_text(encoding="utf-8", errors="ignore"))
                st.download_button("Download RELEASE_NOTES.md", data=out_md.read_bytes(), file_name="RELEASE_NOTES.md", mime="text/markdown")
            else:
                st.info("RELEASE_NOTES.md not found yet.")

        with st.expander("Regression comparisons", expanded=False):
            colA, colB = st.columns([1,1])
            with colA:
                run_now = st.button("Run benchmarks")
            with colB:
                regen = st.button("Regenerate golden (intentional changes)")
    
            def _safe(v):
                try:
                    return float(v)
                except Exception:
                    return float("nan")
    
            if cases_path.exists():
                _cases_raw = json.loads(cases_path.read_text())
            else:
                _cases_raw = {}
    
            # Normalize benchmark cases into a list[dict] with keys: name, inputs
            # Supports dict-form (name -> inputs), list-form (dicts), or list-form (names).
            cases = []
            if isinstance(_cases_raw, dict):
                for _name, _inp in _cases_raw.items():
                    if isinstance(_inp, dict):
                        cases.append({"name": str(_name), "inputs": _inp})
            elif isinstance(_cases_raw, list):
                for i, _c in enumerate(_cases_raw):
                    if isinstance(_c, dict):
                        _name = _c.get("name", f"case_{i}")
                        _inp = _c.get("inputs", _c.get("inp", _c.get("input", {})))
                        if isinstance(_inp, dict):
                            cases.append({"name": str(_name), "inputs": _inp})
                    else:
                        cases.append({"name": str(_c), "inputs": {}})
    
            if not cases:
                # Always provide at least one default case so the UI doesn't crash
                cases = [{"name": "default", "inputs": {"R0_m": 1.85, "a_m": 0.6, "kappa": 1.75, "Bt_T": 12.0, "Ip_MA": 8.0, "Ti_keV": 10.0, "fG": 0.85, "t_shield_m": 0.25, "Paux_MW": 25.0}}]
    
            base = PointInputs(R0_m=1.85, a_m=0.6, kappa=1.75, Bt_T=12.0, Ip_MA=8.0, Ti_keV=10.0, fG=0.85, t_shield_m=0.25, Paux_MW=25.0)
            if run_now or regen:
                results = {}
                for _case in cases:
                    name = _case.get("name","case")
                    overrides = _case.get("inputs", {})
                    # Defensive: apply only existing fields
                    d = base.__dict__.copy()
                    for k, v in overrides.items():
                        if k in d:
                            d[k] = v
                    inp_case = PointInputs(**d)
                    # Golden parity: matches tests/test_golden_physics_outputs.py (bypasses Evaluator).
                    from physics.hot_ion import hot_ion_point
                    results[name] = hot_ion_point(inp_case)
    
                if regen:
                    golden_path.write_text(json.dumps(results, indent=2))
                    st.success(f"Wrote golden: {golden_path}")
                else:
                    if not golden_path.exists():
                        st.error("golden.json not found. Click 'Regenerate golden' once to create it.")
                    else:
                        golden = json.loads(golden_path.read_text())
                        CURATED = ["Q_DT_eqv","H98","P_fus_MW","P_SOL_MW","q_div_MW_m2","B_peak_T","sigma_hoop_MPa","hts_margin_cs","J_eng_A_mm2","t_flat_s","P_net_MW"]
                        rows = []
                        failed = 0
                        for name, cur in results.items():
                            ref = golden.get(name, {})
                            for k in CURATED:
                                a = _safe(cur.get(k))
                                b = _safe(ref.get(k))
                                if not (math.isfinite(a) and math.isfinite(b)):
                                    continue
                                atol = 1e-6
                                rtol = 5e-3
                                ok = abs(a-b) <= max(atol, rtol*max(abs(b),1e-9))
                                if not ok:
                                    failed += 1
                                rows.append({"case":name,"key":k,"got":a,"golden":b,"rel_err":(abs(a-b)/max(abs(b),1e-9)),"ok":ok})
                        import pandas as pd

                        df = pd.DataFrame(rows)
                        st.dataframe(df, use_container_width=True)

                        # Write a machine-readable diff report (used by CI and the UI)
                        try:
                            import time as _time
                            report = {
                                "created_unix": _time.time(),
                                "rtol": 5e-3,
                                "atol": 1e-6,
                                "n_rows": int(len(rows)),
                                "n_failed": int(failed),
                                "rows": rows,
                            }
                            (bench_dir / "last_diff_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
                        except Exception:
                            pass

                        if failed==0:
                            st.success("All benchmark comparisons passed (within tolerances).")
                        else:
                            st.warning(f"{failed} comparisons exceeded tolerance. See table.")
    
    
        st.divider()
        with st.expander("Sensitivity and uncertainty (Monte Carlo)", expanded=False):
            st.subheader("Sensitivity (Monte Carlo)")
            st.write("Runs a lightweight uncertainty scan around a selected benchmark case (Windows-native).")
    
            from analysis.sensitivity import monte_carlo_feasibility
            from models.inputs import PointInputs
    
            case_names = [c.get("name", f"case_{i}") for i,c in enumerate(cases)]
            case_sel = st.selectbox("Benchmark case for sensitivity", case_names, index=0, key="sens_case_sel")
            n_mc = st.number_input("Samples", min_value=50, max_value=2000, value=50, step=50, key="sens_n")
            if st.button("Run Monte Carlo", key="run_mc_bench"):
                c = cases[case_names.index(case_sel)]
                base_inp = PointInputs(**c["inputs"])
                res = monte_carlo_feasibility(base_inp, n=int(n_mc), seed=42)
                st.metric("Feasible probability", f"{res['p_feasible']*100:.1f}%")
                st.write("Most frequently violated constraints:")
                st.dataframe(res["worst_constraints"], use_container_width=True)
    
        st.divider()
        with st.expander("Pareto search (design studies)", expanded=False):
            st.subheader("Pareto Search (LHS)")
            st.write("Finds a feasible Pareto set for a small set of design knobs around a benchmark case.")
            from solvers.optimize import pareto_optimize
    
            case_sel2 = st.selectbox("Benchmark case for Pareto", case_names, index=0, key="pareto_case_sel")
            n_lhs = st.number_input("LHS samples", min_value=50, max_value=5000, value=100, step=50, key="pareto_n")
            # simple bounds
            colp1, colp2 = st.columns(2)
            with colp1:
                R0_lo = st.number_input("R0 min [m]", value=1.5, step=0.1, key="R0_lo")
                Ip_lo = st.number_input("Ip min [MA]", value=5.0, step=0.5, key="Ip_lo")
            with colp2:
                R0_hi = st.number_input("R0 max [m]", value=2.5, step=0.1, key="R0_hi")
                Ip_hi = st.number_input("Ip max [MA]", value=12.0, step=0.5, key="Ip_hi")
            fG_lo = st.number_input("fG min", value=0.4, step=0.05, key="fG_lo")
            fG_hi = st.number_input("fG max", value=1.2, step=0.05, key="fG_hi")
    
            if st.button("Run Pareto search", key="run_pareto"):
                c = cases[case_names.index(case_sel2)]
                base_inp = PointInputs(**c["inputs"])
                bounds = {"R0_m": (float(R0_lo), float(R0_hi)), "Ip_MA": (float(Ip_lo), float(Ip_hi)), "fG": (float(fG_lo), float(fG_hi))}
                objectives = {"R0_m": "min", "B_peak_T": "min", "P_e_net_MW": "max"}
                res = pareto_optimize(base_inp, bounds=bounds, objectives=objectives, n_samples=int(n_lhs), seed=1)
                st.write(f"Feasible points: {len(res['feasible'])} | Pareto points: {len(res['pareto'])}")
                st.dataframe(res["pareto"], use_container_width=True)



    # --- Control Room block 3 (was app.py lines 3947..3966) ---
    with tab_registry:
        st.subheader("Variable Registry")
        st.markdown(
            "A external systems codes-style registry of key SHAMS variables with units, meaning, and model provenance. "
            "Use this to keep the code **auditable** as physics/engineering fidelity increases."
        )
        q = st.text_input("Search variables", value="", placeholder="e.g., H98, q_div, HTS, TBR")
        try:
            df = registry_dataframe(q)
            st.dataframe(df, use_container_width=True, height=520)
            st.download_button(
                "Download registry (CSV)",
                data=df.to_csv(index=False),
                file_name="shams_variable_registry.csv",
                mime="text/csv",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Registry unavailable: {e}")



    # --- Control Room block 4 (was app.py lines 3971..4030) ---
    with tab_validation:
        st.subheader("Validation envelopes")
        st.markdown(
            "Decision-grade validation in SHAMS is **envelope-based**: we check whether a solution lies within "
            "a broad reference band for key metrics, rather than trying to match a single reference point. "
            "This is robust to proxy changes and is aligned with external systems codes-style workflows."
        )
        try:
            from validation.envelopes import default_envelopes
            envs = default_envelopes()
            env_name = st.selectbox("Select envelope", list(envs.keys()), index=0, key="validation_env_sel")
            env = envs[env_name]
            st.caption(env.notes)

            out = st.session_state.get("last_point_out")
            if not out:
                st.info("Run a Point Designer solve first. The latest outputs will be checked here.")
            else:
                report = env.check(out)
                import pandas as pd

                rows = []
                n_fail = 0
                for k, r in report.items():
                    if not r.get("ok"):
                        n_fail += 1
                    rows.append({
                        "metric": k,
                        "value": r.get("value"),
                        "lo": r.get("lo"),
                        "hi": r.get("hi"),
                        "ok": bool(r.get("ok")),
                    })
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, height=360)
                if n_fail == 0:
                    st.success("All selected envelope checks passed.")
                else:
                    st.warning(f"{n_fail} envelope checks failed. This indicates the *targets/bounds* are outside the reference band (not a code error).")
        except Exception as e:
            st.error(f"Validation module unavailable: {e}")

        st.divider()
        st.subheader("Invariant guardrails")
        st.caption("Deterministic sign/bookkeeping checks (not experimental validation).")
        try:
            from validation.invariants import check_invariants
            out = st.session_state.get("last_point_out")
            if not out:
                st.info("Run a Point Designer solve first. The latest outputs will be checked here.")
            else:
                rep = check_invariants(out)
                if bool(rep.get("ok")):
                    st.success("All invariant guardrails passed.")
                else:
                    st.error("Invariant guardrail failures detected (likely bookkeeping/sign issue or invalid inputs).")
                    st.json(rep.get("failures", {}))
        except Exception as e:
            st.caption(f"Invariant checks unavailable: {e}")



    # --- Control Room block 5 (was app.py lines 4036..4087) ---
    with tab_compliance:
        st.subheader("Verification & Compliance")
        st.caption("Shows the latest verification/compliance matrix from verification/report.json (if present).")

        def _load_verification_report_ui():
            try:
                here = Path(__file__).resolve()
                root = here.parent.parent  # ui/ -> repo root
                rp = root / "verification"/ "report.json"
                if rp.exists():
                    return json.loads(rp.read_text(encoding="utf-8"))
            except Exception:
                return None
            return None

        report = _load_verification_report_ui()
        if not report:
            st.info("No verification/report.json found. Run: `python verification/run_verification.py` to generate it.")
        else:
            meta = report.get("meta", {})
            st.write({
                "generated_unix": meta.get("generated_unix"),
                "python": meta.get("python"),
                "platform": meta.get("platform"),
                "git_commit": meta.get("git_commit"),
            })

            # Summary
            summary = report.get("summary", {})
            cols = st.columns(4)
            cols[0].metric("Requirements", int(summary.get("n_requirements", 0)))
            cols[1].metric("Passed", int(summary.get("n_pass", 0)))
            cols[2].metric("Failed", int(summary.get("n_fail", 0)))
            cols[3].metric("Overall", "PASS"if summary.get("all_pass") else "FAIL")

            # Detailed table
            rows = report.get("results", [])
            if rows:
                df = pd.DataFrame(rows)
                # Friendly columns ordering
                keep = [c for c in ["req_id","title","status","details","linked_model_cards"] if c in df.columns]
                df = df[keep] if keep else df
                st.dataframe(df, use_container_width=True, height=520)

            # Download JSON
            st.download_button(
                "Download verification report.json",
                data=json.dumps(report, indent=2, sort_keys=True),
                file_name="verification_report.json",
                mime="application/json",
            )



    # --- Control Room block 6 (was app.py lines 4090..4119) ---
    with tab_docs:
        st.header("Docs")
        st.caption("Built-in documentation bundled with this repository (no internet required).")

        doc_options = {
            "Upgrade plan (transparent)": os.path.join(ROOT, "docs", "SHAMS_upgrade_plan_from_PROCESS.md"),
            "Lessons learned (systems codes)": os.path.join(ROOT, "docs", "PROCESS_lessons.md"),
            "0‑D Physical Models (Phase‑1)": os.path.join(ROOT, "docs", "PHYSICAL_MODELS_0D.md"),
            "Engineering closures": os.path.join(ROOT, "docs", "ENGINEERING_CLOSURES.md"),
            "Operating envelope (multi-point)": os.path.join(ROOT, "docs", "ENVELOPE.md"),
            "Studies workflows": os.path.join(ROOT, "docs", "STUDIES.md"),
            "Model cards (auditability)": os.path.join(ROOT, "docs", "MODEL_CARDS.md"),
            "Compliance & verification": os.path.join(ROOT, "docs", "COMPLIANCE.md"),
            "Regression & golden benchmarks": os.path.join(ROOT, "docs", "REGRESSION.md"),
            "Release notes generation": os.path.join(ROOT, "docs", "RELEASE_NOTES.md"),
            "UI quickstart": os.path.join(ROOT, "README_UI.md"),
        }

        doc_sel = st.selectbox("Select a document", list(doc_options.keys()), index=0, key="doc_select")
        doc_path = doc_options.get(doc_sel)

        if doc_path and os.path.exists(doc_path):
            try:
                with open(doc_path, "r", encoding="utf-8") as f:
                    st.markdown(f.read())
            except Exception as _e:
                st.error(f"Failed to read doc: {_e}")
        else:
            st.warning("Document file not found in this checkout.")



    # --- Control Room block 7 (was app.py lines 4175..4261) ---
    with tab_artifacts:
        st.header("Artifacts Explorer")
        st.caption("Load a SHAMS run artifact and inspect new v50+ artifact sections (constraint ledger, model set, standardized tables).")

        up = st.file_uploader("Upload shams_run_artifact.json", type=["json"], key="ae_upload")
        art = _load_json_from_upload(up)

        col_a, col_b = st.columns([1.2, 1.0])
        with col_a:
            alt_path = st.text_input("...or load from local path", value="", key="ae_path")
        with col_b:
            load_btn = st.button("Load from path", key="ae_load_path")

        if load_btn and alt_path:
            try:
                with open(alt_path, "r", encoding="utf-8") as f:
                    art = json.load(f)
            except Exception as e:
                st.error(f"Failed to load JSON: {type(e).__name__}: {e}")
                art = None

        if not art:
            st.info("Upload an artifact JSON (or provide a path) to explore.")
        else:
            meta = art.get("meta", {}) or {}
            prov = art.get("provenance", {}) or {}
            st.subheader("Metadata")
            st.write({
                "schema_version": art.get("schema_version"),
                "label": meta.get("label"),
                "mode": meta.get("mode"),
                "git_commit": prov.get("git_commit"),
                "python": prov.get("python"),
                "platform": prov.get("platform"),
                "repo_version": prov.get("repo_version"),
            })

            # --- Constraint ledger ---
            st.subheader("Constraint Margin Ledger")
            ledger = art.get("constraint_ledger") or {}
            if isinstance(ledger, dict) and ledger.get("entries"):
                st.caption(f"schema={ledger.get('schema_version','(missing)')} fingerprint={ledger.get('ledger_fingerprint_sha256','(missing)')}")
                top = ledger.get("top_blockers") or []
                if top:
                    st.markdown("**Top blockers**")
                    st.dataframe(_safe_df(top), use_container_width=True)
                with st.expander("All ledger entries"):
                    st.dataframe(_safe_df(ledger.get("entries") or []), use_container_width=True)
            else:
                st.info("No constraint_ledger found in this artifact.")

            # --- Model set / registry ---
            st.subheader("Model Set")
            model_set = art.get("model_set") or {}
            model_registry = art.get("model_registry") or {}
            if model_set:
                st.caption(f"schema={model_set.get('schema_version','(missing)')}")
                st.json(model_set)
            else:
                st.info("No model_set embedded in this artifact.")
            with st.expander("Model Registry"):
                if model_registry:
                    st.caption(f"schema={model_registry.get('schema_version','(missing)')}")
                    st.json(model_registry)
                else:
                    st.info("No model_registry embedded in this artifact.")

            # --- Standard tables ---
            st.subheader("Standard Tables")
            tables = art.get("tables") or {}
            if isinstance(tables, dict) and tables:
                for k in ["plasma", "power_balance", "tritium"]:
                    if k in tables:
                        st.markdown(f"**{k}**")
                        t = tables.get(k)
                        if isinstance(t, dict):
                            st.dataframe(pd.DataFrame([t]), use_container_width=True)
                        elif isinstance(t, list):
                            st.dataframe(pd.DataFrame(t), use_container_width=True)
                        else:
                            st.json(t)
            else:
                st.info("No tables.v1 section found in this artifact.")

            with st.expander("Full artifact JSON"):
                st.json(art)



    # --- Control Room block 8 (was app.py lines 4267..4313) ---
    with tab_deck:
        st.header("Case Deck Runner")
        st.caption("Run a case_deck.v1 YAML/JSON deck and view the resolved config + artifact outputs.")

        up_deck = st.file_uploader("Upload case_deck.yaml / .json", type=["yaml", "yml", "json"], key="deck_upload")
        out_root = os.path.join(ROOT, "ui_runs")
        os.makedirs(out_root, exist_ok=True)
        out_name = st.text_input("Output folder name (under ui_runs/)", value=f"deck_{int(time.time())}", key="deck_out_name")
        run_btn = st.button("Run Case Deck", key="deck_run")

        if run_btn:
            if up_deck is None:
                st.error("Please upload a case deck file first.")
            else:
                try:
                    deck_path = os.path.join(out_root, f"_uploaded_{up_deck.name}")
                    with open(deck_path, "wb") as f:
                        f.write(up_deck.getvalue())
                    out_dir = os.path.join(out_root, out_name)
                    os.makedirs(out_dir, exist_ok=True)
                    runner = os.path.join(ROOT, "tools", "run_case_deck.py")
                    proc = subprocess.run(
                        [sys.executable, runner, deck_path, "--out", out_dir],
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    st.code(proc.stdout or "", language="text")
                    if proc.returncode != 0:
                        st.error("Case deck run failed.")
                        st.code(proc.stderr or "", language="text")
                    else:
                        art_path = os.path.join(out_dir, "shams_run_artifact.json")
                        cfg_path = os.path.join(out_dir, "run_config_resolved.json")
                        st.success(f"Wrote outputs to: {out_dir}")
                        if os.path.exists(cfg_path):
                            st.subheader("Resolved config")
                            with open(cfg_path, "r", encoding="utf-8") as f:
                                st.json(json.load(f))
                        if os.path.exists(art_path):
                            st.subheader("Run artifact (preview)")
                            with open(art_path, "r", encoding="utf-8") as f:
                                st.json(json.load(f))
                except Exception as e:
                    st.error(f"{type(e).__name__}: {e}")



    # --- Control Room block 9 (was app.py lines 4319..4375) ---
    with tab_authority_conf:
        st.header("Authority & Confidence")
        st.caption("Trust ledger: authority tiers, maturity tags, and a design-level confidence class. Post-processing only; truth unchanged.")

        colA, colB = st.columns([0.55, 0.45], gap="large")
        with colA:
            st.markdown("### Load artifact")
            up_art = st.file_uploader("shams_run_artifact.json", type=["json"], key="authconf_upload")
            art = _load_json_from_upload(up_art)
            if not art:
                # Fall back to the most recent artifact in session if present.
                art = st.session_state.get("systems_last_solve_artifact") if isinstance(st.session_state.get("systems_last_solve_artifact"), dict) else None
                if not art:
                    art = st.session_state.get("last_point_artifact") if isinstance(st.session_state.get("last_point_artifact"), dict) else None

            if not art:
                st.info("Upload an artifact, or run Point Designer / Systems Mode to populate a last artifact.")
            else:
                ac = art.get("authority_confidence") if isinstance(art, dict) else None
                if not isinstance(ac, dict):
                    st.warning("No authority_confidence found. (Older artifact?)")
                    st.json({"available_keys": sorted(list(art.keys()))[:40]}, expanded=False)
                else:
                    dc = str((ac.get("design") or {}).get("design_confidence_class", "UNKNOWN"))
                    st.markdown(f"**Design confidence class:** `{dc}`")
                    st.caption("Class is a conservative aggregation over implicated subsystems and near-binding hard constraints.")

        with colB:
            st.markdown("### Quick legend")
            st.markdown("- **A**: anchored by authoritative/external contracts (best)")
            st.markdown("- **B**: parametric / semi-authoritative closure")
            st.markdown("- **C**: proxy models or extrapolation-heavy")
            st.markdown("- **D**: speculative / unknown authority")
            st.markdown("- **UNKNOWN**: missing metadata")

        if isinstance(art, dict) and isinstance(art.get("authority_confidence"), dict):
            ac = art["authority_confidence"]
            subs = ac.get("subsystems") or {}
            rows = []
            for k in sorted(list(subs.keys())):
                v = subs.get(k) or {}
                if not isinstance(v, dict):
                    continue
                rows.append({
                    "subsystem": k,
                    "confidence": v.get("confidence_class"),
                    "authority_tier": v.get("authority_tier"),
                    "maturity": v.get("maturity"),
                    "involved": v.get("involved"),
                    "rationale": v.get("rationale"),
                })
            if rows:
                st.subheader("Subsystem trust ledger")
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("No subsystem entries available.")



    # --- Control Room block 10 (was app.py lines 4381..4439) ---
    with tab_decision_conseq:
        st.header("Decision Consequences")
        st.caption(
            "Advisory governance layer: converts margins + authority into a deterministic 'posture' and risk framing. "
            "Post-processing only; truth unchanged."
        )

        colA, colB = st.columns([0.55, 0.45], gap="large")
        with colA:
            st.markdown("### Load artifact")
            up_art = st.file_uploader("shams_run_artifact.json", type=["json"], key="deccon_upload")
            art = _load_json_from_upload(up_art)
            if not art:
                art = st.session_state.get("systems_last_solve_artifact") if isinstance(st.session_state.get("systems_last_solve_artifact"), dict) else None
                if not art:
                    art = st.session_state.get("last_point_artifact") if isinstance(st.session_state.get("last_point_artifact"), dict) else None

            if not art:
                st.info("Upload an artifact, or run Point Designer / Systems Mode to populate a last artifact.")
            else:
                dc = art.get("decision_consequences") if isinstance(art, dict) else None
                if not isinstance(dc, dict):
                    st.warning("No decision_consequences found. (Older artifact?)")
                    st.json({"available_keys": sorted(list(art.keys()))[:40]}, expanded=False)
                else:
                    st.markdown(f"**Decision posture:** `{str(dc.get('decision_posture','UNKNOWN'))}`")
                    pr = str(dc.get("primary_risk_driver", "") or "")
                    if pr:
                        st.markdown(f"**Primary risk driver:** `{pr}`")
                    wh = dc.get("worst_hard_margin_frac", None)
                    try:
                        wh_s = f"{float(wh):.3f}"if wh is not None else "-"
                    except Exception:
                        wh_s = "-"
                    st.markdown(f"**Worst hard margin (frac):** {wh_s}")
                    st.caption(str(dc.get("narrative", "") or ""))

        with colB:
            st.markdown("### Posture legend")
            st.markdown("- **PROCEED**: feasible with adequate authority")
            st.markdown("- **PROCEED_TARGETED_RD**: feasible but near-binding and/or authority-limited")
            st.markdown("- **HOLD_FOUNDATIONAL**: hard-infeasible; address dominant limiter")
            st.markdown("- **UNKNOWN**: missing/legacy artifact")

        if isinstance(art, dict) and isinstance(art.get("decision_consequences"), dict):
            dc = art["decision_consequences"]
            rows = [
                {"field": "decision_posture", "value": dc.get("decision_posture")},
                {"field": "primary_risk_driver", "value": dc.get("primary_risk_driver")},
                {"field": "dominant_mechanism", "value": dc.get("dominant_mechanism")},
                {"field": "dominant_constraint", "value": dc.get("dominant_constraint")},
                {"field": "worst_hard_margin_frac", "value": dc.get("worst_hard_margin_frac")},
                {"field": "uncertainty_reduction_axis", "value": dc.get("uncertainty_reduction_axis")},
                {"field": "leverage_knobs", "value": dc.get("leverage_knobs")},
                {"field": "stamp_sha256", "value": dc.get("stamp_sha256")},
            ]
            st.subheader("Snapshot")
            st.table(rows)



    # --- Control Room block 11 (was app.py lines 4445..4503) ---
    with tab_authority_dominance:
        st.header("Authority Dominance")
        st.caption(
            "Deterministic dominance engine: identifies the dominant feasibility killer authority "
            "(PLASMA/EXHAUST/MAGNET/CONTROL/NEUTRONICS/FUEL/PLANT) and ranks the top limiting constraints. "
            "Post-processing only; truth unchanged."
        )

        colA, colB = st.columns([0.55, 0.45], gap="large")
        with colA:
            st.markdown("### Load artifact")
            up_art = st.file_uploader("shams_run_artifact.json", type=["json"], key="authdom_upload")
            art = _load_json_from_upload(up_art)
            if not art:
                art = st.session_state.get("systems_last_solve_artifact") if isinstance(st.session_state.get("systems_last_solve_artifact"), dict) else None
                if not art:
                    art = st.session_state.get("last_point_artifact") if isinstance(st.session_state.get("last_point_artifact"), dict) else None

            if not art:
                st.info("Upload an artifact, or run Point Designer / Systems Mode to populate a last artifact.")
            else:
                ad = art.get("authority_dominance") if isinstance(art, dict) else None
                if not isinstance(ad, dict):
                    st.warning("No authority_dominance found. (Older artifact?)")
                    st.json({"available_keys": sorted(list(art.keys()))[:60]}, expanded=False)
                else:
                    st.markdown(f"**Dominance verdict:** `{str(ad.get('dominance_verdict','UNKNOWN'))}`")
                    st.markdown(f"**Dominant authority:** `{str(ad.get('dominant_authority',''))}`")
                    st.markdown(f"**Dominant constraint:** `{str(ad.get('dominant_constraint',''))}`")
                    mm = ad.get("dominant_margin_frac", None)
                    try:
                        mm_s = f"{float(mm):.4f}"if mm is not None else "-"
                    except Exception:
                        mm_s = "-"
                    st.markdown(f"**Dominant margin (frac):** {mm_s}")
                    st.caption(f"stamp_sha256: {str(ad.get('stamp_sha256',''))[:16]}…")

        with colB:
            st.markdown("### Interpretation")
            st.markdown("- **INFEASIBLE**: at least one hard constraint violated; dominance points to the worst hard margin.")
            st.markdown("- **FRAGILE**: hard-feasible but the tightest hard margin is near-binding (default < 0.05).")
            st.markdown("- **FEASIBLE**: hard-feasible with comfortable margins.")

        if isinstance(art, dict) and isinstance(art.get("authority_dominance"), dict):
            ad = art["authority_dominance"]
            with st.expander("Top limiting constraints (hard)", expanded=False):
                rows = ad.get("dominance_topk") or []
                if isinstance(rows, list) and rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No top-k rows available.")

            with st.expander("Authority ranking", expanded=False):
                rows = ad.get("authority_ranked") or []
                if isinstance(rows, list) and rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No authority ranking available.")



    # --- Control Room block 12 (was app.py lines 4510..4579) ---
    with tab_epoch_feas:
        st.header("Epoch Feasibility")
        st.caption(
            "Lifecycle-epoch feasibility (Startup / Nominal / End-of-Life). "
            "Constitutional reclassification only; no re-solving and no truth modification."
        )

        colA, colB = st.columns([0.55, 0.45], gap="large")
        with colA:
            st.markdown("### Load artifact")
            up_art = st.file_uploader("shams_run_artifact.json", type=["json"], key="epochfeas_upload")
            art = _load_json_from_upload(up_art)
            if not art:
                art = st.session_state.get("systems_last_solve_artifact") if isinstance(st.session_state.get("systems_last_solve_artifact"), dict) else None
                if not art:
                    art = st.session_state.get("last_point_artifact") if isinstance(st.session_state.get("last_point_artifact"), dict) else None

            if not art:
                st.info("Upload an artifact, or run Systems Mode to populate a last artifact.")
            else:
                ef = art.get("epoch_feasibility") if isinstance(art, dict) else None
                if not isinstance(ef, dict):
                    st.warning("No epoch_feasibility found. (Older artifact?)")
                    st.json({"available_keys": sorted(list(art.keys()))[:40]}, expanded=False)
                else:
                    st.markdown(f"**Overall:** `{str(ef.get('overall','UNKNOWN'))}`")
                    epochs = ef.get("epochs") or []
                    rows = []
                    for e in epochs:
                        if not isinstance(e, dict):
                            continue
                        wh = e.get("worst_hard_margin_frac", None)
                        try:
                            wh_s = f"{float(wh):.3f}"if wh is not None else "-"
                        except Exception:
                            wh_s = "-"
                        rows.append({
                            "epoch": str(e.get("epoch","")),
                            "verdict": str(e.get("verdict","")),
                            "dominant_mechanism": str(e.get("dominant_mechanism","")),
                            "dominant_constraint": str(e.get("dominant_constraint","")),
                            "worst_hard_margin": wh_s,
                            "n_blocking": len(list(e.get("blocking") or [])),
                            "n_diag": len(list(e.get("diagnostic") or [])),
                        })
                    if rows:
                        st.dataframe(rows, use_container_width=True, hide_index=True)
                    else:
                        st.warning("Epoch list empty.")
        with colB:
            st.markdown("### Constitution (selected epoch)")
            if not art or not isinstance(art, dict) or not isinstance(art.get("epoch_feasibility"), dict):
                st.caption("Load an artifact to view epoch constitutions.")
            else:
                ef = art.get("epoch_feasibility") or {}
                epochs = ef.get("epochs") or []
                labels = [str(e.get("epoch","")) for e in epochs if isinstance(e, dict)]
                sel = st.selectbox("Epoch", labels, index=0 if labels else None, key="epochfeas_pick")
                chosen = None
                for e in epochs:
                    if isinstance(e, dict) and str(e.get("epoch","")) == sel:
                        chosen = e
                        break
                if chosen is None:
                    st.info("No epoch selected.")
                else:
                    st.markdown(f"**Epoch:** `{sel}`")
                    st.json(chosen.get("constitution") or {}, expanded=False)
                    st.caption("These clauses reclassify constraint enforcement deterministically across epochs.")



    # --- Control Room block 13 (was app.py lines 4581..4673) ---
    with tab_delta:
        st.header("Scenario Delta Viewer")
        st.caption("Compare two run artifacts (baseline vs scenario). Uses embedded scenario_delta when available; otherwise computes a transparent diff.")

        col1, col2 = st.columns(2)
        with col1:
            up_base = st.file_uploader("Baseline shams_run_artifact.json", type=["json"], key="delta_base")
        with col2:
            up_scen = st.file_uploader("Scenario shams_run_artifact.json", type=["json"], key="delta_scen")

        base = _load_json_from_upload(up_base)
        scen = _load_json_from_upload(up_scen)

        if not base or not scen:
            st.info("Upload both baseline and scenario artifacts to view deltas.")
        else:
            st.subheader("Embedded scenario_delta")
            sd = scen.get("scenario_delta")
            if sd:
                st.json(sd)
            else:
                st.info("No embedded scenario_delta found; computing diffs from inputs/outputs.")

            st.subheader("Changed inputs")
            bi = base.get("inputs") or {}
            si = scen.get("inputs") or {}
            changed = []
            for k in sorted(set(bi.keys()) | set(si.keys())):
                if bi.get(k) != si.get(k):
                    changed.append({"field": k, "baseline": bi.get(k), "scenario": si.get(k)})
            if changed:
                st.dataframe(pd.DataFrame(changed), use_container_width=True)
            else:
                st.info("No input differences detected.")

            st.subheader("Numeric output deltas")
            bo = base.get("outputs") or {}
            so = scen.get("outputs") or {}
            df = _numeric_delta_table(bo, so)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No numeric output differences detected.")



            st.subheader("Structural / schema diff (read-only)")
            st.caption("Reports *structure* changes (constraints added/removed/meta changes, model cards) without numeric tolerances.")

            try:
                from shams_io.structural_diff import structural_diff as _structural_diff
                sd = _structural_diff(new_artifact=scen, old_artifact=base)
            except Exception as e:
                sd = None
                st.error(f"Structural diff failed: {e}")

            if isinstance(sd, dict):
                # Constraints changes
                cchg = (sd.get("constraints") or {})
                added = cchg.get("added") or []
                removed = cchg.get("removed") or []
                changed = cchg.get("changed_meta") or []
                cols = st.columns(3)
                cols[0].metric("constraints added", str(len(added)))
                cols[1].metric("constraints removed", str(len(removed)))
                cols[2].metric("constraints meta changed", str(len(changed)))

                if added:
                    with st.expander("Added constraints", expanded=False):
                        st.write(added)
                if removed:
                    with st.expander("Removed constraints", expanded=False):
                        st.write(removed)
                if changed:
                    with st.expander("Changed constraint metadata", expanded=False):
                        st.dataframe(pd.DataFrame(changed), use_container_width=True, hide_index=True)

                # Model cards changes
                mc = (sd.get("model_cards") or {})
                mc_added = mc.get("added") or []
                mc_removed = mc.get("removed") or []
                mc_changed = mc.get("changed") or []
                cols2 = st.columns(3)
                cols2[0].metric("model cards added", str(len(mc_added)))
                cols2[1].metric("model cards removed", str(len(mc_removed)))
                cols2[2].metric("model cards changed", str(len(mc_changed)))
                if mc_added or mc_removed or mc_changed:
                    with st.expander("Model card diffs", expanded=False):
                        st.json({"added": mc_added, "removed": mc_removed, "changed": mc_changed}, expanded=False)

                with st.expander("Raw structural diff JSON (audit)", expanded=False):
                    st.json(sd, expanded=False)



    # --- Control Room block 14 (was app.py lines 4679..4787) ---
    with tab_library:
        st.header("Run Library")
        st.caption("Browse a workspace directory of SHAMS run/study artifacts (no physics changes; read-only).")

        def _scan_workspace(root: Path):
            runs = []
            studies = []
            if not root.exists():
                return runs, studies

            # Run artifacts
            for p in root.rglob("*.json"):
                if p.name.lower() in {"shams_run_artifact.json"} or p.name.lower().startswith("case_") or p.name.lower().endswith("_artifact.json"):
                    try:
                        art = read_run_artifact(p)
                        k = art.get("kpis", {}) if isinstance(art, dict) else {}
                        prov = art.get("provenance", {}) if isinstance(art, dict) else {}
                        runs.append({
                            "type": "run",
                            "path": str(p),
                            "created_unix": float(art.get("created_unix", prov.get("created_unix", float("nan")))) if isinstance(art, dict) else float("nan"),
                            "hard_ok": bool(k.get("hard_ok", False)),
                            "hard_worst_margin": k.get("hard_worst_margin", None),
                            "Q": k.get("Q_DT_eqv", k.get("Q", None)),
                            "H98": k.get("H98", None),
                            "message": ((art.get("solver") or {}).get("message") if isinstance(art.get("solver"), dict) else ""),
                        })
                    except Exception:
                        continue

            # Study indexes
            for p in root.rglob("index.json"):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and data.get("schema_version") == "study_index.v1":
                        prov = data.get("provenance", {}) if isinstance(data.get("provenance"), dict) else {}
                        studies.append({
                            "type": "study",
                            "path": str(p),
                            "created_unix": float(data.get("created_unix", prov.get("created_unix", float('nan')))),
                            "n_cases": int(data.get("n_cases", 0)),
                            "elapsed_s": float(data.get("elapsed_s", float('nan'))),
                        })
                except Exception:
                    continue
            return runs, studies

        default_ws = str((Path.cwd()/ "ui_runs").resolve())
        ws = st.text_input("Workspace folder", value=st.session_state.get("ui_workspace", default_ws))
        st.session_state.ui_workspace = ws
        root = Path(ws)

        colA, colB = st.columns([1, 1])
        with colA:
            do_scan = st.button("Scan workspace", use_container_width=True)
        with colB:
            st.write("")
            st.write("")

        if do_scan:
            runs, studies = _scan_workspace(root)
            st.session_state._ws_runs = runs
            st.session_state._ws_studies = studies

        runs = st.session_state.get("_ws_runs", [])
        studies = st.session_state.get("_ws_studies", [])

        st.subheader("Runs")
        if not runs:
            st.info("No run artifacts found yet. Tip: point runs write artifacts under your chosen output directory; studies write case_XXXX.json under the study out folder.")
        else:
            df = pd.DataFrame(runs)
            # Sort: newest first when available
            if "created_unix"in df.columns:
                df = df.sort_values("created_unix", ascending=False, na_position="last")
            st.dataframe(df, use_container_width=True, hide_index=True)

            sel = st.text_input("Select a run artifact path to open", value=st.session_state.get("selected_artifact_path", ""))
            if st.button("Open selected run", use_container_width=True):
                p = Path(sel)
                if p.exists():
                    try:
                        art = read_run_artifact(p)
                        st.session_state.selected_artifact = art
                        st.session_state.selected_artifact_path = str(p)
                        st.success("Loaded run artifact into session.")
                    except Exception as e:
                        st.error(f"Failed to read artifact: {e}")
                else:
                    st.error("Path does not exist.")

        st.subheader("Studies")
        if studies:
            st.dataframe(pd.DataFrame(studies).sort_values("created_unix", ascending=False, na_position="last"), use_container_width=True, hide_index=True)
            ssel = st.text_input("Select a study index.json path to open", value=st.session_state.get("selected_study_index_path", ""))
            if st.button("Open selected study", use_container_width=True):
                p = Path(ssel)
                if p.exists():
                    try:
                        st.session_state.selected_study_index_path = str(p)
                        st.session_state.selected_study_index = json.loads(p.read_text(encoding="utf-8"))
                        st.success("Loaded study index into session.")
                    except Exception as e:
                        st.error(f"Failed to read study index: {e}")
                else:
                    st.error("Path does not exist.")
        else:
            st.caption("No study indexes found in this workspace.")



    # --- Control Room block 15 (was app.py lines 4792..4839) ---
    with tab_constraints:
        st.header("Constraint Cockpit")
        st.caption("Interactively triage constraints using the embedded constraint ledger (read-only).")

        art = st.session_state.get("selected_artifact")
        if not isinstance(art, dict):
            st.info("Load a run artifact first (Run Library or Artifacts Explorer).")
        else:
            ledger = art.get("constraint_ledger", {})
            entries = ledger.get("entries", []) if isinstance(ledger, dict) else []
            if not entries:
                st.warning("This artifact has no constraint ledger. (It should be present in v39+ artifacts.)")
            else:
                df = pd.DataFrame(entries)
                # Basic filters
                c1, c2, c3 = st.columns([1,1,1])
                with c1:
                    sev = st.multiselect("Severity", sorted(df.get("severity", pd.Series(["hard"])).dropna().unique().tolist()), default=["hard","soft"] if "soft"in df.get("severity", pd.Series([])).unique() else ["hard"])
                with c2:
                    grp = st.multiselect("Group", sorted(df.get("group", pd.Series(["general"])).dropna().unique().tolist()), default=[])
                with c3:
                    show_only_failed = st.checkbox("Only failed constraints", value=True)

                view = df.copy()
                if sev:
                    view = view[view["severity"].isin(sev)]
                if grp:
                    view = view[view["group"].isin(grp)]
                if show_only_failed and "passed"in view.columns:
                    view = view[view["passed"] == False]

                # Sort: worst first by margin_frac or margin
                if "margin_frac"in view.columns:
                    view = view.sort_values("margin_frac", ascending=True, na_position="last")
                elif "margin"in view.columns:
                    view = view.sort_values("margin", ascending=True, na_position="last")

                st.subheader("Ledger")
                st.dataframe(view, use_container_width=True, hide_index=True)

                st.subheader("Top blockers")
                top = ledger.get("top_blockers", []) if isinstance(ledger, dict) else []
                if top:
                    st.dataframe(pd.DataFrame(top), use_container_width=True, hide_index=True)
                fp = ledger.get("ledger_fingerprint_sha256")
                if fp:
                    st.caption(f"Ledger fingerprint: `{fp}`")



    # --- Control Room block 16 (was app.py lines 4845..4967) ---
    with tab_constraint_inspector:
        st.header("Constraint Inspector")
        st.caption("Read-only, equation-first inspection of a single constraint: raw inequality, margin, meaning, knobs, and provenance (when available).")

        art = st.session_state.get("selected_artifact")
        if not isinstance(art, dict):
            st.info("Load a run artifact first (Run Library or Artifacts Explorer).")
        else:
            constraints_list = art.get("constraints") or []
            # Build a name -> constraint dict map (best-effort)
            name_to_c = {}
            for c in constraints_list:
                if isinstance(c, dict) and c.get("name"):
                    name_to_c[str(c.get("name"))] = c

            ledger = art.get("constraint_ledger", {})
            entries = ledger.get("entries", []) if isinstance(ledger, dict) else []
            names = []
            # Prefer ledger order if present (it should reflect evaluation order)
            if entries:
                for e in entries:
                    n = str(e.get("name"))
                    if n and n not in names:
                        names.append(n)
            else:
                names = sorted(list(name_to_c.keys()))

            if not names:
                st.warning("No constraints found in this artifact.")
            else:
                sel = st.selectbox("Select constraint", names, index=0, key="constraint_inspector_select")

                # Pull both ledger entry (if present) and raw constraint dict (if present)
                entry = None
                if entries:
                    for e in entries:
                        if str(e.get("name")) == sel:
                            entry = e
                            break
                c = name_to_c.get(sel, {}) if isinstance(name_to_c.get(sel, {}), dict) else {}

                # Compose a canonical view (prefer ledger fields where available)
                view = {}
                for src in (c, entry or {}):
                    if isinstance(src, dict):
                        view.update({k: src.get(k) for k in src.keys()})

                # Core inequality (verbatim fields; no inferred math)
                sense = str(view.get("sense") or "")
                value = view.get("value")
                limit = view.get("limit")
                units = str(view.get("units") or "")
                meaning = str(view.get("meaning") or view.get("note") or "")

                st.subheader("Inequality")
                if sense and value is not None and limit is not None:
                    st.code(f"{sel}: value {sense} limit (value={value}, limit={limit}, units={units})", language="text")
                else:
                    st.code(f"{sel}: (insufficient fields to render inequality)", language="text")

                # Pass/fail + margins
                cols = st.columns(4)
                cols[0].metric("passed", str(bool(view.get("passed", False))))
                if view.get("severity") is not None:
                    cols[1].metric("severity", str(view.get("severity")))
                if view.get("group") is not None:
                    cols[2].metric("group", str(view.get("group")))
                if view.get("dominance_rank") is not None:
                    cols[3].metric("dominance_rank", str(view.get("dominance_rank")))

                c1, c2, c3 = st.columns(3)
                if view.get("margin") is not None:
                    c1.metric("margin", f"{view.get('margin')}")
                if view.get("margin_frac") is not None:
                    c2.metric("margin_frac", f"{view.get('margin_frac')}")
                if view.get("violation_score") is not None:
                    c3.metric("violation_score", f"{view.get('violation_score')}")

                st.subheader("Meaning / proxy")
                if meaning.strip():
                    st.write(meaning)
                else:
                    st.info("No meaning/proxy text is attached to this constraint.")

                # Knobs + dominant inputs
                st.subheader("Knobs / dominant inputs (if present)")
                bb = view.get("best_knobs")
                di = view.get("dominant_inputs")
                kcol1, kcol2 = st.columns(2)
                with kcol1:
                    if bb:
                        st.write("**best_knobs**")
                        st.write(bb)
                    else:
                        st.caption("best_knobs: (none)")
                with kcol2:
                    if di:
                        st.write("**dominant_inputs**")
                        st.write(di)
                    else:
                        st.caption("dominant_inputs: (none)")

                # Provenance (constraint-level and artifact-level)
                st.subheader("Provenance (if present)")
                prov = {}
                if isinstance(view.get("provenance"), dict):
                    prov["constraint"] = view.get("provenance")
                if isinstance(art.get("provenance"), dict):
                    prov["artifact"] = art.get("provenance")
                if prov:
                    st.json(prov, expanded=False)
                else:
                    st.info("No provenance keys present on this constraint (artifact-level provenance may still exist under artifact.provenance).")

                # Raw views for auditability
                with st.expander("Raw JSON (audit)", expanded=False):
                    if isinstance(entry, dict):
                        st.write("**constraint_ledger entry**")
                        st.json(entry, expanded=False)
                    if isinstance(c, dict) and c:
                        st.write("**constraints[] item**")
                        st.json(c, expanded=False)



    # --- Control Room block 17 (was app.py lines 4973..5039) ---
    with tab_sensitivity:
        st.header("Sensitivity Explorer")
        st.caption("Local finite-difference sensitivities around the current point (no model changes).")

        art = st.session_state.get("selected_artifact")
        if not isinstance(art, dict):
            st.info("Load a run artifact first (Run Library or Artifacts Explorer).")
        else:
            inp_d = art.get("inputs", {})
            if not isinstance(inp_d, dict):
                st.error("Artifact inputs missing or invalid.")
            else:
                try:
                    base = PointInputs.from_dict(inp_d)
                except Exception:
                    # Fallback: try direct constructor with expected keys
                    try:
                        base = PointInputs(**{k: inp_d[k] for k in PointInputs.__dataclass_fields__.keys() if k in inp_d})
                    except Exception as e:
                        st.error(f"Could not build PointInputs from artifact inputs: {e}")
                        base = None

                if base is not None:
                    st.subheader("Base point")
                    st.json(base.__dict__)

                    # Choose knobs + outputs
                    knob_defaults = ["Ip_MA", "fG", "Bt_T", "R0_m", "a_m", "kappa", "Paux_MW", "Ti_keV", "Te_keV"]
                    available_knobs = [k for k in knob_defaults if k in base.__dict__]
                    knobs = st.multiselect("Knobs", available_knobs, default=["Ip_MA", "fG"], key="sens_knobs_v294")

                    outputs_default = [
                        "Q_DT_eqv", "H98", "P_fus_total_MW", "Palpha_MW", "beta_N", "nbar20", "P_e_net_MW",
                        "B_peak_T", "q95", "TBR",
                    ]
                    outputs = st.multiselect("Outputs", outputs_default, default=["Q_DT_eqv", "H98"], key="sens_outs_v294")

                    step_rel = st.number_input("Step size (relative)", value=1e-3, min_value=1e-6, format="%.6f", key="sens_step_rel_v294")

                    if st.button("Compute deterministic sensitivity pack", use_container_width=True, key="sens_btn_v294"):
                        try:
                            from analysis.sensitivity import deterministic_sensitivity_pack
                            # Characteristic scales for variables when x0 == 0
                            scales = {k: 1.0 for k in knobs}
                            scales.update({"Paux_MW": 10.0, "Ip_MA": 1.0, "fG": 0.1, "Bt_T": 0.5, "R0_m": 0.5, "a_m": 0.2})
                            pack = deterministic_sensitivity_pack(base, variables={k: scales.get(k, 1.0) for k in knobs}, outputs=list(outputs), step_rel=float(step_rel))

                            # Flatten for table
                            rows = []
                            jac = pack.get("jacobian", {}) if isinstance(pack, dict) else {}
                            for o in outputs:
                                for p in knobs:
                                    try:
                                        v = float((jac.get(o) or {}).get(p))
                                    except Exception:
                                        v = float('nan')
                                    rows.append({"output": o, "knob": p, "d(output)/d(knob)": v})
                            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                            st.subheader("Constraint tightness (top residuals)")
                            st.dataframe(pd.DataFrame(pack.get("constraints_tightness", [])), use_container_width=True, hide_index=True)

                            with st.expander("Raw JSON (audit)", expanded=False):
                                st.json(pack)
                        except Exception as e:
                            st.error(f"Sensitivity computation failed: {e}")



    # --- Control Room block 18 (was app.py lines 5044..5131) ---
    with tab_feasmap:
        st.header("Feasibility Map")
        st.caption("Visualize feasibility from study sweeps (heatmap).")

        # Load study index either from session (Run Library) or by path
        p_default = st.session_state.get("selected_study_index_path", "")
        p = st.text_input("Study index.json path", value=p_default)
        idx_data = None
        if p and Path(p).exists():
            try:
                idx_data = json.loads(Path(p).read_text(encoding="utf-8"))
            except Exception as e:
                st.error(f"Could not read study index: {e}")

        if not isinstance(idx_data, dict) or idx_data.get("schema_version") != "study_index.v1":
            st.info("Provide a valid study_out/index.json (schema study_index.v1).")
        else:
            cases = idx_data.get("cases", [])
            study = idx_data.get("study", {})
            sweeps = (study.get("sweeps") if isinstance(study, dict) else None) or []
            # Determine candidate in_ variables for axes
            in_cols = []
            if cases and isinstance(cases, list) and isinstance(cases[0], dict):
                for k in cases[0].keys():
                    if k.startswith("in_"):
                        in_cols.append(k)
            # Prefer sweep variables
            sweep_vars = ["in_"+str(s.get("name")) for s in sweeps if isinstance(s, dict) and s.get("name") is not None]
            axis_candidates = [c for c in sweep_vars if c in in_cols] + [c for c in in_cols if c not in sweep_vars]
            if len(axis_candidates) < 2:
                st.warning("Need at least two swept input variables (in_*) to plot a 2D feasibility map.")
            else:
                c1, c2 = st.columns([1,1])
                with c1:
                    xcol = st.selectbox("X axis", axis_candidates, index=0)
                with c2:
                    ycol = st.selectbox("Y axis", axis_candidates, index=1 if len(axis_candidates)>1 else 0)

                df = pd.DataFrame(cases)
                if "ok"not in df.columns:
                    st.error("Study cases table missing 'ok' field.")
                else:
                    # Build pivot grid
                    xs = sorted(df[xcol].dropna().unique().tolist())
                    ys = sorted(df[ycol].dropna().unique().tolist())
                    import numpy as np
                    grid = np.full((len(ys), len(xs)), np.nan)
                    for _, r in df.iterrows():
                        try:
                            xi = xs.index(r[xcol])
                            yi = ys.index(r[ycol])
                            grid[yi, xi] = 1.0 if bool(r["ok"]) else 0.0
                        except Exception:
                            continue

                    st.subheader("Feasibility heatmap (1=feasible, 0=infeasible)")
                    try:
                        import matplotlib.pyplot as plt  # type: ignore
                        fig, ax = plt.subplots()
                        im = ax.imshow(grid, origin="lower", aspect="auto")
                        ax.set_xticks(range(len(xs)))
                        ax.set_yticks(range(len(ys)))
                        ax.set_xticklabels([str(x) for x in xs], rotation=45, ha="right")
                        ax.set_yticklabels([str(y) for y in ys])
                        ax.set_xlabel(xcol)
                        ax.set_ylabel(ycol)
                        st.pyplot(fig, clear_figure=True)
                    except Exception as e:
                        st.error(f"Plot failed: {e}")

                    st.subheader("Pick a case to open")
                    selx = st.selectbox("X value", xs, index=0)
                    sely = st.selectbox("Y value", ys, index=0)
                    sub = df[(df[xcol]==selx) & (df[ycol]==sely)]
                    if sub.empty:
                        st.info("No case for that cell.")
                    else:
                        st.dataframe(sub[["case","ok","iters","message","path"] + [xcol,ycol]], use_container_width=True, hide_index=True)
                        if st.button("Load this case artifact", use_container_width=True):
                            path = str(sub.iloc[0]["path"])
                            try:
                                art = read_run_artifact(Path(path))
                                st.session_state.selected_artifact = art
                                st.session_state.selected_artifact_path = path
                                st.success("Loaded case artifact into session.")
                            except Exception as e:
                                st.error(f"Could not load case artifact: {e}")



    # --- Control Room block 19 (was app.py lines 5188..5223) ---
    with tab_decision:
        st.header("Decision Front Page Builder")
        st.caption("UI-native reconstruction of the decision-grade front-page summary from a run artifact (no physics changes).")

        art = _get_active_artifact("decision")
        if not art:
            st.info("Load an artifact to build the decision summary.")
        else:
            d = _decision_summary_from_artifact(art)
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                st.metric("Feasibility verdict", "FEASIBLE "if d["feasible"] else ("INFEASIBLE "if d["feasible"] is not None else "UNKNOWN"))
            with c2:
                st.metric("Top KPI: Q", f"{d['kpis'].get('Q_DT_eqv', d['kpis'].get('Q', '-'))}")
            with c3:
                st.metric("Top KPI: Pfus (MW)", f"{d['kpis'].get('P_fus_MW', d['kpis'].get('Pfus_MW', '-'))}")

            st.subheader("Dominant blockers")
            if d["top_blockers"]:
                st.dataframe(_safe_df(d["top_blockers"]), use_container_width=True, hide_index=True)
            else:
                st.write("No blockers found in artifact.")

            with st.expander("Full decision inputs (provenance + schema versions)"):
                prov = art.get("provenance", {}) if isinstance(art.get("provenance"), dict) else {}
                st.json({
                    "schema_version": art.get("schema_version"),
                    "repo_version": prov.get("repo_version"),
                    "git_commit": prov.get("git_commit"),
                    "python": prov.get("python"),
                    "platform": prov.get("platform"),
                    "created_unix": prov.get("created_unix"),
                })

            _download_json_button("Download decision summary JSON", d, "decision_summary.json", "dl_decision_summary")



    # --- Control Room block 20 (was app.py lines 5226..5453) ---
    with tab_nonfeas:
        st.header("Guided Non-Feasibility Mode")
        st.caption("Turn infeasible outcomes into a structured, auditable recovery workflow (UI-only; no physics changes).")

        art = _get_active_artifact("nonfeas")
        if not art:
            st.info("Load an artifact to guide a non-feasibility recovery path.")
        else:
            cons = art.get("constraints", []) if isinstance(art.get("constraints"), list) else []
            kpis = art.get("kpis", {}) if isinstance(art.get("kpis"), dict) else {}

            # Determine hard feasibility
            feasible_hard = None
            if "feasible_hard"in kpis:
                try:
                    feasible_hard = bool(kpis.get("feasible_hard"))
                except Exception:
                    feasible_hard = None
            if feasible_hard is None and cons:
                try:
                    feasible_hard = all(
                        bool(c.get("passed", True))
                        for c in cons
                        if str(c.get("severity", "hard")).lower() == "hard"
                    )
                except Exception:
                    feasible_hard = None

            if feasible_hard is True:
                st.success("This run is hard-feasible. Guided non-feasibility mode is not needed.")
            else:
                # Get or construct a non-feasibility certificate
                cert = art.get("nonfeasibility_certificate") if isinstance(art.get("nonfeasibility_certificate"), dict) else None
                if not cert:
                    hard_failed = [
                        c for c in cons
                        if str(c.get("severity", "hard")).lower() == "hard"and not bool(c.get("passed", True))
                    ]

                    def _mkey(c):
                        try:
                            return float(c.get("margin", 0.0))
                        except Exception:
                            return 0.0

                    hard_failed.sort(key=_mkey)
                    cert = {
                        "hard_feasible": False,
                        "dominant_blockers": [{
                            "name": c.get("name", ""),
                            "group": c.get("group", ""),
                            "value": c.get("value"),
                            "limit": c.get("limit"),
                            "sense": c.get("sense"),
                            "margin": c.get("margin"),
                            "meaning": c.get("meaning", ""),
                            "best_knobs": c.get("best_knobs", []),
                            "maturity": c.get("maturity"),
                            "provenance": c.get("provenance"),
                        } for c in hard_failed[:10]],
                        "recommendation": "Move the listed best_knobs (and/or relax assumptions) until all hard constraints pass.",
                    }

                st.subheader("Non-Feasibility Certificate")
                st.json(cert)

                t1, t2, t3 = st.tabs(["1) Diagnose", "2) Minimal relaxations", "3) Create a scenario (deck)"])

                with t1:
                    st.markdown("### Dominant hard blockers (ranked)")
                    blockers = cert.get("dominant_blockers", []) if isinstance(cert.get("dominant_blockers"), list) else []
                    if blockers:
                        bdf = _safe_df(blockers)
                        pref = [c for c in ["group", "name", "margin", "value", "limit", "sense", "meaning", "best_knobs", "maturity"] if c in bdf.columns]
                        st.dataframe(bdf[pref] if pref else bdf, use_container_width=True, hide_index=True)
                    else:
                        st.warning("No dominant blockers found in certificate.")

                    # Solver hints (if present)
                    out = art.get("outputs", {}) if isinstance(art.get("outputs"), dict) else {}
                    solver = out.get("_solver") if isinstance(out.get("_solver"), dict) else art.get("solver")
                    if isinstance(solver, dict) and solver:
                        st.markdown("### Solver hints (from artifact)")
                        show = {k: solver.get(k) for k in ["status", "reason", "clamped", "clamped_on", "residuals", "ui_log"] if k in solver}
                        st.json(show or solver)

                    st.markdown("### Action principle")
                    st.write(
                        "Fix **hard** blockers first. Soft constraints are advisory unless your decision policy says otherwise. "
                        "Use the knob suggestions as **directional guidance** (not optimization)."
                    )

                with t2:
                    st.markdown("### Propose a nearest-feasible adjustment (within UI)")
                    base = _guess_point_inputs_from_artifact(art)
                    if base is None:
                        base = st.session_state.get("last_point_inp")

                    if base is None:
                        st.warning("Could not infer PointInputs from artifact. Run Point Designer once or ensure artifact includes inputs.")
                    else:
                        st.caption("Choose a dominant blocker, then adjust one or more knobs and re-evaluate.")
                        blockers = cert.get("dominant_blockers", []) if isinstance(cert.get("dominant_blockers"), list) else []
                        if blockers:
                            labels = []
                            for i, b in enumerate(blockers):
                                nm = b.get("name", "") or f"blocker_{i}"
                                mg = b.get("margin")
                                labels.append(f"{i:02d} - {nm} (margin={mg})")
                            bi = st.selectbox("Select blocker", options=list(range(len(blockers))), format_func=lambda i: labels[i], key="nf_blocker_sel")
                            b = blockers[int(bi)]
                            st.markdown("**Suggested knobs (directional):**")
                            st.write(b.get("best_knobs", []) or ["(none provided)"])
                            st.markdown("**Meaning:**")
                            st.write(b.get("meaning", "(no meaning field)"))

                        knob_fields = ["Ip_MA", "fG", "Bt_T", "R0_m", "a_m", "kappa", "Ti_keV", "Paux_MW", "Ti_over_Te"]
                        colA, colB = st.columns([2, 1])
                        with colA:
                            sel_knobs = st.multiselect("Knobs to adjust", options=knob_fields, default=["Ip_MA"], key="nf_knobs")
                        with colB:
                            mode = st.selectbox("Adjustment mode", options=["percent", "absolute"], index=0, key="nf_adj_mode")

                        deltas = {}
                        for k in sel_knobs:
                            v0 = float(getattr(base, k))
                            if mode == "percent":
                                d = st.slider(f"{k} Δ (%)", -50.0, 50.0, 5.0, step=0.5, key=f"nf_d_{k}")
                                deltas[k] = v0 * (1.0 + d / 100.0)
                            else:
                                step = 0.1 if abs < 10 else 1.0
                                d = st.number_input(f"{k} new value", value=v0, step=step, key=f"nf_abs_{k}")
                                deltas[k] = float(d)

                        fuel_mode = st.selectbox("fuel_mode", options=["DT", "DD"], index=0 if getattr(base, "fuel_mode", "DT") == "DT"else 1, key="nf_fuel_mode")

                        run = st.button("Re-evaluate adjusted point", key="nf_run_eval", use_container_width=True)
                        if run:
                            try:
                                d = base.__dict__.copy()
                                d.update({k: float(v) for k, v in deltas.items()})
                                d["fuel_mode"] = str(fuel_mode)
                                pi = PointInputs(**d)

                                out2 = _ui_evaluate(
                                    pi,
                                    origin="run_artifact",
                                    Paux_for_Q_MW=float(getattr(pi, "Paux_MW", 0.0)),
                                )
                                cons2 = evaluate_constraints(out2)
                                art2 = build_run_artifact(
                                    inputs=dict(pi.__dict__),
                                    outputs=dict(out2),
                                    constraints=cons2,
                                    meta={"mode": "guided_nonfeas"},
                                    baseline_inputs=dict(base.__dict__),
                                )
                                st.session_state["nf_last_artifact"] = art2
                                k2 = art2.get("kpis", {}) if isinstance(art2.get("kpis"), dict) else {}
                                st.success(f"Re-evaluated. feasible_hard={k2.get('feasible_hard')}")

                                led = art2.get("constraint_ledger", {}) if isinstance(art2.get("constraint_ledger"), dict) else {}
                                tb = led.get("top_blockers") if isinstance(led.get("top_blockers"), list) else []
                                if tb:
                                    st.subheader("New top blockers")
                                    st.dataframe(_safe_df(tb), use_container_width=True, hide_index=True)

                                with st.expander("New run artifact (raw)"):
                                    st.json(art2)

                                _download_json_button("Download adjusted run artifact", art2, "shams_run_artifact_adjusted.json", "dl_nf_adjusted_artifact")
                            except Exception as e:
                                st.error(f"Re-evaluation failed: {type(e).__name__}: {e}")

                with t3:
                    st.markdown("### Create a scenario deck for reproducible follow-up")
                    base = _guess_point_inputs_from_artifact(art) or st.session_state.get("last_point_inp")
                    last = st.session_state.get("nf_last_artifact")
                    if not isinstance(last, dict):
                        st.info("First run an adjustment in 'Minimal relaxations' to generate a proposed follow-up scenario.")
                    else:
                        try:
                            import yaml  # type: ignore
                        except Exception:
                            yaml = None  # type: ignore

                        new_inputs = last.get("inputs") if isinstance(last.get("inputs"), dict) else {}
                        base_inputs = dict(base.__dict__) if base is not None else (art.get("inputs") if isinstance(art.get("inputs"), dict) else {})

                        delta = {}
                        for k, v in new_inputs.items():
                            if k in base_inputs and base_inputs.get(k) != v:
                                delta[k] = {"from": base_inputs.get(k), "to": v}

                        st.subheader("Scenario delta (inputs)")
                        st.json(delta if delta else {"note": "No input delta detected."})

                        case_deck = {
                            "schema_version": "case_deck.v1",
                            "name": "guided_nonfeas_followup",
                            "base": {},
                            "point": new_inputs,
                            "notes": {
                                "generated_by": "Guided Non-Feasibility Mode",
                                "source_artifact_schema": art.get("schema_version"),
                            },
                        }

                        deck_txt = yaml.safe_dump(case_deck, sort_keys=False) if yaml is not None else json.dumps(case_deck, indent=2)

                        st.markdown("### Case deck")
                        st.code(deck_txt, language="yaml"if yaml is not None else "json")

                        st.download_button(
                            "Download case_deck.yaml",
                            data=deck_txt.encode("utf-8"),
                            file_name="case_deck.yaml",
                            mime="text/yaml"if yaml is not None else "application/json",
                            use_container_width=True,
                        )
                        st.download_button(
                            "Download scenario_delta.json",
                            data=json.dumps(delta, indent=2).encode("utf-8"),
                            file_name="scenario_delta.json",
                            mime="application/json",
                            use_container_width=True,
                        )



    # --- Control Room block 21 (was app.py lines 5456..5483) ---
    with tab_cprov:
        st.header("Constraint Provenance Drill-Down")
        st.caption("Click into constraints to see definition fields, fingerprints, and maturity/provenance metadata embedded in the artifact.")

        art = _get_active_artifact("cprov")
        if not art:
            st.info("Load an artifact to inspect constraint provenance.")
        else:
            cons = art.get("constraints", [])
            if not isinstance(cons, list) or not cons:
                st.warning("No 'constraints' list found in artifact.")
            else:
                df = _safe_df(cons)
                pref_cols = [c for c in ["group","name","failed","soft_failed","severity","value","limit","margin","margin_frac","units","fingerprint","provenance_fingerprint","maturity"] if c in df.columns]
                st.dataframe(df[pref_cols] if pref_cols else df, use_container_width=True, hide_index=True)

                names = []
                for i,c in enumerate(cons):
                    n = c.get("name") or c.get("id") or f"constraint_{i}"
                    names.append(f"{i:03d} - {n}")
                sel = st.selectbox("Select constraint", options=list(range(len(cons))), format_func=lambda i: names[i], key="cprov_sel")
                c = cons[int(sel)]
                st.subheader("Selected constraint (raw)")
                st.json(c)
                if isinstance(c, dict):
                    st.markdown("**Fingerprint fields**")
                    st.code("\n".join([f"{k}: {c.get(k)}"for k in ["fingerprint","provenance_fingerprint","constraint_fingerprint_sha256"] if k in c] or ["(none found)"]))



    # --- Control Room block 22 (was app.py lines 5485..5573) ---
    with tab_knobs:
        st.header("Knob Trade-Space Explorer")
        st.caption("Explore a 2-knob trade-space by evaluating a small grid around the active point (no optimization; feasibility-first).")

        art = _get_active_artifact("knobs")
        base = _guess_point_inputs_from_artifact(art) if art else None
        if base is None:
            base = st.session_state.get("last_point_inp")

        if base is None:
            st.info("Load an artifact (or run Point Designer) to initialize a base point.")
        else:
            st.markdown("**Base point (editable)**")
            col1, col2, col3 = st.columns(3)
            with col1:
                R0_m = st.number_input("R0 (m)", value=float(base.R0_m), step=0.01, key="knob_R0")
                a_m = st.number_input("a (m)", value=float(base.a_m), step=0.01, key="knob_a")
                kappa = st.number_input("kappa", value=float(base.kappa), step=0.05, key="knob_kappa")
            with col2:
                Bt_T = st.number_input("Bt (T)", value=float(base.Bt_T), step=0.1, key="knob_Bt")
                Ip_MA = st.number_input("Ip (MA)", value=float(base.Ip_MA), step=0.1, key="knob_Ip")
                fG = st.number_input("fG", value=float(base.fG), step=0.01, key="knob_fG")
            with col3:
                Ti_keV = st.number_input("Ti (keV)", value=float(base.Ti_keV), step=0.5, key="knob_Ti")
                Paux_MW = st.number_input("Paux (MW)", value=float(base.Paux_MW), step=1.0, key="knob_Paux")
                Ti_over_Te = st.number_input("Ti/Te", value=float(getattr(base, "Ti_over_Te", 2.0)), step=0.1, key="knob_TiTe")

            fuel_mode = st.selectbox("fuel_mode", options=["DT","DD"], index=0 if getattr(base, "fuel_mode", "DT")=="DT"else 1, key="knob_fuel")

            knobs = ["Ip_MA","fG","Bt_T","R0_m","Paux_MW","Ti_keV"]
            kx = st.selectbox("Knob X", knobs, index=0, key="knob_kx")
            ky = st.selectbox("Knob Y", knobs, index=1, key="knob_ky")

            def _getv(pi: PointInputs, k: str) -> float:
                return float(getattr(pi, k))
            def _setv(pi: PointInputs, k: str, v: float) -> PointInputs:
                d = pi.__dict__.copy()
                d[k]=float(v)
                return PointInputs(**d)

            x0=_getv(base,kx); y0=_getv(base,ky)
            colA,colB=st.columns(2)
            with colA:
                x_span = st.number_input("X span (+/-)", value=0.1*abs(x0) if abs(x0)>0 else 0.1, step=0.01, key="knob_xspan")
            with colB:
                y_span = st.number_input("Y span (+/-)", value=0.1*abs(y0) if abs(y0)>0 else 0.1, step=0.01, key="knob_yspan")
            nx = st.slider("X grid points", 3, 15, 9, key="knob_nx")
            ny = st.slider("Y grid points", 3, 15, 9, key="knob_ny")
            run = st.button("Evaluate grid", key="knob_run", use_container_width=True)

        if run:
                import numpy as np
                xs = np.linspace(x0-x_span, x0+x_span, int(nx))
                ys = np.linspace(y0-y_span, y0+y_span, int(ny))
                rows=[]
                with st.spinner("Evaluating grid..."):
                    for xv in xs:
                        for yv in ys:
                            pi = PointInputs(R0_m=float(R0_m), a_m=float(a_m), kappa=float(kappa),
                                             Bt_T=float(Bt_T), Ip_MA=float(Ip_MA), Ti_keV=float(Ti_keV),
                                             fG=float(fG), Paux_MW=float(Paux_MW), Ti_over_Te=float(Ti_over_Te),
                                             fuel_mode=str(fuel_mode))
                            pi = _setv(pi, kx, float(xv))
                            pi = _setv(pi, ky, float(yv))
                            try:
                                out = _ui_evaluate(pi, origin="scan_grid")
                                cons = evaluate_constraints(out, point_inputs=pi)
                                ok = all((not bool(c.get("failed"))) for c in cons)
                                top=None
                                if not ok:
                                    failed=[c for c in cons if c.get("failed")]
                                    if failed:
                                        top=failed[0].get("name")
                                rows.append({kx: float(xv), ky: float(yv), "feasible": bool(ok), "top_blocker": top,
                                             "Q": float(out.get("Q_DT_eqv", out.get("Q", float('nan')))),
                                             "Pfus_MW": float(out.get("P_fus_MW", out.get("Pfus_MW", float('nan'))))})
                            except Exception:
                                rows.append({kx: float(xv), ky: float(yv), "feasible": False, "top_blocker": "eval_error", "Q": float('nan'), "Pfus_MW": float('nan')})
                df=pd.DataFrame(rows, columns=["name","failed_A","failed_B","margin_A","margin_B","margin_delta"])
                st.subheader("Grid results (table)")
                st.dataframe(df, use_container_width=True, hide_index=True)

                try:
                    piv = df.pivot(index=ky, columns=kx, values="feasible")
                    st.subheader("Feasibility heatmap (True=1 / False=0)")
                    st.dataframe(piv.astype(int), use_container_width=True)
                except Exception as e:
                    st.warning(f"Could not pivot heatmap: {e}")



    # --- Control Room block 23 (was app.py lines 5575..5631) ---
    with tab_regress:
        st.header("What broke? Regression Viewer")
        st.caption("Compare two artifacts: constraints, ledgers, model sets, and key KPIs. This is UI-only; it doesn't modify artifacts.")

        c1, c2 = st.columns(2)
        with c1:
            upA = st.file_uploader("Artifact A (json)", type=["json"], key="regA")
            artA = _load_json_from_upload(upA)
        with c2:
            upB = st.file_uploader("Artifact B (json)", type=["json"], key="regB")
            artB = _load_json_from_upload(upB)

        if artA and artB:
            def _kpi_df(art):
                k = art.get("kpis", {}) if isinstance(art.get("kpis"), dict) else {}
                df = pd.DataFrame([{"kpi": kk, "value": vv} for kk,vv in k.items()])
                if df.empty:
                    return pd.DataFrame(columns=["kpi","value"])
                return df.sort_values("kpi")
            st.subheader("KPI diff")
            dfA=_kpi_df(artA).set_index("kpi")
            dfB=_kpi_df(artB).set_index("kpi")
            join=dfA.join(dfB, lsuffix="_A", rsuffix="_B", how="outer")
            join["delta"]=pd.to_numeric(join["value_B"], errors="coerce")-pd.to_numeric(join["value_A"], errors="coerce")
            st.dataframe(join.reset_index().sort_values("kpi"), use_container_width=True, hide_index=True)

            st.subheader("New / worsened constraint failures")
            consA=artA.get("constraints", []) if isinstance(artA.get("constraints"), list) else []
            consB=artB.get("constraints", []) if isinstance(artB.get("constraints"), list) else []
            def _map(cons):
                m={}
                for c in cons:
                    name=c.get("name") or c.get("id")
                    if name:
                        m[name]=c
                return m
            mA=_map(consA); mB=_map(consB)
            names=sorted(set(mA.keys())|set(mB.keys()))
            rows=[]
            for n in names:
                a=mA.get(n,{}); b=mB.get(n,{})
                fa=bool(a.get("failed")); fb=bool(b.get("failed"))
                ma=a.get("margin"); mb=b.get("margin")
                rows.append({"name": n, "failed_A": fa, "failed_B": fb, "margin_A": ma, "margin_B": mb,
                             "margin_delta": (mb-ma) if isinstance(ma,(int,float)) and isinstance(mb,(int,float)) else None})
            df=pd.DataFrame(rows, columns=["name","failed_A","failed_B","margin_A","margin_B","margin_delta"])
            df_bad=df[(df["failed_B"]==True) & ((df["failed_A"]==False) | (df["failed_A"].isna()))]
            st.markdown("**New failures in B**")
            st.dataframe(df_bad.sort_values("name"), use_container_width=True, hide_index=True)
            st.markdown("**Largest margin regressions (B-A)**")
            df_reg=df.dropna(subset=["margin_delta"]).sort_values("margin_delta").head(20)
            st.dataframe(df_reg, use_container_width=True, hide_index=True)

            st.subheader("Model set comparison")
            msA=artA.get("model_set"); msB=artB.get("model_set")
            st.json({"model_set_A": msA, "model_set_B": msB})



    # --- Control Room block 24 (was app.py lines 5633..5668) ---
    with tab_study_dash:
        st.header("Study Dashboard")
        st.caption("Manager-grade summary for study outputs (feasible fraction, dominant blockers, robustness).")

        up = st.file_uploader("Upload study index.json (study_index.v1)", type=["json"], key="sd_up")
        idx_data = _load_json_from_upload(up)
        if not idx_data:
            idx_path = st.session_state.get("selected_study_path")
            if idx_path and Path(idx_path).exists():
                try:
                    idx_data = json.loads(Path(idx_path).read_text(encoding="utf-8"))
                    st.info("Loaded study index from session.")
                except Exception:
                    idx_data = None

        if idx_data:
            st.subheader("Study headline")
            st.json({k: idx_data.get(k) for k in ["schema_version","n_cases","elapsed_s","created_unix"] if k in idx_data})
            cases = idx_data.get("cases", [])
            if isinstance(cases, list) and cases:
                df = pd.DataFrame(cases)
                if "ok"in df.columns:
                    ok_frac = float(df["ok"].mean())
                    st.metric("Feasible fraction", f"{ok_frac:.3f}")
                for col in ["dominant_blocker","top_blocker","blocker"]:
                    if col in df.columns:
                        st.subheader("Dominant blocker distribution")
                        hist = df[col].fillna("(none)").value_counts().reset_index()
                        hist.columns=[col,"count"]
                        st.dataframe(hist, use_container_width=True, hide_index=True)
                        break
                st.subheader("Cases table")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No 'cases' list found in study index. (Older study output?)")



    # --- Control Room block 25 (was app.py lines 5670..5709) ---
    with tab_maturity:
        st.header("Engineering Maturity Heatmap")
        st.caption("Visualize model maturity / validity info embedded in the artifact (model_set + model_registry).")

        art = _get_active_artifact("maturity")
        if not art:
            st.info("Load an artifact to view maturity info.")
        else:
            reg = art.get("model_registry", {})
            ms = art.get("model_set", {})
            rows=[]
            if isinstance(reg, dict):
                entries = reg.get("entries") if isinstance(reg.get("entries"), list) else None
                if entries is None:
                    if all(isinstance(v, dict) for v in reg.values()):
                        entries=[{"model_id": k, **v} for k,v in reg.items()]
                if entries:
                    selected = set()
                    if isinstance(ms, dict):
                        sel = ms.get("selected")
                        if isinstance(sel, dict):
                            selected = set(sel.values()) | set(sel.keys())
                        elif isinstance(sel, list):
                            selected = set(sel)
                    for e in entries:
                        mid = e.get("model_id", e.get("id", ""))
                        rows.append({
                            "subsystem": e.get("subsystem", e.get("domain", "")),
                            "model_id": mid,
                            "maturity": e.get("maturity", e.get("maturity_tag", "")),
                            "validity": e.get("validity", e.get("validity_range", "")),
                            "selected": (mid in selected)
                        })
            if rows:
                df=pd.DataFrame(rows, columns=["name","failed_A","failed_B","margin_A","margin_B","margin_delta"])
                st.dataframe(df.sort_values(["subsystem","model_id"]), use_container_width=True, hide_index=True)
                st.markdown("Tip: treat this as a policy gate (e.g., block decisions if maturity < required).")
            else:
                st.info("No model_registry entries found in artifact.")



    # --- Control Room block 26 (was app.py lines 5712..5769) ---
    with tab_maintenance:
        st.header("Maintenance & Availability Authority")
        st.caption("Deterministic maintenance scheduling closure (v368.0): outage calendar proxy and schedule-dominated availability.")

        out = st.session_state.get("last_point_out")
        if not isinstance(out, dict):
            st.info("Run a point in Point Designer first (sets last_point_out).")
        else:
            enabled = bool(out.get("maintenance_contract_sha256")) and (out.get("availability_v368") == out.get("availability_v368"))
            if not enabled:
                st.warning("v368 maintenance scheduling is not enabled for the current point. Enable it in Point Designer → Engineering & plant feasibility → Maintenance scheduling authority (v368.0).")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Availability (v368)", _m("availability_v368", "{:.3f}"))
            c2.metric("Outage total (v368)", _m("outage_total_frac_v368", "{:.3f}"))
            c3.metric("Net MWh/y (v368)", _m("net_electric_MWh_per_year_v368", "{:.3g}"))
            c4.metric("Repl. cost (MUSD/y)", _m("replacement_cost_MUSD_per_year_v368", "{:.3g}"))

            with st.expander("What this authority does", expanded=False):
                st.markdown(
                    "- Converts replacement cadences (FW/blanket from v367, plus HCD and tritium plant) and replacement durations into a bundled outage fraction.\n"
                    "- Combines with planned/forced baselines (and optional trips proxy) to form total outage and availability.\n"
                    "- Emits an explicit event table (maintenance_events_v368) for audit and reviewer use."
                )
            with st.expander("What this authority does not do", expanded=False):
                st.markdown(
                    "- Does not run a time-domain availability/RAMI simulation.\n"
                    "- Does not optimize schedules or negotiate constraints.\n"
                    "- Does not modify plasma truth or materials lifetime truth; it only post-processes into a schedule proxy."
                )

            st.subheader("Outage decomposition")
            rows = [
                {"term": "planned", "outage_frac": out.get("planned_outage_frac_v368")},
                {"term": "forced", "outage_frac": out.get("forced_outage_frac_v368")},
                {"term": "replacement", "outage_frac": out.get("replacement_outage_frac_v368")},
                {"term": "total", "outage_frac": out.get("outage_total_frac_v368")},
            ]
            try:
                import pandas as _pd
                df = _pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True)
            except Exception:
                st.write(rows)

            ev = out.get("maintenance_events_v368")
            with st.expander("Maintenance event table (v368)", expanded=False):
                if isinstance(ev, list) and ev:
                    try:
                        import pandas as _pd
                        st.dataframe(_pd.DataFrame(ev), use_container_width=True, hide_index=True)
                    except Exception:
                        st.json(ev)
                else:
                    st.info("No maintenance_events_v368 found (enable v368 and re-run).")

            with st.expander("Contract fingerprint", expanded=False):
                st.code(str(out.get("maintenance_contract_sha256", "")))



    # --- Control Room block 27 (was app.py lines 5772..5811) ---
    with tab_profile_auth:
        st.header("Profile Authority")
        st.caption("1.5D algebraic profile diagnostics (non-iterative, conservative).")
        out = st.session_state.get("last_point_out")
        if not isinstance(out, dict):
            st.info("Run a point in Point Designer first (sets last_point_out).")
        else:
            rows=[
                {"metric":"p_peaking", "value": out.get("profile_p_peaking")},
                {"metric":"j_peaking", "value": out.get("profile_j_peaking")},
                {"metric":"li_proxy", "value": out.get("profile_li_proxy")},
                {"metric":"qmin_proxy", "value": out.get("profile_qmin_proxy")},
                {"metric":"f_bootstrap_proxy", "value": out.get("profile_f_bootstrap_proxy")},
                {"metric":"tag", "value": out.get("profile_assumption_tag")},
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)

            st.markdown("### v399 Multi-species impurity mix (if enabled)")
            rows_v399 = [
                {"metric":"include_impurity_v399", "value": out.get("include_impurity_v399")},
                {"metric":"impurity_v399_mix_json", "value": out.get("impurity_v399_mix_json")},
                {"metric":"impurity_v399_prad_total_MW", "value": out.get("impurity_v399_prad_total_MW")},
                {"metric":"impurity_v399_prad_core_MW", "value": out.get("impurity_v399_prad_core_MW")},
                {"metric":"impurity_v399_prad_edge_MW", "value": out.get("impurity_v399_prad_edge_MW")},
                {"metric":"impurity_v399_prad_sol_MW", "value": out.get("impurity_v399_prad_sol_MW")},
                {"metric":"impurity_v399_prad_div_MW", "value": out.get("impurity_v399_prad_div_MW")},
                {"metric":"impurity_v399_zeff", "value": out.get("impurity_v399_zeff")},
                {"metric":"impurity_v399_fuel_ion_fraction", "value": out.get("impurity_v399_fuel_ion_fraction")},
                {"metric":"detachment_prad_sol_div_achieved_MW_v399", "value": out.get("detachment_prad_sol_div_achieved_MW_v399")},
                {"metric":"detachment_margin_v399", "value": out.get("detachment_margin_v399")},
            ]
            st.dataframe(rows_v399, use_container_width=True, hide_index=True)
            with st.expander("v399 Per-species radiation (MW)", expanded=False):
                st.json(out.get("impurity_v399_by_species_MW", {}))
            with st.expander("v399 Validity flags", expanded=False):
                st.json(out.get("impurity_v399_validity", {}))

            with st.expander("Validity flags", expanded=False):
                st.json(out.get("profile_validity", {}))



    # --- Control Room block 28 (was app.py lines 5813..5837) ---
    with tab_impurity:
        st.header("Impurity & Radiation")
        st.caption("v320 authority: single-species partitions + detachment inversion. v399: multi-species mix → Zeff + partitions + achieved detachment margin (diagnostic; no truth feedback).")
        out = st.session_state.get("last_point_out")
        if not isinstance(out, dict):
            st.info("Run a point in Point Designer first.")
        else:
            rows=[
                {"metric":"impurity_contract_species", "value": out.get("impurity_contract_species")},
                {"metric":"impurity_contract_f_z", "value": out.get("impurity_contract_f_z")},
                {"metric":"impurity_prad_total_MW", "value": out.get("impurity_prad_total_MW")},
                {"metric":"impurity_prad_core_MW", "value": out.get("impurity_prad_core_MW")},
                {"metric":"impurity_prad_edge_MW", "value": out.get("impurity_prad_edge_MW")},
                {"metric":"impurity_prad_sol_MW", "value": out.get("impurity_prad_sol_MW")},
                {"metric":"impurity_prad_div_MW", "value": out.get("impurity_prad_div_MW")},
                {"metric":"impurity_zeff_proxy", "value": out.get("impurity_zeff_proxy")},
                {"metric":"impurity_fuel_ion_fraction", "value": out.get("impurity_fuel_ion_fraction")},
                {"metric":"detachment_f_sol_div_required", "value": out.get("detachment_f_sol_div_required")},
                {"metric":"detachment_prad_sol_div_required_MW", "value": out.get("detachment_prad_sol_div_required_MW")},
                {"metric":"detachment_f_z_required", "value": out.get("detachment_f_z_required")},
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)
            with st.expander("Validity flags", expanded=False):
                st.json(out.get("impurity_validity", {}))



    # --- Control Room block 29 (was app.py lines 5839..5856) ---
    with tab_disruption:
        st.header("Disruption Risk")
        st.caption("Conservative screening tier: LOW/MED/HIGH (diagnostic; not predictive).")
        out = st.session_state.get("last_point_out")
        if not isinstance(out, dict):
            st.info("Run a point in Point Designer first.")
        else:
            st.metric("Tier", str(out.get("disruption_risk_tier", "UNKNOWN")))
            cols=st.columns(3)
            with cols[0]:
                st.metric("Risk index", f"{float(out.get('disruption_risk_index', float('nan'))):.3f}"if out.get('disruption_risk_index')==out.get('disruption_risk_index') else "nan")
            with cols[1]:
                st.metric("Dominant driver", str(out.get("disruption_dominant_driver", "unknown")))
            with cols[2]:
                st.metric("fG", f"{float(getattr(st.session_state.get('last_point_inp', None),'fG', float('nan'))):.3f}"if st.session_state.get('last_point_inp') is not None else "nan")
            with st.expander("Components", expanded=False):
                st.json(out.get("disruption_risk_components", {}))



    # --- Control Room block 30 (was app.py lines 5858..5897) ---
    with tab_stability:
        st.header("Stability Risk")
        st.caption("Conservative screening tier: LOW/MED/HIGH for vertical stability + RWM/control budgets (diagnostic; not predictive).")
        out = st.session_state.get("last_point_out")
        if not isinstance(out, dict):
            st.info("Run a point in Point Designer first.")
        else:
            st.metric("Tier", str(out.get("stability_risk_tier", "UNKNOWN")))
            cols = st.columns(4)
            with cols[0]:
                st.metric(
                    "Risk index",
                    f"{float(out.get('stability_risk_index', float('nan'))):.3f}"
                    if out.get("stability_risk_index") == out.get("stability_risk_index")
                    else "nan",
                )
            with cols[1]:
                st.metric("Dominant driver", str(out.get("stability_dominant_driver", "unknown")))
            with cols[2]:
                st.metric(
                    "vs_margin",
                    f"{float(out.get('vs_margin', float('nan'))):.3f}"
                    if out.get("vs_margin") == out.get("vs_margin")
                    else "nan",
                )
            with cols[3]:
                st.metric("RWM ok", "yes"if bool(out.get("rwm_control_ok", True)) else "no")

            st.divider()
            oc = st.columns(2)
            with oc[0]:
                st.metric("Operational tier", str(out.get("operational_risk_tier", "UNKNOWN")))
            with oc[1]:
                st.metric("Operational driver", str(out.get("operational_dominant_driver", "")) or "-")

            with st.expander("Components", expanded=False):
                st.json(out.get("stability_risk_components", {}))
            with st.expander("Control contract margins", expanded=False):
                st.json(out.get("control_contract_margins", {}))



    # --- Control Room block 31 (was app.py lines 5899..6226) ---
    with tab_cert_search:
        st.header("Certified Search")
        st.caption("Budgeted multi-knob search (external to truth). Each candidate is verified by the frozen evaluator.")

        from dataclasses import replace
        from solvers.budgeted_search import SearchVar
        from solvers.certified_search_orchestrator import (
            OrchestratorSpec,
            SearchStage,
            ParetoObjective,
            run_orchestrated_certified_search,
            run_orchestrated_certified_pareto_search,
        )

        base = st.session_state.get("last_point_inp")
        if base is None:
            st.info("Run a point in Point Designer first so a base point exists.")
        else:
            st.subheader("Knobs")
            knob_options = [
                ("Bt_T", 2.0, 25.0),
                ("Ip_MA", 1.0, 25.0),
                ("Paux_MW", 0.0, 200.0),
                ("Ti_keV", 1.0, 40.0),
                ("fG", 0.2, 1.2),
                ("kappa", 1.0, 2.6),
                ("a_m", 0.2, 3.0),
                ("R0_m", 0.8, 12.0),
            ]
            cols = st.columns(3)
            with cols[0]:
                chosen = st.multiselect(
                    "Select up to 4 knobs",
                    [k[0] for k in knob_options],
                    default=["Bt_T", "Ip_MA"],
                    max_selections=4,
                )
            with cols[1]:
                mode = st.selectbox(
                    "Mode",
                    ["Single objective (v340 compat)", "Pareto frontier (v405)",],
                    index=0,
                    key="cs_mode",
                )
            with cols[2]:
                objective = st.selectbox(
                    "Score objective (PASS-only)",
                    ["Q_DT_eqv", "P_fus_MW", "P_net_MW"],
                    index=0,
                    key="cs_single_obj",
                    disabled=(str(mode) != "Single objective (v340 compat)"),
                )

            pareto_objectives = []
            if str(mode) == "Pareto frontier (v405)":
                st.subheader("Pareto objectives")
                # Deterministic, compact objective menu
                obj_menu = [
                    ("R0_m", "min"),
                    ("B_peak_T", "min"),
                    ("P_e_net_MW", "max"),
                    ("q_div_MW_m2", "min"),
                    ("sigma_vm_MPa", "min"),
                    ("TBR", "max"),
                    ("Q_DT_eqv", "max"),
                ]
                ocols = st.columns(3)
                with ocols[0]:
                    o1 = st.selectbox("Objective #1", [o[0] for o in obj_menu], index=0, key="cs_p_obj1")
                with ocols[1]:
                    o2 = st.selectbox("Objective #2", [o[0] for o in obj_menu], index=2, key="cs_p_obj2")
                with ocols[2]:
                    o3 = st.selectbox("Objective #3 (optional)", ["(none)"] + [o[0] for o in obj_menu], index=0, key="cs_p_obj3")
                senses = {k: s for k, s in obj_menu}
                for ok in [o1, o2] + ([o3] if str(o3) != "(none)"else []):
                    pareto_objectives.append(ParetoObjective(key=str(ok), sense=str(senses.get(str(ok), "min"))))

                cpm = st.columns(2)
                with cpm[0]:
                    max_frontier = int(st.number_input("Max frontier points", value=30, min_value=5, max_value=200, step=5, key="cs_p_maxfront"))
                with cpm[1]:
                    filter_mirage = bool(st.checkbox("Filter mirage (lane)", value=True, key="cs_p_filter_mirage"))

            vars_=[]
            for name,lo,hi in knob_options:
                if name in chosen:
                    c1,c2=st.columns(2)
                    with c1:
                        lo_v = st.number_input(f"{name} lo", value=float(getattr(base,name)), step=0.1, key=f"cs_lo_{name}")
                    with c2:
                        hi_v = st.number_input(f"{name} hi", value=float(getattr(base,name)), step=0.1, key=f"cs_hi_{name}")
                    if hi_v <= lo_v:
                        hi_v = lo_v + 1e-6
                    vars_.append(SearchVar(name=name, lo=float(lo_v), hi=float(hi_v)))

            c1,c2,c3,c4=st.columns(4)
            with c1:
                budget = int(st.number_input("Budget", value=96, min_value=8, max_value=2048, step=8, key="cs_budget"))
            with c2:
                seed = int(st.number_input("Seed", value=0, min_value=0, max_value=10_000, step=1, key="cs_seed"))
            with c3:
                method = st.selectbox("Method", ["halton","lhs","grid"], index=0, key="cs_method")
            with c4:
                two_stage = bool(st.checkbox("Two-stage refine", value=True, key="cs_two_stage"))

            stage2_budget_frac = float(st.slider("Stage-2 budget fraction", min_value=0.10, max_value=0.80, value=0.35, step=0.05, key="cs_stage2_frac")) if two_stage else 0.0
            stage2_shrink = float(st.slider("Stage-2 local shrink", min_value=0.10, max_value=0.80, value=0.35, step=0.05, key="cs_stage2_shrink")) if two_stage else 0.0
            stage2_method = st.selectbox("Stage-2 method", ["grid","halton","lhs"], index=0, key="cs_stage2_method") if two_stage else "grid"

            st.markdown("---")
            insert_surr = bool(st.checkbox("Insert surrogate stage (feasible-first, non-authoritative)", value=False, key="cs_insert_surr"))
            surr_frac = float(
                st.slider(
                    "Surrogate budget fraction",
                    min_value=0.05,
                    max_value=0.60,
                    value=0.20,
                    step=0.05,
                    key="cs_surr_frac",
                    disabled=(not insert_surr),
                )
            )
            s1, s2, s3 = st.columns(3)
            with s1:
                surr_pool_mult = int(st.number_input("Surrogate pool multiplier", value=50, min_value=4, max_value=200, step=1, key="cs_surr_pool", disabled=(not insert_surr)))
            with s2:
                surr_kappa = float(st.slider("Surrogate kappa", min_value=0.0, max_value=2.0, value=0.5, step=0.1, key="cs_surr_kappa", disabled=(not insert_surr)))
            with s3:
                surr_ridge = float(st.number_input("Surrogate ridge alpha", value=1e-3, min_value=1e-6, max_value=1.0, format="%.6f", key="cs_surr_ridge", disabled=(not insert_surr)))

            def _builder(b, overrides):
                return replace(b, **{k: float(v) for k,v in overrides.items()})

            def _verifier(inp_obj):
                out = _ui_evaluate(inp_obj, origin="certified_search_verifier")
                cons = evaluate_constraints(out, point_inputs=inp_obj)
                try:
                    from constraints.bookkeeping import summarize as _summarize_constraints
                    _cs = _summarize_constraints(cons)
                    _min_margin_frac = float(_cs.worst_hard_margin_frac) if _cs.worst_hard_margin_frac is not None else float("nan")
                    _worst_hard = str(_cs.worst_hard or "")
                except Exception:
                    _min_margin_frac = float("nan")
                    _worst_hard = ""
                ok = all((not bool(c.get("failed"))) for c in cons)
                score = float(out.get(objective, 0.0)) if ok else float("-inf")

                evidence={
                    "objective": objective,
                    "objective_value": float(out.get(objective, float("nan"))),
                    "min_margin_frac": _min_margin_frac,
                    "worst_hard": _worst_hard,
                    "worst_hard_margin_frac": float(_min_margin_frac) if _min_margin_frac == _min_margin_frac else float("nan"),
                    "n_failed": int(sum(1 for c in cons if c.get("failed"))),
                    "top_blocker": (next((c.get("name") for c in cons if c.get("failed")), None)),
                }
                return ("PASS"if ok else "FAIL"), score, evidence

            if st.button("Run certified search", use_container_width=True, key="run_cert_search"):
                if not vars_:
                    st.warning("Select at least one knob.")
                else:
                    b1 = int(max(1, round(float(budget) * (1.0 - float(stage2_budget_frac)))))
                    b2 = int(max(0, round(float(budget) * float(stage2_budget_frac))))
                    bs = int(max(0, round(float(budget) * float(surr_frac)))) if insert_surr else 0
                    # cap budgets deterministically
                    b2 = int(min(int(b2), int(max(0, budget - 1))))
                    bs = int(min(int(bs), int(max(0, budget - 1 - b2))))
                    b1 = int(max(1, int(budget) - int(b2) - int(bs)))

                    stages = [SearchStage(name="stage1", method=str(method), budget=int(b1), seed=int(seed), local_refine=False)]
                    if insert_surr and bs > 0:
                        stages.append(
                            SearchStage(
                                name="surrogate",
                                method="surrogate",
                                budget=int(bs),
                                seed=int(seed + 1),
                                local_refine=False,
                                surrogate_pool_mult=int(surr_pool_mult),
                                surrogate_kappa=float(surr_kappa),
                                surrogate_ridge_alpha=float(surr_ridge),
                                surrogate_feas_margin_key="min_margin_frac",
                            )
                        )
                    if two_stage and b2 > 0:
                        stages.append(
                            SearchStage(
                                name="stage2",
                                method=str(stage2_method),
                                budget=int(b2),
                                seed=int(seed + (2 if (insert_surr and bs > 0) else 1)),
                                local_refine=True,
                                local_shrink=float(stage2_shrink),
                            )
                        )
                    if str(mode) == "Pareto frontier (v405)":
                        def _eval_fn(inp_obj):
                            return _ui_evaluate(inp_obj, origin="pareto_frontier_v405")

                        def _cons_fn(out_obj, inp_obj):
                            return evaluate_constraints(out_obj, point_inputs=inp_obj)

                        art = run_orchestrated_certified_pareto_search(
                            base_inputs=base,
                            spec=OrchestratorSpec(variables=tuple(vars_), stages=tuple(stages)),
                            objectives=list(pareto_objectives) if pareto_objectives else [ParetoObjective(key="R0_m", sense="min")],
                            builder=_builder,
                            evaluator_fn=_eval_fn,
                            constraints_fn=_cons_fn,
                            max_frontier=int(max_frontier),
                            filter_mirage=bool(filter_mirage),
                        )
                    else:
                        art = run_orchestrated_certified_search(
                            base,
                            OrchestratorSpec(variables=tuple(vars_), stages=tuple(stages)),
                            verifier=_verifier,
                            builder=_builder,
                        )
                    st.session_state["last_certified_search_artifact"] = art
                    st.session_state["v340_cert_search_last"] = art
                    try:
                        _v98_record_run("certified_search_orchestrated", art, mode="SystemSuite/Chronicle")
                    except Exception:
                        pass

                    n_pass = 0
                    n_tot = 0
                    try:
                        for stg in art.get("stages", []):
                            recs = stg.get("records", [])
                            n_tot += len(recs)
                            n_pass += sum(1 for r in recs if r.get("verdict") == "PASS")
                    except Exception:
                        pass
                    st.success(f"Done. Digest: {str(art.get('digest',''))[:12]} | PASS found: {n_pass}/{n_tot}")

            art = st.session_state.get("v340_cert_search_last")
            if isinstance(art, dict) and art.get("schema_version"):
                st.subheader("Results")
                # Flatten across stages for display
                rows = []
                for stg in art.get("stages", []):
                    for r in stg.get("records", []):
                        rows.append({"stage": stg.get("name"), "i": r.get("i"), "verdict": r.get("verdict"), "score": r.get("score"), **(r.get("x") or {}), **{f"e_{k}": v for k, v in (r.get("evidence") or {}).items()}})
                df = pd.DataFrame(rows)
                with st.expander("Results table", expanded=False):
                    st.dataframe(df, use_container_width=True, hide_index=True)
                if isinstance(art.get("best"), dict) and art["best"].get("x") is not None:
                    with st.expander("Best PASS candidate", expanded=False):
                        st.json(art.get("best"))

                # v405: frontier candidates (Pareto) with per-candidate evidence packs
                cands = art.get("candidates")
                if isinstance(cands, list) and len(cands) > 0:
                    st.subheader("Frontier candidates (v405)")
                    rows2 = []
                    for c in cands:
                        if not isinstance(c, dict):
                            continue
                        objm = c.get("objectives") or {}
                        row = {
                            "id": str(c.get("id", "")),
                            "lane_robust": str(c.get("lane_robust_verdict", "")),
                            "lane_opt": str(c.get("lane_optimistic_verdict", "")),
                            "is_mirage": bool(c.get("is_mirage_lane", False)),
                            "global_min_margin_v402": c.get("global_min_margin_v402"),
                            "dominant_authority": str(c.get("global_dominant_authority_v402", "")),
                            **(c.get("x") or {}),
                        }
                        if isinstance(objm, dict):
                            for k, v in objm.items():
                                row[f"obj_{k}"] = v
                        rows2.append(row)
                    df2 = pd.DataFrame(rows2)
                    with st.expander("Frontier table", expanded=False):
                        st.dataframe(df2, use_container_width=True, hide_index=True)

                    # Evidence pack per candidate
                    try:
                        from tools.frontier_candidate_evidence_zip import build_frontier_candidate_evidence_zip_bytes

                        cand_ids = [str(r.get("id")) for r in cands if isinstance(r, dict) and r.get("id")]
                        sel = st.selectbox("Select candidate for evidence pack", cand_ids, index=0, key="cs_p_sel") if cand_ids else None
                        if sel and st.button("Build selected candidate evidence pack", use_container_width=True, key="cs_p_build"):
                            b = build_frontier_candidate_evidence_zip_bytes(
                                orchestrator_artifact=art,
                                candidate_id=str(sel),
                                basename=f"frontier_candidate_{str(sel)}",
                            )
                            st.session_state["cs_p_candidate_zip"] = b
                            st.success("Candidate evidence pack built.")
                        b = st.session_state.get("cs_p_candidate_zip")
                        if isinstance(b, (bytes, bytearray)) and len(b) > 0:
                            st.download_button(
                                "Download frontier_candidate_evidence.zip",
                                data=b,
                                file_name="frontier_candidate_evidence.zip",
                                mime="application/zip",
                                use_container_width=True,
                                key="cs_p_dl",
                            )
                    except Exception:
                        pass

                # v297: export deterministic evidence pack
                try:
                    from tools.simple_evidence_zip import build_simple_evidence_zip_bytes
                    art2 = st.session_state.get("last_certified_search_artifact")
                    if isinstance(art2, dict):
                        if st.button("Build Certified Search evidence pack", use_container_width=True, key="cs_build_ev"):
                            b = build_simple_evidence_zip_bytes(art2, basename=f"certified_search_{art2.get('digest','')[:12]}")
                            st.session_state["certified_search_evidence_zip"] = b
                            st.success("Evidence pack built.")
                        b = st.session_state.get("certified_search_evidence_zip")
                        if isinstance(b, (bytes, bytearray)) and len(b) > 0:
                            st.download_button(
                                "Download certified_search_evidence.zip",
                                data=b,
                                file_name="certified_search_evidence.zip",
                                mime="application/zip",
                                use_container_width=True,
                                key="cs_dl_ev",
                            )
                except Exception:
                    pass



    # --- Control Room block 32 (was app.py lines 6228..6370) ---
    with tab_repair:
        st.header("Repair Suggestions")
        st.caption("Explanatory-only: proposes bounded knob deltas to reduce dominant constraint residuals; every proposal must be verified by truth.")

        from dataclasses import replace
        from solvers.repair_suggestions import RepairKnob, propose_repair_candidates

        base_inp = st.session_state.get("last_point_inp")
        base_out = st.session_state.get("last_point_out")
        if base_inp is None or not isinstance(base_out, dict):
            st.info("Run a point in Point Designer first.")
        else:
            cons = evaluate_constraints(base_out, point_inputs=base_inp)
            failed = [c for c in cons if c.get("failed")]
            if not failed:
                st.info("Base point is already feasible; repair suggestions are not needed.")
            else:
                # Residual proxy: use 'margin' if present else 1.0
                residuals = {}
                for c in failed:
                    name = str(c.get("name", "(unnamed)"))
                    m = c.get("margin")
                    try:
                        m = float(m)
                    except Exception:
                        m = None
                    # Convert to positive residual where 0 is pass.
                    if m is None or not (m == m):
                        residuals[name] = 1.0
                    else:
                        residuals[name] = max(0.0, -m)

                st.subheader("Select knobs")
                knob_options = [
                    ("Bt_T", 2.0, 25.0),
                    ("Ip_MA", 1.0, 25.0),
                    ("Paux_MW", 0.0, 200.0),
                    ("Ti_keV", 1.0, 40.0),
                    ("fG", 0.2, 1.2),
                    ("kappa", 1.0, 2.6),
                ]
                chosen = st.multiselect("Knobs used for repair", [k[0] for k in knob_options], default=["Bt_T","Ip_MA","Paux_MW"], max_selections=6)
                knobs=[]
                for name,lo,hi in knob_options:
                    if name in chosen:
                        lo_v=float(st.number_input(f"{name} lo", value=float(getattr(base_inp,name)), step=0.1, key=f"rep_lo_{name}"))
                        hi_v=float(st.number_input(f"{name} hi", value=float(getattr(base_inp,name)), step=0.1, key=f"rep_hi_{name}"))
                        if hi_v <= lo_v:
                            hi_v = lo_v + 1e-6
                        knobs.append(RepairKnob(name=name, lo=lo_v, hi=hi_v))

                # Finite-difference jacobian (deterministic): d(residual)/dvar
                def _eval_res(inp_obj):
                    out = _ui_evaluate(inp_obj, origin="jacobian_fd")
                    cons2 = evaluate_constraints(out, point_inputs=inp_obj)
                    res={}
                    for c in cons2:
                        name=str(c.get("name","(unnamed)"))
                        m=c.get("margin")
                        try:
                            m=float(m)
                        except Exception:
                            continue
                        res[name]=max(0.0, -m)
                    return res

                if st.button("Compute repair candidates", use_container_width=True, key="run_repairs"):
                    base_res = _eval_res(base_inp)
                    jac={}
                    for c in base_res:
                        jac[c]={}
                    for kb in knobs:
                        span = kb.hi - kb.lo
                        h = 0.02*span
                        if h<=0: continue
                        x0=float(getattr(base_inp,kb.name))
                        x1=min(kb.hi, x0+h)
                        x2=max(kb.lo, x0-h)
                        # central difference when possible
                        inp_p = replace(base_inp, **{kb.name: x1})
                        inp_m = replace(base_inp, **{kb.name: x2})
                        rp=_eval_res(inp_p)
                        rm=_eval_res(inp_m)
                        denom = (x1-x2) if (x1-x2)!=0 else 1e-12
                        for c in base_res:
                            jac[c][kb.name] = (float(rp.get(c,0.0))-float(rm.get(c,0.0)))/denom

                    cands = propose_repair_candidates(residuals=base_res, jacobian=jac, knobs=knobs, k=8)
                    st.session_state["v296_repair_last"] = {"base_res": base_res, "jac": jac, "cands": cands}

                last = st.session_state.get("v296_repair_last")
                if last:
                    with st.expander("Base residuals", expanded=False):
                        st.dataframe(pd.DataFrame([{ "constraint": k, "residual": v } for k,v in sorted(last["base_res"].items(), key=lambda kv: kv[1], reverse=True)]), use_container_width=True, hide_index=True)
                    st.subheader("Candidates")
                    cands = last["cands"]
                    if cands:
                        df = pd.DataFrame([{ "rationale": c.rationale, "est_reduction": c.estimated_residual_reduction, **c.deltas } for c in cands])
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("No candidates produced (check knob selections).")

                    # v297: build + download a deterministic repair evidence pack
                    try:
                        from dataclasses import asdict
                        from tools.simple_evidence_zip import build_simple_evidence_zip_bytes

                        repair_art = {
                            "schema_version": "repair_evidence.v1",
                            "base_inputs": asdict(base_inp),
                            "base_failed_constraints": [str(c.get("name")) for c in failed][:50],
                            "base_residuals": dict(last.get("base_res", {})),
                            "knobs": [asdict(k) for k in knobs],
                            "candidates": [
                                {
                                    "rationale": getattr(c, "rationale", ""),
                                    "estimated_residual_reduction": float(getattr(c, "estimated_residual_reduction", 0.0)),
                                    "deltas": dict(getattr(c, "deltas", {})),
                                }
                                for c in (cands or [])
                            ],
                        }
                        st.session_state["last_repair_evidence_artifact"] = repair_art

                        if st.button("Build Repair evidence pack", use_container_width=True, key="rep_build_ev"):
                            b = build_simple_evidence_zip_bytes(repair_art, basename="repair_evidence")
                            st.session_state["repair_evidence_zip"] = b
                            _v98_record_run("repair_evidence", repair_art, mode="SystemSuite/Chronicle")
                            st.success("Repair evidence pack built.")

                        b = st.session_state.get("repair_evidence_zip")
                        if isinstance(b, (bytes, bytearray)) and len(b) > 0:
                            st.download_button(
                                "Download repair_evidence.zip",
                                data=b,
                                file_name="repair_evidence.zip",
                                mime="application/zip",
                                use_container_width=True,
                                key="rep_dl_ev",
                            )
                    except Exception:
                        pass



    # --- Control Room block 33 (was app.py lines 6372..6477) ---
    with tab_refine:
        st.header("Interval Refinement")
        st.caption("Deterministic corner evaluation + contract refinement suggestions (explanatory-only).")

        from dataclasses import replace
        from uq_contracts.refinement import suggest_interval_refinements

        base = st.session_state.get("last_point_inp")
        if base is None:
            st.info("Run a point in Point Designer first so a base point exists.")
        else:
            st.subheader("Select up to 3 uncertain variables")
            var_options = ["Bt_T","Ip_MA","Paux_MW","Ti_keV","fG","kappa"]
            chosen = st.multiselect("Variables", var_options, default=["fG"], max_selections=3, key="ref_vars")
            intervals={}
            for v in chosen:
                c1,c2=st.columns(2)
                with c1:
                    lo = float(st.number_input(f"{v} lo", value=float(getattr(base,v))*0.95, step=0.1, key=f"ref_lo_{v}"))
                with c2:
                    hi = float(st.number_input(f"{v} hi", value=float(getattr(base,v))*1.05 + (0.01 if v=='fG' else 0.0), step=0.1, key=f"ref_hi_{v}"))
                if hi <= lo:
                    hi = lo + 1e-6
                intervals[v]=(lo,hi)

            if st.button("Evaluate corners", use_container_width=True, key="run_ref_corners"):
                # build corners
                vs=list(intervals.items())
                corners=[]
                def rec(i,cur):
                    if i==len(vs):
                        corners.append(dict(cur)); return
                    name,(lo,hi)=vs[i]
                    cur[name]=lo; rec(i+1,cur)
                    cur[name]=hi; rec(i+1,cur)
                    cur.pop(name,None)
                rec(0,{})

                results=[]
                for c in corners:
                    inp_obj=base
                    inp_obj=replace(inp_obj, **{k: float(v) for k,v in c.items()})
                    out = _ui_evaluate(inp_obj, origin="corner_probe")
                    cons = evaluate_constraints(out, point_inputs=inp_obj)
                    ok = all((not bool(cc.get("failed"))) for cc in cons)
                    dom = next((cc.get("name") for cc in cons if cc.get("failed")), None)
                    results.append({"corner": c, "verdict": "PASS"if ok else "FAIL", "dominant_mechanism": dom})

                st.session_state["v296_ref_corners"] = {"intervals": intervals, "results": results}

            last = st.session_state.get("v296_ref_corners")
            if last:
                res = last["results"]
                df = pd.DataFrame([{**r["corner"], "verdict": r["verdict"], "dominant": r.get("dominant_mechanism")} for r in res])
                st.dataframe(df, use_container_width=True, hide_index=True)
                fails=sum(1 for r in res if r["verdict"]!='PASS')
                st.metric("FAIL corners", f"{fails}/{len(res)}")
                sugg = suggest_interval_refinements(last["intervals"], res)
                if sugg:
                    st.subheader("Refinement suggestions")
                    sdf = pd.DataFrame([{"var": s.var, "current": s.current_interval, "suggested": s.suggested_interval, "rationale": s.rationale} for s in sugg])
                    st.dataframe(sdf, use_container_width=True, hide_index=True)
                else:
                    st.info("No refinement suggestions (either robust already or insufficient failure signal).")

                # v297: interval refinement evidence pack
                try:
                    from dataclasses import asdict
                    from tools.simple_evidence_zip import build_simple_evidence_zip_bytes

                    refine_art = {
                        "schema_version": "interval_refinement_evidence.v1",
                        "base_inputs": asdict(base),
                        "intervals": {k: list(v) for k, v in (last.get("intervals") or {}).items()},
                        "corner_results": list(res),
                        "suggestions": [
                            {
                                "var": s.var,
                                "current_interval": list(s.current_interval),
                                "suggested_interval": list(s.suggested_interval),
                                "rationale": s.rationale,
                            }
                            for s in (sugg or [])
                        ],
                    }
                    st.session_state["last_interval_refinement_artifact"] = refine_art

                    if st.button("Build Interval Refinement evidence pack", use_container_width=True, key="ref_build_ev"):
                        b = build_simple_evidence_zip_bytes(refine_art, basename="interval_refinement")
                        st.session_state["interval_refinement_zip"] = b
                        _v98_record_run("interval_refinement", refine_art, mode="SystemSuite/Chronicle")
                        st.success("Interval refinement evidence pack built.")

                    b = st.session_state.get("interval_refinement_zip")
                    if isinstance(b, (bytes, bytearray)) and len(b) > 0:
                        st.download_button(
                            "Download interval_refinement_evidence.zip",
                            data=b,
                            file_name="interval_refinement_evidence.zip",
                            mime="application/zip",
                            use_container_width=True,
                            key="ref_dl_ev",
                        )
                except Exception:
                    pass



    # --- Control Room block 34 (was app.py lines 6479..6489) ---
    with tab_narrowing:
        st.header("Interval Narrowing")
        st.caption(
            "Advisory dead-region flags + interval narrowing proposals + repair contract export (no truth mutation)."
        )
        try:
            from ui.interval_narrowing import render_interval_narrowing_panel
            render_interval_narrowing_panel(st, pd, BASE_DIR, st.session_state)
        except Exception as _e:
            st.info("Panel unavailable in this build.")



    # --- Control Room block 35 (was app.py lines 6491..6529) ---
    with tab_surrogate:
        st.header("Surrogate Overlay")
        st.caption("Non-authoritative ridge surrogate fitted to the latest Certified Search results.")

        from optimization.surrogates import fit_ridge_surrogate, predict_surrogate

        res = st.session_state.get("v296_cert_search_last")
        if res is None:
            st.info("Run Certified Search first (Chronicle → Certified Search) to generate training data.")
        else:
            # train on PASS points only
            rows=[]
            for r in res.records:
                if r.verdict == "PASS":
                    rows.append({"x": r.x, "y": r.score})
            if len(rows) < 8:
                st.warning(f"Need at least 8 PASS samples to fit a surrogate; currently have {len(rows)}.")
            else:
                feat = list(rows[0]["x"].keys())
                samples=[rr["x"] for rr in rows]
                targets=[rr["y"] for rr in rows]
                ridge=float(st.number_input("Ridge", value=1e-6, format="%e"))
                if st.button("Fit surrogate", use_container_width=True, key="fit_surr"):
                    model = fit_ridge_surrogate(samples, targets, feat, ridge=ridge)
                    st.session_state["v296_surrogate_model"] = model
                    st.success("Surrogate fitted (non-authoritative).")

                model = st.session_state.get("v296_surrogate_model")
                if model is not None:
                    st.subheader("Query")
                    q={}
                    for f in model.feature_names:
                        q[f]=float(st.number_input(f"{f}", value=float(st.session_state.get('last_point_inp').__dict__.get(f, 0.0)), step=0.1, key=f"surr_q_{f}"))
                    yhat, unc = predict_surrogate(model, q)
                    st.metric("Predicted score", f"{yhat:.6g}")
                    st.metric("Uncertainty proxy", f"{unc:.3f}")
                    with st.expander("Model details", expanded=False):
                        st.write({"features": list(model.feature_names), "ridge": model.ridge})



    # --- Control Room block 36 (was app.py lines 6531..6563) ---
    with tab_active_learning:
        st.header("Active Learning")
        st.caption("Propose new points where surrogate uncertainty is high (non-authoritative).")

        from optimization.active_learning import ALVar, propose_active_learning_points

        model = st.session_state.get("v296_surrogate_model")
        res = st.session_state.get("v296_cert_search_last")
        if model is None or res is None:
            st.info("Fit a surrogate first (Chronicle → Surrogate Overlay).")
        else:
            vars_=[]
            # derive bounds from SearchSpec
            for v in res.spec.variables:
                vars_.append(ALVar(name=v.name, lo=v.lo, hi=v.hi))
            c1,c2,c3=st.columns(3)
            with c1:
                n_candidates=int(st.number_input("Candidates", value=512, min_value=64, max_value=5000, step=64))
            with c2:
                n_select=int(st.number_input("Select", value=16, min_value=4, max_value=128, step=4))
            with c3:
                seed=int(st.number_input("Seed", value=int(res.spec.seed), min_value=0, max_value=10000, step=1))

            if st.button("Propose points", use_container_width=True, key="run_al"):
                props = propose_active_learning_points(model, vars_, n_candidates=n_candidates, n_select=n_select, seed=seed)
                st.session_state["v296_al_props"] = props

            props = st.session_state.get("v296_al_props")
            if props:
                df = pd.DataFrame([{**p.x, "y_pred": p.y_pred, "uncertainty": p.uncertainty} for p in props])
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption("Verify proposals by setting last_point_inp to a row and running Point Designer. External harness integration can automate that next.")



    # --- Control Room block 37 (was app.py lines 6565..6603) ---
    with tab_assumptions:
        st.header("Assumption Toggle Bar")
        st.caption("Fast scenario exploration by toggling common assumptions and re-evaluating the point (still feasibility-first; no optimization).")

        art = _get_active_artifact("assumptions")
        base = _guess_point_inputs_from_artifact(art) if art else None
        if base is None:
            base = st.session_state.get("last_point_inp")
        if base is None:
            st.info("Load an artifact (or run Point Designer) to use assumption toggles.")
        else:
            col1,col2,col3=st.columns(3)
            with col1:
                fuel = st.selectbox("Fuel mode", ["DT","DD"], index=0 if getattr(base,"fuel_mode","DT")=="DT"else 1, key="ass_fuel")
            with col2:
                ti = st.number_input("Ti (keV)", value=float(base.Ti_keV), step=0.5, key="ass_Ti")
            with col3:
                paux = st.number_input("Paux (MW)", value=float(base.Paux_MW), step=1.0, key="ass_Paux")
            tite = st.number_input("Ti/Te", value=float(getattr(base,"Ti_over_Te", 2.0)), step=0.1, key="ass_TiTe")
            apply = st.button("Apply toggles and evaluate", use_container_width=True, key="ass_run")

            if apply:
                pi = PointInputs(R0_m=float(base.R0_m), a_m=float(base.a_m), kappa=float(base.kappa),
                                 Bt_T=float(base.Bt_T), Ip_MA=float(base.Ip_MA), Ti_keV=float(ti),
                                 fG=float(base.fG), Paux_MW=float(paux), Ti_over_Te=float(tite),
                                 fuel_mode=str(fuel))
                out = _ui_evaluate(pi, origin="systems_point")
                cons = evaluate_constraints(out, point_inputs=pi)
                ok = all((not bool(c.get("failed"))) for c in cons)
                st.metric("Feasible", "YES "if ok else "NO ")
                st.subheader("Key outputs")
                st.json({k: out.get(k) for k in ["Q_DT_eqv","P_fus_MW","P_net_MW","betaN","q95","fG"] if k in out})
                st.subheader("Top failed constraints")
                failed=[c for c in cons if c.get("failed")]
                if failed:
                    st.dataframe(_safe_df(failed[:10]), use_container_width=True, hide_index=True)
                else:
                    st.write("No failed constraints.")



    # --- Control Room block 38 (was app.py lines 6605..6652) ---
    with tab_export:
        st.header("Export / Communication Panel")
        st.caption("One-click export helpers (JSON, CSV, and a one-slide PNG-style summary) with provenance footer.")

        art = _get_active_artifact("export")
        if not art:
            st.info("Load an artifact to export.")
        else:
            _download_json_button("Download run artifact JSON", art, "shams_run_artifact.json", "dl_artifact")
            tables = art.get("tables", {}) if isinstance(art.get("tables"), dict) else {}
            if tables:
                for name, obj in tables.items():
                    try:
                        df = _safe_df(obj)
                        st.download_button(f"Download {name}.csv", data=df.to_csv(index=False).encode("utf-8"),
                                           file_name=f"{name}.csv", mime="text/csv", key=f"dl_csv_{name}")
                    except Exception:
                        continue
            else:
                st.info("No standardized tables found in artifact ('tables').")

            try:
                import io
                import matplotlib.pyplot as plt
                prov = art.get("provenance", {}) if isinstance(art.get("provenance"), dict) else {}
                d = _decision_summary_from_artifact(art)
                fig = plt.figure(figsize=(10, 5))
                ax = fig.add_subplot(111)
                ax.axis("off")
                title = "SHAMS Decision Summary"
                verdict = "FEASIBLE"if d["feasible"] else "INFEASIBLE"
                ax.text(0.02, 0.92, f"{title} - {verdict}", fontsize=16, weight="bold")
                ax.text(0.02, 0.82, f"Q: {d['kpis'].get('Q_DT_eqv', d['kpis'].get('Q','-'))} Pfus(MW): {d['kpis'].get('P_fus_MW', d['kpis'].get('Pfus_MW','-'))}", fontsize=12)
                ax.text(0.02, 0.72, "Top blockers:", fontsize=12, weight="bold")
                y=0.66
                for b in (d["top_blockers"] or [])[:6]:
                    ax.text(0.04, y, f"- {b.get('group','')}: {b.get('name','')}", fontsize=11)
                    y -= 0.06
                footer = f"repo_version={prov.get('repo_version')} git={prov.get('git_commit')} python={prov.get('python')}"
                ax.text(0.02, 0.03, footer, fontsize=9)
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
                plt.close(fig)
                st.download_button("Download one-slide summary PNG", data=buf.getvalue(), file_name="shams_one_slide.png",
                                   mime="image/png", key="dl_png_slide")
            except Exception as e:
                st.warning(f"PNG summary unavailable: {e}")



    # --- Control Room block 39 (was app.py lines 6654..6705) ---
    with tab_solver:
        st.header("Solver Introspection")
        st.caption("Inspect solver trace/clamp/residual info from artifacts or the last Point Designer run.")

        art = st.session_state.get("selected_artifact")
        if not isinstance(art, dict) or not art:
            st.info("No session artifact loaded. Upload one below to inspect solver annotations.")
            up = st.file_uploader("Upload shams_run_artifact.json", type=["json"], key="solver_up")
            art = _load_json_from_upload(up)

        if art:
            trace = art.get("solver_trace") if isinstance(art.get("solver_trace"), dict) else None
            if trace:
                st.subheader("solver_trace (artifact)")
                st.json(trace)
            else:
                st.subheader("Solver annotations (best-effort)")
                flat = {}
                for k,v in art.items():
                    if isinstance(k,str) and (k.startswith("_solver") or k.startswith("_H98") or k.startswith("_Q")):
                        flat[k]=v
                kpis = art.get("kpis", {}) if isinstance(art.get("kpis"), dict) else {}
                for k,v in kpis.items():
                    if isinstance(k,str) and (k.startswith("_solver") or k.startswith("_H98") or k.startswith("_Q")):
                        flat[f"kpis.{k}"]=v
                if flat:
                    st.json(flat)
                else:
                    st.info("No solver trace fields found in artifact.")

            st.divider()
            st.subheader("CCFS verifier (external solver firewall)")
            st.caption("Verify an external candidate bundle against frozen truth. Runs do not modify SHAMS physics.")
            up_ccfs = st.file_uploader("Upload ccfs_bundle.json", type=["json"], key="ccfs_up_v294")
            b = _load_json_from_upload(up_ccfs)
            if isinstance(b, dict):
                req_cols = st.columns(2)
                with req_cols[0]:
                    do_phase = st.checkbox("Require phase envelope PASS", value=True, key="ccfs_req_phase_v294")
                with req_cols[1]:
                    do_uq = st.checkbox("Require UQ contract not FAIL", value=False, key="ccfs_req_uq_v294")

                if st.button("Verify CCFS bundle", use_container_width=True, key="ccfs_btn_v294"):
                    try:
                        from extopt.certified_solve import verify_ccfs_bundle
                        res = verify_ccfs_bundle(b, default_request={"phase_envelope": bool(do_phase), "uq_contracts": bool(do_uq)})
                        st.success("CCFS verification complete.")
                        st.json(res, expanded=False)
                        _v98_record_run("ccfs_verify", res, mode="ControlRoom/Diagnostics")
                    except Exception as e:
                        st.error(f"CCFS verification failed: {e}")


