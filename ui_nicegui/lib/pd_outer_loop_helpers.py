"""Point Designer outer-loop helpers — Phase Envelopes & UQ Contracts."""
from __future__ import annotations

import json
from dataclasses import fields
from typing import Any, Dict, List, Optional, Tuple

try:
    from src.models.inputs import PointInputs
    from src.phase_envelopes import PhaseSpec
    from src.uq_contracts import Interval, UncertaintyContractSpec
except ImportError:
    from models.inputs import PointInputs  # type: ignore
    from phase_envelopes import PhaseSpec  # type: ignore
    from uq_contracts import Interval, UncertaintyContractSpec  # type: ignore

_POINTINPUTS_FIELDS = {f.name for f in fields(PointInputs)}

VAR_GROUPS = [
    "PLASMA",
    "GEOMETRY",
    "HEATING",
    "EXHAUST",
    "MAGNETS",
    "CONTROL/PF",
    "NEUTRONICS",
    "OTHER",
    "ALL",
]

DEFAULT_PHASES_JSON = json.dumps(
    [
        {"name": "ramp_up", "input_overrides": {}, "policy_overrides": {}, "notes": "Quasi-static check (no dynamics)."},
        {"name": "flat_top", "input_overrides": {}, "policy_overrides": {}, "notes": "Baseline operating point."},
        {"name": "ramp_down", "input_overrides": {}, "policy_overrides": {}, "notes": "Quasi-static check (no dynamics)."},
    ],
    indent=2,
    sort_keys=True,
)


def field_group(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["r0", "a0", "kappa", "delta", "triang", "aspect", "elong", "shape", "major", "minor"]):
        return "GEOMETRY"
    if any(k in n for k in ["bt", "b0", "btor", "ip", "q", "beta", "li", "wth", "tau", "greenwald", "ne", "ni", "te", "ti"]):
        return "PLASMA"
    if any(k in n for k in ["paux", "pnbi", "pech", "icrh", "lhcd", "power", "heat"]):
        return "HEATING"
    if any(k in n for k in ["pf", "cs", "oh", "rwm", "vertical", "ctrl", "control"]):
        return "CONTROL/PF"
    if any(k in n for k in ["psep", "exhaust", "detachment", "div", "target", "lambda", "sol", "radiat"]):
        return "EXHAUST"
    if any(k in n for k in ["neutron", "blanket", "shield", "tbr", "wall", "fw", "dose"]):
        return "NEUTRONICS"
    if any(k in n for k in ["tf", "coil", "stress", "jcrit", "hts", "magnet"]):
        return "MAGNETS"
    return "OTHER"


def make_point_inputs(inp_dict: Dict[str, Any]) -> PointInputs:
    filtered = {k: v for k, v in (inp_dict or {}).items() if k in _POINTINPUTS_FIELDS}
    return PointInputs(**filtered)


def numeric_point_fields(base_dict: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    numeric = [k for k in sorted(_POINTINPUTS_FIELDS) if isinstance(base_dict.get(k), (int, float))]
    other = [k for k in sorted(_POINTINPUTS_FIELDS) if k not in set(numeric)]
    return numeric, other


def filter_fields_by_group(fields_list: List[str], group: str) -> List[str]:
    if group == "ALL":
        return list(fields_list)
    return [k for k in fields_list if field_group(k) == group]


def parse_phases_json(phases_json: str) -> List[PhaseSpec]:
    raw = json.loads(phases_json)
    if not isinstance(raw, list) or not raw:
        raise ValueError("Phases JSON must be a non-empty list.")
    phases: List[PhaseSpec] = []
    for item in raw:
        if not isinstance(item, dict) or "name" not in item:
            raise ValueError("Each phase must be an object with at least a 'name'.")
        phases.append(
            PhaseSpec(
                name=str(item["name"]),
                input_overrides=dict(item.get("input_overrides") or {}),
                policy_overrides=dict(item.get("policy_overrides") or {}) if item.get("policy_overrides") is not None else None,
                notes=str(item.get("notes", "")),
            )
        )
    return phases


def build_uq_spec(
    *,
    name: str,
    base_inp: Dict[str, Any],
    dims: List[str],
    mode: str,
    pct: float,
    abs_bounds: Optional[Dict[str, Tuple[float, float]]] = None,
) -> UncertaintyContractSpec:
    intervals: Dict[str, Interval] = {}
    for k in dims:
        v = base_inp.get(k)
        if not isinstance(v, (int, float)):
            continue
        v = float(v)
        if mode.startswith("±%"):
            lo = v * (1.0 - float(pct) / 100.0)
            hi = v * (1.0 + float(pct) / 100.0)
            intervals[k] = Interval(lo=lo, hi=hi)
        else:
            bounds = (abs_bounds or {}).get(k)
            if bounds is None:
                intervals[k] = Interval(lo=v, hi=v)
            else:
                intervals[k] = Interval(lo=float(bounds[0]), hi=float(bounds[1]))
    return UncertaintyContractSpec(name=str(name), intervals=intervals, policy_overrides=None, notes="")


def phase_table_rows(env: dict) -> List[dict]:
    rows: List[dict] = []
    phases = env.get("phases_ordered") or []
    if not isinstance(phases, list):
        return rows
    for art in phases:
        if not isinstance(art, dict):
            continue
        ph = art.get("phase") or {}
        cs = art.get("constraints_summary") or {}
        rows.append(
            {
                "phase": ph.get("name") if isinstance(ph, dict) else "",
                "feasible": bool(cs.get("feasible", False)),
                "n_hard_failed": cs.get("n_hard_failed"),
                "worst_hard": cs.get("worst_hard"),
                "worst_margin": cs.get("worst_hard_margin_frac"),
            }
        )
    return rows
