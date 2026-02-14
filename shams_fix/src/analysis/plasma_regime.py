from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping
import math

try:
    from ..contracts.plasma_regime_authority_contract import PlasmaRegimeContract, contract_defaults
except Exception:  # supports import when `src` is on PYTHONPATH
    from contracts.plasma_regime_authority_contract import PlasmaRegimeContract, contract_defaults


@dataclass(frozen=True)
class PlasmaRegimeResult:
    confinement_regime: str
    burn_regime: str
    plasma_regime: str
    margins: Dict[str, float]
    min_margin_frac: float
    fragility_class: str


def _finite(x: Any) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else float('nan')
    except Exception:
        return float('nan')


def _signed_margin_frac(value: float, limit: float, sense: str) -> float:
    """Signed fractional margin.

    sense='le' => constraint value <= limit (positive if satisfied)
    sense='ge' => constraint value >= limit
    """
    if not (math.isfinite(value) and math.isfinite(limit)):
        return float('nan')
    if abs(limit) < 1e-12:
        return float('nan')
    if sense == 'le':
        return (limit - value) / abs(limit)
    if sense == 'ge':
        return (value - limit) / abs(limit)
    return float('nan')


def evaluate_plasma_regime(outputs: Mapping[str, Any], contract: PlasmaRegimeContract) -> PlasmaRegimeResult:
    """Deterministic regime classifier.

    Uses *existing* outputs only. Must not mutate truth.
    """
    dflt = contract_defaults(contract)
    fragile_thr = float(dflt.get('fragile_margin_frac', 0.05) or 0.05)

    # Confinement regime: prefer explicit label when present.
    conf = str(outputs.get('confinement_regime', 'unknown') or 'unknown')
    if conf not in {'H', 'L'}:
        conf = 'unknown'

    # Burn regime based on M_ign_total.
    M_ign_total = _finite(outputs.get('M_ign_total'))
    ign_thr = float(dflt.get('ignition_threshold', 1.0) or 1.0)
    aa_thr = float(dflt.get('alpha_assisted_threshold', 0.5) or 0.5)
    if math.isfinite(M_ign_total):
        if M_ign_total >= ign_thr:
            burn = 'ignited'
        elif M_ign_total >= aa_thr:
            burn = 'alpha_assisted'
        else:
            burn = 'aux_dominated'
    else:
        burn = 'aux_dominated'

    # Margins (fractional) for classic operating limits.
    margins: Dict[str, float] = {}

    # Greenwald
    fG = _finite(outputs.get('fG', outputs.get('f_G')))
    fG_max = _finite(outputs.get('greenwald_fG_max', dflt.get('greenwald_fG_max')))
    margins['greenwald_margin_frac'] = _signed_margin_frac(fG, fG_max, 'le')

    # q95
    q95 = _finite(outputs.get('q95_proxy', outputs.get('q95')))
    q95_min = _finite(outputs.get('q95_min', dflt.get('q95_min')))
    margins['q95_margin_frac'] = _signed_margin_frac(q95, q95_min, 'ge')

    # betaN
    betaN = _finite(outputs.get('betaN_proxy', outputs.get('betaN')))
    betaN_max = _finite(outputs.get('betaN_max', dflt.get('betaN_max')))
    margins['betaN_margin_frac'] = _signed_margin_frac(betaN, betaN_max, 'le')

    # H-mode access margin (only meaningful when P_LH available)
    Pin = _finite(outputs.get('Pin_MW'))
    PLH = _finite(outputs.get('P_LH_MW'))
    f_lh = _finite(outputs.get('f_LH_access', dflt.get('hmode_access_factor')))
    if math.isfinite(Pin) and math.isfinite(PLH) and math.isfinite(f_lh) and PLH > 0:
        margins['hmode_access_margin_frac'] = _signed_margin_frac(Pin, f_lh * PLH, 'ge')
    else:
        margins['hmode_access_margin_frac'] = float('nan')

    # Ignition margin
    if math.isfinite(M_ign_total):
        margins['ignition_margin_frac'] = _signed_margin_frac(M_ign_total, ign_thr, 'ge')
    else:
        margins['ignition_margin_frac'] = float('nan')

    # Determine min margin ignoring NaNs
    finite_m = [v for v in margins.values() if math.isfinite(v)]
    min_m = min(finite_m) if finite_m else float('nan')

    # Fragility class
    if not math.isfinite(min_m):
        frag = 'UNKNOWN'
    elif min_m < 0:
        frag = 'INFEASIBLE'
    elif min_m <= fragile_thr:
        frag = 'FRAGILE'
    else:
        frag = 'FEASIBLE'

    # Overall regime label (coarse, deterministic)
    # Favor explicit limiting mechanisms when margins fail.
    if math.isfinite(margins.get('greenwald_margin_frac', float('nan'))) and margins['greenwald_margin_frac'] < 0:
        overall = 'density_limited'
    elif math.isfinite(margins.get('betaN_margin_frac', float('nan'))) and margins['betaN_margin_frac'] < 0:
        overall = 'stability_limited'
    elif conf in {'H', 'L'}:
        if burn in {'ignited', 'alpha_assisted'}:
            overall = f"{conf}_burn"
        else:
            overall = f"{conf}_nonburn"
    else:
        overall = 'unknown'

    return PlasmaRegimeResult(
        confinement_regime=conf,
        burn_regime=burn,
        plasma_regime=overall,
        margins=margins,
        min_margin_frac=float(min_m),
        fragility_class=frag,
    )
