from __future__ import annotations
"""
Validate SHAMS JSON artifacts against shipped JSON Schemas (offline-friendly).

Usage:
  python -m tools.validate_schemas --json path/to/artifact.json --schema schemas/shams_run_artifact.schema.json

If `jsonschema` is available, uses full Draft 2020-12 validation.
Otherwise falls back to minimal required-field checks for the shipped schemas.
"""
import argparse, json
from pathlib import Path
from typing import Any, Dict, List, Tuple

def _fallback_validate(obj: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    req = schema.get("required", [])
    for k in req:
        if k not in obj:
            errs.append(f"Missing required field: {k}")
    # const checks
    props = schema.get("properties", {})
    for k, spec in props.items():
        if "const" in spec and k in obj and obj[k] != spec["const"]:
            errs.append(f"Field {k} must equal {spec['const']!r} (got {obj[k]!r})")
    return errs

def main():
    ap = argparse.ArgumentParser(description="Validate JSON artifact against SHAMS schema")
    ap.add_argument("--json", required=True, help="Path to JSON artifact")
    ap.add_argument("--schema", required=True, help="Path to schema JSON")
    args = ap.parse_args()

    obj = json.loads(Path(args.json).read_text(encoding="utf-8"))
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))

    try:
        import jsonschema  # type: ignore
        jsonschema.validate(instance=obj, schema=schema)
        print("OK (jsonschema)")
        return 0
    except ImportError:
        errs = _fallback_validate(obj, schema)
        if errs:
            print("FAILED (fallback):")
            for e in errs:
                print(" -", e)
            return 2
        print("OK (fallback)")
        return 0
    except Exception as e:
        print("FAILED (jsonschema):", repr(e))
        return 3

if __name__ == "__main__":
    raise SystemExit(main())
