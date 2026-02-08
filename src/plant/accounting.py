from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any

@dataclass(frozen=True)
class PlantLedger:
    P_fus: float
    P_alpha: float
    P_th: float
    eta_th: float
    P_el_gross: float
    P_aux: float
    P_cd: float
    P_cry: float
    P_pumps: float
    P_el_recirc: float
    P_el_net: float
    Q_plasma: float
    Q_eng: float

def _get(d: Dict[str, Any], path: str, default: float = 0.0) -> float:
    cur: Any = d
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return float(default)
    try:
        return float(cur)
    except Exception:
        return float(default)

def compute_plant_ledger(artifact: Dict[str, Any], *, eta_th_default: float = 0.35) -> PlantLedger:
    """Deterministic plant power accounting (algebraic, no iteration)."""
    out = artifact.get("outputs", {}) if isinstance(artifact, dict) else {}
    P_fus = _get(out, "P_fus", 0.0)
    P_alpha = _get(out, "P_alpha", 0.2 * P_fus)
    P_aux = _get(out, "P_aux", _get(out, "Paux", 0.0))
    P_cd  = _get(out, "P_cd", 0.0)
    P_th  = _get(out, "P_th", P_fus)

    eta_th = _get(out, "eta_th", eta_th_default)
    if eta_th <= 0.0:
        eta_th = eta_th_default

    P_el_gross = eta_th * P_th

    # Conservative recirc placeholders (override if evaluator exports explicit)
    P_cry   = _get(out, "P_cry", 0.03 * P_el_gross)
    P_pumps = _get(out, "P_pumps", 0.01 * P_el_gross)

    P_el_recirc = P_aux + P_cd + P_cry + P_pumps
    P_el_net = P_el_gross - P_el_recirc

    denom_plasma = max(P_aux + P_cd, 1e-12)
    Q_plasma = P_fus / denom_plasma
    denom_eng = max(P_el_recirc, 1e-12)
    Q_eng = P_el_net / denom_eng

    return PlantLedger(
        P_fus=float(P_fus), P_alpha=float(P_alpha), P_th=float(P_th), eta_th=float(eta_th),
        P_el_gross=float(P_el_gross), P_aux=float(P_aux), P_cd=float(P_cd),
        P_cry=float(P_cry), P_pumps=float(P_pumps), P_el_recirc=float(P_el_recirc),
        P_el_net=float(P_el_net), Q_plasma=float(Q_plasma), Q_eng=float(Q_eng),
    )

def ledger_to_json(ledger: PlantLedger) -> Dict[str, Any]:
    return {
        "P_fus_W": ledger.P_fus,
        "P_alpha_W": ledger.P_alpha,
        "P_th_W": ledger.P_th,
        "eta_th": ledger.eta_th,
        "P_el_gross_W": ledger.P_el_gross,
        "P_aux_W": ledger.P_aux,
        "P_cd_W": ledger.P_cd,
        "P_cry_W": ledger.P_cry,
        "P_pumps_W": ledger.P_pumps,
        "P_el_recirc_W": ledger.P_el_recirc,
        "P_el_net_W": ledger.P_el_net,
        "Q_plasma": ledger.Q_plasma,
        "Q_eng": ledger.Q_eng,
    }
