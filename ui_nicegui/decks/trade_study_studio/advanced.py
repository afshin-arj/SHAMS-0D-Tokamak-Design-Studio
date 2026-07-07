"""Trade Study Studio advanced decks — Phase 17."""
from __future__ import annotations

import json

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.json_view import render_json_blob
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.components.proposal_banner import render_proposal_banner
from ui_nicegui.lib.control_room_helpers import report_to_json_bytes
from ui_nicegui.lib.external_optimizer_helpers import (
    build_v324_regime_maps,
    build_v351_atlas,
    default_pathfinding_levers,
    family_summary_rows,
    launch_optimizer_kit,
    run_mirage_path_scan,
    run_two_lane_uq,
)
from ui_nicegui.lib.pareto_interpret_helpers import v351_empty_region_report
from ui_nicegui.lib.display_labels import (
    DECK_FRONTIER_ATLAS,
    DECK_REGIME_MAPS,
    DECK_ROBUST_CERT,
    normalize_user_label,
)
from ui_nicegui.lib.trade_study_helpers import ADVANCED_DECKS, objectives_catalog
from ui_nicegui.session import DesignSession

try:
    from src.trade_studies.spec import default_knob_sets
except ImportError:
    from trade_studies.spec import default_knob_sets  # type: ignore


def render_advanced_deck(session: DesignSession, deck: str) -> None:
    deck = normalize_user_label(deck)
    render_proposal_banner(title=deck)
    if deck == DECK_FRONTIER_ATLAS:
        _render_v351(session)
    elif deck == DECK_ROBUST_CERT:
        _render_v352(session)
    elif deck == "Feasible-First Surrogate Accelerator":
        _render_surrogate_accel(session)
    elif deck == "Optimizer Kits (External)":
        _render_optimizer_kits(session)
    elif deck == "Fast Optimistic Design (Two-Lane)":
        _render_two_lane(session)
    elif deck == "Design Family Atlas":
        _render_family_atlas(session)
    elif deck == DECK_REGIME_MAPS:
        _render_v324(session)
    elif deck == "Mirage Pathfinding":
        _render_mirage_pathfinding(session)
    else:
        empty_state(f"Unknown deck: {deck}", kind="warning")


def _require_trade_last(session: DesignSession):
    rep = session.trade_last
    if not isinstance(rep, dict):
        empty_state("Run **Study Setup & Run** first.", kind="info")
        return None
    return rep


