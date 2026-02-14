from __future__ import annotations

"""Materials lifetime closure (v367.0).

This module is deliberately placed under the repo-root `analysis/` namespace
because SHAMS test/runtime wiring imports `analysis.*` from repo root.

Purpose
-------
Provide deterministic, audit-ready bookkeeping that links:

  - irradiation-derived lifetime proxies (fw_lifetime_yr, blanket_lifetime_yr)
  - plant design lifetime policy
  - replacement cadence and counts
  - annualized replacement cost-rate proxies

No solvers. No iteration. No hidden relaxation.

Author: © 2026 Afshin Arjhangmehr
"""

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Mapping


def _finite(x: float) -> bool:
    return (x == x) and (abs(x) != float("inf"))


def _load_contract_defaults() -> Dict[str, Any]:
    contract_path = Path(__file__).resolve().parents[1] / "contracts" / "materials_lifetime_v367_contract.json"
    try:
        raw = contract_path.read_text(encoding="utf-8")
        j = json.loads(raw)
        d = dict(j.get("defaults", {}) or {})
        # Normalize key presence / types
        d["plant_design_lifetime_yr"] = float(d.get("plant_design_lifetime_yr", float("nan")))
        d["materials_life_cover_plant_enforce"] = bool(d.get("materials_life_cover_plant_enforce", False))
        d["fw_replace_interval_min_yr"] = float(d.get("fw_replace_interval_min_yr", float("nan")))
        d["blanket_replace_interval_min_yr"] = float(d.get("blanket_replace_interval_min_yr", float("nan")))
        d["fw_capex_fraction_of_blanket"] = float(d.get("fw_capex_fraction_of_blanket", 0.20))
        d["blanket_capex_fraction_of_blanket"] = float(d.get("blanket_capex_fraction_of_blanket", 1.00))
        d["replacement_installation_factor"] = float(d.get("replacement_installation_factor", 1.15))
        d["fallback_blanket_shield_capex_frac_of_total"] = float(d.get("fallback_blanket_shield_capex_frac_of_total", 0.25))
        return d
    except Exception:
        return {
            "plant_design_lifetime_yr": 30.0,
            "materials_life_cover_plant_enforce": False,
            "fw_replace_interval_min_yr": float("nan"),
            "blanket_replace_interval_min_yr": float("nan"),
            "fw_capex_fraction_of_blanket": 0.20,
            "blanket_capex_fraction_of_blanket": 1.00,
            "replacement_installation_factor": 1.15,
            "fallback_blanket_shield_capex_frac_of_total": 0.25,
        }


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


@dataclass(frozen=True)
class MaterialsLifetimeClosureV367:
    plant_design_lifetime_yr: float
    fw_lifetime_yr: float
    blanket_lifetime_yr: float
    fw_replace_interval_y: float
    blanket_replace_interval_y: float
    fw_replacements_over_plant_life: float
    blanket_replacements_over_plant_life: float
    fw_replacement_cost_MUSD_per_year: float
    blanket_replacement_cost_MUSD_per_year: float
    replacement_cost_MUSD_per_year_total: float
    materials_lifetime_contract_sha256: str


