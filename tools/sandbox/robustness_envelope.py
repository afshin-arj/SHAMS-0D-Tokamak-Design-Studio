"""Reactor Design Forge — Robustness Envelope (v1)

PROCESS often serves as a crude robustness check. SHAMS exposes robustness
explicitly as a *declared* sweep.

In v1 we implement a conservative, audit-clean approach that does not
require re-evaluating physics: we perturb declared margins by small factors
to approximate uncertainty in allowables/assumptions and compute a pass rate.

This is *not* a replacement for full UQ; it is a transparent first-order
confidence instrument.
"""

from __future__ import annotations

from typing import Any, Dict, List


DEFAULT_PERTURBATIONS = [-0.15, -0.10, -0.05, 0.0, 0.05, 0.10, 0.15]


def robustness_envelope_from_records(records: List[Dict[str, Any]], perturbations=DEFAULT_PERTURBATIONS) -> Dict[str, Any]:
    """Compute a robustness envelope from constraint records.

    We interpret each record's signed margin as a normalized headroom. A
    perturbation p applies: margin' = margin + p*|margin| (worst case). We
    then compute how many constraints remain passing (margin' >= 0).
    """

    recs = records or []
    margins = []
    for r in recs:
        m = r.get("signed_margin")
        if m is None:
            m = r.get("margin")
        try:
            margins.append(float(m))
        except Exception:
            continue

    if not margins:
        return {
            "schema": "shams.reactor_design_forge.robustness_envelope.v1",
            "ok": False,
            "reason": "No usable signed margins found in records.",
            "perturbations": list(perturbations),
            "pass_fraction": [],
        }

    pass_fracs = []
    for p in perturbations:
        passes = 0
        for m in margins:
            mp = m + p * abs(m)
            if mp >= 0:
                passes += 1
        pass_fracs.append(passes / max(1, len(margins)))

    return {
        "schema": "shams.reactor_design_forge.robustness_envelope.v1",
        "ok": True,
        "reason": None,
        "perturbations": list(perturbations),
        "pass_fraction": pass_fracs,
        "n_constraints": len(margins),
        "note": "First-order margin perturbation sweep; does not rerun truth.",
    }
