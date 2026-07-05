"""Control Room Chronicle helpers — Phase 18."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ui_nicegui.bootstrap import repo_root


def repo() -> Path:
    return Path(repo_root())


def point_inputs_from_artifact(art: dict):
    from src.models.inputs import PointInputs

    inp_d = art.get("inputs") if isinstance(art.get("inputs"), dict) else {}
    if not inp_d:
        raise ValueError("Artifact has no inputs block")
    try:
        return PointInputs.from_dict(inp_d)
    except Exception:
        fields = PointInputs.__dataclass_fields__.keys()
        return PointInputs(**{k: inp_d[k] for k in fields if k in inp_d})


def run_sensitivity_pack(
    base,
    *,
    knobs: List[str],
    outputs: List[str],
    step_rel: float = 1e-3,
) -> dict:
    from src.analysis.sensitivity import deterministic_sensitivity_pack

    scales = {k: 1.0 for k in knobs}
    scales.update({"Paux_MW": 10.0, "Ip_MA": 1.0, "fG": 0.1, "Bt_T": 0.5, "R0_m": 0.5, "a_m": 0.2})
    return deterministic_sensitivity_pack(
        base,
        variables={k: scales.get(k, 1.0) for k in knobs},
        outputs=list(outputs),
        step_rel=float(step_rel),
    )


def sensitivity_table_rows(pack: dict, knobs: List[str], outputs: List[str]) -> List[dict]:
    rows: List[dict] = []
    jac = pack.get("jacobian") if isinstance(pack.get("jacobian"), dict) else {}
    for o in outputs:
        for p in knobs:
            try:
                v = float((jac.get(o) or {}).get(p))
            except (TypeError, ValueError):
                v = None
            rows.append({"output": o, "knob": p, "jacobian": v})
    return rows


def load_study_index(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Study index must be a JSON object")
    return data


def feasibility_map_grid(cases: List[dict], xcol: str, ycol: str) -> dict:
    xs = sorted({c.get(xcol) for c in cases if xcol in c})
    ys = sorted({c.get(ycol) for c in cases if ycol in c})
    grid: List[List[Optional[bool]]] = []
    for y in ys:
        row: List[Optional[bool]] = []
        for x in xs:
            match = [c for c in cases if c.get(xcol) == x and c.get(ycol) == y]
            if not match:
                row.append(None)
            else:
                row.append(bool(match[0].get("ok", match[0].get("is_feasible"))))
        grid.append(row)
    return {"x": xs, "y": ys, "ok_grid": grid, "n_cases": len(cases)}


def flatten_certified_search_artifact(art: dict) -> tuple:
    variables = list((art.get("spec") or {}).get("variables") or [])
    records: List[dict] = []
    for stg in art.get("stages") or []:
        if not isinstance(stg, dict):
            continue
        for r in stg.get("records") or []:
            if not isinstance(r, dict):
                continue
            x = r.get("x") or {}
            if isinstance(x, dict):
                records.append(
                    {
                        "x": x,
                        "verdict": r.get("verdict"),
                        "score": r.get("score"),
                        "evidence": r.get("evidence") or {},
                        "stage": stg.get("name"),
                    }
                )
    return variables, records


def analyze_interval_narrowing(
    variables: List[dict],
    records: List[dict],
    *,
    bins: int = 12,
    min_samples_per_bin: int = 2,
) -> dict:
    from src.solvers.interval_narrowing import propose_interval_narrowing

    return propose_interval_narrowing(
        variables=variables,
        records=records,
        bins=int(bins),
        min_samples_per_bin=int(min_samples_per_bin),
    )


def run_local_forensics(base, *, design_intent: str = "Reactor") -> dict:
    from src.analysis.forensics import local_sensitivity

    return local_sensitivity(base, design_intent=design_intent)


def list_variable_registry_keys() -> List[str]:
    try:
        from docs.variable_registry import VARIABLES
    except ImportError:
        try:
            from src.docs.variable_registry import VARIABLES
        except ImportError:
            return []
    return sorted({str(v.get("key", "")) for v in VARIABLES if v.get("key")})