def compute_materials_lifetime_closure_v367(outputs: Mapping[str, Any], inp: Any) -> Dict[str, Any]:
    """Compute deterministic replacement cadence and cost-rate proxies.

    Inputs (in `inp` or contract defaults):
      - plant_design_lifetime_yr (default 30)
      - fw_replace_interval_min_yr (NaN disables)
      - blanket_replace_interval_min_yr (NaN disables)
      - fw_capex_fraction_of_blanket (default 0.2)
      - blanket_capex_fraction_of_blanket (default 1.0)
      - replacement_installation_factor (default 1.15)

    Required physics proxies in `outputs`:
      - fw_lifetime_yr, blanket_lifetime_yr (finite preferred; NaN allowed)
      - capex_blanket_shield_MUSD or CAPEX_component_proxy_MUSD/CAPEX_proxy_MUSD (fallback)
    """

    d = _load_contract_defaults()
    plant_life = float(getattr(inp, "plant_design_lifetime_yr", d["plant_design_lifetime_yr"]) or d["plant_design_lifetime_yr"])
    plant_life = max(1.0, plant_life) if _finite(plant_life) else d["plant_design_lifetime_yr"]

    fw_min = float(getattr(inp, "fw_replace_interval_min_yr", d["fw_replace_interval_min_yr"]))
    bl_min = float(getattr(inp, "blanket_replace_interval_min_yr", d["blanket_replace_interval_min_yr"]))
    fw_min = fw_min if _finite(fw_min) else float("nan")
    bl_min = bl_min if _finite(bl_min) else float("nan")

    fw_frac = float(getattr(inp, "fw_capex_fraction_of_blanket", d["fw_capex_fraction_of_blanket"]) or d["fw_capex_fraction_of_blanket"])
    bl_frac = float(getattr(inp, "blanket_capex_fraction_of_blanket", d["blanket_capex_fraction_of_blanket"]) or d["blanket_capex_fraction_of_blanket"])
    fw_frac = max(0.0, min(1.0, fw_frac))
    bl_frac = max(0.0, min(1.0, bl_frac))

    install = float(getattr(inp, "replacement_installation_factor", d["replacement_installation_factor"]) or d["replacement_installation_factor"])
    install = max(1.0, install) if _finite(install) else d["replacement_installation_factor"]

    fw_life = float(outputs.get("fw_lifetime_yr", float("nan")))
    bl_life = float(outputs.get("blanket_lifetime_yr", float("nan")))
    fw_life = fw_life if _finite(fw_life) else float("nan")
    bl_life = bl_life if _finite(bl_life) else float("nan")

    def _interval(life: float, minv: float) -> float:
        if not _finite(life) or life <= 0.0:
            return float("nan")
        if _finite(minv) and minv > 0.0:
            return max(life, minv)
        return life

    fw_int = _interval(fw_life, fw_min)
    bl_int = _interval(bl_life, bl_min)

    def _repl_count(plant: float, interval_y: float) -> float:
        if not _finite(interval_y) or interval_y <= 0.0:
            return float("nan")
        # replacements during plant life (excluding initial install)
        return max(0.0, math.ceil(plant / interval_y) - 1)

    fw_n = _repl_count(plant_life, fw_int)
    bl_n = _repl_count(plant_life, bl_int)

    # CAPEX base for blanket+shield (prefer explicit component if present)
    cap_bs = float(outputs.get("capex_blanket_shield_MUSD", float("nan")))
    if not _finite(cap_bs):
        cap_total = float(outputs.get("CAPEX_component_proxy_MUSD", outputs.get("CAPEX_proxy_MUSD", float("nan"))))
        if _finite(cap_total):
            cap_bs = max(0.0, cap_total) * float(d["fallback_blanket_shield_capex_frac_of_total"])
        else:
            cap_bs = float("nan")

    fw_cap = (max(0.0, cap_bs) * fw_frac) if _finite(cap_bs) else float("nan")
    bl_cap = (max(0.0, cap_bs) * bl_frac) if _finite(cap_bs) else float("nan")

    def _annual_cost(capex: float, interval_y: float) -> float:
        if not _finite(capex) or not _finite(interval_y) or interval_y <= 0.0:
            return float("nan")
        return max(0.0, capex) * install / interval_y

    fw_cost = _annual_cost(fw_cap, fw_int)
    bl_cost = _annual_cost(bl_cap, bl_int)

    total = 0.0
    any_finite = False
    for v in (fw_cost, bl_cost):
        if _finite(v):
            total += max(0.0, v)
            any_finite = True
    total = total if any_finite else float("nan")

    contract_sha = ""
    try:
        contract_path = Path(__file__).resolve().parents[1] / "contracts" / "materials_lifetime_v367_contract.json"
        if contract_path.exists():
            contract_sha = _sha256_file(contract_path)
    except Exception:
        contract_sha = ""

    clo = MaterialsLifetimeClosureV367(
        plant_design_lifetime_yr=float(plant_life),
        fw_lifetime_yr=float(fw_life),
        blanket_lifetime_yr=float(bl_life),
        fw_replace_interval_y=float(fw_int),
        blanket_replace_interval_y=float(bl_int),
        fw_replacements_over_plant_life=float(fw_n),
        blanket_replacements_over_plant_life=float(bl_n),
        fw_replacement_cost_MUSD_per_year=float(fw_cost),
        blanket_replacement_cost_MUSD_per_year=float(bl_cost),
        replacement_cost_MUSD_per_year_total=float(total),
        materials_lifetime_contract_sha256=contract_sha,
    )

    # Expose a stable, explicit output namespace (v367 keys)
    out: Dict[str, Any] = asdict(clo)
    out["materials_lifetime_schema_version"] = "v367.0"
    # Back-compat aliases used by v359 ledger integration
    out["fw_replace_interval_y_v367"] = out.pop("fw_replace_interval_y")
    out["blanket_replace_interval_y_v367"] = out.pop("blanket_replace_interval_y")
    out["replacement_cost_MUSD_per_year_v367_total"] = out.pop("replacement_cost_MUSD_per_year_total")
    return out
