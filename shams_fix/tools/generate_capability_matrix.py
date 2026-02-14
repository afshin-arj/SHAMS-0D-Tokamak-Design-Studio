#!/usr/bin/env python3
from __future__ import annotations

"""Generate SHAMS Physics Capability Matrix (read-only).

Deterministic generator of a reviewer-facing snapshot consumed by the UI.

Inputs:
  - provenance.authority.AUTHORITY_CONTRACTS
  - models.model_registry.default_model_registry()

Output:
  - docs/PHYSICS_CAPABILITY_MATRIX_GENERATED.md

This script does NOT run physics, does NOT execute scans, and does NOT modify
the frozen evaluator. It only summarizes already-declared authority contracts
and registered model cards.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _stable_hash_json(obj: Any) -> str:
    try:
        s = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(s).hexdigest()
    except Exception:
        return ""


def _repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "requirements.txt").exists() or (cur / ".git").exists() or (cur / "VERSION").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def _read_version(root: Path) -> str:
    p = root / "VERSION"
    if p.exists():
        return p.read_text(encoding="utf-8", errors="ignore").strip()
    return ""


def _load_authority_contracts() -> Tuple[Dict[str, Dict[str, Any]], str]:
    try:
        from provenance.authority import AUTHORITY_CONTRACTS  # type: ignore

        contracts = {k: v.to_dict() for k, v in AUTHORITY_CONTRACTS.items()}
        h = _stable_hash_json(contracts)
        return contracts, h
    except Exception:
        try:
            from src.provenance.authority import AUTHORITY_CONTRACTS  # type: ignore

            contracts = {k: v.to_dict() for k, v in AUTHORITY_CONTRACTS.items()}
            h = _stable_hash_json(contracts)
            return contracts, h
        except Exception:
            return {}, ""


def _load_model_registry() -> Dict[str, Any]:
    try:
        from models.model_registry import default_model_registry  # type: ignore

        return default_model_registry()
    except Exception:
        try:
            from src.models.model_registry import default_model_registry  # type: ignore

            return default_model_registry()
        except Exception:
            return {}


def _md_table(rows: List[List[str]], headers: List[str]) -> str:
    out: List[str] = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def main() -> int:
    here = Path(__file__).resolve()
    root = _repo_root(here)
    version = _read_version(root)
    contracts, contracts_hash = _load_authority_contracts()
    registry = _load_model_registry()

    now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    gen_meta = {
        "generated_utc": now_utc,
        "shams_version": version,
        "authority_contracts_hash_sha256": contracts_hash,
        "model_registry_hash_sha256": _stable_hash_json(registry),
    }

    # Summaries
    tiers = {}
    for _, c in contracts.items():
        t = str(c.get("tier", "unknown"))
        tiers[t] = tiers.get(t, 0) + 1

    tier_rows = [[str(k), str(v)] for k, v in sorted(tiers.items(), key=lambda kv: kv[0])]
    if not tier_rows:
        tier_rows = [["unknown", "0"]]

    contract_rows: List[List[str]] = []
    for k in sorted(contracts.keys()):
        c = contracts[k]
        contract_rows.append([
            k,
            str(c.get("tier", "unknown")),
            str(c.get("validity_domain", "")),
            str(c.get("notes", ""))[:80].replace("\n", " "),
        ])
    if not contract_rows:
        contract_rows = [["(none)", "unknown", "", ""]]

    # Model registry: best-effort table
    model_rows: List[List[str]] = []
    cards = registry.get("cards") if isinstance(registry, dict) else None
    if isinstance(cards, dict):
        for k in sorted(cards.keys()):
            cd = cards[k]
            if not isinstance(cd, dict):
                continue
            model_rows.append([
                k,
                str(cd.get("label", "")),
                str(cd.get("authority", cd.get("tier", ""))),
                str(cd.get("validity", cd.get("validity_domain", ""))),
            ])
    if not model_rows:
        model_rows = [["(unavailable)", "", "", ""]]

    md: List[str] = []
    md.append("# Physics Capability Matrix (Generated)")
    md.append("")
    md.append(f"**SHAMS version:** `{version}`")
    md.append(f"**Generated:** `{now_utc}`")
    md.append("")
    md.append("This file is generated from the frozen internal declarations (authority contracts + model registry).")
    md.append("It is read-only in the UI; edit source declarations, then regenerate.")
    md.append("")
    md.append("## Generation fingerprints")
    md.append("```json")
    md.append(json.dumps(gen_meta, indent=2, sort_keys=True))
    md.append("```")
    md.append("")
    md.append("## Authority contract coverage")
    md.append(_md_table(tier_rows, headers=["Tier", "Count"]))
    md.append("")
    md.append("### Contract list")
    md.append(_md_table(contract_rows, headers=["Subsystem", "Tier", "Validity domain", "Notes (truncated)"]))
    md.append("")
    md.append("## Model registry snapshot")
    md.append(_md_table(model_rows, headers=["Model key", "Label", "Authority", "Validity"]))
    md.append("")
    md.append("## Interpretation rules")
    md.append("- **Proxy**: screening-only; do not treat as licensing-grade.")
    md.append("- **Semi-authoritative**: regression / limited validation; requires reviewer attention.")
    md.append("- **Authoritative**: sourced from curated DB / validated closure within stated validity domain.")
    md.append("")

    out_path = root / "docs" / "PHYSICS_CAPABILITY_MATRIX_GENERATED.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
