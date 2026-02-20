from __future__ import annotations

"""Neutronics & Activation Authority 3.0 (v390.0.0)

Deterministic, algebraic tightening of neutronics/activation plausibility.

Scope (v390)
------------
- Effective shielding thickness requirement (regime-binned, algebraic)
- First-wall damage proxy (DPA-lite) and derived FW lifetime in FPY
- Activation index proxy and cooldown/maintenance binning

Hard rules
----------
- No Monte Carlo, no transport, no iteration.
- No modification of upstream truth; only derives additional outputs.
- Optional feasibility constraints are explicit; NaN disables.

Units
-----
- Thickness: cm
- DPA rate: DPA/FPY
- Lifetime: FPY
- Activation index: dimensionless

Validity
--------
Screening-level proxies only. Interpret as governance signals.
"""

from dataclasses import dataclass
import math
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class ActivationLedgerEntryV390:
    item: str
    value: float
    units: str
    driver: str
    notes: str = ""


def _finite(x: float) -> bool:
    return bool(x == x and math.isfinite(x))


def _clip(x: float, lo: float, hi: float) -> float:
    return float(min(max(x, lo), hi))


def _bin_wall_load(q_MW_m2: float) -> str:
    if not _finite(q_MW_m2):
        return "UNKNOWN"
    if q_MW_m2 < 1.0:
        return "LOW"
    if q_MW_m2 < 2.5:
        return "MID"
    return "HIGH"


def _blanket_mult(blanket_class: str) -> float:
    bc = (blanket_class or "STANDARD").strip().upper()
    # Conservative multipliers: more activation burden for compact / high power density concepts
    return {
        "STANDARD": 1.00,
        "DEMO": 1.10,
        "PILOT": 0.95,
        "COMPACT": 1.20,
        "HEAVY_SHIELD": 0.90,
    }.get(bc, 1.00)


