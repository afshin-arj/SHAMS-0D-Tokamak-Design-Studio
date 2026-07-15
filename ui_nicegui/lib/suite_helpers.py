"""System Suite shared helpers — run-lock, tab summaries, authority ledger, handoffs."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from nicegui import ui

from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.components.verdict_banner import verdict_banner
from ui_nicegui.lib.helm_helpers import log_ui_event
from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status
from ui_nicegui.lib.systems_plant_authority import build_exhaust_authority_bundle, exhaust_table_row
from ui_nicegui.session import DesignSession

SUITE_RUNLOCK_OWNER = "SystemSuite"


def _fin(v: Any, fmt: str = ".2f") -> str:
    try:
        f = float(v)
        if not math.isfinite(f):
            return "-"
        return format(f, fmt)
    except (TypeError, ValueError):
        return "-"


def try_acquire_suite_lock(session: DesignSession, task: str) -> bool:
    locked, existing, is_owner = runlock_status(SUITE_RUNLOCK_OWNER)
    if locked and not is_owner:
        ui.notify(f"Run lock busy: {existing or 'another task'}", type="warning")
        return False
    if not runlock_acquire(task, SUITE_RUNLOCK_OWNER):
        ui.notify("Run lock busy (another deck is evaluating).", type="warning")
        return False
    session.suite_running = True
    return True


def release_suite_lock(session: DesignSession) -> None:
    runlock_release(SUITE_RUNLOCK_OWNER)
    session.suite_running = False


def authority_version_badges(out: dict) -> List[str]:
    if not isinstance(out, dict):
        return []
    checks = [
        ("magnet_v400_enabled", "v400 magnets"),
        ("nm_authority_v401_enabled", "v401 neutronics"),
        ("nuclear_data_authority_v407_enabled", "v407 nuclear data"),
        ("structural_stress_v389_enabled", "v389 structural"),
        ("tritium_authority_v405_enabled", "v405 tritium"),
        ("cd_mix_plant_ledger_v408_enabled", "v408 plant ledger"),
    ]
    return [label for key, label in checks if bool(out.get(key))]


def lifetime_binding_summary(lr) -> Dict[str, Any]:
    margins = {
        "FW dpa": getattr(lr, "fw_dpa_margin", float("nan")),
        "Pulse cycles": getattr(lr, "cycles_margin", float("nan")),
        "TBR": getattr(lr, "tbr_margin", float("nan")),
    }
    binding = []
    worst_name = ""
    worst_val = float("inf")
    for name, m in margins.items():
        if math.isfinite(m) and m < 0:
            binding.append(name)
            if m < worst_val:
                worst_val = m
                worst_name = name
    return {
        "binding": binding,
        "worst_name": worst_name,
        "worst_margin": worst_val if binding else float("nan"),
        "posture": "LIFETIME BINDING" if binding else "WITHIN BUDGET",
    }


def envelope_posture_summary(session: DesignSession) -> str:
    pc = session.profile_contracts_v362_last if isinstance(session.profile_contracts_v362_last, dict) else {}
    parts: List[str] = []
    if pc:
        rob = "robust YES" if pc.get("robust_feasible") else "robust NO"
        opt = "optimistic YES" if pc.get("optimistic_feasible") else "optimistic NO"
        parts.append(f"Profile corners: {opt}, {rob}")
    if isinstance(session.suite_parity_last_report, dict):
        rows = session.suite_parity_last_report.get("summary_rows") or []
        n = len(rows)
        parts.append(f"Parity: {n} case(s) on record")
    if isinstance(session.suite_campaign_summary, dict):
        n_f = session.suite_campaign_summary.get("n_feasible", "?")
        n_t = session.suite_campaign_summary.get("n_total", "?")
        parts.append(f"Campaign: {n_f}/{n_t} feasible")
    return " · ".join(parts) if parts else "Run envelope tools or exports to populate posture."


def render_tab_summary_strip(posture: str, *, detail: str = "", kpis: Optional[List[tuple[str, str]]] = None) -> None:
    verdict_banner(posture, detail=detail)
    if kpis:
        kpi_row(kpis)


def impurity_radiation_summary(point_out: dict) -> Dict[str, Any]:
    """Read-only SOL / radiation / detachment snapshot from frozen L0 outputs."""
    o = point_out if isinstance(point_out, dict) else {}

    def _sf(key: str, default: float = float("nan")) -> float:
        try:
            v = float(o.get(key, default))
            return v if math.isfinite(v) else default
        except (TypeError, ValueError):
            return default

    q_div = _sf("q_div_MW_m2")
    q_max = _sf("q_div_max_MW_m2")
    q_margin = (q_max - q_div) if math.isfinite(q_div) and math.isfinite(q_max) else float("nan")
    binding: List[str] = []
    if math.isfinite(q_margin) and q_margin < 0:
        binding.append("q_div")
    fz_req = _sf("detachment_f_z_required")
    fz_max = _sf("detachment_fz_max")
    if math.isfinite(fz_req) and math.isfinite(fz_max) and fz_req > fz_max:
        binding.append("f_z")
    return {
        "radiation_enabled": bool(o.get("include_radiation", False)),
        "prad_core_MW": _sf("Prad_core_MW"),
        "p_sol_MW": _sf("P_SOL_MW"),
        "f_rad_div": _sf("f_rad_div"),
        "zeff": _sf("zeff"),
        "radiation_model": str(o.get("radiation_model", "-") or "-"),
        "impurity_regime": str(o.get("impurity_regime", "") or ""),
        "impurity_species": str(o.get("impurity_species", "") or ""),
        "impurity_fragility": str(o.get("impurity_fragility_class", "") or ""),
        "impurity_min_margin": _sf("impurity_min_margin_frac"),
        "q_div_MW_m2": q_div,
        "q_div_max_MW_m2": q_max,
        "q_div_margin": q_margin,
        "div_regime": str(o.get("div_regime", "") or ""),
        "exhaust_regime": str(o.get("exhaust_regime", "") or ""),
        "exhaust_fragility": str(o.get("exhaust_fragility_class", "") or ""),
        "exhaust_min_margin": _sf("exhaust_min_margin_frac"),
        "exhaust_rad_dom": _sf("exhaust_radiation_dominated") >= 0.5,
        "q_div_target": _sf("q_div_target_MW_m2"),
        "detachment_f_sol_div": _sf("detachment_f_sol_div_required"),
        "detachment_prad_req_MW": _sf("detachment_prad_sol_div_required_MW"),
        "detachment_f_z": fz_req,
        "partition": {
            "core": _sf("impurity_partition_core"),
            "edge": _sf("impurity_partition_edge"),
            "sol": _sf("impurity_partition_sol"),
            "div": _sf("impurity_partition_div"),
        },
        "binding": binding,
        "posture": "EXHAUST BINDING" if binding else "IMPURITY / RADIATION",
    }


def render_impurity_radiation_panel(point_out: dict, *, expert: bool = False) -> None:
    s = impurity_radiation_summary(point_out)
    render_tab_summary_strip(
        s["posture"],
        detail=(
            f"Binding: {', '.join(s['binding'])}"
            if s["binding"]
            else "SOL / divertor / core radiation snapshot from last Point Designer evaluation."
        ),
        kpis=[
            ("Prad_core (MW)", _fin(s["prad_core_MW"], ".1f")),
            ("P_SOL (MW)", _fin(s["p_sol_MW"], ".1f")),
            ("q_div (MW/m²)", _fin(s["q_div_MW_m2"], ".1f")),
            ("q_div margin", _fin(s["q_div_margin"], ".2f")),
        ],
    )
    ui.label(
        "Read-only impurity & radiation ledger — algebraic detachment / SOL fields from L0; not a radiation solver."
    ).classes("text-caption q-mb-sm")
    kpi_row([
        ("Radiation enabled", "YES" if s["radiation_enabled"] else "NO"),
        ("Radiation model", s["radiation_model"]),
        ("Zeff", _fin(s["zeff"])),
        ("f_rad_div", _fin(s["f_rad_div"])),
    ])
    if s["impurity_regime"] or s["impurity_species"]:
        kpi_row([
            ("Impurity regime", s["impurity_regime"] or "-"),
            ("Species", s["impurity_species"] or "-"),
            ("Fragility", s["impurity_fragility"] or "-"),
            ("Min margin (frac)", _fin(s["impurity_min_margin"], ".3f")),
        ])
    if s["exhaust_regime"] or s["div_regime"]:
        kpi_row([
            ("Divertor regime", s["div_regime"] or "-"),
            ("Exhaust regime", s["exhaust_regime"] or "-"),
            ("Exhaust fragility", s["exhaust_fragility"] or "-"),
            ("Radiation-dom", "YES" if s["exhaust_rad_dom"] else "NO"),
        ])
    if math.isfinite(s["q_div_target"]) or math.isfinite(s["detachment_f_sol_div"]):
        kpi_row([
            ("q_div target", _fin(s["q_div_target"], ".1f")),
            ("f_SOL+div req", _fin(s["detachment_f_sol_div"])),
            ("Prad_SOL+div req (MW)", _fin(s["detachment_prad_req_MW"], ".1f")),
            ("f_z required", f"{s['detachment_f_z']:.1e}" if math.isfinite(s["detachment_f_z"]) else "-"),
        ])
        ui.label(
            "Detachment authority is algebraic: q_div_target → required SOL+div radiation → implied impurity fraction."
        ).classes("text-caption text-grey")
    part = s["partition"]
    if any(math.isfinite(float(v)) for v in part.values()):
        with ui.expansion("Impurity partition (core / edge / SOL / divertor)", icon="pie_chart").classes("w-full"):
            kpi_row([
                ("Core", _fin(part["core"])),
                ("Edge", _fin(part["edge"])),
                ("SOL", _fin(part["sol"])),
                ("Divertor", _fin(part["div"])),
            ])
    if expert:
        from ui_nicegui.components.json_view import render_json_blob

        with ui.expansion("Impurity / radiation raw fields", icon="data_object").classes("w-full"):
            keys = [
                "Prad_core_MW", "P_SOL_MW", "P_SOL_over_R_MW_m", "f_rad_div", "f_rad_core",
                "q_div_MW_m2", "q_div_max_MW_m2", "q_div_target_MW_m2",
                "detachment_f_sol_div_required", "detachment_prad_sol_div_required_MW",
                "detachment_f_z_required", "impurity_regime", "exhaust_regime",
                "exhaust_authority_contract_sha256",
            ]
            render_json_blob({k: point_out.get(k) for k in keys if k in point_out})


def campaign_results_to_atlas_records(
    jsonl_bytes: Optional[bytes] = None,
    preview_rows: Optional[list] = None,
) -> List[dict]:
    """Normalize campaign batch results into Pareto Lab regime-atlas records."""
    from ui_nicegui.lib.external_optimizer_helpers import load_records_from_upload

    records: List[dict] = []
    if isinstance(jsonl_bytes, (bytes, bytearray)) and jsonl_bytes:
        records = load_records_from_upload("campaign_results.jsonl", bytes(jsonl_bytes))
    elif isinstance(preview_rows, list):
        for r in preview_rows:
            if isinstance(r, dict):
                records.append(dict(r))
            else:
                # CampaignEvalRow dataclass
                try:
                    records.append({
                        "cid": getattr(r, "cid", ""),
                        "inputs": dict(getattr(r, "inputs", {}) or {}),
                        "feasible_hard": bool(getattr(r, "feasible_hard", False)),
                        "verdict": str(getattr(r, "verdict", "")),
                        "dominant_mechanism": str(getattr(r, "dominant_mechanism", "")),
                        "worst_hard_margin": getattr(r, "worst_hard_margin", None),
                    })
                except Exception:
                    continue
    out: List[dict] = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        flat = dict(rec)
        art = rec.get("artifact") if isinstance(rec.get("artifact"), dict) else None
        if art:
            outs = art.get("outputs") if isinstance(art.get("outputs"), dict) else {}
            for k, v in outs.items():
                flat.setdefault(k, v)
            kpis = art.get("kpis") if isinstance(art.get("kpis"), dict) else {}
            for k, v in kpis.items():
                flat.setdefault(k, v)
            flat.setdefault("plasma_regime", outs.get("plasma_regime"))
            flat.setdefault("exhaust_regime", outs.get("exhaust_regime") or art.get("dominant_mechanism"))
            flat.setdefault("dominance_label", art.get("dominant_mechanism") or rec.get("dominant_mechanism"))
        else:
            flat.setdefault("dominance_label", rec.get("dominant_mechanism"))
        inputs = rec.get("inputs") if isinstance(rec.get("inputs"), dict) else {}
        for k, v in inputs.items():
            flat.setdefault(k, v)
        # Robustness class proxy for atlas gates
        if "robustness_class" not in flat:
            flat["robustness_class"] = "robust" if bool(rec.get("feasible_hard")) else "infeasible"
        out.append(flat)
    return out


def campaign_to_concept_family_yaml(
    point_inp: Optional[dict],
    candidates: list,
    *,
    name: str = "suite_campaign_family",
    intent: str = "reactor",
) -> Tuple[bytes, str]:
    """Build concept_family.v1 YAML bytes from System Suite campaign candidates."""
    import yaml

    base = dict(point_inp or {})
    cands_out: List[dict] = []
    for i, c in enumerate(candidates or []):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("cid") or c.get("id") or f"cand_{i:04d}")
        ov = {
            k: v
            for k, v in c.items()
            if k not in ("cid", "id") and (k not in base or base.get(k) != v)
        }
        cands_out.append({"id": cid, "overrides": ov})
    if not cands_out:
        raise ValueError("No campaign candidates to bridge — generate or run batch first.")
    if not base:
        # Fall back: first candidate absolute inputs as base, empty overrides for that row
        first = dict(candidates[0]) if isinstance(candidates[0], dict) else {}
        first.pop("cid", None)
        first.pop("id", None)
        base = first
        cands_out[0]["overrides"] = {}
    doc = {
        "schema_version": "concept_family.v1",
        "name": str(name),
        "intent": str(intent or "reactor"),
        "notes": "Bridged from System Suite campaign (session handoff — no re-upload).",
        "base_inputs": base,
        "candidates": cands_out,
    }
    fname = f"{name}.yaml"
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True).encode("utf-8"), fname


def bridge_campaign_to_pareto(session: DesignSession) -> Dict[str, Any]:
    """Push campaign results into Pareto Lab extopt / regime-atlas session slots."""
    records = campaign_results_to_atlas_records(
        session.suite_campaign_jsonl_bytes,
        session.suite_campaign_results_preview,
    )
    cands = session.suite_campaign_candidates
    if not records and not (isinstance(cands, list) and cands):
        raise ValueError("No campaign results or candidates — run Generate / batch first.")

    n_records = 0
    if records:
        session.regime_atlas_records = records
        n_records = len(records)

    yaml_name = ""
    if isinstance(cands, list) and cands:
        from ui_nicegui.lib.artifact_access import get_point_artifact_triple

        _, point_inp, _ = get_point_artifact_triple(session)
        summary = session.suite_campaign_summary if isinstance(session.suite_campaign_summary, dict) else {}
        intent = str(summary.get("intent") or "reactor")
        name = str(summary.get("campaign") or "suite_campaign_family")
        ybytes, yaml_name = campaign_to_concept_family_yaml(
            point_inp if isinstance(point_inp, dict) else dict(session.inputs),
            cands,
            name=name,
            intent=intent,
        )
        session.extopt_suite_upload_bytes = ybytes
        session.extopt_suite_upload_name = yaml_name
        session.extopt_copilot_yaml_bytes = ybytes
        session.extopt_copilot_yaml_name = yaml_name
        session.suite_pareto_bridge_meta = {
            "n_records": n_records,
            "n_candidates": len(cands),
            "yaml_name": yaml_name,
            "source": "System Suite campaign",
        }
    elif n_records:
        session.suite_pareto_bridge_meta = {
            "n_records": n_records,
            "n_candidates": 0,
            "yaml_name": "",
            "source": "System Suite campaign results",
        }
    return dict(session.suite_pareto_bridge_meta or {})


def render_authority_ledger(point_out: dict, *, expert: bool = False) -> None:
    from ui_nicegui.lib.pd_parity_helpers import magnet_v400_summary, power_ledger_badged_rows

    ui.label("Authority ledger (from last Point Designer evaluation)").classes("text-subtitle2")
    ui.label("Read-only drill-down — authority modules run at evaluate time, not in Suite.").classes(
        "text-caption q-mb-sm"
    )

    mag = magnet_v400_summary(point_out)
    if mag:
        kpi_row([
            ("Magnet v400 tier", str(mag.get("tier", "-"))),
            ("Combined margin", _fin(mag.get("combined_margin"), ".3f")),
            ("Dominant limiter", str(mag.get("dominant", "-"))),
        ])
    else:
        ui.label("Magnet v400 authority not enabled on this point.").classes("text-caption text-grey")

    exh = build_exhaust_authority_bundle(point_out)
    row = exhaust_table_row(exh)
    if any(math.isfinite(float(v)) if isinstance(v, (int, float)) else False for v in row.values()):
        kpi_row([(k, _fin(v, ".3g") if isinstance(v, (int, float)) else str(v)) for k, v in list(row.items())[:4]])
    else:
        ui.label("Exhaust authority fields not populated.").classes("text-caption text-grey")

    kpi_row([
        ("TBR", _fin(point_out.get("TBR", point_out.get("tbr_proxy")))),
        ("FW dpa/yr", _fin(point_out.get("fw_dpa_per_year"))),
        ("TF struct margin v389", _fin(point_out.get("tf_struct_margin_v389"), ".3f")),
        ("NM margin v401", _fin(point_out.get("nm_min_margin_frac_v401"), ".3f")),
    ])

    if expert:
        with ui.expansion("Plasma power ledger", icon="bolt").classes("w-full q-mt-sm"):
            rows = power_ledger_badged_rows(point_out, include_radiation=True)
            if rows:
                ui.table(
                    columns=[
                        {"name": "item", "label": "Item", "field": "item", "align": "left"},
                        {"name": "MW", "label": "MW", "field": "MW", "align": "left"},
                        {"name": "type", "label": "Tier", "field": "type", "align": "left"},
                    ],
                    rows=rows,
                    row_key="item",
                ).classes("w-full")


def render_suite_handoffs(session: DesignSession, point_out: dict) -> None:
    from ui_nicegui.lib.compare_helpers import artifact_from_point, send_row_to_compare_slot, store_compare_slot
    from ui_nicegui.lib.navigation import switch_deck

    ui.label("Cross-deck handoffs").classes("text-subtitle2")
    ui.label(
        "Send the loaded point or a campaign row to Compare; open Control Room for audit on the same artifact."
    ).classes("text-caption text-grey q-mb-sm")

    def _point_compare(slot: str) -> None:
        art = artifact_from_point(session)
        if not art:
            ui.notify("No Point Designer evaluation loaded.", type="warning")
            return
        store_compare_slot(session, art, slot, label="System Suite point")
        ui.notify(f"Loaded point into Compare slot {slot}", type="positive")
        log_ui_event(session, SUITE_RUNLOCK_OWNER, "HandoffCompare", {"slot": slot, "source": "point"})

    def _open_cr() -> None:
        if not isinstance(point_out, dict) or not point_out:
            ui.notify("No evaluation loaded.", type="warning")
            return
        switch_deck("Control Room")
        ui.notify("Opened Control Room — study uses pd_last_artifact.", type="info")
        log_ui_event(session, SUITE_RUNLOCK_OWNER, "HandoffControlRoom", {})

    def _open_pd() -> None:
        switch_deck("Point Designer")
        ui.notify("Opened Point Designer — re-evaluate after input changes.", type="info")

    def _to_pareto() -> None:
        try:
            from ui_nicegui.lib.suite_helpers import bridge_campaign_to_pareto

            meta = bridge_campaign_to_pareto(session)
            session.pareto_workflow_step = "5 · External Tools"
            switch_deck("Pareto Lab", force=True)
            ui.notify(
                f"Bridged to Pareto Lab External Tools: {meta.get('n_records', 0)} atlas records, "
                f"{meta.get('n_candidates', 0)} candidates → {meta.get('yaml_name') or 'results only'}.",
                type="positive",
            )
            log_ui_event(session, SUITE_RUNLOCK_OWNER, "HandoffParetoExtopt", meta)
        except Exception as exc:
            ui.notify(f"Pareto bridge failed: {exc}", type="negative")

    row_idx = ui.number("Campaign row # (for Compare)", value=0, min=0, step=1).classes("w-48")

    def _campaign_compare(slot: str) -> None:
        preview = session.suite_campaign_results_preview
        if not isinstance(preview, list) or not preview:
            ui.notify("Run campaign batch first.", type="warning")
            return
        ix = int(row_idx.value or 0)
        ix = max(0, min(ix, len(preview) - 1))
        row = preview[ix]
        if not isinstance(row, dict):
            # CampaignEvalRow → inputs dict for Compare re-eval
            try:
                row = dict(getattr(row, "inputs", {}) or {})
                row.setdefault("cid", getattr(preview[ix], "cid", ix))
            except Exception:
                ui.notify("Invalid campaign row.", type="negative")
                return
        try:
            # Prefer inputs sub-dict when present (JSONL result shape)
            payload = dict(row.get("inputs") or row)
            send_row_to_compare_slot(session, payload, slot, label="System Suite campaign")
            ui.notify(f"Campaign row {ix} → Compare slot {slot} (re-evaluated)", type="positive")
            log_ui_event(session, SUITE_RUNLOCK_OWNER, "HandoffCompare", {"slot": slot, "source": "campaign", "row": ix})
        except Exception as exc:
            ui.notify(f"Compare handoff failed: {exc}", type="negative")

    with ui.row().classes("gap-2 flex-wrap"):
        ui.button("Point → Compare A", icon="compare", on_click=lambda: _point_compare("A")).props("outline")
        ui.button("Point → Compare B", icon="compare", on_click=lambda: _point_compare("B")).props("outline")
        ui.button("Campaign row → Compare A", icon="compare", on_click=lambda: _campaign_compare("A")).props("flat outline")
        ui.button("Campaign row → Compare B", icon="compare", on_click=lambda: _campaign_compare("B")).props("flat outline")
        ui.button("Campaign → Pareto Lab (extopt)", icon="hub", on_click=_to_pareto).props("color=primary outline")
        ui.button("Open Control Room", icon="gavel", on_click=_open_cr).props("flat outline")
        ui.button("Open Point Designer", icon="design_services", on_click=_open_pd).props("flat outline")

    meta = getattr(session, "suite_pareto_bridge_meta", None)
    if isinstance(meta, dict) and meta:
        ui.label(
            f"Last Pareto bridge: {meta.get('n_records', 0)} records · "
            f"{meta.get('n_candidates', 0)} candidates · {meta.get('yaml_name') or '—'}"
        ).classes("text-caption text-grey q-mt-xs")


def render_export_bar(session: DesignSession) -> None:
    ui.label("Available exports").classes("text-subtitle2")
    with ui.row().classes("gap-2 flex-wrap q-mb-sm"):
        data = session.suite_campaign_jsonl_bytes
        if isinstance(data, (bytes, bytearray)):
            ui.button(
                "Download campaign results.jsonl",
                icon="download",
                on_click=lambda: ui.download(bytes(data), "campaign_results.jsonl"),
            ).props("color=primary outline")
        else:
            ui.button("Download campaign results.jsonl", icon="download").props("disable outline")
        rep = session.suite_parity_last_report
        if isinstance(rep, dict):
            from ui_nicegui.lib.suite_extended_helpers import parity_zip_bytes

            ui.button(
                "Download parity reviewer pack",
                icon="archive",
                on_click=lambda: ui.download(parity_zip_bytes(rep), "SHAMS_benchmark_parity_pack.zip"),
            ).props("outline")
        pc = session.profile_contracts_v362_last
        if isinstance(pc, dict) and pc:
            ui.badge("Profile corners report ready — export inside Tab 4", color="blue").props("outline")
