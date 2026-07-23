"""Forge instrument computation engine — full Streamlit workbench parity."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ui_nicegui.lib.forge_expert_signals import (
    constraint_spend_rate,
    first_kill,
    regime_signature,
    scan_grounding,
)
from ui_nicegui.lib.forge_interpret_helpers import (
    design_card_markdown,
    enrich_candidate_instruments,
    ladder_histogram_rows,
    summarize_conflict_atlas,
    update_conflict_atlas,
    why_not_for_candidate,
)
from ui_nicegui.lib.forge_machine_finder_helpers import (
    evaluate_forge_candidate,
    intent_from_label,
    resistance_atlas_rows,
    summarize_workbench_run,
)
from ui_nicegui.session import DesignSession


@dataclass
class InstrumentView:
    caption: str = ""
    kpis: List[Tuple[str, str]] = field(default_factory=list)
    markdown: str = ""
    json_blob: Any = None
    json_expanded: bool = False
    table_rows: Optional[List[dict]] = None
    table_columns: Optional[List[dict]] = None
    table_row_key: str = "idx"
    download: Optional[Tuple[bytes, str, str]] = None
    error: str = ""


@dataclass
class ForgeContext:
    session: DesignSession
    run: dict
    intent: str
    archive: list
    filtered_archive: list
    trace: list
    candidate: Optional[dict]
    scan_artifact: Optional[dict]
    var_keys: list
    constraint_names: list


def filter_archive(
    archive: list,
    *,
    only_robust: bool = False,
    min_score: float = float("-inf"),
    max_coe: Optional[float] = None,
) -> list:
    out: list = []
    for a in archive or []:
        if not isinstance(a, dict):
            continue
        if only_robust:
            try:
                if float(a.get("min_signed_margin", -1.0)) < 0:
                    continue
            except (TypeError, ValueError):
                continue
        if min_score > float("-inf"):
            try:
                if float(a.get("_score", -1e30)) < min_score:
                    continue
            except (TypeError, ValueError):
                pass
        if max_coe is not None:
            cost = a.get("cost") or {}
            try:
                coe = float(cost.get("COE_proxy") or cost.get("LCOE_USD_per_MWh") or float("inf"))
                if coe > max_coe:
                    continue
            except (TypeError, ValueError):
                pass
        out.append(a)
    return out


def _var_keys_from_run(run: dict) -> list:
    keys: list = []
    for v in run.get("var_specs") or []:
        if isinstance(v, dict) and v.get("key"):
            keys.append(str(v["key"]))
        else:
            try:
                keys.append(str(getattr(v, "key")))
            except Exception:
                pass
    return keys


def _constraint_names_from_archive(archive: list) -> list:
    names: list = []
    for a in archive or []:
        for c in a.get("constraints") or []:
            nm = str(c.get("name") or "")
            if nm and nm not in names:
                names.append(nm)
        if names:
            break
    return names


def _prepare_candidate(cand: dict, intent: str) -> dict:
    c = dict(cand)
    inst = enrich_candidate_instruments(c, intent)
    for k in ("closure_bundle", "margin_budget", "reality_gates", "report_pack"):
        if k in inst and inst[k] is not None:
            c[k] = inst[k]
    return c


def build_context(session: DesignSession) -> ForgeContext:
    run = session.forge_workbench_run if isinstance(session.forge_workbench_run, dict) else {}
    archive = list(run.get("archive") or [])
    filt = filter_archive(
        archive,
        only_robust=bool(session.forge_filter_robust),
        min_score=float(session.forge_filter_min_score or float("-inf")),
        max_coe=session.forge_filter_max_coe,
    )
    intent = str(run.get("intent") or intent_from_label(session.forge_mf_intent_label))
    cand = None
    if filt:
        idx = min(max(int(session.forge_inspect_idx or 0), 0), len(filt) - 1)
        cand = _prepare_candidate(filt[idx], intent)
    scan_art = getattr(session, "scan_last", None)
    if not isinstance(scan_art, dict):
        scan_art = None
    return ForgeContext(
        session=session,
        run=run,
        intent=intent,
        archive=archive,
        filtered_archive=filt,
        trace=list(run.get("trace") or []),
        candidate=cand,
        scan_artifact=scan_art,
        var_keys=_var_keys_from_run(run),
        constraint_names=_constraint_names_from_archive(archive),
    )


def compute_instrument(tool: str, ctx: ForgeContext) -> InstrumentView:
    handlers = {
        "Run dashboard": _inst_run_dashboard,
        "Forge timeline": _inst_forge_timeline,
        "Trace telemetry": _inst_trace_telemetry,
        "Budget allocation": _inst_budget_allocation,
        "Resistance brief": _inst_resistance_brief,
        "Filtered archive": _inst_filtered_archive,
        "Archive regimes & coverage": _inst_archive_regimes,
        "Machine existence report": _inst_existence_report,
        "Feasibility skeleton": _inst_feasibility_skeleton,
        "Pareto (multi-objective)": _inst_pareto,
        "Machine dossier": _inst_machine_dossier,
        "Review Trinity": _inst_review_trinity,
        "Attack simulation": _inst_attack_simulation,
        "Expert compare": _inst_expert_compare,
        "Casebook runner": _inst_casebook,
        "Closure certificate": _inst_closure_certificate,
        "Reactor accounting console": _inst_accounting_console,
        "Margin ledger": _inst_margin_ledger,
        "Reality gates": _inst_reality_gates,
        "Engineering reality budget": _inst_reality_budget,
        "Failure-mode canon": _inst_failure_canon,
        "Economics deck": _inst_economics_deck,
        "Report pack": _inst_report_pack,
        "Design narrative": _inst_design_narrative,
        "Design card": _inst_design_card,
        "Design packet": _inst_design_packet,
        "Design class": _inst_design_class,
        "Citation blocks": _inst_citation_blocks,
        "Reference reproduction": _inst_reference_reproduction,
        "Reviewer packet": _inst_reviewer_packet,
        "Conflict atlas": _inst_conflict_atlas,
        "Boundary navigator": _inst_boundary_navigator,
        "Constraint spend map": _inst_spend_map,
        "Robustness envelope": _inst_robustness_envelope,
        "Design navigation (steering)": _inst_design_navigation,
        "Scan ↔ Forge grounding": _inst_scan_grounding,
        "Inverse design / Why not?": _inst_why_not,
        "Discovered relations": _inst_discovered_relations,
        "Counterfactual lens": _inst_counterfactual,
        "Intent trajectories": _inst_intent_trajectories,
        "Confidence sweep": _inst_confidence_sweep,
        "Sensitivity fingerprint": _inst_sensitivity_fingerprint,
        "Local cartography": _inst_local_cartography,
        "Uncertainty (Monte Carlo)": _inst_monte_carlo,
        "Counter-optimization": _inst_counter_optimization,
        "Epistemic gap map": _inst_epistemic_gap,
        "Constraint personas": _inst_constraint_personas,
        "Design genealogy": _inst_design_genealogy,
        "Lineage graph": _inst_lineage_graph,
        "Provenance graph": _inst_provenance_graph,
        "Process of elimination": _inst_elimination,
        "Do-not-build brief": _inst_do_not_build,
        "Paper-ready signals": _inst_paper_signals,
        "Exposure readiness": _inst_exposure_readiness,
        "PROCESS parity benchmarks": _inst_process_parity,
        "Parity validation packs": _inst_parity_validation,
        "Parity calibration": _inst_parity_calibration,
        "Decision scenarios": _inst_decision_scenarios,
        "Collaboration (review sessions)": _inst_collaboration,
        "Epistemic guarantees": _inst_epistemic_guarantees,
        "Standards & DOI export": _inst_doi_export,
        "Design-space verdicts": _inst_design_verdicts,
        "Epistemic confidence bounds": _inst_confidence_bounds,
        "Intent-conditional design laws": _inst_intent_laws,
        "Machine genealogy": _inst_machine_genealogy,
        "Reproducibility": _inst_reproducibility,
        "Silence mode": _inst_silence_mode,
    }
    fn = handlers.get(tool)
    if fn is None:
        return InstrumentView(error=f"Unknown instrument: {tool}")
    try:
        return fn(ctx)
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _need_cand(ctx: ForgeContext) -> Optional[dict]:
    return ctx.candidate


def _inst_run_dashboard(ctx: ForgeContext) -> InstrumentView:
    s = summarize_workbench_run(ctx.run)
    tr = ctx.trace
    n_f = sum(1 for t in tr if bool(t.get("feasible")))
    return InstrumentView(
        kpis=[
            ("Intent", str(s.get("intent", "-"))),
            ("Trace", f"{n_f}/{len(tr)} feasible"),
            ("Archive", f"{s.get('n_feasible_archive')}/{s.get('n_archive')}"),
            ("Top blocker", str(s.get("top_blocker") or "-")),
        ],
        json_blob={
            "run_contract": {
                "intent": ctx.run.get("intent"),
                "seed": ctx.run.get("seed"),
                "lens": ctx.run.get("lens_contract") or ctx.session.forge_lens_contract,
            },
            "resistance_report_headline": ctx.run.get("resistance_report"),
        },
    )


def _inst_forge_timeline(ctx: ForgeContext) -> InstrumentView:
    rows = []
    for i, t in enumerate(ctx.trace[:500]):
        rows.append({
            "step": i,
            "phase": t.get("phase") or t.get("step") or "",
            "feasible": bool(t.get("feasible")),
            "score": t.get("_score"),
            "failure_mode": t.get("failure_mode") or "",
        })
    cols = [
        {"name": "step", "label": "#", "field": "step"},
        {"name": "phase", "label": "Phase", "field": "phase", "align": "left"},
        {"name": "feasible", "label": "OK", "field": "feasible"},
        {"name": "score", "label": "Score", "field": "score"},
        {"name": "failure_mode", "label": "Failure", "field": "failure_mode", "align": "left"},
    ]
    return InstrumentView(
        caption="Timeline strip of evaluations (phases + scores).",
        table_rows=rows,
        table_columns=cols,
        table_row_key="step",
    )


def _inst_trace_telemetry(ctx: ForgeContext) -> InstrumentView:
    scores = [t.get("_score") for t in ctx.trace if t.get("_score") is not None]
    return InstrumentView(
        caption="Score progression over trace evaluations.",
        kpis=[("Evaluations", str(len(ctx.trace))), ("Scored", str(len(scores)))],
        json_blob={"score_tail": scores[-50:]},
    )


def _inst_budget_allocation(ctx: ForgeContext) -> InstrumentView:
    ba = ctx.run.get("budget_allocation")
    if not isinstance(ba, dict):
        return InstrumentView(caption="No budget allocation recorded for this run.")
    return InstrumentView(json_blob=ba, json_expanded=True)


def _inst_resistance_brief(ctx: ForgeContext) -> InstrumentView:
    return InstrumentView(
        json_blob={
            "resistance": ctx.run.get("resistance"),
            "variable_correlations": ctx.run.get("variable_correlations"),
            "resistance_report": ctx.run.get("resistance_report"),
        },
    )


def _inst_filtered_archive(ctx: ForgeContext) -> InstrumentView:
    rows = []
    for i, a in enumerate(ctx.filtered_archive[:80]):
        inp = a.get("inputs") or {}
        rows.append({
            "idx": i,
            "feasible": bool(a.get("feasible")),
            "score": a.get("_score"),
            "R0_m": inp.get("R0_m"),
            "min_margin": a.get("min_signed_margin"),
            "failure": a.get("failure_mode") or "-",
        })
    return InstrumentView(
        caption=f"{len(ctx.filtered_archive)}/{len(ctx.archive)} candidates after filters.",
        table_rows=rows,
        table_columns=[
            {"name": "idx", "label": "#", "field": "idx"},
            {"name": "feasible", "label": "OK", "field": "feasible"},
            {"name": "score", "label": "Score", "field": "score"},
            {"name": "R0_m", "label": "R0", "field": "R0_m"},
            {"name": "min_margin", "label": "Min margin", "field": "min_margin"},
            {"name": "failure", "label": "Failure", "field": "failure", "align": "left"},
        ],
    )


def _inst_archive_regimes(ctx: ForgeContext) -> InstrumentView:
    hist = ladder_histogram_rows(ctx.archive)
    summ = {}
    try:
        from tools.sandbox.archive_intelligence import regime_clusters_summary

        summ = regime_clusters_summary(
            archive=ctx.archive,
            var_keys=ctx.var_keys,
            max_k=10,
            seed=int(ctx.run.get("seed", 0) or 0),
        )
    except Exception as exc:
        summ = {"ok": False, "reason": str(exc)}
    return InstrumentView(
        caption="Feasibility ladder + regime clusters (descriptive only).",
        table_rows=hist,
        table_columns=[
            {"name": "bucket", "label": "Bucket", "field": "bucket", "align": "left"},
            {"name": "count", "label": "Count", "field": "count"},
        ],
        table_row_key="bucket",
        json_blob=summ,
    )


def _inst_existence_report(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    try:
        from tools.sandbox.existence_report import existence_report

        return InstrumentView(json_blob=existence_report(cand))
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_feasibility_skeleton(ctx: ForgeContext) -> InstrumentView:
    sk = ctx.run.get("feasibility_skeleton") or {}
    if not sk:
        return InstrumentView(caption="Skeleton not available (need feasible points in run).")
    return InstrumentView(
        kpis=[
            ("Feasible points", str(sk.get("n_feasible", "-"))),
            ("Components", str(sk.get("n_components", "-"))),
        ],
        json_blob=sk,
    )


def _inst_pareto(ctx: ForgeContext) -> InstrumentView:
    objs = ctx.run.get("objectives") or []
    if not isinstance(objs, list) or len(objs) < 2:
        return InstrumentView(caption="Need multi-objective run (≥2 objectives).")
    feas = [a for a in ctx.filtered_archive if a.get("feasible")]
    if len(feas) < 2:
        return InstrumentView(caption="Need ≥2 feasible archive points for Pareto view.")
    keys = []
    for o in objs:
        k = o.get("key") if isinstance(o, dict) else getattr(o, "key", None)
        if k:
            keys.append(str(k))
    rows = [{k: (a.get("outputs") or {}).get(k) for k in keys} for a in feas[:40]]
    return InstrumentView(
        caption="Non-dominated subset is descriptive — not a recommendation.",
        table_rows=[{**r, "idx": i} for i, r in enumerate(rows)],
        table_columns=[{"name": "idx", "label": "#", "field": "idx"}]
        + [{"name": k, "label": k, "field": k} for k in keys],
    )


def _inst_machine_dossier(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    from ui_nicegui.lib.plant_kpi_honesty_ui import format_claim_kpi_for_table

    inp = cand.get("inputs") or {}
    out = cand.get("outputs") or {}
    if not isinstance(out, dict):
        out = {}
    feasible = bool(cand.get("feasible", False))
    from ui_nicegui.lib.compare_helpers import _pick_output

    dossier_keys = (
        ("Pfus_total_MW", "Pfus_total_MW"),
        ("P_e_net_MW", "P_e_net_MW"),
        ("Q_DT_eqv", "Q_DT_eqv"),
        ("q_div_MW_m2", "q_div_MW_m2"),
        ("min_signed_margin", "min_signed_margin"),
    )
    headline = {}
    for label, pick_key in dossier_keys:
        raw = _pick_output(out, pick_key) if pick_key != "min_signed_margin" else out.get(pick_key)
        if raw is None and pick_key == "min_signed_margin":
            raw = cand.get("min_signed_margin")
        if raw is None:
            continue
        headline[label] = format_claim_kpi_for_table(
            label, raw, feasible=feasible, point_out=out
        )
    md = (
        f"### Machine Dossier — candidate #{ctx.session.forge_inspect_idx}\n\n"
        f"**Regime:** {', '.join(regime_signature(cand)) or '-'}\n\n"
        f"**First kill:** {first_kill(cand).get('name')} (margin {first_kill(cand).get('signed_margin')})\n\n"
        f"**Feasibility:** {cand.get('feasibility_state')} · **Failure:** {cand.get('failure_mode') or 'OK'}"
    )
    if not feasible:
        md += (
            "\n\n*Headline Q / P_net / Pfus shown as diagnostic only — "
            "candidate is INFEASIBLE.*"
        )
    spend = constraint_spend_rate(cand, ctx.archive, ctx.run)
    return InstrumentView(
        markdown=md,
        kpis=[
            ("R0", f"{inp.get('R0_m', '-')} m"),
            ("Bt", f"{inp.get('Bt_T', '-')} T"),
            ("Score", str(cand.get("_score", "-"))),
            ("Q", headline.get("Q_DT_eqv", "n/a")),
            ("P_net,e", headline.get("P_e_net_MW", "n/a")),
        ],
        json_blob={
            "inputs": inp,
            "outputs_headline": headline,
            "spend_rate": spend,
            "constraints": cand.get("constraints"),
            "claim_kpi_feasible": feasible,
        },
    )


def _inst_review_trinity(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    try:
        from tools.sandbox.review_room import build_review_trinity

        sg = scan_grounding(cand, ctx.scan_artifact, intent=ctx.intent) if ctx.scan_artifact else {}
        tri = build_review_trinity(candidate=cand, scan_grounding=sg if isinstance(sg, dict) else {})
        # Source builder already applies PHYS-KPI-001; surface markdown + honest JSON download.
        md = str(tri.get("markdown") or "")
        blob = json.dumps(tri, indent=2, sort_keys=True, default=str).encode("utf-8")
        return InstrumentView(
            markdown=md,
            download=(blob, "review_trinity.json", "application/json"),
            json_blob=tri,
        )
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_attack_simulation(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    try:
        from tools.sandbox.review_room import build_attack_simulation

        cap = ctx.run.get("capsule_v2")
        atk = build_attack_simulation(candidate=cand, run_capsule=cap if isinstance(cap, dict) else None)
        md = atk.get("markdown") or ""
        return InstrumentView(markdown=md, json_blob=atk)
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_expert_compare(ctx: ForgeContext) -> InstrumentView:
    bench = ctx.session.forge_review_bench or list(range(min(3, len(ctx.filtered_archive))))
    rows = []
    for ix in bench[:12]:
        if ix >= len(ctx.filtered_archive):
            continue
        a = ctx.filtered_archive[ix]
        inp = a.get("inputs") or {}
        rows.append({
            "idx": ix,
            "feasibility_state": a.get("feasibility_state"),
            "R0_m": inp.get("R0_m"),
            "Bt_T": inp.get("Bt_T"),
            "Ip_MA": inp.get("Ip_MA"),
            "min_margin": a.get("min_signed_margin"),
            "failure": a.get("failure_mode") or "-",
        })
    return InstrumentView(
        caption="Side-by-side compare from review bench indices (no ranking).",
        table_rows=rows,
        table_columns=[
            {"name": c, "label": c.replace("_", " ").title(), "field": c, "align": "left" if c == "failure" else "left"}
            for c in ("idx", "feasibility_state", "R0_m", "Bt_T", "Ip_MA", "min_margin", "failure")
        ],
    )


def _inst_casebook(ctx: ForgeContext) -> InstrumentView:
    book = ctx.session.forge_casebook or []
    results = ctx.session.forge_casebook_results or []
    return InstrumentView(
        caption="Declare cases on Setup tab; results stored in session after run.",
        table_rows=results or book,
        table_columns=[
            {"name": "case", "label": "Case", "field": "case", "align": "left"},
            {"name": "lens", "label": "Lens", "field": "lens"},
            {"name": "n_eval", "label": "Evals", "field": "n_eval"},
            {"name": "n_feasible", "label": "Feasible", "field": "n_feasible"},
        ] if results else [
            {"name": "name", "label": "Name", "field": "name", "align": "left"},
            {"name": "lens", "label": "Lens", "field": "lens"},
        ],
        table_row_key="case" if results else "name",
        json_blob={"casebook": book, "results": results},
    )


def _inst_closure_certificate(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    try:
        from tools.sandbox.closure_certificate import build_closure_certificate
        from ui_nicegui.lib.forge_interpret_helpers import watermark_forge_report_pack

        feasible = bool(cand.get("feasible", False))
        cert = cand.get("closure_certificate") or build_closure_certificate(cand)
        # Reuse report-pack watermark path for key_numbers via a thin wrap.
        wrapped = watermark_forge_report_pack(
            {"json": {"closure_certificate": cert, "key_outputs": {}, "closure_bundle": {}}},
            feasible=feasible,
            point_out=cand.get("outputs") if isinstance(cand.get("outputs"), dict) else None,
        )
        cert_disp = (wrapped.get("json") or {}).get("closure_certificate") or cert
        blob = json.dumps(cert_disp, indent=2, sort_keys=True, default=str).encode("utf-8")
        caption = ""
        if not feasible:
            caption = (
                "PHYS-KPI-001: key_numbers claim FoMs are diagnostic on INFEASIBLE — not design claims."
            )
        return InstrumentView(
            caption=caption,
            kpis=[("Verdict", str(cert_disp.get("verdict", "-")))],
            json_blob=cert_disp,
            download=(blob, "shams_closure_certificate.json", "application/json"),
        )
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_accounting_console(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    from ui_nicegui.lib.forge_interpret_helpers import watermark_forge_closure_bundle

    feasible = bool(cand.get("feasible", False))
    raw = cand.get("closure_bundle") or {}
    disp = watermark_forge_closure_bundle(
        raw if isinstance(raw, dict) else {},
        feasible=feasible,
        point_out=cand.get("outputs") if isinstance(cand.get("outputs"), dict) else None,
    )
    return InstrumentView(
        caption=(
            "Explicit plant closure (derived). No hidden penalties."
            if feasible
            else "PHYS-KPI-001: net_electric / claim FoMs are diagnostic on INFEASIBLE — not design claims."
        ),
        json_blob=disp,
    )


def _inst_margin_ledger(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    mb = cand.get("margin_budget") or {}
    rows = mb.get("rows") or []
    if rows:
        return InstrumentView(
            table_rows=rows,
            table_columns=[{"name": k, "label": k, "field": k, "align": "left"} for k in rows[0].keys()],
            table_row_key=list(rows[0].keys())[0],
        )
    return InstrumentView(json_blob=mb)


def _inst_reality_gates(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    return InstrumentView(json_blob=cand.get("reality_gates") or {})


def _inst_reality_budget(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    mb = cand.get("margin_budget") or {}
    rows = mb.get("rows") or []
    groups: dict = {"plasma": [], "materials": [], "thermal": [], "economics": [], "other": []}
    for r in rows:
        nm = str(r.get("name") or "").lower()
        if any(k in nm for k in ("q95", "bet", "greenwald", "plasma")):
            groups["plasma"].append(r)
        elif any(k in nm for k in ("sigma", "stress", "hts", "coil")):
            groups["materials"].append(r)
        elif any(k in nm for k in ("q_div", "heat", "divert", "thermal")):
            groups["thermal"].append(r)
        elif any(k in nm for k in ("coe", "cost", "econ", "net")):
            groups["economics"].append(r)
        else:
            groups["other"].append(r)
    return InstrumentView(json_blob=groups, json_expanded=True)


def _inst_failure_canon(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    canon = {
        "heat-flux dominated": ["q_div", "divertor"],
        "stress-limited": ["sigma", "stress"],
        "hts-margin collapse": ["hts"],
        "breeding-limited": ["tbr"],
        "recirculation-trapped": ["recirc", "net"],
    }
    fm = str(cand.get("failure_mode") or "").lower()
    tag = "unclassified"
    for k, toks in canon.items():
        if any(t in fm for t in toks):
            tag = k
            break
    return InstrumentView(
        kpis=[("Archetype", tag), ("Failure mode", str(cand.get("failure_mode") or "-"))],
        json_blob=canon,
    )


def _inst_economics_deck(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    try:
        from src.models.inputs import PointInputs
        from src.parity import parity_costing_envelope, parity_costing
        from ui_nicegui.lib.plant_kpi_honesty_ui import format_claim_kpi_for_table

        pi = PointInputs(**dict(cand.get("inputs") or {}))
        outputs = dict(cand.get("outputs") or {})
        env = parity_costing_envelope(pi, outputs)
        base = parity_costing(pi, outputs)
        derived = base.get("derived") if isinstance(base.get("derived"), dict) else {}
        lcoe_raw = derived.get("LCOE_USD_per_MWh", float("nan"))
        # Stamp derived LCOE onto outputs so plant honesty can resolve it when feasible.
        if "LCOE_proxy_USD_per_MWh" not in outputs and lcoe_raw == lcoe_raw:
            outputs = {**outputs, "LCOE_proxy_USD_per_MWh": lcoe_raw}
        feasible = bool(cand.get("feasible", False))
        if feasible:
            lcoe_disp = format_claim_kpi_for_table(
                "LCOE_USD_per_MWh", lcoe_raw, feasible=True, point_out=outputs
            )
        else:
            lcoe_disp = "— (diagnostic)"
        return InstrumentView(
            caption=(
                ""
                if feasible
                else "LCOE watermarked — candidate is INFEASIBLE (proxy bookkeeping only)."
            ),
            kpis=[
                ("CAPEX MUSD (proxy)", f"{derived.get('CAPEX_MUSD', float('nan')):.3g}"),
                ("LCOE", lcoe_disp),
            ],
            json_blob={"envelope": env, "base": base},
        )
    except Exception as exc:
        cb = cand.get("closure_bundle") or {}
        return InstrumentView(json_blob=cb, error=str(exc) if not cb else "")


def _inst_report_pack(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    from ui_nicegui.lib.forge_interpret_helpers import watermark_forge_report_pack

    feasible = bool(cand.get("feasible", False))
    rp_raw = cand.get("report_pack") or {}
    # Prefer enriched instruments if already on candidate via workbench path.
    rp = watermark_forge_report_pack(
        rp_raw if isinstance(rp_raw, dict) else {},
        feasible=feasible,
        point_out=cand.get("outputs") if isinstance(cand.get("outputs"), dict) else None,
    )
    md = rp.get("markdown") or "(no report)"
    return InstrumentView(
        caption=(
            ""
            if feasible
            else "PHYS-KPI-001: report pack claim FoMs are diagnostic on INFEASIBLE — not design claims."
        ),
        markdown=str(md),
        json_blob=rp.get("json") or rp,
        download=(str(md).encode("utf-8"), "shams_forge_report.md", "text/markdown"),
    )


def _inst_design_narrative(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    try:
        from tools.sandbox.narrative_pack import build_narrative

        c = dict(cand)
        if ctx.intent and not (c.get("design_intent") or c.get("intent")):
            c["intent"] = str(ctx.intent)
        nar = build_narrative(c)
        md = nar.get("markdown") if isinstance(nar, dict) else str(nar)
        return InstrumentView(markdown=str(md or ""), json_blob=nar if isinstance(nar, dict) else None)
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_design_card(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    md = design_card_markdown(cand, ctx.intent)
    return InstrumentView(markdown=md or "(empty)", download=(md.encode("utf-8"), "design_card.md", "text/markdown") if md else None)


def _inst_design_packet(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    try:
        from tools.sandbox.design_packet import build_design_packet_files
        from tools.sandbox.narrative_pack import build_narrative

        c = dict(cand)
        if ctx.intent and not (c.get("design_intent") or c.get("intent")):
            c["intent"] = str(ctx.intent)
        card_md = design_card_markdown(c, ctx.intent)
        nar = build_narrative(c)
        narrative_md = str(nar.get("markdown") or "") if isinstance(nar, dict) else ""
        files = build_design_packet_files(
            title=f"Design Packet — {c.get('id') or c.get('candidate_id') or 'candidate'}",
            card_md=card_md,
            narrative_md=narrative_md,
            candidate=c,
        )
        blob: Dict[str, Any] = {
            "files": [k for k in ("markdown", "pdf_bytes", "schema", "ok", "note") if isinstance(files, dict) and k in files],
            "schema": files.get("schema") if isinstance(files, dict) else None,
            "ok": files.get("ok") if isinstance(files, dict) else False,
            "note": files.get("note") if isinstance(files, dict) else None,
        }
        md = str(files.get("markdown") or "") if isinstance(files, dict) else ""
        return InstrumentView(markdown=md or "(empty)", json_blob=blob)
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_design_class(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    try:
        from tools.sandbox.design_classes import classify_candidate

        return InstrumentView(json_blob=classify_candidate(cand))
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_citation_blocks(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.citation_blocks import build_citation_blocks

        root = Path(__file__).resolve().parents[2]
        return InstrumentView(json_blob=build_citation_blocks(root))
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_reference_reproduction(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    try:
        from tools.sandbox.history_repro import history_repro_bundle

        bundle = history_repro_bundle(cand)
        feasible = bool(cand.get("feasible", False))
        caption = (
            "PHYS-KPI-001: Q / Pfus / P_net deltas vs historical anchors are diagnostic "
            "on INFEASIBLE — not design claims."
            if not feasible
            else "Reference comparisons are contextual anchors, not targets."
        )
        return InstrumentView(caption=caption, json_blob=bundle)
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_reviewer_packet(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    try:
        from tools.sandbox.reviewer_packet_builder import ReviewerPacketOptions, build_reviewer_packet_zip

        sg = scan_grounding(cand, ctx.scan_artifact, intent=ctx.intent) if ctx.scan_artifact else None
        opts = ReviewerPacketOptions(include_scan_grounding=bool(sg))
        root = Path(__file__).resolve().parents[2]
        zip_bytes, summary = build_reviewer_packet_zip(
            candidate=cand,
            repo_root=root,
            run_capsule=ctx.run,
            scan_grounding=sg,
            options=opts,
        )
        return InstrumentView(
            json_blob=summary,
            download=(zip_bytes, "shams_reviewer_packet.zip", "application/zip"),
        )
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_conflict_atlas(ctx: ForgeContext) -> InstrumentView:
    atlas = update_conflict_atlas(ctx.session.forge_conflict_atlas, ctx.run.get("resistance_report"))
    ctx.session.forge_conflict_atlas = atlas
    rows = summarize_conflict_atlas(atlas, top_n=25)
    if not rows:
        return InstrumentView(caption="No conflicts accumulated yet.")
    cols = [{"name": k, "label": k.replace("_", " ").title(), "field": k, "align": "left"} for k in rows[0].keys()]
    blob = json.dumps(atlas, indent=2, sort_keys=True, default=str).encode("utf-8")
    return InstrumentView(
        table_rows=rows,
        table_columns=cols,
        table_row_key=list(rows[0].keys())[0],
        download=(blob, "shams_conflict_atlas.json", "application/json"),
    )


def _inst_boundary_navigator(ctx: ForgeContext) -> InstrumentView:
    cn = ctx.session.forge_surface_constraint or (ctx.constraint_names[0] if ctx.constraint_names else "")
    if not ctx.var_keys or not cn:
        return InstrumentView(error="Need var specs and constraint records in archive.")
    try:
        from tools.sandbox.advanced_features import constraint_surface_map

        m = constraint_surface_map(archive=ctx.filtered_archive or ctx.archive, var_keys=ctx.var_keys, constraint_name=cn)
        return InstrumentView(caption=f"Local linear surface for **{cn}**.", json_blob=m)
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_spend_map(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.spend_map import build_spend_scatter

        m = build_spend_scatter(ctx.filtered_archive or ctx.archive, color_by="min_margin")
        return InstrumentView(json_blob=m)
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_robustness_envelope(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.robustness_envelope import robustness_envelope_from_records

        recs = []
        for a in ctx.filtered_archive:
            recs.append({"inputs": a.get("inputs"), "feasible": a.get("feasible"), "min_margin": a.get("min_signed_margin")})
        env = robustness_envelope_from_records(recs, var_keys=ctx.var_keys[:2] if ctx.var_keys else ["R0_m", "Ip_MA"])
        return InstrumentView(json_blob=env)
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_design_navigation(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.advanced_features import constraint_surface_map
        from tools.sandbox.design_navigation import filter_cues, steering_cues_from_surface_map

        if not ctx.var_keys or not ctx.constraint_names:
            return InstrumentView(error="Need archive with constraints.")
        cn = ctx.constraint_names[0]
        smap = constraint_surface_map(archive=ctx.archive, var_keys=ctx.var_keys, constraint_name=cn)
        cues = steering_cues_from_surface_map(smap)
        return InstrumentView(json_blob=filter_cues(cues))
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_scan_grounding(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    if not ctx.scan_artifact:
        return InstrumentView(caption="No Scan Lab artifact in session — run Scan Lab first.")
    sg = scan_grounding(cand, ctx.scan_artifact, intent=ctx.intent)
    return InstrumentView(json_blob=sg)


def _inst_why_not(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    wn = why_not_for_candidate(cand, ctx.intent)
    return InstrumentView(json_blob=wn)


def _inst_discovered_relations(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.tier56 import discovered_relations, export_relations_markdown

        rel = discovered_relations(ctx.filtered_archive or ctx.archive, var_keys=ctx.var_keys)
        md = export_relations_markdown(rel)
        return InstrumentView(markdown=md, json_blob=rel)
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_counterfactual(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    try:
        from tools.sandbox.tier56 import counterfactual_gate

        return InstrumentView(json_blob=counterfactual_gate(cand, intent=ctx.intent))
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_intent_trajectories(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.tier56 import build_intent_trajectory

        traj = build_intent_trajectory(ctx.archive, intent=ctx.intent)
        return InstrumentView(json_blob=traj)
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_confidence_sweep(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    try:
        from tools.sandbox.confidence_sweep import confidence_sweep

        cons = cand.get("constraints") if isinstance(cand.get("constraints"), list) else []
        closure = cand.get("closure_bundle") if isinstance(cand.get("closure_bundle"), dict) else {}
        feasible = bool(cand.get("feasible", False))
        sweep = confidence_sweep(
            cons,
            closure_bundle=closure,
            feasible=feasible,
        )
        caption = (
            "PHYS-KPI-001: proxy_headlines net electric / LCOE are diagnostic on "
            "INFEASIBLE — not design claims."
            if not feasible
            else "Margin + proxy uncertainty sweep (descriptive; frozen truth unchanged)."
        )
        return InstrumentView(caption=caption, json_blob=sweep)
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_sensitivity_fingerprint(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    try:
        from tools.sandbox.sensitivity_fingerprint import build_fingerprint

        def _eval(inp: dict) -> dict:
            return evaluate_forge_candidate(inp, ctx.intent)

        return InstrumentView(json_blob=build_fingerprint(cand, _eval))
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_local_cartography(ctx: ForgeContext) -> InstrumentView:
    df = ctx.session.forge_localcart_df
    if df is None:
        return InstrumentView(caption="Configure axes and click **Run local cartography** above.")
    if isinstance(df, list):
        return InstrumentView(table_rows=df, table_columns=[
            {"name": "x", "label": "x", "field": "x"},
            {"name": "y", "label": "y", "field": "y"},
            {"name": "feasible", "label": "OK", "field": "feasible"},
            {"name": "min_margin", "label": "Margin", "field": "min_margin"},
        ])
    return InstrumentView(json_blob=df)


def run_local_cartography(ctx: ForgeContext, session: DesignSession) -> list:
    import numpy as np

    base = ctx.candidate or (ctx.filtered_archive[0] if ctx.filtered_archive else None)
    if not base:
        raise RuntimeError("No candidate to center on")
    xk = session.forge_localcart_x or ctx.var_keys[0]
    yk = session.forge_localcart_y or ctx.var_keys[min(1, len(ctx.var_keys) - 1)]
    span = float(session.forge_localcart_span or 20)
    ngrid = int(session.forge_localcart_grid or 21)
    vs = ctx.run.get("var_specs") or []
    bmap = {v.get("key"): (float(v.get("lo")), float(v.get("hi"))) for v in vs if isinstance(v, dict) and v.get("key")}
    bx = (base.get("inputs") or {}).get(xk)
    by = (base.get("inputs") or {}).get(yk)
    xlo, xhi = bmap.get(xk, (float(bx) * 0.8, float(bx) * 1.2))
    ylo, yhi = bmap.get(yk, (float(by) * 0.8, float(by) * 1.2))
    xmid = float(bx) if bx is not None else 0.5 * (xlo + xhi)
    ymid = float(by) if by is not None else 0.5 * (ylo + yhi)
    dx = (xhi - xlo) * span / 100.0
    dy = (yhi - ylo) * span / 100.0
    xs = np.linspace(max(xlo, xmid - dx), min(xhi, xmid + dx), ngrid)
    ys = np.linspace(max(ylo, ymid - dy), min(yhi, ymid + dy), ngrid)
    rows = []
    for xv in xs:
        for yv in ys:
            cand_in = dict(base.get("inputs") or {})
            cand_in[xk] = float(xv)
            cand_in[yk] = float(yv)
            r = evaluate_forge_candidate(cand_in, ctx.intent)
            rows.append({
                "x": float(xv),
                "y": float(yv),
                "feasible": bool(r.get("feasible")),
                "score": float(r.get("_score", -1e30)),
                "min_margin": float(r.get("min_signed_margin", float("nan"))),
            })
    session.forge_localcart_df = rows
    return rows


def _inst_monte_carlo(ctx: ForgeContext) -> InstrumentView:
    res = ctx.session.forge_uq_result
    if not isinstance(res, dict):
        return InstrumentView(caption="Configure samples and click **Run robustness Monte Carlo** above.")
    return InstrumentView(
        kpis=[
            ("Feasible rate", f"{100 * float(res.get('feasible_rate', 0)):.1f}%"),
            ("N feasible", str(res.get("n_feasible", "-"))),
        ],
        json_blob=res,
    )


def run_robustness_mc(ctx: ForgeContext, session: DesignSession) -> dict:
    import numpy as np

    cand = ctx.candidate or (ctx.filtered_archive[0] if ctx.filtered_archive else None)
    if not cand:
        raise RuntimeError("No candidate")
    ns = int(session.forge_uq_samples or 200)
    pct = float(session.forge_uq_pct or 5)
    rng = np.random.default_rng(int(ctx.run.get("seed", 1) or 1))
    base_in = dict(cand.get("inputs") or {})
    feas = 0
    scores: list = []
    for _ in range(ns):
        ci = dict(base_in)
        for k in ctx.var_keys:
            v0 = float(base_in.get(k, 0.0))
            dv = v0 * pct / 100.0
            ci[k] = float(rng.uniform(v0 - dv, v0 + dv))
        r = evaluate_forge_candidate(ci, ctx.intent)
        if r.get("feasible"):
            feas += 1
            scores.append(float(r.get("_score", -1e30)))
    res = {
        "samples": ns,
        "pct": pct,
        "feasible_rate": float(feas) / float(ns) if ns else 0.0,
        "mean_score_feasible": float(np.mean(scores)) if scores else None,
        "n_feasible": int(feas),
    }
    session.forge_uq_result = res
    return res


def _inst_counter_optimization(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.tier89 import counter_optimization_report

        return InstrumentView(json_blob=counter_optimization_report(ctx.filtered_archive or ctx.archive))
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_epistemic_gap(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.forge_supremacy_plus import epistemic_gap_map

        ctx_map = {"run": ctx.run, "archive": ctx.archive, "trace": ctx.trace}
        return InstrumentView(json_blob=epistemic_gap_map(ctx_map))
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_constraint_personas(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.forge_supremacy_plus import constraint_personas

        return InstrumentView(json_blob=constraint_personas())
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_design_genealogy(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.forge_supremacy_plus import genealogy_markdown

        md = genealogy_markdown(ctx.archive)
        return InstrumentView(markdown=md)
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_lineage_graph(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.lineage_graph import build_lineage_edges, compute_tree_layout

        edges = build_lineage_edges(ctx.archive)
        layout = compute_tree_layout(edges)
        return InstrumentView(json_blob={"edges": edges, "layout": layout})
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_provenance_graph(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.constraint_provenance_graph import build_cpg_for_constraint

        cname = ctx.session.forge_provenance_constraint or "q_div"
        cpg = build_cpg_for_constraint(cname, intent=ctx.intent)
        blob = json.dumps(cpg, indent=2, sort_keys=True, default=str).encode("utf-8")
        return InstrumentView(json_blob=cpg, download=(blob, "constraint_provenance.json", "application/json"))
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_elimination(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.forge_supremacy_plus import elimination_narrative

        ctx_map = {"run": ctx.run, "resistance": ctx.run.get("resistance")}
        return InstrumentView(markdown=elimination_narrative(ctx_map))
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_do_not_build(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    try:
        from tools.sandbox.forge_supremacy_plus import do_not_build_brief

        return InstrumentView(json_blob=do_not_build_brief(cand, {"run": ctx.run}))
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_paper_signals(ctx: ForgeContext) -> InstrumentView:
    cand = _need_cand(ctx)
    if not cand:
        return InstrumentView(error="No candidate selected.")
    try:
        from tools.sandbox.forge_supremacy_plus import paper_ready_signals

        return InstrumentView(json_blob=paper_ready_signals(cand))
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_exposure_readiness(ctx: ForgeContext) -> InstrumentView:
    try:
        root = Path(__file__).resolve().parents[2]
        chk = (root / "docs" / "EXTERNAL_EXPOSURE_CHECKLIST.md").read_text(encoding="utf-8")
    except Exception:
        chk = "(missing docs/EXTERNAL_EXPOSURE_CHECKLIST.md)"
    return InstrumentView(
        markdown=chk,
        download=(chk.encode("utf-8"), "EXTERNAL_EXPOSURE_CHECKLIST.md", "text/markdown"),
    )


def _inst_process_parity(ctx: ForgeContext) -> InstrumentView:
    return InstrumentView(
        caption="Launch **Publication Benchmarks** or **Parity Harness** decks for PROCESS comparisons.",
        markdown="PROCESS parity is firewalled — SHAMS truth is not tuned to match external codes.",
    )


def _inst_parity_validation(ctx: ForgeContext) -> InstrumentView:
    return InstrumentView(
        caption="Use System Suite → Parity tab or Publication Benchmarks for PASS/WARN/FAIL packs.",
    )


def _inst_parity_calibration(ctx: ForgeContext) -> InstrumentView:
    return InstrumentView(caption="Reference deltas are exported from parity harness — not auto-applied.")


def _inst_decision_scenarios(ctx: ForgeContext) -> InstrumentView:
    lens = ctx.run.get("lens_contract") or ctx.session.forge_lens_contract or {}
    return InstrumentView(
        caption="Program lens contract (objectives exported with run).",
        json_blob=lens,
    )


def _inst_collaboration(ctx: ForgeContext) -> InstrumentView:
    rs = ctx.session.forge_review_session
    if isinstance(rs, dict):
        return InstrumentView(
            caption="Active review session — export ZIP for collaboration or archive.",
            json_blob=rs,
            kpis=[
                ("Session", str(rs.get("title", "-"))[:40]),
                ("Candidates", str(len(rs.get("candidates") or []))),
                ("Comments", str(len(rs.get("comments") or []))),
            ],
        )
    return InstrumentView(
        caption="Use controls above to create or import a review session.",
        markdown="Review sessions store **comments, votes, and tags** over archive candidates — descriptive only.",
    )


def _inst_epistemic_guarantees(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.tier7 import run_regression_suite

        root = Path(__file__).resolve().parents[2]
        rep = run_regression_suite(root)
        return InstrumentView(json_blob=rep)
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_doi_export(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.tier7 import export_doi_ready_pack, repo_fingerprint
        from ui_nicegui.lib.external_optimizer_helpers import watermark_extopt_zip_bytes

        root = Path(__file__).resolve().parents[2]
        run_meta = {
            "intent": ctx.intent,
            "seed": ctx.run.get("seed"),
            "evaluator_fp": repo_fingerprint(root),
        }
        for k in ("objectives", "bounds", "provenance", "var_specs", "pack_name"):
            if k in (ctx.run or {}):
                run_meta[k] = ctx.run.get(k)
        blob = export_doi_ready_pack(
            repo_root=root,
            run_meta=run_meta,
            archive_rows=list(ctx.archive or []),
            trace_rows=list(ctx.trace or []),
        )
        blob = watermark_extopt_zip_bytes(blob)
        return InstrumentView(
            caption="DOI-ready pack (PHYS-KPI-001 watermarked on INFEASIBLE archive rows).",
            json_blob={"n_archive": len(ctx.archive or []), "n_trace": len(ctx.trace or []), "run_meta_keys": sorted(run_meta)},
            download=(blob, "shams_doi_pack.zip", "application/zip"),
        )
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_design_verdicts(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.tier89 import candidate_verdict, region_verdict

        cand = ctx.candidate
        cv = {}
        if cand:
            v = candidate_verdict(cand, ctx.filtered_archive or ctx.archive, ctx.var_keys or ["R0_m"])
            cv = {"label": v.label, "confidence": v.confidence, "rationale": v.rationale}
        rv = region_verdict(ctx.trace)
        return InstrumentView(json_blob={"candidate": cv, "region": {"label": rv.label, "confidence": rv.confidence, "rationale": rv.rationale}})
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_confidence_bounds(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.tier89 import feasibility_confidence_from_trace

        return InstrumentView(json_blob=feasibility_confidence_from_trace(ctx.trace))
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_intent_laws(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.tier89 import intent_conditional_laws

        return InstrumentView(json_blob=intent_conditional_laws(ctx.archive, intent=ctx.intent))
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_machine_genealogy(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.tier89 import reconstruct_genealogy

        return InstrumentView(json_blob=reconstruct_genealogy(ctx.archive))
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_reproducibility(ctx: ForgeContext) -> InstrumentView:
    try:
        from tools.sandbox.tier7 import candidate_fingerprint, repo_fingerprint

        root = Path(__file__).resolve().parents[2]
        cand = ctx.candidate
        fp = candidate_fingerprint(cand.get("inputs") or {}, intent=ctx.intent, evaluator_fp=repo_fingerprint(root)) if cand else {}
        return InstrumentView(
            json_blob={
                "repo_fingerprint": repo_fingerprint(root),
                "candidate_fingerprint": fp,
                "run_seed": ctx.run.get("seed"),
            },
        )
    except Exception as exc:
        return InstrumentView(error=str(exc))


def _inst_silence_mode(ctx: ForgeContext) -> InstrumentView:
    return InstrumentView(
        markdown="**Silence Mode active** — review-room calm. No celebratory UI; physics unchanged.",
        caption="Toggle is display-only in NiceGUI; use Review Mode to lock exploration controls.",
    )
