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
    return json.dumps(payload, indent=2, default=str).encode("utf-8")
