from __future__ import annotations

"""Campaign specification (v363.0).

A campaign is a deterministic, audit-safe wrapper around:
  - variable definitions (bounds/discrete sets)
  - fixed assumptions bundle
  - candidate generation recipe (seeded)
  - evaluation recipe (evaluator label)

No optimization occurs in this layer.

© 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json


@dataclass(frozen=True)
class CampaignVariable:
    name: str
    kind: str  # "float" | "int" | "choice"
    lo: Optional[float] = None
    hi: Optional[float] = None
    values: Optional[List[Any]] = None

    def validate(self) -> None:
        k = str(self.kind or "").lower().strip()
        if k not in {"float", "int", "choice"}:
            raise ValueError(f"CampaignVariable.kind invalid: {self.kind}")
        if not self.name or not isinstance(self.name, str):
            raise ValueError("CampaignVariable.name required")
        if k in {"float", "int"}:
            if self.lo is None or self.hi is None:
                raise ValueError(f"Variable '{self.name}' requires lo/hi")
            if float(self.hi) <= float(self.lo):
                raise ValueError(f"Variable '{self.name}' requires hi>lo")
        if k == "choice":
            if not self.values or len(self.values) < 2:
                raise ValueError(f"Variable '{self.name}' requires values")


@dataclass(frozen=True)
class GeneratorSpec:
    mode: str  # "grid" | "lhs" | "sobol" | "passthrough"
    n: int = 64
    seed: int = 123

    def validate(self) -> None:
        m = str(self.mode or "").lower().strip()
        if m not in {"grid", "lhs", "sobol", "passthrough"}:
            raise ValueError(f"GeneratorSpec.mode invalid: {self.mode}")
        if int(self.n) < 1 or int(self.n) > 2_000_000:
            raise ValueError("GeneratorSpec.n out of range")
        if int(self.seed) < 0:
            raise ValueError("GeneratorSpec.seed must be >=0")


@dataclass(frozen=True)
class ProfileContractSpec:
    tier: str = "both"  # "optimistic" | "robust" | "both"
    preset: str = "C16"  # C8/C16/C32

    def validate(self) -> None:
        t = str(self.tier or "").lower().strip()
        if t not in {"optimistic", "robust", "both"}:
            raise ValueError("ProfileContractSpec.tier invalid")
        p = str(self.preset or "").upper().strip()
        if p not in {"C8", "C16", "C32"}:
            raise ValueError("ProfileContractSpec.preset invalid")


@dataclass(frozen=True)
class CampaignSpec:
    schema: str
    name: str
    intent: str
    evaluator_label: str
    variables: List[CampaignVariable]
    fixed_inputs: Dict[str, Any]
    generator: GeneratorSpec
    profile_contracts: ProfileContractSpec
    include_full_artifact: bool = False

    def validate(self) -> None:
        if str(self.schema or "") != "shams_campaign.v1":
            raise ValueError("CampaignSpec.schema must be shams_campaign.v1")
        if not self.name:
            raise ValueError("CampaignSpec.name required")
        if not self.intent:
            raise ValueError("CampaignSpec.intent required")
        if not self.evaluator_label:
            raise ValueError("CampaignSpec.evaluator_label required")
        if not self.variables:
            raise ValueError("CampaignSpec.variables required")
        names = [v.name for v in self.variables]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate variable names")
        for v in self.variables:
            v.validate()
        if not isinstance(self.fixed_inputs, dict):
            raise ValueError("CampaignSpec.fixed_inputs must be dict")
        self.generator.validate()
        self.profile_contracts.validate()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "name": self.name,
            "intent": self.intent,
            "evaluator_label": self.evaluator_label,
            "variables": [
                {
                    "name": v.name,
                    "kind": v.kind,
                    "lo": v.lo,
                    "hi": v.hi,
                    "values": v.values,
                }
                for v in self.variables
            ],
            "fixed_inputs": dict(self.fixed_inputs),
            "generator": {"mode": self.generator.mode, "n": int(self.generator.n), "seed": int(self.generator.seed)},
            "profile_contracts": {"tier": self.profile_contracts.tier, "preset": self.profile_contracts.preset},
            "include_full_artifact": bool(self.include_full_artifact),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CampaignSpec":
        vars_raw = d.get("variables", []) or []
        variables = [
            CampaignVariable(
                name=str(v.get("name")),
                kind=str(v.get("kind", "float")),
                lo=v.get("lo", None),
                hi=v.get("hi", None),
                values=v.get("values", None),
            )
            for v in vars_raw
        ]
        gen = d.get("generator", {}) or {}
        pc = d.get("profile_contracts", {}) or {}
        spec = CampaignSpec(
            schema=str(d.get("schema", "")),
            name=str(d.get("name", "")),
            intent=str(d.get("intent", "")),
            evaluator_label=str(d.get("evaluator_label", "hot_ion_point")),
            variables=variables,
            fixed_inputs=dict(d.get("fixed_inputs", {}) or {}),
            generator=GeneratorSpec(mode=str(gen.get("mode", "sobol")), n=int(gen.get("n", 64)), seed=int(gen.get("seed", 123))),
            profile_contracts=ProfileContractSpec(tier=str(pc.get("tier", "both")), preset=str(pc.get("preset", "C16"))),
            include_full_artifact=bool(d.get("include_full_artifact", False)),
        )
        return spec


def validate_campaign_spec(spec: CampaignSpec) -> None:
    spec.validate()


def load_campaign_spec(path: Path) -> CampaignSpec:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    spec = CampaignSpec.from_dict(d)
    spec.validate()
    return spec


def save_campaign_spec(spec: CampaignSpec, path: Path) -> None:
    spec.validate()
    Path(path).write_text(json.dumps(spec.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
