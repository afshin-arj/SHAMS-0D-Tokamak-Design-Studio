from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


def _load_yaml_or_json(path: Path) -> Dict[str, Any]:
    txt = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except Exception as e:
            raise RuntimeError("YAML support requires PyYAML. Install it or use JSON.") from e
        return dict(yaml.safe_load(txt) or {})
    return dict(json.loads(txt) or {})


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass
class CaseDeck:
    """Top-level case deck (inputs → resolved config → run).

    This is intentionally additive: it coexists with existing UI presets.
    """

    schema_version: str
    label: str
    base_preset: str | None
    inputs: Dict[str, Any]
    targets: Dict[str, Any]
    variables: Dict[str, Any]
    model_overrides: Dict[str, str]

    @staticmethod
    def from_path(path: str | Path) -> "CaseDeck":
        p = Path(path)
        d = _load_yaml_or_json(p)
        return CaseDeck(
            schema_version=str(d.get("schema_version", "case_deck.v1")),
            label=str(d.get("label", p.stem)),
            base_preset=(d.get("base_preset") or None),
            inputs=dict(d.get("inputs", {}) or {}),
            targets=dict(d.get("targets", {}) or {}),
            variables=dict(d.get("variables", {}) or {}),
            model_overrides=dict(d.get("model_overrides", {}) or {}),
        )

    def to_resolved_config(self) -> Dict[str, Any]:
        """Resolve the deck to a single, explicit run config dict."""
        return {
            "schema_version": "run_config_resolved.v1",
            "label": self.label,
            "base_preset": self.base_preset,
            "inputs": dict(self.inputs),
            "targets": dict(self.targets),
            "variables": dict(self.variables),
            "model_overrides": dict(self.model_overrides),
        }

    def resolved_fingerprint_sha256(self) -> str:
        import hashlib
        s = _stable_json(self.to_resolved_config()).encode("utf-8")
        return hashlib.sha256(s).hexdigest()
