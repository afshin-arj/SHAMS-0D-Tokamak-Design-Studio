"""PROPOSAL-026: code-generate authority spec module from JSON registry."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

_HEADER = '''"""AUTO-GENERATED from authority_caps.json — do not edit by hand.

Regenerate: python -m constraints.registry_codegen
"""
from __future__ import annotations

from typing import Any, Dict, List

REGISTRY_SPECS: List[Dict[str, Any]] = [
'''


def _registry_json_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "authority_caps.json"


def _codegen_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "authority_specs_codegen.py"


def _row_literal(row: Dict[str, Any]) -> str:
    parts = [f'"{k}": {json.dumps(v)}' for k, v in row.items()]
    return "    {" + ", ".join(parts) + "},"


def generate_registry_module(*, write: bool = True) -> str:
    """Render Python module text from authority_caps.json."""
    rows: List[Dict[str, Any]] = json.loads(_registry_json_path().read_text(encoding="utf-8"))
    body = _HEADER
    for row in rows:
        body += _row_literal(row) + "\n"
    body += "]\n"
    body += f"REGISTRY_SPEC_COUNT = {len(rows)}\n"
    if write:
        _codegen_path().write_text(body, encoding="utf-8")
    return body


def verify_codegen_sync() -> bool:
    """Return True when JSON and generated module agree on spec count."""
    rows = json.loads(_registry_json_path().read_text(encoding="utf-8"))
    try:
        from .data.authority_specs_codegen import REGISTRY_SPEC_COUNT, REGISTRY_SPECS  # type: ignore

        return len(rows) == REGISTRY_SPEC_COUNT and len(REGISTRY_SPECS) == REGISTRY_SPEC_COUNT
    except Exception:
        return False


if __name__ == "__main__":
    generate_registry_module(write=True)
    print(f"wrote {_codegen_path()}")
