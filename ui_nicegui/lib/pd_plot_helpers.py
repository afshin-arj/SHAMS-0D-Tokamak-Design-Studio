"""Matplotlib plot helpers for Point Designer Plot Deck (PNG bytes)."""
from __future__ import annotations

import io
import math
from typing import Any, Dict, List, Optional, Tuple


def _sf(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _bar_png(labels: List[str], values: List[float], *, title: str, ylabel: str = "") -> Optional[bytes]:
    if len(labels) < 1:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.bar(labels, values)
    ax.set_title(title)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    return buf.getvalue()


def _barh_png(labels: List[str], values: List[float], *, title: str, xlabel: str = "") -> Optional[bytes]:
    if len(labels) < 1:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.barh(labels, values)
    ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    return buf.getvalue()


def plot_power_stack(out: Dict[str, Any]) -> Optional[bytes]:
    pairs = [
        ("Fusion", _sf(out.get("Pfus_total_MW", out.get("Pfus_DT_adj_MW", out.get("P_fus_MW", out.get("Pfus_MW")))))),
        ("Aux", _sf(out.get("Paux_MW"))),
        ("Recirc", _sf(out.get("P_recirc_MW", out.get("P_e_recirc_MW")))),
        ("Net", _sf(out.get("P_e_net_MW", out.get("P_net_e_MW")))),
    ]
    labs, vals = [], []
    for lab, v in pairs:
        if v == v:
            labs.append(lab)
            vals.append(v)
    return _bar_png(labs, vals, title="Power stack (screening)", ylabel="MW")


def plot_tight_constraints(artifact: Dict[str, Any]) -> Optional[bytes]:
    tight = (artifact.get("run_summary") or {}).get("tightest_hard_constraints", [])
    tight = [t for t in (tight or []) if isinstance(t, dict)]
    tight = sorted(tight, key=lambda t: _sf(t.get("margin_frac", float("inf"))))[:10]
    if not tight:
        return None
    names = [str(t.get("name", "?")) for t in tight][::-1]
    mfs = [_sf(t.get("margin_frac")) for t in tight][::-1]
    return _barh_png(names, mfs, title="Tightest hard constraints", xlabel="Margin fraction (>=1 pass)")


def plot_regime_dials(out: Dict[str, Any]) -> Optional[bytes]:
    pairs = [
        ("q95 (proxy)", _sf(out.get("q95_proxy", out.get("q95")))),
        ("βN (screen)", _sf(out.get("beta_N", out.get("betaN_proxy", out.get("betaN"))))),
        ("fG", _sf(out.get("fG"))),
    ]
    labs, vals = [], []
    for lab, v in pairs:
        if v == v:
            labs.append(lab)
            vals.append(v)
    return _bar_png(labs, vals, title="Regime dials (dimensionless proxies)")


def plot_engineering_severity(out: Dict[str, Any]) -> Optional[bytes]:
    pairs = [
        ("Bpeak (T)", _sf(out.get("B_peak_T", out.get("Bpeak_T")))),
        ("qdiv", _sf(out.get("q_div_MW_m2"))),
        ("NWL", _sf(out.get("NWL_MW_m2", out.get("nwl_MW_m2")))),
    ]
    labs, vals = [], []
    for lab, v in pairs:
        if v == v:
            labs.append(lab)
            vals.append(v)
    return _bar_png(labs, vals, title="Engineering severity (screening)")


def plot_power_balance_bars(out: Dict[str, Any]) -> Optional[bytes]:
    keys = {
        "Paux": out.get("Paux_MW"),
        "Pfus": out.get("Pfus_total_MW", out.get("Pfus_DT_adj_MW")),
        "Pα": out.get("Palpha_MW", out.get("Palpha_dep_MW")),
        "Prad": out.get("Prad_core_MW"),
        "P_SOL": out.get("P_SOL_MW"),
        "P_net": out.get("P_e_net_MW", out.get("P_net_e_MW")),
    }
    labs, vals = [], []
    for k, v in keys.items():
        fv = _sf(v)
        if fv == fv:
            labs.append(k)
            vals.append(fv)
    return _bar_png(labs, vals, title="Power balance (MW)", ylabel="MW")


def plot_stability_limits(out: Dict[str, Any]) -> Optional[bytes]:
    # L0 keys: q95_proxy, beta_N / betaN_proxy, fG (never bare q95/betaN/fGW).
    pairs = [
        ("q95", _sf(out.get("q95_proxy", out.get("q95")))),
        ("βN", _sf(out.get("beta_N", out.get("betaN_proxy", out.get("betaN"))))),
        ("fG", _sf(out.get("fG", out.get("greenwald_fraction", out.get("fGW"))))),
    ]
    labs, vals = [], []
    for lab, v in pairs:
        if v == v:
            labs.append(lab)
            vals.append(v)
    return _bar_png(labs, vals, title="Stability & limits (cyl. / screening proxies)")


def plot_geometry_build(out: Dict[str, Any]) -> Optional[bytes]:
    pairs = [
        ("R0", _sf(out.get("R0_m"))),
        ("a", _sf(out.get("a_m"))),
        ("κ", _sf(out.get("kappa"))),
        ("A=R/a", (
            _sf(out.get("aspect_ratio", out.get("A")))
            if out.get("aspect_ratio") is not None or out.get("A") is not None
            else (
                (_sf(out.get("R0_m")) / _sf(out.get("a_m")))
                if _sf(out.get("a_m")) > 0
                else float("nan")
            )
        )),
    ]
    labs, vals = [], []
    for lab, v in pairs:
        if v == v:
            labs.append(lab)
            vals.append(v)
    return _bar_png(labs, vals, title="Geometry / build")


def plot_confinement(out: Dict[str, Any]) -> Optional[bytes]:
    pairs = [
        ("H98", _sf(out.get("H98"))),
        ("H_regime", _sf(out.get("H_regime"))),
        ("τE_eff (s)", _sf(out.get("tauE_eff_s", out.get("tauE_s", out.get("tau_E_s"))))),
        ("τIPB98 (s)", _sf(out.get("tauIPB98_s", out.get("tauIPB")))),
    ]
    labs, vals = [], []
    for lab, v in pairs:
        if v == v:
            labs.append(lab)
            vals.append(v)
    return _bar_png(labs, vals, title="Confinement proxies")
