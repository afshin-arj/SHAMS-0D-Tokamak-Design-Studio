"""Current-drive library certification (v395.0.0).

Purpose
-------
SHAMS v395 expands the current-drive (CD) efficiency proxy to allow a deterministic
multi-actuator mix (ECCD/LHCD/NBI/ICRF) with explicit per-channel bookkeeping.

Hard laws
---------
- No solvers.
- No iteration.
- No truth re-evaluation; uses already-produced Systems outputs.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
import math

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONTRACT_PATH = _REPO_ROOT / "contracts" / "current_drive_library_v395.json"


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()


def _sha256_file(p: Path) -> str:
    return _sha256_bytes(p.read_bytes())


def _load_contract() -> Dict[str, Any]:
    return json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))


CONTRACT: Dict[str, Any] = _load_contract()
CONTRACT_SHA256: str = _sha256_file(_CONTRACT_PATH)


def _safe_f(out: Dict[str, Any], key: str) -> Optional[float]:
    try:
        v = float(out.get(key, float("nan")))
        if math.isfinite(v):
            return v
    except Exception:
        pass
    return None


def _safe_s(out: Dict[str, Any], key: str) -> Optional[str]:
    try:
        s = str(out.get(key, ""))
        if s.strip():
            return s
    except Exception:
        pass
    return None


@dataclass(frozen=True)
class CDLibraryCertificationV395:
    model_used: str
    actuator_used: str
    mix_detected: bool
    channels: Dict[str, Dict[str, float]]
    P_cd_launch_MW: float
    I_cd_total_MA: float
    gamma_eff_A_per_W: float
    eta_wallplug_eff: float
    tier: str
    top_limiter: str
    contract_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "current_drive_library.v395",
            "current_drive_library_contract_sha256": self.contract_sha256,
            "model_used": self.model_used,
            "actuator_used": self.actuator_used,
            "mix_detected": self.mix_detected,
            "P_cd_launch_MW": self.P_cd_launch_MW,
            "I_cd_total_MA": self.I_cd_total_MA,
            "gamma_eff_A_per_W": self.gamma_eff_A_per_W,
            "eta_wallplug_eff": self.eta_wallplug_eff,
            "channels": self.channels,
            "tier": self.tier,
            "top_limiter": self.top_limiter,
        }


def certify_current_drive_library_v395(outputs: Dict[str, Any], contract: Dict[str, Any] = CONTRACT) -> CDLibraryCertificationV395:
    defaults = contract.get("defaults") or {}
    gamma_min = float(defaults.get("gamma_min_A_per_W", 5e-4))

    model_used = _safe_s(outputs, "cd_model_used") or _safe_s(outputs, "cd_model") or "UNKNOWN"
    actuator_used = _safe_s(outputs, "cd_actuator_used") or _safe_s(outputs, "cd_actuator_used") or "UNKNOWN"

    Pcd = _safe_f(outputs, "P_cd_launch_MW")
    if Pcd is None:
        Pcd = _safe_f(outputs, "P_CD_MW")
    Icd = _safe_f(outputs, "I_cd_MA")
    gamma_eff = _safe_f(outputs, "gamma_cd_A_per_W_used")
    if gamma_eff is None:
        gamma_eff = _safe_f(outputs, "eta_CD_A_W")

    eta_eff = _safe_f(outputs, "eta_cd_wallplug_used")
    if eta_eff is None:
        eta_eff = _safe_f(outputs, "eta_cd_wallplug")

    Pcd = float(Pcd) if Pcd is not None else float("nan")
    Icd = float(Icd) if Icd is not None else float("nan")
    gamma_eff = float(gamma_eff) if gamma_eff is not None else float("nan")
    eta_eff = float(eta_eff) if eta_eff is not None else float("nan")

    # Detect channel bookkeeping
    ch_names = ["ECCD", "LHCD", "NBI", "ICRF"]
    ch: Dict[str, Dict[str, float]] = {}
    mix_detected = False
    for n in ch_names:
        Pn = _safe_f(outputs, f"P_cd_{n}_MW")
        In = _safe_f(outputs, f"I_cd_{n}_MA")
        gn = _safe_f(outputs, f"gamma_cd_{n}_A_per_W")
        et = _safe_f(outputs, f"eta_cd_wallplug_{n}")
        if any(v is not None for v in (Pn, In, gn, et)):
            mix_detected = True
        ch[n] = {
            "P_cd_MW": float(Pn) if Pn is not None else 0.0,
            "I_cd_MA": float(In) if In is not None else 0.0,
            "gamma_A_per_W": float(gn) if gn is not None else float("nan"),
            "eta_wallplug": float(et) if et is not None else float("nan"),
        }

    # Tiering: conservative and purely audit-driven
    tier = "OK"
    top = "-"

    if not math.isfinite(Pcd) or not math.isfinite(Icd) or Pcd <= 0.0:
        tier, top = "UNAVAILABLE", "missing_Pcd_or_Icd"
    else:
        # basic gamma floor
        if math.isfinite(gamma_eff) and gamma_eff < gamma_min:
            tier, top = "TIGHT", "gamma_eff_floor"
        # if mix is detected, require at least one finite channel gamma
        if mix_detected:
            finite = [v for v in (ch["ECCD"]["gamma_A_per_W"], ch["LHCD"]["gamma_A_per_W"], ch["NBI"]["gamma_A_per_W"], ch["ICRF"]["gamma_A_per_W"]) if math.isfinite(v)]
            if not finite:
                tier, top = "BLOCK", "mix_missing_channel_gammas"

    return CDLibraryCertificationV395(
        model_used=model_used,
        actuator_used=actuator_used,
        mix_detected=mix_detected,
        channels=ch,
        P_cd_launch_MW=Pcd,
        I_cd_total_MA=Icd,
        gamma_eff_A_per_W=gamma_eff,
        eta_wallplug_eff=eta_eff,
        tier=tier,
        top_limiter=top,
        contract_sha256=CONTRACT_SHA256,
    )


def certification_table_rows(cert: Dict[str, Any]) -> Tuple[List[List[Any]], List[str]]:
    # For UI tables
    cols = ["Field", "Value"]
    rows: List[List[Any]] = []
    def add(k: str, v: Any):
        rows.append([k, v])

    add("tier", cert.get("tier"))
    add("top_limiter", cert.get("top_limiter"))
    add("model_used", cert.get("model_used"))
    add("actuator_used", cert.get("actuator_used"))
    add("mix_detected", cert.get("mix_detected"))
    add("P_cd_launch_MW", cert.get("P_cd_launch_MW"))
    add("I_cd_total_MA", cert.get("I_cd_total_MA"))
    add("gamma_eff_A_per_W", cert.get("gamma_eff_A_per_W"))
    add("eta_wallplug_eff", cert.get("eta_wallplug_eff"))

    return rows, cols
