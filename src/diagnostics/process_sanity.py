"""PROCESS-style sanity diagnostics (non-authoritative).

These functions provide lightweight cross-checks inspired by classic PROCESS-style
0-D relations and the educational Toka_LITE code.

Design contract:
- Diagnostic only: never affects feasibility, constraints, or solver behavior.
- Best-effort: returns NaNs when inputs are missing or invalid.
- Transparent: exposes intermediate fq shape factor.

Currently implemented:
- fq_PROCESS: geometric shaping factor used in some PROCESS relations.
- Ip_from_q95_PROCESS: approximate plasma current from q95, Bt, and shape.

The implementation matches Toka_LITE (prajwal1798/Toka_LITE) equations:
  Ip(MA) = 5 * a^2 * Bt / (q95 * R * fq)

where fq is a function of aspect ratio, kappa, and delta.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Shape:
    R: float
    a: float
    kappa: float
    delta: float

    @property
    def aspect_ratio(self) -> float:
        if not math.isfinite(self.R) or not math.isfinite(self.a) or self.a == 0:
            return float("nan")
        return self.R / self.a


def fq_PROCESS(shape: Shape) -> float:
    """PROCESS-style fq shaping factor.

    Best-effort: returns NaN if parameters are not finite.
    """
    A = float(shape.aspect_ratio)
    k = float(shape.kappa)
    d = float(shape.delta)
    if not (math.isfinite(A) and math.isfinite(k) and math.isfinite(d)):
        return float("nan")

    # Toka_LITE / PROCESS-inspired functional form
    num = 1.17 - 0.65 * A * A
    den = 1.0 - A * A
    if den <= 0.0:
        den = 1e-6
    f1 = num / den
    f2 = 0.5 * (1.0 + k * k)
    f3 = 1.0 + 2.0 * d * d - 1.2 * d * d * d
    fq = f1 * f2 * f3
    return float(fq)


def Ip_from_q95_PROCESS(Bt_T: float, q95: float, shape: Shape) -> float:
    """Approximate Ip (MA) from q95, Bt, and shape (PROCESS-style)."""
    Bt_T = float(Bt_T)
    q95 = float(q95)
    if not (math.isfinite(Bt_T) and math.isfinite(q95)):
        return float("nan")
    if q95 == 0:
        return float("nan")
    fq = fq_PROCESS(shape)
    if not math.isfinite(fq) or fq == 0:
        return float("nan")
    if not (math.isfinite(shape.a) and math.isfinite(shape.R)):
        return float("nan")
    if shape.R == 0:
        return float("nan")
    return float(5.0 * shape.a * shape.a * Bt_T / (q95 * shape.R * fq))


def compute_process_sanity(outputs: Dict[str, float]) -> Dict[str, float]:
    """Return diagnostic cross-check values from an outputs dict.

    Expects (best-effort): R0_m, a_m, kappa, delta, B0_T, Ip_MA, q95.
    If q95 is missing, also tries q95_proxy.
    """
    try:
        R0 = float(outputs.get("R0_m", float("nan")))
        a = float(outputs.get("a_m", float("nan")))
        kappa = float(outputs.get("kappa", float("nan")))
        delta = float(outputs.get("delta", float("nan")))
        Bt = float(outputs.get("B0_T", float("nan")))
        Ip = float(outputs.get("Ip_MA", float("nan")))
        q95 = float(outputs.get("q95", outputs.get("q95_proxy", float("nan"))))

        shape = Shape(R=R0, a=a, kappa=kappa, delta=delta)
        fq = fq_PROCESS(shape)
        Ip_proc = Ip_from_q95_PROCESS(Bt, q95, shape)
        ratio = float("nan")
        if math.isfinite(Ip) and math.isfinite(Ip_proc) and Ip_proc != 0:
            ratio = float(Ip / Ip_proc)

        return {
            "fq_PROCESS": float(fq),
            "Ip_from_q95_PROCESS_MA": float(Ip_proc),
            "Ip_vs_PROCESS_ratio": float(ratio),
        }
    except Exception:
        return {
            "fq_PROCESS": float("nan"),
            "Ip_from_q95_PROCESS_MA": float("nan"),
            "Ip_vs_PROCESS_ratio": float("nan"),
        }
