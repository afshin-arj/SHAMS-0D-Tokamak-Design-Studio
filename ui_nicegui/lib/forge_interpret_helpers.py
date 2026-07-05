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
        )
        out["closure_bundle"] = closure
        out["margin_budget"] = mb
        out["reality_gates"] = rg
        out["report_pack"] = rp
    except Exception as exc:
        out["error"] = str(exc)
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


def design_card_markdown(cand: dict, intent: str) -> str:
    try:
        from tools.sandbox.design_card import build_design_card_md
    except ImportError:
        return ""
    try:
        return str(build_design_card_md(cand, intent=str(intent)))
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
