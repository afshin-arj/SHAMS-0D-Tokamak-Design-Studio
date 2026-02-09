from __future__ import annotations

"""🧪 Trade Study Studio UI (v303.0).

This is the PROCESS-replacement ergonomics layer:
  - feasibility-first trade studies
  - UI-orchestrated firewalled optimizer kits
  - two-lane optimistic vs robust contracts
  - design-family atlas
  - mirage pathfinding (deterministic scans)

All evaluation remains through the frozen evaluator. No internal solver/optimization
enters the truth layer.

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import asdict
import json
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd  # type: ignore

from evaluator.core import Evaluator
from models.inputs import PointInputs

from trade_studies.spec import default_knob_sets
from trade_studies.runner import run_trade_study
from trade_studies.families import attach_families, family_summary, FAMILIES
from trade_studies.pathfinding import default_pathfinding_levers, one_knob_path_scan

from optimization.objectives import list_objectives

from uq_contracts.runner import run_uncertainty_contract_for_point
from uq_contracts.spec import optimistic_uncertainty_contract, robust_uncertainty_contract


def _ss_get_point(st: Any) -> PointInputs:
    base_inp = st.session_state.get("last_point_inp", None)
    if isinstance(base_inp, PointInputs):
        return base_inp
    # fallback: canonical baseline (mirrors tests/test_smoke.py)
    return PointInputs(
        R0_m=1.81,
        a_m=0.57,
        kappa=1.8,
        Bt_T=12.2,
        Ip_MA=7.5,
        Ti_keV=12.0,
        fG=0.85,
        Paux_MW=25.0,
    )


def _objectives_catalog() -> Tuple[List[str], Dict[str, str]]:
    reg = list_objectives()
    names = sorted(reg.keys())
    senses = {k: str(reg[k].sense) for k in names}

    # v327.5: pipeline-native DSG subset linking (best-effort)
    try:
        from ui.handoff import render_subset_linker_best_effort  # type: ignore
        _df_for_link = locals().get("df_show") or locals().get("df_ranked") or locals().get("df") or locals().get("df_out")
        if _df_for_link is not None:
            render_subset_linker_best_effort(df=_df_for_link, label="Trade Study", kind="trade_select", note="Selection from Trade Study table")
    except Exception:
        pass

    return names, senses


def render_trade_study_studio(st: Any, *, repo_root: Path) -> None:
    st.header("🧪 Trade Study Studio")
    st.caption(
        "Feasibility-first trade studies + firewalled optimizer kits + two-lane optimistic design. "
        "Truth remains frozen; optimization is proposal-only."
    )

    with st.expander("Scope: what this mode does / does not do", expanded=False):
        st.markdown(
            """
**Does**
- Runs deterministic, budgeted trade studies over explicit knob sets.
- Extracts Pareto fronts **only over feasible points**.
- Launches **external** optimizer kits that generate candidate proposals.
- Evaluates candidates under **Optimistic vs Robust** contract lanes.
- Builds deterministic **design-family** narratives.
- Performs deterministic **mirage pathfinding** scans (no solvers).

