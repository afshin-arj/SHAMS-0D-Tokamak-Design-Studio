from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

_CONTRACT_REL_PATH = Path(__file__).resolve().parents[2] / "contracts" / "exhaust_radiation_regime_contract.json"

def _load_contract() -> Dict[str, Any]:
    p = _CONTRACT_REL_PATH
    return json.loads(p.read_text(encoding="utf-8"))

def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

CONTRACT: Dict[str, Any] = _load_contract()
CONTRACT_SHA256: str = _sha256_file(_CONTRACT_REL_PATH)

@dataclass(frozen=True)
class ExhaustRegimeClassification:
    regime: str
    fragility_class: str
    min_margin_frac: float

    # Core derived quantities (for UI/explainability)
    detach_metric_MW_m: float
    detach_thr_MW_m: float
    detach_margin_MW_m: float

    q_div_MW_m2: float
    q_div_max_MW_m2: float
    q_margin_MW_m2: float

    f_rad_div_eff: float
    radiation_dominated_flag: float

    # Optional: detachment inversion (if available)
    f_sol_div_required: float

    def to_outputs_dict(self) -> Dict[str, float | str]:
        return {
            "exhaust_regime": str(self.regime),
            "exhaust_fragility_class": str(self.fragility_class),
            "exhaust_min_margin_frac": float(self.min_margin_frac),
            "exhaust_detach_metric_MW_m": float(self.detach_metric_MW_m),
            "exhaust_detach_thr_MW_m": float(self.detach_thr_MW_m),
            "exhaust_detach_margin_MW_m": float(self.detach_margin_MW_m),
            "exhaust_q_div_MW_m2": float(self.q_div_MW_m2),
            "exhaust_q_div_max_MW_m2": float(self.q_div_max_MW_m2),
            "exhaust_q_margin_MW_m2": float(self.q_margin_MW_m2),
            "exhaust_f_rad_div_eff": float(self.f_rad_div_eff),
            "exhaust_radiation_dominated": float(self.radiation_dominated_flag),
            "exhaust_f_sol_div_required": float(self.f_sol_div_required),
            "exhaust_contract_sha256": str(CONTRACT_SHA256),
        }

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

def classify_exhaust_regime(
    *,
    P_SOL_MW: float,
    R0_m: float,
    P_SOL_over_R_max_MW_m: float,
    q_div_MW_m2: float,
    q_div_max_MW_m2: float,
    f_rad_div_eff: float,
    f_sol_div_required: float = float("nan"),
) -> ExhaustRegimeClassification:
    """Deterministic exhaust/radiation regime classifier.

    Regime logic (ordered):
      1) overheat: q_div exceeds limit
      2) radiation_dominated: very high effective divertor radiation fraction OR required SOL+div radiation is high
      3) attached vs marginal_detach vs detached: based on P_SOL/R0 overload relative to threshold
    """
    import math

    P_SOL = max(float(P_SOL_MW), 0.0)
    R0 = max(float(R0_m), 1e-9)
    thr = max(float(P_SOL_over_R_max_MW_m), 1e-9)
    metric = P_SOL / R0

    q = float(q_div_MW_m2)
    qmax = float(q_div_max_MW_m2)
    q_margin = qmax - q

    # Normalized margins (dimensionless), conservative guards.
    m_q_frac = q_margin / max(qmax, 1e-9)

    detach_margin = thr - metric
    m_detach_frac = detach_margin / max(thr, 1e-9)

    # Radiation-dominated criteria
    g = CONTRACT.get("global") or {}
    f_rad_dom = float(g.get("radiation_dominated_f_rad_min", 0.90))
    f_req_dom = float(g.get("radiation_required_min", 0.70))

    rad_flag = 1.0 if (float(f_rad_div_eff) >= f_rad_dom) else 0.0
    if math.isfinite(f_sol_div_required):
        if float(f_sol_div_required) >= f_req_dom:
            rad_flag = 1.0

    # Choose regime
    if math.isfinite(q) and math.isfinite(qmax) and (q > qmax * 1.000001):
        regime = "overheat"
    elif rad_flag >= 0.5:
        regime = "radiation_dominated"
    else:
        band = float(g.get("detach_band_frac", 0.10))
        if metric <= thr * (1.0 - band):
            regime = "attached"
        elif metric <= thr:
            regime = "marginal_detach"
        else:
            regime = "detached"

    min_margin = min(m_q_frac, m_detach_frac)
    # If q or qmax are nan, drop q margin from min calculation
    if not (math.isfinite(q) and math.isfinite(qmax) and qmax > 0):
        min_margin = m_detach_frac
    frag = classify_fragility(min_margin)

    return ExhaustRegimeClassification(
        regime=str(regime),
        fragility_class=str(frag),
        min_margin_frac=float(min_margin),
        detach_metric_MW_m=float(metric),
        detach_thr_MW_m=float(thr),
        detach_margin_MW_m=float(detach_margin),
        q_div_MW_m2=float(q),
        q_div_max_MW_m2=float(qmax),
        q_margin_MW_m2=float(q_margin),
        f_rad_div_eff=float(f_rad_div_eff),
        radiation_dominated_flag=float(rad_flag),
        f_sol_div_required=float(f_sol_div_required),
    )
