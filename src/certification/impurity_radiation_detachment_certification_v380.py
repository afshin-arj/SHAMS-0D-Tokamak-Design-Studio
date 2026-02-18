"""Impurity radiation partition & detachment requirement certification (v380.0.0).

Deterministic, governance-only certification derived from Systems outputs.

Scope
-----
- Partition total radiation into core vs SOL+div (when keys exist).
- Compute a conservative detachment requirement via algebraic inversion:
    q_div(no-rad) -> required SOL+div radiation fraction -> implied impurity seeding fraction f_z
  using src.physics.impurities.detachment_authority.

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

from src.physics.impurities.detachment_authority import detachment_requirement_from_target
from src.physics.impurities.species_library import Species


_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONTRACT_PATH = _REPO_ROOT / "contracts" / "impurity_radiation_detachment_authority_v380.json"


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


def _safe_s(out: Dict[str, Any], *keys: str) -> Optional[str]:
    for k in keys:
        if k in out:
            try:
                s = str(out[k])
                if s.strip():
                    return s
            except Exception:
                pass
    return None


def _species_from_label(label: str) -> Species:
    lab = (label or "NE").strip().upper()
    if lab in ("N", "N2", "NITROGEN"):
        return Species.N
    if lab in ("AR", "ARGON"):
        return Species.AR
    if lab in ("KR", "KRYPTON"):
        return Species.KR
    # default
    return Species.NE


@dataclass(frozen=True)
class ImpurityDetachmentCertification:
    # Radiation partition
    Prad_total_MW: float
    Prad_core_MW: float
    Prad_sol_div_MW: float
    f_core: float
    f_sol_div: float

    # Detachment requirement inversion
    q_div_no_rad_MW_m2: float
    q_div_target_MW_m2: float
    f_sol_div_required: float
    Prad_sol_div_required_MW: float
    f_z_required: float

    # Policy/tiering
    tier: str
    top_limiter: str
    contract_sha256: str
    ctx: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "impurity_radiation_detachment_authority.v380",
            "impurity_radiation_detachment_contract_sha256": self.contract_sha256,
            "Prad_total_MW": self.Prad_total_MW,
            "Prad_core_MW": self.Prad_core_MW,
            "Prad_sol_div_MW": self.Prad_sol_div_MW,
            "f_core": self.f_core,
            "f_sol_div": self.f_sol_div,
            "q_div_no_rad_MW_m2": self.q_div_no_rad_MW_m2,
            "q_div_target_MW_m2": self.q_div_target_MW_m2,
            "f_sol_div_required": self.f_sol_div_required,
            "Prad_sol_div_required_MW": self.Prad_sol_div_required_MW,
            "f_z_required": self.f_z_required,
            "tier": self.tier,
            "top_limiter": self.top_limiter,
            "ctx": self.ctx,
        }


def _tier_from_margins(fz: float, fz_warn: float, fz_block: float, avail_margin: float) -> Tuple[str, str]:
    # avail_margin = (f_sol_div - f_required) / max(f_required, eps)
    if not math.isfinite(fz) and not math.isfinite(avail_margin):
        return "UNAVAILABLE", "missing_inputs"

    # Blocking conditions
    if math.isfinite(fz) and fz > fz_block:
        return "BLOCK", "f_z_required"
    if math.isfinite(avail_margin) and avail_margin < 0.0:
        return "BLOCK", "SOL_div_radiation_shortfall"

    # Warn/tight
    if math.isfinite(fz) and fz > fz_warn:
        return "TIGHT", "f_z_required"

    # If we are within 20% of required fraction, call it tight
    if math.isfinite(avail_margin) and avail_margin < 0.2:
        return "TIGHT", "SOL_div_radiation_margin"

    return "OK", "-"


def evaluate_impurity_radiation_detachment_authority(
    out: Dict[str, Any],
    *,
    contract: Dict[str, Any] = CONTRACT,
) -> ImpurityDetachmentCertification:
    """Evaluate v380 authority from Systems outputs only."""

    defaults = (contract.get("defaults") or {})
    policy = (contract.get("policy") or {})

    # Radiation partition (best-effort)
    Prad_total = _safe_f(out, "Prad_MW", "P_rad_MW")
    if Prad_total is None:
        # fall back: from power ledger names
        Prad_total = _safe_f(out, "P_rad_total_MW", "P_rad_tot_MW")

    Prad_core = _safe_f(out, "Prad_core_MW", "P_rad_core_MW")

    if Prad_total is None:
        Prad_total = float("nan")
    if Prad_core is None:
        Prad_core = float("nan")

    Prad_sol_div = float("nan")
    if math.isfinite(Prad_total) and math.isfinite(Prad_core):
        Prad_sol_div = max(0.0, Prad_total - Prad_core)

    f_core = float("nan")
    f_sol_div = float("nan")
    if math.isfinite(Prad_total) and Prad_total > 0.0 and math.isfinite(Prad_sol_div):
        f_sol_div = Prad_sol_div / Prad_total
        f_core = 1.0 - f_sol_div

    # Detachment requirement inversion inputs
    # Need A_wet and Psep (used) plus a "no-rad" Psep estimate.
    A_wet = _safe_f(out, "A_wet_m2")
    q_div = _safe_f(out, "q_div_MW_m2")

    # If q_div isn't present, try divertor proxy naming
    if q_div is None:
        q_div = _safe_f(out, "q_par_MW_m2", "q_par_MW_per_m2")

    Pfus = _safe_f(out, "Pfus_MW", "Pfus_DT_adj_MW", "Pfus_DT_MW") or 0.0
    Paux = _safe_f(out, "Paux_MW") or 0.0
    f_sep = float(_safe_f(out, "f_Psep") or float(defaults.get("f_Psep", 0.70)))

    # Psep used in divertor proxy (includes radiation subtraction if Prad_total known)
    if math.isfinite(Prad_total):
        Psep_used = max(0.0, f_sep * (Pfus + Paux - Prad_total))
    else:
        Psep_used = max(0.0, f_sep * (Pfus + Paux))

    Psep_no_rad = max(0.0, f_sep * (Pfus + Paux))

    # Compute q_div_no_rad via linear scaling with Psep if possible
    q_div_no_rad = float("nan")
    if A_wet is not None and A_wet > 0.0:
        # Conservative: assume same geometry/peaking
        q_div_no_rad = Psep_no_rad / max(A_wet, 1e-9)
    elif q_div is not None and math.isfinite(Psep_used) and Psep_used > 0.0:
        q_div_no_rad = float(q_div) * (Psep_no_rad / Psep_used)

    # Target heat flux (use explicit max if present; otherwise contract fallback)
    q_target = _safe_f(out, "q_div_max_MW_m2")
    if q_target is None:
        q_target = float(defaults.get("q_div_target_MW_m2_fallback", 10.0))

    # For required radiation, need ne20 and plasma volume
    ne20 = _safe_f(out, "ne20", "ne20_lineavg", "ne_bar_1e20_m3", "nbar20", "ne_1e20_m3") or float("nan")
    V = _safe_f(out, "V_plasma_m3", "V_m3", "Vplasma_m3")
    if V is None:
        # rough fallback: 2π^2 R a^2 κ
        R0 = _safe_f(out, "R0_m")
        a = _safe_f(out, "a_m")
        kap = _safe_f(out, "kappa")
        if R0 is not None and a is not None and kap is not None:
            V = float(2.0 * math.pi * math.pi * max(R0, 0.0) * max(a, 0.0) ** 2 * max(kap, 0.0))
        else:
            V = float("nan")

    # Use P_SOL approximated as Psep_used (consistent with proxy definition)
    P_SOL = float(Psep_used)

    species_label = (_safe_s(out, "seed_species", "impurity_species") or str(defaults.get("species", "NE")))
    species = _species_from_label(species_label)

    T_sol_keV = float(defaults.get("T_sol_keV", 0.08))
    fV = float(defaults.get("f_V_sol_div", 0.12))

    req = detachment_requirement_from_target(
        species=species,
        ne20=float(ne20 if math.isfinite(ne20) else 0.0),
        volume_m3=float(V if math.isfinite(V) else 0.0),
        P_SOL_MW=float(P_SOL),
        q_div_no_rad_MW_m2=float(q_div_no_rad),
        q_div_target_MW_m2=float(q_target),
        T_sol_keV=T_sol_keV,
        f_V_sol_div=fV,
    )

    f_req = float(req.f_sol_div_required)

    # Availability: compare inferred SOL+div radiation fraction to required
    avail_margin = float("nan")
    if math.isfinite(f_sol_div) and math.isfinite(f_req) and f_req > 0.0:
        avail_margin = (f_sol_div - f_req) / max(f_req, 1e-30)

    fz_warn = float(policy.get("fz_required_warn", 0.002))
    fz_block = float(policy.get("fz_required_block", 0.010))

    tier, limiter = _tier_from_margins(float(req.f_z_required), fz_warn, fz_block, avail_margin)

    ctx = {
        "species": species.name,
        "species_label": species_label,
        "T_sol_keV": T_sol_keV,
        "f_V_sol_div": fV,
        "f_Psep": f_sep,
        "Psep_used_MW": Psep_used,
        "Psep_no_rad_MW": Psep_no_rad,
        "A_wet_m2": A_wet,
        "q_div_MW_m2": q_div,
        "avail_margin_frac": avail_margin,
        "detachment_validity": req.validity,
    }

    return ImpurityDetachmentCertification(
        Prad_total_MW=float(Prad_total),
        Prad_core_MW=float(Prad_core),
        Prad_sol_div_MW=float(Prad_sol_div),
        f_core=float(f_core),
        f_sol_div=float(f_sol_div),
        q_div_no_rad_MW_m2=float(q_div_no_rad),
        q_div_target_MW_m2=float(q_target),
        f_sol_div_required=float(req.f_sol_div_required),
        Prad_sol_div_required_MW=float(req.prad_sol_div_required_MW),
        f_z_required=float(req.f_z_required),
        tier=str(tier),
        top_limiter=str(limiter),
        contract_sha256=str(CONTRACT_SHA256),
        ctx=ctx,
    )


def certification_table_rows(cert: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten for UI table."""
    ctx = cert.get("ctx") if isinstance(cert.get("ctx"), dict) else {}
    return {
        "tier": cert.get("tier"),
        "top_limiter": cert.get("top_limiter"),
        "species": ctx.get("species"),
        "Prad_total_MW": cert.get("Prad_total_MW"),
        "Prad_core_MW": cert.get("Prad_core_MW"),
        "Prad_sol_div_MW": cert.get("Prad_sol_div_MW"),
        "f_sol_div": cert.get("f_sol_div"),
        "f_sol_div_required": cert.get("f_sol_div_required"),
        "Prad_sol_div_required_MW": cert.get("Prad_sol_div_required_MW"),
        "f_z_required": cert.get("f_z_required"),
        "q_div_no_rad_MW_m2": cert.get("q_div_no_rad_MW_m2"),
        "q_div_target_MW_m2": cert.get("q_div_target_MW_m2"),
    }
