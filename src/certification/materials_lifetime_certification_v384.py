from __future__ import annotations

"""Materials & Lifetime Tightening certification (v384.0.0).

This certification is governance-only: it summarizes the deterministic v384 outputs
(divertor+magnet lifetime proxies, downtime-coupled CF, and annualized replacement cost)
and provides a simple tier classification.

No solves, no iteration.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def _finite(x: float) -> bool:
    return (x == x) and (x != float("inf")) and (x != -float("inf"))


def _sf(outputs: Dict[str, Any], key: str, default: float = float("nan")) -> float:
    try:
        return float(outputs.get(key, default))
    except Exception:
        return float(default)


@dataclass(frozen=True)
class MaterialsLifetimeCertificationV384:
    schema: str
    run_id: Optional[str]
    inputs_hash: Optional[str]

    enabled: bool
    tier: str

    limiting_component: str
    replacement_interval_y: float

    fw_lifetime_yr: float
    blanket_lifetime_yr: float
    divertor_lifetime_yr: float
    magnet_lifetime_yr: float

    replacement_downtime_fraction: float
    capacity_factor_used: float

    replacement_cost_MUSD_per_year: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "run_id": self.run_id,
            "inputs_hash": self.inputs_hash,
            "enabled": self.enabled,
            "tier": self.tier,
            "limiting_component": self.limiting_component,
            "replacement_interval_y": self.replacement_interval_y,
            "fw_lifetime_yr": self.fw_lifetime_yr,
            "blanket_lifetime_yr": self.blanket_lifetime_yr,
            "divertor_lifetime_yr_v384": self.divertor_lifetime_yr,
            "magnet_lifetime_yr_v384": self.magnet_lifetime_yr,
            "replacement_downtime_fraction_v384": self.replacement_downtime_fraction,
            "capacity_factor_used_v384": self.capacity_factor_used,
            "replacement_cost_MUSD_per_year_v384": self.replacement_cost_MUSD_per_year,
        }


def certify_materials_lifetime_v384(
    outputs: Dict[str, Any],
    inputs: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
    inputs_hash: Optional[str] = None,
) -> MaterialsLifetimeCertificationV384:
    enabled = bool(outputs.get("include_materials_lifetime_v384", False))

    lim_comp = str(outputs.get("limiting_component_v384", "unknown"))
    repl_int = _sf(outputs, "replacement_interval_y_v384")

    fw = _sf(outputs, "fw_lifetime_yr")
    bl = _sf(outputs, "blanket_lifetime_yr")
    div = _sf(outputs, "divertor_lifetime_yr_v384")
    mag = _sf(outputs, "magnet_lifetime_yr_v384")

    dt = _sf(outputs, "replacement_downtime_fraction_v384")
    cf = _sf(outputs, "capacity_factor_used_v384")
    rc = _sf(outputs, "replacement_cost_MUSD_per_year_v384")

    # Tier: PASS if enabled and all primary quantities are finite; TIGHT if any are near bounds; BLOCK if enabled but non-finite.
    tier = "OFF"
    if enabled:
        primary = [repl_int, div, mag, cf, rc]
        if all(_finite(x) for x in primary):
            tier = "PASS"
        else:
            tier = "BLOCK"

        # Optional caps: if present and tight, flag TIGHT even if passing.
        try:
            cf_min = float(outputs.get("capacity_factor_min_v384", float("nan")))
        except Exception:
            cf_min = float("nan")
        try:
            rc_max = float(outputs.get("replacement_cost_max_MUSD_per_y_v384", float("nan")))
        except Exception:
            rc_max = float("nan")
        if tier == "PASS":
            tight = False
            if _finite(cf_min) and _finite(cf) and cf_min > 0.0 and (cf - cf_min) / max(cf_min, 1e-9) < 0.10:
                tight = True
            if _finite(rc_max) and _finite(rc) and rc_max > 0.0 and (rc_max - rc) / max(rc_max, 1e-9) < 0.10:
                tight = True
            if tight:
                tier = "TIGHT"

    return MaterialsLifetimeCertificationV384(
        schema="materials_lifetime_certification_v384",
        run_id=run_id,
        inputs_hash=inputs_hash,
        enabled=enabled,
        tier=tier,
        limiting_component=lim_comp,
        replacement_interval_y=repl_int,
        fw_lifetime_yr=fw,
        blanket_lifetime_yr=bl,
        divertor_lifetime_yr=div,
        magnet_lifetime_yr=mag,
        replacement_downtime_fraction=dt,
        capacity_factor_used=cf,
        replacement_cost_MUSD_per_year=rc,
    )


def certification_table_rows(cert: Dict[str, Any]) -> Tuple[List[List[Any]], List[str]]:
    cols = ["Field", "Value", "Units", "Note"]
    rows: List[List[Any]] = []
    rows.append(["tier", cert.get("tier", ""), "-", "PASS/TIGHT/BLOCK/OFF"])
    rows.append(["limiting_component", cert.get("limiting_component", ""), "-", "Minimum replacement interval driver"])
    rows.append(["replacement_interval_y", cert.get("replacement_interval_y", float("nan")), "yr", "Min interval across components"])
    rows.append(["divertor_lifetime_yr_v384", cert.get("divertor_lifetime_yr_v384", float("nan")), "yr", "q_div-based proxy"])
    rows.append(["magnet_lifetime_yr_v384", cert.get("magnet_lifetime_yr_v384", float("nan")), "yr", "Margin-based proxy"])
    rows.append(["replacement_downtime_fraction_v384", cert.get("replacement_downtime_fraction_v384", float("nan")), "-", "Σ downtime/interval"])
    rows.append(["capacity_factor_used_v384", cert.get("capacity_factor_used_v384", float("nan")), "-", "Base CF × (1-downtime)"])
    rows.append(["replacement_cost_MUSD_per_year_v384", cert.get("replacement_cost_MUSD_per_year_v384", float("nan")), "MUSD/y", "Annualized proxy"])
    return rows, cols
