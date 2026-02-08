from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Literal, Optional
import json

VarType = Literal["continuous", "integer"]
ScaleType = Literal["linear", "log"]

@dataclass(frozen=True)
class VariableSpec:
    name: str
    vtype: VarType
    lower: float
    upper: float
    scale: ScaleType = "linear"
    units: str = ""

@dataclass(frozen=True)
class ObjectiveSpec:
    field: str
    direction: Literal["min", "max"]
    description: str = ""

@dataclass(frozen=True)
class ConstraintSpec:
    # For optimizer use: a field holding a margin with sign convention ">= 0 is feasible"
    margin_field: str
    sense: Literal[">=0"] = ">=0"
    kind: Literal["hard", "soft"] = "hard"
    description: str = ""

@dataclass(frozen=True)
class ProblemSpec:
    name: str
    variables: List[VariableSpec]
    objectives: List[ObjectiveSpec]
    constraints: List[ConstraintSpec]
    notes: str = ""

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "extopt.problem_spec.v1",
            "name": self.name,
            "variables": [vars(v) for v in self.variables],
            "objectives": [vars(o) for o in self.objectives],
            "constraints": [vars(c) for c in self.constraints],
            "notes": self.notes,
        }

    def dumps(self) -> str:
        return json.dumps(self.to_json_dict(), sort_keys=True, indent=2)
