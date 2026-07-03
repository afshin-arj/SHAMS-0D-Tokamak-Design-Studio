"""
SHAMS — Impurity Species & Radiation Partition Authority (v399)
Author: © 2026 Afshin Arjhangmehr

Post-processing authority: uses TRUTH outputs (and v399 partition ledger outputs)
to compute explicit margins, tiers, and dominance-ready diagnostics.

No solvers. No iteration.

"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class ImpurityRadiationV399Result:
    tier: str
    min_margin_frac: float
    margins: Dict[str, float]
    derived: Dict[str, float]
    validity: Dict[str, Any]


def _sf(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return default


def evaluate_impurity_radiation_v399(out: Dict[str, Any], thresholds: Dict[str, float] | None = None) -> ImpurityRadiationV399Result:
    thr = thresholds or {}
    zeff_max = float(thr.get("Zeff_max", 2.5))
    f_core_rad_max = float(thr.get("f_core_rad_max", 0.75))
    f_total_rad_max = float(thr.get("f_total_rad_max", 0.85))
    # detachment margin: achieved/required - 1 (>=0 feasible)
    det_margin_min = float(thr.get("detachment_margin_min", 0.0))

    Pin = _sf(out.get("Pin_MW", out.get("P_in_MW", float("nan"))))
    Prad_core = _sf(out.get("impurity_v399_prad_core_MW", out.get("impurity_prad_core_MW", float("nan"))))
    Prad_tot = _sf(out.get("impurity_v399_prad_total_MW", out.get("impurity_prad_total_MW", float("nan"))))
    Zeff = _sf(out.get("impurity_v399_zeff", out.get("Zeff", out.get("impurity_zeff_proxy", float("nan")))))

    # radiation fractions (guarded)
    f_core = Prad_core / Pin if (Pin == Pin and Pin > 0 and Prad_core == Prad_core) else float("nan")
    f_tot = Prad_tot / Pin if (Pin == Pin and Pin > 0 and Prad_tot == Prad_tot) else float("nan")

    margins: Dict[str, float] = {}
    margins["zeff_margin"] = (zeff_max - Zeff) / zeff_max if (Zeff == Zeff and zeff_max > 0) else float("nan")
    margins["f_core_rad_margin"] = (f_core_rad_max - f_core) / f_core_rad_max if (f_core == f_core and f_core_rad_max > 0) else float("nan")
    margins["f_total_rad_margin"] = (f_total_rad_max - f_tot) / f_total_rad_max if (f_tot == f_tot and f_total_rad_max > 0) else float("nan")

    # detachment achieved vs required (from inverted detachment authority)
    prad_sol_div = _sf(out.get("impurity_v399_prad_sol_MW", float("nan"))) + _sf(out.get("impurity_v399_prad_div_MW", float("nan")))
    prad_req = _sf(out.get("detachment_prad_sol_div_required_MW", float("nan")))
    det_margin = (prad_sol_div / prad_req - 1.0) if (prad_sol_div == prad_sol_div and prad_req == prad_req and prad_req > 0.0) else float("nan")
    margins["detachment_margin"] = (det_margin - det_margin_min) / max(1e-9, abs(det_margin_min) + 1.0) if det_margin == det_margin else float("nan")

    # min margin
    mm = float("nan")
    for v in margins.values():
        if v == v:
            mm = v if (mm != mm or v < mm) else mm

    tier = "unknown"
    if mm == mm:
        if mm >= 0.10:
            tier = "comfortable"
        elif mm >= 0.0:
            tier = "near_limit"
        else:
            tier = "deficit"

    derived = {
        "f_core_rad": float(f_core) if f_core == f_core else float("nan"),
        "f_total_rad": float(f_tot) if f_tot == f_tot else float("nan"),
        "detachment_margin": float(det_margin) if det_margin == det_margin else float("nan"),
    }
    validity = dict(out.get("impurity_v399_validity", {})) if isinstance(out.get("impurity_v399_validity", {}), dict) else {}
    return ImpurityRadiationV399Result(
        tier=tier,
        min_margin_frac=float(mm),
        margins=margins,
        derived=derived,
        validity=validity,
    )


# --- Post-truth partition overlay (PROPOSAL-022) --------------------------------

import json
import math

try:
    from physics.impurities.species_library_v399 import (  # type: ignore
        ImpurityMixContractV399,
        evaluate_impurity_radiation_partition_v399,
    )
except ImportError:
    from ..physics.impurities.species_library_v399 import (  # type: ignore
        ImpurityMixContractV399,
        evaluate_impurity_radiation_partition_v399,
    )


def _float_out(out: Dict[str, Any], *keys: str) -> float:
    for k in keys:
        v = out.get(k)
        if v is not None:
            try:
                fv = float(v)
                if fv == fv:
                    return fv
            except (TypeError, ValueError):
                continue
    return float("nan")


def evaluate_impurity_radiation_authority_v399(out: Dict[str, Any], inp: Any) -> Dict[str, Any]:
    """Governance overlay: v399 impurity partition (extracted from L0 host)."""
    patch: Dict[str, Any] = {}
    patch["include_impurity_v399"] = float(bool(getattr(inp, "include_impurity_v399", False)))
    mix_json = str(getattr(inp, "impurity_mix_json_v399", "") or "").strip()
    patch["impurity_v399_mix_json"] = mix_json
    patch["zeff_max_v399"] = float(getattr(inp, "zeff_max_v399", float("nan")))
    patch["prad_core_frac_max_v399"] = float(getattr(inp, "prad_core_frac_max_v399", float("nan")))
    patch["prad_total_frac_max_v399"] = float(getattr(inp, "prad_total_frac_max_v399", float("nan")))
    patch["detachment_margin_min_v399"] = float(getattr(inp, "detachment_margin_min_v399", float("nan")))

    def _nan_block() -> None:
        patch["impurity_v399_prad_total_MW"] = float("nan")
        patch["impurity_v399_prad_core_MW"] = float("nan")
        patch["impurity_v399_prad_edge_MW"] = float("nan")
        patch["impurity_v399_prad_sol_MW"] = float("nan")
        patch["impurity_v399_prad_div_MW"] = float("nan")
        patch["impurity_v399_zeff"] = float("nan")
        patch["impurity_v399_fuel_ion_fraction"] = float("nan")
        patch["impurity_v399_by_species_MW"] = {}
        patch["impurity_v399_validity"] = {}
        patch["detachment_prad_sol_div_achieved_MW_v399"] = float("nan")
        patch["detachment_margin_v399"] = float("nan")

    if not bool(getattr(inp, "include_impurity_v399", False)):
        _nan_block()
        return patch

    ne20 = _float_out(out, "ne20", "ne_bar_1e20_m3", "nbar20")
    volume_m3 = _float_out(out, "volume_m3", "V_m3")
    t_keV = _float_out(out, "Ti_keV", "Ti")
    if volume_m3 != volume_m3:
        try:
            from phase1_models import tokamak_volume  # type: ignore
        except ImportError:
            from ..phase1_models import tokamak_volume  # type: ignore
        volume_m3 = float(
            tokamak_volume(
                float(getattr(inp, "R0_m", float("nan"))),
                float(getattr(inp, "a_m", float("nan"))),
                float(getattr(inp, "kappa", 1.7)),
            )
        )

    try:
        if not mix_json:
            _sp = str(
                getattr(inp, "impurity_contract_species", getattr(inp, "impurity_species", "")) or ""
            ).strip()
            _sp = _sp if _sp in {"C", "N", "Ne", "Ar", "W"} else "Ne"
            _fz = float(getattr(inp, "impurity_contract_f_z", getattr(inp, "impurity_frac", 0.0)) or 0.0)
            mix_json = json.dumps(
                {
                    "species_fz": {str(_sp): float(_fz)},
                    "f_core": float(getattr(inp, "impurity_partition_core", 0.50) or 0.50),
                    "f_edge": float(getattr(inp, "impurity_partition_edge", 0.20) or 0.20),
                    "f_sol": float(getattr(inp, "impurity_partition_sol", 0.20) or 0.20),
                    "f_divertor": float(getattr(inp, "impurity_partition_div", 0.10) or 0.10),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            patch["impurity_v399_mix_json"] = mix_json

        mix = ImpurityMixContractV399.from_json(mix_json)
        rp399 = evaluate_impurity_radiation_partition_v399(
            mix,
            ne20=float(ne20),
            volume_m3=float(volume_m3),
            t_keV=float(t_keV),
        )
        patch["impurity_v399_prad_total_MW"] = float(rp399.prad_total_MW)
        patch["impurity_v399_prad_core_MW"] = float(rp399.prad_core_MW)
        patch["impurity_v399_prad_edge_MW"] = float(rp399.prad_edge_MW)
        patch["impurity_v399_prad_sol_MW"] = float(rp399.prad_sol_MW)
        patch["impurity_v399_prad_div_MW"] = float(rp399.prad_div_MW)
        patch["impurity_v399_zeff"] = float(rp399.zeff)
        patch["impurity_v399_fuel_ion_fraction"] = float(rp399.fuel_ion_fraction)
        patch["impurity_v399_by_species_MW"] = dict(rp399.by_species_MW)
        patch["impurity_v399_validity"] = dict(rp399.validity)

        prad_sol_div = float(rp399.prad_sol_MW + rp399.prad_div_MW)
        prad_req = float(out.get("detachment_prad_sol_div_required_MW", float("nan")))
        if math.isfinite(prad_req) and prad_req > 0.0:
            patch["detachment_prad_sol_div_achieved_MW_v399"] = prad_sol_div
            patch["detachment_margin_v399"] = float(prad_sol_div / prad_req - 1.0)
        else:
            patch["detachment_prad_sol_div_achieved_MW_v399"] = float("nan")
            patch["detachment_margin_v399"] = float("nan")
    except Exception as e:
        patch["impurity_v399_error"] = f"{type(e).__name__}: {e}"
        patch["include_impurity_v399"] = 0.0
        patch["impurity_v399_validity"] = {"error": str(e)}
        _nan_block()

    return patch
