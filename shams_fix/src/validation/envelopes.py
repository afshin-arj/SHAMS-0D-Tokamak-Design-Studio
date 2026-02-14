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


def _load_baseline_v2230_bounds() -> Dict[str, Tuple[Optional[float], Optional[float]]]:
    """Load the build-generated baseline envelope bounds.

    The baseline file is generated from the current codebase and is used for
    regression safety (CI). It is not an external validation claim.
    """
    import json
    from pathlib import Path

    p = Path(__file__).resolve().parent / "baselines" / "baseline_v2230.json"
    if not p.exists():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        bounds = d.get("bounds", {}) or {}
        out: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
        for k, v in bounds.items():
            if not isinstance(v, (list, tuple)) or len(v) != 2:
                continue
            lo = v[0] if v[0] is not None else None
            hi = v[1] if v[1] is not None else None
            out[str(k)] = (float(lo) if lo is not None else None, float(hi) if hi is not None else None)
        return out
    except Exception:
        return {}


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
    # Freeze-grade naming logic:
    #   ENV|<FAMILY>
    # Keep short family keys (SPARC/ARC/ITER/HH170/...) as aliases for backwards compat.
    env = {
        "ENV|BASELINE_v2230": Envelope(
            name="BASELINE_v2230",
            bounds=_load_baseline_v2230_bounds(),
            notes="Golden baseline envelope generated from this SHAMS build (v223.0). Used for regression safety, not for external validation.",
        ),
        "ENV|SPARC": Envelope(
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
        "ENV|ARC": Envelope(
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
        "ENV|ITER": Envelope(
            name="ITER",
            bounds={
                "Q_DT_eqv": (5.0, 20.0),
                "H98": (0.8, 1.3),
                "betaN": (1.2, 2.5),
                "fG": (0.6, 1.0),
                "q95": (2.8, 4.0),
                "neutron_wall_load_MW_m2": (0.0, 2.0),
            },
            notes="ITER-like moderate beta, higher density fraction envelope.",
        ),
        "ENV|HH170": Envelope(
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

    # Backwards-compatible aliases
    aliases = {
        "SPARC": "ENV|SPARC",
        "ARC": "ENV|ARC",
        "ITER": "ENV|ITER",
        "ITER-inspired": "ENV|ITER",
        "HH170": "ENV|HH170",
    }
    for legacy, canon in aliases.items():
        if canon in env:
            env[legacy] = env[canon]
    return env


def _load_baseline_v2230_bounds() -> Dict[str, Tuple[Optional[float], Optional[float]]]:
    """Load the build-generated golden baseline envelope bounds.

    The file is generated during the upgrade process and is part of the repo.
    It contains conservative (wide) bounds around the baseline outputs.
    """
    try:
        import json
        from pathlib import Path

        p = Path(__file__).resolve().parent / "baselines" / "baseline_v2230.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        bounds = data.get("bounds", {}) or {}
        # ensure correct typing
        out: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
        for k, band in bounds.items():
            lo, hi = band
            out[str(k)] = (float(lo) if lo is not None else None, float(hi) if hi is not None else None)
        return out
    except Exception:
        # Fall back to empty envelope if baseline is missing.
        return {}
