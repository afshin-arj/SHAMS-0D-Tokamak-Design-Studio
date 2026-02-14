from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, Optional

from .envelopes import Envelope

@dataclass
class EnvelopeCheckResult:
    ok: bool
    failures: Dict[str, str]
    values: Dict[str, float]

def check_point_against_envelope(outputs: Dict[str, float], envelope: Envelope) -> EnvelopeCheckResult:
    """Check outputs against an envelope, returning detailed failures.

    Envelope rules are simple min/max bands on output keys.
    """
    failures: Dict[str, str] = {}
    values: Dict[str, float] = {}
    for k, band in envelope.bounds.items():
        v = float(outputs.get(k, float("nan")))
        values[k] = v
        lo, hi = band
        if v != v:  # nan
            failures[k] = "nan"
        else:
            if lo is not None and v < float(lo):
                failures[k] = f"below min ({v:.4g} < {lo})"
            if hi is not None and v > float(hi):
                failures[k] = f"above max ({v:.4g} > {hi})"
    return EnvelopeCheckResult(ok=(len(failures)==0), failures=failures, values=values)
