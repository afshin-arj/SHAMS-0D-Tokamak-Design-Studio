from __future__ import annotations

"""Materials lifetime closure (v367.0).

NOTE: This module is duplicated under both `analysis/` and `src/analysis/`.
Some entrypoints (e.g., `benchmarks/run.py`) add only `src/` to sys.path,
while others (tests/UI) import from repo root. Keeping the same deterministic
implementation in both namespaces ensures import-safe behavior.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict


def _finite(x: float) -> bool:
    return (x == x) and (x != float("inf")) and (x != -float("inf"))


def _ceil_div(a: float, b: float) -> float:
    if not _finite(a) or not _finite(b) or b <= 0:
        return float("nan")
    return float(int((a + b - 1e-12) // b + 1))


def _sha256_hex_bytes(data: bytes) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _load_contract_defaults(contract_path: str) -> Dict[str, Any]:
    import json
    from pathlib import Path

    p = Path(contract_path)
    if not p.exists():
        return {}
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            return dict(obj.get("defaults", {}) or {})
    except Exception:
        return {}
    return {}


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


def compute_materials_lifetime_closure_v367(outputs: Dict[str, Any], inp: Any) -> Dict[str, Any]:
    """Compute deterministic materials lifetime replacement closure.

    Inputs (from inp)
    -----------------
    - plant_design_lifetime_yr (default 30)
    - materials_life_cover_plant_enforce (bool, used in constraints)
    - fw_replace_interval_min_yr, blanket_replace_interval_min_yr (optional)
    - fw_capex_fraction_of_blanket, blanket_capex_fraction_of_blanket (optional)

    Outputs (added)
    ---------------
    - fw_replace_interval_y_v367, blanket_replace_interval_y_v367
    - fw_replacements_over_plant_life, blanket_replacements_over_plant_life
    - fw_replacement_cost_MUSD_per_year, blanket_replacement_cost_MUSD_per_year
    - replacement_cost_MUSD_per_year_v367_total
    - materials_lifetime_contract_sha256
    """

    contract_path = "contracts/materials_lifetime_v367_contract.json"
    defaults = _load_contract_defaults(contract_path)
    contract_sha = ""
    try:
        from pathlib import Path

        contract_sha = _sha256_hex_bytes(Path(contract_path).read_bytes())
    except Exception:
        contract_sha = ""

    plant_life = float(getattr(inp, "plant_design_lifetime_yr", defaults.get("plant_design_lifetime_yr", 30.0)) or 30.0)
    plant_life = max(plant_life, 0.0)

    fw_life = float(outputs.get("fw_lifetime_yr", float("nan")))
    bl_life = float(outputs.get("blanket_lifetime_yr", float("nan")))

    fw_min = float(getattr(inp, "fw_replace_interval_min_yr", defaults.get("fw_replace_interval_min_yr", float("nan"))))
    bl_min = float(getattr(inp, "blanket_replace_interval_min_yr", defaults.get("blanket_replace_interval_min_yr", float("nan"))))

    fw_int = fw_life if _finite(fw_life) and fw_life > 0 else float("nan")
    bl_int = bl_life if _finite(bl_life) and bl_life > 0 else float("nan")

    if _finite(fw_min) and _finite(fw_int) and fw_int > 0:
        fw_int = max(fw_int, fw_min)
    if _finite(bl_min) and _finite(bl_int) and bl_int > 0:
        bl_int = max(bl_int, bl_min)

    fw_n = _ceil_div(plant_life, fw_int) if _finite(fw_int) and fw_int > 0 else float("nan")
    bl_n = _ceil_div(plant_life, bl_int) if _finite(bl_int) and bl_int > 0 else float("nan")

    capex_bs = float(outputs.get("capex_blanket_shield_MUSD", float("nan")))
    if not _finite(capex_bs):
        capex_total = float(outputs.get("capex_total_MUSD", float("nan")))
        if _finite(capex_total):
            capex_bs = 0.25 * capex_total

    fw_frac = float(getattr(inp, "fw_capex_fraction_of_blanket", defaults.get("fw_capex_fraction_of_blanket", 0.20)) or 0.20)
    bl_frac = float(getattr(inp, "blanket_capex_fraction_of_blanket", defaults.get("blanket_capex_fraction_of_blanket", 1.00)) or 1.00)
    fw_frac = min(max(fw_frac, 0.0), 1.0)
    bl_frac = min(max(bl_frac, 0.0), 1.0)

    fw_cost = float("nan")
    bl_cost = float("nan")
    if _finite(capex_bs):
        if _finite(fw_int) and fw_int > 0:
            fw_cost = max(capex_bs, 0.0) * fw_frac / fw_int
        if _finite(bl_int) and bl_int > 0:
            bl_cost = max(capex_bs, 0.0) * bl_frac / bl_int

    total = 0.0
    have_any = False
    if _finite(fw_cost):
        total += fw_cost
        have_any = True
    if _finite(bl_cost):
        total += bl_cost
        have_any = True
    if not have_any:
        total = float("nan")

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

    out: Dict[str, Any] = asdict(clo)
    out["materials_lifetime_schema_version"] = "v367.0"
    out["fw_replace_interval_y_v367"] = out.pop("fw_replace_interval_y")
    out["blanket_replace_interval_y_v367"] = out.pop("blanket_replace_interval_y")
    out["replacement_cost_MUSD_per_year_v367_total"] = out.pop("replacement_cost_MUSD_per_year_total")
    return out
