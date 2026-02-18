"""Advanced current-drive authority certification (v381.0.0).

Deterministic, governance-only certification derived from Systems outputs.

Purpose
-------
PROCESS historically provides broader, regime-aware current-drive libraries. SHAMS v381
adds an explicit *credibility certification* layer for current drive claims using
algebraic checks and regime flags.

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
from typing import Any, Dict, Optional, Tuple
import hashlib
import json
import math


_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONTRACT_PATH = _REPO_ROOT / "contracts" / "current_drive_authority_v381.json"


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()


def _sha256_file(p: Path) -> str:
    return _sha256_bytes(p.read_bytes())


def _load_contract() -> Dict[str, Any]:
    return json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))


CONTRACT: Dict[str, Any] = _load_contract()
CONTRACT_SHA256: str = _sha256_file(_CONTRACT_PATH)


def _safe_f(out: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        if k in out:
            try:
                v = float(out[k])
                if math.isfinite(v):
                    return v
            except Exception:
                pass
    return None


def _tier_from(f_ni: float, f_warn: float, f_block: float, eta: float, eta_warn: float, eta_block: float,
              flags: Dict[str, bool]) -> Tuple[str, str]:
    if not math.isfinite(f_ni) and not math.isfinite(eta):
        return "UNAVAILABLE", "missing_inputs"

    # Hard blocks
    if math.isfinite(f_ni) and f_ni > f_block:
        return "BLOCK", "f_NI_claim"
    if math.isfinite(eta) and eta > eta_block:
        return "BLOCK", "eta_cd_claim"

    # Regime blocks
    if flags.get("lh_density_block", False):
        return "BLOCK", "LH_density_limit"
    if flags.get("ech_density_block", False):
        return "BLOCK", "ECH_density_cutoff"
    if flags.get("nbi_shinethrough_block", False):
        return "BLOCK", "NBI_shinethrough"

    # Tight
    if math.isfinite(f_ni) and f_ni > f_warn:
        return "TIGHT", "f_NI_claim"
    if math.isfinite(eta) and eta > eta_warn:
        return "TIGHT", "eta_cd_claim"

    # Warn-level regime
    if flags.get("lh_density_warn", False):
        return "TIGHT", "LH_density_limit"
    if flags.get("ech_density_warn", False):
        return "TIGHT", "ECH_density_cutoff"
    if flags.get("nbi_shinethrough_warn", False):
        return "TIGHT", "NBI_shinethrough"

    return "OK", "-"


@dataclass(frozen=True)
class CurrentDriveCertification:
    Ip_MA: float
    I_bs_MA: float
    I_cd_MA: float
    f_NI_claim: float
    f_NI_reported: float

    P_CD_MW: float
    eta_cd_MA_per_MW: float

    # Regime flags (best-effort)
    lh_density_warn: bool
    lh_density_block: bool
    ech_density_warn: bool
    ech_density_block: bool
    nbi_shinethrough_warn: bool
    nbi_shinethrough_block: bool

    tier: str
    top_limiter: str
    contract_sha256: str
    ctx: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "current_drive_authority.v381",
            "current_drive_authority_contract_sha256": self.contract_sha256,
            "Ip_MA": self.Ip_MA,
            "I_bs_MA": self.I_bs_MA,
            "I_cd_MA": self.I_cd_MA,
            "f_NI_claim": self.f_NI_claim,
            "f_NI_reported": self.f_NI_reported,
            "P_CD_MW": self.P_CD_MW,
            "eta_cd_MA_per_MW": self.eta_cd_MA_per_MW,
            "flags": {
                "lh_density_warn": self.lh_density_warn,
                "lh_density_block": self.lh_density_block,
                "ech_density_warn": self.ech_density_warn,
                "ech_density_block": self.ech_density_block,
                "nbi_shinethrough_warn": self.nbi_shinethrough_warn,
                "nbi_shinethrough_block": self.nbi_shinethrough_block,
            },
            "tier": self.tier,
            "top_limiter": self.top_limiter,
            "ctx": self.ctx,
        }


def evaluate_current_drive_authority(
    out: Dict[str, Any],
    *,
    contract: Dict[str, Any] = CONTRACT,
) -> CurrentDriveCertification:
    """Evaluate v381 current-drive authority from Systems outputs only."""

    defaults = (contract.get("defaults") or {})

    Ip = _safe_f(out, "Ip_MA", "I_p_MA")
    Ibs = _safe_f(out, "I_bs_MA", "I_boot_MA", "Ibs_MA")
    Icd = _safe_f(out, "I_cd_MA", "Icd_MA")

    f_NI_reported = _safe_f(out, "f_NI")

    # CD power accounting: prefer explicit P_CD_MW
    Pcd = _safe_f(out, "P_CD_MW", "Pcd_MW", "P_cd_MW")

    # Density for regime flags
    ne20 = _safe_f(out, "ne20", "ne_20", "n_e_20", "nbar_20")

    # Fill NaNs
    Ip = float(Ip) if Ip is not None else float("nan")
    Ibs = float(Ibs) if Ibs is not None else float("nan")
    Icd = float(Icd) if Icd is not None else float("nan")
    Pcd = float(Pcd) if Pcd is not None else float("nan")
    f_NI_reported = float(f_NI_reported) if f_NI_reported is not None else float("nan")

    # Claim: bootstrap + external CD fraction
    f_NI_claim = float("nan")
    if math.isfinite(Ip) and Ip > 0.0 and (math.isfinite(Ibs) or math.isfinite(Icd)):
        f_NI_claim = (0.0 if not math.isfinite(Ibs) else Ibs) + (0.0 if not math.isfinite(Icd) else Icd)
        f_NI_claim = f_NI_claim / Ip

    # Effective efficiency (MA/MW)
    eta = float("nan")
    if math.isfinite(Icd) and math.isfinite(Pcd) and Pcd > 0.0:
        eta = Icd / Pcd

    # Regime flags (best-effort): only uses density thresholds; component powers may be absent.
    lh_lim = float(defaults.get("lh_density_limit_ne20", 1.2))
    ech_cut = float(defaults.get("ech_density_cutoff_ne20", 1.8))
    nbi_warn = float(defaults.get("nbi_shinethrough_warn_ne20", 0.2))
    nbi_block = float(defaults.get("nbi_shinethrough_block_ne20", 0.1))

    flags = {
        "lh_density_warn": False,
        "lh_density_block": False,
        "ech_density_warn": False,
        "ech_density_block": False,
        "nbi_shinethrough_warn": False,
        "nbi_shinethrough_block": False,
    }

    if ne20 is not None and math.isfinite(float(ne20)):
        ne20v = float(ne20)
        # LHCD: density limit (accessibility)
        if ne20v >= lh_lim:
            flags["lh_density_warn"] = True
        if ne20v >= 1.25 * lh_lim:
            flags["lh_density_block"] = True
        # ECH: very rough high-density accessibility/cutoff flag
        if ne20v >= ech_cut:
            flags["ech_density_warn"] = True
        if ne20v >= 1.20 * ech_cut:
            flags["ech_density_block"] = True
        # NBI: shine-through risk when density is *too low*
        if ne20v <= nbi_warn:
            flags["nbi_shinethrough_warn"] = True
        if ne20v <= nbi_block:
            flags["nbi_shinethrough_block"] = True

    # Tiering thresholds
    f_warn = float(defaults.get("f_NI_warn", 0.70))
    f_block = float(defaults.get("f_NI_block", 0.90))
    eta_warn = float(defaults.get("eta_cd_warn_MA_per_MW", 0.02))
    eta_block = float(defaults.get("eta_cd_block_MA_per_MW", 0.08))

    tier, limiter = _tier_from(f_NI_claim, f_warn, f_block, eta, eta_warn, eta_block, flags)

    ctx = {
        "ne20": (float(ne20) if ne20 is not None and math.isfinite(float(ne20)) else None),
        "thresholds": {
            "f_NI_warn": f_warn,
            "f_NI_block": f_block,
            "eta_cd_warn_MA_per_MW": eta_warn,
            "eta_cd_block_MA_per_MW": eta_block,
            "lh_density_limit_ne20": lh_lim,
            "ech_density_cutoff_ne20": ech_cut,
            "nbi_shinethrough_warn_ne20": nbi_warn,
            "nbi_shinethrough_block_ne20": nbi_block,
        },
        "notes": "Best-effort regime flags from density only when component-specific powers are unavailable in outputs.",
    }

    return CurrentDriveCertification(
        Ip_MA=Ip,
        I_bs_MA=Ibs,
        I_cd_MA=Icd,
        f_NI_claim=f_NI_claim,
        f_NI_reported=f_NI_reported,
        P_CD_MW=Pcd,
        eta_cd_MA_per_MW=eta,
        lh_density_warn=bool(flags["lh_density_warn"]),
        lh_density_block=bool(flags["lh_density_block"]),
        ech_density_warn=bool(flags["ech_density_warn"]),
        ech_density_block=bool(flags["ech_density_block"]),
        nbi_shinethrough_warn=bool(flags["nbi_shinethrough_warn"]),
        nbi_shinethrough_block=bool(flags["nbi_shinethrough_block"]),
        tier=str(tier),
        top_limiter=str(limiter),
        contract_sha256=CONTRACT_SHA256,
        ctx=ctx,
    )


def certification_table_rows(cert: Dict[str, Any]) -> Dict[str, Any]:
    """Compact row for UI tables."""
    flags = cert.get("flags", {}) if isinstance(cert.get("flags", {}), dict) else {}
    return {
        "tier": cert.get("tier"),
        "top_limiter": cert.get("top_limiter"),
        "f_NI_claim": cert.get("f_NI_claim"),
        "f_NI_reported": cert.get("f_NI_reported"),
        "eta_cd_MA_per_MW": cert.get("eta_cd_MA_per_MW"),
        "LH_density_warn": bool(flags.get("lh_density_warn", False)),
        "ECH_density_warn": bool(flags.get("ech_density_warn", False)),
        "NBI_shinethrough_warn": bool(flags.get("nbi_shinethrough_warn", False)),
        "contract_sha256": cert.get("current_drive_authority_contract_sha256", ""),
    }
