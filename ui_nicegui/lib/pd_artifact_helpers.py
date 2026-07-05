"""Build canonical run artifacts for NiceGUI Point Designer."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_point_artifact(
    *,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    design_intent: str = "",
    forensics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Rich artifact for dominance/closure/export — uses shams_io when available."""
    constraints_list: List[Any] = []
    solver_meta = dict(outputs.get("_solver")) if isinstance(outputs.get("_solver"), dict) else None
    try:
        try:
            from constraints.constraints import evaluate_constraints
        except ImportError:
            from src.constraints.constraints import evaluate_constraints  # type: ignore
        constraints_list = evaluate_constraints(outputs)
    except Exception:
        constraints_list = []

    try:
        try:
            from shams_io.run_artifact import build_run_artifact
        except ImportError:
            from src.shams_io.run_artifact import build_run_artifact  # type: ignore
        artifact = build_run_artifact(
            inputs=dict(inputs),
            outputs=dict(outputs),
            constraints=constraints_list,
            solver=solver_meta,
            baseline_inputs=dict(inputs),
        )
    except Exception:
        artifact = {
            "inputs": dict(inputs),
            "outputs": dict(outputs),
            "constraints": list(constraints_list) if constraints_list else [],
            "solver": solver_meta,
        }

    if design_intent:
        artifact["design_intent"] = str(design_intent)
    if isinstance(forensics, dict) and forensics:
        artifact.setdefault("studies", {})
        artifact["studies"]["feasibility_forensics"] = forensics
    return artifact
