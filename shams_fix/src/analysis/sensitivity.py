from __future__ import annotations
"""Sensitivity and uncertainty utilities.

SHAMS truth is deterministic and reviewer-safe. Robustness is handled via:
- quasi-static phase envelopes
- deterministic interval-corner uncertainty contracts

This module additionally provides an audit-friendly *deterministic* local
sensitivity pack for external optimizers.

Legacy note
-----------
The Monte Carlo helper remains for historical experiments, but is not part of
the SHAMS robustness authority path.
"""

import math
import random
from dataclasses import asdict, replace
from typing import Dict, List, Tuple, Callable, Optional

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore
from physics.hot_ion import hot_ion_point
from constraints.system import build_constraints_from_outputs

def _rand_lognormal(mu: float, sigma: float) -> float:
    # mu,sigma in linear space, approximate by sampling in log space
    if mu <= 0:
        return mu
    return math.exp(random.gauss(math.log(mu), sigma))

def monte_carlo_feasibility(
    base: PointInputs,
    n: int = 200,
    *,
    # relative uncertainties (1-sigma) on multiplicative factors
    sigma_confinement: float = 0.10,
    sigma_lambda_q: float = 0.25,
    sigma_hts_jc: float = 0.10,
    # additive uncertainties
    sigma_zeff: float = 0.15,
    seed: Optional[int] = None,
) -> Dict[str, object]:
    """
    Simple Monte Carlo uncertainty engine.

    Returns:
      - p_feasible: fraction of samples that satisfy all constraints
      - worst_constraints: list of most frequently violated constraints
      - samples: list of dict summaries (lightweight)
    """
    if seed is not None:
        random.seed(seed)

    violated_counts: Dict[str, int] = {}
    samples: List[Dict[str, float]] = []
    ok_count = 0

    for _ in range(max(1, int(n))):
        inp = replace(
            base,
            confinement_mult=_rand_lognormal(max(getattr(base, "confinement_mult", 1.0), 1e-6), sigma_confinement),
            lambda_q_mult=_rand_lognormal(max(getattr(base, "lambda_q_mult", 1.0), 1e-6), sigma_lambda_q),
            hts_Jc_mult=_rand_lognormal(max(getattr(base, "hts_Jc_mult", 1.0), 1e-6), sigma_hts_jc),
            zeff=max(1.0, random.gauss(base.zeff, sigma_zeff)),
        )
        out = hot_ion_point(inp)
        cs = build_constraints_from_outputs(out)
        ok = all(c.ok for c in cs)
        if ok:
            ok_count += 1
        else:
            for c in cs:
                if not c.ok:
                    violated_counts[c.name] = violated_counts.get(c.name, 0) + 1

        samples.append({
            "Q": float(out.get("Q_DT_eqv", float("nan"))),
            "H98": float(out.get("H98", float("nan"))),
            "Pnet_MW": float(out.get("P_e_net_MW", float("nan"))),
            "Bpeak_T": float(out.get("B_peak_T", float("nan"))),
            "ok": 1.0 if ok else 0.0,
        })

    worst = sorted(violated_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    return {
        "p_feasible": ok_count / max(1, int(n)),
        "worst_constraints": [{"name": k, "count": v} for k, v in worst],
        "samples": samples,
    }


def deterministic_sensitivity_pack(
    base: PointInputs,
    *,
    variables: Dict[str, float],
    outputs: List[str],
    step_rel: float = 1e-3,
) -> Dict[str, object]:
    """Compute a deterministic local sensitivity pack.

    Parameters
    ----------
    base:
        Baseline point.
    variables:
        Mapping var_name -> characteristic scale (used when base value is 0).
        Example: {"Paux_MW": 10.0, "fG": 0.1, "Bt_T": 0.5}
    outputs:
        List of hot_ion_point output keys to differentiate.
    step_rel:
        Relative perturbation size (central difference), default 1e-3.

    Returns
    -------
    dict with:
      - base_outputs
      - base_constraints (with residuals)
      - jacobian: nested dict d(output)/d(var)
      - constraint_tightness: top constraints by normalized residual
    """
    if step_rel <= 0:
        raise ValueError("step_rel must be > 0")

    base_out = hot_ion_point(base)
    cs = build_constraints_from_outputs(base_out)

    def _tightness() -> List[Dict[str, float]]:
        rows = []
        for c in cs:
            try:
                rows.append({"name": c.name, "residual": float(c.residual())})
            except Exception:
                continue
        rows.sort(key=lambda r: r["residual"], reverse=True)
        return rows[:15]

    jac: Dict[str, Dict[str, float]] = {k: {} for k in outputs}
    log: List[Dict[str, object]] = []

    for var, scale in (variables or {}).items():
        if not hasattr(base, var):
            log.append({"var": var, "status": "SKIP", "reason": "not_in_PointInputs"})
            continue
        x0 = float(getattr(base, var))
        s = abs(x0) if abs(x0) > 0 else float(abs(scale) if scale else 1.0)
        h = max(step_rel * s, 1e-12)

        try:
            plus = replace(base, **{var: x0 + h})
            minus = replace(base, **{var: x0 - h})
        except Exception as e:
            log.append({"var": var, "status": "SKIP", "reason": f"replace_failed: {e}"})
            continue

        out_p = hot_ion_point(plus)
        out_m = hot_ion_point(minus)

        for ok in outputs:
            try:
                fp = float(out_p.get(ok, float("nan")))
                fm = float(out_m.get(ok, float("nan")))
                if fp == fp and fm == fm:
                    jac[ok][var] = (fp - fm) / (2.0 * h)
                else:
                    jac[ok][var] = float("nan")
            except Exception:
                jac[ok][var] = float("nan")

        log.append({"var": var, "h": h, "status": "OK"})

    return {
        "schema_version": "deterministic_sensitivity_pack.v1",
        "base_inputs": asdict(base),
        "base_outputs": {k: float(base_out.get(k, float("nan"))) for k in outputs},
        "constraints_tightness": _tightness(),
        "jacobian": jac,
        "log": log,
    }
