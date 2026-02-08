from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from benchmarks.constitutional.constitutions import intent_to_constitution, constitution_diff
try:
    from governance.citations import validate_clause_citations, summarize_citation_completeness
except Exception:
    from src.governance.citations import validate_clause_citations, summarize_citation_completeness

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

ALLOWED_VALUES = {"required","hard","diagnostic","ignored","unknown"}

@dataclass(frozen=True)
class CrossCodeConstitution:
    schema: str
    code_name: str
    code_version: str
    source_notes: str
    citations: List[str]
    clauses: Dict[str, str]
    authority_behavior: Dict[str, Any]

def list_crosscode_constitutions() -> List[Tuple[str, Path]]:
    items: List[Tuple[str, Path]] = []
    if DATA_DIR.exists():
        for p in sorted(DATA_DIR.glob("*.json"), key=lambda x: x.name.lower()):
            items.append((p.stem, p))
    return items

def load_crosscode_constitution(path: Path) -> CrossCodeConstitution:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != "crosscode_constitution.v1":
        raise ValueError(f"Unsupported schema: {raw.get('schema')}")
    clauses = dict(raw.get("clauses") or {})
    for k,v in list(clauses.items()):
        if v not in ALLOWED_VALUES:
            clauses[k] = "unknown"
    return CrossCodeConstitution(
        schema=raw["schema"],
        code_name=str(raw.get("code_name","")),
        code_version=str(raw.get("code_version","")),
        source_notes=str(raw.get("source_notes","")),
        citations=list(raw.get("citations") or []),
        clauses=clauses,
        authority_behavior=dict(raw.get("authority_behavior") or {}),
    )

def compare_to_shams_intent(intent: str, cc: CrossCodeConstitution) -> Dict[str, Any]:
    baseline = intent_to_constitution(intent)
    diff = constitution_diff(baseline, cc.clauses)
    unknown_count = sum(1 for v in cc.clauses.values() if v == "unknown")
    # Citation governance: if a clause is asserted (not unknown), require at least one citation.
    clause_map = {k: {"state": v, "citations": cc.citations} for k,v in cc.clauses.items()}
    citation_issues = validate_clause_citations(clause_map, state_key="state", citations_key="citations")
    citation_completeness = summarize_citation_completeness(citation_issues)
    return {
        "schema":"crosscode_comparison.v1",
        "timestamp_utc": __import__("datetime").datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "intent": intent,
        "baseline_constitution": baseline,
        "crosscode_constitution": {
            "code_name": cc.code_name,
            "code_version": cc.code_version,
            "source_notes": cc.source_notes,
            "citations": cc.citations,
            "clauses": cc.clauses,
            "authority_behavior": cc.authority_behavior,
        },
        "diff": diff,
        "unknown_clause_count": unknown_count,
        "citation_completeness": citation_completeness,
    }
