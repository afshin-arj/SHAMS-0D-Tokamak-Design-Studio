
"""Canonical citation / methods blocks for SHAMS.

Generates ready-to-paste 'Methods' text and a short citation block for papers,
proposals, and reviewer packets.

No web calls; local repo content only.
"""

from __future__ import annotations
from typing import Dict, Any
from pathlib import Path

def _safe_read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""

def build_citation_blocks(base_dir: Path) -> Dict[str, Any]:
    cff = _safe_read(base_dir / "CITATION.cff")
    manifesto = _safe_read(base_dir / "NON_OPTIMIZER_MANIFESTO.md")
    scope = _safe_read(base_dir / "docs" / "MODEL_SCOPE_CARD.md")
    vocab = _safe_read(base_dir / "docs" / "VOCABULARY_LEDGER.md")

    methods = []
    methods.append("SHAMS is a constraint-first, feasibility-authoritative 0-D tokamak design framework.")
    methods.append("Truth is defined once in a frozen evaluator; exploration negotiates around truth without modifying physics or constraints.")
    methods.append("All outputs are deterministic, replayable, and audit-ready. SHAMS does not rank or recommend machines.")
    if scope:
        methods.append("Model scope and proxy boundaries are explicitly declared (Model Scope Card).")

    return {
        "schema": "shams.forge.citation_blocks.v1",
        "citation_cff": cff.strip(),
        "methods_block": "\n".join(methods).strip(),
        "scope_card": scope.strip(),
        "vocabulary_ledger": vocab.strip(),
        "non_optimizer_manifesto": manifesto.strip(),
    }
