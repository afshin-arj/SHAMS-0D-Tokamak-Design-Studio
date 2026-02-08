
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

@dataclass
class TBRProxyResult:
    TBR: float
    TBR_required: float
    margin: float
    validity: str

def tbr_proxy(out: Dict[str, float], inp: object) -> TBRProxyResult:
    """Transparent TBR proxy.

    Uses blanket thickness, shield thickness, and coverage to estimate TBR.
    This is NOT neutronics; it's a monotonic proxy with explicit validity notes.
    """
    t_blanket = float(out.get("t_blanket_m", getattr(inp, "t_blanket_m", 0.80)))
    coverage = float(getattr(inp, "blanket_coverage", 0.85))
    enrich = float(getattr(inp, "li6_enrichment", 0.30))  # fraction 0-1
    t_shield = float(out.get("t_shield_m", getattr(inp, "t_shield_m", 0.70)))

    # proxy: increases with blanket thickness and enrichment and coverage; shield steals volume
    TBR = 0.85 + 0.55 * (1.0 - pow(2.71828, -t_blanket/0.5)) * (0.6 + 0.8*enrich) * coverage - 0.05*(t_shield/0.7 - 1.0)
    req = float(getattr(inp, "TBR_required", 1.10))
    margin = TBR - req

    validity = "proxy"
    if t_blanket < 0.3 or t_blanket > 1.5:
        validity = "out_of_range"
    if coverage < 0.5 or coverage > 0.95:
        validity = "out_of_range"

    return TBRProxyResult(TBR=TBR, TBR_required=req, margin=margin, validity=validity)
