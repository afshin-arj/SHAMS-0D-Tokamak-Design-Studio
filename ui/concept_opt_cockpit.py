"""Concept Optimization Cockpit (UI deck).

This deck provides a feasibility-first batch evaluation UI for concept families.

Import policy:
- This module must not execute Streamlit calls at import time.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
import yaml

from extopt import BatchEvalConfig, evaluate_concept_family, export_evidence_pack
from extopt.family import load_concept_family


@dataclass
class _CockpitRun:
    family_path: str
    run_unix: float
    summary: Dict[str, Any]
    table: pd.DataFrame
    artifacts: Dict[str, Dict[str, Any]]
    cache_hits: Dict[str, bool]


def _list_example_families(repo_root: Path) -> List[Path]:
    base = repo_root / "examples" / "concept_families"
    if not base.is_dir():
        return []
    out = []
    for p in sorted(base.glob("*.y*ml")):
        out.append(p)
    return out


def render_concept_optimization_cockpit(repo_root: Path) -> None:
    """Render the Concept Optimization Cockpit deck."""

    st.markdown("### 📈 Concept Optimization Cockpit — Feasibility Oracle")
    st.caption(
        "Batch-evaluate concept families from YAML using the frozen evaluator. "
        "No internal optimization is performed; infeasibility is reported, not negotiated."
    )

    tab_setup, tab_results, tab_evidence = st.tabs(["🧬 Setup", "📊 Results", "📦 Evidence"])

    with tab_setup:
        c0, c1, c2 = st.columns([2, 1, 1])
        examples = _list_example_families(repo_root)
        ex_names = [p.name for p in examples]
        ex_sel = c0.selectbox(
            "Example family (optional)",
            options=["(none)"] + ex_names,
            index=0,
            help="Pick a shipped example YAML, or upload your own below.",
            key="concept_cockpit_example",
        )

        up = st.file_uploader(
            "Upload concept family YAML", type=["yaml", "yml"], key="concept_cockpit_upload"
        )

        cache_enabled = c1.checkbox(
            "Disk cache", value=True, help="Acceleration only (does not change results).", key="concept_cockpit_cache"
        )
        cache_dir = c2.text_input(
            "Cache folder", value=str(repo_root / ".shams_extopt_cache"), key="concept_cockpit_cache_dir"
        )

        run_btn = st.button("Run batch evaluation", type="primary", key="concept_cockpit_run")

        # Resolve YAML source
        family_path: Optional[Path] = None
        family_bytes: Optional[bytes] = None

        if up is not None:
            family_bytes = up.getvalue()
        elif ex_sel != "(none)":
            family_path = repo_root / "examples" / "concept_families" / ex_sel

        if run_btn:
            if family_bytes is None and family_path is None:
                st.error("Please select an example family or upload a YAML file.")
            else:
                # Materialize uploaded YAML to a deterministic run folder for provenance.
                out_root = repo_root / "ui_runs" / "concept_cockpit"
                out_root.mkdir(parents=True, exist_ok=True)
                run_tag = f"run_{int(time.time())}"
                run_dir = out_root / run_tag
                run_dir.mkdir(parents=True, exist_ok=True)

                if family_bytes is not None:
                    family_path = run_dir / f"uploaded_{int(time.time())}.yaml"
                    family_path.write_bytes(family_bytes)

                assert family_path is not None

                try:
                    fam = load_concept_family(family_path)
                except Exception as e:
                    st.error(f"Failed to load concept family: {e}")
                else:
                    cfg = BatchEvalConfig(
                        cache_enabled=bool(cache_enabled),
                        cache_dir=Path(cache_dir) if cache_enabled and cache_dir else None,
                    )
                    res = evaluate_concept_family(fam, config=cfg, repo_root=repo_root)

                    rows: List[Dict[str, Any]] = []
                    arts: Dict[str, Dict[str, Any]] = {}
                    hits: Dict[str, bool] = {}
                    for r in res.results:
                        art = r.artifact
                        arts[r.cid] = art
                        hits[r.cid] = bool(r.cache_hit)
                        out = art.get("outputs", {}) if isinstance(art.get("outputs"), dict) else {}
                        kpis = art.get("kpis", {}) if isinstance(art.get("kpis"), dict) else {}
                        rows.append(
                            {
                                "id": r.cid,
                                "verdict": art.get("verdict", ""),
                                "feasible_hard": bool(kpis.get("feasible_hard", False)),
                                "min_hard_margin": kpis.get("min_hard_margin"),
                                "dominant_mechanism": art.get("dominant_mechanism", ""),
                                "dominant_constraint": art.get("dominant_constraint", ""),
                                "Q_DT_eqv": out.get("Q_DT_eqv"),
                                "H98": out.get("H98"),
                                "beta_N": out.get("beta_N"),
                                "P_net_e_MW": out.get("P_net_e_MW"),
                                "cache_hit": bool(r.cache_hit),
                            }
                        )

                    df = pd.DataFrame(rows)
                    df = df.sort_values(by=["feasible_hard", "min_hard_margin"], ascending=[False, False], kind="mergesort")

                    st.session_state["concept_cockpit_last"] = _CockpitRun(
                        family_path=str(family_path),
                        run_unix=time.time(),
                        summary=res.summary,
                        table=df,
                        artifacts=arts,
                        cache_hits=hits,
                    )
                    st.success("Batch evaluation completed.")

        # Show resolved family preview
        if family_bytes is not None:
            try:
                d = yaml.safe_load(family_bytes.decode("utf-8"))
                st.caption("Uploaded YAML preview")
                st.json(d, expanded=False)
            except Exception:
                st.info("Uploaded YAML preview unavailable.")
        elif family_path is not None:
            st.caption(f"Selected example: {family_path.name}")

    with tab_results:
        run: Optional[_CockpitRun] = st.session_state.get("concept_cockpit_last")
        if run is None:
            st.info("Run a batch evaluation in the Setup tab.")
        else:
            s = run.summary
            cA, cB, cC, cD = st.columns(4)
            cA.metric("Total", s.get("n_total", "—"))
            cB.metric("Hard-feasible", s.get("n_feasible", "—"))
            try:
                cC.metric("PASS rate", f"{100*float(s.get('pass_rate',0.0)):.1f}%")
            except Exception:
                cC.metric("PASS rate", "—")
            # Dominant mechanism = most common label
            hist = s.get("dominant_mechanism_hist", {}) if isinstance(s.get("dominant_mechanism_hist"), dict) else {}
            top = "—"
            try:
                if hist:
                    top = max(hist.items(), key=lambda kv: kv[1])[0]
            except Exception:
                top = "—"
            cD.metric("Most common blocker", top)

            with st.container(border=True):
                st.markdown("**Candidate table**")
                st.dataframe(run.table, use_container_width=True, height=420)

            with st.expander("Dominant mechanism histogram", expanded=False):
                st.json(hist, expanded=False)

            with st.container(border=True):
                st.markdown("**Batch bundle export (single deterministic ZIP)**")
                st.caption(
                    "For external optimizers / reviewers: index + manifest + artifacts, optional evidence packs. "
                    "Pure I/O contract; does not affect frozen truth."
                )
                include_packs = st.toggle(
                    "Include evidence packs (only if already built)",
                    value=False,
                    key="concept_cockpit_bundle_include_packs",
                )
                if st.button("Build bundle ZIP", use_container_width=True, key="concept_cockpit_build_bundle"):
                    try:
                        try:
                            from src.extopt.bundle import (
                                BundleCandidate,
                                BundleProvenance,
                                export_bundle_zip_v273 as export_bundle_zip,
                            )
                        except Exception:
                            from extopt.bundle import BundleCandidate, BundleProvenance, export_bundle_zip  # type: ignore

                        try:
                            ver = (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip()
                        except Exception:
                            ver = "unknown"

                        cands = []
                        for cid2, art2 in (run.artifacts or {}).items():
                            cands.append(
                                BundleCandidate(
                                    cid=str(cid2),
                                    artifact=dict(art2) if isinstance(art2, dict) else {},
                                    cache_hit=bool(run.cache_hits.get(cid2, False)),
                                )
                            )
                        prov = BundleProvenance(
                            shams_version=str(ver),
                            evaluator_label=str(run.summary.get("evaluator_label", "hot_ion_point")),
                            intent=str(run.summary.get("intent", "")),
                            family_name=str(run.summary.get("family", "")),
                            family_source=str(run.family_path),
                        )

                        # Collect evidence packs if requested and available
                        ep = {}
                        if include_packs:
                            for cid2 in list((run.artifacts or {}).keys()):
                                man = st.session_state.get(f"concept_cockpit_pack_{cid2}")
                                if isinstance(man, dict) and man.get("out_zip"):
                                    p = Path(str(man["out_zip"]))
                                    if p.exists():
                                        ep[str(cid2)] = p

                        out_dir = Path("ui_runs") / "concept_cockpit" / "bundles"
                        out_dir.mkdir(parents=True, exist_ok=True)
                        out_zip = out_dir / "concept_family_bundle.zip"

                        # v273: attach problem spec + runspec to bundle (optimizer handoff contract)
                        try:
                            from clients.reference_optimizer import build_default_problem_spec

                            problem_spec = build_default_problem_spec(name=str(run.summary.get("family", "concept_family")))
                        except Exception:
                            problem_spec = {
                                "schema_version": "extopt.problem_spec.v1",
                                "name": str(run.summary.get("family", "concept_family")),
                                "variables": [],
                                "objectives": [],
                                "constraints": [],
                            }

                        runspec = {
                            "schema_version": "extopt.runspec.v1",
                            "producer": "concept_opt_cockpit",
                            "family_source": str(run.family_path),
                            "intent": str(run.summary.get("intent", "")),
                            "evaluator_label": str(run.summary.get("evaluator_label", "hot_ion_point")),
                        }

                        export_bundle_zip(
                            out_zip=out_zip,
                            candidates=cands,
                            provenance=prov,
                            include_artifact_json=True,
                            include_evidence_packs=bool(include_packs),
                            evidence_pack_paths=ep,
                            problem_spec_json=problem_spec,
                            runspec_json=runspec,
                        )
                        st.session_state["concept_cockpit_bundle_path"] = str(out_zip)
                        st.success("Bundle built.")
                    except Exception as e:
                        st.error(f"Bundle build failed: {e}")

    pth = st.session_state.get("concept_cockpit_bundle_path")
    if isinstance(pth, str) and pth:
        p = Path(pth)
        if p.exists():
            st.download_button(
                "Download batch bundle ZIP",
                data=p.read_bytes(),
                file_name=p.name,
                mime="application/zip",
                use_container_width=True,
                key="concept_cockpit_dl_bundle",
            )

    with tab_evidence:
        run: Optional[_CockpitRun] = st.session_state.get("concept_cockpit_last")
        if run is None:
            st.info("Run a batch evaluation first.")
        else:
            ids = list(run.artifacts.keys())
            if not ids:
                st.info("No artifacts available.")
            else:
                cid = st.selectbox("Candidate", options=ids, index=0, key="concept_cockpit_ev_sel")
                art = run.artifacts.get(cid, {})

                c1, c2, c3 = st.columns([1, 1, 2])
                c1.write(f"**Verdict:** {art.get('verdict','—')}")
                c2.write(f"**Cache hit:** {bool(run.cache_hits.get(cid, False))}")
                c3.write(f"**Dominant:** {art.get('dominant_mechanism','')} / {art.get('dominant_constraint','')}")

                # Downloads
                art_bytes = json.dumps(art, indent=2, sort_keys=True).encode("utf-8")
                st.download_button(
                    "Download artifact JSON",
                    data=art_bytes,
                    file_name=f"artifact_{cid}.json",
                    mime="application/json",
                    use_container_width=True,
                    key=f"concept_cockpit_dl_art_{cid}",
                )

                # Evidence pack generation on demand
                out_dir = repo_root / "ui_runs" / "concept_cockpit" / "evidence_packs"
                basename = f"evidence_{cid}"
                if st.button("Build evidence pack (zip)", key=f"concept_cockpit_build_pack_{cid}"):
                    try:
                        man = export_evidence_pack(art, out_dir, basename=basename)
                        st.session_state[f"concept_cockpit_pack_{cid}"] = man
                        st.success("Evidence pack built.")
                    except Exception as e:
                        st.error(f"Evidence pack build failed: {e}")

                man = st.session_state.get(f"concept_cockpit_pack_{cid}")
                if isinstance(man, dict) and man.get("out_zip"):
                    p = Path(man["out_zip"])
                    if p.exists():
                        st.download_button(
                            "Download evidence pack ZIP",
                            data=p.read_bytes(),
                            file_name=p.name,
                            mime="application/zip",
                            use_container_width=True,
                            key=f"concept_cockpit_dl_pack_{cid}",
                        )

                with st.expander("Constraint ledger (top blockers)", expanded=False):
                    led = art.get("constraint_ledger", {}) if isinstance(art.get("constraint_ledger"), dict) else {}
                    st.json(led.get("top_blockers", []), expanded=False)

                with st.expander("Full artifact (read-only)", expanded=False):
                    st.json(art, expanded=False)
