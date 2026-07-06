"""Pareto Lab external optimizer decks — Phase 17."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.components.proposal_banner import render_proposal_banner
from ui_nicegui.lib.external_optimizer_helpers import (
    atlas_evidence_zip,
    build_design_families,
    build_regime_atlas,
    candidate_sources,
    evaluate_concept_family_yaml,
    interpret_optimizer_trace,
    list_concept_family_yamls,
    list_optimizer_run_dirs,
    load_phase_defaults,
    load_records_from_upload,
    load_uq_defaults,
    read_run_json,
    repo,
    run_extopt_workbench,
    run_optimizer_job,
    run_orchestrator_v385,
    run_robust_pareto_frontier,
)
from ui_nicegui.lib.control_room_helpers import report_to_json_bytes
from ui_nicegui.session import DesignSession


def render_external_deck(session: DesignSession, deck: str) -> None:
    render_proposal_banner(title=deck)
    if deck == "Robust Pareto Frontier (Phase+UQ)":
        _render_robust_pareto(session)
    elif deck == "Regime-Conditioned Pareto Atlas 2.0":
        _render_regime_atlas(session)
    elif deck == "Design Family Narratives":
        _render_design_families(session)
    elif deck == "External Optimization Workbench":
        _render_extopt_workbench(session)
    elif deck == "External Optimizer Suite":
        _render_extopt_suite(session)
    elif deck == "External Optimizer Co-Pilot":
        _render_extopt_copilot(session)
    elif deck == "External Optimization Interpretation":
        _render_extopt_interpretation(session)
    elif deck == "Certified Optimization Orchestrator":
        _render_certified_orchestrator(session)
    elif deck == "Concept Optimization Cockpit":
        _render_concept_cockpit(session)
    elif deck == "Feasible Optimizer (External)":
        _render_feasible_optimizer(session)
    elif deck == "Optimization Evidence Packs":
        _render_evidence_packs(session)
    else:
        empty_state(f"Unknown deck: {deck}", kind="warning")


def _render_robust_pareto(session: DesignSession) -> None:
    sources = candidate_sources(session)
    if not sources:
        empty_state("Run Internal Pareto Frontier or a Trade Study first.", kind="info")
        return
    labels = [s[0] for s in sources]
    if session.robust_pareto_source not in labels:
        session.robust_pareto_source = labels[0]
    src_sel = ui.select(labels, label="Candidate source", value=session.robust_pareto_source).classes("w-full")
    bundle = dict(next(b for l, b in sources if l == src_sel.value))

    if not session.robust_pareto_phases_json:
        session.robust_pareto_phases_json = load_phase_defaults()
    if not session.robust_pareto_uq_json:
        session.robust_pareto_uq_json = load_uq_defaults()

    phases = ui.textarea("Phases JSON", value=session.robust_pareto_phases_json).classes("w-full").props("rows=8")
    uq = ui.textarea("UQ contract JSON", value=session.robust_pareto_uq_json).classes("w-full").props("rows=8")
    n_take = ui.number("Max points", value=min(20, len(bundle.get("pareto") or [])), min=1, max=200)

    async def _run() -> None:
        session.robust_pareto_phases_json = str(phases.value or "")
        session.robust_pareto_uq_json = str(uq.value or "")
        session.robust_pareto_source = str(src_sel.value)
        ui.notify("Running robust frontier interrogation…", type="info")
        try:
            res = await run.io_bound(
                run_robust_pareto_frontier,
                session,
                bundle=bundle,
                phases_json=session.robust_pareto_phases_json,
                uq_json=session.robust_pareto_uq_json,
                n_take=int(n_take.value or 10),
            )
            session.robust_pareto_last = res
            ui.notify(f"Classified {res.get('n', 0)} points", type="positive")
            _robust_view.refresh()
        except Exception as exc:
            ui.notify(f"Robust Pareto failed: {exc}", type="negative")

    ui.button("Run Robust Frontier", icon="shield", on_click=_run).props("color=primary outline")
    _robust_view(session)


@ui.refreshable
def _robust_view(session: DesignSession) -> None:
    res = session.robust_pareto_last
    if not isinstance(res, dict):
        return
    counts = res.get("counts") or {}
    kpi_row([(k, str(v)) for k, v in sorted(counts.items())])
    rows = res.get("rows") or []
    if rows:
        obj_senses = res.get("objectives") or {}
        rob_keys = [k for k in rows[0].keys() if str(k).startswith("robust_")]
        if len(rob_keys) >= 1:
            try:
                import plotly.graph_objects as go

                xk = rob_keys[0]
                yk = rob_keys[1] if len(rob_keys) > 1 else rob_keys[0]
                fig = go.Figure()
                tiers = sorted({str(r.get("tier")) for r in rows})
                for tier in tiers:
                    sub = [r for r in rows if str(r.get("tier")) == tier]
                    fig.add_trace(
                        go.Scatter(
                            x=[r.get(xk) for r in sub],
                            y=[r.get(yk) for r in sub],
                            mode="markers",
                            name=tier,
                        )
                    )
                fig.update_layout(
                    height=360,
                    xaxis_title=xk.replace("robust_", ""),
                    yaxis_title=yk.replace("robust_", ""),
                    margin=dict(l=48, r=20, t=36, b=48),
                )
                ui.plotly(fig).classes("w-full q-mb-sm")
            except Exception:
                pass
        cols = [
            {"name": "i", "label": "#", "field": "i"},
            {"name": "tier", "label": "Tier", "field": "tier"},
            {"name": "env_verdict", "label": "Phase", "field": "env_verdict"},
            {"name": "uq_verdict", "label": "UQ", "field": "uq_verdict"},
            {"name": "env_worst_margin", "label": "Phase margin", "field": "env_worst_margin"},
            {"name": "uq_worst_margin", "label": "UQ margin", "field": "uq_worst_margin"},
            {"name": "dominant_constraint", "label": "Dominant", "field": "dominant_constraint", "align": "left"},
        ]
        for rk in rob_keys[:3]:
            cols.append({"name": rk, "label": rk, "field": rk})
        ui.table(columns=cols, rows=rows, row_key="i").classes("w-full")
        pick = ui.number("Promote row #", value=0, min=0, max=max(len(rows) - 1, 0), step=1).classes("w-32")

        def _promote_robust() -> None:
            i = int(pick.value or 0)
            if i < 0 or i >= len(rows):
                ui.notify("Invalid row", type="warning")
                return
            pick_row = rows[i]
            bundle_pts = (session.pareto_last or {}).get("pareto") or []
            cand = bundle_pts[i] if i < len(bundle_pts) else pick_row
            from ui_nicegui.lib.pareto_interpret_helpers import promote_point_inputs

            promote_point_inputs(session, cand if isinstance(cand, dict) else pick_row, session.pareto_bounds or {})
            ui.notify("Promoted point to Point Designer inputs — evaluate there.", type="positive")

        ui.button("Promote row → Point Designer", icon="upload", on_click=_promote_robust).props("outline")
        ui.button(
            "Download robust_pareto.json",
            icon="download",
            on_click=lambda: ui.download(report_to_json_bytes(res), "robust_pareto.json"),
        ).props("flat outline")


def _render_regime_atlas(session: DesignSession) -> None:
    blob: dict = {"records": []}

    async def _upload(e) -> None:
        recs = load_records_from_upload(e.name, e.content.read())
        blob["records"] = recs
        session.regime_atlas_records = recs
        ui.notify(f"Loaded {len(recs)} records", type="info")

    ui.upload(on_upload=_upload).props('accept=".json,.jsonl,.zip" auto-upload label="Upload candidate records"')

    recs = session.regime_atlas_records or blob.get("records") or []
    if not recs:
        ui.label("Upload records or run a campaign first.").classes("text-caption")
        return

    gate = ui.select(
        ["any_feasible", "optimistic", "robust", "robust_only"],
        label="Feasibility gate",
        value=session.regime_atlas_gate or "robust_only",
    )
    min_bucket = ui.number("Min bucket size", value=session.regime_atlas_min_bucket or 8, min=1)

    async def _build() -> None:
        cfg = {
            "axes": ["plasma_regime", "exhaust_regime", "dominance_label", "robustness_class"],
            "min_bucket_size": int(min_bucket.value or 8),
            "feasibility_gate": str(gate.value),
            "metrics": [
                {"key": "P_e_net_MW", "dir": "max"},
                {"key": "f_recirc", "dir": "min"},
                {"key": "CoE_USD_MWh", "dir": "min"},
            ],
        }
        try:
            atlas = await run.io_bound(build_regime_atlas, recs, cfg)
            session.regime_atlas_last = atlas
            ui.notify("Atlas built", type="positive")
            _atlas_view.refresh()
        except Exception as exc:
            ui.notify(f"Atlas build failed: {exc}", type="negative")

    ui.button("Build Atlas", icon="map", on_click=_build).props("outline")
    _atlas_view(session)


@ui.refreshable
def _atlas_view(session: DesignSession) -> None:
    atlas = session.regime_atlas_last
    if not isinstance(atlas, dict):
        return
    with ui.expansion("Atlas summary", icon="analytics").classes("w-full"):
        ui.json({k: atlas.get(k) for k in ["schema", "fingerprint_sha256", "config"] if k in atlas})
    ui.button(
        "Download Atlas Evidence Pack ZIP",
        icon="download",
        on_click=lambda: ui.download(atlas_evidence_zip(atlas), "SHAMS_AtlasEvidencePack_v365.zip"),
    ).props("outline")


def _render_design_families(session: DesignSession) -> None:
    src = ui.toggle(["Pareto points", "All feasible points"], value="Pareto points")

    async def _run() -> None:
        try:
            res = await run.io_bound(
                build_design_families,
                session,
                source="pareto" if src.value == "Pareto points" else "feasible",
            )
            session.design_families_last = res
            ui.notify(f"Built families from {res.get('n_records', 0)} records", type="positive")
            _fam_view.refresh()
        except Exception as exc:
            ui.notify(str(exc), type="warning")

    ui.button("Build design families", icon="category", on_click=_run).props("outline")
    _fam_view(session)


@ui.refreshable
def _fam_view(session: DesignSession) -> None:
    res = session.design_families_last
    if not isinstance(res, dict):
        return
    fams = res.get("families") or []
    if isinstance(fams, list):
        ui.label(f"Families: {len(fams)}").classes("text-caption")
        with ui.expansion("Families JSON", icon="data_object").classes("w-full"):
            ui.json(fams[:20] if len(fams) > 20 else fams)


def _render_extopt_workbench(session: DesignSession) -> None:
    yamls = list_concept_family_yamls()
    if not yamls:
        empty_state("No concept family YAMLs under examples/concept_families/", kind="warning")
        return
    sel = ui.select([p.name for p in yamls], label="Concept family YAML", value=yamls[0].name)
    seed = ui.number("Seed", value=1, min=0)
    nprop = ui.number("Proposals", value=32, min=4, step=4)
    robust = ui.checkbox("Robust mode (UQ-lite corners)", value=False)

    async def _run() -> None:
        path = next(p for p in yamls if p.name == sel.value)
        try:
            bundle = await run.io_bound(
                run_extopt_workbench,
                family_yaml=path,
                seed=int(seed.value or 1),
                n_proposals=int(nprop.value or 32),
                robust=bool(robust.value),
                evaluator_label="hot_ion_point",
            )
            session.extopt_workbench_last = bundle
            ui.notify("Reference optimizer run complete", type="positive")
            _wb_dl.refresh()
        except Exception as exc:
            ui.notify(f"Workbench failed: {exc}", type="negative")

    ui.button("Run reference optimizer", icon="play_arrow", on_click=_run).props("color=primary outline")
    _wb_dl(session)


@ui.refreshable
def _wb_dl(session: DesignSession) -> None:
    p = session.extopt_workbench_last
    if isinstance(p, str) and Path(p).is_file():
        ui.button(
            "Download optimizer bundle ZIP",
            icon="download",
            on_click=lambda: ui.download(Path(p).read_bytes(), Path(p).name),
        ).props("flat outline")


def _render_extopt_suite(session: DesignSession) -> None:
    ui.label("Orchestrator 2.0 — import concept family YAML and re-verify through frozen truth.").classes("text-caption")

    async def _upload(e) -> None:
        session.extopt_suite_upload_name = e.name
        session.extopt_suite_upload_bytes = e.content.read()

    ui.upload(on_upload=_upload).props('accept=".yaml,.yml" auto-upload label="Concept family YAML"')
    intent = ui.select(["research", "reactor"], label="Design intent", value="reactor")
    include_ep = ui.checkbox("Include per-candidate evidence packs", value=True)

    async def _run() -> None:
        data = session.extopt_suite_upload_bytes
        if not isinstance(data, (bytes, bytearray)):
            ui.notify("Upload a YAML first", type="warning")
            return
        try:
            res = await run.io_bound(
                run_orchestrator_v385,
                yaml_bytes=bytes(data),
                yaml_name=str(session.extopt_suite_upload_name or "family.yaml"),
                evaluator_label="hot_ion_point",
                intent=str(intent.value),
                include_ep=bool(include_ep.value),
            )
            session.extopt_last_run = res
            ui.notify("Verification complete", type="positive")
            _suite_view.refresh()
        except Exception as exc:
            ui.notify(f"Orchestrator failed: {exc}", type="negative")

    ui.button("Run import & verification", icon="verified", on_click=_run).props("outline")
    _suite_view(session)


@ui.refreshable
def _suite_view(session: DesignSession) -> None:
    last = session.extopt_last_run
    if not isinstance(last, dict):
        return
    kpi_row([
        ("Candidates", str(last.get("n_total", "-"))),
        ("Feasible", str(last.get("n_feasible", "-"))),
        ("Pass rate", f"{100.0 * float(last.get('pass_rate', 0.0)):.1f}%"),
    ])
    zpath = last.get("bundle_zip")
    if isinstance(zpath, str) and Path(zpath).is_file():
        ui.button(
            "Download evidence bundle ZIP",
            icon="download",
            on_click=lambda: ui.download(Path(zpath).read_bytes(), Path(zpath).name),
        ).props("flat outline")


def _render_extopt_copilot(session: DesignSession) -> None:
    ui.label("Upload concept family YAML; SHAMS batch-evaluates candidates (no internal optimization).").classes(
        "text-caption"
    )

    async def _upload(e) -> None:
        session.extopt_copilot_yaml_bytes = e.content.read()
        session.extopt_copilot_yaml_name = e.name

    ui.upload(on_upload=_upload).props('accept=".yaml,.yml" auto-upload')

    async def _run() -> None:
        data = session.extopt_copilot_yaml_bytes
        if not data:
            ui.notify("Upload YAML first", type="warning")
            return
        tdir = repo() / "ui_runs" / "uploads"
        tdir.mkdir(parents=True, exist_ok=True)
        p = tdir / str(session.extopt_copilot_yaml_name or "family.yaml")
        p.write_bytes(bytes(data))
        try:
            from src.extopt.copilot import run_copilot_from_concept_family

            res = await run.io_bound(
                run_copilot_from_concept_family,
                concept_family_yaml=p,
                repo_root=repo(),
                run_id="nicegui_copilot",
                evaluator_label="hot_ion_point",
                export_evidence_packs=True,
            )
            session.extopt_copilot_last = res.__dict__ if hasattr(res, "__dict__") else dict(res)
            ui.notify("Co-Pilot run complete", type="positive")
        except Exception as exc:
            ui.notify(f"Co-Pilot failed: {exc}", type="negative")

    ui.button("Run Co-Pilot evaluation", icon="psychology", on_click=_run).props("outline")


def _render_extopt_interpretation(session: DesignSession) -> None:
    trace_blob: dict = {}

    async def _upload(e) -> None:
        try:
            trace_blob.clear()
            trace_blob.update(json.loads(e.content.read().decode("utf-8")))
        except Exception as exc:
            ui.notify(f"Invalid JSON: {exc}", type="negative")

    ui.upload(on_upload=_upload).props('accept=".json" auto-upload label="optimizer_trace.json"')

    def _interpret() -> None:
        if not trace_blob:
            ui.notify("Upload trace JSON", type="warning")
            return
        try:
            session.extopt_interpret_last = interpret_optimizer_trace(trace_blob)
            _interp_view.refresh()
        except Exception as exc:
            ui.notify(f"Interpretation failed: {exc}", type="negative")

    ui.button("Interpret trace", icon="analytics", on_click=_interpret).props("outline")
    _interp_view(session)


@ui.refreshable
def _interp_view(session: DesignSession) -> None:
    rep = session.extopt_interpret_last
    if isinstance(rep, dict):
        with ui.expansion("Interpretation report", icon="description").classes("w-full"):
            ui.json(rep)


def _render_certified_orchestrator(session: DesignSession) -> None:
    kit = ui.select(["NSGA2-lite", "CMAES-lite", "BO-lite"], label="Kit", value="NSGA2-lite")
    seed = ui.number("Seed", value=1, min=0)
    n = ui.number("Budget (n)", value=200, min=50, step=50)
    objs = ui.select(["P_e_net_MW", "R0_m", "B_peak_T"], label="Objective", value="P_e_net_MW", multiple=True)

    async def _run() -> None:
        if not objs.value:
            ui.notify("Select objectives", type="warning")
            return
        try:
            from src.trade_studies.spec import default_knob_sets

            base = session.build_point_inputs()
            ksel = default_knob_sets()[0]
            chosen = list(objs.value) if isinstance(objs.value, list) else [str(objs.value)]
            senses = {o: "max" if o == "P_e_net_MW" else "min" for o in chosen}
            res = await run.io_bound(
                run_optimizer_job,
                kit=str(kit.value),
                seed=int(seed.value or 1),
                n=int(n.value or 200),
                objectives=chosen,
                senses=senses,
                bounds=dict(ksel.bounds),
                base=base,
            )
            session.certified_opt_last = res
            ui.notify("Optimizer job complete", type="positive")
            _cert_view.refresh()
        except Exception as exc:
            ui.notify(f"Orchestrator failed: {exc}", type="negative")

    ui.button("Run certified optimizer job", icon="gavel", on_click=_run).props("outline")
    _cert_view(session)


@ui.refreshable
def _cert_view(session: DesignSession) -> None:
    rep = session.certified_opt_last
    if isinstance(rep, dict):
        with ui.expansion("Job report", icon="assignment").classes("w-full"):
            ui.json(rep)


def _render_concept_cockpit(session: DesignSession) -> None:
    yamls = list_concept_family_yamls()
    if not yamls:
        empty_state("No example concept families found.", kind="warning")
        return
    sel = ui.select([p.name for p in yamls], label="Concept family", value=yamls[0].name)

    async def _run() -> None:
        path = next(p for p in yamls if p.name == sel.value)
        try:
            res = await run.io_bound(evaluate_concept_family_yaml, path)
            session.concept_cockpit_last = res
            ui.notify("Batch evaluation complete", type="positive")
            _cockpit_view.refresh()
        except Exception as exc:
            ui.notify(f"Cockpit failed: {exc}", type="negative")

    ui.button("Batch evaluate family", icon="science", on_click=_run).props("color=primary outline")
    _cockpit_view(session)


@ui.refreshable
def _cockpit_view(session: DesignSession) -> None:
    rep = session.concept_cockpit_last
    if isinstance(rep, dict):
        summary = rep.get("summary") or rep
        kpi_row([
            ("N", str(summary.get("n_total", summary.get("n", "-")))),
            ("Feasible", str(summary.get("n_feasible", "-"))),
        ])
        ui.button(
            "Download results JSON",
            icon="download",
            on_click=lambda: ui.download(report_to_json_bytes(rep), "concept_cockpit_results.json"),
        ).props("flat outline")


def _render_feasible_optimizer(session: DesignSession) -> None:
    from ui_nicegui.lib.external_optimizer_helpers import launch_optimizer_kit
    from ui_nicegui.lib.pareto_helpers import default_bounds

    ui.label(
        "External feasible optimizer — proposes inputs only; SHAMS re-evaluates with frozen truth."
    ).classes("text-caption")
    base = session.build_point_inputs()
    bounds = dict(session.pareto_bounds or default_bounds(base))
    kit = ui.select(["NSGA2-lite", "CMAES-lite", "BO-lite"], label="Optimizer kit", value="NSGA2-lite")
    seed = ui.number("Seed", value=session.pareto_seed, min=0, step=1)
    budget = ui.number("Budget (evaluations)", value=200, min=50, max=5000, step=50)
    obj_opts = ["P_e_net_MW", "R0_m", "B_peak_T", "Q_DT_eqv", "q_div_MW_m2"]
    objs = ui.select(obj_opts, label="Objectives", value=["P_e_net_MW", "R0_m"], multiple=True)

    with ui.expansion("Knob bounds (same hyper-rectangle as Internal Pareto)", icon="crop").classes("w-full"):
        for key in ("R0_m", "Bt_T", "Ip_MA", "fG"):
            lo, hi = bounds.get(key, (0.0, 1.0))
            ui.label(f"{key}: [{lo:.3g}, {hi:.3g}]").classes("text-caption")

    async def _run() -> None:
        chosen = list(objs.value) if isinstance(objs.value, list) else [str(objs.value)]
        if len(chosen) < 1:
            ui.notify("Select at least one objective", type="warning")
            return
        senses = {o: "max" if o == "P_e_net_MW" else "min" for o in chosen}
        ui.notify("Launching external optimizer kit…", type="info")
        try:
            res = await run.io_bound(
                launch_optimizer_kit,
                kit=str(kit.value),
                seed=int(seed.value or 1),
                n=int(budget.value or 200),
                objectives=chosen,
                senses=senses,
                bounds=bounds,
                base=base,
            )
            session.feasible_optimizer_last = res
            rc = int(res.get("returncode", 1))
            if rc == 0:
                ui.notify("Optimizer kit finished", type="positive")
            else:
                ui.notify(f"Kit exited with code {rc} — see log below", type="warning")
            _feas_opt_view.refresh()
        except Exception as exc:
            ui.notify(f"Launch failed: {exc}", type="negative")

    ui.button("Run feasible optimizer kit", icon="rocket_launch", on_click=_run).props("color=primary outline")
    _feas_opt_view(session)


@ui.refreshable
def _feas_opt_view(session: DesignSession) -> None:
    res = session.feasible_optimizer_last
    if not isinstance(res, dict):
        return
    with ui.expansion("Run log", icon="terminal").classes("w-full"):
        ui.label(f"Config: {res.get('config_path', '-')}").classes("text-caption")
        if res.get("stdout"):
            ui.code(str(res.get("stdout"))[:6000]).classes("w-full")
        if res.get("stderr"):
            ui.code(str(res.get("stderr"))[:4000]).classes("w-full text-orange")


def _render_evidence_packs(session: DesignSession) -> None:
    runs = list_optimizer_run_dirs()
    if not runs:
        empty_state("No optimizer runs under runs/optimizer/. Run an external optimizer first.", kind="info")
        return
    names = [p.name for p in runs]
    sel = ui.select(names, label="Run directory", value=names[0])

    def _show() -> None:
        run_dir = next(p for p in runs if p.name == sel.value)
        meta = read_run_json(run_dir, "meta.json") or {}
        summary = read_run_json(run_dir, "summary.json") or {}
        kpi_row([
            ("N", str(meta.get("n", "-"))),
            ("Feasible", str(meta.get("n_feasible", "-"))),
            ("Objective", str(meta.get("objective", "-"))),
        ])
        session.optimizer_evidence_sel = str(run_dir)
        with ui.expansion("Summary JSON", icon="description").classes("w-full"):
            ui.json(summary)

    sel.on("update:model-value", lambda: _show())
    _show()
