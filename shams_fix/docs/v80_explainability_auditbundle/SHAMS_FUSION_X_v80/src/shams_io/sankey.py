
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from .run_artifact import read_run_artifact

def build_power_balance_sankey(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Return a Plotly-compatible Sankey dict for plant power balance.

    This is inspired by PROCESS's plot_plotly_sankey.py. The exact nodes/links are SHAMS-native.
    """
    out = artifact.get("outputs", {})
    # SHAMS outputs (phase14): these keys are produced by physics/plant.py plant_power_closure
    Pfus = float(out.get("Pfus_MW", 0.0))
    Paux = float(out.get("Paux_MW", 0.0))
    Palpha = float(out.get("Palpha_MW", 0.0))
    Pneu = float(out.get("Pneu_MW", 0.0))
    Pth = float(out.get("Pth_MW", out.get("Pth_gross_MW", 0.0)))
    Pnet = float(out.get("Pnet_MWe", 0.0))
    P_recirc = float(out.get("Precirc_MWe", out.get("P_recirc_MWe", 0.0)))
    P_rad = float(out.get("Prad_core_MW", out.get("Prad_MW", 0.0)))
    P_sol = float(out.get("Psol_MW", 0.0))

    nodes = ["Fusion", "Alpha to plasma", "Neutrons to blanket", "Aux heating", "Core radiation", "SOL/divertor", "Thermal to turbine", "Recirc loads", "Net electric"]
    idx = {n:i for i,n in enumerate(nodes)}
    links = []
    def add(src, tgt, val):
        val = float(val)
        if val <= 0:
            return
        links.append((idx[src], idx[tgt], val))
    add("Fusion", "Alpha to plasma", Palpha)
    add("Fusion", "Neutrons to blanket", Pneu)
    add("Aux heating", "Alpha to plasma", Paux)
    add("Alpha to plasma", "Core radiation", P_rad)
    add("Alpha to plasma", "SOL/divertor", P_sol)
    add("Neutrons to blanket", "Thermal to turbine", max(Pth, 0.0))
    add("Thermal to turbine", "Recirc loads", max(P_recirc, 0.0))
    add("Thermal to turbine", "Net electric", max(Pnet, 0.0))

    return {
        "nodes": nodes,
        "links": links,
    }

def write_sankey_html(artifact: Dict[str, Any], savepath: str | Path, title: str = "SHAMS power balance") -> Path:
    """Write an interactive HTML Sankey diagram using Plotly if installed."""
    try:
        import plotly.graph_objects as go
    except Exception as e:
        raise RuntimeError("Plotly is required for Sankey HTML. Install with `pip install plotly`.") from e

    sank = build_power_balance_sankey(artifact)
    src = [s for s,_,_ in sank["links"]]
    tgt = [t for _,t,_ in sank["links"]]
    val = [v for *_,v in sank["links"]]

    fig = go.Figure(data=[go.Sankey(
        node=dict(label=sank["nodes"]),
        link=dict(source=src, target=tgt, value=val),
    )])
    fig.update_layout(title_text=title, font_size=12)

    p = Path(savepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(p), include_plotlyjs="cdn")
    return p