def _render_v351(session: DesignSession) -> None:
    rep = session.trade_last
    cap = session.active_study_capsule
    if not isinstance(rep, dict) and not isinstance(cap, dict):
        empty_state("Run **Setup & Run** first or upload a study capsule.", kind="info")
        return

    records: list = []
    if isinstance(cap, dict):
        records = list(cap.get("records") or [])
    elif isinstance(rep, dict):
        records = list(rep.get("records") or [])
    base_inputs = (cap or {}).get("base_inputs") if isinstance(cap, dict) else {}
    if cap:
        ui.label(f"Using study capsule id={cap.get('id', '-')} · N={len(records)}").classes("text-caption text-positive")

    obj_names, obj_senses = objectives_catalog()
    present = [o for o in obj_names if records and o in records[0]]
    if not present:
        present = obj_names[:4]
    chosen = ui.select(present, label="Objectives", value=present[:2], multiple=True).classes("w-full")
    lane_budget = ui.number("Lane classification budget", value=20, min=1, max=200)

    async def _run() -> None:
        objs = list(chosen.value) if chosen.value else []
        if not objs:
            ui.notify("Select objectives", type="warning")
            return
        senses = {o: str(obj_senses.get(o, "min")) for o in objs}
        try:
            atlas = await run.io_bound(build_v351_atlas, session, objectives=objs, senses=senses)
            session.v351_atlas_last = atlas
            feas = [r for r in records if r.get("is_feasible")]
            from src.atlas.frontier_atlas_v351 import pareto_front, classify_lanes_for_points, bin_counts
            from src.evaluator.core import Evaluator
            from src.uq_contracts.spec import optimistic_uncertainty_contract, robust_uncertainty_contract
            from src.uq_contracts.runner import run_uncertainty_contract_for_point

            pareto_rows = pareto_front(feas, objectives=objs, senses=senses)
            if pareto_rows and base_inputs:
                ev = Evaluator(label="NiceGUI:v351", cache_enabled=True)
                session.v351_lane_rows = await run.io_bound(
                    classify_lanes_for_points,
                    evaluator=ev,
                    base_inputs=base_inputs,
                    rows=pareto_rows,
                    optimistic_contract_fn=optimistic_uncertainty_contract,
                    robust_contract_fn=robust_uncertainty_contract,
                    run_uq_fn=run_uncertainty_contract_for_point,
                    label_prefix="v351",
                    max_points=int(lane_budget.value or 20),
                )
            numeric = sorted(
                {k for r in records[:50] for k in r if isinstance(r.get(k), (int, float))}
            )[:12]
            if len(numeric) >= 2:
                atlas["empty_region_axes"] = numeric
            session.v351_atlas_last = atlas
            ui.notify(f"Atlas: {atlas.get('n_pareto', 0)} Pareto points", type="positive")
            _v351_view.refresh()
        except Exception as exc:
            ui.notify(f"Frontier atlas failed: {exc}", type="negative")

    ui.button("Build frontier atlas + lane classify", icon="map", on_click=_run).props("outline")
    _v351_view(session)


@ui.refreshable
def _v351_view(session: DesignSession) -> None:
    atlas = session.v351_atlas_last
    if not isinstance(atlas, dict):
        return
    kpi_row([
        ("Total", str(atlas.get("n_total", "-"))),
        ("Feasible", str(atlas.get("n_feasible", "-"))),
        ("Pareto", str(atlas.get("n_pareto", "-"))),
    ])
    if atlas.get("all_infeasible"):
        ui.label(
            "No intent-feasible samples in this study — frontier atlas is empty (NO-SOLUTION is valid)."
        ).classes("text-caption text-orange")
    lanes = session.v351_lane_rows
    if isinstance(lanes, list) and lanes:
        nrob = sum(1 for r in lanes if r.get("is_robust"))
        nmir = sum(1 for r in lanes if r.get("is_mirage"))
        ui.label(f"Lane labels: robust={nrob} · mirage={nmir} · classified={len(lanes)}").classes("text-caption")
        ui.table(
            columns=[
                {"name": "i", "label": "i", "field": "i"},
                {"name": "is_robust", "label": "Robust", "field": "is_robust"},
                {"name": "is_mirage", "label": "Mirage", "field": "is_mirage"},
                {"name": "lane_robust_verdict", "label": "Lane-R", "field": "lane_robust_verdict", "align": "left"},
            ],
            rows=[{k: r.get(k) for k in ("i", "is_robust", "is_mirage", "lane_robust_verdict")} for r in lanes[:40]],
            row_key="i",
        ).classes("w-full")
    cap = session.active_study_capsule or {}
    rep = session.trade_last or {}
    records = list((cap.get("records") if isinstance(cap, dict) else None) or rep.get("records") or [])
    axes = atlas.get("empty_region_axes") or []
    if records and len(axes) >= 2:
        ui.label("Empty-region map (2D binning)").classes("text-subtitle2 q-mt-sm")
        xk = ui.select(axes, label="X axis", value=axes[0]).classes("flex-1")
        yk = ui.select(axes, label="Y axis", value=axes[1]).classes("flex-1")
        xb = ui.number("X bins", value=12, min=4, max=40)
        yb = ui.number("Y bins", value=12, min=4, max=40)

        def _empty_report() -> None:
            er = v351_empty_region_report(
                records,
                x_key=str(xk.value),
                y_key=str(yk.value),
                x_bins=int(xb.value or 12),
                y_bins=int(yb.value or 12),
                lane_rows=lanes if isinstance(lanes, list) else None,
            )
            session.v351_empty_region = er
            render_json_blob(er)
            _empty_region_view.refresh()

        ui.button("Compute empty-region report", icon="grid_on", on_click=_empty_report).props("flat outline")

        @ui.refreshable
        def _empty_region_view() -> None:
            if isinstance(session.v351_empty_region, dict):
                render_json_blob(session.v351_empty_region)

        _empty_region_view()
    payload = dict(atlas)
    if isinstance(session.v351_empty_region, dict):
        payload["empty_region"] = session.v351_empty_region
    ui.button(
        "Download frontier atlas JSON",
        icon="download",
        on_click=lambda: ui.download(report_to_json_bytes(payload), "shams_frontier_atlas.json"),
    ).props("flat outline")


