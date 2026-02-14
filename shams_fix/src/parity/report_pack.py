from __future__ import annotations

"""PROCESS Parity Layer v1: report pack.

This module generates a compact, PROCESS-style report bundle from:

* Point inputs (design variables)
* Evaluator outputs (physics + constraints)
* Parity blocks (plant closure, magnets, cryo, costing)

The report pack is intended for export and reproducible sharing. It does not
attempt to match PROCESS text output formatting exactly; it matches the *information
content* in an SHAMS-native, schema-stable format.
"""

from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, Tuple


def _flatten(prefix: str, d: Dict[str, Any], out: Dict[str, Any]) -> None:
    for k, v in (d or {}).items():
        kk = f"{prefix}{k}" if prefix else str(k)
        if isinstance(v, dict):
            _flatten(kk + ".", v, out)
        else:
            out[kk] = v


def build_parity_report_pack(
    *,
    inputs: Any,
    outputs: Dict[str, Any],
    parity: Dict[str, Any],
    run_id: str,
    version: str,
) -> Dict[str, Any]:
    """Create a JSON-serializable report pack."""

    ts = datetime.utcnow().isoformat() + "Z"
    # Minimal identity section
    ident = {
        "kind": "parity_report_pack_v2",
        "run_id": str(run_id),
        "created_utc": ts,
        "shams_version": str(version),
    }

    # Inputs: best-effort serialization
    try:
        in_dict = asdict(inputs)  # dataclass
    except Exception:
        in_dict = {k: getattr(inputs, k) for k in dir(inputs) if not k.startswith("_") and isinstance(getattr(inputs, k), (int, float, str, bool))}

    # Compact summary table (flat) for CSV export
    flat: Dict[str, Any] = {}
    _flatten("in.", in_dict, flat)
    _flatten("out.", outputs, flat)
    _flatten("parity.", parity.get("derived", {}), flat)

    return {
        "identity": ident,
        "inputs": in_dict,
        "outputs": outputs,
        "parity": parity,
        "flat": flat,
    }


def report_pack_to_csv_rows(pack: Dict[str, Any]) -> Tuple[list, list]:
    """Return (header, row) for a single-row CSV export."""
    flat = dict(pack.get("flat") or {})
    header = sorted(flat.keys())
    row = [flat.get(k) for k in header]
    return header, row


def report_pack_to_markdown(pack: Dict[str, Any]) -> str:
    ident = pack.get("identity") or {}
    parity = pack.get("parity") or {}
    d = parity.get("derived") or {}

    lines = []
    lines.append(f"# SHAMS PROCESS Parity Layer — Report Pack\n")
    lines.append(f"- run_id: `{ident.get('run_id','')}`")
    lines.append(f"- created: `{ident.get('created_utc','')}`")
    lines.append(f"- SHAMS version: `{ident.get('shams_version','')}`\n")

    # Plant closure summary
    plant = (parity.get("plant") or {}).get("derived") or {}
    if plant:
        lines.append("## Plant closure")
        for k in ["Pth_MW", "P_e_gross_MW", "P_recirc_MW", "P_e_net_MW", "Qe"]:
            if k in plant:
                lines.append(f"- **{k}**: {plant[k]:.3g}")
        lines.append("")

    # Costing
    cost = (parity.get("costing") or {}).get("derived") or {}
    if cost:
        lines.append("## Costing (proxy)")
        for k in ["CAPEX_MUSD", "OPEX_MUSD_per_y", "COE_USD_per_MWh", "LCOE_USD_per_MWh"]:
            if k in cost:
                v = cost[k]
                if isinstance(v, (int, float)):
                    lines.append(f"- **{k}**: {v:.3g}")
        bd = cost.get("breakdown_MUSD") or {}
        if isinstance(bd, dict) and bd:
            lines.append("\n**CAPEX breakdown (MUSD)**")
            for kk, vv in bd.items():
                try:
                    lines.append(f"- {kk}: {float(vv):.3g}")
                except Exception:
                    lines.append(f"- {kk}: {vv}")
        lines.append("")

    # Magnets + Cryo
    mag = (parity.get("magnets") or {}).get("derived") or {}
    if mag:
        lines.append("## Magnets")
        for k in ["Bt_T", "sigma_vm_MPa", "sigma_allow_MPa", "stress_margin_frac", "E_tf_MJ", "Tcoil_K"]:
            if k in mag:
                v = mag[k]
                if isinstance(v, (int, float)):
                    lines.append(f"- **{k}**: {v:.3g}")
        lines.append("")

    cryo = (parity.get("cryo") or {}).get("derived") or {}
    if cryo:
        lines.append("## Cryogenics")
        for k in ["P_cold_20K_MW", "cryo_COP", "P_cryo_e_MW", "coil_heat_MW"]:
            if k in cryo:
                v = cryo[k]
                if isinstance(v, (int, float)):
                    lines.append(f"- **{k}**: {v:.3g}")
        lines.append("")

    # Neutronics & materials (v321.0 expansion)
    out = pack.get("outputs") or {}
    if isinstance(out, dict):
        keys = [
            ("neutron_wall_load_MW_m2", "NWL (MW/m^2)"),
            ("TBR", "TBR"),
            ("TBR_min", "TBR_min"),
            ("TBR_margin", "TBR_margin"),
            ("TBR_domain_ok", "TBR_domain_ok"),
            ("neutron_attenuation_fast", "A_fast"),
            ("neutron_attenuation_gamma", "A_gamma"),
            ("P_nuc_total_MW", "P_nuc_total_MW"),
            ("P_nuc_TF_MW", "P_nuc_TF_MW"),
            ("P_nuc_PF_MW", "P_nuc_PF_MW"),
            ("P_nuc_cryo_kW", "P_nuc_cryo_kW"),
            ("fw_lifetime_yr", "FW_life_yr"),
            ("blanket_lifetime_yr", "Blanket_life_yr"),
            ("fw_T_margin_C", "FW_T_margin_C"),
            ("blanket_T_margin_C", "Blanket_T_margin_C"),
            ("fw_sigma_margin_MPa", "FW_stress_margin_MPa"),
            ("blanket_sigma_margin_MPa", "Blanket_stress_margin_MPa"),
        ]
        present = [(k, lbl) for k, lbl in keys if k in out]
        if present:
            lines.append("## Neutronics & materials (proxy)")
            for k, lbl in present:
                v = out.get(k)
                if isinstance(v, (int, float)):
                    lines.append(f"- **{lbl}**: {v:.3g}")
                else:
                    lines.append(f"- **{lbl}**: {v}")
            lines.append("")
    # Notes
    lines.append("---")
    lines.append("This report pack is generated by SHAMS' PROCESS Parity Layer (v2).")
    lines.append("It is a transparent proxy layer and should be used for relative comparisons unless calibrated against your program references.")
    return "\n".join(lines)
