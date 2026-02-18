"""SHAMS v382.0.0 — Transport Profile Authority (1.5D-lite proxies)

Deterministic governance-only certification of profile/transport plausibility.

Hard laws:
- No solvers.
- No iteration.
- No mutation of physics truth.
- Best-effort: if required signals are missing, emit UNAVAILABLE.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        v = float(x)
        if v != v:  # NaN
            return None
        return v
    except Exception:
        return None


def _repo_root_from_here() -> Path:
    # src/certification/<file>.py -> src -> repo root
    p = Path(__file__).resolve()
    for _ in range(6):
        if (p / "contracts").exists() and (p / "ui").exists():
            return p
        p = p.parent
    # Fallback: three levels up
    return Path(__file__).resolve().parents[2]


def load_contract() -> Dict[str, Any]:
    root = _repo_root_from_here()
    path = root / "contracts" / "transport_profile_authority_v382.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _intent_from_inputs(inputs: Dict[str, Any], contract: Dict[str, Any]) -> str:
    # Best-effort intent inference.
    raw = (
        inputs.get("intent")
        or inputs.get("machine_intent")
        or inputs.get("design_intent")
        or inputs.get("mode")
        or inputs.get("scenario")
        or "research"
    )
    s = str(raw).strip().lower()
    aliases = contract.get("regime_aliases") or {}
    return str(aliases.get(s, s)) if s in aliases else ("reactor" if s in ("reactor", "powerplant", "demo") else "research")


@dataclass(frozen=True)
class TransportProfileAuthorityResult:
    version: str
    intent_tier: str

    # Signals
    peaking_ne: Optional[float]
    peaking_Te: Optional[float]
    peaking_Ti: Optional[float]
    li: Optional[float]

    # Bounds
    ne_peak_max: Optional[float]
    Te_peak_max: Optional[float]
    Ti_peak_max: Optional[float]
    li_min: Optional[float]
    li_max: Optional[float]

    # Findings
    flags: List[str]
    tier: str
    top_limiter: str

    run_id: Optional[str] = None
    inputs_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Keep deterministic ordering stable enough
        return d


def _compute_peaking(outputs: Dict[str, Any], center_keys: List[str], avg_keys: List[str]) -> Optional[float]:
    c = None
    a = None
    for k in center_keys:
        c = _safe_float(outputs.get(k))
        if c is not None:
            break
    for k in avg_keys:
        a = _safe_float(outputs.get(k))
        if a is not None:
            break
    if c is None or a is None or a <= 0.0:
        return None
    return float(c / a)


def certify_transport_profile(
    *,
    outputs: Dict[str, Any],
    inputs: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
    inputs_hash: Optional[str] = None,
    contract: Optional[Dict[str, Any]] = None,
) -> TransportProfileAuthorityResult:
    """Certify transport/profile plausibility using 1.5D-lite proxies.

    Required: outputs dict.
    Best-effort: if signals are missing, tier becomes UNAVAILABLE.
    """

    if contract is None:
        contract = load_contract()
    if inputs is None:
        inputs = {}

    version = str(contract.get("version") or "382.0.0")
    intent = _intent_from_inputs(inputs, contract)
    tiers = (contract.get("intent_tiers") or {})
    tier_cfg = tiers.get(intent) or tiers.get("research") or {}

    # Peaking factors (central / volume-average) best-effort.
    peaking_ne = _compute_peaking(
        outputs,
        center_keys=["ne0", "ne_0", "n_e0", "ne_center", "n_e_center"],
        avg_keys=["ne", "ne_bar", "n_e", "n_e_bar", "ne_avg"],
    )
    peaking_Te = _compute_peaking(
        outputs,
        center_keys=["Te0", "Te_0", "T_e0", "Te_center", "T_e_center"],
        avg_keys=["Te", "Te_bar", "T_e", "T_e_bar", "Te_avg"],
    )
    peaking_Ti = _compute_peaking(
        outputs,
        center_keys=["Ti0", "Ti_0", "T_i0", "Ti_center", "T_i_center"],
        avg_keys=["Ti", "Ti_bar", "T_i", "T_i_bar", "Ti_avg"],
    )

    # Internal inductance proxy.
    li = None
    for k in ("li", "l_i", "internal_inductance", "li3"):
        li = _safe_float(outputs.get(k))
        if li is not None:
            break

    pfmax = (tier_cfg.get("peaking_factor_max") or {})
    ne_peak_max = _safe_float(pfmax.get("ne"))
    Te_peak_max = _safe_float(pfmax.get("Te"))
    Ti_peak_max = _safe_float(pfmax.get("Ti"))

    li_cfg = tier_cfg.get("internal_inductance") or {}
    li_min = _safe_float(li_cfg.get("li_min"))
    li_max = _safe_float(li_cfg.get("li_max"))

    flags: List[str] = []

    # Determine availability.
    have_any = any(v is not None for v in (peaking_ne, peaking_Te, peaking_Ti, li))
    if not have_any:
        return TransportProfileAuthorityResult(
            version=version,
            intent_tier=intent,
            peaking_ne=peaking_ne,
            peaking_Te=peaking_Te,
            peaking_Ti=peaking_Ti,
            li=li,
            ne_peak_max=ne_peak_max,
            Te_peak_max=Te_peak_max,
            Ti_peak_max=Ti_peak_max,
            li_min=li_min,
            li_max=li_max,
            flags=["missing_required_signals"],
            tier="UNAVAILABLE",
            top_limiter="missing_required_signals",
            run_id=run_id,
            inputs_hash=inputs_hash,
        )

    # Peaking bounds checks.
    def _check_pf(name: str, val: Optional[float], vmax: Optional[float]) -> None:
        if val is None or vmax is None:
            return
        if val > vmax:
            flags.append("peaking_factor_exceeds")
            flags.append(f"{name}_peaking>{vmax:g}")

    _check_pf("ne", peaking_ne, ne_peak_max)
    _check_pf("Te", peaking_Te, Te_peak_max)
    _check_pf("Ti", peaking_Ti, Ti_peak_max)

    # li bounds check.
    if li is not None and li_min is not None and li_max is not None:
        if li < li_min or li > li_max:
            flags.append("li_out_of_bounds")
            flags.append(f"li_not_in[{li_min:g},{li_max:g}]")

    # Tiering logic.
    tier = "OK"
    top_limiter = "all_within_bounds"

    if "missing_required_signals" in flags:
        tier = "UNAVAILABLE"
        top_limiter = "missing_required_signals"
    elif "peaking_factor_exceeds" in flags or "li_out_of_bounds" in flags:
        tier = "TIGHT"
        top_limiter = "peaking_factor_exceeds" if "peaking_factor_exceeds" in flags else "li_out_of_bounds"

    if not flags:
        flags = ["all_within_bounds"]

    return TransportProfileAuthorityResult(
        version=version,
        intent_tier=intent,
        peaking_ne=peaking_ne,
        peaking_Te=peaking_Te,
        peaking_Ti=peaking_Ti,
        li=li,
        ne_peak_max=ne_peak_max,
        Te_peak_max=Te_peak_max,
        Ti_peak_max=Ti_peak_max,
        li_min=li_min,
        li_max=li_max,
        flags=flags,
        tier=tier,
        top_limiter=top_limiter,
        run_id=run_id,
        inputs_hash=inputs_hash,
    )


def certification_table_rows(cert: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Return rows, columns for display."""
    rows: List[Dict[str, Any]] = []

    def add(metric: str, value: Any, bound: Any = "", flag: str = "") -> None:
        rows.append({"Metric": metric, "Value": value, "Bound": bound, "Flag": flag})

    add("Intent tier", cert.get("intent_tier"))
    add("Tier", cert.get("tier"))
    add("Top limiter", cert.get("top_limiter"))

    add("ne peaking", cert.get("peaking_ne"), cert.get("ne_peak_max"))
    add("Te peaking", cert.get("peaking_Te"), cert.get("Te_peak_max"))
    add("Ti peaking", cert.get("peaking_Ti"), cert.get("Ti_peak_max"))
    add("Internal inductance li", cert.get("li"), f"[{cert.get('li_min')},{cert.get('li_max')}]" if cert.get('li_min') is not None else "")

    flags = cert.get("flags")
    if isinstance(flags, list):
        add("Flags", ", ".join(str(x) for x in flags))

    cols = ["Metric", "Value", "Bound", "Flag"]
    return rows, cols