def _render_v352(session: DesignSession) -> None:
    rep = _require_trade_last(session)
    if rep is None:
        return
    ui.label("Robust envelope certification under ROBUST UQ-lite contract (budgeted).").classes("text-caption")
    source = ui.select(
        ["Trade Study: Feasible", "Trade Study: Pareto"],
        label="Candidate source",
        value="Trade Study: Pareto",
    )
    budget = ui.number("Certification budget (points)", value=10, min=1, max=100)

    async def _run() -> None:
        key = "feasible" if "Feasible" in str(source.value) else "pareto"
        rows = list(rep.get(key) or [])
        if not rows:
            ui.notify("Empty candidate source", type="warning")
            return
        try:
            from src.certification.robust_envelope_v352 import TierThresholds, certify_points_under_contract
            from src.models.inputs import PointInputs
            from src.uq_contracts.runner import run_uncertainty_contract_for_point
            from src.uq_contracts.spec import robust_uncertainty_contract

            base = session.build_point_inputs()
            base_d = base.__dict__ if hasattr(base, "__dict__") else {}
            pts = []
            for r in rows[: int(budget.value or 10)]:
                d = dict(base_d)
                for k, v in (r or {}).items():
                    if k in d:
                        try:
                            d[k] = float(v)
                        except (TypeError, ValueError):
                            pass
                pts.append(PointInputs(**d))
            spec = robust_uncertainty_contract(base).to_dict()
            cert = certify_points_under_contract(
                points=pts,
                contract_spec=spec,
                run_uq_fn=run_uncertainty_contract_for_point,
                thresholds=TierThresholds(tier_A_min=0.10, tier_B_min=0.03, tier_C_min=0.0),
                label_prefix="v352",
                max_points=int(budget.value or 10),
            )
            session.v352_cert_last = cert
            ui.notify("Certification complete", type="positive")
            _v352_view.refresh()
        except Exception as exc:
            ui.notify(f"Robust certification failed: {exc}", type="negative")

    ui.button("Run Robust Envelope Certification", icon="verified_user", on_click=_run).props("outline")
    _v352_view(session)


@ui.refreshable
def _v352_view(session: DesignSession) -> None:
    cert = session.v352_cert_last
    if isinstance(cert, dict):
        rep0 = cert.get("report") or {}
        with ui.expansion("Certification report", icon="description").classes("w-full"):
            render_json_blob(rep0)
        rows = rep0.get("rows") or []
        if rows:
            show = ["index", "verdict", "tier", "worst_hard_margin_frac", "n_corners", "n_feasible"]
            ui.table(
                columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in show if c in rows[0]],
                rows=[{c: r.get(c) for c in show if c in r} for r in rows[:50]],
                row_key="index",
            ).classes("w-full")


