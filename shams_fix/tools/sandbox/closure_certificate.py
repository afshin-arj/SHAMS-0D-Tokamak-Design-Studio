
"""Feasibility Closure Certificate (FCC)

A formal, exportable closure summary for a Forge candidate.
Purely descriptive; does not alter evaluation.

Schema: shams.forge.fcc.v1
"""

from __future__ import annotations
from typing import Any, Dict, Optional

def build_closure_certificate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    c = candidate or {}
    intent = str(c.get("intent") or "")
    feasible = bool(c.get("feasible", False))

    closure = c.get("closure_bundle") if isinstance(c.get("closure_bundle"), dict) else {}
    gates = c.get("reality_gates") if isinstance(c.get("reality_gates"), dict) else {}

    # Conservative interpretation: if a key is absent, mark as unknown.
    def _tri(pass_key: str) -> str:
        v = gates.get(pass_key)
        if v is True:
            return "PASS"
        if v is False:
            return "FAIL"
        return "UNKNOWN"

    cert = {
        "schema": "shams.forge.fcc.v1",
        "intent": intent,
        "feasible": feasible,
        "verdict": "PASS" if feasible else "FAIL",
        "closures": {
            "power_balance": _tri("power_balance_ok"),
            "net_electric": _tri("net_electric_ok") if intent.upper().startswith("REACTOR") or intent.lower().startswith("reactor") else "N/A",
            "magnet": _tri("magnet_ok"),
            "cryo": _tri("cryo_ok"),
            "radial_build": _tri("radial_build_ok"),
        },
        "key_numbers": {
            "gross_electric_MW": closure.get("gross_electric_MW"),
            "recirc_electric_MW": closure.get("recirc_electric_MW"),
            "net_electric_MW": closure.get("net_electric_MW"),
        },
        "notes": [
            "FCC is a 0-D closure certificate under declared proxies; it does not imply safety, availability, or licensing readiness.",
        ],
    }
    # Conditional verdict: if feasible but some closures unknown, mark conditional.
    if feasible and any(v == "UNKNOWN" for v in cert["closures"].values() if isinstance(v, str)):
        cert["verdict"] = "CONDITIONAL"
    return cert
