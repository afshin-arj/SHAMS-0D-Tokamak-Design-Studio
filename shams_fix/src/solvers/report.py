from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class SolveReport:
    backend: str = ""
    status: str = "unknown"   # success | failed | partial
    message: str = ""
    n_iter: int = 0
    residual_norm: float = float("nan")
    target_errors: Dict[str, float] = field(default_factory=dict)
    best_achieved: Dict[str, float] = field(default_factory=dict)
    active_bounds: Dict[str, str] = field(default_factory=dict)  # var -> "lo"|"hi"|"" 
    trace: List[Dict[str, Any]] = field(default_factory=list)
    corners: Optional[List[Dict[str, Any]]] = None  # list of {"x":{var:val}, "out":{k:v}}
    timings_s: Dict[str, float] = field(default_factory=dict)
    scaling: Dict[str, Dict[str, float]] = field(default_factory=dict)  # {"variables":{...}, "residuals":{...}}

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "backend": self.backend,
            "status": self.status,
            "message": self.message,
            "n_iter": int(self.n_iter),
            "residual_norm": float(self.residual_norm) if self.residual_norm == self.residual_norm else None,
            "target_errors": {str(k): float(v) for k, v in (self.target_errors or {}).items()},
            "best_achieved": {str(k): float(v) for k, v in (self.best_achieved or {}).items()},
            "active_bounds": dict(self.active_bounds or {}),
            "trace": list(self.trace or []),
            "timings_s": {str(k): float(v) for k, v in (self.timings_s or {}).items()},
        }
        if self.corners is not None:
            d["corners"] = self.corners
        if self.scaling:
            d["scaling"] = {
                "variables": {str(k): float(v) for k, v in (self.scaling.get("variables") or {}).items()},
                "residuals": {str(k): float(v) for k, v in (self.scaling.get("residuals") or {}).items()},
            }
        return d
