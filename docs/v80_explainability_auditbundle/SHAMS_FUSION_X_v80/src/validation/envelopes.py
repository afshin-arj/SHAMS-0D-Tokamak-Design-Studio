from __future__ import annotations

"""Reference envelopes for validation (decision-grade).

This module intentionally avoids brittle "match a single point" benchmarking.
Instead, it defines *envelopes* (bands/limits) for key metrics for each
reference machine family. SHAMS solutions can then be checked for whether they
lie within the intended design space.

The intent is analogous to PROCESS validation workflows, but SHAMS-native and
proxy-friendly.
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional


@dataclass(frozen=True)
class Envelope:
    name: str
    # key -> (lo, hi) where either can be None
    bounds: Dict[str, Tuple[Optional[float], Optional[float]]]
    notes: str = ""

    def check(self, out: Dict[str, float]) -> Dict[str, Dict[str, object]]:
        """Return per-metric pass/fail and margins."""
        report: Dict[str, Dict[str, object]] = {}
        for k, (lo, hi) in self.bounds.items():
            v = out.get(k, float("nan"))
            ok = True
            if lo is not None and isinstance(v, (int, float)) and v == v:
                ok = ok and (v >= lo)
            if hi is not None and isinstance(v, (int, float)) and v == v:
                ok = ok and (v <= hi)
            report[k] = {
                "value": v,
                "lo": lo,
                "hi": hi,
                "ok": bool(ok),
                "margin_lo": (v - lo) if (lo is not None and v == v) else None,
                "margin_hi": (hi - v) if (hi is not None and v == v) else None,
            }
        return report


def default_envelopes() -> Dict[str, Envelope]:
    """Curated, proxy-friendly envelopes for common reference families.

    These are intentionally broad and can be refined as SHAMS validation
    improves. Keys should align with SHAMS outputs.
    """
    return {
        "SPARC": Envelope(
            name="SPARC",
            bounds={
                "Q_DT_eqv": (5.0, 50.0),
                "H98": (0.7, 1.4),
                "betaN": (1.0, 3.5),
                "fG": (0.3, 1.2),
                "q95": (2.5, 6.0),
                "neutron_wall_load_MW_m2": (0.0, 6.0),
            },
            notes="Broad SPARC-like performance/stability envelope.",
        ),
        "ARC": Envelope(
            name="ARC",
            bounds={
                "Q_DT_eqv": (5.0, 100.0),
                "H98": (0.8, 1.6),
                "betaN": (2.0, 5.0),
                "fG": (0.3, 1.2),
                "q95": (2.5, 6.0),
                "P_e_net_MW": (50.0, None),
                "TBR": (1.05, None),
            },
            notes="ARC-like high-field pilot-plant envelope.",
        ),
        "ITER-inspired": Envelope(
            name="ITER-inspired",
            bounds={
                "Q_DT_eqv": (5.0, 20.0),
                "H98": (0.8, 1.3),
                "betaN": (1.2, 2.5),
                "fG": (0.6, 1.0),
                "q95": (2.8, 4.0),
                "neutron_wall_load_MW_m2": (0.0, 2.0),
            },
            notes="ITER-inspired moderate beta, higher density fraction envelope.",
        ),
        "HH170": Envelope(
            name="HH170",
            bounds={
                "Q_DT_eqv": (1.0, None),
                "H98": (0.6, 1.6),
                "betaN": (1.0, 5.0),
                "fG": (0.2, 1.2),
                "q95": (2.0, 7.0),
            },
            notes="HH170 placeholder envelope (Energy Singularity style).",
        ),
    }
