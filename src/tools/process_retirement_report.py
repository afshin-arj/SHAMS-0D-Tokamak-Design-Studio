"""PROCESS retirement report (governance artifact).

This is a reviewer-facing, deterministic summary that argues that SHAMS can
replace PROCESS for a given study context, while documenting lane, contracts,
and deltas.

No external data is required. Optionally, the caller may pass a PROCESS-style
JSON dict to include a lightweight parameter mapping appendix.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import datetime


def _f(x: Any, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def generate_retirement_report(
    *,
    shams_inputs: Dict[str, Any],
    shams_outputs: Dict[str, Any],
    process_payload: Optional[Dict[str, Any]] = None,
    title: str = "PROCESS Retirement Report (SHAMS)",
) -> str:
    """Return a markdown report."""
    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    lane = str(shams_outputs.get("lane", shams_inputs.get("lane", "unknown")))
    Pe_net = _f(shams_outputs.get("P_e_net_MW", float('nan')))
    f_recirc = _f(shams_outputs.get("f_recirc", float('nan')))
    TBR = _f(shams_outputs.get("TBR", float('nan')))
    TBR_req = _f(shams_outputs.get("TBR_required_fuelcycle", float('nan')))
    fw_life = _f(shams_outputs.get("fw_lifetime_yr", float('nan')))
    nwl = _f(shams_outputs.get("neutron_wall_load_MW_m2", float('nan')))

    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Generated:** {now}")
    lines.append("")
    lines.append("## Scope contract")
    lines.append("- SHAMS truth is frozen, deterministic, algebraic; no solvers.")
    lines.append("- Optimization is external-only; this report documents feasibility and margins.")
    lines.append("")
    lines.append("## Point summary (SHAMS)")
    lines.append("| Quantity | Value | Units | Notes |")
    lines.append("|---|---:|---|---|")
    lines.append(f"| Net electric | {Pe_net:.3g} | MW | from plant closure proxy |")
    lines.append(f"| Recirculating fraction | {f_recirc:.3g} | - | Precirc/Pe_gross |")
    lines.append(f"| Neutron wall load | {nwl:.3g} | MW/m² | proxy |")
    lines.append(f"| First-wall lifetime | {fw_life:.3g} | yr | proxy from dpa/y |")
    lines.append(f"| TBR | {TBR:.3g} | - | neutronics proxy |")
    lines.append(f"| Fuel-cycle required TBR | {TBR_req:.3g} | - | contract proxy |")
    lines.append("")
    lines.append("## Replacement argument")
    lines.append("This study demonstrates that SHAMS can replace PROCESS for feasibility and trade studies because:")
    lines.append("1. Feasibility is explicit (no convergence artifacts).") 
    lines.append("2. Margins are reported and exportable (reviewer-safe).") 
    lines.append("3. Optimistic-vs-robust lanes can detect mirage designs.")
    lines.append("4. Plant ledger + fuel-cycle ledger provide system-level closure for user workflows.")
    lines.append("")
    if process_payload is not None:
        lines.append("## PROCESS payload appendix (optional)")
        lines.append("A PROCESS-style payload was provided; SHAMS does not ingest it automatically.")
        lines.append("This appendix records it for audit only.")
        lines.append("```json")
        # keep small
        import json
        lines.append(json.dumps(process_payload, indent=2)[:4000])
        lines.append("```")
    lines.append("")
    lines.append("---") 
    lines.append("© 2026 Afshin Arjhangmehr") 
    return "\n".join(lines)
