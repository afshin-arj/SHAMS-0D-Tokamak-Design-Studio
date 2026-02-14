from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, List

@dataclass
class SessionStateModel:
    # Point Designer
    last_point_inputs: Optional[Dict[str, Any]] = None
    last_point_outputs: Optional[Dict[str, Any]] = None
    last_point_artifact: Optional[Dict[str, Any]] = None
    last_point_radial_png: Optional[bytes] = None

    # Systems Mode
    last_systems_result: Optional[Dict[str, Any]] = None

    # Scan Mode
    last_scan_meta: Optional[Dict[str, Any]] = None
    last_scan_points: Optional[List[Dict[str, Any]]] = None

    # Sandbox
    last_sandbox_run: Optional[Dict[str, Any]] = None

    # Paper figures pack (zip bytes)
    last_figures_pack_zip: Optional[bytes] = None

    # Run timeline (most recent last)
    run_history: List[Dict[str, Any]] = None  # populated lazily in UI
    pinned_run_ids: List[str] = None  # populated lazily in UI

    def has_point(self) -> bool:
        return self.last_point_outputs is not None and self.last_point_artifact is not None