def _render_surrogate_accel(session: DesignSession) -> None:
    rep = _require_trade_last(session)
    if rep is None:
        return
    ui.label("Surrogate proposes; frozen truth re-verifies (non-authoritative speed layer).").classes("text-caption")
    obj_names, obj_senses = objectives_catalog()
    primary = ui.select(obj_names, label="Primary acquisition objective", value=obj_names[0] if obj_names else "")
    n_prop = ui.number("Batch proposals", value=12, min=4, max=200)
    n_pool = ui.number("Candidate pool", value=1000, min=200, max=20000, step=200)

    async def _propose() -> None:
        cap = session.active_study_capsule or {}
        bounds = dict((cap.get("knob_set") or {}).get("bounds") or {})
        if not bounds:
            ks = default_knob_sets()[0]
            bounds = dict(ks.bounds)
        try:
            from src.extopt.surrogate_accel import propose_candidates

            cand = await run.io_bound(
                propose_candidates,
                records=rep.get("records") or [],
                bounds=bounds,
                objective_key=str(primary.value),
                objective_sense=str(obj_senses.get(str(primary.value), "min")),
                n_pool=int(n_pool.value or 1000),
                n_propose=int(n_prop.value or 12),
                seed=17,
                kappa=0.5,
            )
            session.ts_sa_candidates = cand
            ui.notify(f"Proposed {len(cand)} candidates", type="positive")
            _sa_view.refresh()
        except Exception as exc:
            ui.notify(f"Proposal failed: {exc}", type="negative")

    async def _verify() -> None:
        cand = session.ts_sa_candidates
        if not cand:
            ui.notify("Propose candidates first", type="warning")
            return
        cap = session.active_study_capsule or {}
        study_obj = cap.get("objectives") or (rep.get("meta") or {}).get("objectives") or [str(primary.value)]
        study_senses = cap.get("objective_senses") or (rep.get("meta") or {}).get("objective_senses") or {}
        try:
            from src.evaluator.core import Evaluator
            from src.extopt.surrogate_accel import verify_candidates_as_rows

            ev = Evaluator(label="NiceGUI:SurrogateVerify", cache_enabled=True)
            vrows = await run.io_bound(
                verify_candidates_as_rows,
                evaluator=ev,
                base_inputs=session.build_point_inputs(),
                candidates=cand,
                objectives=list(study_obj),
                objective_senses=dict(study_senses) if study_senses else {str(primary.value): str(obj_senses.get(str(primary.value), "min"))},
                include_outputs=False,
            )
            session.ts_sa_verified_rows = vrows
            ui.notify(f"Verified {len(vrows)} candidates", type="positive")
            _sa_view.refresh()
        except Exception as exc:
            ui.notify(f"Verification failed: {exc}", type="negative")

    ui.button("Propose candidates (surrogate)", icon="bolt", on_click=_propose).props("outline")
    ui.button("Verify with frozen truth", icon="verified", on_click=_verify).props("outline")
    _sa_view(session)


@ui.refreshable
def _sa_view(session: DesignSession) -> None:
    cand = session.ts_sa_candidates
    if isinstance(cand, list) and cand:
        ui.label(f"Proposed (unverified): {len(cand)}").classes("text-caption")
    vrows = session.ts_sa_verified_rows
    if isinstance(vrows, list) and vrows:
        ui.label(f"Verified: {len(vrows)}").classes("text-caption text-positive")
        ui.table(
            columns=[
                {"name": "i", "label": "i", "field": "i"},
                {"name": "is_feasible", "label": "Feasible", "field": "is_feasible"},
                {"name": "dominant_constraint", "label": "Dominant", "field": "dominant_constraint", "align": "left"},
            ],
            rows=[{k: r.get(k) for k in ("i", "is_feasible", "dominant_constraint")} for r in vrows[:30]],
            row_key="i",
        ).classes("w-full")


