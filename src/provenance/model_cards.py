from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import hashlib
import yaml

_MODEL_CARD_DIR = Path(__file__).resolve().parent.parent / "model_cards"

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def load_model_cards() -> Dict[str, Dict[str, Any]]:
    """Load all model cards shipped with the repo.

    Returns dict keyed by card id, with minimal metadata + full card content.
    """
    cards: Dict[str, Dict[str, Any]] = {}
    if not _MODEL_CARD_DIR.exists():
        return cards
    for p in sorted(_MODEL_CARD_DIR.glob("*.yaml")):
        raw = p.read_bytes()
        doc = yaml.safe_load(raw) or {}
        cid = str(doc.get("id") or p.stem)
        cards[cid] = {
            "id": cid,
            "name": str(doc.get("name","")),
            "version": str(doc.get("version","")),
            "module": str(doc.get("module","")),
            "entrypoint": str(doc.get("entrypoint","")),
            "sha256": _sha256_bytes(raw),
            "path": str(p.relative_to(Path(__file__).resolve().parent.parent)),
            "card": doc,
        }
    return cards

def model_cards_index() -> Dict[str, Dict[str, Any]]:
    """Return a compact index suitable for storing in artifacts.

    Keeps artifact payloads light while preserving auditability:
      - id/name/version/hash: identity + provenance
      - maturity: TRL + assumption envelope tags
      - validity: ranges used by check_model_card_validity
    """
    cards = load_model_cards()
    idx: Dict[str, Dict[str, Any]] = {}
    for k, v in (cards or {}).items():
        card = (v or {}).get("card") or {}
        entry = {
            "id": v.get("id", k),
            "name": v.get("name", k),
            "version": v.get("version", ""),
            "hash": v.get("sha256", ""),
            "maturity": card.get("maturity", {}),
            "validity": card.get("validity", {}),
        }
        idx[k] = entry

        # Backward-compatible aliases: allow both "plasma_hot_ion_point" and
        # "plasma.hot_ion_point" style identifiers.
        if "_" in k and "." not in k:
            parts = k.split("_", 1)
            if len(parts) == 2:
                alias = f"{parts[0]}.{parts[1]}"
                if alias not in idx:
                    idx[alias] = entry
    return idx


def check_model_card_validity(index: Dict[str, Dict[str, Any]], inputs: Dict[str, Any], outputs: Dict[str, Any]) -> Dict[str, Any]:
    """Check simple validity ranges declared in model cards.

    Expected schema in model card YAML:
      validity:
        inputs:
          R0_m: [min,max]
        outputs:
          betaN_proxy: [min,max]

    Values missing from inputs/outputs are ignored.
    """
    status: Dict[str, Any] = {}
    for mid, info in (index or {}).items():
        v = (info or {}).get("validity") or {}
        failed = []
        for space, src in (("inputs", inputs), ("outputs", outputs)):
            ranges = (v.get(space) or {})
            for key, bounds in ranges.items():
                try:
                    if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
                        continue
                    lo, hi = bounds
                    if key not in src:
                        continue
                    x = float(src.get(key))
                    if lo is not None and x < float(lo):
                        failed.append({"field": f"{space}.{key}", "value": x, "lo": lo, "hi": hi})
                    elif hi is not None and x > float(hi):
                        failed.append({"field": f"{space}.{key}", "value": x, "lo": lo, "hi": hi})
                except Exception:
                    continue
        status[mid] = {"ok": len(failed) == 0, "failed": failed}
    return status
