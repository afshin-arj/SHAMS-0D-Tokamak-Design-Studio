from __future__ import annotations

"""Availability 2.0 — Reliability Envelope Authority (v391.0.0).

Deterministic, algebraic governance overlay.

This authority *does not* run a RAMI simulation (no Monte Carlo, no Markov chains).
It provides an audit-friendly availability envelope driven by explicit MTBF/MTTR
proxies plus planned and maintenance downtime fractions.

Frozen-truth discipline:
- Does not modify plasma truth.
- Outputs are pure functions of (out, inp).
- No iteration / solvers.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
import hashlib
import math


def _finite(x: float) -> bool:
    return (x == x) and math.isfinite(x)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _contract_sha256() -> str:
    try:
        here = Path(__file__).resolve()
        p = here.parents[2] / "contracts" / "availability_reliability_v391_contract.json"
        if p.exists():
            return hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception:
        pass
    return ""


@dataclass(frozen=True)
class AvailabilityReliabilityEntryV391:
    subsystem: str
    mtbf_h: float
    mttr_h: float
    a_i: float
    note: str


@dataclass(frozen=True)
class AvailabilityReliabilityResultV391:
    enabled: bool
    availability_cert: float
    unplanned_downtime_frac: float
    planned_outage_frac: float
    maint_downtime_frac: float
    driver: str
    regime: str
    contract_sha256: str
    ledger: List[Dict[str, Any]]


def _ai(mtbf_h: float, mttr_h: float) -> float:
    """Per-subsystem availability factor (deterministic)."""
    if not (_finite(mtbf_h) and _finite(mttr_h)):
        return float("nan")
    mtbf_h = max(mtbf_h, 1e-6)
    mttr_h = max(mttr_h, 0.0)
    return mtbf_h / (mtbf_h + mttr_h)


def _maintenance_fraction(out: Dict[str, Any], inp: Any) -> Tuple[float, str]:
    """Deterministic maintenance downtime fraction.

    Uses the best available authority outputs, in order of precedence:
    - v368 planned/replacement outage fractions (if present)
    - v359 replacement downtime fraction (if present)
    - fallback: 0

    Applies activation/cooldown burden from v390 if available.
    """

    # Base maintenance fraction from ledger authorities
    src = "none"
    base = 0.0
    try:
        # If v368 maintenance schedule authority was enabled, use its computed replacement fraction
        repl368 = float(out.get("replacement_outage_frac_v368", float("nan")))
        if _finite(repl368):
            base = max(repl368, 0.0)
            src = "v368"
    except Exception:
        pass
    if src == "none":
        try:
            repl359 = float(out.get("availability_replacement_downtime_frac_v359", float("nan")))
            if _finite(repl359):
                base = max(repl359, 0.0)
                src = "v359"
        except Exception:
            pass

    # Apply activation/cooldown burden from v390 (governance-only)
    cooldown_days = float(out.get("cooldown_days_v390", float("nan")))
    burden = float(out.get("maintenance_burden_factor_v390", float("nan")))
    cooldown_frac = 0.0
    if _finite(cooldown_days) and cooldown_days > 0.0:
        cooldown_frac = cooldown_days / 365.0
    if not _finite(burden):
        burden = 1.0
    burden = _clamp(burden, 0.5, 5.0)

    # Add cooldown as an additive planned component, then scale the replacement workload by burden.
    maint = (base * burden) + cooldown_frac
    maint = _clamp(maint, 0.0, 0.95)
    return float(maint), src


def compute_availability_reliability_bundle_v391(out: Dict[str, Any], inp: Any) -> Dict[str, Any]:
    """Compute availability reliability envelope bundle (v391).

    Returns a dict of new outputs. If disabled, returns NaNs + empty ledger.
    """

    include = bool(getattr(inp, "include_availability_reliability_v391", False))
    if not include:
        return {
            "include_availability_reliability_v391": False,
            "availability_cert_v391": float("nan"),
            "unplanned_downtime_frac_v391": float("nan"),
            "planned_outage_frac_v391": float("nan"),
            "maint_downtime_frac_v391": float("nan"),
            "availability_driver_v391": "",
            "availability_regime_v391": "",
            "availability_ledger_v391": [],
            "availability_reliability_contract_sha256_v391": _contract_sha256(),
        }

    # Planned outage: explicit days/year input
    planned_days = float(getattr(inp, "planned_outage_days_per_y_v391", 30.0) or 30.0)
    planned_days = _clamp(planned_days, 0.0, 365.0)
    planned = planned_days / 365.0

    # Maintenance downtime (replacement + activation/cooldown burden)
    maint, maint_src = _maintenance_fraction(out, inp)

    # Per-subsystem MTBF/MTTR inputs (hours)
    subsystems = [
        ("TF", "mtbf_tf_h_v391", "mttr_tf_h_v391"),
        ("PF/CS", "mtbf_pfcs_h_v391", "mttr_pfcs_h_v391"),
        ("Divertor", "mtbf_divertor_h_v391", "mttr_divertor_h_v391"),
        ("Blanket", "mtbf_blanket_h_v391", "mttr_blanket_h_v391"),
        ("Cryoplant", "mtbf_cryo_h_v391", "mttr_cryo_h_v391"),
        ("HCD", "mtbf_hcd_h_v391", "mttr_hcd_h_v391"),
        ("BOP", "mtbf_bop_h_v391", "mttr_bop_h_v391"),
    ]

    ledger_entries: List[AvailabilityReliabilityEntryV391] = []
    a_prod = 1.0
    worst = ("", 1.0)
    for name, k_mtbf, k_mttr in subsystems:
        mtbf = float(getattr(inp, k_mtbf, 5.0e4) or 5.0e4)
        mttr = float(getattr(inp, k_mttr, 72.0) or 72.0)
        mtbf = max(mtbf, 1.0)
        mttr = max(mttr, 0.0)
        ai = _ai(mtbf, mttr)
        if _finite(ai):
            a_prod *= _clamp(ai, 0.0, 1.0)
        if _finite(ai) and ai < worst[1]:
            worst = (name, ai)
        ledger_entries.append(
            AvailabilityReliabilityEntryV391(
                subsystem=name,
                mtbf_h=float(mtbf),
                mttr_h=float(mttr),
                a_i=float(ai),
                note="A_i = MTBF/(MTBF+MTTR)",
            )
        )

    # Convert product to an unplanned downtime fraction
    a_unplanned = _clamp(float(a_prod), 0.0, 1.0)
    unplanned_downtime = 1.0 - a_unplanned
    unplanned_downtime = _clamp(unplanned_downtime, 0.0, 0.99)

    # Certified availability envelope
    A = a_unplanned * (1.0 - planned) * (1.0 - maint)
    A = _clamp(float(A), 0.0, 1.0)

    # Driver attribution
    driver = "unplanned"
    if planned >= maint and planned >= unplanned_downtime:
        driver = "planned"
    elif maint >= planned and maint >= unplanned_downtime:
        driver = f"maintenance({maint_src})"
    else:
        driver = f"unplanned(worst={worst[0]})"

    # Regime bins (deterministic, transparent)
    if A >= 0.85:
        regime = "GREEN"
    elif A >= 0.70:
        regime = "YELLOW"
    else:
        regime = "RED"

    ledger: List[Dict[str, Any]] = [e.__dict__ for e in ledger_entries]
    ledger.append(
        {
            "subsystem": "SUMMARY",
            "mtbf_h": float("nan"),
            "mttr_h": float("nan"),
            "a_i": float(a_unplanned),
            "note": f"A_unplanned=prod(A_i); planned={planned:.3f}; maint={maint:.3f}; driver={driver}; regime={regime}",
        }
    )

    return {
        "include_availability_reliability_v391": True,
        "availability_cert_v391": float(A),
        "unplanned_downtime_frac_v391": float(unplanned_downtime),
        "planned_outage_frac_v391": float(planned),
        "maint_downtime_frac_v391": float(maint),
        "availability_driver_v391": str(driver),
        "availability_regime_v391": str(regime),
        "availability_ledger_v391": ledger,
        "availability_reliability_contract_sha256_v391": _contract_sha256(),
    }