def _render_optimizer_kits(session: DesignSession) -> None:
    kit = ui.select(
        [
            "NSGA-II-lite (multi-objective batch)",
            "CMA-ES-lite (continuous, feasible-only)",
            "BO-lite (surrogate-guided feasible-only)",
        ],
        label="Kit",
        value="NSGA-II-lite (multi-objective batch)",
    )
    seed = ui.number("Seed", value=11)
    n = ui.number("Budget (truth calls)", value=400, min=100, max=5000)
    obj_names, obj_senses = objectives_catalog()
    chosen = ui.select(obj_names, label="Objectives", value=obj_names[:3], multiple=True)
    ks = default_knob_sets()
    knob = ui.select([k.name for k in ks], label="Knob bounds", value=ks[0].name)

    async def _launch() -> None:
        objs = list(chosen.value) if chosen.value else []
        if not objs:
            ui.notify("Select objectives", type="warning")
            return
        ksel = next(k for k in ks if k.name == knob.value)
        try:
            rep = await run.io_bound(
                launch_optimizer_kit,
                kit=str(kit.value),
                seed=int(seed.value or 11),
                n=int(n.value or 400),
                objectives=objs,
                senses={o: str(obj_senses.get(o, "min")) for o in objs},
                bounds=dict(ksel.bounds),
                base=session.build_point_inputs(),
            )
            session.ts_kit_last = rep
            ui.notify(f"Kit finished rc={rep.get('returncode')}", type="positive" if rep.get("returncode") == 0 else "warning")
            _kit_log.refresh()
        except Exception as exc:
            ui.notify(f"Kit launch failed: {exc}", type="negative")

    ui.button("Launch kit", icon="rocket_launch", on_click=_launch).props("color=primary outline")
    _kit_log(session)


@ui.refreshable
def _kit_log(session: DesignSession) -> None:
    rep = session.ts_kit_last
    if isinstance(rep, dict) and (rep.get("stdout") or rep.get("stderr")):
        with ui.expansion("Kit log", icon="terminal").classes("w-full"):
            ui.code((rep.get("stdout") or "") + "\n" + (rep.get("stderr") or ""))


def _render_two_lane(session: DesignSession) -> None:
    async def _eval() -> None:
        try:
            res = await run.io_bound(run_two_lane_uq, session.build_point_inputs())
            session.lane_last = res
            ui.notify(f"Class: {res.get('class')}", type="positive")
            _lane_view.refresh()
        except Exception as exc:
            ui.notify(f"Lane eval failed: {exc}", type="negative")

    ui.button("Evaluate current point (lane O & R)", icon="compare", on_click=_eval).props("outline")
    _lane_view(session)


@ui.refreshable
def _lane_view(session: DesignSession) -> None:
    lr = session.lane_last
    if not isinstance(lr, dict):
        return
    kpi_row([
        ("Lane-O", str(lr.get("verdict_O", "-"))),
        ("Lane-R", str(lr.get("verdict_R", "-"))),
        ("Class", str(lr.get("class", "-"))),
    ])


def _render_family_atlas(session: DesignSession) -> None:
    rep = _require_trade_last(session)
    if rep is None:
        return
    records = rep.get("records") or []
    fam = family_summary_rows(records)
    rows = fam.get("rows") or []
    if rows:
        ui.table(
            columns=[
                {"name": "family", "label": "Family", "field": "family", "align": "left"},
                {"name": "n", "label": "N", "field": "n"},
                {"name": "feasible_frac", "label": "Feasible frac", "field": "feasible_frac"},
            ],
            rows=rows,
            row_key="family",
        ).classes("w-full")
    else:
        ui.label("No family summary rows.").classes("text-caption")


