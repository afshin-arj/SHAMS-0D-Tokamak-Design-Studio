"""Publication Benchmarks deck -- extracted from ui/app.py (UI redesign).

Pure move + cosmetic de-emoji (UI redesign). No physics, constraint,
solver, evaluator, session-state key, or routing-ID changes. The block runs
with app.py module globals injected (namespace bridge, including app.py's
__file__ so path computations resolve as before); this bridge is temporary
tech debt to be replaced with explicit imports/ctx in a later cleanup commit.
"""
from __future__ import annotations
import streamlit as st
import sys


from ._bridge import bridge_deck

def render_publication_benchmarks(_app_module) -> None:
    # Namespace bridge: borrow app.py module globals so this extracted block
    # resolves every bare name exactly as it did inline. __file__ is injected
    # so Path(__file__).resolve().parent.parent / .parents[1] still resolve to
    # the SHAMS-0D root (app.py's location), not ui/decks/. Pure move.
    bridge_deck(_app_module, globals())

    st.header("Publication Benchmarks")
    st.caption("Benchmark suite: publication tables and the Tokamak Constitutional Atlas (preset-driven, intent-aware).")

    _pb_tabs = st.tabs([
        "Tokamak Constitutional Atlas",
        "Cross‑Code Constitutions",
        "Publication Benchmarks",
        "Contract Studio",
        "Regulatory Evidence Pack Builder (v387)",
    ])
    with _pb_tabs[0]:
        st.subheader("Tokamak Constitutional Atlas")
        st.caption("Select a famous tokamak preset and evaluate under **Research** or **Reactor** intent. No tuning. Deterministic, reviewer-safe.")

        try:
            from benchmarks.constitutional.atlas import evaluate_atlas_case, local_fragility_scan
            from benchmarks.constitutional.constitutions import intent_to_constitution, constitution_diff, pretty_clause
        except Exception as e:
            st.error("Constitutional Atlas modules are unavailable. Check installation / repo integrity.")
            st.exception(e)
        else:
            cat = reference_catalog()
            # Build categories (expert-friendly, stable ordering)
            _items = []
            for k, ent in cat.items():
                _items.append((k, str(ent.get("intent","")), str(ent.get("family","")), str(ent.get("label",k))))
            # deterministic sorting
            _items.sort(key=lambda x: (x[1], x[2], x[3]))

            # Categorize
            def _bucket(intent: str, family: str) -> str:
                it = intent.strip().upper()
                fam = family.strip().upper()
                if it.startswith("RESEARCH"):
                    return "Experimental Devices"
                if fam in ("ITER","JET","DIIID","DIII-D","EAST","KSTAR","JT-60SA","ASDEX","ASDEX-U","AUG","NSTX-U","MAST-U"):
                    return "Large-Scale & Program"
                if fam in ("SPARC","ARC"):
                    return "Compact / HTS"
                return "Reactor Concepts"

            buckets = {}
            for k,intent,family,label in _items:
                b=_bucket(intent,family)
                buckets.setdefault(b, []).append((k,label,intent,family))

            left, right = st.columns([0.32, 0.68], gap="large")
            with left:
                st.markdown("### Preset")
                _bucket_names = list(buckets.keys())
                _bucket_sel = st.radio("Category", _bucket_names, index=0, horizontal=False, label_visibility="collapsed")
                opts = buckets[_bucket_sel]
                labels = [o[1] for o in opts]
                keys = [o[0] for o in opts]
                sel_label = st.radio("Tokamak", labels, index=0)
                preset_key = keys[labels.index(sel_label)]

                st.markdown("### Intent")
                intent_sel = st.radio("Intent", ["Research", "Reactor"], index=0, horizontal=True)

                st.caption("Preset key")
                st.code(preset_key)

            with right:
                # Run evaluation
                with st.spinner("Evaluating preset under selected intent…"):
                    res = evaluate_atlas_case(preset_key, intent_sel)

                # Decks
                decks = st.tabs(["Verdict", "Constitution Diff", "Envelope & Fragility", "Evidence"])
                with decks[0]:
                    run = res.run or {}
                    verdict = str(run.get("verdict","")).upper() if isinstance(run, dict) else ""
                    dom_mech = run.get("dominant_mechanism","")
                    dom_con = run.get("dominant_constraint","")
                    # v258.0: epoch feasibility summary (if present)
                    epoch_overall = ""
                    epoch_rows = []
                    try:
                        _ef = ((run.get("artifact") or {}).get("epoch_feasibility") or {}) if isinstance(run, dict) else {}
                        epoch_overall = str(_ef.get("overall","") or "")
                        for e in (_ef.get("epochs") or []):
                            if not isinstance(e, dict):
                                continue
                            epoch_rows.append({
                                "epoch": str(e.get("epoch","")),
                                "verdict": str(e.get("verdict","")),
                            })
                    except Exception:
                        epoch_overall = ""
                        epoch_rows = []

                    # derive worst hard margin if present
                    worst = None
                    led = (run.get("constraints", {}) or {}) if isinstance(run, dict) else {}
                    for _,c in led.items():
                        if isinstance(c, dict) and c.get("severity","").lower()=="hard":
                            m = c.get("margin")
                            if isinstance(m,(int,float)):
                                worst = m if worst is None else min(worst, m)
                    st.markdown(f"**Status:** {verdict or '-'}")
                    st.markdown(f"**Dominant mechanism:** {dom_mech or '-'}")
                    st.markdown(f"**Dominant constraint:** {dom_con or '-'}")
                    st.markdown(f"**Worst hard margin:** {('%.3f'%worst) if isinstance(worst,(int,float)) else '-'}")
                    if epoch_overall:
                        st.markdown(f"**Epoch feasibility (overall):** `{epoch_overall}`")
                    if epoch_rows:
                        st.dataframe(epoch_rows, use_container_width=True, hide_index=True)
                    # v256.0: authority confidence badge (trust ledger)
                    try:
                        _art = (run.get("artifact") or {}) if isinstance(run, dict) else {}
                        _ac = (_art.get("authority_confidence") or {}) if isinstance(_art, dict) else {}
                        _dc = str((_ac.get("design") or {}).get("design_confidence_class", "UNKNOWN"))
                        st.markdown(f"**Design confidence:** `{_dc}`")

                        # v366.0: multi-fidelity tier stamp (reviewer-facing)
                        _ft = (_art.get("fidelity_tiers") or {}) if isinstance(_art, dict) else {}
                        _fl = str((_ft.get("design") or {}).get("design_fidelity_label", ""))
                        if _fl:
                            st.markdown(f"**Fidelity tier:** `{_fl}`")

                        _dcon = (_art.get("decision_consequences") or {}) if isinstance(_art, dict) else {}
                        _post = str(_dcon.get("decision_posture", "UNKNOWN"))
                        _risk = str(_dcon.get("primary_risk_driver", "") or "")
                        st.markdown(f"**Decision posture:** `{_post}`")
                        if _risk:
                            st.markdown(f"**Primary risk driver:** `{_risk}`")
                    except Exception:
                        st.markdown("**Design confidence:** `UNKNOWN`")
                    st.caption(f"Native preset intent: **{res.native_intent}** • Stamp: `{res.stamp_sha256[:12]}…`")

                with decks[1]:
                    st.markdown("**Selected intent constitution**")
                    st.json(res.constitution_selected, expanded=False)
                    st.markdown("**Preset native intent constitution**")
                    st.json(res.constitution_native, expanded=False)

                    diff = res.constitution_diff or []
                    st.markdown("### Diff (selected → native)")
                    if not diff:
                        st.success("No constitutional differences. (Selected intent matches the preset’s native intent semantics.)")
                    else:
                        # Present as compact diff table
                        rows=[]
                        for d in diff:
                            rows.append({
                                "Clause": pretty_clause(d.get("key","")),
                                "Selected": d.get("from",""),
                                "Native": d.get("to",""),
                            })
                        st.table(rows)

                with decks[2]:
                    st.caption("Deterministic local neighborhood scan (small grid) to classify robustness/fragility.")
                    # Choose knobs based on typical availability
                    # Use fG and Paux_MW if present; fall back to H98 and fG
                    base_in = dict(reference_catalog()[preset_key]["inputs"].to_dict())
                    knobs={}
                    if "fG"in base_in:
                        knobs["fG"] = (float(base_in["fG"]), 0.05, 0.05)
                    if "Paux_MW"in base_in:
                        knobs["Paux_MW"] = (float(base_in["Paux_MW"]), 0.10, 0.10)
                    elif "H98"in base_in:
                        knobs["H98"] = (float(base_in["H98"]), 0.05, 0.05)
                    scan = local_fragility_scan(preset_key, intent_sel, knobs)
                    st.markdown(f"**Pass fraction:** {scan.get('pass_fraction',0):.2f}")
                    st.markdown(f"**Mechanism stable:** {'Yes' if scan.get('mechanism_stable', True) else 'No'}")
                    wm = scan.get("worst_margin_min")
                    st.markdown(f"**Worst margin (min):** {('%.3f'%wm) if isinstance(wm,(int,float)) else '-'}")
                    st.json(scan, expanded=False)

                with decks[3]:
                    payload = {
                        "schema": res.schema,
                        "preset_key": res.preset_key,
                        "preset_label": res.preset_label,
                        "selected_intent": res.selected_intent,
                        "native_intent": res.native_intent,
                        "constitution_selected": res.constitution_selected,
                        "constitution_native": res.constitution_native,
                        "constitution_diff": res.constitution_diff,
                        "run": res.run,
                        "stamp_sha256": res.stamp_sha256,
                    }
                    st.download_button(
                        "Download Atlas Evidence (JSON)",
                        data=json.dumps(payload, indent=2),
                        file_name=f"atlas_{res.selected_intent.lower()}_{res.preset_key.replace('|','_')}.json",
                        mime="application/json",
                        use_container_width=True,
                    )
                    st.caption("This is a deterministic, single-case evidence capsule: inputs, outputs, ledger, constitution semantics, and a stable SHA-256 stamp.")

    

    with _pb_tabs[1]:
        st.subheader("Cross‑Code Constitutions")
        st.caption("Documentation-level comparison: map other system codes' effective enforcement semantics against SHAMS intent constitutions. This does not execute external codes; it records and diffs declared clause semantics, with citations.")
        try:
            from benchmarks.crosscode.crosscode_compare import list_crosscode_constitutions, load_crosscode_constitution, compare_to_shams_intent
        except Exception as e:
            st.error(f"Cross-code module import failed: {e}")
        else:
            _items = list_crosscode_constitutions()
            if not _items:
                st.info("No cross-code constitution records found.")
            else:
                labels = [k for k,_ in _items]
                paths_map = {k:p for k,p in _items}
                colA, colB = st.columns([2,1], vertical_alignment="top")
                with colA:
                    code_key = st.selectbox("External code", labels, index=0, key="cc_code_sel")
                with colB:
                    intent = st.radio("SHAMS intent", ["research","reactor"], horizontal=True, key="cc_intent_sel")
                cc = load_crosscode_constitution(paths_map[code_key])
                comp = compare_to_shams_intent(intent, cc)
                c1, c2, c3 = st.columns(3)
                c1.metric("Unknown clauses", comp["unknown_clause_count"])
                c2.metric("Clauses total", len(comp["crosscode_constitution"]["clauses"]))
                c3.metric("Diff entries", len(comp["diff"]))
                st.markdown("#### Notes")
                st.write(cc.source_notes)
                if cc.citations:
                    st.markdown("#### Citations")
                    for c in cc.citations:
                        st.write(f"- {c}")
                st.markdown("#### Constitution Diff")
                st.json(comp["diff"], expanded=False)
                st.markdown("#### Clause Table")
                st.dataframe(
                    [{"clause": k, "shams": comp["baseline_constitution"].get(k, "(missing)"), "external": v}
                     for k, v in sorted(comp["crosscode_constitution"]["clauses"].items())],
                    use_container_width=True,
                    hide_index=True,
                )
                st.markdown("#### Export")
                st.download_button(
                    "Download comparison (JSON)",
                    data=json.dumps(comp, indent=2).encode("utf-8"),
                    file_name=f"crosscode_comparison__{code_key}__{intent}.json",
                    mime="application/json",
                )

    with _pb_tabs[2]:

                # Status pill (simple, honest)
                _status = "Ready"
                _status_help = "Benchmarks are available. Runs use the frozen evaluator and configured machine list."
                st.markdown(f"**Status:** {_status}")
                st.caption(_status_help)

                # Topology regression (CI-grade): shows whether feasibility topology drifted vs baseline.
                with st.expander("Topology regression (robust/fragile/empty stability)", expanded=False):
                    rep_path = Path(ROOT) / "verification"/ "topology_regression_report.json"
                    if rep_path.exists():
                        try:
                            rep = json.loads(rep_path.read_text(encoding="utf-8"))
                        except Exception:
                            rep = {}
                        ok = bool(rep.get("ok", False))
                        st.markdown(f"**Result:** {' PASS' if ok else ' FAIL'}")
                        if not ok:
                            st.warning("Topology regression failed. See report details below; run gatecheck for full context.")
                        st.json(rep, expanded=False)
                    else:
                        st.info("No topology regression report found yet. Run **Run gatecheck** (or run `python verification/topology_regression.py`).")

                with st.container(border=True):
                    st.subheader("What this does")
                    st.write(
                        "Generates paper-ready benchmark tables and per-machine artifacts by evaluating the configured "
                        "reference machines with the frozen Point Designer. No physics, constraints, or policies are modified."
                    )
                    st.markdown("**Outputs include:**")
                    st.markdown("- CSV benchmark tables (Research & Reactor)\n- Per-machine JSON artifacts (inputs, outputs, constraint ledger)\n- Run metadata (timestamp, version, hash)")

                    cL, cR = st.columns(2, gap="large")
                    with cL:
                        st.markdown("### Research Machines")
                        st.caption("Policy: Research Intent • q95 hard • Plant constraints diagnostic/ignored")
                        st.markdown("- ITER / JET / DIII-D / EAST / KSTAR / JT-60SA\n- SPARC / NSTX-U / MAST-U (as configured)")
                    with cR:
                        st.markdown("### Reactor & Pilot Plants")
                        st.caption("Policy: Reactor Intent • Full feasibility gates enforced")
                        st.markdown("- ARC / ARIES-class\n- EU DEMO (incl. low-A variants)\n- STEP Prototype Plant (as configured)")

                    st.divider()

                    st.markdown("### Reproducibility contract")
                    st.markdown("-  Frozen Point Designer evaluator\n-  Deterministic run (no stochastic elements)\n-  Explicit Design Intent policies\n-  Versioned artifact schema")
                    st.caption("Every run is replayable. Every table is traceable.")

                    st.divider()

                    # One-button launcher with explicit acknowledgment (keeps it review-safe)
                    if "pubbench_ack"not in st.session_state:
                        st.session_state.pubbench_ack = False
                    if "pubbench_running"not in st.session_state:
                        st.session_state.pubbench_running = False
                    if "pubbench_last_outdir"not in st.session_state:
                        st.session_state.pubbench_last_outdir = None
                    if "pubbench_last_rc"not in st.session_state:
                        st.session_state.pubbench_last_rc = None

                    st.markdown("### Action")
                    st.checkbox("I understand this is a non-interactive, audit-grade run.", key="pubbench_ack")

                    run_btn = st.button("Generate Publication Benchmark Pack", type="primary", disabled=(not st.session_state.pubbench_ack or st.session_state.pubbench_running))
                    prog = st.empty()
                    log_box = st.empty()

                    if run_btn:
                        st.session_state.pubbench_running = True
                        try:
                            import sys, subprocess, time, os
                            ts = time.strftime("%Y%m%d_%H%M%S")
                            outdir = os.path.join("benchmarks", "publication", "out_ui", ts)
                            os.makedirs(outdir, exist_ok=True)
                            cases = os.path.join("benchmarks", "publication", "cases_point_designer.json")
                            runner = os.path.join("benchmarks", "publication", "run_point_designer_benchmarks.py")

                            cmd = [sys.executable, runner, "--cases", cases, "--outdir", outdir, "--also-run-opposite-intent"]
                            prog.progress(0.05)
                            p = subprocess.run(cmd, capture_output=True, text=True)
                            prog.progress(1.0)

                            st.session_state.pubbench_last_outdir = outdir
                            st.session_state.pubbench_last_rc = int(p.returncode)

                            _out = (p.stdout or "").strip()
                            _err = (p.stderr or "").strip()
                            if _out:
                                log_box.code(_out[:8000])
                            if _err:
                                st.warning("Runner warnings/errors (stderr):")
                                st.code(_err[:8000])

                            if p.returncode == 0:
                                st.success(f"Completed. Output: {outdir}")
                            else:
                                st.error(f"Benchmark run failed (exit code {p.returncode}). Output folder: {outdir}")
                        except Exception as e:
                            st.error(f"Benchmark run failed: {e}")
                        finally:
                            st.session_state.pubbench_running = False

                    if st.session_state.pubbench_last_outdir:
                        st.caption(f"Last output: {st.session_state.pubbench_last_outdir} (rc={st.session_state.pubbench_last_rc})")

                    if st.session_state.pubbench_last_outdir and int(st.session_state.pubbench_last_rc or 0) == 0:
                        st.markdown("#### Pack inspection (topology + delta)")
                        outdir = st.session_state.pubbench_last_outdir
                        # B3: topology
                        try:
                            import os, json
                            topo_p = os.path.join(outdir, "topology.json")
                            if os.path.exists(topo_p):
                                topo = json.loads(open(topo_p, "r", encoding="utf-8").read())
                                cA, cB, cC, cD = st.columns(4)
                                fr = (topo.get("fractions") or {})
                                cA.metric("Pass frac", f"{float(fr.get('pass',0.0)):.2f}")
                                cB.metric("Robust frac", f"{float(fr.get('robust',0.0)):.2f}")
                                cC.metric("Fragile frac", f"{float(fr.get('fragile',0.0)):.2f}")
                                cD.metric("Fail frac", f"{float(fr.get('fail',0.0)):.2f}")
                                st.json({"dominant_mechanism_hist": topo.get("dominant_mechanism_hist", {})})
                        except Exception:
                            pass

                        # B2: delta explainer
                        st.markdown("##### Explain delta vs baseline")
                        try:
                            import os, glob
                            base_dir = os.path.join("benchmarks", "publication", "baselines")
                            opts = []
                            if os.path.isdir(base_dir):
                                # allow baseline packs as directories, else fall back to shipped CSV baseline
                                for d in sorted(glob.glob(os.path.join(base_dir, "*"))):
                                    opts.append(d)
                            baseline_sel = st.selectbox("Baseline pack/folder", opts if opts else [base_dir], index=0, key="pubbench_delta_base_v235")
                            if st.button("Explain delta (baseline → last pack)", use_container_width=True, key="pubbench_delta_btn_v235"):
                                runner = os.path.join("benchmarks", "publication", "explain_delta.py")
                                cmd = [sys.executable, runner, "--baseline", baseline_sel, "--candidate", outdir]
                                p = subprocess.run(cmd, capture_output=True, text=True)
                                if p.returncode == 0:
                                    st.success("Delta explanation written to delta.md in the candidate pack.")
                                    delta_path = os.path.join(outdir, "delta.md")
                                    if os.path.exists(delta_path):
                                        st.code(open(delta_path, "r", encoding="utf-8").read()[:12000])
                                else:
                                    st.error(f"Delta explainer failed (rc={p.returncode}).")
                                    if p.stderr:
                                        st.code(p.stderr[:8000])
                        except Exception as e:
                            st.warning(f"Delta tools unavailable: {e}")

                st.caption("Exploration happens elsewhere in the UI. Evidence is generated here.")

                st.divider()
                st.markdown("### Evidence exports")
                st.caption("Generate reviewer/regulator and licensing packs from the current session artifact (read-only).")

                with st.expander("Regulatory & Reviewer Evidence Packs (v334)", expanded=False):
                    try:
                        from ui.regulatory_evidence_pack import render_regulatory_evidence_pack_panel
                        render_regulatory_evidence_pack_panel(REPO_ROOT)
                    except Exception as _e:
                        st.error(f"Regulatory evidence pack panel import failed: {_e}")

                with st.expander("Licensing Evidence Tier 2 (v355)", expanded=False):
                    try:
                        from ui.licensing_evidence_tier2 import render_licensing_evidence_tier2_panel
                        render_licensing_evidence_tier2_panel(REPO_ROOT)
                    except Exception as _e:
                        st.error(f"Licensing Tier 2 panel import failed: {_e}")

    with _pb_tabs[3]:
        st.subheader("Contract Studio")
        st.caption("Validate and export governance contracts (read-only).")
        try:
            from ui.contract_studio import render_contract_studio
            from pathlib import Path
            _repo_root = Path(__file__).resolve().parents[1]
            render_contract_studio(_repo_root, ui_key_prefix="pb_contract_studio")
        except Exception as e:
            try:
                st.error(f"Contract Studio import failed: {e}")
            except Exception:
                pass

    with _pb_tabs[4]:
        st.subheader("Regulatory Evidence Pack Builder (v387)")
        st.caption("Deterministic, hash-locked evidence ZIP from cached runs (export-only).")

        try:
            from src.tools.evidence_pack_v387 import build_evidence_pack_v387
        except Exception as _e:
            st.error(f"Evidence pack builder import failed: {_e}")
        else:
            # Cache-only: do not compute here; export whatever is already in session cache.
            cache_sources = {
                "pd_last_outputs": st.session_state.get("pd_last_outputs"),
                "systems_last_solution": st.session_state.get("systems_last_solution"),
                "scan_last_artifact": st.session_state.get("scan_last_artifact"),
                "pareto_last_front": st.session_state.get("pareto_last_front"),
                "extopt_last_run": st.session_state.get("extopt_last_run"),
                "surrogate_v386_last_screening_run": st.session_state.get("surrogate_v386_last_screening_run"),
            }

            st.markdown("### Select cached sources")
            include_flags: Dict[str, bool] = {}
            cols = st.columns(2)
            for i, k in enumerate(sorted(cache_sources.keys())):
                v = cache_sources.get(k)
                avail = isinstance(v, (dict, list))
                with cols[i % 2]:
                    include_flags[k] = st.checkbox(
                        f"Include `{k}`{' ' if avail else ' (missing)'}",
                        value=bool(avail),
                        disabled=not avail,
                        key=f"pb_v387_inc_{k}",
                    )

            notes = st.text_area(
                "Reviewer notes (optional)",
                value=str(st.session_state.get("pb_v387_notes", "")),
                key="pb_v387_notes",
                height=120,
            )
            st.session_state["pb_v387_notes"] = notes

            run_btn = st.button("Build Evidence Pack", type="primary", key="pb_v387_build")
            if run_btn:
                shams_version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip().splitlines()[0]
                out_dir = REPO_ROOT / "ui_runs"/ "evidence_packs_v387"
                out_dir.mkdir(parents=True, exist_ok=True)
                out_zip = out_dir / "evidence_pack_v387.zip"
                with st.spinner("Building deterministic evidence ZIP…"):
                    res = build_evidence_pack_v387(
                        out_zip,
                        shams_version=shams_version,
                        sources=cache_sources,
                        include=include_flags,
                        notes=notes,
                    )
                st.session_state["evidence_pack_v387_last_zip"] = str(res.zip_path)
                st.session_state["evidence_pack_v387_last_index"] = res.index

            # Render from cache
            idx = st.session_state.get("evidence_pack_v387_last_index")
            zpath = st.session_state.get("evidence_pack_v387_last_zip")
            if isinstance(idx, dict):
                with st.expander("Pack index", expanded=False):
                    st.json(idx, expanded=False)
            if isinstance(zpath, str) and zpath:
                try:
                    from pathlib import Path
                    p = Path(zpath)
                    if p.exists():
                        st.download_button(
                            "Download Evidence Pack (ZIP)",
                            data=p.read_bytes(),
                            file_name=p.name,
                            mime="application/zip",
                            use_container_width=True,
                            key="pb_v387_dl",
                        )
                except Exception as _e:
                    st.error(f"Unable to load evidence ZIP: {_e}")
