"""Publication Benchmarks / Constitutional Atlas helpers."""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, List, Tuple

PUB_BENCH_TABS = [
    "Tokamak Constitutional Atlas",
    "Cross-Code Constitutions",
    "Publication Benchmarks",
    "Contract Studio",
    "Regulatory Evidence Pack Builder",
]


def build_preset_buckets() -> Dict[str, List[Tuple[str, str, str, str]]]:
    try:
        from src.models.reference_machines import reference_catalog
    except ImportError:
        from models.reference_machines import reference_catalog  # type: ignore

    cat = reference_catalog()
    items: List[Tuple[str, str, str, str]] = []
    for k, ent in cat.items():
        items.append((k, str(ent.get("intent", "")), str(ent.get("family", "")), str(ent.get("label", k))))
    items.sort(key=lambda x: (x[1], x[2], x[3]))

    def _bucket(intent: str, family: str) -> str:
        it = intent.strip().upper()
        fam = family.strip().upper()
        if it.startswith("RESEARCH"):
            return "Experimental Devices"
        if fam in (
            "ITER", "JET", "DIIID", "DIII-D", "EAST", "KSTAR", "JT-60SA",
            "ASDEX", "ASDEX-U", "AUG", "NSTX-U", "MAST-U",
        ):
            return "Large-Scale & Program"
        if fam in ("SPARC", "ARC"):
            return "Compact / HTS"
        return "Reactor Concepts"

    buckets: Dict[str, List[Tuple[str, str, str, str]]] = {}
    for k, intent, family, label in items:
        b = _bucket(intent, family)
        buckets.setdefault(b, []).append((k, label, intent, family))
    return buckets


def evaluate_atlas(preset_key: str, intent: str):
    from benchmarks.constitutional.atlas import evaluate_atlas_case

    return evaluate_atlas_case(preset_key, intent)


def run_fragility_scan(preset_key: str, intent: str) -> dict:
    from benchmarks.constitutional.atlas import local_fragility_scan

    try:
        from src.models.reference_machines import reference_catalog
    except ImportError:
        from models.reference_machines import reference_catalog  # type: ignore

    base_in = dict(reference_catalog()[preset_key]["inputs"].to_dict())
    knobs: Dict[str, Tuple[float, float, float]] = {}
    if "fG" in base_in:
        knobs["fG"] = (float(base_in["fG"]), 0.05, 0.05)
    if "Paux_MW" in base_in:
        knobs["Paux_MW"] = (float(base_in["Paux_MW"]), 0.10, 0.10)
    elif "H98" in base_in:
        knobs["H98"] = (float(base_in["H98"]), 0.05, 0.05)
    return local_fragility_scan(preset_key, intent, knobs)


def atlas_result_to_dict(res) -> dict:
    if hasattr(res, "__dataclass_fields__"):
        return asdict(res)
    return dict(res) if isinstance(res, dict) else {}


def summarize_atlas_result(res_dict: dict) -> Dict[str, Any]:
    run = res_dict.get("run") or {}
    verdict = str(run.get("verdict", "")).upper() if isinstance(run, dict) else ""
    worst = run.get("worst_hard_margin")
    if worst is None and isinstance(run, dict):
        led = run.get("constraints") or {}
        for _, c in led.items():
            if isinstance(c, dict) and str(c.get("severity", "")).lower() == "hard":
                m = c.get("margin")
                if isinstance(m, (int, float)):
                    worst = m if worst is None else min(worst, m)

    art = (run.get("artifact") or {}) if isinstance(run, dict) else {}
    ac = art.get("authority_confidence") or {} if isinstance(art, dict) else {}
    dc = art.get("decision_consequences") or {} if isinstance(art, dict) else {}
    ft = art.get("fidelity_tiers") or {} if isinstance(art, dict) else {}
    ef = art.get("epoch_feasibility") or {} if isinstance(art, dict) else {}
    classified = art.get("classification") or {} if isinstance(art, dict) else {}
    diag = list(classified.get("diagnostic") or [])

    epoch_rows: List[Dict[str, str]] = []
    for e in ef.get("epochs") or []:
        if isinstance(e, dict):
            epoch_rows.append({
                "epoch": str(e.get("epoch", "")),
                "verdict": str(e.get("verdict", "")),
            })

    return {
        "loaded": bool(res_dict),
        "verdict": verdict or "-",
        "dominant_mechanism": run.get("dominant_mechanism") or "-",
        "dominant_constraint": run.get("dominant_constraint") or "-",
        "worst_hard_margin": worst,
        "preset_label": res_dict.get("preset_label") or res_dict.get("preset_key") or "-",
        "selected_intent": res_dict.get("selected_intent") or "-",
        "native_intent": res_dict.get("native_intent") or "-",
        "stamp": str(res_dict.get("stamp_sha256") or "")[:12],
        "design_confidence": str((ac.get("design") or {}).get("design_confidence_class", "UNKNOWN")),
        "fidelity_label": str((ft.get("design") or {}).get("design_fidelity_label", "")),
        "decision_posture": str(dc.get("decision_posture", "UNKNOWN")),
        "primary_risk_driver": str(dc.get("primary_risk_driver") or ""),
        "epoch_overall": str(ef.get("overall") or ""),
        "epoch_rows": epoch_rows,
        "failed_diagnostic": diag,
    }


