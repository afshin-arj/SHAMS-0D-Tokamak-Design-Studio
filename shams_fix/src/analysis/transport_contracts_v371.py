from __future__ import annotations

"""Transport Contract Library evaluation (v371.0).

This module is *post-processing-only* (governance): it consumes already-computed
frozen-truth outputs and point inputs to derive:

- a deterministic confinement regime label (L/H) based on the existing P_LH proxy
- a regime-conditioned envelope over available τE scalings
- optional gating checks for optimistic vs robust caps on required confinement

It MUST NOT modify the physics operating point.
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from phase1_models import (
    tauE_ipb98y2,
    tauE_iter89p,
    tauE_kaye_goldston,
    tauE_neo_alcator,
    tauE_mirnov,
    tauE_shimomura,
    p_LH_martin08,
    q95_proxy_cyl,
)



from pathlib import Path

def load_transport_contract_v371(profile: str = "default") -> Dict[str, Any]:
    """Load the v371 transport contract (JSON).

    The contract is part of governance (assumption registry). It is a static
    JSON file in repo_root/contracts/. If the file is missing (should not
    happen in a release), a minimal deterministic fallback is used to remain
    import-safe.
    """
    repo_root = Path(__file__).resolve().parents[2]
    p = repo_root / "contracts" / "transport_contracts_v371_contract.json"
    if p.is_file():
        try:
            import json
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Minimal fallback (deterministic)
    return {
        "name": "Transport Contract Library v371",
        "version": "v371.0",
        "envelopes": ["IPB98Y2", "ITER89P", "KG", "NEOALC"],
        "regime_classifier": "P_LH proxy (Martin-2008) using P_SOL vs P_LH",
        "notes": "Fallback contract used because JSON could not be read.",
    }


def _norm(s: Any) -> str:
    return str(s or "").strip().upper().replace(" ", "")


def _finite(x: Any) -> Optional[float]:
    try:
        f = float(x)
        if f != f:
            return None
        return f
    except Exception:
        return None


def _tau_from_scaling(
    scaling: str,
    *,
    Ip_MA: float,
    Bt_T: float,
    ne20: float,
    Ploss_MW: float,
    R_m: float,
    a_m: float,
    kappa: float,
    A_eff: float,
) -> float:
    s = _norm(scaling)
    if s in {"IPB98Y2", "IPB98", "H98"}:
        return tauE_ipb98y2(Ip_MA=Ip_MA, Bt_T=Bt_T, ne20=ne20, Ploss_MW=Ploss_MW, R_m=R_m, a_m=a_m, kappa=kappa, M_amu=A_eff)
    if s in {"ITER89P", "ITER89-P", "89P"}:
        return tauE_iter89p(Ip_MA=Ip_MA, Bt_T=Bt_T, ne20=ne20, Ploss_MW=Ploss_MW, R_m=R_m, a_m=a_m, kappa=kappa, M_amu=A_eff)
    if s in {"KG", "KAYE", "KAYE-GOLDSTON", "KAYEGOLDSTON"}:
        return tauE_kaye_goldston(Ip_MA=Ip_MA, Bt_T=Bt_T, ne20_lineavg=ne20, Ploss_MW=Ploss_MW, R_m=R_m, a_m=a_m, kappa=kappa, M_amu=A_eff)
    if s in {"NEOALC", "NEO-ALCATOR", "NEOALCATOR", "NA"}:
        qstar = q95_proxy_cyl(R_m, a_m, Bt_T, Ip_MA, kappa)
        return tauE_neo_alcator(ne20_lineavg=ne20, R_m=R_m, a_m=a_m, qstar=qstar)
    if s in {"MIRNOV"}:
        return tauE_mirnov(a_m=a_m, kappa=kappa, Ip_MA=Ip_MA)
    if s in {"SHIMOMURA", "SHIMO"}:
        return tauE_shimomura(R_m=R_m, a_m=a_m, Bt_T=Bt_T, kappa=kappa, M_amu=A_eff)
    # Unknown scaling -> fall back to IPB98
    return tauE_ipb98y2(Ip_MA=Ip_MA, Bt_T=Bt_T, ne20=ne20, Ploss_MW=Ploss_MW, R_m=R_m, a_m=a_m, kappa=kappa, M_amu=A_eff)


def evaluate_transport_contracts_v371(
    *,
    inp: Any,
    out_partial: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate v371 transport contract diagnostics.

    Parameters
    ----------
    inp:
        PointInputs-like object (attribute access).
    out_partial:
        Frozen-truth outputs dict (may be partially constructed); must contain at least
        the basic plasma scalars needed for confinement scalings.
    """

    enabled = bool(getattr(inp, "include_transport_contracts_v371", False))
    if not enabled:
        return {
            "transport_contracts_v371_enabled": False,
            "transport_contracts_v371_contract": load_transport_contract_v371(None),
        }

    # Collect required primitives
    Ip_MA = float(getattr(inp, "Ip_MA"))
    Bt_T = float(getattr(inp, "Bt_T"))
    R_m = float(getattr(inp, "R0_m"))
    a_m = float(getattr(inp, "a_m"))
    kappa = float(getattr(inp, "kappa"))
    A_eff = float(getattr(inp, "A_eff", getattr(inp, "A_eff", 2.5)))

    ne20 = _finite(out_partial.get("ne20", out_partial.get("ne20_lineavg", None)))
    if ne20 is None:
        ne20 = _finite(out_partial.get("ne_20", None))
    ne20 = float(ne20 or 0.0)

    Ploss_MW = _finite(out_partial.get("P_SOL_MW", out_partial.get("Ploss_MW", None)))
    Ploss_MW = float(Ploss_MW or 0.0)

    # Determine confinement regime via existing P_LH proxy.
    # Use existing S if available; otherwise attempt to fall back to evaluator's S_m2 key.
    S_m2 = _finite(out_partial.get("S_m2", out_partial.get("S", None)))
    S_m2 = float(S_m2 or 0.0)
    Pin_MW = _finite(out_partial.get("Pin_MW", None))
    if Pin_MW is None:
        # Pin may not be in partial dict; use Paux + Palpha_dep when available.
        Pin_MW = _finite(out_partial.get("Paux_MW", 0.0))
        Palpha = _finite(out_partial.get("Palpha_dep_MW", 0.0))
        Pin_MW = float(Pin_MW or 0.0) + float(Palpha or 0.0)
    Pin_MW = float(Pin_MW or 0.0)

    PLH_MW = p_LH_martin08(ne20_lineavg=ne20, Bt_T=Bt_T, S_m2=max(S_m2, 0.0), A_eff=float(getattr(inp, "A_eff", 2.0) or 2.0))
    f_access = float(getattr(inp, "f_LH_access", 1.0) or 1.0)
    confinement_regime = "H" if (PLH_MW > 0.0 and Pin_MW >= f_access * PLH_MW) else "L"

    contract = load_transport_contract_v371(str(getattr(inp, "transport_contract_profile", "default")))
    scalings: List[str] = list(contract.get("scalings_H") if confinement_regime == "H" else contract.get("scalings_L"))
    scalings = [str(s) for s in scalings if str(s).strip()]
    if not scalings:
        scalings = ["IPB98Y2"]

    tau_vals: List[Tuple[str, float]] = []
    for s in scalings:
        try:
            tau = float(
                _tau_from_scaling(
                    s,
                    Ip_MA=Ip_MA,
                    Bt_T=Bt_T,
                    ne20=ne20,
                    Ploss_MW=Ploss_MW,
                    R_m=R_m,
                    a_m=a_m,
                    kappa=kappa,
                    A_eff=float(getattr(inp, "A_eff", 2.5) or 2.5),
                )
            )
            if tau == tau and tau > 0.0:
                tau_vals.append((s, tau))
        except Exception:
            continue

    if not tau_vals:
        tau_vals = [("IPB98Y2", float(_tau_from_scaling("IPB98Y2", Ip_MA=Ip_MA, Bt_T=Bt_T, ne20=ne20, Ploss_MW=Ploss_MW, R_m=R_m, a_m=a_m, kappa=kappa, A_eff=float(getattr(inp, "A_eff", 2.5) or 2.5))))]

    tau_min = min(t for _, t in tau_vals)
    tau_max = max(t for _, t in tau_vals)

    # Required confinement relative to IPB98(y,2) is already computed by truth
    H_required = _finite(out_partial.get("H_required", None))
    if H_required is None:
        # Best-effort compute from tauE_required/tauIPB when available.
        tau_req = _finite(out_partial.get("tauE_required_s", None))
        tau_ipb = _finite(out_partial.get("tauIPB_s", None))
        if tau_req is not None and tau_ipb is not None and tau_ipb > 0.0:
            H_required = float(tau_req) / float(tau_ipb)
    H_required = float(H_required) if H_required is not None else float("nan")

    # Optional gating caps (explicitly set by user; NaN disables)
    Hmax_opt = float(getattr(inp, "H_required_max_optimistic", float("nan")))
    Hmax_rob = float(getattr(inp, "H_required_max_robust", float("nan")))
    pass_opt = float("nan")
    pass_rob = float("nan")
    if H_required == H_required and Hmax_opt == Hmax_opt and Hmax_opt > 0.0:
        pass_opt = 1.0 if H_required <= Hmax_opt else 0.0
    if H_required == H_required and Hmax_rob == Hmax_rob and Hmax_rob > 0.0:
        pass_rob = 1.0 if H_required <= Hmax_rob else 0.0

    return {
        "transport_contracts_v371_enabled": True,
        "transport_contracts_v371_contract": contract,
        "transport_confinement_regime_v371": confinement_regime,
        "P_LH_martin08_MW": float(PLH_MW),
        "transport_contract_scalings_v371": scalings,
        "tauE_envelope_min_s": float(tau_min),
        "tauE_envelope_max_s": float(tau_max),
        "H_required": float(H_required),
        "H_required_max_optimistic": float(Hmax_opt),
        "H_required_max_robust": float(Hmax_rob),
        "transport_pass_optimistic": float(pass_opt),
        "transport_pass_robust": float(pass_rob),
        "transport_contract_stamp_sha256": "6b1f63102459f805df66d3d4cfb526d33acbb3eb8bcdad167338cc8c11eecc38",
    }
