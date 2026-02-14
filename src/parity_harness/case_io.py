from __future__ import annotations

"""Benchmark case I/O for PROCESS parity harness (v364.0).

These benchmark cases are synthetic by default and exist to exercise:
- evaluator determinism
- constraint ledgers and dominance attribution
- robustness overlays (profile contracts)
- mapping artifacts for PROCESS-style parity discussion

No claim of correspondence to any specific machine is implied unless a case explicitly
states a provenance source.

© 2026 Afshin Arjhangmehr
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import json


@dataclass(frozen=True)
class BenchmarkCase:
    suite: str
    case_id: str
    label: str
    notes: str
    inputs: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "shams_benchmark_case.v1",
            "suite": self.suite,
            "case_id": self.case_id,
            "label": self.label,
            "notes": self.notes,
            "inputs": dict(self.inputs),
        }


def load_case(path: Path) -> BenchmarkCase:
    path = Path(path)
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("Benchmark case must be a JSON object")

    if str(obj.get("schema", "")) != "shams_benchmark_case.v1":
        raise ValueError("Unsupported benchmark case schema")

    suite = str(obj.get("suite", ""))
    case_id = str(obj.get("case_id", ""))
    label = str(obj.get("label", ""))
    notes = str(obj.get("notes", ""))
    inputs = obj.get("inputs", {})
    if not isinstance(inputs, dict):
        raise ValueError("Benchmark case 'inputs' must be an object")

    return BenchmarkCase(suite=suite, case_id=case_id, label=label, notes=notes, inputs=dict(inputs))


def discover_cases(cases_dir: Path, *, suite: str = "v364") -> List[Path]:
    cases_dir = Path(cases_dir)
    if not cases_dir.exists():
        return []
    paths = sorted(p for p in cases_dir.glob(f"{suite}_*.json") if p.is_file())
    return paths
