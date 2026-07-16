
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from .run_artifact import read_run_artifact

def build_power_balance_sankey(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Return **kwargs for ``plotly.graph_objects.Sankey`` for plant power balance.

    Notes
    -----
    - The return value is intended to be passed as ``go.Sankey(**kwargs)``.
    - This function intentionally returns a *trace kwargs dict* (``node=...``, ``link=...``)
      rather than a SHAMS-native schema, because the UI uses ``go.Sankey(**...)``.
    - This is inspired by PROCESS's Sankey plots, but nodes/links are SHAMS-native.
    - When plant Sankey ledger v419 is enabled on the point, prefer its stamped kwargs
      (PROXY, conservation-checked source→sink table).
    """
    out = artifact.get("outputs", {}) if isinstance(artifact, dict) else {}
    if not isinstance(out, dict) and isinstance(artifact, dict):
        # Allow passing raw outputs dict
        out = artifact
    # Independence 2.3: prefer v419 Sankey-grade ledger when stamped
    if bool(out.get("plant_v419_enabled", False)):
        kw = out.get("plant_v419_sankey_kwargs")
        if isinstance(kw, dict) and kw.get("node") and kw.get("link"):
            return dict(kw)
    # SHAMS outputs (phase14): these keys are produced by physics/plant.py plant_power_closure
    Pfus = float(out.get("Pfus_MW", out.get("Pfus_total_MW", 0.0)) or 0.0)
    Paux = float(out.get("Paux_MW", 0.0) or 0.0)
    Palpha = float(out.get("Palpha_MW", 0.0) or 0.0)
    Pneu = float(out.get("Pneu_MW", out.get("P_n_MW", 0.0)) or 0.0)
    Pth = float(out.get("Pth_MW", out.get("Pth_total_MW", out.get("Pth_gross_MW", 0.0))) or 0.0)
    Pnet = float(out.get("Pnet_MWe", out.get("P_e_net_MW", 0.0)) or 0.0)
    P_recirc = float(out.get("Precirc_MWe", out.get("P_recirc_MWe", out.get("P_recirc_MW", 0.0))) or 0.0)
    P_rad = float(out.get("Prad_core_MW", out.get("Prad_MW", 0.0)) or 0.0)
    P_sol = float(out.get("Psol_MW", out.get("P_SOL_MW", 0.0)) or 0.0)

    labels = [
        "Fusion",
        "Alpha → plasma",
        "Neutrons → blanket",
        "Aux heating",
        "Core radiation",
        "SOL / divertor",
        "Thermal → turbine",
        "Recirc loads",
        "Net electric",
    ]
    idx = {n: i for i, n in enumerate(labels)}
    links = []
    def add(src: str, tgt: str, val: float):
        val = float(val)
        if val <= 0:
            return
        links.append((idx[src], idx[tgt], val))

    # Build links (sources/targets are label strings).
    add("Fusion", "Alpha → plasma", Palpha)
    add("Fusion", "Neutrons → blanket", Pneu)
    add("Aux heating", "Alpha → plasma", Paux)
    add("Alpha → plasma", "Core radiation", P_rad)
    add("Alpha → plasma", "SOL / divertor", P_sol)
    add("Neutrons → blanket", "Thermal → turbine", max(Pth, 0.0))
    add("Thermal → turbine", "Recirc loads", max(P_recirc, 0.0))
    add("Thermal → turbine", "Net electric", max(Pnet, 0.0))

    src = [s for s, _, _ in links]
    tgt = [t for _, t, _ in links]
    val = [v for *_, v in links]

    return {
        "arrangement": "snap",
        "valueformat": ".2f",
        "valuesuffix": " MW",
        "node": {
            "label": labels,
            "pad": 12,
            "thickness": 14,
        },
        "link": {
            "source": src,
            "target": tgt,
            "value": val,
        },
    }

def write_sankey_html(artifact: Dict[str, Any], savepath: str | Path, title: str = "SHAMS power balance") -> Path:
    """Write an interactive HTML Sankey diagram using Plotly if installed."""
    try:
        import plotly.graph_objects as go
    except Exception as e:
        raise RuntimeError("Plotly is required for Sankey HTML. Install with `pip install plotly`.") from e

    sank = build_power_balance_sankey(artifact)
    fig = go.Figure(data=[go.Sankey(**sank)])
    fig.update_layout(title_text=title, font_size=12)

    p = Path(savepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(p), include_plotlyjs="cdn")
    return p
