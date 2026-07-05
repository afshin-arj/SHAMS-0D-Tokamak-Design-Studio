"""Trade Study Studio advanced decks — Phase 17."""
from __future__ import annotations

import json

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
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
from ui_nicegui.lib.trade_study_helpers import ADVANCED_DECKS, objectives_catalog
from ui_nicegui.session import DesignSession

try:
    from src.trade_studies.spec import default_knob_sets
except ImportError:
    from trade_studies.spec import default_knob_sets  # type: ignore


def render_advanced_deck(session: DesignSession, deck: str) -> None:
    render_proposal_banner(title=deck)
    if deck == "Multi-Objective Feasible Frontier Atlas (v351)":
        _render_v351(session)
    elif deck == "Robust Design Envelope Certification (v352)":
        _render_v352(session)
    elif deck == "Feasible-First Surrogate Accelerator":
        _render_surrogate_accel(session)
    elif deck == "Optimizer Kits (External)":
        _render_optimizer_kits(session)
    elif deck == "Fast Optimistic Design (Two-Lane)":
        _render_two_lane(session)
    elif deck == "Design Family Atlas":
        _render_family_atlas(session)
    elif deck == "Regime Maps & Narratives (v324)":
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
    rep = _require_trade_last(session)
    if rep is None:
        return
    obj_names, obj_senses = objectives_catalog()
    chosen = ui.select(obj_names, label="Objectives", value=obj_names[:2], multiple=True).classes("w-full")

    async def _run() -> None:
        objs = list(chosen.value) if chosen.value else []
        if len(objs) < 1:
            ui.notify("Select objectives", type="warning")
            return
        senses = {o: str(obj_senses.get(o, "min")) for o in objs}
        try:
            atlas = await run.io_bound(build_v351_atlas, session, objectives=objs, senses=senses)
            session.v351_atlas_last = atlas
            ui.notify(f"Pareto subset: {atlas.get('n_pareto', 0)} points", type="positive")
            _v351_view.refresh()
        except Exception as exc:
            ui.notify(f"v351 failed: {exc}", type="negative")

    ui.button("Build v351 atlas", icon="map", on_click=_run).props("outline")
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
    ui.button(
        "Download v351 atlas JSON",
        icon="download",
        on_click=lambda: ui.download(report_to_json_bytes(atlas), "shams_frontier_atlas_v351.json"),
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
            ui.notify(f"v352 failed: {exc}", type="negative")

    ui.button("Run Robust Envelope Certification", icon="verified_user", on_click=_run).props("outline")
    _v352_view(session)


@ui.refreshable
def _v352_view(session: DesignSession) -> None:
    cert = session.v352_cert_last
    if isinstance(cert, dict):
        rep0 = cert.get("report") or {}
        with ui.expansion("Certification report", icon="description").classes("w-full"):
            ui.json(rep0)


def _render_surrogate_accel(session: DesignSession) -> None:
    rep = _require_trade_last(session)
    if rep is None:
        return
    ui.label("Surrogate proposes candidates; truth re-verifies (non-authoritative speed layer).").classes("text-caption")
    obj_names, obj_senses = objectives_catalog()
    primary = ui.select(obj_names, label="Primary acquisition objective", value=obj_names[0] if obj_names else "")
    n_prop = ui.number("Batch proposals", value=12, min=4, max=200)

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
                n_pool=1000,
                n_propose=int(n_prop.value or 12),
                seed=17,
                kappa=0.5,
            )
            session.ts_sa_candidates = cand
            ui.notify(f"Proposed {len(cand)} candidates", type="positive")
        except Exception as exc:
            ui.notify(f"Proposal failed: {exc}", type="negative")

    ui.button("Propose candidates (surrogate)", icon="bolt", on_click=_propose).props("outline")


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
            ui.notify(f"v324 failed: {exc}", type="negative")

    ui.button("Build regime map report", icon="hub", on_click=_run).props("outline")
    _v324_view(session)


@ui.refreshable
def _v324_view(session: DesignSession) -> None:
    rpt = session.v324_regime_maps
    if isinstance(rpt, dict):
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
