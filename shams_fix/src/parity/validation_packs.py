from __future__ import annotations

"""PROCESS Parity Layer v3: validation packs.

Validation packs are *named, reproducible comparisons* against reference outputs
(e.g., published studies or internal baselines). They are designed to be run
from the UI as a single click:

PASS / WARN / FAIL

Contract
--------
- Packs do not alter frozen evaluator truth.
- Packs compare derived parity quantities and selected evaluator outputs.
- Packs are transparent: assumptions + tolerances are explicit.

This module is intentionally conservative: it provides structure for calibration
and validation. Absolute credibility comes from the reference data you load.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from models.inputs import PointInputs
from models.reference_machines import REFERENCE_MACHINES
from physics.hot_ion import hot_ion_point
from constraints import build_constraints_from_outputs, summarize_constraints

from parity import parity_plant_closure, parity_magnets, parity_cryo, parity_costing

# -----------------------------
# Data structures
# -----------------------------

@dataclass(frozen=True)
class ValidationPack:
    pack_id: str
    title: str
    preset_key: str
    design_intent: str  # 'Reactor' or 'Research'
    compare_keys: List[str]          # flattened keys into a metrics dict
    tolerances_rel: Dict[str, float] # relative tolerance per key (e.g., 0.1 = 10%)
    severities: Dict[str, str]       # 'warn' or 'fail' per key


def _flatten_metrics(*, outputs: Dict[str, Any], parity: Dict[str, Any]) -> Dict[str, float]:
    """Flatten a small set of metrics for validation.

    Keys are stable strings; values are floats.
    """
    m: Dict[str, float] = {}
    # Common physics outputs (stable aliases)
    aliases = {
        "P_fus_MW": ["P_fus_MW", "Pfus_DT_eqv_MW", "Pfus_DT_adj_MW", "Pfus_profile_MW"],
        "Pnet_e_MW": ["Pnet_e_MW", "P_e_net_MW", "P_e_net_avg_MW"],
        "Q_DT_eqv": ["Q_DT_eqv"],
        "q_div_MW_m2": ["q_div_MW_m2"],
        "Bmax_T": ["Bmax_T"],
        "Ip_MA": ["Ip_MA"],
        "Bt_T": ["Bt_T"],
        "R0_m": ["R0_m"],
    }
    for alias, keys in aliases.items():
        for k in keys:
            if k in outputs and outputs[k] is not None:
                try:
                    m[f"out.{alias}"] = float(outputs[k])
                    break
                except Exception:
                    continue

    # Plant closure
    pc = parity.get("plant_closure", {})
    pc_d = pc.get("derived", pc)
    for k in ["P_e_gross_MW", "P_recirc_MW", "P_e_net_MW", "Qe"]:
        v = pc_d.get(k)
        if v is not None:
            try:
                m[f"plant.{k}"] = float(v)
            except Exception:
                pass

        v = pc.get(k)
        if v is not None:
            try:
                m[f"plant.{k}"] = float(v)
            except Exception:
                pass

    # Magnets
    mag = parity.get("magnets", {})
    mag_d = mag.get("derived", mag)
    for k, alias in [("B_peak_TF_T","B_peak_TF_T"), ("sigma_vm_MPa","sigma_vm_MPa"), ("E_tf_MJ","E_tf_MJ")]:
        v = mag_d.get(k)
        if v is not None:
            try:
                m[f"mag.{alias}"] = float(v)
            except Exception:
                pass

        v = mag.get(k)
        if v is not None:
            try:
                m[f"mag.{k}"] = float(v)
            except Exception:
                pass

    # Cryo
    cry = parity.get("cryo", {})
    cry_d = cry.get("derived", cry)
    for k, alias in [("P_cold_20K_MW","P_cold_20K_MW"), ("P_cryo_e_MW","P_cryo_e_MW"), ("cryo_COP","cryo_COP")]:
        v = cry_d.get(k)
        if v is not None:
            try:
                m[f"cryo.{alias}"] = float(v)
            except Exception:
                pass

        v = cry.get(k)
        if v is not None:
            try:
                m[f"cryo.{k}"] = float(v)
            except Exception:
                pass

    # Costing
    cost = parity.get("costing", {})
    cost_d = cost.get("derived", cost)
    # normalize units to BUSD where convenient
    capex_musd = cost_d.get("CAPEX_MUSD")
    if capex_musd is not None:
        try:
            m["cost.CAPEX_BUSD"] = float(capex_musd) / 1000.0
        except Exception:
            pass
    opex_musd = cost_d.get("OPEX_MUSD_per_y")
    if opex_musd is not None:
        try:
            m["cost.OPEX_BUSD_per_y"] = float(opex_musd) / 1000.0
        except Exception:
            pass
    for k in ["LCOE_USD_per_MWh", "COE_USD_per_MWh"]:
        v = cost_d.get(k)
        if v is not None:
            try:
                m[f"cost.{k}"] = float(v)
            except Exception:
                pass

    return m


def load_validation_packs(path: Path) -> List[ValidationPack]:
    data = json_load(path)
    packs: List[ValidationPack] = []
    for p in data.get("packs", []):
        packs.append(
            ValidationPack(
                pack_id=p["pack_id"],
                title=p["title"],
                preset_key=p["preset_key"],
                design_intent=p.get("design_intent", "Reactor"),
                compare_keys=list(p.get("compare_keys", [])),
                tolerances_rel=dict(p.get("tolerances_rel", {})),
                severities=dict(p.get("severities", {})),
            )
        )
    return packs


def json_load(path: Path) -> Dict[str, Any]:
    return __import__("json").loads(path.read_text(encoding="utf-8"))


def evaluate_pack_candidate(pack: ValidationPack) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, float], Dict[str, Any]]:
    """Evaluate the preset for a given pack and return (inputs, outputs, metrics, meta)."""
    preset = REFERENCE_MACHINES.get(pack.preset_key)
    if preset is None:
        raise KeyError(f"Unknown preset_key: {pack.preset_key}")

    pi = PointInputs(**preset)
    outputs = hot_ion_point(pi)

    # constraints summary (used for meta / later)
    cons = build_constraints_from_outputs(outputs)
    cons_summary = summarize_constraints(cons)

    parity: Dict[str, Any] = {}
    parity["plant_closure"] = parity_plant_closure(inputs=pi, outputs=outputs)
    parity["magnets"] = parity_magnets(inputs=pi, outputs=outputs)
    parity["cryo"] = parity_cryo(inputs=pi, outputs=outputs)
    parity["costing"] = parity_costing(inputs=pi, outputs=outputs)

    metrics = _flatten_metrics(outputs=outputs, parity=parity)

    meta = {
        "design_intent": pack.design_intent,
        "preset_key": pack.preset_key,
        "constraints_summary": cons_summary,
        "assumptions": {
            "plant": parity["plant_closure"].get("assumptions", {}),
            "cryo": parity["cryo"].get("assumptions", {}),
            "cost": parity["costing"].get("assumptions", {}),
        },
    }
    return preset, outputs, metrics, meta


def compare_to_reference(
    *,
    pack: ValidationPack,
    metrics: Dict[str, float],
    reference: Dict[str, float],
) -> Dict[str, Any]:
    """Return structured comparison results for a pack."""
    rows: List[Dict[str, Any]] = []
    status = "PASS"
    worst = 0.0

    for key in pack.compare_keys:
        ref = reference.get(key)
        val = metrics.get(key)
        if ref is None or val is None:
            # missing data => WARN (never hard fail)
            rows.append({"key": key, "value": val, "ref": ref, "rel_err": None, "tol": None, "severity": "warn", "ok": False})
            status = "WARN" if status != "FAIL" else status
            continue

        rel_err = abs(val - ref) / max(1e-12, abs(ref))
        tol = float(pack.tolerances_rel.get(key, 0.10))
        severity = pack.severities.get(key, "warn").lower()
        ok = rel_err <= tol
        worst = max(worst, rel_err)

        if not ok:
            if severity == "fail":
                status = "FAIL"
            elif status != "FAIL":
                status = "WARN"

        rows.append({"key": key, "value": val, "ref": ref, "rel_err": rel_err, "tol": tol, "severity": severity, "ok": ok})

    return {"pack_id": pack.pack_id, "title": pack.title, "status": status, "worst_rel_err": worst, "rows": rows}