**Does not**
- Modify frozen physics truth.
- Use internal solvers / penalty smoothing.
- Claim a globally ‘best machine’.
"""
        )

    ev = Evaluator(cache_enabled=True)
    base = _ss_get_point(st)

    # --- Deck navigation ---
    deck = st.selectbox(
        "Studio deck",
        [
            "🎛️ Study Setup & Run",
            "⚡ Feasible-First Surrogate Accelerator",
            "🧰 Optimizer Kits (External)",
            "⚡ Fast Optimistic Design (Two-Lane)",
            "🧬 Design Family Atlas",
            "🗺️ Regime Maps & Narratives (v324)",
            "🧭 Mirage Pathfinding",
        ],
        key="trade_study_deck",
    )

    # Persistent state slots
    if "ts_last" not in st.session_state:
        st.session_state["ts_last"] = None
    if "ts_last_lane" not in st.session_state:
        st.session_state["ts_last_lane"] = None

    # --------------------
    # Deck 1: Study Setup
    # --------------------
    if deck == "🎛️ Study Setup & Run":
        st.subheader("🎛️ Deterministic Trade Study")

        ks = default_knob_sets()
        ks_names = [k.name for k in ks]
        sel = st.selectbox("Knob set", ks_names, index=0, key="ts_knob_set")
        ksel = next(k for k in ks if k.name == sel)
        st.caption(ksel.notes)

        n_samples = int(st.slider("Budget (samples)", min_value=20, max_value=2000, value=200, step=20, key="ts_budget"))
        seed = int(st.number_input("Seed", value=7, step=1, key="ts_seed"))

        obj_names, obj_senses = _objectives_catalog()
        default_obj = ["min_R0", "min_Bpeak", "max_Pnet"]
        default_obj = [o for o in default_obj if o in obj_names]
        chosen = st.multiselect(
            "Objectives (Pareto mapping over feasible points)",
            obj_names,
            default=default_obj,
            max_selections=4,
            key="ts_objectives",
        )
        if not chosen:
            st.warning("Select at least one objective.")
            return
        senses = {o: str(obj_senses.get(o, "min")) for o in chosen}

        # Optional lane evaluation of the resulting Pareto set
        lane = st.selectbox(
            "Contract lane for post-run classification",
            ["Nominal only", "Optimistic vs Robust"],
            index=1,
            key="ts_lane_mode",
        )

        if st.button("Run trade study", key="ts_run"):
            rep = run_trade_study(
                evaluator=ev,
                base_inputs=base,
                bounds=ksel.bounds,
                objectives=list(chosen),
                objective_senses=senses,
                n_samples=n_samples,
                seed=seed,
                include_outputs=False,
            )
            # Attach family labels (narrative only)
            rep["records"] = attach_families(rep.get("records", []) or [])
            rep["feasible"] = attach_families(rep.get("feasible", []) or [])
            rep["pareto"] = attach_families(rep.get("pareto", []) or [])
            st.session_state["ts_last"] = rep
            st.session_state["ts_last_lane"] = str(lane)

            # Publish a Study Capsule for cross-panel interoperability (Pareto Lab, Compare, export).
            try:
                meta = rep.get("meta", {}) or {}
                cap_payload = {
                    "schema": "shams.study_capsule.v1",
                    "created_ts": float(time.time()),
                    "meta": dict(meta),
                    "knob_set": {"name": str(ksel.name), "bounds": dict(ksel.bounds)},
                    "objectives": list(chosen),
                    "objective_senses": dict(senses),
                    "base_inputs": asdict(base),
                    "records": rep.get("records", []) or [],
                    "feasible": rep.get("feasible", []) or [],
                    "pareto": rep.get("pareto", []) or [],
                    "lane_mode": str(lane),
                }
                _h = hashlib.sha256(json.dumps({"meta": meta, "knobs": ksel.name, "seed": seed, "n": n_samples, "obj": list(chosen), "senses": senses}, sort_keys=True).encode("utf-8")).hexdigest()
                cap_payload["id"] = _h[:12]
                st.session_state["active_study_capsule"] = cap_payload
            except Exception:
                pass

        rep = st.session_state.get("ts_last")
        if rep is None:
            st.info("Run a trade study to populate results.")
            return

        meta = rep.get("meta", {})
        st.markdown(f"**Study:** N={meta.get('n_samples')}  seed={meta.get('seed')}  objectives={meta.get('objectives')}")

        df_all = pd.DataFrame(rep.get("records", []) or [])
        df_feas = pd.DataFrame(rep.get("feasible", []) or [])
        df_pareto = pd.DataFrame(rep.get("pareto", []) or [])

        if maybe_add_dsg_node_id_column is not None:
            df_all = maybe_add_dsg_node_id_column(df_all)
        render_dataframe_with_selection(df=df_all, key="trade_table_1", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True, "table_title": "All samples"})

        # v327.9: One-click DSG linking from table selection
        try:
            from ui.dsg_actions import link_selected_to_parent as _link_selected
        except Exception:
            try:
                from .dsg_actions import link_selected_to_parent as _link_selected
            except Exception:
                _link_selected = None
        sel_ids = st.session_state.get("trade_selected_dsg_node_ids") or []
        if _link_selected is not None and isinstance(sel_ids, list) and len(sel_ids) > 0:
            if st.button("Link selected ➜ active parent (DSG) — All samples", use_container_width=True, key="trade_link_tbl1"):
                n = _link_selected(selected_node_ids=sel_ids, kind="trade_select", note="UI: Trade table selection")
                if n > 0:
                    st.success(f"Linked {n} selected node(s) to active parent.")
                else:
                    st.info("No DSG edges were added.")

        if maybe_add_dsg_node_id_column is not None:
            df_feas = maybe_add_dsg_node_id_column(df_feas)
        render_dataframe_with_selection(df=df_feas, key="trade_table_2", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True, "table_title": "Feasible samples"})

        # v327.9: One-click DSG linking from table selection
        try:
            from ui.dsg_actions import link_selected_to_parent as _link_selected
        except Exception:
            try:
                from .dsg_actions import link_selected_to_parent as _link_selected
            except Exception:
                _link_selected = None
        sel_ids = st.session_state.get("trade_selected_dsg_node_ids") or []
        if _link_selected is not None and isinstance(sel_ids, list) and len(sel_ids) > 0:
            if st.button("Link selected ➜ active parent (DSG) — Feasible samples", use_container_width=True, key="trade_link_tbl2"):
                n = _link_selected(selected_node_ids=sel_ids, kind="trade_select", note="UI: Trade table selection")
                if n > 0:
                    st.success(f"Linked {n} selected node(s) to active parent.")
                else:
                    st.info("No DSG edges were added.")

        if maybe_add_dsg_node_id_column is not None:
            df_pareto = maybe_add_dsg_node_id_column(df_pareto)
        render_dataframe_with_selection(df=df_pareto, key="trade_table_3", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True, "table_title": "Feasible Pareto subset"})

        # v327.9: One-click DSG linking from table selection
        try:
            from ui.dsg_actions import link_selected_to_parent as _link_selected
        except Exception:
            try:
                from .dsg_actions import link_selected_to_parent as _link_selected
            except Exception:
                _link_selected = None
        sel_ids = st.session_state.get("trade_selected_dsg_node_ids") or []
        if _link_selected is not None and isinstance(sel_ids, list) and len(sel_ids) > 0:
            if st.button("Link selected ➜ active parent (DSG) — Feasible Pareto subset", use_container_width=True, key="trade_link_tbl3"):
                n = _link_selected(selected_node_ids=sel_ids, kind="trade_select", note="UI: Trade table selection")
                if n > 0:
                    st.success(f"Linked {n} selected node(s) to active parent.")
                else:
                    st.info("No DSG edges were added.")


        # Promote a selected Pareto point into Point Designer workspace
        if not df_pareto.empty:
            st.markdown("#### Promote a Pareto design to Point Designer")
            try:
                sel_i = st.selectbox("Select Pareto point index i", options=[int(x) for x in df_pareto["i"].tolist()] if "i" in df_pareto.columns else list(range(len(df_pareto))), key="ts_promote_i")
                if st.button("Promote to 🧭 Point Designer", use_container_width=True, key="ts_promote_btn"):
                    # reconstruct candidate dict from base + knob keys
                    dd = asdict(base)
                    row = df_pareto.iloc[int(df_pareto.index[df_pareto["i"] == sel_i][0])] if ("i" in df_pareto.columns) else df_pareto.iloc[int(sel_i)]
                    for k in ksel.bounds.keys():
                        if k in row:
                            try:
                                dd[k] = float(row[k])
                            except Exception:
                                pass
                    if _stage_pd is not None:
                        _stage_pd(dict(dd), source="🧪 Trade Study Studio", note="Promoted selected trade-study row")
                    else:
                        st.session_state["pd_candidate_apply"] = dict(dd)

                    # --- v327.3: DSG pipeline capture for Trade promotions (no truth evaluation) ---
                    try:
                        from evaluator.cache_key import canonical_json
                        import hashlib
                        _parent = st.session_state.get("dsg_selected_node_id") or st.session_state.get("active_design_node_id")
                        _inp_json = canonical_json(dict(dd))
                        _nid = hashlib.sha256(_inp_json.encode("utf-8")).hexdigest()
                        st.session_state["trade_last_parent_node_id"] = str(_parent) if _parent else ""
                        st.session_state["trade_last_node_ids"] = [_nid]
                    except Exception:
                        pass
                    from datetime import datetime
                    st.session_state["last_promotion_event"] = {
                        "source": "🧪 Trade Study Studio / Pareto Promote",
                        "note": "Selected Pareto design",
                        "ts": datetime.now().isoformat(timespec="seconds"),
                    }
                    st.session_state["pd_needs_sync"] = True
                    st.success("Promoted. Open 🧭 Point Designer to evaluate the point.")
            except Exception as e:
                st.warning(f"Promote failed: {e}")

        # Family summary
        fam = family_summary(rep.get("records", []) or [])
        if maybe_add_dsg_node_id_column is not None:
            pd = maybe_add_dsg_node_id_column(pd)
        render_dataframe_with_selection(df=pd.DataFrame(fam.get("rows", []) or []), key="trade_table_4", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True, "table_title": "Design family summary"})

        # Lane classification for Pareto points
        if st.session_state.get("ts_last_lane") == "Optimistic vs Robust" and not df_pareto.empty:
            st.subheader("⚡ Two-lane classification (Pareto points)")
            rows = []
            for _, r in df_pareto.iterrows():
                # Build PointInputs with sampled knobs only (best-effort)
                dd = asdict(base)
                for k in ksel.bounds.keys():
                    if k in r:
                        try:
                            dd[k] = float(r[k])
                        except Exception:
                            pass
                inp = PointInputs(**dd)

                uqO = run_uncertainty_contract_for_point(inp, optimistic_uncertainty_contract(inp), label_prefix="laneO")
                uqR = run_uncertainty_contract_for_point(inp, robust_uncertainty_contract(inp), label_prefix="laneR")
                sO = dict(uqO.get("summary", {}) or {})
                sR = dict(uqR.get("summary", {}) or {})
                vO = str(sO.get("verdict", ""))
                vR = str(sR.get("verdict", ""))
                cls = "ROBUST" if vR == "ROBUST_PASS" else ("MIRAGE" if vO == "ROBUST_PASS" else "FAIL")
                rows.append({
                    "i": int(r.get("i", -1)),
                    "family": str(r.get("family", "")),
                    "laneO": vO,
                    "laneR": vR,
                    "class": cls,
                    "laneO_worst_margin_frac": float(sO.get("worst_hard_margin_frac", float("nan")) or float("nan")),
                    "laneR_worst_margin_frac": float(sR.get("worst_hard_margin_frac", float("nan")) or float("nan")),
                })
            if maybe_add_dsg_node_id_column is not None:
                pd = maybe_add_dsg_node_id_column(pd)
            render_dataframe_with_selection(df=pd.DataFrame(rows), key="trade_table_5", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True, "table_title": "Lane-O vs Lane-R verdicts"})

    # -------------------------------------------
    # Deck: Feasible-First Surrogate Acceleration
    # -------------------------------------------
    elif deck == "⚡ Feasible-First Surrogate Accelerator":
        st.subheader("⚡ Feasible-First Surrogate Accelerator")
        st.caption(
            "Non-authoritative speed layer: trains a deterministic surrogate on verified study rows, "
            "proposes candidates predicted feasible + improving, then re-verifies with frozen truth."
        )

        rep = st.session_state.get("ts_last")
        if rep is None:
            st.info("Run a trade study first (Study Setup & Run) to generate training rows.")
            return

        # Resolve active knob-set bounds from the last study capsule (preferred) or UI selection.
        cap = st.session_state.get("active_study_capsule", None)
        if isinstance(cap, dict) and isinstance(cap.get("knob_set", None), dict):
            bounds = dict((cap["knob_set"].get("bounds") or {}) )
            knob_name = str((cap["knob_set"].get("name") or ""))
            objectives = list(cap.get("objectives") or [])
            senses = dict(cap.get("objective_senses") or {})
        else:
            ks = default_knob_sets()
            ks_names = [k.name for k in ks]
            sel = st.selectbox("Knob set (fallback)", ks_names, index=0, key="ts_sa_knob_set")
            ksel = next(k for k in ks if k.name == sel)
            bounds = dict(ksel.bounds)
            knob_name = str(ksel.name)
            objectives, senses = _objectives_catalog()
            senses = {o: str(senses[o]) for o in objectives}

        if not bounds:
            st.error("No knob bounds available for surrogate acceleration.")
            return

        records = rep.get("records", []) or []
        n_total = len(records)
        n_feas = len([r for r in records if bool(r.get("is_feasible", False))])
        st.markdown(f"**Training rows:** {n_total} (feasible: {n_feas})  •  **Knob set:** `{knob_name}`")

        # Choose a primary objective for acquisition.
        obj_names, obj_senses = _objectives_catalog()
        obj_default = None
        for cand in ["max_Pnet", "min_R0", "min_Bpeak", "min_COE"]:
            if cand in obj_names:
                obj_default = cand
                break
        primary_obj = st.selectbox("Primary acquisition objective", obj_names, index=obj_names.index(obj_default) if obj_default in obj_names else 0, key="ts_sa_obj")
        primary_sense = str(obj_senses.get(primary_obj, "min"))
        st.caption(f"Objective sense: **{primary_sense}**")

        n_pool = int(st.slider("Candidate pool size", min_value=200, max_value=20000, value=4000, step=200, key="ts_sa_pool"))
        n_prop = int(st.slider("Batch proposals", min_value=4, max_value=200, value=24, step=4, key="ts_sa_prop"))
        seed = int(st.number_input("Seed", value=17, step=1, key="ts_sa_seed"))
        kappa = float(st.slider("Uncertainty weight (kappa)", min_value=0.0, max_value=3.0, value=0.5, step=0.1, key="ts_sa_kappa"))

        from extopt.surrogate_accel import propose_candidates, verify_candidates_as_rows

        if st.button("Propose candidates (surrogate)", use_container_width=True, key="ts_sa_propose"):
            try:
                cand = propose_candidates(
                    records=records,
                    bounds=bounds,
                    objective_key=str(primary_obj),
                    objective_sense=str(primary_sense),
                    n_pool=int(n_pool),
                    n_propose=int(n_prop),
                    seed=int(seed),
                    kappa=float(kappa),
                )
                st.session_state["ts_sa_candidates"] = cand
            except Exception as e:
                st.error(f"Surrogate proposal failed: {e}")

        cand = st.session_state.get("ts_sa_candidates", None)
        if not cand:
            st.info("Propose a batch to continue.")
            return

        if maybe_add_dsg_node_id_column is not None:
            pd = maybe_add_dsg_node_id_column(pd)
        render_dataframe_with_selection(df=pd.DataFrame(list(cand)), key="trade_table_6", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True, "table_title": "Proposed knob candidates (unverified)"})

        if st.button("Verify proposed candidates (truth)", use_container_width=True, key="ts_sa_verify"):
            try:
                # verify using the same objective list used by the study if possible
                study_obj = (cap.get("objectives") or []) if isinstance(cap, dict) else (rep.get("meta", {}).get("objectives") or [])
                study_senses = (cap.get("objective_senses") or {}) if isinstance(cap, dict) else (rep.get("meta", {}).get("objective_senses") or {})
                vrows = verify_candidates_as_rows(
                    evaluator=ev,
                    base_inputs=base,
                    candidates=cand,
                    objectives=list(study_obj) if study_obj else [str(primary_obj)],
                    objective_senses=dict(study_senses) if study_senses else {str(primary_obj): str(primary_sense)},
                    include_outputs=False,
                )
                st.session_state["ts_sa_verified_rows"] = vrows
            except Exception as e:
                st.error(f"Truth verification failed: {e}")

        vrows = st.session_state.get("ts_sa_verified_rows", None)
        if not vrows:
            return

        dfv = pd.DataFrame(vrows)
        if maybe_add_dsg_node_id_column is not None:
            dfv = maybe_add_dsg_node_id_column(dfv)
        render_dataframe_with_selection(df=dfv, key="trade_table_7", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True, "table_title": "Verified candidates (frozen truth)"})

        # Append verified rows into the active study capsule for cross-panel use
        if st.button("Append verified rows to active Study Capsule", use_container_width=True, key="ts_sa_append"):
            if isinstance(cap, dict):
                cap_rec = list(cap.get("records") or [])
                cap_rec.extend(vrows)
                cap["records"] = cap_rec
                # update feasible subset
                cap["feasible"] = [r for r in cap_rec if bool(r.get("is_feasible", False))]
                st.session_state["active_study_capsule"] = cap
                st.success("Appended to Study Capsule (records + feasible updated).")
            else:
                st.warning("No active Study Capsule found.")

        # Promote a verified point to Point Designer
        if not dfv.empty:
            st.markdown("#### Promote a verified point to Point Designer")
            i_sel = st.selectbox("Select verified row index i", options=[int(x) for x in dfv["i"].tolist()] if "i" in dfv.columns else list(range(len(dfv))), key="ts_sa_promote_i")
            if st.button("Promote selected verified point", use_container_width=True, key="ts_sa_promote"):
                # convert selected row back to point inputs via base+knobs
                dd = asdict(base)
                row = dfv.iloc[int(dfv.index[dfv["i"] == i_sel][0])] if ("i" in dfv.columns) else dfv.iloc[int(i_sel)]
                for k in bounds.keys():
                    if k in row:
                        try:
                            dd[k] = float(row[k])
                        except Exception:
                            pass
                st.session_state["pd_candidate_apply"] = dict(dd)
                st.session_state["last_promotion_event"] = {"source": "Trade Study Studio / Surrogate Accelerator", "ts": float(time.time())}
                st.success("Promoted candidate to Point Designer workspace.")

    # --------------------
    # Deck 2: Optimizer Kits
    # --------------------
    elif deck == "🧰 Optimizer Kits (External)":
        st.subheader("🧰 Firewalled Optimizer Kits")
        st.caption("These kits run as external processes and emit evidence packs under runs/optimizer_kits/.")
        st.info(
            "Note: these are proposal generators. SHAMS re-verifies every candidate against frozen truth."
        )

        kit = st.selectbox(
            "Kit",
            [
                "NSGA-II-lite (multi-objective batch)",
                "CMA-ES-lite (continuous, feasible-only)",
                "BO-lite (surrogate-guided feasible-only)",
            ],
            key="ts_kit",
        )
        seed = int(st.number_input("Seed", value=11, step=1, key="ts_kit_seed"))
        n = int(st.slider("Budget (truth calls)", min_value=100, max_value=5000, value=800, step=100, key="ts_kit_budget"))

        obj_names, obj_senses = _objectives_catalog()
        chosen = st.multiselect(
            "Objectives (used by kit)",
            obj_names,
            default=[o for o in ("min_R0", "min_Bpeak", "max_Pnet") if o in obj_names],
            max_selections=4,
            key="ts_kit_objectives",
        )
        if not chosen:
            st.warning("Select at least one objective.")
            return

        # Bounds via knob sets
        ks = default_knob_sets()
        sel = st.selectbox("Knob bounds", [k.name for k in ks], index=0, key="ts_kit_knobs")
        ksel = next(k for k in ks if k.name == sel)

        # Write config into pending area and launch script
        pending = repo_root / "runs" / "pending"
        pending.mkdir(parents=True, exist_ok=True)
        cfg_path = pending / f"optimizer_kit_{seed}_{n}.json"

        if st.button("Launch kit", key="ts_kit_launch"):
            cfg = {
                "schema": "optimizer_kit.v1",
                "kit": str(kit),
                "seed": int(seed),
                "n": int(n),
                "objectives": list(chosen),
                "objective_senses": {o: str(obj_senses.get(o, "min")) for o in chosen},
                "bounds": {k: [float(v[0]), float(v[1])] for k, v in ksel.bounds.items()},
                "base_inputs": asdict(base),
            }
            import json
            cfg_path.write_text(json.dumps(cfg, indent=2, sort_keys=True), encoding="utf-8")
            st.success(f"Wrote config: {cfg_path.relative_to(repo_root)}")

            # Launch external runner (subprocess)
            import subprocess
            script = repo_root / "clients" / "optimizer_kits" / "run_kit.py"
            cmd = [
                "python",
                str(script),
                "--repo-root",
                str(repo_root),
                "--config",
                str(cfg_path),
            ]
            proc = subprocess.Popen(cmd, cwd=str(repo_root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            st.session_state["ts_kit_proc"] = proc
            st.session_state["ts_kit_log"] = ""
            from datetime import datetime
            st.session_state["active_extopt_run"] = {
                "kit": str(kit),
                "run_id": "",
                "config": str(cfg_path.relative_to(repo_root)) if cfg_path.exists() else str(cfg_path),
                "status": "RUNNING",
                "ts": datetime.now().isoformat(timespec="seconds"),
            }

        # Stream logs if running
        proc = st.session_state.get("ts_kit_proc", None)
        if proc is not None:
            try:
                out = proc.stdout.readline() if proc.stdout is not None else ""
                if out:
                    st.session_state["ts_kit_log"] = (st.session_state.get("ts_kit_log", "") + out)[-8000:]
            except Exception:
                pass
            st.text_area("Kit log (tail)", value=st.session_state.get("ts_kit_log", ""), height=220)
            if proc.poll() is not None:
                st.success(f"Kit finished with code {proc.returncode}")
                st.session_state["ts_kit_proc"] = None
                try:
                    from datetime import datetime
                    ext = st.session_state.get("active_extopt_run")
                    if isinstance(ext, dict):
                        ext["status"] = f"FINISHED({proc.returncode})"
                        ext["ts"] = datetime.now().isoformat(timespec="seconds")
                        # Best-effort attach newest run directory name.
                        runs_dir = repo_root / "runs" / "optimizer_kits"
                        if runs_dir.exists():
                            runs = sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.name, reverse=True)
                            if runs:
                                ext["run_id"] = str(runs[0].name)
                        st.session_state["active_extopt_run"] = ext
                except Exception:
                    pass

        # Show latest kit runs
        runs_dir = repo_root / "runs" / "optimizer_kits"
        if runs_dir.exists():
            runs = sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.name, reverse=True)
            if runs:
                if maybe_add_dsg_node_id_column is not None:
                    pd = maybe_add_dsg_node_id_column(pd)
                render_dataframe_with_selection(df=pd.DataFrame([{"run": r.name, "path": str(r)} for r in runs[:30]]), key="trade_table_8", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True, "table_title": "Recent kit runs"})

    # --------------------
    # Deck 3: Two-Lane
    # --------------------
    elif deck == "⚡ Fast Optimistic Design (Two-Lane)":
        st.subheader("⚡ Fast Optimistic Design")
        st.caption("Evaluate a point under explicit Optimistic vs Robust lanes (UQ-lite).")

        if st.button("Evaluate current point (lane O & R)", key="lane_eval"):
            uqO = run_uncertainty_contract_for_point(base, optimistic_uncertainty_contract(base), label_prefix="laneO")
            uqR = run_uncertainty_contract_for_point(base, robust_uncertainty_contract(base), label_prefix="laneR")
            st.session_state["lane_last"] = {"O": uqO, "R": uqR}

        lr = st.session_state.get("lane_last", None)
        if lr is None:
            st.info("Click evaluate to produce lane verdicts.")
            return
        sO = dict(lr["O"].get("summary", {}) or {})
        sR = dict(lr["R"].get("summary", {}) or {})
        vO = str(sO.get("verdict", ""))
        vR = str(sR.get("verdict", ""))
        cls = "ROBUST" if vR == "ROBUST_PASS" else ("MIRAGE" if vO == "ROBUST_PASS" else "FAIL")

        st.markdown(f"**Lane-O:** `{vO}`   **Lane-R:** `{vR}`   **Class:** **{cls}**")
        if maybe_add_dsg_node_id_column is not None:
            pd = maybe_add_dsg_node_id_column(pd)
        render_dataframe_with_selection(df=pd.DataFrame([sO]), key="trade_table_9", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True, "table_title": "Lane-O summary"})
        if maybe_add_dsg_node_id_column is not None:
            pd = maybe_add_dsg_node_id_column(pd)
        render_dataframe_with_selection(df=pd.DataFrame([sR]), key="trade_table_10", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True, "table_title": "Lane-R summary"})

    # --------------------
    # Deck 4: Design Families
    # --------------------
    elif deck == "🧬 Design Family Atlas":
        st.subheader("🧬 Design Family Atlas")
        st.caption("Family labels are deterministic narrative buckets over candidate sets.")

        rep = st.session_state.get("ts_last")
        if rep is None:
            st.info("Run a trade study first (Study Setup & Run).")
            return
        df = pd.DataFrame(rep.get("records", []) or [])
        if df.empty:
            st.warning("No records available.")
            return
        if maybe_add_dsg_node_id_column is not None:
            df = maybe_add_dsg_node_id_column(df)
        render_dataframe_with_selection(df=df, key="trade_table_11", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True, "table_title": "Records with family labels"})
        fam = family_summary(rep.get("records", []) or [])
        if maybe_add_dsg_node_id_column is not None:
            pd = maybe_add_dsg_node_id_column(pd)
        render_dataframe_with_selection(df=pd.DataFrame(fam.get("rows", []) or []), key="trade_table_12", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True, "table_title": "Family summary"})
        with st.expander("Family definitions", expanded=False):
            if maybe_add_dsg_node_id_column is not None:
                pd = maybe_add_dsg_node_id_column(pd)
            render_dataframe_with_selection(df=pd.DataFrame([{"family": f.key, "title": f.title, "notes": f.notes} for f in FAMILIES]), key="trade_table_13", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True})

    # --------------------
    # Deck 5: Regime Maps & Narratives (v324)
    # --------------------
    elif deck == "🗺️ Regime Maps & Narratives (v324)":
        from tools.regime_maps import build_regime_maps_report, select_default_features

        st.subheader("🗺️ Regime Maps & Narratives")
        st.caption("Deterministic clustering of feasible designs into families + mechanism-driven regime labels.")

        rep = st.session_state.get("ts_last")
        if rep is None:
            st.info("Run a trade study first (Study Setup & Run).")
            return

        recs = list(rep.get("records", []) or [])
        if not recs:
            st.warning("No records available.")
            return

        feas = [r for r in recs if isinstance(r, dict) and bool(r.get("is_feasible"))]
        st.write({"n_records": len(recs), "n_feasible": len(feas)})
        if not feas:
            st.info("No feasible points to cluster. Adjust bounds/seed and rerun.")
            return

        # Feature selection controls
        default_feats = select_default_features(feas, max_features=6)
        feats = st.multiselect(
            "Clustering features (numeric)",
            options=sorted({k for r in feas[:80] for k, v in (r.items() if isinstance(r, dict) else []) if isinstance(k, str)}),
            default=default_feats,
            key="v324_feats",
        )
        min_cluster = int(st.slider("Min cluster size", 3, 30, 6, 1, key="v324_min_cluster"))
        max_bins = int(st.slider("Bins per feature", 6, 24, 12, 1, key="v324_bins"))

        if st.button("Build regime map report", key="v324_run"):
            try:
                rpt = build_regime_maps_report(
                    records=recs,
                    features=feats,
                    min_cluster_size=min_cluster,
                    max_bins=max_bins,
                )
                st.session_state["v324_regime_maps"] = rpt
                st.success(f"Built regime report with {len(rpt.get('clusters', []) or [])} clusters.")
            except Exception as e:
                st.error(f"v324 failed: {e!r}")

        rpt = st.session_state.get("v324_regime_maps")
        if not isinstance(rpt, dict):
            st.info("Click 'Build regime map report'.")
            return

        clusters = list(rpt.get("clusters", []) or [])
        if not clusters:
            st.warning(rpt.get("error") or "No clusters produced.")
            return

        # Summary table
        rows = []
        for c in clusters:
            if not isinstance(c, dict):
                continue
            auth = c.get("authority") or {}
            rows.append(
                {
                    "cluster_id": c.get("cluster_id"),
                    "n": c.get("n"),
                    "regime": c.get("regime_label"),
                    "dominant_constraint": c.get("dominant_constraint"),
                    "mechanism_group": c.get("dominant_mechanism_group"),
                    "authority_tier": auth.get("authority_tier"),
                    "subsystem": auth.get("subsystem"),
                    "min_margin_frac": (c.get("margin") or {}).get("min_margin_frac"),
                    "median_margin_frac": (c.get("margin") or {}).get("median_margin_frac"),
                }
            )
        if maybe_add_dsg_node_id_column is not None:
            pd = maybe_add_dsg_node_id_column(pd)
        render_dataframe_with_selection(df=pd.DataFrame(rows), key="trade_table_14", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True, "table_title": "Regime clusters"})

        # Narrative blocks
        with st.expander("Narratives (per cluster)", expanded=False):
            for c in clusters:
                st.markdown(f"**Cluster {c.get('cluster_id')} — {c.get('regime_label')}**")
                st.write(c.get("narrative"))
                fs = c.get("feature_stats") or {}
                if isinstance(fs, dict) and fs:
                    render_dataframe_with_selection(df=pd.DataFrame(
                            [
                                {"feature": k, **(v if isinstance(v, dict) else {})}
                                for k, v in fs.items()
                                if isinstance(k, str)
                            ]
                        ), key="trade_table_15", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True, "table_title": f"Cluster {c.get('cluster_id')} feature ranges"})
                st.markdown("---")

        # Regime map scatter
        num_cols = [k for k in (rpt.get("features") or []) if isinstance(k, str)]
        if len(num_cols) >= 2:
            x = st.selectbox("X", options=num_cols, index=0, key="v324_x")
            y = st.selectbox("Y", options=num_cols, index=1, key="v324_y")
            try:
                import plotly.express as px

                df = pd.DataFrame(feas)
                # map by record 'i' if present
                id_to_regime = {a.get("i"): a.get("regime_label") for a in (rpt.get("assignments") or []) if isinstance(a, dict)}
                if "i" in df.columns:
                    df["regime_label"] = df["i"].map(id_to_regime)
                else:
                    df["regime_label"] = None
                fig = px.scatter(df, x=x, y=y, color="regime_label", hover_data=["min_margin_frac", "dominant_constraint"])
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.info(f"Plotly scatter unavailable: {e!r}")

        st.download_button(
            "Download regime_maps_report.json",
            data=json.dumps(rpt, indent=2, sort_keys=True),
            file_name="regime_maps_report.json",
            mime="application/json",
            use_container_width=True,
            key="v324_dl",
        )

    # --------------------
    # Deck 6: Mirage Pathfinding
    # --------------------
    elif deck == "🧭 Mirage Pathfinding":
        st.subheader("🧭 Mirage Pathfinding")
        st.caption("Deterministic one-knob scans to map optimistic→robust feasibility paths.")

        st.info("Pathfinding runs UQ-lite Robust evaluations repeatedly. Use small budgets.")
        levers = default_pathfinding_levers(base)
        lever_names = [f"{k}: {lo:.3g} → {hi:.3g}" for (k, lo, hi) in levers]
        sel = st.selectbox("Improvement lever", lever_names, index=0, key="pf_lever")
        idx = lever_names.index(sel)
        knob, lo, hi = levers[idx]
        n = int(st.slider("Scan points", min_value=7, max_value=41, value=17, step=2, key="pf_n"))

        if st.button("Run path scan", key="pf_run"):
            rep = one_knob_path_scan(ev, base, knob, lo=lo, hi=hi, n=n)
            st.session_state["pf_last"] = rep

        rep = st.session_state.get("pf_last", None)
        if rep is None:
            st.info("Run a scan to view results.")
            return
        if maybe_add_dsg_node_id_column is not None:
            pd = maybe_add_dsg_node_id_column(pd)
        render_dataframe_with_selection(df=pd.DataFrame(rep.get("rows", []) or []), key="trade_table_16", store_key="trade_selected_dsg_node_ids", dataframe_kwargs={"use_container_width": True, "table_title": "Path scan"})
        st.write("First robust-pass:", rep.get("first_robust_pass"))
