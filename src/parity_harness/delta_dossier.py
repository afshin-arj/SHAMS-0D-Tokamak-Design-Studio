from __future__ import annotations

"""Delta dossier generator for PROCESS parity harness (v364.0).

Given:
- a SHAMS artifact (run artifact)
- optional PROCESS outputs (user-provided JSON)

Generate a reviewer-grade explanation of differences:
- mapping assumptions (if available)
- output deltas for a selected set of KPI fields
- constraint margin deltas (if PROCESS margins supplied)
- mechanism dominance explanations

PROCESS is treated as an external reference; SHAMS does not attempt to re-derive PROCESS.

© 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import json
import math


_KPI_FIELDS = [
    "Q_plasma",
    "Q_eng",
    "Pe_net_MW",
    "Pe_gross_MW",
    "P_fus_MW",
    "P_aux_MW",
    "P_recirc_MW",
    "recirc_frac",
]


def _dig(d: Dict[str, Any], path: str) -> Optional[Any]:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def extract_shams_kpis(artifact: Dict[str, Any]) -> Dict[str, Any]:
    k = artifact.get("kpis", {}) if isinstance(artifact.get("kpis"), dict) else {}
    out: Dict[str, Any] = {}
    for f in _KPI_FIELDS:
        if f in k and k.get(f) is not None:
            out[f] = k.get(f)
    # SHAMS run-artifact aliases (headline KPIs use different names than PROCESS-style fields)
    aliases = {
        "Q_plasma": ("Q_DT_eqv", "Q", "Q_plasma"),
        "P_fus_MW": ("Pfus_DT_adj_MW", "P_fus_MW", "Pfus_MW"),
        "Pe_net_MW": ("P_net_e_MW", "Pe_net_MW", "P_e_net_MW"),
        "P_aux_MW": ("Paux_MW", "P_aux_MW"),
    }
    for canonical, keys in aliases.items():
        if canonical in out:
            continue
        for key in keys:
            if key in k and k.get(key) is not None:
                out[canonical] = k.get(key)
                break
            v = _dig(artifact, f"outputs.{key}") if isinstance(artifact.get("outputs"), dict) else None
            if v is not None:
                out[canonical] = v
                break
    # common alternates
    if "Pe_net_MW" not in out:
        v = _dig(artifact, "closure_ledger.Pe_net_MW")
        if v is not None:
            out["Pe_net_MW"] = v
    # Drop non-finite floats (NaN/Inf) so METHOD-ONLY dossiers stay JSON-clean
    clean: Dict[str, Any] = {}
    for key, val in out.items():
        if isinstance(val, float) and not math.isfinite(val):
            continue
        clean[key] = val
    return clean


def extract_shams_summary(artifact: Dict[str, Any]) -> Dict[str, Any]:
    k = artifact.get("kpis", {}) if isinstance(artifact.get("kpis"), dict) else {}
    verdict = artifact.get("verdict")
    if verdict is None:
        fh = k.get("feasible_hard")
        if fh is True:
            verdict = "FEASIBLE"
        elif fh is False:
            verdict = "NO-SOLUTION"
    return {
        "verdict": verdict,
        "dominant_mechanism": artifact.get("dominant_mechanism"),
        "dominant_constraint": artifact.get("dominant_constraint"),
        "worst_hard_margin": artifact.get("worst_hard_margin", k.get("min_hard_margin")),
        "feasible_hard": k.get("feasible_hard"),
    }


def extract_process_kpis(proc: Dict[str, Any]) -> Dict[str, Any]:
    # Expect a user-provided dict with keys matching _KPI_FIELDS or close variants.
    # None / null values are omitted so METHOD-ONLY honesty stays clean.
    out: Dict[str, Any] = {}
    for f in _KPI_FIELDS:
        if f in proc and proc.get(f) is not None:
            out[f] = proc.get(f)
    # allow nesting
    k = proc.get("kpis", {}) if isinstance(proc.get("kpis"), dict) else {}
    for f in _KPI_FIELDS:
        if f not in out and f in k and k.get(f) is not None:
            out[f] = k.get(f)
    # Common PROCESS-style aliases (only when numeric)
    aliases = {
        "Q_plasma": ("Q", "qplasma", "Q_DT"),
        "P_fus_MW": ("P_fus_W", "pfusmw", "Pfusion"),
        "Pe_net_MW": ("P_el_net_W", "P_el_net_MW", "Pe_net"),
        "P_aux_MW": ("Paux_MW", "pauxmw"),
    }
    for canonical, alts in aliases.items():
        if canonical in out:
            continue
        for a in alts:
            if a in proc and proc.get(a) is not None:
                # Convert Watts → MW when alias ends with _W
                v = proc.get(a)
                try:
                    fv = float(v)
                except Exception:
                    continue
                if str(a).endswith("_W") and not str(a).endswith("_MW"):
                    fv = fv / 1.0e6
                out[canonical] = fv
                break
    return out


def has_numeric_process_kpis(proc: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(proc, dict):
        return False
    return bool(extract_process_kpis(proc))


def classify_dossier_status(process_payload: Optional[Dict[str, Any]]) -> str:
    """NUMERIC only when real PROCESS KPI numbers are present; else METHOD-ONLY."""
    return "NUMERIC" if has_numeric_process_kpis(process_payload) else "METHOD-ONLY"


def delta_table(a: Dict[str, Any], b: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    keys = sorted(set(a.keys()) | set(b.keys()))
    for k in keys:
        va = a.get(k, None)
        vb = b.get(k, None)
        dv = None
        try:
            if va is not None and vb is not None:
                dv = float(va) - float(vb)
        except Exception:
            dv = None
        rows.append({"field": k, "shams": va, "process": vb, "delta": dv})
    return rows


def build_delta_dossier(
    *,
    case_id: str,
    shams_artifact: Dict[str, Any],
    process_payload: Optional[Dict[str, Any]] = None,
    mapping_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    sh_k = extract_shams_kpis(shams_artifact)
    pr_k = extract_process_kpis(process_payload) if isinstance(process_payload, dict) else {}
    status = classify_dossier_status(process_payload if isinstance(process_payload, dict) else None)

    dossier: Dict[str, Any] = {
        "schema": "shams_delta_dossier.v1",
        "case_id": str(case_id),
        "dossier_status": status,
        "has_process_reference": status == "NUMERIC",
        "shams_summary": extract_shams_summary(shams_artifact),
        "mapping": mapping_payload if isinstance(mapping_payload, dict) else None,
        "kpi_deltas": delta_table(sh_k, pr_k) if pr_k else [],
        "shams_kpis": sh_k,
    }

    if status == "METHOD-ONLY":
        dossier["honesty"] = {
            "label": "METHOD-ONLY",
            "statement": (
                "No numeric PROCESS reference KPIs were supplied. "
                "This dossier records SHAMS diagnostics and mapping assumptions only; "
                "it does not invent MFILE / OUT.DAT values."
            ),
        }

    # Provide top blockers for reviewer readability
    ledger = shams_artifact.get("constraint_ledger", {}) if isinstance(shams_artifact.get("constraint_ledger"), dict) else {}
    top = ledger.get("top_blockers", []) if isinstance(ledger.get("top_blockers"), list) else []
    dossier["shams_top_blockers"] = top[:10]

    # If process provides its own blockers, include a comparative view
    if isinstance(process_payload, dict):
        pb = process_payload.get("top_blockers", None)
        if isinstance(pb, list):
            dossier["process_top_blockers"] = pb[:10]

    return dossier


def render_delta_dossier_markdown(dossier: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# Delta dossier — {dossier.get('case_id','')}")
    lines.append("")
    status = dossier.get("dossier_status", "METHOD-ONLY" if not dossier.get("has_process_reference") else "NUMERIC")
    lines.append(f"**Dossier status:** `{status}`")
    lines.append("")
    s = dossier.get("shams_summary", {}) if isinstance(dossier.get("shams_summary"), dict) else {}
    lines.append("## SHAMS verdict")
    lines.append(f"- Verdict: **{s.get('verdict','?')}**")
    lines.append(f"- Dominant mechanism: `{s.get('dominant_mechanism','')}`")
    lines.append(f"- Dominant constraint: `{s.get('dominant_constraint','')}`")
    lines.append(f"- Worst hard margin: `{s.get('worst_hard_margin', None)}`")
    lines.append("")

    if status == "NUMERIC" or dossier.get("has_process_reference", False):
        lines.append("## KPI deltas (SHAMS − PROCESS)")
        rows = dossier.get("kpi_deltas", []) if isinstance(dossier.get("kpi_deltas"), list) else []
        if rows:
            lines.append("| Field | SHAMS | PROCESS | Δ |")
            lines.append("|---|---:|---:|---:|")
            for r in rows:
                lines.append(f"| {r.get('field','')} | {r.get('shams','')} | {r.get('process','')} | {r.get('delta','')} |")
        else:
            lines.append("(No KPI deltas available.)")
        lines.append("")
    else:
        lines.append("## PROCESS reference")
        honesty = dossier.get("honesty", {}) if isinstance(dossier.get("honesty"), dict) else {}
        stmt = honesty.get("statement") or (
            "No PROCESS payload provided; this dossier contains SHAMS-only diagnostics (METHOD-ONLY)."
        )
        lines.append(f"(METHOD-ONLY) {stmt}")
        lines.append("")

    lines.append("## SHAMS top blockers")
    tb = dossier.get("shams_top_blockers", []) if isinstance(dossier.get("shams_top_blockers"), list) else []
    if tb:
        for t in tb:
            if isinstance(t, dict):
                lines.append(f"- `{t.get('name','')}` (mech: {t.get('mechanism_group', t.get('mechanism',''))}, margin: {t.get('margin', None)})")
    else:
        lines.append("(No blockers recorded.)")

    return "\n".join(lines) + "\n"
