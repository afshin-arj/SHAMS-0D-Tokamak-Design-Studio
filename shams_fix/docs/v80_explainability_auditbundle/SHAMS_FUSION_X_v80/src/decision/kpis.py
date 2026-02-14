from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional


@dataclass(frozen=True)
class KPI:
    key: str
    label: str
    units: str = ""
    fmt: str = "{:g}"  # applied to float(value)
    fallback: Any = float("nan")


# Single source of truth for headline KPIs used in UI + PDF, in stable order.
# Keep this list short and decision-relevant.
KPI_SET: List[KPI] = [
    KPI("Q_DT_eqv", "Q_DT_eqv", "-", "{:.3f}"),
    KPI("H98", "H98", "-", "{:.3f}"),
    KPI("Pfus_DT_adj_MW", "Pfus_DT_adj [MW]", "MW", "{:.1f}"),
    KPI("Ploss_MW", "Ploss [MW]", "MW", "{:.1f}"),
    KPI("Bpeak_T", "Bpeak [T]", "T", "{:.2f}"),
    KPI("sigma_hoop_MPa", "σ_hoop [MPa]", "MPa", "{:.0f}"),
    KPI("q_div_MW_m2", "q_div [MW/m²]", "MW/m²", "{:.1f}"),
    KPI("TBR", "TBR", "-", "{:.2f}"),
    KPI("P_net_e_MW", "P_net_e [MW]", "MW", "{:.1f}"),
    KPI("COE_proxy_USD_per_MWh", "COE_proxy [$/MWh]", "$/MWh", "{:.0f}"),
]


def format_kpi_value(kpi: KPI, outputs: Dict[str, Any]) -> str:
    v = outputs.get(kpi.key, kpi.fallback)
    try:
        if v is None:
            return "—"
        vf = float(v)
        if vf != vf:
            return "—"
        return kpi.fmt.format(vf)
    except Exception:
        return str(v)


def headline_kpis(outputs: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Return (label, formatted_value) pairs in stable order."""
    return [(k.label, format_kpi_value(k, outputs)) for k in KPI_SET]
