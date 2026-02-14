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
            "🗺️ Multi-Objective Feasible Frontier Atlas (v351)",
            "🧾 Robust Design Envelope Certification (v352)",
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

    # -----------------------------------------------
    # Deck 2: Multi-Objective Feasible Frontier Atlas
    # -----------------------------------------------
    if deck == "🗺️ Multi-Objective Feasible Frontier Atlas (v351)":
        st.subheader("🗺️ Multi-Objective Feasible Frontier Atlas (v351)")
        st.caption(
            "Descriptive atlas over evaluated points: feasible envelope, robust envelope, mirage set, and empty-region maps. "
            "No optimization is performed here."
        )

        with st.expander("Scope: what this deck does / does not do", expanded=False):
            st.markdown(
                """
**Does**
- Builds a deterministic atlas from an existing point set (trade study, external pack CSV).
- Extracts a feasible-only Pareto subset (multi-objective).
- Optionally classifies Pareto points under **Optimistic vs Robust** contract lanes.
- Produces empty-region maps via deterministic 2D binning.

**Does not**
- Run any internal optimizer.
- Modify frozen evaluator truth.
- Smooth, relax, or negotiate constraints.
"""
            )

        # Data source: prefer the active Study Capsule
        cap = st.session_state.get("active_study_capsule")
        df: Optional[pd.DataFrame] = None
        base_inputs: Optional[Dict[str, Any]] = None

        if isinstance(cap, dict) and (cap.get("records") is not None):
            df = pd.DataFrame(cap.get("records") or [])
            base_inputs = dict(cap.get("base_inputs") or {})
            st.success(f"Using active Study Capsule: id={cap.get('id','')}  N={len(df)}")
        else:
            st.info("No active Study Capsule found. Upload a CSV export to build an atlas.")
            up = st.file_uploader("Upload points CSV (trade study / candidate pack)", type=["csv"], key="v351_csv")
            if up is not None:
                try:
                    df = pd.read_csv(up)
                    st.success(f"Loaded CSV: N={len(df)}")
                except Exception as e:
                    st.error(f"Failed to read CSV: {e}")
                    return

        if df is None or len(df) == 0:
            st.info("Provide a point set to build an atlas.")
            return

        # Choose objectives present in dataframe
        obj_names, obj_senses = _objectives_catalog()
        cols = set(df.columns)
        obj_present = [o for o in obj_names if o in cols]
        if len(obj_present) == 0:
            st.warning("No known objective columns found in the dataset.")
            return

        chosen = st.multiselect(
            "Objectives (Pareto mapping over feasible points)",
            obj_present,
            default=obj_present[:2],
            max_selections=4,
            key="v351_objs",
        )
        if not chosen:
            st.warning("Select at least one objective.")
            return

        senses = {o: str(obj_senses.get(o, "min")) for o in chosen}

        # Filter feasible records (nominal)
        if "is_feasible" in df.columns:
            dfF = df[df["is_feasible"] == True].copy()  # noqa: E712
        else:
            dfF = df.copy()
        st.markdown(f"**Feasible set:** {len(dfF)} / {len(df)}")

        # Extract Pareto subset
        try:
            from atlas.frontier_atlas_v351 import pareto_front as _pareto_front  # type: ignore
        except Exception:
            try:
                from src.atlas.frontier_atlas_v351 import pareto_front as _pareto_front  # type: ignore
            except Exception:
                _pareto_front = None

        if _pareto_front is None:
            st.error("v351 atlas module failed to import.")
            return

        pareto_rows = _pareto_front(dfF.to_dict(orient="records"), objectives=list(chosen), senses=senses)
        dfP = pd.DataFrame(pareto_rows)
        st.markdown(f"**Feasible Pareto subset:** {len(dfP)}")

        with st.expander("Table: Feasible Pareto subset", expanded=False):
            st.dataframe(dfP, use_container_width=True)

        # Optional lane classification (budgeted)
        if base_inputs is not None and len(dfP) > 0:
            st.divider()
            st.markdown("### Two-lane classification (Optimistic vs Robust)")
            nmax = int(st.slider("Classification budget (Pareto points)", 5, 200, min(50, len(dfP)), 5, key="v351_lane_budget"))
            if st.button("Classify Pareto points under lanes", use_container_width=True, key="v351_classify"):
                try:
                    from atlas.frontier_atlas_v351 import classify_lanes_for_points  # type: ignore
                except Exception:
                    from src.atlas.frontier_atlas_v351 import classify_lanes_for_points  # type: ignore

                rows_in = dfP.to_dict(orient="records")
                rows_out = classify_lanes_for_points(
                    evaluator=ev,
                    base_inputs=base_inputs,
                    rows=rows_in,
                    optimistic_contract_fn=optimistic_uncertainty_contract,
                    robust_contract_fn=robust_uncertainty_contract,
                    run_uq_fn=run_uncertainty_contract_for_point,
                    label_prefix="v351",
                    max_points=nmax,
                )
                dfL = pd.DataFrame(rows_out)
                st.session_state["v351_lane_df"] = dfL

        dfL = st.session_state.get("v351_lane_df")
        if isinstance(dfL, pd.DataFrame) and len(dfL) > 0:
            nrob = int((dfL.get("is_robust") == True).sum()) if "is_robust" in dfL.columns else 0  # noqa: E712
            nmir = int((dfL.get("is_mirage") == True).sum()) if "is_mirage" in dfL.columns else 0  # noqa: E712
            st.info(f"Lane results (budgeted): robust={nrob}  mirage={nmir}  total_classified={len(dfL)}")
            with st.expander("Table: Pareto subset with lane labels", expanded=False):
                st.dataframe(dfL, use_container_width=True)

        # Empty-region maps (binning)
        st.divider()
        st.markdown("### Empty-region map (2D binning)")
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if len(numeric_cols) < 2:
            st.warning("Need at least two numeric columns to build an empty-region map.")
            return

        xk = st.selectbox("X axis", numeric_cols, index=0, key="v351_xk")
        yk = st.selectbox("Y axis", numeric_cols, index=1, key="v351_yk")
        xb = int(st.slider("X bins", 4, 40, 12, 1, key="v351_xb"))
        yb = int(st.slider("Y bins", 4, 40, 12, 1, key="v351_yb"))

        try:
            from atlas.frontier_atlas_v351 import bin_counts  # type: ignore
        except Exception:
            from src.atlas.frontier_atlas_v351 import bin_counts  # type: ignore

        # Build three maps: feasible, robust (if available), mirage (if available)
        rows_all = df.to_dict(orient="records")
        rows_feas = dfF.to_dict(orient="records")
        map_feas = bin_counts(rows_feas, xk, yk, x_bins=xb, y_bins=yb)

        map_rob = None
        map_mir = None
        if isinstance(dfL, pd.DataFrame) and len(dfL) > 0:
            rows_l = dfL.to_dict(orient="records")
            map_rob = bin_counts(rows_l, xk, yk, x_bins=xb, y_bins=yb, predicate=lambda r: bool(r.get("is_robust", False)))
            map_mir = bin_counts(rows_l, xk, yk, x_bins=xb, y_bins=yb, predicate=lambda r: bool(r.get("is_mirage", False)))

        with st.expander("Empty-region report", expanded=False):
            st.json({
                "feasible": {"total_points": map_feas.get("total_points"), "empty_cells": map_feas.get("empty_cells")},
                "robust": None if map_rob is None else {"total_points": map_rob.get("total_points"), "empty_cells": map_rob.get("empty_cells")},
                "mirage": None if map_mir is None else {"total_points": map_mir.get("total_points"), "empty_cells": map_mir.get("empty_cells")},
                "axes": {"x": xk, "y": yk, "bins": {"x": xb, "y": yb}},
            }, expanded=False)

        # Provide downloadable atlas JSON
        try:
            import json
            payload = {
                "schema": "shams.frontier_atlas.v351",
                "objectives": list(chosen),
                "objective_senses": dict(senses),
                "counts": {
                    "n_total": int(len(df)),
                    "n_feasible": int(len(dfF)),
                    "n_pareto": int(len(dfP)),
                },
                "empty_region": {
                    "feasible": map_feas,
                    "robust": map_rob,
                    "mirage": map_mir,
                },
            }
            st.download_button(
                "Download v351 atlas JSON",
                data=json.dumps(payload, indent=2, sort_keys=True),
                file_name="shams_frontier_atlas_v351.json",
                mime="application/json",
                use_container_width=True,
            )
        except Exception:
            pass

        st.caption("v351 atlas deck is descriptive-only and does not push points back into truth. Promote designs via the Study Setup deck.")

    # -------------------------------------------
    # Deck: Feasible-First Surrogate Acceleration
    # -------------------------------------------
    

    # --------------------
    # Deck: v352 Robust Envelope Certification
    # --------------------
    elif deck == "🧾 Robust Design Envelope Certification (v352)":
        st.subheader("🧾 Robust Design Envelope Certification (v352)")
        st.caption(
            "Governance-grade certification of a candidate set under the ROBUST UQ-lite contract. "
            "Budgeted deterministic corner enumeration (no optimization; no truth modification)."
        )

        with st.expander("Scope: what this deck does / does not do", expanded=False):
            st.markdown(
                """
**Does**
- Certifies an explicit candidate set (Feasible / Pareto / Lane table) under the **Robust** interval contract.
- Enumerates **all corners** deterministically (2^N) and summarizes feasibility + worst margin.
- Assigns deterministic tiers (A/B/C) based on *worst hard margin fraction*.
- Produces a reviewer-safe evidence ZIP (report + optional corner artifacts).

**Does not**
- Optimize, tune, or search within truth.
- Use probability, Monte Carlo, or iterative solvers.
- Hide infeasibility or negotiate constraints.
"""
            )

        rep = st.session_state.get("ts_last")
        lane_df = st.session_state.get("v351_lane_df", None)

        if rep is None and lane_df is None:
            st.warning("No candidate set available yet. Run a Trade Study (or v351 lane classification) first.")
            return

        source = st.selectbox(
            "Candidate source",
            ["Trade Study: Feasible", "Trade Study: Pareto", "v351: Lane Table (Pareto+labels)"],
            index=1,
            key="v352_source",
        )

        rows: List[Dict[str, Any]] = []
        if source.startswith("Trade Study") and isinstance(rep, dict):
            key = "feasible" if "Feasible" in source else "pareto"
            rows = list(rep.get(key, []) or [])
        elif source.startswith("v351") and lane_df is not None:
            try:
                rows = lane_df.to_dict(orient="records")
            except Exception:
                rows = []

        if not rows:
            st.warning("Selected candidate source is empty.")
            return

        st.markdown(f"**Candidate rows available:** {len(rows)}")

        max_points = int(st.slider("Certification budget (points)", 1, min(100, len(rows)), min(20, len(rows)), 1, key="v352_budget"))
        include_corners = bool(st.checkbox("Include corner artifacts in evidence ZIP (can be large)", value=False, key="v352_include_corners"))

        # Tier thresholds (deterministic policy)
        st.markdown("### Tier thresholds (worst hard margin fraction)")
        colA, colB, colC = st.columns(3)
        with colA:
            tA = float(st.number_input("Tier A min", min_value=0.0, max_value=1.0, value=0.10, step=0.01, key="v352_tA"))
        with colB:
            tB = float(st.number_input("Tier B min", min_value=0.0, max_value=1.0, value=0.03, step=0.01, key="v352_tB"))
        with colC:
            tC = float(st.number_input("Tier C min", min_value=-1.0, max_value=1.0, value=0.00, step=0.01, key="v352_tC"))

        if tA < tB or tB < tC:
            st.error("Thresholds must satisfy Tier A ≥ Tier B ≥ Tier C.")
            return

        if st.button("Run Robust Envelope Certification", use_container_width=True, key="v352_run"):
            try:
                from certification.robust_envelope_v352 import TierThresholds, certify_points_under_contract, build_certification_evidence_zip  # type: ignore
            except Exception:
                from src.certification.robust_envelope_v352 import TierThresholds, certify_points_under_contract, build_certification_evidence_zip  # type: ignore

            base_inputs = _ss_get_point(st)
            base_d = asdict(base_inputs)

            pts: List[PointInputs] = []
            for r in rows[:max_points]:
                d = dict(base_d)
                # apply overrides for any PointInputs field present in row
                for k, v in (r or {}).items():
                    if k in d:
                        try:
                            d[k] = float(v)
                        except Exception:
                            pass
                pts.append(PointInputs(**d))

            spec = robust_uncertainty_contract(base_inputs).to_dict()
            cert = certify_points_under_contract(
                points=pts,
                contract_spec=spec,
                run_uq_fn=run_uncertainty_contract_for_point,
                thresholds=TierThresholds(tier_A_min=tA, tier_B_min=tB, tier_C_min=tC),
                label_prefix="v352",
                max_points=max_points,
            )
            st.session_state["v352_cert"] = cert

            rep0 = cert.get("report", {})
            counts = rep0.get("counts", {}) if isinstance(rep0, dict) else {}
            st.success(
                f"Certification complete. certified={counts.get('n_certified')}  "
                f"robust={counts.get('n_robust')}  fragile={counts.get('n_fragile')}  fail={counts.get('n_fail')}"
            )

            # Build ZIP for download
            zbytes = build_certification_evidence_zip(certification=cert, include_corners=include_corners)
            st.session_state["v352_zip_bytes"] = zbytes

        cert = st.session_state.get("v352_cert")
        if isinstance(cert, dict) and isinstance(cert.get("report"), dict):
            rep0 = cert["report"]
            with st.expander("Report: robust envelope certification", expanded=False):
                st.json(rep0)

            # Table view
            try:
                import pandas as _pd  # type: ignore
                dfR = _pd.DataFrame(rep0.get("rows", []) or [])
                if len(dfR) > 0:
                    # flatten a few helpful columns
                    show_cols = [c for c in ["index", "verdict", "tier", "worst_hard_margin_frac", "n_corners", "n_feasible", "worst_corner_index"] if c in dfR.columns]
                    with st.expander("Table: per-point certification summary", expanded=False):
                        st.dataframe(dfR[show_cols], use_container_width=True)
            except Exception:
                pass

            zbytes = st.session_state.get("v352_zip_bytes")
            if isinstance(zbytes, (bytes, bytearray)) and len(zbytes) > 0:
                st.download_button(
                    "⬇️ Download v352 evidence ZIP",
                    data=bytes(zbytes),
                    file_name="v352_robust_envelope_evidence.zip",
                    mime="application/zip",
                    use_container_width=True,
                    key="v352_dl",
                )

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