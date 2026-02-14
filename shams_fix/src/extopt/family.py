from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass(frozen=True)
class ConceptCandidate:
    """A single candidate defined as overrides on top of base_inputs."""

    cid: str
    overrides: Dict[str, Any]


@dataclass(frozen=True)
class ConceptFamily:
    """A concept family definition.

    schema_version: must be "concept_family.v1".
    intent: e.g. "research" or "reactor" (passed into constraint builder).
    """

    schema_version: str
    name: str
    intent: str
    base_inputs: Dict[str, Any]
    candidates: List[ConceptCandidate]
    notes: str = ""


def load_concept_family(path: str | Path) -> ConceptFamily:
    p = Path(path)
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(d, dict):
        raise ValueError("Concept family YAML must be a mapping")

    schema = str(d.get("schema_version", ""))
    if schema != "concept_family.v1":
        raise ValueError(f"Unsupported concept family schema_version: {schema}")

    name = str(d.get("name", p.stem))
    intent = str(d.get("intent", "research"))
    base = d.get("base_inputs", {})
    if not isinstance(base, dict):
        raise ValueError("base_inputs must be a mapping")

    cand_raw = d.get("candidates", [])
    if not isinstance(cand_raw, list) or not cand_raw:
        raise ValueError("candidates must be a non-empty list")

    cands: List[ConceptCandidate] = []
    for i, c in enumerate(cand_raw):
        if not isinstance(c, dict):
            raise ValueError(f"candidate[{i}] must be a mapping")
        cid = str(c.get("id", c.get("cid", f"cand_{i:03d}")))
        ov = c.get("overrides", c.get("inputs", {}))
        if not isinstance(ov, dict):
            raise ValueError(f"candidate[{i}].overrides must be a mapping")
        cands.append(ConceptCandidate(cid=cid, overrides=ov))

    notes = str(d.get("notes", ""))
    return ConceptFamily(schema_version=schema, name=name, intent=intent, base_inputs=base, candidates=cands, notes=notes)
