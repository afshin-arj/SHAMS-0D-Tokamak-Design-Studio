from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import json
from pathlib import Path

@dataclass
class SweepVar:
    name: str
    values: List[float]


@dataclass
class DistributionSpec:
    """Random-variable distribution used for Monte-Carlo/UQ."""
    name: str
    dist: str  # "uniform" | "normal" | "lognormal"
    params: Dict[str, float]  # e.g. {"lo":...,"hi":...} or {"mu":..."sigma":...}

@dataclass
class StudySpec:
    """Portable study specification for scans / Monte-Carlo / optimization.

    SHAMS stays artifact-first: a StudySpec should be serializable and runnable
    headlessly. This is inspired by PROCESS's batch workflows but modernized.
    """
    name: str
    base_preset: str = ""
    base_inputs: Dict[str, Any] = field(default_factory=dict)
    targets: Dict[str, float] = field(default_factory=dict)
    variables: Dict[str, List[float]] = field(default_factory=dict)  # var -> [x0, lo, hi]
    sweeps: List[SweepVar] = field(default_factory=list)
    distributions: List[DistributionSpec] = field(default_factory=list)
    n_samples: int = 0  # if >0, run Monte-Carlo using distributions
    seed: int = 0
    notes: str = ""
    outputs: List[str] = field(default_factory=list)  # keys to record in UQ aggregates
    # --- Execution / scaling ---
    max_iter: int = 35
    tol: float = 1e-3
    damping: float = 0.6
    n_workers: int = 1  # parallelism for studies (Windows-safe spawn)
    use_sqlite_index: bool = False  # optional sqlite index (else JSON)

    # --- Optional subsystem configs recorded in artifacts ---
    fidelity: Optional[Dict[str, Any]] = None
    calibration: Optional[Dict[str, Any]] = None


    @staticmethod
    def from_path(path: Union[str, Path]) -> "StudySpec":
        p = Path(path)
        raw = p.read_text(encoding="utf-8")
        if p.suffix.lower() in (".yaml", ".yml"):
            try:
                import yaml  # type: ignore
            except Exception as e:
                raise RuntimeError("YAML study spec requires pyyaml") from e
            data = yaml.safe_load(raw)
        else:
            data = json.loads(raw)
        return StudySpec.from_dict(data)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "StudySpec":
        sweeps = []
        for s in d.get("sweeps", []) or []:
            sweeps.append(SweepVar(name=str(s["name"]), values=[float(x) for x in s.get("values", [])]))
        dists: List[DistributionSpec] = []
        for ds in d.get("distributions", []) or []:
            dists.append(DistributionSpec(
                name=str(ds.get("name")),
                dist=str(ds.get("dist", "uniform")),
                params={str(k): float(v) for k, v in (ds.get("params", {}) or {}).items()},
            ))
        return StudySpec(
            name=str(d.get("name", "study")),
            base_preset=str(d.get("base_preset", "")),
            base_inputs=dict(d.get("base_inputs", {}) or {}),
            targets={str(k): float(v) for k, v in (d.get("targets", {}) or {}).items()},
            variables={str(k): [float(x) for x in v] for k, v in (d.get("variables", {}) or {}).items()},
            sweeps=sweeps,
            distributions=dists,
            n_samples=int(d.get("n_samples", 0) or 0),
            seed=int(d.get("seed", 0) or 0),
            notes=str(d.get("notes", "")),
            outputs=[str(x) for x in (d.get("outputs", []) or [])],
            max_iter=int(d.get("max_iter", 35) or 35),
            tol=float(d.get("tol", 1e-3) or 1e-3),
            damping=float(d.get("damping", 0.6) or 0.6),
            n_workers=int(d.get("n_workers", 1) or 1),
            use_sqlite_index=bool(d.get("use_sqlite_index", False)),
            fidelity=dict(d.get("fidelity", {}) or {}) if d.get("fidelity", None) is not None else None,
            calibration=dict(d.get("calibration", {}) or {}) if d.get("calibration", None) is not None else None,
        )