from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

@dataclass
class ScenarioSpec:
    """Scenario defines economic and programmatic assumptions applied on top of a design point."""
    name: str = "base"
    label: str = ""
    economics_overrides: Dict[str, Any] = None
    input_overrides: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "economics_overrides": dict(self.economics_overrides or {}),
            "input_overrides": dict(self.input_overrides or {}),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ScenarioSpec":
        return ScenarioSpec(
            name=str(d.get("name","base")),
            label=str(d.get("label","")),
            economics_overrides=dict(d.get("economics_overrides") or {}),
            input_overrides=dict(d.get("input_overrides") or {}),
        )