def _render_v324(session: DesignSession) -> None:
    rep = _require_trade_last(session)
    if rep is None:
        return
    records = list(rep.get("records") or [])
    min_cluster = ui.number("Min cluster size", value=6, min=3, max=30)
    max_bins = ui.number("Bins per feature", value=12, min=6, max=24)

    async def _run() -> None:
        feas = [r for r in records if isinstance(r, dict) and bool(r.get("is_feasible"))]
        if not feas:
            ui.notify("No feasible points", type="warning")
            return
        feats = sorted({k for r in feas[:80] for k in r.keys() if isinstance(k, str) and isinstance(r.get(k), (int, float))})[:6]
        try:
            rpt = await run.io_bound(
                build_v324_regime_maps,
                records,
                features=feats,
                min_cluster=int(min_cluster.value or 6),
                max_bins=int(max_bins.value or 12),
            )
            session.v324_regime_maps = rpt
            ui.notify(f"Built {len(rpt.get('clusters') or [])} clusters", type="positive")
            _v324_view.refresh()
        except Exception as exc:
            ui.notify(f"Regime maps failed: {exc}", type="negative")

    ui.button("Build regime map report", icon="hub", on_click=_run).props("outline")
    _v324_view(session)


@ui.refreshable
def _v324_view(session: DesignSession) -> None:
    rpt = session.v324_regime_maps
    if not isinstance(rpt, dict):
        return
    clusters = rpt.get("clusters") or []
    if clusters:
        ui.label("Regime clusters").classes("text-subtitle2")
        table_rows = []
        for c in clusters:
            if not isinstance(c, dict):
                continue
            auth = c.get("authority") or {}
            table_rows.append({
                "cluster_id": c.get("cluster_id"),
                "n": c.get("n"),
                "regime": c.get("regime_label"),
                "dominant_constraint": c.get("dominant_constraint"),
                "authority_tier": auth.get("authority_tier"),
            })
        if table_rows:
            ui.table(
                columns=[
                    {"name": "cluster_id", "label": "ID", "field": "cluster_id"},
                    {"name": "n", "label": "N", "field": "n"},
                    {"name": "regime", "label": "Regime", "field": "regime", "align": "left"},
                    {"name": "dominant_constraint", "label": "Dominant", "field": "dominant_constraint", "align": "left"},
                ],
                rows=table_rows,
                row_key="cluster_id",
            ).classes("w-full")
        with ui.expansion("Cluster narratives", icon="article").classes("w-full"):
            for c in clusters[:12]:
                if isinstance(c, dict):
                    ui.markdown(f"**Cluster {c.get('cluster_id')} — {c.get('regime_label')}**")
                    ui.label(str(c.get("narrative") or "")).classes("text-caption")
    ui.button(
        "Download regime_maps_report.json",
        icon="download",
        on_click=lambda: ui.download(report_to_json_bytes(rpt), "regime_maps_report.json"),
    ).props("flat outline")


def _render_mirage_pathfinding(session: DesignSession) -> None:
    levers = default_pathfinding_levers(session.build_point_inputs())
    if not levers:
        empty_state("No pathfinding levers available for current point.", kind="warning")
        return
    labels = [f"{k}: {lo:.3g} → {hi:.3g}" for k, lo, hi in levers]
    sel = ui.select(labels, label="Improvement lever", value=labels[0])
    n = ui.number("Scan points", value=17, min=7, max=41, step=2)

    async def _run() -> None:
        idx = labels.index(str(sel.value))
        knob, lo, hi = levers[idx]
        try:
            rep = await run.io_bound(
                run_mirage_path_scan,
                session.build_point_inputs(),
                knob,
                lo,
                hi,
                int(n.value or 17),
            )
            session.pf_last = rep
            ui.notify("Path scan complete", type="positive")
            _pf_view.refresh()
        except Exception as exc:
            ui.notify(f"Path scan failed: {exc}", type="negative")

    ui.button("Run path scan", icon="route", on_click=_run).props("outline")
    _pf_view(session)


@ui.refreshable
def _pf_view(session: DesignSession) -> None:
    rep = session.pf_last
    if not isinstance(rep, dict):
        return
    ui.label(f"First robust-pass: {rep.get('first_robust_pass')}").classes("text-caption")
    rows = rep.get("rows") or []
    if rows:
        cols = list(rows[0].keys())[:8]
        ui.table(
            columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in cols],
            rows=[{c: r.get(c) for c in cols} for r in rows[:50]],
            row_key=cols[0],
        ).classes("w-full")