def compute_neutronics_activation_bundle_v390(out: Dict[str, float], inp: object) -> Dict[str, object]:
    """Compute v390 neutronics/activation proxies.

    Parameters
    ----------
    out:
        Existing output dict from truth evaluation (will not be mutated except by caller merging this dict).
    inp:
        PointInputs-like object.

    Returns
    -------
    Dict[str, object]
        Scalar outputs + a small ledger list for audit UI.
    """
    include = bool(getattr(inp, "include_neutronics_activation_v390", False))

    # Always carry through input caps for transparency
    shield_margin_min_cm = float(getattr(inp, "shield_margin_min_cm_v390", float("nan")))
    fw_life_min_fpy = float(getattr(inp, "fw_life_min_fpy_v390", float("nan")))
    dpa_max = float(getattr(inp, "dpa_per_fpy_max_v390", float("nan")))
    activation_max = float(getattr(inp, "activation_index_max_v390", float("nan")))

    if not include:
        return {
            "include_neutronics_activation_v390": False,
            "shield_required_cm_v390": float("nan"),
            "shield_effective_cm_v390": float("nan"),
            "shield_margin_cm_v390": float("nan"),
            "shield_regime_v390": "OFF",
            "dpa_per_fpy_v390": float("nan"),
            "fw_life_fpy_v390": float("nan"),
            "activation_index_v390": float("nan"),
            "cooldown_bin_v390": "OFF",
            "cooldown_days_v390": float("nan"),
            "maintenance_burden_factor_v390": float("nan"),
            "shield_margin_min_cm_v390": shield_margin_min_cm,
            "fw_life_min_fpy_v390": fw_life_min_fpy,
            "dpa_per_fpy_max_v390": dpa_max,
            "activation_index_max_v390": activation_max,
            "neutronics_activation_ledger_v390": [],
        }

    ledger: List[ActivationLedgerEntryV390] = []

    # --- Inputs from truth outputs ---
    Pfus = float(out.get("Pfus_total_MW", out.get("Pfus_MW", float("nan"))))
    q_wall = float(out.get("neutron_wall_load_MW_m2", float("nan")))
    att_fast = float(out.get("neutron_attenuation_fast", out.get("neutron_attenuation_factor", float("nan"))))

    # --- Effective shielding thickness (cm): use declared radial stack if available ---
    t_blank = float(getattr(inp, "t_blanket_m", 0.0))
    t_shield = float(getattr(inp, "t_shield_m", 0.0))
    t_vv = float(getattr(inp, "t_vv_m", 0.0))

    # A simple “effective” shielding thickness relevant to ex-vessel activation: blanket + shield + half VV.
    t_eff_cm = 100.0 * (max(t_blank, 0.0) + max(t_shield, 0.0) + 0.5 * max(t_vv, 0.0))

    blanket_class = str(getattr(inp, "blanket_class_v390", "STANDARD"))
    bmult = _blanket_mult(blanket_class)

    # --- Shield requirement envelope (cm) ---
    # A conservative deterministic scaling: increases with fusion power and wall load.
    # This is *not* transport; it is a screening envelope.
    #
    # t_req = t0(bin) * (Pfus/500)^a * (q_wall/1)^b * blanket_mult
    # with explicit bin-dependent t0.
    bin_q = _bin_wall_load(q_wall)
    t0_map = {
        "LOW":  45.0,
        "MID":  60.0,
        "HIGH": 80.0,
        "UNKNOWN": 60.0,
    }
    t0 = float(t0_map.get(bin_q, 60.0))

    a = float(getattr(inp, "shield_req_Pfus_exp_v390", 0.25))
    b = float(getattr(inp, "shield_req_qwall_exp_v390", 0.50))

    Pf = max(Pfus, 0.0) if _finite(Pfus) else 0.0
    qw = max(q_wall, 0.0) if _finite(q_wall) else 0.0

    t_req_cm = t0 * (max(Pf / 500.0, 1e-9) ** _clip(a, 0.0, 1.0)) * (max(qw / 1.0, 1e-9) ** _clip(b, 0.0, 2.0)) * max(bmult, 0.5)

    shield_margin_cm = float(t_eff_cm - t_req_cm)
    shield_regime = f"{bin_q}" if bin_q != "UNKNOWN" else "MID"

    ledger.append(ActivationLedgerEntryV390(
        item="Shield effective thickness",
        value=float(t_eff_cm),
        units="cm",
        driver="t_blanket_m + t_shield_m + 0.5*t_vv_m",
        notes="Effective thickness used for activation/shielding envelope (ex-vessel relevance).",
    ))
    ledger.append(ActivationLedgerEntryV390(
        item="Shield required thickness",
        value=float(t_req_cm),
        units="cm",
        driver="regime bin + Pfus + q_wall",
        notes=f"Envelope: t0({bin_q})*(Pfus/500)^a*(q_wall)^b*blanket_mult; blanket_class={blanket_class}.",
    ))

    # --- DPA-lite (DPA/FPY) ---
    # For FW damage, shielding does not help much; we therefore base primarily on wall load.
    # Use a conservative linear map: dpa = k*q_wall with k set by a declared reference.
    k_dpa = float(getattr(inp, "fw_dpa_per_fpy_per_MWm2_v390", 15.0))
    dpa = k_dpa * qw

    # FW life in FPY
    dpa_limit = float(getattr(inp, "fw_dpa_limit_v390", 20.0))
    fw_life_fpy = float(dpa_limit / max(dpa, 1e-30)) if _finite(dpa_limit) else float("nan")

    ledger.append(ActivationLedgerEntryV390(
        item="FW DPA rate (lite)",
        value=float(dpa),
        units="DPA/FPY",
        driver="neutron_wall_load_MW_m2",
        notes=f"Linear proxy: {k_dpa:g}*q_wall. Shielding does not mitigate first-wall DPA in this envelope.",
    ))

    # --- Activation index + cooldown bin ---
    # Use fast attenuation as a proxy that improved shielding reduces ex-vessel activation burden.
    # att_fast~exp(-ΣR t); smaller means better shielding. We map to a bounded benefit factor.
    att = att_fast if _finite(att_fast) else 1.0
    att = _clip(att, 0.0, 1.0)
    benefit = 1.0 / (1.0 + 4.0 * (1.0 - att))  # ranges ~[0.2,1]

    # Activation increases with Pfus and wall load, reduced by shielding (benefit).
    act = (max(Pf / 500.0, 1e-9) ** 0.50) * (max(qw / 1.0, 1e-9) ** 0.30) * (1.0 / max(benefit, 1e-6)) * max(bmult, 0.5)
    act = float(_clip(act, 0.0, 10.0))

    if act < 0.7:
        cooldown_bin, cooldown_days, burden = "LOW", 7.0, 1.00
    elif act < 1.3:
        cooldown_bin, cooldown_days, burden = "MID", 30.0, 1.10
    else:
        cooldown_bin, cooldown_days, burden = "HIGH", 90.0, 1.25

    ledger.append(ActivationLedgerEntryV390(
        item="Activation index",
        value=float(act),
        units="-",
        driver="Pfus + q_wall + attenuation",
        notes="Dimensionless proxy; higher implies longer cooldown/maintenance burden.",
    ))

    # Optional note on attenuation
    ledger.append(ActivationLedgerEntryV390(
        item="Fast attenuation factor",
        value=float(att),
        units="-",
        driver="neutronics/materials stack",
        notes="Uses neutron_attenuation_fast when available; mapped to activation benefit factor.",
    ))

    return {
        "include_neutronics_activation_v390": True,
        "shield_required_cm_v390": float(t_req_cm),
        "shield_effective_cm_v390": float(t_eff_cm),
        "shield_margin_cm_v390": float(shield_margin_cm),
        "shield_regime_v390": str(shield_regime),
        "dpa_per_fpy_v390": float(dpa),
        "fw_life_fpy_v390": float(fw_life_fpy),
        "activation_index_v390": float(act),
        "cooldown_bin_v390": str(cooldown_bin),
        "cooldown_days_v390": float(cooldown_days),
        "maintenance_burden_factor_v390": float(burden),
        "shield_margin_min_cm_v390": shield_margin_min_cm,
        "fw_life_min_fpy_v390": fw_life_min_fpy,
        "dpa_per_fpy_max_v390": dpa_max,
        "activation_index_max_v390": activation_max,
        "neutronics_activation_ledger_v390": [e.__dict__ for e in ledger],
    }