def constitution_diff_rows(res_dict: dict) -> List[Dict[str, str]]:
    try:
        from benchmarks.constitutional.constitutions import pretty_clause
    except ImportError:
        pretty_clause = lambda k: str(k)  # noqa: E731

    rows: List[Dict[str, str]] = []
    for d in res_dict.get("constitution_diff") or []:
        if not isinstance(d, dict):
            continue
        rows.append({
            "clause": pretty_clause(d.get("key", "")),
            "selected": str(d.get("from", "")),
            "native": str(d.get("to", "")),
        })
    return rows


def atlas_evidence_json(res_dict: dict) -> bytes:
    """Serialize Atlas evidence capsule with PHYS-KPI-001 watermark on FAIL runs."""
    from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_claim_kpi_map

    payload = {
        "schema": res_dict.get("schema"),
        "preset_key": res_dict.get("preset_key"),
        "preset_label": res_dict.get("preset_label"),
        "selected_intent": res_dict.get("selected_intent"),
        "native_intent": res_dict.get("native_intent"),
        "constitution_selected": res_dict.get("constitution_selected"),
        "constitution_native": res_dict.get("constitution_native"),
        "constitution_diff": res_dict.get("constitution_diff"),
        "run": res_dict.get("run"),
        "stamp_sha256": res_dict.get("stamp_sha256"),
    }
    run = payload.get("run")
    if isinstance(run, dict):
        verdict = str(run.get("verdict") or "").upper()
        feasible = verdict in ("PASS", "FEASIBLE", "OK")
        display_run = dict(run)
        outs = run.get("outputs")
        if isinstance(outs, dict):
            display_run["outputs"] = watermark_claim_kpi_map(outs, feasible=feasible, point_out=outs)
        art = run.get("artifact")
        if isinstance(art, dict):
            art2 = dict(art)
            aouts = art.get("outputs")
            if isinstance(aouts, dict):
                art2["outputs"] = watermark_claim_kpi_map(aouts, feasible=feasible, point_out=aouts)
            tables = art.get("tables")
            if isinstance(tables, dict):
                t2 = dict(tables)
                v1 = tables.get("v1") or tables
                if isinstance(v1, dict):
                    v1d = dict(v1)
                    for section in ("plasma", "power_balance"):
                        block = v1.get(section)
                        if isinstance(block, dict):
                            v1d[section] = watermark_claim_kpi_map(
                                block, feasible=feasible, point_out=aouts if isinstance(aouts, dict) else outs
                            )
                    if "v1" in tables:
                        t2["v1"] = v1d
                    else:
                        t2.update(v1d)
                art2["tables"] = t2
            display_run["artifact"] = art2
        if not feasible:
            display_run["phys_kpi_001"] = (
                "Claim KPIs (Q/H98/Pfus/P_net) watermarked as diagnostic on FAIL — not design claims."
            )
        payload["run"] = display_run
    return json.dumps(payload, indent=2, default=str).encode("utf-8")
