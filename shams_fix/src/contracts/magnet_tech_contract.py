from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_CONTRACT_REL_PATH = Path(__file__).resolve().parents[2] / "contracts" / "magnet_tech_contract.json"

def _load_contract() -> Dict[str, Any]:
    p = _CONTRACT_REL_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    return data

def _sha256_file(p: Path) -> str:
    b = p.read_bytes()
    return hashlib.sha256(b).hexdigest()

CONTRACT: Dict[str, Any] = _load_contract()
CONTRACT_SHA256: str = _sha256_file(_CONTRACT_REL_PATH)

@dataclass(frozen=True)
class MagnetLimits:
    regime: str
    B_peak_limit_T: float
    sigma_allow_MPa: float
    J_eng_max_A_mm2: float
    Tcoil_min_K: float
    Tcoil_max_K: float
    sc_margin_min: float = float("nan")
    P_tf_ohmic_max_MW: float = float("nan")
    coil_heat_nuclear_max_MW: float = float("nan")
    coil_thermal_margin_min: float = 0.0
    quench_proxy_min: float = float("nan")

    def to_outputs_dict(self) -> Dict[str, float]:
        return {
            "B_peak_allow_T": float(self.B_peak_limit_T),
            "sigma_allow_MPa": float(self.sigma_allow_MPa),
            "J_eng_max_A_mm2": float(self.J_eng_max_A_mm2),
            "Tcoil_min_K": float(self.Tcoil_min_K),
            "Tcoil_max_K": float(self.Tcoil_max_K),
            "hts_margin_min": float(self.sc_margin_min),
            "P_tf_ohmic_max_MW": float(self.P_tf_ohmic_max_MW),
            "coil_heat_nuclear_max_MW": float(self.coil_heat_nuclear_max_MW),
            "coil_thermal_margin_min": float(self.coil_thermal_margin_min),
            "quench_proxy_min": float(self.quench_proxy_min),
        }

def infer_magnet_regime(magnet_technology: str) -> str:
    tech = str(magnet_technology or "").strip().upper()
    if not tech:
        return "HTS"
    # direct hits
    if "COPPER" in tech or tech in ("CU", "RESISTIVE"):
        return "CU"
    if "LTS" in tech or "NBTI" in tech or "NB3SN" in tech:
        return "LTS"
    if "HTS" in tech or "REBCO" in tech or "BI" in tech:
        return "HTS"
    # fallback: treat unknown as HTS but mark inconsistent downstream
    return "HTS"

def _regime_entry(regime: str) -> Dict[str, Any]:
    reg = (CONTRACT.get("regimes") or {}).get(regime, None)
    if not isinstance(reg, dict):
        raise KeyError(f"Unknown magnet regime: {regime}")
    return reg

def limits_for_regime(regime: str) -> MagnetLimits:
    reg = _regime_entry(regime)
    return MagnetLimits(
        regime=str(regime),
        B_peak_limit_T=float(reg.get("B_peak_limit_T")),
        sigma_allow_MPa=float(reg.get("sigma_allow_MPa")),
        J_eng_max_A_mm2=float(reg.get("J_eng_max_A_mm2")),
        Tcoil_min_K=float(reg.get("Tcoil_min_K")),
        Tcoil_max_K=float(reg.get("Tcoil_max_K")),
        sc_margin_min=float(reg.get("sc_margin_min", float("nan"))),
        P_tf_ohmic_max_MW=float(reg.get("P_tf_ohmic_max_MW", float("nan"))),
        coil_heat_nuclear_max_MW=float(reg.get("coil_heat_nuclear_max_MW", float("nan"))),
        coil_thermal_margin_min=float(reg.get("coil_thermal_margin_min", 0.0)),
        quench_proxy_min=float(reg.get("quench_proxy_min", float("nan"))),
    )

def regime_consistent(magnet_technology: str, regime: str) -> bool:
    tech = str(magnet_technology or "").strip().upper()
    aliases = _regime_entry(regime).get("aliases", []) or []
    aliases_u = [str(a).strip().upper() for a in aliases]
    if not tech:
        return True
    # Consider consistent if any alias is a substring of the tech string, or tech equals alias.
    for a in aliases_u:
        if not a:
            continue
        if tech == a or a in tech:
            return True
    # Also accept family markers (HTS/LTS/CU) present in tech
    if regime == "HTS" and ("HTS" in tech or "REBCO" in tech or "BI" in tech):
        return True
    if regime == "LTS" and ("LTS" in tech or "NBTI" in tech or "NB3SN" in tech):
        return True
    if regime == "CU" and ("COPPER" in tech or "CU" == tech or "RESIST" in tech):
        return True
    return False

def classify_fragility(min_margin_frac: float) -> str:
    try:
        thr = float((CONTRACT.get("global") or {}).get("fragile_margin_frac", 0.05))
    except Exception:
        thr = 0.05
    if min_margin_frac != min_margin_frac:
        return "UNKNOWN"
    if min_margin_frac < 0:
        return "INFEASIBLE"
    if min_margin_frac < thr:
        return "FRAGILE"
    return "FEASIBLE"
