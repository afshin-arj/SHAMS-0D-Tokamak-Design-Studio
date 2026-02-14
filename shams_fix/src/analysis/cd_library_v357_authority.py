"""SHAMS — Current Drive Library Expansion Authority (v357)
Author: © 2026 Afshin Arjhangmehr

Purpose
-------
Provide explicit, deterministic, actuator-specific *engineering* constraints for CD channels.

This authority does NOT do:
- ray tracing
- deposition physics
- transport
- iterative profile closure

It DOES:
- interpret v357 channel diagnostics emitted by the frozen evaluator
- compute signed margins vs contract caps (LH accessibility, ECCD launcher power density, NBI shine-through)
- classify feasibility/fragility with an explicit min-margin rule
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import math


def _sf(out: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        if k in out:
            try:
                v = float(out[k])
                if math.isfinite(v):
                    return v
            except Exception:
                pass
    return None


def _ss(out: Dict[str, Any], *keys: str) -> Optional[str]:
    for k in keys:
        if k in out:
            try:
                s = str(out[k])
                if s.strip():
                    return s
            except Exception:
                pass
    return None


@dataclass(frozen=True)
class CDLibraryV357Result:
    cd_channel: str
    fragility_class: str
    min_margin_frac: float
    top_limiter: str
    margins: Dict[str, float]
    ctx: Dict[str, Any]


def _fragility(min_margin: float, fragile_thr: float) -> str:
    if not math.isfinite(min_margin):
        return "UNKNOWN"
    if min_margin < 0.0:
        return "INFEASIBLE"
    if min_margin < fragile_thr:
        return "FRAGILE"
    return "FEASIBLE"


def evaluate_cd_library_v357_authority(out: Dict[str, Any], contract: Any) -> CDLibraryV357Result:
    regimes = getattr(contract, "regimes", {}) or {}
    fragile_thr = float(getattr(contract, "fragile_margin_frac", 0.05))

    ch = (_ss(out, "cd_actuator_used", "cd_actuator", "CD_ACTUATOR", "cd_tech_regime") or "ECCD").strip().upper()
    if ch in ("EC", "ECH", "ECRH", "ECCD"):
        ch = "ECCD"
    elif ch in ("LH", "LHCD"):
        ch = "LHCD"
    elif ch in ("NB", "NBI"):
        ch = "NBI"
    elif ch in ("IC", "ICRF", "FWCD"):
        ch = "ICRF"

    thr = dict(regimes.get(ch, {}) or {})
    if not thr and "ECCD" in regimes:
        thr = dict(regimes["ECCD"])
        ch = "ECCD"

    margins: Dict[str, float] = {}

    # --- LHCD accessibility: n_parallel window + density ceiling (proxy) ---
    npar = _sf(out, "lhcd_n_parallel")
    nbar20 = _sf(out, "ne_bar_1e20_m3", "nbar20", "ne20")
    if ch == "LHCD" and npar is not None:
        nmin = float(thr.get("n_parallel_min", float("nan")))
        nmax = float(thr.get("n_parallel_max", float("nan")))
        if math.isfinite(nmin) and math.isfinite(nmax) and nmax > nmin:
            # Signed distance to nearest bound normalized by range
            dist = min(npar - nmin, nmax - npar)
            margins["lhcd_n_parallel_margin_frac"] = dist / (nmax - nmin)
        else:
            margins["lhcd_n_parallel_margin_frac"] = float("nan")

        nceil = float(thr.get("nbar20_max_proxy", float("nan")))
        if nbar20 is not None and math.isfinite(nceil) and nceil > 0.0:
            margins["lhcd_density_margin_frac"] = (nceil - nbar20) / nceil
        else:
            margins["lhcd_density_margin_frac"] = float("nan")
    else:
        margins["lhcd_n_parallel_margin_frac"] = float("nan")
        # density margin already computed in cd_tech_authority; keep separate here
        margins["lhcd_density_margin_frac"] = float("nan")

    # --- ECCD launcher power density cap ---
    pd = _sf(out, "eccd_launcher_power_density_MW_m2")
    if ch == "ECCD" and pd is not None:
        pdmax = float(thr.get("launcher_power_density_max_MW_m2", float("nan")))
        if math.isfinite(pdmax) and pdmax > 0.0:
            margins["eccd_launcher_pd_margin_frac"] = (pdmax - pd) / pdmax
        else:
            margins["eccd_launcher_pd_margin_frac"] = float("nan")

        lf = _sf(out, "eccd_launch_factor")
        lfmin = float(thr.get("launch_factor_min", float("nan")))
        lfmax = float(thr.get("launch_factor_max", float("nan")))
        if lf is not None and math.isfinite(lfmin) and math.isfinite(lfmax) and lfmax > lfmin:
            dist = min(lf - lfmin, lfmax - lf)
            margins["eccd_launch_factor_margin_frac"] = dist / (lfmax - lfmin)
        else:
            margins["eccd_launch_factor_margin_frac"] = float("nan")
    else:
        margins["eccd_launcher_pd_margin_frac"] = float("nan")
        margins["eccd_launch_factor_margin_frac"] = float("nan")

    # --- NBI shine-through cap ---
    st = _sf(out, "nbi_shinethrough_frac")
    if ch == "NBI" and st is not None:
        stmax = float(thr.get("shinethrough_frac_max", float("nan")))
        if math.isfinite(stmax) and stmax > 0.0:
            margins["nbi_shinethrough_margin_frac"] = (stmax - st) / stmax
        else:
            margins["nbi_shinethrough_margin_frac"] = float("nan")

        E = _sf(out, "nbi_beam_energy_keV")
        Emin = float(thr.get("beam_energy_keV_min", float("nan")))
        Emax = float(thr.get("beam_energy_keV_max", float("nan")))
        if E is not None and math.isfinite(Emin) and math.isfinite(Emax) and Emax > Emin:
            dist = min(E - Emin, Emax - E)
            margins["nbi_energy_margin_frac"] = dist / (Emax - Emin)
        else:
            margins["nbi_energy_margin_frac"] = float("nan")
    else:
        margins["nbi_shinethrough_margin_frac"] = float("nan")
        margins["nbi_energy_margin_frac"] = float("nan")

    # Select min finite margin
    finite = {k: v for k, v in margins.items() if isinstance(v, float) and math.isfinite(v)}
    if finite:
        top, mmin = min(finite.items(), key=lambda kv: kv[1])
    else:
        top, mmin = "UNKNOWN", float("nan")

    frag = _fragility(mmin, fragile_thr)

    ctx = {
        "cd_channel": ch,
        "lhcd_n_parallel": float(npar) if npar is not None else float("nan"),
        "nbar20": float(nbar20) if nbar20 is not None else float("nan"),
        "eccd_launcher_power_density_MW_m2": float(pd) if pd is not None else float("nan"),
        "nbi_shinethrough_frac": float(st) if st is not None else float("nan"),
    }

    return CDLibraryV357Result(
        cd_channel=ch,
        fragility_class=frag,
        min_margin_frac=mmin,
        top_limiter=top,
        margins=margins,
        ctx=ctx,
    )
