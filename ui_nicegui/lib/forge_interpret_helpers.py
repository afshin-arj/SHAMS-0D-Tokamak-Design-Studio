"""Forge workbench interpretability — conflict atlas, candidate instruments."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def update_conflict_atlas(atlas: Optional[dict], resistance_report: Optional[dict]) -> dict:
    try:
        from tools.sandbox.conflict_atlas import new_atlas, update_atlas
    except ImportError:
        return dict(atlas or {})
    base = atlas if isinstance(atlas, dict) and atlas else new_atlas()
    if isinstance(resistance_report, dict):
        try:
            return update_atlas(base, resistance_report)
        except Exception:
            pass
    return base


def summarize_conflict_atlas(atlas: dict, *, top_n: int = 20) -> List[dict]:
    try:
        from tools.sandbox.conflict_atlas import summarize_atlas
    except ImportError:
        return []
    try:
        rows = summarize_atlas(atlas or {}, top_n=int(top_n))
        return [r for r in rows if isinstance(r, dict)]
    except Exception:
        return []


def enrich_candidate_instruments(cand: dict, intent: str) -> dict:
    """Closure console, margin budget, reality gates, report pack."""
    out: dict = {}
    outputs = cand.get("outputs") or {}
    constraints = cand.get("constraints") or []
    cost = cand.get("cost") or {}
    if not isinstance(outputs, dict):
        return out
    feasible = bool(cand.get("feasible", False))
    try:
        from tools.sandbox.closure_console import closure_console
        from tools.sandbox.margin_budget import margin_budget
        from tools.sandbox.reality_gates import reality_gates
        from tools.sandbox.report_pack import build_report_pack

        closure = closure_console(outputs=outputs, cost_proxy=cost if isinstance(cost, dict) else {})
        mb = margin_budget(constraints)
        rg = reality_gates(constraints, closure if isinstance(closure, dict) else None)
        rp = build_report_pack(
            intent=str(intent),
            inputs=dict(cand.get("inputs") or {}),
            outputs=outputs,
            constraints=constraints,
            closure_bundle=closure if isinstance(closure, dict) else None,
            margin_budget=mb,
            reality_gates=rg,
            feasible=feasible,
            failure_mode=cand.get("failure_mode"),
        )
        out["closure_bundle"] = watermark_forge_closure_bundle(
            closure if isinstance(closure, dict) else {},
            feasible=feasible,
            point_out=outputs,
        )
        out["margin_budget"] = mb
        out["reality_gates"] = rg
        out["report_pack"] = watermark_forge_report_pack(
            rp if isinstance(rp, dict) else {},
            feasible=feasible,
            point_out=outputs,
        )
        out["feasible"] = feasible
    except Exception as exc:
        out["error"] = str(exc)
    return out


def watermark_forge_closure_bundle(
    bundle: dict,
    *,
    feasible: bool,
    point_out: Optional[dict] = None,
) -> dict:
    """PHYS-KPI-001: watermark claim FoMs in Forge closure_bundle for display/export."""
    from ui_nicegui.lib.plant_kpi_honesty_ui import format_claim_kpi_for_table, is_claim_kpi_key

    src = dict(bundle) if isinstance(bundle, dict) else {}
    if feasible:
        return src
    out: Dict[str, Any] = {}
    for k, v in src.items():
        key = str(k)
        claim = key if is_claim_kpi_key(key) else ("P_e_net_MW" if key == "net_electric_MW" else None)
        if claim:
            out[key] = format_claim_kpi_for_table(claim, v, feasible=False, point_out=point_out)
        else:
            out[key] = v
    return out


def watermark_forge_report_pack(
    pack: dict,
    *,
    feasible: bool,
    point_out: Optional[dict] = None,
) -> dict:
    """Copy report pack with claim FoMs watermarked when candidate is INFEASIBLE."""
    import re

    from ui_nicegui.lib.plant_kpi_honesty_ui import (
        format_claim_kpi_for_table,
        is_claim_kpi_key,
        watermark_claim_kpi_map,
    )

    if not isinstance(pack, dict):
        return {}
    if feasible:
        return dict(pack)

    out = dict(pack)
    j = dict(out.get("json") or {}) if isinstance(out.get("json"), dict) else {}
    if isinstance(j.get("key_outputs"), dict):
        j["key_outputs"] = watermark_claim_kpi_map(
            j["key_outputs"], feasible=False, point_out=point_out or j.get("key_outputs")
        )
    if isinstance(j.get("closure_bundle"), dict):
        j["closure_bundle"] = watermark_forge_closure_bundle(
            j["closure_bundle"], feasible=False, point_out=point_out
        )
    fcc = j.get("closure_certificate")
    if isinstance(fcc, dict):
        fcc2 = dict(fcc)
        kn = dict(fcc2.get("key_numbers") or {})
        for k, v in list(kn.items()):
            claim = str(k) if is_claim_kpi_key(str(k)) else (
                "P_e_net_MW" if str(k) == "net_electric_MW" else None
            )
            if claim:
                kn[k] = format_claim_kpi_for_table(claim, v, feasible=False, point_out=point_out)
        fcc2["key_numbers"] = kn
        notes = list(fcc2.get("notes") or [])
        note = "PHYS-KPI-001: key_numbers claim FoMs are diagnostic on INFEASIBLE — not design claims."
        if note not in notes:
            notes.append(note)
        fcc2["notes"] = notes
        j["closure_certificate"] = fcc2
    out["json"] = j

    md = str(out.get("markdown") or "")
    prefix = (
        "PHYS-KPI-001: claim FoMs (Q / H98 / Pfus / P_net) on this INFEASIBLE candidate "
        "are diagnostic residue — not design claims.\n\n"
    )
    if "PHYS-KPI-001" not in md:
        md = prefix + md
    cb = j.get("closure_bundle") if isinstance(j.get("closure_bundle"), dict) else {}
    net = cb.get("net_electric_MW")
    if net is not None:
        md = re.sub(r"(?m)^- net_electric_MW:.*$", f"- net_electric_MW: {net}", md)
    out["markdown"] = md
    out["phys_kpi_note"] = (
        "PHYS-KPI-001: claim FoMs watermarked as diagnostic on INFEASIBLE Forge candidate."
    )
    return out


def why_not_for_candidate(cand: dict, intent: str, *, disabled: Optional[List[str]] = None) -> dict:
    try:
        from tools.sandbox.tier56 import why_not_report
    except ImportError as exc:
        return {"error": str(exc)}
    try:
        return why_not_report(
            candidate=cand,
            intent=str(intent),
            disabled_constraints=list(disabled or []),
        )
    except Exception as exc:
        return {"error": str(exc)}


def design_card_markdown(cand: dict, intent: str = "") -> str:
    """Render design-card markdown. ``intent`` is unused (card reads candidate fields)."""
    try:
        from tools.sandbox.design_card import build_design_card_md
    except ImportError:
        return ""
    try:
        c = dict(cand) if isinstance(cand, dict) else {}
        # Prefer explicit intent from UI when candidate lacks it.
        if intent and not (c.get("design_intent") or c.get("intent")):
            c["intent"] = str(intent)
        return str(build_design_card_md(c))
    except Exception:
        return ""


def ladder_histogram_rows(archive: list) -> List[dict]:
    try:
        from tools.sandbox.archive_intelligence import ladder_histogram
    except ImportError:
        return []
    try:
        hist = ladder_histogram(archive or [])
        if isinstance(hist, dict):
            return [{"bucket": k, "count": v} for k, v in hist.items()]
        if isinstance(hist, list):
            return [r for r in hist if isinstance(r, dict)]
    except Exception:
        pass
    return []


def scatter_axis_options(archive: list) -> List[str]:
    keys = set()
    for a in archive or []:
        if not isinstance(a, dict):
            continue
        for src in (a.get("inputs") or {}, a.get("outputs") or {}, a):
            if isinstance(src, dict):
                for k, v in src.items():
                    if isinstance(v, (int, float)):
                        keys.add(str(k))
    preferred = [
        "R0_m", "Bt_T", "Ip_MA", "Paux_MW", "P_e_net_MW", "Pfus_total_MW",
        "Q_DT_eqv", "q_div_MW_m2", "min_signed_margin", "_score",
    ]
    ordered = [k for k in preferred if k in keys]
    ordered += sorted(k for k in keys if k not in ordered)
    return ordered[:16]


def archive_point(a: dict, key: str):
    if not isinstance(a, dict):
        return None
    if key in a:
        return a.get(key)
    inp = a.get("inputs") or {}
    out = a.get("outputs") or {}
    if key in inp:
        return inp.get(key)
    if key in out:
        return out.get(key)
    return None
